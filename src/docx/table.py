"""The |Table| object and related proxy classes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator, cast, overload

from typing_extensions import TypeAlias

from docx.blkcntnr import BlockItemContainer
from docx.borders import _Borders  # pyright: ignore[reportPrivateUsage]
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml.deletion import delete_element
from docx.oxml.table import CT_TblBorders, CT_TblGridCol, CT_TcBorders
from docx.shared import Inches, Parented, Pct, StoryChild, lazyproperty

if TYPE_CHECKING:
    import docx.types as t
    from docx.enum.table import (
        WD_ROW_HEIGHT_RULE,
        WD_TABLE_ALIGNMENT,
        WD_TABLE_DIRECTION,
    )
    from docx.enum.text import WD_TEXT_DIRECTION
    from docx.oxml.table import (
        CT_Row,
        CT_Tbl,
        CT_TblPr,
        CT_Tc,
        _CT_BordersBase,  # pyright: ignore[reportPrivateUsage]
    )
    from docx.shared import Length
    from docx.styles.style import (
        ParagraphStyle,
        _TableStyle,  # pyright: ignore[reportPrivateUsage]
    )

TableParent: TypeAlias = "Table | _Columns | _Rows"


class _TableBorders(_Borders):
    """The border edges of a table, `table.borders`."""

    def __init__(self, tbl: CT_Tbl):
        # -- the edges come from the element class rather than being repeated here, so
        # -- the mapping cannot drift from the schema sequence the element declares --
        super().__init__(CT_TblBorders.edges)
        self._tbl = tbl

    def clear(self) -> None:
        self._tbl.tblPr._remove_tblBorders()  # pyright: ignore[reportPrivateUsage]

    @property
    def _element(self) -> _CT_BordersBase | None:
        return self._tbl.tblPr.tblBorders

    def _get_or_add_element(self) -> _CT_BordersBase:
        return self._tbl.tblPr.get_or_add_tblBorders()


class _CellBorders(_Borders):
    """The border edges of a table cell, `cell.borders`."""

    def __init__(self, tc: CT_Tc):
        super().__init__(CT_TcBorders.edges)
        self._tc = tc

    def clear(self) -> None:
        tcPr = self._tc.tcPr
        if tcPr is not None:
            tcPr._remove_tcBorders()  # pyright: ignore[reportPrivateUsage]

    @property
    def _element(self) -> _CT_BordersBase | None:
        tcPr = self._tc.tcPr
        return None if tcPr is None else tcPr.tcBorders

    def _get_or_add_element(self) -> _CT_BordersBase:
        return self._tc.get_or_add_tcPr().get_or_add_tcBorders()


class _TableLook:
    """Which parts of the table style apply to a table, `table.look`.

    `w:tblLook` is what tells Word whether the first row is a header row, whether the
    first or last column is emphasised, and whether row or column banding is on. Without
    it a styled table looks nothing like the style preview in Word.

    Each flag is tri-state: |None| means the attribute is absent and Word applies its own
    default (off for every flag). The two banding flags are stored inverted in the XML,
    as `w:noHBand` and `w:noVBand`; that inversion lives here so the oxml layer stays
    faithful to the attribute names.

    Word writes the six named attributes *and* the equivalent legacy bitmask in
    `@w:val`, and keeps them in step. Setting any flag through this proxy rewrites
    `@w:val` to match, because some older consumers read only the bitmask.
    """

    def __init__(self, tbl: CT_Tbl):
        self._tbl = tbl

    @property
    def first_row(self) -> bool | None:
        """|True| when the table style's first-row (header) formatting applies."""
        return self._get("firstRow")

    @first_row.setter
    def first_row(self, value: bool | None) -> None:
        self._set("firstRow", value)

    @property
    def last_row(self) -> bool | None:
        """|True| when the table style's last-row (total) formatting applies."""
        return self._get("lastRow")

    @last_row.setter
    def last_row(self, value: bool | None) -> None:
        self._set("lastRow", value)

    @property
    def first_column(self) -> bool | None:
        """|True| when the table style's first-column formatting applies."""
        return self._get("firstColumn")

    @first_column.setter
    def first_column(self, value: bool | None) -> None:
        self._set("firstColumn", value)

    @property
    def last_column(self) -> bool | None:
        """|True| when the table style's last-column formatting applies."""
        return self._get("lastColumn")

    @last_column.setter
    def last_column(self, value: bool | None) -> None:
        self._set("lastColumn", value)

    @property
    def horizontal_banding(self) -> bool | None:
        """|True| when the table style's row banding applies.

        Stored inverted, as `w:noHBand`.
        """
        value = self._get("noHBand")
        return None if value is None else not value

    @horizontal_banding.setter
    def horizontal_banding(self, value: bool | None) -> None:
        self._set("noHBand", None if value is None else not value)

    @property
    def vertical_banding(self) -> bool | None:
        """|True| when the table style's column banding applies.

        Stored inverted, as `w:noVBand`.
        """
        value = self._get("noVBand")
        return None if value is None else not value

    @vertical_banding.setter
    def vertical_banding(self, value: bool | None) -> None:
        self._set("noVBand", None if value is None else not value)

    def _get(self, attr_name: str) -> bool | None:
        tblLook = self._tbl.tblPr.tblLook
        return None if tblLook is None else cast("bool | None", getattr(tblLook, attr_name))

    def _set(self, attr_name: str, value: bool | None) -> None:
        tblPr = self._tbl.tblPr
        if value is None and tblPr.tblLook is None:
            return
        tblLook = tblPr.get_or_add_tblLook()
        setattr(tblLook, attr_name, value)
        tblLook.update_val()


