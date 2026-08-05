# Document properties

Word keeps three separate sets of properties, in three parts of the package. They are not
interchangeable, and which one you want depends on who wrote the value.

| | Part | Written by |
| --- | --- | --- |
| [Core](#core-properties) | `docProps/core.xml` | you, and Word's File → Info panel |
| [Extended](#extended-properties) | `docProps/app.xml` | Word, mostly statistics |
| [Custom](#custom-properties) | `docProps/custom.xml` | you, under any name you like |

## Core properties

The standard Dublin Core set — the fields Word shows under File → Info:

```python
from docx import Document

document = Document()
core = document.core_properties

core.title = "Quarterly report"
core.author = "Ada Lovelace"
core.subject = "Finance"
core.keywords = "quarterly, finance, 2026"
core.comments = "Draft for review"
core.category = "Report"
core.content_status = "Draft"
core.language = "en-GB"
```

The date fields take a `datetime`:

```python
import datetime as dt

core.created = dt.datetime(2026, 3, 14, 9, 0)
core.modified = dt.datetime.now()
```

Also available: `identifier`, `last_modified_by`, `last_printed`, `revision` (an `int`)
and `version`.

Unset string properties read as `""` rather than `None`, and unset dates as `None`. The
date properties accept only a `datetime` on assignment — assigning `None` to clear one
raises `ValueError`.

## Extended properties

`docProps/app.xml` is mostly Word's own bookkeeping — how many pages, words and
characters the document had when Word last saved it:

```python
extended = document.extended_properties

extended.pages
extended.words
extended.characters
extended.paragraphs
extended.lines
extended.total_time      # editing minutes
extended.application     # e.g. "Microsoft Office Word"
extended.app_version
```

!!! warning

    These statistics are whatever Word wrote when it last saved. This library does not
    recompute them, so a document you have edited here reports the old counts. Treat
    them as a record of Word's last visit, not as a live measure.

A few are yours to set, and Word displays them:

```python
extended.company = "Analytical Engines Ltd"
extended.manager = "Charles Babbage"
extended.hyperlink_base = "https://example.com/docs/"
```

`template` names the template the document was created from.

!!! note

    `CT_Properties` is an `xsd:all` type, so Word writes these children in an order that
    does not match the order the schema lists them in. That is expected, and nothing in
    the API depends on their order.

## Custom properties

`docProps/custom.xml` holds properties under any name you choose, which is what makes it
useful for carrying your own metadata through a document. It behaves as a `dict`:

```python
import datetime as dt

props = document.custom_properties

props["Matter number"] = 4242
props["Reviewed"] = True
props["Reviewed on"] = dt.datetime(2026, 3, 14)
props["Rate"] = 1.5
props["Client"] = "Analytical Engines Ltd"

props["Matter number"]      # -> 4242
"Client" in props           # -> True
len(props)
list(props)                 # -> the names
del props["Reviewed"]
```

A value may be a `str`, `int`, `float`, `bool` or `datetime`; those are the variant types
Word writes, and each reads back as the same Python type. Assigning anything else raises
`ValueError` rather than writing a file Word would refuse to open.

Names are unique and case-sensitive, and may contain spaces.

### Showing one in the document

A `DOCPROPERTY` field puts a custom property's value into the text, so it updates
wherever it appears when the property changes ([Fields](fields.md)):

```python
from docx import fields

paragraph = document.add_paragraph("Matter: ")
paragraph.add_field(fields.doc_property("Matter number"))
```

## The custom XML data store

A different thing from the properties above, and easy to confuse with them. The three
kinds of properties are flat named scalars — a string, a number, a date. The **custom XML
data store** holds arbitrary XML documents, each in a part of its own
(`customXml/item1.xml`, with an `itemProps1.xml` sidecar declaring its schemas).

This is where a document-generation pipeline keeps the structured data its content
controls are bound to. Word's data binding points a content control at an XPath into one
of these items, so the control's displayed text and the stored data stay the same thing.

```python
part = document.add_custom_xml_part(
    "<invoice xmlns='urn:example:invoice'>"
    "<number>2026-014</number><total>1450.00</total>"
    "</invoice>",
    schema_refs=("urn:example:invoice",),
)

part.item_id      # -> "{...}", the GUID Word identifies the item by
part.schema_refs  # -> ("urn:example:invoice",)
part.xml          # -> the XML as text
```

Reading them back:

```python
for part in document.custom_xml_parts:
    print(part.partname, part.item_id, part.schema_refs)
    print(part.xml)
```

[`Document.custom_xml_parts`][docx.document.Document.custom_xml_parts] is a tuple in
relationship order, empty for a document that has no data store.
[`add_custom_xml_part()`][docx.document.Document.add_custom_xml_part] accepts a `str` or
`bytes`, allocates the next free partname, and generates the `w:itemProps` sidecar with a
GUID of its own — Word requires the sidecar, and an item without one is a repair prompt.

`schema_refs` names the namespaces the item uses. It is optional and it is what Word's
XML mapping pane lists, so supplying it is what makes the item usable for data binding
through the UI.

!!! warning

    **The generated GUID is the one thing in this library's output that is not a function
    of its input.** Everything else about a saved document is deterministic — see
    [Reproducible output](documents.md#reproducible-output). If that matters to you, supply the `item_id`:

    ```python
    document.add_custom_xml_part(xml, item_id="{...}")
    ```

    It only has to be unique within the document.

!!! note

    A document created by this library carries **no** data store. The bundled template
    used to ship an empty bibliography item left over from its author's Word session,
    which meant `custom_xml_parts` reported a store the caller had never added. That is
    gone as of 2.1.0.
