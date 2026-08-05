# Command line

`python -m docx` answers the questions people ask about a `.docx` one at a time: what
styles it defines, which of them are actually used, and why the file is 900 KB.

It is deliberately thin. Every subcommand maps onto one public library operation and
holds no logic of its own, so there is nothing reachable through the command line that is
not reachable from Python. There is no new dependency — it is `argparse` only.

```console
$ python -m docx --help
usage: python -m docx [-h] {info,styles,cleanup} ...

Inspect and clean up Word documents.

positional arguments:
  {info,styles,cleanup}
    info                list the parts of a document with their sizes
    styles              inspect a document's styles
    cleanup             remove unused styles, numbering and media
```

## `info` — what is in the package

The fastest answer to "why is this file like this": the part inventory, biggest first.

```console
$ python -m docx info report.docx
    350527  word/styles.xml
      7642  word/theme/theme1.xml
      5513  word/numbering.xml
      2811  word/fontTable.xml
      2535  word/settings.xml
      1586  word/document.xml
    ...
    375746  TOTAL uncompressed (20199 on disk)
```

This is how the 438 KB `word/stylesWithEffects.xml` that used to ship in the bundled
template turned up. `--json` emits the same data for a script to consume.

## `styles` — what it defines and what it uses

```console
$ python -m docx styles report report.docx
168 styles defined  (30 character, 1 list, 37 paragraph, 100 table)
10 in use, 158 unused
131 latent style exceptions
```

"In use" is a reachability closure over every story part, not a scan of the body — see
[Style usage and cleanup](cleanup.md) for what that means and why the distinction
matters.

`styles list` prints the names, optionally filtered:

```console
$ python -m docx styles list report.docx --used
Normal
Default Paragraph Font
Normal Table
No List
List Bullet
...
```

`--used` and `--unused` are mutually exclusive; asking for both would match nothing.

`styles extract` writes the styles out to a document of their own, which is how you turn
a document you like the look of into a template:

```console
$ python -m docx styles extract house-style.docx -o house.dotx --as-template
$ python -m docx styles extract report.docx -o headings.docx --names "Heading 1,Heading 2"
```

Named styles come with their `basedOn` / `next` / `link` closure, so the extract is a
document that opens without repair.

## `cleanup` — remove what nothing points at

```console
$ python -m docx cleanup report.docx -o small.docx
removed 158 styles, 3 numbering definitions, 3 abstract numbering definitions, 0 media parts and 0 latent style exceptions
wrote small.docx
```

Two rules this command keeps:

**It never writes to its input.** `-o` is required. Someone will point it at their only
copy.

**`--check` is a CI gate.** It reports what *would* be removed and exits non-zero if
anything would be, so a pipeline can fail a build that has grown dead weight:

```console
$ python -m docx cleanup report.docx --check
would have removed 158 styles, 3 numbering definitions, ...
$ echo $?
1
```

| Flag | Effect |
| --- | --- |
| `--keep NAMES` | comma-separated style names to preserve, along with their dependencies |
| `--no-styles` | leave the style definitions alone |
| `--no-numbering` | leave the numbering definitions alone |
| `--no-media` | leave orphaned image parts alone |
| `--latent-styles` | *also* drop the latent-style exceptions — off by default, because this changes what a user sees in Word's style gallery |
| `--json` | emit the full list of what went, not just the counts |

## Exit codes

These end up in scripts, so they are part of the contract:

| Code | Meaning |
| --- | --- |
| `0` | success |
| `1` | `cleanup --check` found something to remove |
| `2` | the document could not be opened, or an argument named something that is not there |

A document that cannot be opened is reported as a message on stderr, never as a
traceback — including the password-protected case, which is a different thing from a
corrupt file:

```console
$ python -m docx info nope.docx
error: cannot open document: Package not found at 'nope.docx'
```