class _TableCellMargins:
    """The default cell margins of a table, `table.cell_margins`.

    These are the padding Word applies inside every cell of the table that does not
    override them. An edge reads |None| when the table sets no value for it, in which
    case the table style's value applies.

    The `start` and `end` edges are the logical (writing-direction) synonyms of `left`
    and `right`. Word writes `left` and `right`; both are exposed because documents from
    other producers use the newer pair.
    """

    def __init__(self, tbl: CT_Tbl):
        self._tbl = tbl

    @property
    def top(self) -> Length | None:
        return self._get("top")

    @top.setter
    def top(self, value: Length | None) -> None:
        self._set("top", value)

    @property
    def bottom(self) -> Length | None:
        return self._get("bottom")

    @bottom.setter
    def bottom(self, value: Length | None) -> None:
        self._set("bottom", value)

    @property
    def left(self) -> Length | None:
        return self._get("left")

    @left.setter
    def left(self, value: Length | None) -> None:
        self._set("left", value)

    @property
    def right(self) -> Length | None:
        return self._get("right")

    @right.setter
    def right(self, value: Length | None) -> None:
        self._set("right", value)

    @property
    def start(self) -> Length | None:
        return self._get("start")

    @start.setter
    def start(self, value: Length | None) -> None:
        self._set("start", value)

    @property
    def end(self) -> Length | None:
        return self._get("end")

    @end.setter
    def end(self, value: Length | None) -> None:
        self._set("end", value)

    def clear(self) -> None:
        """Remove the `w:tblCellMar` element, restoring the table style's margins."""
        self._tbl.tblPr._remove_tblCellMar()  # pyright: ignore[reportPrivateUsage]

    def _get(self, edge: str) -> Length | None:
        tblCellMar = self._tbl.tblPr.tblCellMar
        return None if tblCellMar is None else tblCellMar.get_margin(edge)

    def _set(self, edge: str, value: Length | None) -> None:
        tblPr = self._tbl.tblPr
        if value is None and tblPr.tblCellMar is None:
            return
        tblPr.get_or_add_tblCellMar().set_margin(edge, value)


