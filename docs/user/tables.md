# Working with Tables

Word provides sophisticated capabilities to create tables. As usual, this power comes with additional conceptual complexity.

This complexity becomes most apparent when *reading* tables, in particular from documents drawn from the wild where there is limited or no prior knowledge as to what the tables might contain or how they might be structured.

These are some of the important concepts you'll need to understand.

## Concept: Simple (uniform) tables

    +---+---+---+
    | a | b | c |
    +---+---+---+
    | d | e | f |
    +---+---+---+
    | g | h | i |
    +---+---+---+

The basic concept of a table is intuitive enough. You have *rows* and *columns*, and at each (row, column) position is a different *cell*. It can be described as a *grid* or a *matrix*. Let's call this concept a *uniform table*. A relational database table and a Pandas dataframe are both examples of a uniform table.

The following invariants apply to uniform tables:

- Each row has the same number of cells, one for each column.
- Each column has the same number of cells, one for each row.

## Complication 1: Merged Cells

    +---+---+---+   +---+---+---+
    |   a   | b |   |   | b | c |
    +---+---+---+   + a +---+---+
    | c | d | e |   |   | d | e |
    +---+---+---+   +---+---+---+
    | f | g | h |   | f | g | h |
    +---+---+---+   +---+---+---+

While very suitable for data processing, a uniform table lacks expressive power desireable for tables intended for a human reader.

Perhaps the most important characteristic a uniform table lacks is *merged cells*. It is very common to want to group multiple cells into one, for example to form a column-group heading or provide the same value for a sequence of cells rather than repeat it for each cell. These make a rendered table more *readable* by reducing the cognitive load on the human reader and make certain relationships explicit that might easily be missed otherwise.

Unfortunately, accommodating merged cells breaks both the invariants of a uniform table:

- Each row can have a different number of cells.
- Each column can have a different number of cells.

This challenges reading table contents programatically. One might naturally want to read the table into a uniform matrix data structure like a 3 x 3 "2D array" (list of lists perhaps), but this is not directly possible when the table is not known to be uniform.

## Concept: The layout grid

    + - + - + - +
    |   |   |   |
    + - + - + - +
    |   |   |   |
    + - + - + - +
    |   |   |   |
    + - + - + - +

In Word, each table has a *layout grid*.

- The layout grid is *uniform*. There is a layout position for every (layout-row, layout-column) pair.
- The layout grid itself is not visible. However it is represented and referenced by certain elements and attributes within the table XML
- Each table cell is located at a layout-grid position; i.e. the top-left corner of each cell is the top-left corner of a layout-grid cell.
- Each table cell occupies one or more whole layout-grid cells. A merged cell will occupy multiple layout-grid cells. No table cell can occupy a partial layout-grid cell.
- Another way of saying this is that every vertical boundary (left and right) of a cell aligns with a layout-grid vertical boundary, likewise for horizontal boundaries. But not all layout-grid boundaries need be occupied by a cell boundary of the table.

## Complication 2: Omitted Cells

    +---+---+   +---+---+---+
    | a | b |   | a | b | c |
    +---+---+---+   +---+---+---+
    | c | d |           | d |
    +---+---+       +---+---+---+
    | e |       | e | f | g |
    +---+       +---+---+---+

Word is unusual in that it allows cells to be omitted from the beginning or end (but not the middle) of a row. A typical practical example is a table with both a row of column headings and a column of row headings, but no top-left cell (position 0, 0), such as this XOR truth table.

    +---+---+
    | T | F |
    +---+---+---+
    | T | F | T |
    +---+---+---+
    | F | T | F |
    +---+---+---+

In *python-docx*, omitted cells in a [_Row][docx.table._Row] object are represented by the `.grid_cols_before` and `.grid_cols_after` properties. In the example above, for the first row, `.grid_cols_before` would equal `1` and `.grid_cols_after` would equal `0`.

Note that omitted cells are not just "empty" cells. They represent layout-grid positions that are unoccupied by a cell and they cannot be represented by a [_Cell][docx.table._Cell] object. This distinction becomes important when trying to produce a uniform representation (e.g. a 2D array) for an arbitrary Word table.

## Concept: *python-docx* approximates uniform tables by default

