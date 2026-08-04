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
