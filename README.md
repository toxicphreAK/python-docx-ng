# python-docx-ng

[![PyPI](https://img.shields.io/pypi/v/python-docx-ng)](https://pypi.org/project/python-docx-ng/)
[![Downloads](https://img.shields.io/pypi/dm/python-docx-ng)](https://pypistats.org/packages/python-docx-ng)

*python-docx-ng* is a Python library for reading, creating, and updating Microsoft Word
2007+ (.docx) files.

It is a downstream superset of [python-docx](https://github.com/python-openxml/python-docx)
by [scanny](https://github.com/scanny): everything upstream does, plus features upstream
has not adopted. As of 2.0.0 this project tracks upstream v1.2.0 directly, so it builds on
upstream's typed and tested core rather than a 2021 snapshot of it.

- Documentation: <https://toxicphreak.github.io/python-docx-ng/>
- Repo: <https://github.com/toxicphreAK/python-docx-ng>
- Releases: <https://github.com/toxicphreAK/python-docx-ng/releases>
- PyPI: <https://pypi.org/project/python-docx-ng/>

## Installation

```commandline
pip install python-docx-ng
```

> Note: the importable package is `docx`, not `python_docx_ng` — use `import docx`.
> `python-docx-ng` and `python-docx` therefore cannot be installed side by side.

Python 3.9 through 3.14. The only runtime dependencies are `lxml` and
`typing_extensions`; `lxml` is floored at 6.1.0, the first release fixing
CVE-2026-41066.

## Example

```python
>>> from docx import Document

>>> document = Document()
>>> document.add_paragraph("It was a dark and stormy night.")
<docx.text.paragraph.Paragraph object at 0x10f19e760>
>>> document.save("dark-and-stormy.docx")

>>> document = Document("dark-and-stormy.docx")
>>> document.paragraphs[0].text
'It was a dark and stormy night.'
```

## Documentation

**<https://toxicphreak.github.io/python-docx-ng/>**

- [User guide](https://toxicphreak.github.io/python-docx-ng/user/quickstart/) — documents,
  text, tables, sections, styles
- [How-to pages](https://toxicphreak.github.io/python-docx-ng/user/search-replace/) — the
  features listed below, each with worked examples
- [Command line](https://toxicphreak.github.io/python-docx-ng/user/cli/) —
  `python -m docx info`, `styles report`, `cleanup`
- [API reference](https://toxicphreak.github.io/python-docx-ng/api/docx/) — every module,
  generated from the source
- [Migrating from 0.9.x](https://toxicphreak.github.io/python-docx-ng/user/migrating-from-0-9/)

The [upstream python-docx documentation](https://python-docx.readthedocs.org/en/latest/)
also covers the shared core.

### For language models

The site publishes [llms.txt](https://toxicphreak.github.io/python-docx-ng/llms.txt) and
[llms-full.txt](https://toxicphreak.github.io/python-docx-ng/llms-full.txt). Any tool that
reads the format can consume them — for example
[mcpdoc](https://github.com/langchain-ai/mcpdoc), which serves them to an editor over MCP:

```commandline
uvx --from mcpdoc mcpdoc --urls python-docx-ng:https://toxicphreak.github.io/python-docx-ng/llms.txt
```

## What this adds over python-docx

Everything upstream v1.2.0 does, plus:

**Editing and review**

+ Tracked changes — read revisions, and accept or reject them individually or in bulk
+ Comments, footnotes, endnotes, and cross-run search and replace that survives Word's run splitting
+ A deletion API — `.delete()` on paragraphs, runs, tables, rows and columns
+ `copy_to()` on paragraphs, runs, rows and tables — with relationships, ids, styles and numbering repaired

**Content people ask for**

+ Fields and a table of contents — `Paragraph.add_field()`, with builders for PAGE, TOC, REF, SEQ and the rest
+ Captions — `Document.add_caption()` writes the label, the SEQ field and the `_Ref` bookmark Word's cross-reference dialogue needs
+ List numbering, readable *and* writable — define a list from scratch, apply it, restart it
+ Bookmarks and `Paragraph.add_hyperlink()`
+ Watermarks, text and image, written into the header where Word expects them
+ Floating (anchored) images with text wrapping, alongside inline ones
+ Legacy form fields — read and fill text inputs, check boxes and drop-downs
+ AltChunk — embed HTML, RTF or another `.docx` for Word to import on open
+ Embedded OLE objects — discover and extract a document's attachments, or add one

**Formatting**

+ Borders on tables, cells, paragraphs and pages — `Table.borders["top"].line = WD_LINE_STYLE.SINGLE`
+ Table width (including percentages), indent, cell margins, and the `tblLook` style flags
+ Row properties — `repeat_as_header`, `hidden`, alignment, cell spacing, `dont_split`
+ Paragraph and run shading, including the pattern and its colour
+ Document defaults (`w:docDefaults`) — the bottom of the inheritance chain, and often the only place the base font is set
+ The paragraph mark's own formatting, which is what an empty paragraph is formatted with
+ Right-to-left and vertical text on paragraphs, sections and cells
+ Character-unit indents and line-unit spacing
+ Multi-column section layout
+ Outline level — drives the outline shown in navigation panes and PDF bookmarks
+ Font scaling, theme typefaces, East Asian and complex-script typefaces

**Styles**

+ Which styles are actually used — a reachability closure over every story part, not a scan of the body
+ `Document.cleanup()` — remove the styles, numbering and media nothing points at; 20 KB down to 9 KB
+ Bulk style transfer — import a house `.dotx`'s styles, or extract a document's into one
+ Copying a style between documents, with its `basedOn`/`next`/`link` closure and numbering

**Files and formats**

+ `.docm` (macro-enabled) and `.dotx`/`.dotm` (template) support, plus reading, transplanting and stripping the VBA project itself
+ SVG, EMF, WMF and WebP image support
+ Image extraction — `InlineShape.image`, `FloatingShape.image`, `Document.images`
+ EXIF orientation honoured, so a portrait photo off a phone is not inserted sideways
+ Custom and extended document properties (`docProps/custom.xml`, `docProps/app.xml`), and the custom XML data store content controls bind to
+ The theme part — the fonts and colours a `minorHAnsi` token resolves through
+ OMML equations, readable through `Document.math`
+ Reproducible documents — the same input produces byte-identical output
+ Accepts `pathlib.Path` anywhere a path is taken

**Accessibility**

+ Alt text on pictures, inline shapes and tables

**Tooling**

+ `python -m docx` — `info`, `styles report/list/extract` and `cleanup`, with a `--check` mode that works as a CI gate

**Robustness**

+ Tolerates oversized attribute values the default `lxml` parser rejects
+ Corrupt, truncated and password-protected files raise something that says which
+ Custom namespaces in `xpath()` calls

Some things are deliberately not here yet — reading ISO Strict documents, charts and
SmartArt, and decompressing VBA module source among them. See the
[issue tracker](https://github.com/toxicphreAK/python-docx-ng/issues) for what is
planned, and [HISTORY.rst](https://github.com/toxicphreAK/python-docx-ng/blob/main/HISTORY.rst)
for the full changelog.

## Upgrading from 0.9.x

2.0.0 rebases onto upstream v1.2.0 and contains **breaking changes**. Several 0.9.x
additions were dropped in favour of upstream implementations of the same features, which
are better tested and differently shaped — notably comments, hyperlinks, and table cell
access. Read the
[migration guide](https://toxicphreak.github.io/python-docx-ng/user/migrating-from-0-9/)
before upgrading.

## Development

Requires [uv](https://docs.astral.sh/uv/).

```commandline
uv sync              # create the environment
uv run pytest        # unit tests
make accept          # acceptance tests (behave)
uv run pyright       # type check
uv run ruff check .  # lint
```

## Contributors

- [@lyydsheep](https://github.com/lyydsheep) — `os.PathLike` support throughout document open and save ([#130](https://github.com/toxicphreAK/python-docx-ng/pull/130))
- [@builtbyhuy](https://github.com/builtbyhuy) — XPath variable binding, so style names containing quotes are reachable ([#131](https://github.com/toxicphreAK/python-docx-ng/pull/131))
- [@BortnikMaxim](https://github.com/BortnikMaxim) — table alternative text, `Table.title` and `Table.description` ([#132](https://github.com/toxicphreAK/python-docx-ng/pull/132))

The full list, by release, is in [CONTRIBUTORS.md](CONTRIBUTORS.md). Patches are
welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE). Originally developed by Steve Canny as *python-docx*.