To accurately represent an arbitrary table would require a complex graph data structure. Navigating this data structure would be at least as complex as navigating the *python-docx* object graph for a table. When extracting content from a collection of arbitrary Word files, such as for indexing the document, it is common to choose a simpler data structure and *approximate* the table in that structure.

Reflecting on how a relational table or dataframe represents tabular information, a straightforward approximation would simply repeat merged-cell values for each layout-grid cell occupied by the merged cell:

    +---+---+---+      +---+---+---+
    |   a   | b |  ->  | a | a | b |
    +---+---+---+      +---+---+---+
    |   | d | e |  ->  | c | d | e |
    + c +---+---+      +---+---+---+
    |   | f | g |  ->  | c | f | g |
    +---+---+---+      +---+---+---+

This is what `_Row.cells` does by default. Conceptually:

```pycon
>>> [tuple(c.text for c in r.cells) for r in table.rows]
[
  (a, a, b),
  (c, d, e),
  (c, f, g),
]
```
Note this only produces a uniform "matrix" of cells when there are no omitted cells. Dealing with omitted cells requires a more sophisticated approach when maintaining column integrity is required:

    #     +---+---+
    #     | a | b |
    # +---+---+---+
    # | c | d |
    # +---+---+
    #     | e |
    #     +---+

    def iter_row_cell_texts(row: _Row) -> Iterator[str]:
        for _ in range(row.grid_cols_before):
            yield ""
        for c in row.cells:
            yield c.text
        for _ in range(row.grid_cols_after):
            yield ""

```pycon
>>> [tuple(iter_row_cell_texts(r)) for r in table.rows]
[
  ("",  "a", "b"),
  ("c", "d", ""),
  ("",  "e", ""),
]
```
## Complication 3: Tables are Recursive

Further complicating table processing is their recursive nature. In Word, as in HTML, a table cell can itself include one or more tables.

These can be detected using `_Cell.tables` or `_Cell.iter_inner_content()`. The latter preserves the document order of the table with respect to paragraphs also in the cell.

## Borders

[`Table.borders`][docx.table.Table.borders] and [`_Cell.borders`][docx.table._Cell.borders]
are mappings keyed by edge name:

```python
from docx.enum.table import WD_LINE_STYLE
from docx.shared import Pt, RGBColor

table = document.add_table(rows=2, cols=2)

table.borders["top"].line = WD_LINE_STYLE.SINGLE
table.borders["top"].size = Pt(1)
table.borders["top"].color = RGBColor(0xFF, 0x00, 0x00)
```

A table admits `left`, `right`, `top`, `bottom`, and `insideH` and `insideV` for the
horizontal and vertical borders *between* its cells. A cell admits the same four edges
plus the two diagonals, `tl2br` and `tr2bl`:

```python
cell = table.cell(0, 0)
cell.borders["bottom"].line = WD_LINE_STYLE.DOUBLE
```

A border set on a cell takes precedence over the table border at the same edge.

Each edge exposes `line` (a [`WD_LINE_STYLE`][docx.enum.table.WD_LINE_STYLE] member),
`size` (a [`Length`][docx.shared.Length]), `color` (an
[`RGBColor`][docx.shared.RGBColor], not a hex string) and `space`. Setting `line` to
`WD_LINE_STYLE.NONE` removes the border.

## Table width, indent and cell margins

[`Table.width`][docx.table.Table.width] is the table's *preferred* width — Word treats it
as a request and may narrow the table to fit its container. It takes either a
[`Length`][docx.shared.Length] or a percentage:

```python
from docx.shared import Inches, Pct

table.width = Inches(4)
table.width = Pct(50)      # -> half the container width
table.width = None         # -> auto-fit, which is the default
```

[`Pct`][docx.shared.Pct] is deliberately *not* a `Length`. Every `Length` unit is
absolute and reduces to EMU; a percentage does not, and cannot be converted to one
without knowing what it is a percentage of. Reading `width` back gives whichever of the
two the table actually carries.

[`Table.indent`][docx.table.Table.indent] moves the whole table in from the margin, and
[`Table.cell_margins`][docx.table.Table.cell_margins] sets the default padding inside
every cell:

