# Bookmarks

A bookmark names a span of content so something else can point at it — a cross-reference,
a hyperlink, or a `PAGEREF` field asking which page it fell on.

In OOXML a bookmark is not a container. It is a pair of markers, `w:bookmarkStart` and
`w:bookmarkEnd`, that can sit anywhere relative to the content between them; that is why
a bookmark can span paragraphs, or half a table.

## Creating one

Over a whole paragraph:

```python
from docx import Document

document = Document()
heading = document.add_heading("Introduction", level=1)
heading.add_bookmark("intro")
```

Over a narrower range, from one run through another:

```python
paragraph = document.add_paragraph()
first = paragraph.add_run("the ")
middle = paragraph.add_run("important")
last = paragraph.add_run(" bit")

first.mark_bookmark_range(last, "highlight")
```

Passing the same run as both ends bookmarks just that run.

!!! warning

    A bookmark name must be unique in the document. Word treats a duplicate as a second,
    separate bookmark, and the two then compete for anything that refers to the name.

## Reading them

[`Document.bookmarks`][docx.document.Document.bookmarks] supports `len()`, iteration,
indexed access and lookup by name:

```python
len(document.bookmarks)
document.bookmarks[0].name
document.bookmarks["intro"].text
document.bookmarks.get("missing")  # -> None rather than KeyError
```

Each [`Bookmark`][docx.bookmark.Bookmark] carries:

- [`name`][docx.bookmark.Bookmark.name] and [`id`][docx.bookmark.Bookmark.id]
- [`text`][docx.bookmark.Bookmark.text] — the text it spans
- [`is_closed`][docx.bookmark.Bookmark.is_closed] — whether the matching
  `w:bookmarkEnd` is present. A start without an end is malformed but does occur in the
  wild
- [`is_hidden`][docx.bookmark.Bookmark.is_hidden] — whether Word maintains it for itself

### Word's own bookmarks

Word keeps bookmarks of its own: `_GoBack` for the last edit position, and a `_Toc…`
anchor for every heading a table of contents points at. These are hidden by default,
because they are noise in almost every case:

```python
for bookmark in document.bookmarks.iter_all(include_hidden=True):
    print(bookmark.name)
```

## Deleting

```python
document.bookmarks["intro"].delete()
```

This removes both markers and leaves the content between them alone.

## Pointing at a bookmark

Bookmarks exist to be referred to. From a field, so Word renders the target's text or
page number ([Fields](fields.md)):

```python
from docx import fields

paragraph = document.add_paragraph("See ")
paragraph.add_field(fields.cross_reference("intro"))
paragraph.add_run(" on page ")
paragraph.add_field(fields.page_reference("intro"))
```

Or from a hyperlink, which jumps there when clicked:

```python
paragraph = document.add_paragraph()
paragraph.add_hyperlink("back to the introduction", fragment="intro")
```

[`add_hyperlink()`][docx.text.paragraph.Paragraph.add_hyperlink] takes `address` for an
external URL and `fragment` for a location inside the document; give both to link to an
anchor in another document.
