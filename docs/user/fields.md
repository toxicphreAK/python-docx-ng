# Fields and tables of contents

A field is how Word represents anything it works out for itself: page numbers, a table
of contents, cross-references, captions that renumber, dates, and references to document
properties. Every one of those is the same feature with a different instruction string.

!!! warning

    **This library cannot compute a field result, and no API can change that.** A table
    of contents added here is empty, a `PAGE` field has no number, and a
    cross-reference shows nothing, because all three depend on how Word lays the
    document out. Fields are written asking Word to refresh them when it opens the
    file — see [Getting Word to fill them in](#getting-word-to-fill-them-in).

## Adding a field

[`Paragraph.add_field()`][docx.text.paragraph.Paragraph.add_field] takes a field code.
The builders in [`docx.fields`][docx.fields] write the ones people usually want, so you
rarely need to remember the switch syntax:

```python
from docx import Document, fields

document = Document()

paragraph = document.add_paragraph("Page ")
paragraph.add_field(fields.page_number())
paragraph.add_run(" of ")
paragraph.add_field(fields.page_count())
```

The builders return the instruction string, not the field, so they compose with anything
that takes a field code:

| Builder | Field |
| --- | --- |
| [`page_number()`][docx.fields.page_number] | `PAGE` — the current page |
| [`page_count()`][docx.fields.page_count] | `NUMPAGES` — pages in the document |
| [`table_of_contents()`][docx.fields.table_of_contents] | `TOC` |
| [`cross_reference()`][docx.fields.cross_reference] | `REF` — text of a bookmark |
| [`page_reference()`][docx.fields.page_reference] | `PAGEREF` — page a bookmark is on |
| [`sequence()`][docx.fields.sequence] | `SEQ` — caption and figure numbering |
| [`date()`][docx.fields.date] | `DATE` |
| [`doc_property()`][docx.fields.doc_property] | `DOCPROPERTY` |
| [`styleref()`][docx.fields.styleref] | `STYLEREF` — nearest text in a style |

An instruction Word understands but no builder covers can be passed directly:

```python
paragraph.add_field(r'INCLUDEPICTURE "logo.png" \d')
```

## A table of contents

```python
from docx import Document, fields

document = Document()

document.add_paragraph("Contents", style="Heading 1")
toc = document.add_paragraph()
toc.add_field(fields.table_of_contents(levels=(1, 3)))

document.add_page_break()
document.add_heading("Introduction", level=1)
document.add_paragraph("...")

document.settings.update_fields_on_open = True
document.save("with-toc.docx")
```

`levels` is the heading range to include. The document opens showing "Update this
document?" and the contents appear once Word rebuilds them.

## Cross-references

A cross-reference points at a bookmark, so bookmark the target first:

```python
from docx import Document, fields

document = Document()

intro = document.add_heading("Introduction", level=1)
intro.add_bookmark("intro")

body = document.add_paragraph("See ")
body.add_field(fields.cross_reference("intro"))
body.add_run(" on page ")
body.add_field(fields.page_reference("intro"))
```

[`cross_reference()`][docx.fields.cross_reference] writes the bookmark's *text* and
[`page_reference()`][docx.fields.page_reference] the *page number* it falls on. See
[Bookmarks](bookmarks.md) for the ways to create one.

## Captions that renumber

`SEQ` is the counter behind Word's captions. Each name is its own sequence:

```python
caption = document.add_paragraph("Figure ", style="Caption")
caption.add_field(fields.sequence("Figure"))
caption.add_run(": the architecture")
```

Pass `restart_at_heading_level` to start the numbering over at each chapter, which gives
the "Figure 3-2" style:

```python
caption.add_field(fields.sequence("Figure", restart_at_heading_level=1))
```

## Reading the fields in a document

[`Document.fields`][docx.document.Document.fields] returns every field in the body, and
[`Paragraph.fields`][docx.text.paragraph.Paragraph.fields] the fields of one paragraph:

```python
for field in document.fields:
    print(field.type, field.instruction, repr(field.result_text))
```

- [`Field.instruction`][docx.fields.Field.instruction] — the field code, switches and all
- [`Field.type`][docx.fields.Field.type] — the first word of it, e.g. `"PAGE"`
- [`Field.result_text`][docx.fields.Field.result_text] — the cached result Word last
  computed, which is what a reader saw
- [`Field.is_simple`][docx.fields.Field.is_simple] — whether Word stored it as a
  self-contained `w:fldSimple` or spread it across runs

A field's cached result counts towards
[`Paragraph.text`][docx.text.paragraph.Paragraph.text], so the page number a reader saw
is part of the text you read back.

Complex fields nest — a `TOC` result is full of `PAGEREF` fields — and each inner field
is a field in its own right.

## Getting Word to fill them in

Two things ask Word to compute results, and they are not the same:

```python
document.settings.update_fields_on_open = True
```

[`Settings.update_fields_on_open`][docx.settings.Settings.update_fields_on_open] sets a
document-wide flag; Word prompts on open and refreshes every field. This is what a
generated table of contents needs.

Individual fields are written with `w:dirty` set, which asks Word to refresh that field
alone. Pass `dirty=False` to
[`add_field()`][docx.text.paragraph.Paragraph.add_field] to suppress it.

To keep the field from showing as blank before the first refresh, supply cached result
text of your own. That requires `simple=True`, because only a `w:fldSimple` stores its
result as plain content — a complex field's result is whatever sits between its
`separate` and `end` field characters, which Word writes when it computes it:

```python
paragraph.add_field(fields.page_number(), simple=True, result="1")
```
