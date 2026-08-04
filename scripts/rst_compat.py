"""Render the reStructuredText markup inherited from upstream as Markdown.

The docstrings in ``src/docx`` follow upstream python-docx's conventions. Class
references are written as ``|Paragraph|`` substitutions, which the retired Sphinx
configuration expanded from an ``rst_epilog`` table; cross-references use roles such as
``:attr:`.Document.styles```; and example code is introduced by a trailing ``::``.

Rewriting all of that in the source would conflict with every future merge from
upstream, so the translation runs at documentation build time instead. Targets are
resolved against the object tree Griffe has already built rather than against a
hand-maintained table, so a reference works as soon as the thing it names exists.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from griffe import Extension

if TYPE_CHECKING:
    from griffe import GriffeLoader, Module, Object

# -- names that resolve to the standard library rather than to anything in this package,
# -- and so are rendered as plain code spans --
_STDLIB_NAMES = frozenset(
    (
        "AttributeError",
        "bool",
        "datetime",
        "dict",
        "False",
        "float",
        "IndexError",
        "int",
        "KeyError",
        "None",
        "str",
        "True",
        "TypeError",
        "ValueError",
    )
)

# -- ``|docx|`` stands for the project name in running text --
_PROJECT_SUBSTITUTION = "python-docx"

_SUBSTITUTION_RE = re.compile(r"\|([A-Za-z_][A-Za-z0-9_]*)\|")
_ROLE_RE = re.compile(r":(attr|class|meth|func|exc|mod|obj|data|ref):`([^`]+)`")
_MS_API_NAME_RE = re.compile(r"MS API name: `([A-Za-z0-9_]+)`")
_LITERAL_INTRO_RE = re.compile(r"\S::$")
_FENCE_RE = re.compile(r"^\s*```")


def _indent_of(line: str) -> int:
    """Number of leading spaces on `line`, or 0 for a blank line."""
    return len(line) - len(line.lstrip())


def _fence_literal_blocks(text: str) -> str:
    """Replace RST literal blocks in `text` with fenced code blocks.

    A trailing ``::`` introduces the indented block that follows it. The fence is tagged
    ``xml`` when the block opens with a tag and ``python`` otherwise, which covers every
    literal block in this package.
    """
    lines = text.split("\n")
    out: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        bare = line.strip() == "::"
        if not bare and not _LITERAL_INTRO_RE.search(line):
            out.append(line)
            i += 1
            continue

        intro_indent = _indent_of(line)
        if bare:
            intro_indent = _indent_of(line)
        else:
            # -- "Example::" introduces the block and stays as "Example:" --
            out.append(line[:-1])
        i += 1

        while i < len(lines) and not lines[i].strip():
            i += 1
        if i == len(lines):
            break

        block_indent = _indent_of(lines[i])
        if block_indent <= intro_indent:
            # -- nothing is actually indented under the marker --
            continue

        block: list[str] = []
        while i < len(lines) and (not lines[i].strip() or _indent_of(lines[i]) >= block_indent):
            block.append(lines[i][block_indent:] if lines[i].strip() else "")
            i += 1
        while block and not block[-1]:
            block.pop()

        pad = " " * intro_indent
        lang = "xml" if block and block[0].lstrip().startswith("<") else "python"
        out.append("")
        out.append(f"{pad}```{lang}")
        out.extend(f"{pad}{block_line}" if block_line else "" for block_line in block)
        out.append(f"{pad}```")
        out.append("")

    return "\n".join(out)


class RstCompat(Extension):
    """Translate the inherited RST markup in every docstring into Markdown."""

    def __init__(self) -> None:
        self._objects: dict[str, str] = {}
        self._members: dict[str, str] = {}
        self._ms_api_names: dict[str, str] = {}
        self._aliases: dict[str, str] = {}

    # -- index -------------------------------------------------------------------------

    @staticmethod
    def _better(existing: str, candidate: str) -> str:
        """The more likely of two paths to be the one a docstring means.

        Prefers the public API layer over the XML and packaging layers, then the shorter
        path, which puts ``docx.text.paragraph.Paragraph`` ahead of any namesake nested
        deeper in the tree.
        """

        def rank(path: str) -> tuple[bool, int, str]:
            return (path.startswith(("docx.oxml.", "docx.opc.")), path.count("."), path)

        return min(existing, candidate, key=rank)

    def _record(self, index: dict[str, str], key: str, path: str) -> None:
        index[key] = self._better(index[key], path) if key in index else path

    def _index(self, obj: Object) -> None:
        """Walk `obj` recording every name a docstring might refer to."""
        for member in obj.members.values():
            if member.is_alias:
                continue
            kind = member.kind.value

            # -- a compatibility alias such as ``_ParagraphStyle = ParagraphStyle`` has
            # -- no documentation of its own; point references at the real class --
            if kind == "attribute":
                value = str(getattr(member, "value", "") or "")
                if value.isidentifier():
                    self._aliases[member.name] = value
                    continue

            self._record(self._objects, member.name, member.path)

            if kind == "class":
                docstring = member.docstring.value if member.docstring else ""
                if match := _MS_API_NAME_RE.search(docstring):
                    self._record(self._ms_api_names, match.group(1), member.path)
                for sub in member.members.values():
                    if not sub.is_alias:
                        self._record(self._members, f"{member.name}.{sub.name}", sub.path)

            if kind in ("module", "class"):
                self._index(member)

    def _resolve(self, target: str) -> str | None:
        """The canonical path `target` names, or `None` when nothing matches."""
        target = self._aliases.get(target.lstrip("."), target.lstrip("."))
        for index in (self._members, self._objects, self._ms_api_names):
            if target in index:
                return index[target]
        return None

    # -- translation -------------------------------------------------------------------

    def _substitution(self, match: re.Match[str]) -> str:
        name = match.group(1)
        if name == "docx":
            return f"`{_PROJECT_SUBSTITUTION}`"
        if name in _STDLIB_NAMES:
            return f"`{name}`"
        if path := self._resolve(name):
            return f"[{name}][{path}]"
        return f"`{name}`"

    def _role(self, match: re.Match[str]) -> str:
        role, target = match.group(1), match.group(2)
        abbreviated = target.startswith("~")
        target = target.lstrip("~")
        label = target.lstrip(".").rsplit(".", 1)[-1] if abbreviated else target.lstrip(".")

        if role == "ref":
            # -- enum pages were labelled by MS API name, which the enum docstrings carry --
            path = self._ms_api_names.get(target)
            return f"[{label}][{path}]" if path else f"`{label}`"
        if path := self._resolve(target):
            return f"[{label}][{path}]"
        return f"`{label}`"

    def _translate(self, text: str) -> str:
        """Rewrite the RST constructs in `text`, leaving fenced code untouched."""
        text = _fence_literal_blocks(text)
        out: list[str] = []
        fenced = False
        for line in text.split("\n"):
            if _FENCE_RE.match(line):
                fenced = not fenced
                out.append(line)
                continue
            if fenced:
                out.append(line)
                continue
            line = _ROLE_RE.sub(self._role, line)
            out.append(_SUBSTITUTION_RE.sub(self._substitution, line))
        return "\n".join(out)

    def _rewrite(self, obj: Object) -> None:
        if obj.docstring and obj.docstring.value:
            obj.docstring.value = self._translate(obj.docstring.value)
        for member in obj.members.values():
            if not member.is_alias:
                self._rewrite(member)

    # -- hook --------------------------------------------------------------------------

    def on_package(self, *, pkg: Module, loader: GriffeLoader, **kwargs: Any) -> None:
        """Index and rewrite the package once its object tree is complete."""
        del loader, kwargs
        self._index(pkg)
        self._rewrite(pkg)