class Table(StoryChild):
    """Proxy class for a WordprocessingML ``<w:tbl>`` element."""

    def __init__(self, tbl: CT_Tbl, parent: t.ProvidesStoryPart):
        super(Table, self).__init__(parent)
        self._element = tbl
        self._tbl = tbl

    def add_column(self, width: Length):
        """Return a |_Column| object of `width`, newly added rightmost to the table."""
        tblGrid = self._tbl.tblGrid
        gridCol = tblGrid.add_gridCol()
        gridCol.w = width
        for tr in self._tbl.tr_lst:
            tc = tr.add_tc()
            tc.width = width
        return _Column(gridCol, self)

    def add_row(self):
        """Return a |_Row| instance, newly added bottom-most to the table."""
        tbl = self._tbl
        tr = tbl.add_tr()
        for gridCol in tbl.tblGrid.gridCol_lst:
            tc = tr.add_tc()
            if gridCol.w is not None:
                tc.width = gridCol.w
        return _Row(tr, self)

    @property
    def alignment(self) -> WD_TABLE_ALIGNMENT | None:
        """Read/write.

        A member of :ref:`WdRowAlignment` or None, specifying the positioning of this
        table between the page margins. |None| if no setting is specified, causing the
        effective value to be inherited from the style hierarchy.
        """
        return self._tblPr.alignment

    @alignment.setter
    def alignment(self, value: WD_TABLE_ALIGNMENT | None):
        self._tblPr.alignment = value

    @property
    def autofit(self) -> bool:
        """|True| if column widths can be automatically adjusted to improve the fit of
        cell contents.

        |False| if table layout is fixed. Column widths are adjusted in either case if
        total column width exceeds page width. Read/write boolean.
        """
        return self._tblPr.autofit

    @autofit.setter
    def autofit(self, value: bool):
        self._tblPr.autofit = value

    @lazyproperty
    def borders(self) -> _TableBorders:
        """The border edges of this table, as a mapping keyed by edge name::

            table.borders["top"].line = WD_LINE_STYLE.SINGLE
            table.borders["top"].size = Pt(1)

        These are the borders applied to the table as a whole; `insideH` and `insideV`
        set the horizontal and vertical borders between its cells. A border set on an
        individual cell through `cell.borders` takes precedence over the table border
        at that edge.
        """
        return _TableBorders(self._tbl)

    def cell(self, row_idx: int, col_idx: int) -> _Cell:
        """|_Cell| at `row_idx`, `col_idx` intersection.

        (0, 0) is the top, left-most cell. Negative indices count back from the end, as
        for a sequence.

        Raises |IndexError| if `row_idx` is out of range, or if the row does not occupy
        layout-grid column `col_idx` — Word allows a row to start late or end early.

        The target cell is located directly, without materializing the whole layout
        grid, so reading a table cell-by-cell costs time proportional to the number of
        cells rather than to its square.
        """
        tr = self._tbl.tr_at_idx(row_idx)

        if col_idx < 0:
            col_idx += self._column_count
        try:
            tc = tr.tc_covering_grid_offset(col_idx)
        except ValueError:
            raise IndexError("table column index [%d] is out of range" % col_idx) from None

        # -- a continuation cell of a vertical span holds no content; the cell the span
        # -- starts at does --
        return _Cell(tc.top_tc, self)

    def column_cells(self, column_idx: int) -> list[_Cell]:
        """Sequence of cells in the column at `column_idx` in this table.

        A row that does not occupy `column_idx`, because it starts late or ends early,
        contributes no cell.
        """

        def iter_column_cells() -> Iterator[_Cell]:
            for tr in self._tbl.tr_lst:
                try:
                    tc = tr.tc_covering_grid_offset(column_idx)
                except ValueError:
                    continue
                yield _Cell(tc.top_tc, self)

        return list(iter_column_cells())

    @property
    def description(self) -> str | None:
        """Alternative-text description for this table, or |None| if not set.

        Assigning |None| removes the description. This value is stored in the
        ``w:tblDescription`` table-property element and is used by assistive
        technologies.
        """
        tblDescription = self._tblPr.tblDescription
        return None if tblDescription is None else tblDescription.val

    @description.setter
    def description(self, value: str | None):
        tblPr = self._tblPr
        tblPr._remove_tblDescription()  # pyright: ignore[reportPrivateUsage]
        if value is not None:
            tblPr.get_or_add_tblDescription().val = value

    @lazyproperty
    def cell_margins(self) -> _TableCellMargins:
        """The default cell margins for every cell of this table::

            table.cell_margins.left = Pt(6)

        An edge reads |None| when the table sets no value for it, in which case the
        table style's margin applies. Assigning |None| removes the override.
        """
        return _TableCellMargins(self._tbl)

    @property
    def indent(self) -> Length | None:
        """Indentation of this table from the margin, or |None| if not set.

        This is `w:tblInd`. Assigning |None| removes it.
        """
        tblInd = self._tblPr.tblInd
        return None if tblInd is None else tblInd.width

    @indent.setter
    def indent(self, value: Length | None) -> None:
        tblPr = self._tblPr
        if value is None:
            tblPr._remove_tblInd()  # pyright: ignore[reportPrivateUsage]
            return
        tblPr.get_or_add_tblInd().width = value

    @lazyproperty
    def look(self) -> _TableLook:
        """Which parts of the table style apply to this table::

            table.look.first_row = True
            table.look.horizontal_banding = True

        Applying a table style without setting these produces a table that looks nothing
        like the style preview in Word.
        """
        return _TableLook(self._tbl)

    @property
    def width(self) -> Length | Pct | None:
        """The preferred width of this table.

        A |Length| for an absolute width, a |Pct| for a percentage of the text column,
        and |None| when the width is `auto` — Word sizing the table to its content —
        or no `w:tblW` is present at all.

        A percentage table reflows with the page margins where one built from absolute
        column widths does not, so ``table.width = Pct(100)`` is not the same as setting
        the column widths to add up::

            table.width = Pct(100)
            table.width = Inches(6)
            table.width = None       # auto

        Note this is the *preferred* width: Word may widen a table whose content does
        not fit, and a table with `autofit` on will do so routinely.
        """
        tblW = self._tblPr.tblW
        return None if tblW is None else tblW.value

    @width.setter
    def width(self, value: Length | Pct | None) -> None:
        tblPr = self._tblPr
        if value is None and tblPr.tblW is None:
            return
        tblPr.get_or_add_tblW().value = value

    def delete(self) -> None:
        """Remove this table from the document.

        Relationships referenced only from inside the table are dropped, and any range
        marker left unmatched is removed, as for `Paragraph.delete()`.
        """
        delete_element(self._tbl, self.part)

    @lazyproperty
    def columns(self):
        """|_Columns| instance representing the sequence of columns in this table."""
        return _Columns(self._tbl, self)

    def row_cells(self, row_idx: int) -> list[_Cell]:
        """DEPRECATED: Use `table.rows[row_idx].cells` instead.

        Sequence of cells in the row at `row_idx` in this table.
        """
        column_count = self._column_count
        start = row_idx * column_count
        end = start + column_count
        return self._cells[start:end]

    @lazyproperty
    def rows(self) -> _Rows:
        """|_Rows| instance containing the sequence of rows in this table."""
        return _Rows(self._tbl, self)

    @property
    def style(self) -> _TableStyle | None:
        """|_TableStyle| object representing the style applied to this table.

        Read/write. The default table style for the document (often `Normal Table`) is
        returned if the table has no directly-applied style. Assigning |None| to this
        property removes any directly-applied table style causing it to inherit the
        default table style of the document.

        Note that the style name of a table style differs slightly from that displayed
        in the user interface; a hyphen, if it appears, must be removed. For example,
        `Light Shading - Accent 1` becomes `Light Shading Accent 1`.
        """
        style_id = self._tbl.tblStyle_val
        return cast("_TableStyle | None", self.part.get_style(style_id, WD_STYLE_TYPE.TABLE))

    @style.setter
    def style(self, style_or_name: _TableStyle | str | None):
        style_id = self.part.get_style_id(style_or_name, WD_STYLE_TYPE.TABLE)
        self._tbl.tblStyle_val = style_id

    @property
    def table(self):
        """Provide child objects with reference to the |Table| object they belong to,
        without them having to know their direct parent is a |Table| object.

        This is the terminus of a series of `parent._table` calls from an arbitrary
        child through its ancestors.
        """
        return self

    @property
    def table_direction(self) -> WD_TABLE_DIRECTION | None:
        """Member of :ref:`WdTableDirection` indicating cell-ordering direction.

        For example: `WD_TABLE_DIRECTION.LTR`. |None| indicates the value is inherited
        from the style hierarchy.
        """
        return cast("WD_TABLE_DIRECTION | None", self._tbl.bidiVisual_val)

    @table_direction.setter
    def table_direction(self, value: WD_TABLE_DIRECTION | None):
        self._element.bidiVisual_val = value

    @property
    def title(self) -> str | None:
        """Alternative-text title for this table, or |None| if not set.

        Assigning |None| removes the title. This value is stored in the
        ``w:tblCaption`` table-property element and is used by assistive technologies.
        """
        tblCaption = self._tblPr.tblCaption
        return None if tblCaption is None else tblCaption.val

    @title.setter
    def title(self, value: str | None):
        tblPr = self._tblPr
        tblPr._remove_tblCaption()  # pyright: ignore[reportPrivateUsage]
        if value is not None:
            tblPr.get_or_add_tblCaption().val = value

    @property
    def _cells(self) -> list[_Cell]:
        """A sequence of |_Cell| objects, one for each cell of the layout grid.

        If the table contains a span, one or more |_Cell| object references are
        repeated.
        """
        cells: list[_Cell] = []
        cell_by_tc: dict[CT_Tc, _Cell] = {}
        for tc in self._tbl.iter_tcs():
            # -- a continuation cell of a vertical span repeats the cell the span starts
            # -- at; callers depend on getting the same object back --
            top_tc = tc.top_tc
            cell = cell_by_tc.get(top_tc)
            if cell is None:
                cell = cell_by_tc[top_tc] = _Cell(top_tc, self)
            cells.extend([cell] * tc.grid_span)
        return cells

    @property
    def _column_count(self):
        """The number of grid columns in this table."""
        return self._tbl.col_count

    @property
    def _tblPr(self) -> CT_TblPr:
        return self._tbl.tblPr


