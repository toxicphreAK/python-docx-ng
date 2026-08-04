# Tracked changes

A document edited with Word's "Track Changes" on carries its history: insertions in
`w:ins` elements, deletions in `w:del`, and the same treatment for formatting changes,
paragraph marks and table rows. This library reads that history and can accept or reject
any part of it.

## What `Paragraph.text` means here

Text in a document with tracked changes has two well-defined readings, and this library
gives you both:

```python
paragraph.text           # the document as it now reads
paragraph.original_text  # the document as it read before the changes
```

[`text`][docx.text.paragraph.Paragraph.text] includes insertions and excludes deletions —
what you would get by accepting everything.
[`original_text`][docx.text.paragraph.Paragraph.original_text] does the reverse. For a
paragraph with no revisions the two are identical.

Neither is "the text with markup shown". Word displays deletions struck through
*alongside* insertions, which is a rendering rather than a string.

!!! note

    This changed in 2.0.0. The 0.9.x line dropped both insertions and deletions, so the
    result matched neither reading. [`Paragraph.runs`][docx.text.paragraph.Paragraph.runs]
    likewise now includes runs inside a `w:ins`.

## Reading the revisions

[`Document.revisions`][docx.document.Document.revisions] returns every revision in the
body, in document order:

```python
from docx import Document

document = Document("reviewed.docx")

for revision in document.revisions:
    print(revision.type, revision.author, revision.date, repr(revision.text))
```

```text
WD_REVISION_TYPE.INSERTION Ada Lovelace 2026-03-14 09:12:00 'and therefore '
WD_REVISION_TYPE.DELETION Charles Babbage 2026-03-14 10:03:00 'possibly '
```

Each [`Revision`][docx.revisions.Revision] carries:

- [`type`][docx.revisions.Revision.type] — a
  [`WD_REVISION_TYPE`][docx.enum.revision.WD_REVISION_TYPE] member
- [`author`][docx.revisions.Revision.author] and
  [`date`][docx.revisions.Revision.date] — `date` is `None` when Word recorded none
- [`text`][docx.revisions.Revision.text] — the text inserted or deleted
- [`is_paragraph_mark`][docx.revisions.Revision.is_paragraph_mark] — a paragraph split or
  merge rather than a text change
- [`is_row`][docx.revisions.Revision.is_row] — a table row inserted or deleted

[`Paragraph.revisions`][docx.text.paragraph.Paragraph.revisions] narrows this to one
paragraph.

### Who changed what

```python
authors = {revision.author for revision in document.revisions}
```

## Accepting and rejecting

Individually:

```python
for revision in document.revisions:
    if revision.author == "Ada Lovelace":
        revision.accept()
    else:
        revision.reject()
```

Accepting an insertion keeps the text and drops the marker; rejecting it removes the
text. For a deletion it is the other way round.

Wholesale, on the document or on one paragraph — each returns how many revisions it
handled:

```python
document.accept_all_revisions()   # -> 12
document.reject_all_revisions()

paragraph.accept_all_revisions()
paragraph.reject_all_revisions()
```

!!! warning

    Accepting or rejecting mutates the tree, so a list of revisions taken beforehand
    goes stale. Re-read [`Document.revisions`][docx.document.Document.revisions] rather
    than holding onto revisions across a change, and iterate over a snapshot — as in the
    loop above, which reads the list once — rather than over a live traversal.

## Turning tracking on

[`Settings.track_revisions`][docx.settings.Settings.track_revisions] is the document-wide
flag Word's "Track Changes" button sets:

```python
document.settings.track_revisions = True
document.save("for-review.docx")
```

This asks Word to record changes made from now on. It does not cause edits made through
this library to be recorded as revisions — those are written directly, as if tracking
were off.
