# Templates, styles across documents, embedded files and macros

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

## Importing a template's styles

`copy_style_from()` moves one style. Two operations built on it move whole sets, which is
what a house template usually calls for:

```python
report = Document()

result = report.styles.import_from("house-style.dotx")
# -> {"Callout": "added", "Heading 1": "skipped", ...}
```

[`Styles.import_from()`][docx.styles.styles.Styles.import_from] accepts a path, a stream or
an already-open `Document` — a `.dotx` opens without special handling, since a template
holds the same main part as a document. It returns a report keyed by UI name, saying what
it did with each: `"added"`, `"replaced"` or `"skipped"`.

```python
report.styles.import_from("house-style.dotx", ["Callout", "Sidebar"])
report.styles.import_from("house-style.dotx", overwrite=True)
report.styles.import_from("house-style.dotx", include_latent=True)
```

Without `overwrite`, a name the destination already defines is skipped and reported as
such — the existing definition wins, which is what "import these styles into my document"
almost always means. `include_latent` also brings the source's `w:latentStyles`
exceptions across, and is off by default because that changes which of Word's built-ins
appear in the destination's style gallery.

The other direction pulls styles *out* of a document into a template of their own:

```python
added = report.styles.extract("house.dotx", as_template=True)
added = report.styles.extract("headings.docx", ["Heading 1", "Heading 2"])

xml = report.styles.extract_xml(["Heading 1"])   # -> just the styles.xml bytes
```

[`Styles.extract()`][docx.styles.styles.Styles.extract] writes an otherwise empty document
carrying the named styles and their dependency closure, and returns the names it added.
Naming nothing extracts every style the document defines. The extract starts from a
template whose own unused styles have been pruned, so what comes out is the styles you
named plus the handful the closure keeps alive — `Normal`, `Default Paragraph Font` and the
other defaults — rather than those plus the 168 the bundled template ships.

`as_template=True` writes a `.dotx` — the same content with the template content type, so
Word treats it as a template rather than a document.

## Embedded OLE objects

An OLE object is a whole file carried *inside* the document and shown as an icon or a
preview image that opens the original application on double-click. This is a different
thing from an `altChunk`: an `altChunk` is dissolved into the document when Word opens the
file, whereas an embedded object stays a distinct file forever.

The read side matters on its own. A document with attachments embedded in it previously
gave no way to discover that they exist, let alone get them out:

```python
from pathlib import Path

for obj in document.embedded_objects:
    print(obj.prog_id, obj.content_type, obj.filename)
    if obj.blob is not None:
        Path(obj.filename or "attachment").write_bytes(obj.blob)
```

[`Document.embedded_objects`][docx.document.Document.embedded_objects] covers the body and
[`Run.embedded_objects`][docx.text.run.Run.embedded_objects] one run. Each
[`EmbeddedObject`][docx.object.EmbeddedObject] offers:

| | |
| --- | --- |
| `prog_id` | the application Word launches, e.g. `"Excel.Sheet.12"` |
| `blob` | the bytes of the embedded file, or `None` |
| `content_type` | the content type of the embedded part |
| `filename` | the basename of the part it landed in, e.g. `"oleObject1.bin"` |
| `is_linked` | `True` when the object *links* to an external file instead of embedding it, in which case there are no bytes in the package |
| `shows_icon` | `True` when Word shows an icon rather than a preview |
| `image` | the icon or preview image Word displays |
| `embedded_part` | the package part itself |

!!! note

    OOXML does not record the original file name of an embedded object. `filename` is the
    name of the part it was stored in, which is what a caller extracting it has to work
    with.

Writing one takes an icon, and the icon is required:

```python
run = document.add_paragraph().add_run()
run.add_embedded_object(
    "budget.xlsx",
    icon="excel-icon.png",
    prog_id="Excel.Sheet.12",
)
```

Word cannot render the embedded file itself, so without an image there is nothing to draw
where the object sits. `prog_id` defaults to `"Package"`, the generic value Word uses for a
file it has no better name for — an object whose `ProgID` names no installed application is
one Word displays but cannot open, so pass the right one when you know it. `width` and
`height` default to the icon's own size.

The visual is VML, not DrawingML, because that is what Word writes for an OLE object.

## Macros

A macro-enabled document keeps its VBA project as a single opaque blob,
`word/vbaProject.bin`:

```python
document = Document("macros.docm")

document.has_macros      # -> True
len(document.vba_project) # -> the project bytes
```

Reading, transplanting and stripping one are all expressible:

```python
# -- move a project into a generated document --
generated = Document()
generated.vba_project = Document("macros.docm").vba_project
generated.save("generated.docm")

# -- strip the macros out of a document you received --
received = Document("received.docm")
del received.vba_project          # -- or: received.vba_project = None
received.save("safe.docx")

received.remove_vba_project()     # -> how many were removed, 0 or 1
```

Assigning or removing a project **switches the main part's content type with it**, which is
the part that is easy to get wrong by hand: Word ignores macros in a document that does not
claim to be macro-enabled, and warns about macros in a document that claims to be
macro-enabled but is not. A template switches to the macro-enabled *template* type rather
than the document one.

!!! note

    The blob is not parsed. The project is an OLE compound file with compressed module
    streams inside it; reading the source of a macro is a separate matter and is not
    supported.

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
