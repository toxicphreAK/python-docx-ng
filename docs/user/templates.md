# Templates, styles across documents, and embedded files

## Word templates

A `.dotx` or `.dotm` template holds exactly the same markup as a document. It differs
only in the content type of its main part, which is what tells Word to start a *new*
document from it rather than open it for editing.

Templates open like anything else:

```python
from docx import Document

document = Document("house-style.dotx")
document.is_template  # -> True
```

[`save()`][docx.document.Document.save] keeps whichever it already is, so a template
opened and saved is still a template. `as_template` overrides that, which is how you
generate a document from a template — or turn a document into one:

```python
document.save("report.docx", as_template=False)   # a document from a template
document.save("house-style.dotx", as_template=True)  # a template from a document
```

Macro-enabled input stays macro-enabled either way, so a `.dotm` saved with
`as_template=False` is a `.docm`.

!!! note

    This sets the content type. It does not choose the file extension for you — pass a
    name whose extension matches, or Word will complain about the mismatch.

## Copying a style between documents

Applying a style by name fails with `KeyError: no style with name 'Callout'` whenever the
target document's style part lacks it, which is routine when content is assembled from
several sources. [`copy_style_from()`][docx.styles.styles.Styles.copy_style_from] brings
one across:

```python
template = Document("house-style.dotx")
report = Document()

callout = template.styles["Callout"]
report.styles.copy_style_from(callout)
report.add_paragraph("Mind the gap", style="Callout")
```

**The dependency closure is the point.** A style is not a self-contained object:
`w:basedOn` names the style it inherits from, `w:next` the style for the following
paragraph, and `w:link` the paired character or paragraph style. Copying one `w:style`
element by hand gives a style whose `basedOn` target is missing, which then renders as if
it inherited from Normal. Those are followed and copied too, unless you say otherwise:

```python
report.styles.copy_style_from(callout, include_dependencies=False)
```

A list style references `numbering.xml`, so `include_numbering` (on by default) copies
the `w:num` and `w:abstractNum` behind it and rewrites the reference to the new id.

### Name collisions

```python
report.styles.copy_style_from(callout, name="House Callout")
report.styles.copy_style_from(callout, on_collision="overwrite")
```

`on_collision` decides what happens when the target already has a style of that name:

| Value | Behaviour |
| --- | --- |
| `"skip"` (default) | leave the existing style alone and return it |
| `"overwrite"` | replace its definition |
| `"rename"` | copy under a free name — "Callout 2", and so on |
| `"raise"` | raise `ValueError` |

!!! warning

    **Theme fonts are not carried over.** A style referencing `w:asciiTheme` resolves
    against *this* document's theme part, so a copied style can legitimately look
    different in its new home.

## Embedding another document

An `altChunk` embeds a whole file — HTML, RTF, another `.docx` — and lets Word import it
on open:

```python
document = Document()
document.add_alt_chunk(b"<h1>Report</h1><p>Generated.</p>", content_type="text/html")
```

`chunk` may be bytes, a path, or a file-like object open for binary read. Note that a
`str` is read as a **path**, not as content — pass content as bytes, as above.

`content_type` must be right, because Word picks its importer from it:

| Content type | Format |
| --- | --- |
| `text/html` | HTML |
| `text/plain` | plain text |
| `application/rtf` | RTF |
| `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | `.docx` |

```python
with open("appendix.docx", "rb") as f:
    document.add_alt_chunk(
        f,
        content_type=(
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document"
        ),
    )
```

!!! warning

    **Word performs the import when it opens the document, so the embedded content is
    not visible to this library.** Its paragraphs and tables do not appear in
    [`Document.paragraphs`][docx.document.Document.paragraphs],
    [`Document.tables`][docx.document.Document.tables] or
    [`iter_inner_content()`][docx.document.Document.iter_inner_content], and nothing here
    can style it. It is a handover to Word, not a merge.

    Readers other than Word may ignore `altChunk` entirely.

[`Document.alt_chunks`][docx.document.Document.alt_chunks] lists what has been embedded.
