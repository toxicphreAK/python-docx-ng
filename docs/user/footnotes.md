# Footnotes

A footnote lives in its own part, `word/footnotes.xml`, and the document body carries
only a reference to it. Creating one is therefore two steps: add the footnote, then
reference it from a run.

## Adding a footnote

```python
from docx import Document

document = Document()

paragraph = document.add_paragraph("The engine was never built")
footnote = document.footnotes.add_footnote("Babbage, 1837.")
paragraph.runs[-1].add_footnote_reference(footnote)
```

[`add_footnote_reference()`][docx.text.run.Run.add_footnote_reference] appends the
reference mark to the end of the run, so which run you call it on decides where the
superscript number appears.

A footnote can hold more than the one paragraph its text argument creates:

```python
footnote = document.footnotes.add_footnote("See also:")
footnote.add_paragraph("Menabrea, 1842.")
footnote.add_paragraph("Lovelace, Note G.", style="Quote")
```

## Reading them

[`Document.footnotes`][docx.document.Document.footnotes] supports `len()` and iteration,
and looks a footnote up by id:

```python
len(document.footnotes)

for footnote in document.footnotes:
    print(footnote.footnote_id, footnote.text)

document.footnotes.get(2)   # -> the Footnote, or None
```

!!! note

    Word reserves the first two ids for the separator and continuation separator — the
    little rules drawn above footnote text. Iterating skips those, so what you get is
    the footnotes a reader would count.

Numbering is Word's to compute, as with any field: `footnote_id` is an identifier, not
the number printed in the margin.

!!! note

    The API changed in 2.0.0. The 0.9.x line had `Paragraph.add_footnote()`; footnotes
    are now [`Document.footnotes`][docx.document.Document.footnotes] plus
    [`Run.add_footnote_reference()`][docx.text.run.Run.add_footnote_reference], which
    separates creating the note from placing the mark.

## Endnotes

Endnotes are the same shape, one part over: they live in `word/endnotes.xml` and collect
at the end of the document or section rather than at the foot of the page.

```python
paragraph = document.add_paragraph("The engine was never built")
endnote = document.endnotes.add_endnote("Babbage, 1837.")
paragraph.runs[-1].add_endnote_reference(endnote)
```

[`Document.endnotes`][docx.document.Document.endnotes] supports `len()`, iteration and
lookup by id, exactly as `footnotes` does, and an
[`Endnote`][docx.footnotes.Endnote] has `.text`, `.endnote_id` and `.add_paragraph()`:

```python
for endnote in document.endnotes:
    print(endnote.endnote_id, endnote.text)

document.endnotes.get(1)   # -> the Endnote, or None
```

`word/endnotes.xml` is created on demand the first time you add one, as the footnotes part
is, so a document that has no endnotes carries no endnotes part.

!!! note

    As in the footnotes part, ids `-1` and `0` are taken by the separator and continuation
    separator — the rules drawn above endnote text — so the first real endnote is id `1`.
    Iterating skips the separators, so what you get is the endnotes a reader would count.

A document can carry both kinds at once — they are independent sequences, numbered
separately, and Word renders footnotes in Arabic numerals and endnotes in lower-case Roman
by default.

[`replace_text()`][docx.document.Document.replace_text] reaches endnotes under
`footnotes=True`, which covers both note stories:

```python
document.replace_text("Babbage", "Charles Babbage", footnotes=True)
```