class _Cell(BlockItemContainer):
    """Table cell."""

    def __init__(self, tc: CT_Tc, parent: TableParent):
        super(_Cell, self).__init__(tc, cast("t.ProvidesStoryPart", parent))
        self._parent = parent
        self._tc = self._element = tc

    def add_paragraph(self, text: str = "", style: str | ParagraphStyle | None = None):
        """Return a paragraph newly added to the end of the content in this cell.

        If present, `text` is added to the paragraph in a single run. If specified, the
        paragraph style `style` is applied. If `style` is not specified or is |None|,
        the result is as though the 'Normal' style was applied. Note that the formatting
        of text in a cell can be influenced by the table style. `text` can contain tab
        (``\\t``) characters, which are converted to the appropriate XML form for a tab.
        `text` can also include newline (``\\n``) or carriage return (``\\r``)
        characters, each of which is converted to a line break.
        """
        return super(_Cell, self).add_paragraph(text, style)

    def add_table(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        rows: int,
        cols: int,
        *,
        title: str | None = None,
        description: str | None = None,
    ) -> Table:
        """Return a table newly added to this cell after any existing cell content.

        The new table will have `rows` rows and `cols` columns.

        An empty paragraph is added after the table because Word requires a paragraph
        element as the last element in every cell.

        `description` is the table's alternative text and `title` the separate,
        caption-like field Word writes alongside it. Both are omitted from the XML when
        |None|.
        """
        width = self.width if self.width is not None else Inches(1)
        table = super(_Cell, self).add_table(
            rows, cols, width, title=title, description=description
        )
        self.add_paragraph()
        return table

    @lazyproperty
    def borders(self) -> _CellBorders:
        """The border edges of this cell, as a mapping keyed by edge name::

            cell.borders["bottom"].line = WD_LINE_STYLE.DOUBLE

        A cell adds the two diagonal edges `tl2br` and `tr2bl` to the edges a table
        admits. A border set here takes precedence over the table border at the same
        edge.
        """
        return _CellBorders(self._tc)

    @property
    def column_index(self) -> int:
        """Index of the left-most layout-grid column this cell occupies.

        Together with `.row_index` this gives the origin of the cell, which is what
        tells a repeat of a merged cell apart from a cell in its own right::

            for row_idx, row in enumerate(table.rows):
                for col_idx, cell in enumerate(row.cells):
                    if (cell.row_index, cell.column_index) != (row_idx, col_idx):
                        continue  # -- already emitted, this is part of a merged cell --
                    emit(cell.text, rowspan=cell.span_height, colspan=cell.grid_span)

        Note this is a layout-grid column index, so it accounts for the grid positions a
        row leaves unpopulated at its start; see `_Row.grid_cols_before`.
        """
        return self._tc.left

    @property
    def grid_span(self) -> int:
        """Number of layout-grid cells this cell spans horizontally.

        A "normal" cell has a grid-span of 1. A horizontally merged cell has a grid-span of 2 or
        more.
        """
        return self._tc.grid_span

    @property
    def is_merged(self) -> bool:
        """|True| when this cell spans more than one layout-grid cell.

        Horizontally, vertically, or both.
        """
        return self.grid_span > 1 or self.span_height > 1

    def merge(self, other_cell: _Cell):
        """Return a merged cell created by spanning the rectangular region having this
        cell and `other_cell` as diagonal corners.

        Raises |InvalidSpanError| if the cells do not define a rectangular region.
        """
        tc, tc_2 = self._tc, other_cell._tc
        merged_tc = tc.merge(tc_2)
        return _Cell(merged_tc, self._parent)

    @property
    def paragraphs(self):
        """List of paragraphs in the cell.

        A table cell is required to contain at least one block-level element and end
        with a paragraph. By default, a new cell contains a single paragraph. Read-only
        """
        return super(_Cell, self).paragraphs

    @property
    def row_index(self) -> int:
        """Index of the top-most row this cell occupies.

        For a vertically merged cell this is the row the merge starts at, not the row
        the cell was reached through. See `.column_index` for how the pair is used.
        """
        return self._tc.top

    @property
    def span(self) -> tuple[int, int]:
        """The extent of this cell as `(rows, columns)`.

        `(1, 1)` for an unmerged cell.
        """
        return (self.span_height, self.grid_span)

    @property
    def span_height(self) -> int:
        """Number of rows this cell spans vertically.

        An unmerged cell has a span-height of 1; a vertically merged cell has 2 or more.
        This is the read-side counterpart of `.grid_span`, and the two together describe
        a merge completely, including the combined case of a cell that is merged in both
        directions.

        A merge is measured by following its continuation cells, so a document whose
        origin cell omits `w:vMerge` — legal in practice and common from generators
        other than Word — reports the same extent Word renders.
        """
        return self._tc.bottom - self._tc.top

    @property
    def tables(self):
        """List of tables in the cell, in the order they appear.

        Read-only.
        """
        return super(_Cell, self).tables

    @property
    def text(self) -> str:
        """The entire contents of this cell as a string of text.

        Assigning a string to this property replaces all existing content with a single
        paragraph containing the assigned text in a single run.
        """
        return "\n".join(p.text for p in self.paragraphs)

    @text.setter
    def text(self, text: str):
        """Write-only.

        Set entire contents of cell to the string `text`. Any existing content or
        revisions are replaced.
        """
        tc = self._tc
        tc.clear_content()
        p = tc.add_p()
        r = p.add_r()
        r.text = text

    @property
    def text_direction(self) -> WD_TEXT_DIRECTION | None:
        """Flow direction of the text in this cell, or |None| when inherited.

        This is what a rotated header cell needs::

            cell.text_direction = WD_TEXT_DIRECTION.BT_LR

        Assigning |None| removes the setting, restoring inheritance.
        """
        tcPr = self._element.tcPr
        return None if tcPr is None else tcPr.textDirection_val

    @text_direction.setter
    def text_direction(self, value: WD_TEXT_DIRECTION | None) -> None:
        if value is None and self._element.tcPr is None:
            return
        self._element.get_or_add_tcPr().textDirection_val = value

    @property
    def vertical_alignment(self):
        """Member of :ref:`WdCellVerticalAlignment` or None.

        A value of |None| indicates vertical alignment for this cell is inherited.
        Assigning |None| causes any explicitly defined vertical alignment to be removed,
        restoring inheritance.
        """
        tcPr = self._element.tcPr
        if tcPr is None:
            return None
        return tcPr.vAlign_val

    @vertical_alignment.setter
    def vertical_alignment(self, value: WD_CELL_VERTICAL_ALIGNMENT | None):
        tcPr = self._element.get_or_add_tcPr()
        tcPr.vAlign_val = value

    @property
    def width(self):
        """The width of this cell in EMU, or |None| if no explicit width is set."""
        return self._tc.width

    @width.setter
    def width(self, value: Length):
        self._tc.width = value


