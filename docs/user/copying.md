# Copying content

`copy_to()` duplicates a paragraph, a run, a table row or a whole table — into the same
document or a different one.

```python
paragraph.copy_to(document)
row.copy_to(table)
table.copy_to(other_document)
run.copy_to(paragraph)
```

## Why not `copy.deepcopy()`

Duplicating content is the operation most often written by hand against this library, and
the hand-written version works for plain text and quietly breaks for anything
interesting. `copy_to()` is a deep copy plus a repair for each of these:

- **A picture's `r:embed`** names a relationship id belonging to the *source* part, so a
  copied image is either the wrong image or a dangling reference.
- **A hyperlink's `r:id`** has the same problem, and points at an external target that
  may not exist in the destination package.
- **`wp:docPr/@id`** must be unique document-wide, and a deep copy duplicates it.
- **A bookmark name** is document-wide, and a duplicate is not a copy of a bookmark: Word
  treats it as a second bookmark of the same name, and anything referring to that name
  resolves to whichever it finds first.
- **Across documents**, a `w:pStyle` names a style that may not be there and a `w:numPr`
  names a `numId` that certainly means something else.

Relating the same image into the destination reuses the sha1 deduplication, so copying a
picture into a document that already has it does not add a second copy of the bytes.

## Where the copy goes

Appended to the end of the container by default; `before` and `after` place it:

```python
paragraph.copy_to(document)                              # -> at the end of the body
paragraph.copy_to(document, before=document.paragraphs[0])
paragraph.copy_to(cell)                                  # -> into a table cell
row.copy_to(table, after=table.rows[0])
```

Appending to a body that ends in a `w:sectPr` inserts before it, since the section
properties have to stay last. Passing both `before` and `after` raises `ValueError`.

Each returns a proxy for the copy, so a repeated row is one line:

```python
template_row = table.rows[0]
for record in records:
    new_row = template_row.copy_to(table)
    new_row.cells[0].text = record.name
```

## Copying into another document

A cross-document copy brings what the content refers to with it. `missing_style` decides
what happens to a style the destination does not define:

| Value | Behaviour |
| --- | --- |
| `"copy"` (default) | copy the style across with its `basedOn` / `next` / `link` closure |
| `"drop"` | remove the style reference; the content falls back to the destination's default |
| `"raise"` | raise `ValueError` |

```python
paragraph.copy_to(other_document, missing_style="drop")
```

A style reference the *source* cannot resolve either is left alone — it is already broken
there, and inventing a target would be worse than carrying the break over.

Numbering comes across too, and this is the part that is easy to get wrong by hand. A
`w:numId` means something else in the destination, so leaving it alone numbers the copied
paragraph according to whichever list happens to hold that id — a silent wrong answer
rather than a visible failure. The definition is copied and the copy repointed at it, and
the source's `w:nsid` is dropped so the destination's list gallery does not show two
definitions as the same list.

## Bookmarks are dropped, not renamed

```python
paragraph.add_bookmark("Target")
copy = paragraph.copy_to(document)

[b.name for b in document.bookmarks]   # -> ["Target"], not two of them
```

This is the one place `copy_to()` deliberately loses something. Renaming would leave a
bookmark nothing points at; keeping the name would leave two competing for every
reference to it. Dropping is the only outcome that is not silently wrong — use
[`Paragraph.add_bookmark()`][docx.text.paragraph.Paragraph.add_bookmark] on the copy to
bookmark it afresh.
