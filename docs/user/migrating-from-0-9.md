# Migrating from 0.9.x

Version 2.0.0 restarts *python-docx-ng* from upstream python-docx v1.2.0.

The 0.9.x line had diverged from upstream v0.8.11 in 2021 and drifted for four years. Rather than merge four years of upstream change into that tree, 2.0.0 branches from upstream and re-applies the python-docx-ng features on top, one at a time. The benefit is a typed, tested core that tracks upstream; the cost is that several 0.9.x additions are gone, replaced by upstream implementations of the same features that are shaped differently.

**This is a breaking release.** Read this page before upgrading. Code that only used the parts of the API that upstream python-docx also has is very likely unaffected.

## Features upstream has since implemented

These existed in 0.9.x as fork additions. Upstream has since implemented the same features, and 2.0.0 uses upstream's version.

### Comments

0.9.x added comments to a paragraph. Upstream models them as a collection on the document, with the comment range marked on runs.

``` python
# -- 0.9.x --
paragraph.add_comment("Needs a citation.", author="RS", initials="rs")
paragraph.comments

# -- 2.0.0 --
comment = document.add_comment(paragraph.runs, "Needs a citation.", author="RS", initials="rs")
document.comments                       # -- the Comments collection --
document.comments.get(comment_id)
run.mark_comment_range(last_run, comment_id)   # -- for finer control --
```

The `docx.text.comment` module is gone; the objects live in `docx.comments`. A comment is now a block-item container, so it can hold several paragraphs and even tables, and `comment.text` joins its paragraphs with newlines.

See [comments](comments.md) for the full API.

### Hyperlinks

0.9.x added its own hyperlink handling. Upstream's [Hyperlink][docx.text.hyperlink.Hyperlink] reads links already in a document and exposes `.address`, `.fragment`, `.runs`, `.text` and `.contains_page_break`; [Paragraph.hyperlinks][docx.text.paragraph.Paragraph.hyperlinks] lists them, and `paragraph.text` includes hyperlink text, which it did not in 0.8.11.

[Paragraph.add_hyperlink][docx.text.paragraph.Paragraph.add_hyperlink] is still present — that is a python-docx-ng addition upstream has not adopted — but its signature has changed:

``` python
# -- 2.0.0 --
paragraph.add_hyperlink("python-docx-ng", address="https://example.com/")
paragraph.add_hyperlink("see above", fragment="my_bookmark")   # -- internal link --
```

It returns a [Hyperlink][docx.text.hyperlink.Hyperlink], not a run.

### Table cell access

This is the change most likely to affect existing code.

In 0.9.x, `Table._cells` built a row-major matrix of the layout grid, and `Table.cell()`, `Table.row_cells()` and `Table.column_cells()` indexed into it. Upstream returns a flat list, and — importantly — `_Row.cells` returns only the cells that are actually present.

Word allows a row to start late or end early, so rows of the same table can have different numbers of cells. Two new properties report the gap:

``` python
for row in table.rows:
    leading = row.grid_cols_before      # -- unpopulated grid columns before the first cell --
    trailing = row.grid_cols_after      # -- and after the last --
    for cell in row.cells:
        ...
```

If you were relying on every row having one cell per column, add `grid_cols_before` and `grid_cols_after` to your indexing, or use [Table.cell][docx.table.Table.cell], which addresses the layout grid directly and raises `IndexError` for a grid position the row does not occupy.

`Table.cell()` now locates its target without materializing the whole grid, so reading a table cell-by-cell costs time proportional to the number of cells rather than to its square. `Table.row_cells()` is deprecated in favour of `table.rows[i].cells`.

## Behaviour changes

### `Paragraph.text` with tracked changes

In 0.9.x — and in upstream — revision markup was not modelled at all. Runs inside a `w:ins` were skipped, so inserted text was missing, and deleted text was missing too because it lives in `w:delText` rather than `w:t`. The result was neither the original nor the final version of the document but a third thing matching no view Word offers, and it was wrong silently.

`Paragraph.text` is now the document **as it now reads** — every revision accepted:

``` python
paragraph.text            # -- insertions in, deletions out --
paragraph.original_text   # -- deletions in, insertions out --
```

`Paragraph.runs` follows the same reading, so a run inside a `w:ins` now appears in it and a run inside a `w:del` does not.

If you were relying on the old behaviour to strip insertions, use `original_text`. If you want the revision markup gone from the file altogether, call `document.accept_all_revisions()` or `document.reject_all_revisions()`. See [Document.revisions][docx.document.Document.revisions] for reading the individual changes.

### `Paragraph.text` with simple fields

The cached result of a `w:fldSimple` — the page number a `PAGE` field displays, the text a cross-reference resolves to — is now part of `Paragraph.text`. It was previously skipped, so such text went missing. This is displayed text and belongs there; a field *instruction* (`w:instrText`) is still never reported as text, because it is not.