class _Column(Parented):
    """Table column."""

    def __init__(self, gridCol: CT_TblGridCol, parent: TableParent):
        super(_Column, self).__init__(parent)
        self._parent = parent
        self._gridCol = gridCol

    @property
    def cells(self) -> tuple[_Cell, ...]:
        """Sequence of |_Cell| instances corresponding to cells in this column."""
        return tuple(self.table.column_cells(self._index))

    def delete(self) -> None:
        """Remove this column from its table.

        Removes the `w:gridCol` and the cell occupying this layout-grid column in every
        row. A cell that spans this column and others is narrowed by one rather than
        removed, so the rest of its span survives.
        """
        table = self.table
        column_idx = self._index
        for tr in table._tbl.tr_lst:  # pyright: ignore[reportPrivateUsage]
            tr.delete_grid_column(column_idx, table.part)
        delete_element(self._gridCol, table.part)

    @property
    def table(self) -> Table:
        """Reference to the |Table| object this column belongs to."""
        return self._parent.table

    @property
    def width(self) -> Length | None:
        """The width of this column in EMU, or |None| if no explicit width is set."""
        return self._gridCol.w

    @width.setter
    def width(self, value: Length | None):
        self._gridCol.w = value

    @property
    def _index(self):
        """Index of this column in its table, starting from zero."""
        return self._gridCol.gridCol_idx


