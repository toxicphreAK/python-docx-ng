# Finding, replacing and deleting text

## Why `run.text = ...` so often does nothing

Word splits a paragraph into runs for reasons that have nothing to do with formatting:
spell-check state, language tagging, revision marks, or simply where the cursor happened
to be. A placeholder you can see as one word is routinely three runs:

```xml
<w:r><w:t>{{na</w:t></w:r>
<w:r><w:t>me</w:t></w:r>
<w:r><w:t>}}</w:t></w:r>
```

No single run contains `{{name}}`, so no assignment to `run.text` replaces it. This is
the single most common surprise in working with `.docx` files.

## Replacing text

[`replace_text()`][docx.text.paragraph.Paragraph.replace_text] matches against the
paragraph's text as a whole, so it succeeds whether or not Word split it up. It returns
how many replacements it made:

```python
from docx import Document

document = Document()
paragraph = document.add_paragraph("Dear {{name}}, welcome.")

paragraph.replace_text("{{name}}", "Ada")  # -> 1
paragraph.text                             # -> 'Dear Ada, welcome.'
```

It is available on paragraphs, on anything that contains block items, and on the
document as a whole.

### Across a whole document

[`Document.replace_text()`][docx.document.Document.replace_text] makes what gets searched
explicit, because "replace it everywhere" means different things to different callers and
getting it wrong stays invisible until someone reads the header:

```python
document.replace_text("{{name}}", "Ada")                        # body only
document.replace_text("{{name}}", "Ada", headers_footers=True)  # and those
document.replace_text("{{name}}", "Ada", footnotes=True)
document.replace_text("{{name}}", "Ada", tables=False)          # skip tables
```

Tables are searched by default; headers, footers and footnotes are not.

### Regular expressions

```python
import re

document.replace_text(r"\{\{(\w+)\}\}", r"<\1>", regex=True)
document.replace_text("draft", "final", regex=True, flags=re.IGNORECASE)
```

`count` limits how many replacements are made; the default of `-1` means all of them.

### What happens to formatting

The replacement takes the formatting of the run holding the first replaced character.

When a match spans runs formatted differently, the rest of the matched text is removed
along with its formatting — but the runs themselves stay. A hyperlink, bookmark, comment
range or field that the match only partly covers therefore keeps its structure rather
than being torn in half.

## Formatting part of a paragraph

The same run-splitting problem applies when you want to embolden a phrase that is not
already its own run. [`isolate_run()`][docx.text.paragraph.Paragraph.isolate_run] splits
the runs as needed so a character range becomes exactly one run, which can then be
formatted on its own:

```python
paragraph = document.add_paragraph("the important part matters")
paragraph.isolate_run(4, 13).bold = True
```

Offsets are measured against [`Paragraph.text`][docx.text.paragraph.Paragraph.text], so a
tab counts as one character and a line break as one newline. Where the range already
lines up with a run, nothing is split.

This is what [`replace_text()`][docx.text.paragraph.Paragraph.replace_text] is built on.

## Deleting content

`.delete()` removes an object from its parent, and exists on paragraphs, runs, tables,
rows and columns:

```python
paragraph.delete()
run.delete()
table.delete()
table.rows[1].delete()
table.columns[0].delete()
```

Deletion is not just an unlink. A relationship — a hyperlink target, an image — referenced
only from the deleted content is dropped with it, and a range marker left unmatched (half
a bookmark, half a comment range) is removed rather than left dangling to corrupt the
file.

Two cases follow Word rather than the literal XML:

- Deleting a **row** does not drop a vertically merged cell whose span began in it. The
  row below inherits the merge, so it continues to render.
- Deleting a **column** narrows a cell that spans it and others by one, rather than
  removing the cell, so the rest of the span survives.

!!! warning

    Deleting while iterating invalidates the collection you are iterating. Take a list
    first:

    ```python
    for paragraph in list(document.paragraphs):
        if not paragraph.text.strip():
            paragraph.delete()
    ```
