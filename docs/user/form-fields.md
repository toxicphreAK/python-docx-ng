# Form fields and content controls

Word has two mechanisms for "a place in the document where someone fills something in",
from two different eras. Both are read here; which one a document uses depends on which
Word feature built it.

- **Legacy form fields** (`w:fldChar` with `w:ffData`) — the text input, check box and
  drop-down from the old Forms toolbar. Values are read *and written*.
- **Content controls** (`w:sdt`, "structured document tags") — the modern replacement,
  and also what a mail-merge or template tool typically inserts. Read-only here.

## Legacy form fields

[`Document.form_fields`][docx.document.Document.form_fields] returns every one in the
body, and [`Paragraph.form_fields`][docx.text.paragraph.Paragraph.form_fields] those of a
single paragraph:

```python
from docx import Document

document = Document("form.docx")

for field in document.form_fields:
    print(field.name, field.type, field.value)
```

```text
Surname WD_FORM_FIELD_TYPE.TEXT 'Lovelace'
Agreed WD_FORM_FIELD_TYPE.CHECK_BOX True
Department WD_FORM_FIELD_TYPE.DROP_DOWN 'Engineering'
```

[`FormField.value`][docx.formfield.FormField.value] reads and writes:

```python
field.value = "Babbage"     # a text input
field.value = True          # a check box
field.value = "Finance"     # a drop-down, by entry text
```

What [`value`][docx.formfield.FormField.value] means follows the field type:

| Type | Value |
| --- | --- |
| `TEXT` | the result text Word last rendered |
| `CHECK_BOX` | a `bool` |
| `DROP_DOWN` | the selected entry, `""` when nothing is selected |

!!! warning

    Word renders an empty text field as filler — five spaces or similar — and that
    filler is what `value` returns, because it is what the document actually contains.
    Test against [`default`][docx.formfield.FormField.default] rather than against `""`
    when you need to know whether a field was filled in.

The other properties describe how Word presents the field:

```python
field.name          # the bookmark name Word gives it
field.default
field.enabled
field.help_text
field.status_text
field.max_length    # text inputs
field.text_type     # WD_TEXT_FORM_FIELD_TYPE: REGULAR_TEXT, NUMBER_TEXT, DATE_TEXT, ...
field.items         # drop-down entries
field.calc_on_exit
```

## Content controls

A `w:sdt` wraps content rather than standing in for it, which has one consequence worth
knowing: **text inside a content control is ordinary document text**. Before 2.0.0 it was
invisible to the API — a document built from a template could read back as empty.

[`Document.content_controls`][docx.document.Document.content_controls] and
[`Paragraph.content_controls`][docx.text.paragraph.Paragraph.content_controls] give you
the controls themselves:

```python
for control in document.content_controls:
    print(control.tag, control.alias, repr(control.text))
```

- [`tag`][docx.sdt.ContentControl.tag] — the machine-readable name, which is what a
  template tool keys on
- [`alias`][docx.sdt.ContentControl.alias] — the title Word shows the user
- [`type`][docx.sdt.ContentControl.type] — rich text, plain text, date picker, and so on
- [`text`][docx.sdt.ContentControl.text] — everything inside, paragraphs separated by
  newlines, as for a table cell
- [`showing_placeholder`][docx.sdt.ContentControl.showing_placeholder] — whether what you
  are reading is the grey prompt text rather than a real value
- [`is_block_level`][docx.sdt.ContentControl.is_block_level] — whether it wraps whole
  paragraphs and tables, or sits inline within a paragraph

Reach the content through
[`runs`][docx.sdt.ContentControl.runs],
[`paragraphs`][docx.sdt.ContentControl.paragraphs],
[`tables`][docx.sdt.ContentControl.tables] or
[`iter_inner_content()`][docx.sdt.ContentControl.iter_inner_content]:

```python
control = document.content_controls[0]

for run in control.runs:
    run.bold = True
```

To change the text in a control, edit those runs, or use
[`replace_text()`][docx.document.Document.replace_text], which reaches inside content
controls like any other text. See [Finding and replacing text](search-replace.md).