```python
table.indent = Inches(0.5)

table.cell_margins.left = Inches(0.1)
table.cell_margins.top = Inches(0.05)
table.cell_margins.clear()          # -> back to inherited
```

The mapping admits `top`, `bottom`, `left`, `right` and the direction-relative `start`
and `end`. These are the table-wide defaults; a cell's own `w:tcMar` overrides them where
it has one.

## Which parts of a table style apply

A table style can define different formatting for the first row, the last row, the first
and last columns, and alternating bands. Which of those *apply* is not part of the style —
it is a set of flags on the table, the ones Word shows as the "Table Style Options"
checkboxes:

```python
table.look.first_row = True          # -- header row formatting on
table.look.horizontal_banding = True # -- alternating row shading on
table.look.last_column = False
```

[`Table.look`][docx.table.Table.look] exposes `first_row`, `last_row`, `first_column`,
`last_column`, `horizontal_banding` and `vertical_banding`. Each is `True` or `False` —
never `None`, because `w:tblLook` has a defined default for each flag rather than an
inherited one.

!!! note

    `w:tblLook` carries both modern per-flag attributes and a legacy `@w:val` bitmask,
    and older versions of Word read the bitmask. Setting a flag rewrites both, as Word
    does, so the table looks the same wherever it is opened.

## Row properties

```python
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Inches

row = table.rows[0]

row.repeat_as_header = True          # -- "Repeat Header Rows"
row.hidden = False
row.alignment = WD_TABLE_ALIGNMENT.CENTER
row.cell_spacing = Inches(0.02)
row.width_before = Inches(0.5)
row.width_after = Inches(0.5)
```

[`repeat_as_header`][docx.table._Row.repeat_as_header] is the useful one: it is what makes
a header row reappear at the top of every page a long table spans. All of these are
tri-state where the XML is — `None` means the value is inherited — and
[`_Row.height`][docx.table._Row.height], `height_rule` and
[`_Row.dont_split`][docx.table._Row.dont_split] round out `w:trPr`.

`width_before` and `width_after` are the widths of the grid positions a row leaves
unpopulated, the companions to the `grid_cols_before` and `grid_cols_after` counts
described above.

## Text direction in a cell

[`_Cell.text_direction`][docx.table._Cell.text_direction] rotates the text in a cell,
which is how a narrow column gets a readable heading:

```python
from docx.enum.text import WD_TEXT_DIRECTION

table.cell(0, 1).text_direction = WD_TEXT_DIRECTION.BT_LR   # -- bottom-to-top
```

See [Right-to-left and vertical text](text.md#right-to-left-and-vertical-text) for the
full set of [`WD_TEXT_DIRECTION`][docx.enum.text.WD_TEXT_DIRECTION] values.

## Alternative text

A table carries the same two alt-text values Word's "Alt Text" pane writes for a
picture, and they matter for the same reason — an accessibility check on a generated
document flags a table without them:

```python
table = document.add_table(rows=2, cols=2)

table.title = "Quarterly revenue"
table.description = "Revenue by region for Q1 through Q4 2026, in thousands of euro."
```

Both are read/write on [`Table`][docx.table.Table] and both are `None` when unset;
assigning `None` removes them. They are stored as `w:tblCaption` and `w:tblDescription`
and are never rendered — this is metadata read by assistive technology, not a visible
caption above or below the table.

They can also be given when the table is created, which saves the round trip and matches
the way [`add_picture()`][docx.text.run.Run.add_picture] takes them:

```python
table = document.add_table(
    rows=2,
    cols=2,
    style="Light Grid Accent 1",
    title="Quarterly revenue",
    description="Revenue by region for Q1 through Q4 2026, in thousands of euro.",
)
```

Both are keyword-only, both default to `None`, and omitting them writes nothing.
[`_Cell.add_table()`][docx.table._Cell.add_table] and
[`BlockItemContainer.add_table()`][docx.blkcntnr.BlockItemContainer.add_table] take them
too.

## Captions

[`_Cell.add_caption()`][docx.table._Cell.add_caption] puts a self-renumbering caption
inside a cell. For a caption above or below a table, use
[`Document.add_caption()`][docx.document.Document.add_caption] — see
[Captions](fields.md#captions).
