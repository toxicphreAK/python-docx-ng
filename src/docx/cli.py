"""A command-line front end for the inspection and cleanup operations.

``python -m docx`` answers the questions people ask about a `.docx` one at a time:
what styles it defines, which are actually used, and why the file is 900 KB. Those are
diagnostic operations — you run them to find out something about a file, not as part of
an application — and a diagnostic API with no command-line front end mostly does not get
used.

Deliberately thin: every subcommand maps onto one public library operation and holds no
logic of its own, so the CLI cannot drift from the API or grow behaviour that is only
reachable through it. argparse only; no new runtime dependency.

Two rules the commands keep:

- **Never modify the input.** ``cleanup`` writes to ``-o`` and refuses without it.
  Someone will point it at their only copy.
- **Exit codes matter**, because this ends up in scripts: non-zero for a document that
  cannot be opened, and ``--check`` reports what would be removed and exits non-zero if
  anything would be, so it can be a CI gate.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from typing import IO, Any, Dict, List, Sequence

import docx
from docx.opc.exceptions import EncryptedPackageError, PackageNotFoundError

#: Exit code for a document that cannot be opened.
EXIT_CANNOT_OPEN = 2
#: Exit code for `cleanup --check` when there is something to remove.
EXIT_WOULD_CHANGE = 1


def main(argv: Sequence[str] | None = None, stdout: IO[str] | None = None) -> int:
    """Run the CLI; return the process exit code.

    `argv` and `stdout` are injectable so the tests do not have to drive a subprocess.
    """
    out = sys.stdout if stdout is None else stdout
    parser = _build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "func", None) is None:
        parser.print_help(out)
        return 0

    try:
        return args.func(args, out)
    except FileNotFoundError as e:
        print("error: no such file: %s" % e.filename, file=sys.stderr)
        return EXIT_CANNOT_OPEN
    except EncryptedPackageError:
        print("error: document is password-protected", file=sys.stderr)
        return EXIT_CANNOT_OPEN
    except (PackageNotFoundError, zipfile.BadZipFile) as e:
        print("error: cannot open document: %s" % e, file=sys.stderr)
        return EXIT_CANNOT_OPEN
    except KeyError as e:
        # -- `styles extract --names` and `cleanup --keep` name styles, and a name the
        # -- document does not define surfaces here rather than as a traceback --
        message = e.args[0] if e.args else str(e)
        print("error: %s" % message, file=sys.stderr)
        return EXIT_CANNOT_OPEN


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m docx",
        description="Inspect and clean up Word documents.",
    )
    parser.set_defaults(func=None)
    subparsers = parser.add_subparsers(dest="command")

    info = subparsers.add_parser(
        "info",
        help="list the parts of a document with their sizes",
        description=(
            "The fastest answer to 'why is this file like this' — the part inventory"
            " with sizes and content types, which is how the 438 KB"
            " stylesWithEffects.xml in the bundled template turned up."
        ),
    )
    info.add_argument("path")
    info.add_argument("--json", action="store_true", help="emit JSON rather than a table")
    info.set_defaults(func=_cmd_info)

    styles = subparsers.add_parser("styles", help="inspect a document's styles")
    styles_sub = styles.add_subparsers(dest="styles_command")
    styles.set_defaults(func=lambda args, out: _require_subcommand(styles, out))

    report = styles_sub.add_parser("report", help="summarise defined and used styles")
    report.add_argument("path")
    report.add_argument("--json", action="store_true")
    report.set_defaults(func=_cmd_styles_report)

    listing = styles_sub.add_parser("list", help="list style names")
    listing.add_argument("path")
    # -- asking for both would silently print nothing, so argparse refuses the pair --
    which = listing.add_mutually_exclusive_group()
    which.add_argument("--unused", action="store_true", help="only the unused ones")
    which.add_argument("--used", action="store_true", help="only the ones in use")
    listing.add_argument("--json", action="store_true")
    listing.set_defaults(func=_cmd_styles_list)

    extract = styles_sub.add_parser("extract", help="write styles to a new document")
    extract.add_argument("path")
    extract.add_argument("-o", "--output", required=True, help="where to write")
    extract.add_argument(
        "--names", help="comma-separated style names; every style when omitted"
    )
    extract.add_argument(
        "--as-template", action="store_true", help="write a .dotx rather than a .docx"
    )
    extract.set_defaults(func=_cmd_styles_extract)

    cleanup = subparsers.add_parser(
        "cleanup",
        help="remove unused styles, numbering and media",
        description=(
            "Destructive, so it never writes to the input: -o is required. --check"
            " reports what would go and exits non-zero if anything would, so it can be"
            " a CI gate."
        ),
    )
    cleanup.add_argument("path")
    cleanup.add_argument("-o", "--output", help="where to write; required unless --check")
    cleanup.add_argument(
        "--check",
        action="store_true",
        help="report what would be removed and exit non-zero if anything would be",
    )
    cleanup.add_argument("--keep", help="comma-separated style names to preserve")
    cleanup.add_argument("--no-styles", action="store_true")
    cleanup.add_argument("--no-numbering", action="store_true")
    cleanup.add_argument("--no-media", action="store_true")
    cleanup.add_argument(
        "--latent-styles",
        action="store_true",
        help="also drop the latent-style exceptions, which changes Word's style gallery",
    )
    cleanup.add_argument("--json", action="store_true")
    cleanup.set_defaults(func=_cmd_cleanup)

    return parser


def _require_subcommand(parser: argparse.ArgumentParser, out: IO[str]) -> int:
    parser.print_help(out)
    return 0


def _names_arg(value: str | None) -> List[str] | None:
    """A `--names`-style comma-separated list, or |None| when it was not given."""
    if value is None:
        return None
    return [name.strip() for name in value.split(",") if name.strip()]


def _emit(out: IO[str], payload: Dict[str, Any] | List[Any], as_json: bool, lines: List[str]):
    """Write `payload` as JSON or `lines` as text.

    A `--json` flag on the reporting commands costs nothing and makes the whole thing
    composable, so every reporting command has one.
    """
    if as_json:
        print(json.dumps(payload, indent=2), file=out)
    else:
        for line in lines:
            print(line, file=out)


def _cmd_info(args: argparse.Namespace, out: IO[str]) -> int:
    with zipfile.ZipFile(args.path) as package:
        members = [
            {
                "name": info.filename,
                "size": info.file_size,
                "compressed": info.compress_size,
            }
            for info in package.infolist()
        ]
    total = sum(m["size"] for m in members)
    compressed = os.path.getsize(args.path)

    lines = ["%10d  %s" % (m["size"], m["name"]) for m in sorted(
        members, key=lambda m: -m["size"]
    )]
    lines.append("%10d  TOTAL uncompressed (%d on disk)" % (total, compressed))

    _emit(
        out,
        {"parts": members, "uncompressed": total, "on_disk": compressed},
        args.json,
        lines,
    )
    return 0


def _cmd_styles_report(args: argparse.Namespace, out: IO[str]) -> int:
    document = docx.Document(args.path)
    usage = document.styles.usage()

    by_type: Dict[str, int] = {}
    for style in document.styles:
        name = style.type.name.lower() if style.type else "unknown"
        by_type[name] = by_type.get(name, 0) + 1

    lines = [
        "%d styles defined  (%s)"
        % (
            len(usage.defined),
            ", ".join("%d %s" % (count, name) for name, count in sorted(by_type.items())),
        ),
        "%d in use, %d unused" % (len(usage.used), len(usage.unused)),
        "%d latent style exceptions" % len(usage.latent),
    ]
    _emit(
        out,
        {
            "defined": len(usage.defined),
            "by_type": by_type,
            "used": len(usage.used),
            "unused": len(usage.unused),
            "latent": len(usage.latent),
        },
        args.json,
        lines,
    )
    return 0


def _cmd_styles_list(args: argparse.Namespace, out: IO[str]) -> int:
    document = docx.Document(args.path)
    usage = document.styles.usage()
    used_ids = set(usage.used)

    names: List[str] = []
    for style in document.styles:
        if args.unused and style.style_id in used_ids:
            continue
        if args.used and style.style_id not in used_ids:
            continue
        names.append(style.name or style.style_id)

    _emit(out, names, args.json, names)
    return 0


def _cmd_styles_extract(args: argparse.Namespace, out: IO[str]) -> int:
    document = docx.Document(args.path)
    added = document.styles.extract(
        args.output, _names_arg(args.names), as_template=args.as_template
    )
    print("extracted %d styles to %s" % (len(added), args.output), file=out)
    return 0


def _cmd_cleanup(args: argparse.Namespace, out: IO[str]) -> int:
    if not args.check and not args.output:
        print(
            "error: cleanup needs -o/--output; it never writes to the input",
            file=sys.stderr,
        )
        return EXIT_CANNOT_OPEN

    document = docx.Document(args.path)
    result = document.cleanup(
        styles=not args.no_styles,
        numbering=not args.no_numbering,
        media=not args.no_media,
        latent_styles=args.latent_styles,
        keep=tuple(_names_arg(args.keep) or ()),
    )

    payload = {
        "styles": list(result.styles),
        "num_ids": list(result.num_ids),
        "abstract_num_ids": list(result.abstract_num_ids),
        "media": list(result.media),
        "latent_styles": result.latent_styles,
    }
    summary = str(result)
    lines = ["would have " + summary if args.check else summary]

    would_change = bool(
        result.styles
        or result.num_ids
        or result.abstract_num_ids
        or result.media
        or result.latent_styles
    )

    if args.check:
        _emit(out, payload, args.json, lines)
        return EXIT_WOULD_CHANGE if would_change else 0

    document.save(args.output)
    lines.append("wrote %s" % args.output)
    _emit(out, payload, args.json, lines)
    return 0