class _Columns(Parented):
    """Sequence of |_Column| instances corresponding to the columns in a table.

    Supports ``len()``, iteration and indexed access.
    """

    def __init__(self, tbl: CT_Tbl, parent: TableParent):
        super(_Columns, self).__init__(parent)
        self._parent = parent
        self._tbl = tbl

    def __getitem__(self, idx: int):
        """Provide indexed access, e.g. 'columns[0]'."""
        try:
            gridCol = self._gridCol_lst[idx]
        except IndexError:
            msg = "column index [%d] is out of range" % idx
            raise IndexError(msg)
        return _Column(gridCol, self)

    def __iter__(self):
        for gridCol in self._gridCol_lst:
            yield _Column(gridCol, self)

    def __len__(self):
        return len(self._gridCol_lst)

    @property
    def table(self) -> Table:
        """Reference to the |Table| object this column collection belongs to."""
        return self._parent.table

    @property
    def _gridCol_lst(self):
        """Sequence containing ``<w:gridCol>`` elements for this table, each
        representing a table column."""
        tblGrid = self._tbl.tblGrid
        return tblGrid.gridCol_lst


class _Row(Parented):
    """Table row."""

    def __init__(self, tr: CT_Row, parent: TableParent):
        super(_Row, self).__init__(parent)
        self._parent = parent
        self._tr = self._element = tr

    @property
    def cells(self) -> tuple[_Cell, ...]:
        """Sequence of |_Cell| instances corresponding to cells in this row.

        Note that Word allows table rows to start later than the first column and end before the
        last column.

        - Only cells actually present are included in the return value.
        - This implies the length of this cell sequence may differ between rows of the same table.
        - If you are reading the cells from each row to form a rectangular "matrix" data structure
          of the table cell values, you will need to account for empty leading and/or trailing
          layout-grid positions using `.grid_cols_before` and `.grid_cols_after`.

        """

        def iter_tc_cells(tc: CT_Tc) -> Iterator[_Cell]:
            """Generate a cell object for each layout-grid cell in `tc`.

            In particular, a `<w:tc>` element with a horizontal "span" with generate the same cell
            multiple times, one for each grid-cell being spanned. This approximates a row in a
            "uniform" table, where each row has a cell for each column in the table.
            """
            # -- a cell comprising the second or later row of a vertical span is indicated by
            # -- tc.vMerge="continue" (the default value of the `w:vMerge` attribute, when it is
            # -- present in the XML). The `w:tc` element at the same grid-offset in the prior row
            # -- is guaranteed to be the same width (gridSpan). So we can delegate content
            # -- discovery to that prior-row `w:tc` element (recursively) until we arrive at the
            # -- "root" cell -- for the vertical span.
            if tc.vMerge == "continue":
                yield from iter_tc_cells(tc._tc_above)  # pyright: ignore[reportPrivateUsage]
                return

            # -- Otherwise, vMerge is either "restart" or None, meaning this `tc` holds the actual
            # -- content of the cell (whether it is vertically merged or not).
            cell = _Cell(tc, self.table)
            for _ in range(tc.grid_span):
                yield cell

        def _iter_row_cells() -> Iterator[_Cell]:
            """Generate `_Cell` instance for each populated layout-grid cell in this row."""
            for tc in self._tr.tc_lst:
                yield from iter_tc_cells(tc)

        return tuple(_iter_row_cells())

    def delete(self) -> None:
        """Remove this row from its table.

        A vertically merged cell whose span started in this row is not dropped: the row
        below inherits it, so the merge continues to render, which is what Word does
        when a row is deleted.
        """
        self._tr.transfer_vertical_spans_to_row_below()
        delete_element(self._tr, self.table.part)

    @property
    def grid_cols_after(self) -> int:
        """Count of unpopulated grid-columns after the last cell in this row.

        Word allows a row to "end early", meaning that one or more cells are not present at the
        end of that row.

        Note these are not simply "empty" cells. The renderer reads this value and "skips" this
        many columns after drawing the last cell.

        Note this also implies that not all rows are guaranteed to have the same number of cells,
        e.g. `_Row.cells` could have length `n` for one row and `n - m` for the next row in the same
        table. Visually this appears as a column (at the beginning or end, not in the middle) with
        one or more cells missing.
        """
        return self._tr.grid_after

    @property
    def grid_cols_before(self) -> int:
        """Count of unpopulated grid-columns before the first cell in this row.

        Word allows a row to "start late", meaning that one or more cells are not present at the
        beginning of that row.

        Note these are not simply "empty" cells. The renderer reads this value and skips forward to
        the table layout-grid position of the first cell in this row; the renderer "skips" this many
        columns before drawing the first cell.

        Note this also implies that not all rows are guaranteed to have the same number of cells,
        e.g. `_Row.cells` could have length `n` for one row and `n - m` for the next row in the same
        table.
        """
        return self._tr.grid_before

    @property
    def height(self) -> Length | None:
        """Return a |Length| object representing the height of this cell, or |None| if
        no explicit height is set."""
        return self._tr.trHeight_val

    @height.setter
    def height(self, value: Length | None):
        self._tr.trHeight_val = value

    @property
    def dont_split(self) -> bool | None:
        """|True| if this row is kept on a single page rather than broken across pages.

        Corresponds to unchecking "Allow row to break across pages" in Word. |None|
        indicates no explicit setting, which Word treats as allowing the break.
        """
        return self._tr.cantSplit_val

    @dont_split.setter
    def dont_split(self, value: bool | None) -> None:
        self._tr.cantSplit_val = value

    @property
    def repeat_as_header(self) -> bool | None:
        """|True| when this row repeats at the top of each page the table spans.

        Corresponds to "Repeat Header Rows" in Word. |None| indicates no explicit
        setting, which Word treats as off.

        Word only honours this on a contiguous run of rows starting at the first row of
        the table. Setting it on row 3 alone is legal XML that has no visible effect.
        """
        return self._tr.tblHeader_val

    @repeat_as_header.setter
    def repeat_as_header(self, value: bool | None) -> None:
        self._tr.tblHeader_val = value

    @property
    def hidden(self) -> bool | None:
        """|True| when this row is not displayed.

        |None| indicates no explicit setting, which Word treats as visible.
        """
        return self._tr.hidden_val

    @hidden.setter
    def hidden(self, value: bool | None) -> None:
        self._tr.hidden_val = value

    @property
    def alignment(self) -> WD_TABLE_ALIGNMENT | None:
        """Horizontal alignment of this row within the table, or |None| if not set.

        This overrides the table's own alignment for this row alone.
        """
        return self._tr.alignment

    @alignment.setter
    def alignment(self, value: WD_TABLE_ALIGNMENT | None) -> None:
        self._tr.alignment = value

    @property
    def cell_spacing(self) -> Length | None:
        """Spacing between the cells of this row, or |None| if not set."""
        return self._tr.cell_spacing

    @cell_spacing.setter
    def cell_spacing(self, value: Length | None) -> None:
        self._tr.cell_spacing = value

    @property
    def width_before(self) -> Length | None:
        """Width of the grid positions this row leaves unpopulated at its start.

        Pairs with `.grid_cols_before`, which counts them. |None| if not set.
        """
        return self._tr.width_before

    @width_before.setter
    def width_before(self, value: Length | None) -> None:
        self._tr.width_before = value

    @property
    def width_after(self) -> Length | None:
        """Width of the grid positions this row leaves unpopulated at its end.

        Pairs with `.grid_cols_after`, which counts them. |None| if not set.
        """
        return self._tr.width_after

    @width_after.setter
    def width_after(self, value: Length | None) -> None:
        self._tr.width_after = value

    @property
    def height_rule(self) -> WD_ROW_HEIGHT_RULE | None:
        """Return the height rule of this cell as a member of the :ref:`WdRowHeightRule`.

        This value is |None| if no explicit height_rule is set.
        """
        return self._tr.trHeight_hRule

    @height_rule.setter
    def height_rule(self, value: WD_ROW_HEIGHT_RULE | None):
        self._tr.trHeight_hRule = value

    @property
    def table(self) -> Table:
        """Reference to the |Table| object this row belongs to."""
        return self._parent.table

    @property
    def _index(self) -> int:
        """Index of this row in its table, starting from zero."""
        return self._tr.tr_idx


class _Rows(Parented):
    """Sequence of |_Row| objects corresponding to the rows in a table.

    Supports ``len()``, iteration, indexed access, and slicing.
    """

    def __init__(self, tbl: CT_Tbl, parent: TableParent):
        super(_Rows, self).__init__(parent)
        self._parent = parent
        self._tbl = tbl

    @overload
    def __getitem__(self, idx: int) -> _Row: ...

    @overload
    def __getitem__(self, idx: slice) -> list[_Row]: ...

    def __getitem__(self, idx: int | slice) -> _Row | list[_Row]:
        """Provide indexed access, (e.g. `rows[0]` or `rows[1:3]`)"""
        return list(self)[idx]

    def __iter__(self):
        return (_Row(tr, self) for tr in self._tbl.tr_lst)

    def __len__(self):
        return len(self._tbl.tr_lst)

    @property
    def table(self) -> Table:
        """Reference to the |Table| object this row collection belongs to."""
        return self._parent.table
