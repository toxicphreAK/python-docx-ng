# python-docx-ng

*python-docx-ng* is a Python library for reading, creating, and updating Microsoft Word
2007+ (.docx) files.

It is a downstream superset of [python-docx](https://github.com/python-openxml/python-docx)
by [scanny](https://github.com/scanny): everything upstream does, plus features upstream
has not adopted. As of 2.0.0 this project tracks upstream v1.2.0 directly, so it builds on
upstream's typed and tested core rather than a 2021 snapshot of it.

Repo: <https://github.com/toxicphreAK/python-docx-ng>
Releases: <https://github.com/toxicphreAK/python-docx-ng/releases>
PyPI: <https://pypi.org/project/python-docx-ng/>

## Installation

```commandline
pip install python-docx-ng
```

> Note: the importable package is `docx`, not `python_docx_ng` — use `import docx`.
> `python-docx-ng` and `python-docx` therefore cannot be installed side by side.

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

The [python-docx documentation](https://python-docx.readthedocs.org/en/latest/) covers the
shared core. Additions specific to this project are documented in
[docs](https://github.com/toxicphreAK/python-docx-ng/tree/main/docs).

## What this adds over python-docx

*Being ported onto the v1.2.0 base — see [HISTORY.rst](HISTORY.rst) for current status
and the [2.0.0 milestone](https://github.com/toxicphreAK/python-docx-ng/milestone/1) for
what is still to come.*

+ Footnotes — `Document.footnotes` and `Run.add_footnote_reference()`
+ Legacy form fields — read and fill text inputs, check boxes and drop-downs
+ Table and cell borders — `Table.borders["top"].line = WD_LINE_STYLE.SINGLE`
+ AltChunk — embed HTML, RTF or another `.docx` for Word to import on open
+ Custom and extended document properties (`docProps/custom.xml`, `docProps/app.xml`)
+ Bookmarks, `Paragraph.add_hyperlink()`, and a deletion API
+ `.docm` (macro-enabled) and `.dotx`/`.dotm` (template) support
+ SVG, EMF, WMF and WebP image support
+ Outline level — drives the outline shown in navigation panes and PDF bookmarks
+ Font scaling, theme typefaces, East Asian and complex-script typefaces
+ Paragraph and run shading
+ Multi-column section layout, and row `dont_split`
+ Reproducible documents — the same input produces byte-identical output
+ Custom namespaces in `xpath()` calls
+ Tolerates oversized attribute values the default `lxml` parser rejects

## Upgrading from 0.9.x

2.0.0 rebases onto upstream v1.2.0 and contains **breaking changes**. Several 0.9.x
additions were dropped in favour of upstream implementations of the same features, which
are better tested and differently shaped — notably comments, hyperlinks, and table cell
access. Read the
[migration guide](https://github.com/toxicphreAK/python-docx-ng/blob/main/docs/user/migrating-from-0-9.rst)
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

## License

MIT — see [LICENSE](LICENSE). Originally developed by Steve Canny as *python-docx*.
