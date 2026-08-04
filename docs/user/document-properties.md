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