### `Font.highlight_color`

In 0.9.x this fell back to the `w:shd` shading fill when no highlight was set, and accepted RGB values on assignment. Highlighting and shading are different things in Word, and conflating them meant you could not tell them apart. They are now separate:

``` python
font.highlight_color       # -- a WD_COLOR_INDEX member or None, never an RGB value --
font.shading_fill          # -- an RGBColor, the string "auto", or None --
```

`highlight_color` also distinguishes `WD_COLOR_INDEX.NO_HIGHLIGHT` — highlighting explicitly turned off, which Word writes as `w:highlight w:val="none"` — from `None`, which means no setting is present and the value is inherited.

### `ParagraphFormat.outline_level`

0.9.x returned `9` when no outline level was set. `None` and `9` are different things: `None` means the level is inherited from the style hierarchy, and `9` is Word's explicit "Body Text" level, which deliberately excludes the paragraph from the outline. 2.0.0 reports them distinctly, and assigning a value outside 0–9 raises `ValueError` rather than writing an invalid document.

## Removed without replacement

`Section.paragraphs`  
Use [Section.iter_inner_content][docx.section.Section.iter_inner_content], which generates the paragraphs and tables of a section in document order rather than paragraphs alone.

`Table.section`  
Removed. The 0.9.x implementation walked to the first following `w:sectPr`, which returns the wrong section for every table but those in the last section of a multi-section document. There is no correct one-line replacement; iterate [Document.sections][docx.document.Document.sections] and [Section.iter_inner_content][docx.section.Section.iter_inner_content] to find the section a table belongs to.

## Fork features, re-applied and reshaped

These are python-docx-ng features that upstream does not have. They are back on the 2.0.0 base, in some cases with a different API than 0.9.x had.

### Table and cell borders

0.9.x exposed borders as a sequence with `add_border()` and `remove_border()` methods, a `_Border.name` setter that returned a value Python discarded, and line styles as bare strings validated against a 200-entry tuple. 2.0.0 makes it a mapping keyed by edge:

``` python
# -- 0.9.x --
table.borders.add_border("top", "single", sz=8, color="FF0000")

# -- 2.0.0 --
from docx.enum.table import WD_LINE_STYLE
from docx.shared import Pt, RGBColor

table.borders["top"].line = WD_LINE_STYLE.SINGLE
table.borders["top"].size = Pt(1)
table.borders["top"].color = RGBColor(0xFF, 0x00, 0x00)
table.borders["top"].line = None        # -- remove the edge --
```

Edges are named for the XML: `top`, `start`, `left`, `bottom`, `end`, `right`, `insideH` and `insideV`, plus `tl2br` and `tr2bl` on a cell. Sizes are [Length][docx.shared.Length] values, so `Pt(1)` composes as it does everywhere else, rather than a raw count of eighths of a point.

### Footnotes

0.9.x had `paragraph.add_footnote(text)`, derived from bayoo-docx, and a `paragraph.footnotes` that returned a bool. The 2.0.0 implementation mirrors the shape upstream gave comments:

``` python
footnote = document.footnotes.add_footnote("See Smith (2019), p. 42.")
paragraph.add_run().add_footnote_reference(footnote)

len(document.footnotes)
document.footnotes.get(footnote.footnote_id)
```

Creating a footnote and referencing it are separate steps, because a footnote can be referenced from anywhere and one that is never referenced does not render. A footnote is a block-item container, so it can hold several paragraphs, tables and images.

Word keeps two structural footnotes at ids -1 and 0 for the separator rules. Those are in the part but never in the collection, so authored footnotes are numbered from 1.

See [footnotes](../api/docx/footnotes.md).

### Form fields

0.9.x exposed only element classes; there was no proxy API and no way to read or set a field value without dropping to the XML. 2.0.0 adds one:

``` python
values = {f.name: f.value for f in document.form_fields}

field = document.form_fields[0]
field.value = "Carol Chen"      # -- str, or bool for a check box --
field.items                     # -- the entries of a drop-down --
```

`.value` reads and writes in the form natural to the kind of field. See [FormField][docx.formfield.FormField].

### AltChunk

0.9.x had an `AltchunkPart` but no public API. 2.0.0 adds one:

``` python
document.add_alt_chunk(b"<html><body><p>Imported.</p></body></html>", "text/html")
document.alt_chunks
```

Word performs the import when it opens the document, so the embedded content stays invisible to this library until then.

## Still to come

Some 0.9.x features have not been re-applied yet. Check the [2.0.0 milestone](https://github.com/toxicphreAK/python-docx-ng/milestone/1) before assuming something is gone for good.
