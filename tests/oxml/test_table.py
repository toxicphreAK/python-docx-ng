# pyright: reportPrivateUsage=false

"""Test suite for the docx.oxml.text module."""

from __future__ import annotations

from typing import cast

import pytest

from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.exceptions import InvalidSpanError
from docx.oxml.ns import nsdecls
from docx.oxml.parser import parse_xml
from docx.oxml.table import (
    CT_Row,
    CT_Tbl,
    CT_TblCellMar,
    CT_TblLook,
    CT_TblPr,
    CT_TblWidth,
    CT_Tc,
    CT_TrPr,
)
from docx.oxml.text.paragraph import CT_P
from docx.shared import Inches, Pct, Twips

from ..unitutil.cxml import element, xml
from ..unitutil.file import snippet_seq
from ..unitutil.mock import FixtureRequest, Mock, call, instance_mock, method_mock, property_mock


class DescribeCT_Row:
    @pytest.mark.parametrize(
        ("tr_cxml", "expected_cxml"),
        [
            ("w:tr", "w:tr/w:trPr"),
            ("w:tr/w:tblPrEx", "w:tr/(w:tblPrEx,w:trPr)"),
            ("w:tr/w:tc", "w:tr/(w:trPr,w:tc)"),
            ("w:tr/(w:sdt,w:del,w:tc)", "w:tr/(w:trPr,w:sdt,w:del,w:tc)"),
        ],
    )
    def it_can_add_a_trPr(self, tr_cxml: str, expected_cxml: str):
        tr = cast(CT_Row, element(tr_cxml))
        tr._add_trPr()
        assert tr.xml == xml(expected_cxml)

    @pytest.mark.parametrize(("snippet_idx", "row_idx", "col_idx"), [(0, 0, 3), (1, 0, 1)])
    def it_raises_on_tc_at_grid_col(self, snippet_idx: int, row_idx: int, col_idx: int):
        tr = cast(CT_Tbl, parse_xml(snippet_seq("tbl-cells")[snippet_idx])).tr_lst[row_idx]
        with pytest.raises(ValueError, match=f"no `tc` element at grid_offset={col_idx}"):
            tr.tc_at_grid_offset(col_idx)


class DescribeCT_Tc:
    """Unit-test suite for `docx.oxml.table.CT_Tc` objects."""

    @pytest.mark.parametrize(
        ("tr_cxml", "tc_idx", "expected_value"),
        [
            ("w:tr/(w:tc/w:p,w:tc/w:p)", 0, 0),
            ("w:tr/(w:tc/w:p,w:tc/w:p)", 1, 1),
            ("w:tr/(w:trPr/w:gridBefore{w:val=2},w:tc/w:p,w:tc/w:p)", 0, 2),
            ("w:tr/(w:trPr/w:gridBefore{w:val=2},w:tc/w:p,w:tc/w:p)", 1, 3),
            ("w:tr/(w:trPr/w:gridBefore{w:val=4},w:tc/w:p,w:tc/w:p,w:tc/w:p,w:tc/w:p)", 2, 6),
        ],
    )
    def it_knows_its_grid_offset(self, tr_cxml: str, tc_idx: int, expected_value: int):
        tr = cast(CT_Row, element(tr_cxml))
        tc = tr.tc_lst[tc_idx]

        assert tc.grid_offset == expected_value

    def it_can_merge_to_another_tc(
        self, tr_: Mock, _span_dimensions_: Mock, _tbl_: Mock, _grow_to_: Mock, top_tc_: Mock
    ):
        top_tr_ = tr_
        tc, other_tc = cast(CT_Tc, element("w:tc")), cast(CT_Tc, element("w:tc"))
        top, left, height, width = 0, 1, 2, 3
        _span_dimensions_.return_value = top, left, height, width
        _tbl_.return_value.tr_lst = [tr_]
        tr_.tc_at_grid_offset.return_value = top_tc_

        merged_tc = tc.merge(other_tc)

        _span_dimensions_.assert_called_once_with(tc, other_tc)
        top_tr_.tc_at_grid_offset.assert_called_once_with(left)
        top_tc_._grow_to.assert_called_once_with(width, height)
        assert merged_tc is top_tc_

    @pytest.mark.parametrize(
        ("snippet_idx", "row", "col", "attr_name", "expected_value"),
        [
            (0, 0, 0, "top", 0),
            (2, 0, 1, "top", 0),
            (2, 1, 1, "top", 0),
            (4, 2, 1, "top", 1),
            (0, 0, 0, "left", 0),
            (1, 0, 1, "left", 2),
            (3, 1, 0, "left", 0),
            (3, 1, 1, "left", 2),
            (0, 0, 0, "bottom", 1),
            (1, 0, 0, "bottom", 1),
            (2, 0, 1, "bottom", 2),
            (4, 1, 1, "bottom", 3),
            (0, 0, 0, "right", 1),
            (1, 0, 0, "right", 2),
            (4, 2, 1, "right", 3),
        ],
    )
    def it_knows_its_extents_to_help(
        self, snippet_idx: int, row: int, col: int, attr_name: str, expected_value: int
    ):
        tbl = self._snippet_tbl(snippet_idx)
        tc = tbl.tr_lst[row].tc_lst[col]

        extent = getattr(tc, attr_name)

        assert extent == expected_value

    @pytest.mark.parametrize(
        ("snippet_idx", "row", "col", "row_2", "col_2", "expected_value"),
        [
            (0, 0, 0, 0, 1, (0, 0, 1, 2)),
            (0, 0, 1, 2, 1, (0, 1, 3, 1)),
            (0, 2, 2, 1, 1, (1, 1, 2, 2)),
            (0, 1, 2, 1, 0, (1, 0, 1, 3)),
            (1, 0, 0, 1, 1, (0, 0, 2, 2)),
            (1, 0, 1, 0, 0, (0, 0, 1, 3)),
            (2, 0, 1, 2, 1, (0, 1, 3, 1)),
            (2, 0, 1, 1, 0, (0, 0, 2, 2)),
            (2, 1, 2, 0, 1, (0, 1, 2, 2)),
            (4, 0, 1, 0, 0, (0, 0, 1, 3)),
        ],
    )
    def it_calculates_the_dimensions_of_a_span_to_help(
        self,
        snippet_idx: int,
        row: int,
        col: int,
        row_2: int,
        col_2: int,
        expected_value: tuple[int, int, int, int],
    ):
        tbl = self._snippet_tbl(snippet_idx)
        tc = tbl.tr_lst[row].tc_lst[col]
        other_tc = tbl.tr_lst[row_2].tc_lst[col_2]

        dimensions = tc._span_dimensions(other_tc)

        assert dimensions == expected_value

    @pytest.mark.parametrize(
        ("snippet_idx", "row", "col", "row_2", "col_2"),
        [
            (1, 0, 0, 1, 0),  # inverted-L horz
            (1, 1, 0, 0, 0),  # same in opposite order
            (2, 0, 2, 0, 1),  # inverted-L vert
            (5, 0, 1, 1, 0),  # tee-shape horz bar
            (5, 1, 0, 2, 1),  # same, opposite side
            (6, 1, 0, 0, 1),  # tee-shape vert bar
            (6, 0, 1, 1, 2),  # same, opposite side
        ],
    )
    def it_raises_on_invalid_span(
        self, snippet_idx: int, row: int, col: int, row_2: int, col_2: int
    ):
        tbl = self._snippet_tbl(snippet_idx)
        tc = tbl.tr_lst[row].tc_lst[col]
        other_tc = tbl.tr_lst[row_2].tc_lst[col_2]

        with pytest.raises(InvalidSpanError):
            tc._span_dimensions(other_tc)

    @pytest.mark.parametrize(
        ("snippet_idx", "row", "col", "width", "height"),
        [
            (0, 0, 0, 2, 1),
            (0, 0, 1, 1, 2),
            (0, 1, 1, 2, 2),
            (1, 0, 0, 2, 2),
            (2, 0, 0, 2, 2),
            (2, 1, 2, 1, 2),
        ],
    )
    def it_can_grow_itself_to_help_merge(
        self, snippet_idx: int, row: int, col: int, width: int, height: int, _span_to_width_: Mock
    ):
        tbl = self._snippet_tbl(snippet_idx)
        tc = tbl.tr_lst[row].tc_lst[col]
        start = 0 if height == 1 else 1
        end = start + height

        tc._grow_to(width, height, None)

        assert (
            _span_to_width_.call_args_list
            == [
                call(width, tc, None),
                call(width, tc, "restart"),
                call(width, tc, "continue"),
                call(width, tc, "continue"),
            ][start:end]
        )

    def it_can_extend_its_horz_span_to_help_merge(
        self, top_tc_: Mock, grid_span_: Mock, _move_content_to_: Mock, _swallow_next_tc_: Mock
    ):
        grid_span_.side_effect = [1, 3, 4]
        grid_width, vMerge = 4, "continue"
        tc = cast(CT_Tc, element("w:tc"))

        tc._span_to_width(grid_width, top_tc_, vMerge)

        _move_content_to_.assert_called_once_with(tc, top_tc_)
        assert _swallow_next_tc_.call_args_list == [
            call(tc, grid_width, top_tc_),
            call(tc, grid_width, top_tc_),
        ]
        assert tc.vMerge == vMerge

    def it_knows_its_inner_content_block_item_elements(self):
        tc = cast(CT_Tc, element("w:tc/(w:p,w:tbl,w:p)"))
        assert [type(e) for e in tc.inner_content_elements] == [CT_P, CT_Tbl, CT_P]

    @pytest.mark.parametrize(
        ("tr_cxml", "tc_idx", "grid_width", "expected_cxml"),
        [
            (
                "w:tr/(w:tc/w:p,w:tc/w:p)",
                0,
                2,
                "w:tr/(w:tc/(w:tcPr/w:gridSpan{w:val=2},w:p))",
            ),
            (
                "w:tr/(w:tc/w:p,w:tc/w:p,w:tc/w:p)",
                1,
                2,
                "w:tr/(w:tc/w:p,w:tc/(w:tcPr/w:gridSpan{w:val=2},w:p))",
            ),
            (
                'w:tr/(w:tc/w:p/w:r/w:t"a",w:tc/w:p/w:r/w:t"b")',
                0,
                2,
                'w:tr/(w:tc/(w:tcPr/w:gridSpan{w:val=2},w:p/w:r/w:t"a",w:p/w:r/w:t"b"))',
            ),
            (
                "w:tr/(w:tc/(w:tcPr/w:gridSpan{w:val=2},w:p),w:tc/w:p)",
                0,
                3,
                "w:tr/(w:tc/(w:tcPr/w:gridSpan{w:val=3},w:p))",
            ),
            (
                "w:tr/(w:tc/w:p,w:tc/(w:tcPr/w:gridSpan{w:val=2},w:p))",
                0,
                3,
                "w:tr/(w:tc/(w:tcPr/w:gridSpan{w:val=3},w:p))",
            ),
        ],
    )
    def it_can_swallow_the_next_tc_help_merge(
        self, tr_cxml: str, tc_idx: int, grid_width: int, expected_cxml: str
    ):
        tr = cast(CT_Row, element(tr_cxml))
        tc = top_tc = tr.tc_lst[tc_idx]

        tc._swallow_next_tc(grid_width, top_tc)

        assert tr.xml == xml(expected_cxml)

    @pytest.mark.parametrize(
        ("tr_cxml", "tc_idx", "grid_width", "expected_cxml"),
        [
            # both cells have a width
            (
                "w:tr/(w:tc/(w:tcPr/w:tcW{w:w=1440,w:type=dxa},w:p),"
                "w:tc/(w:tcPr/w:tcW{w:w=1440,w:type=dxa},w:p))",
                0,
                2,
                "w:tr/(w:tc/(w:tcPr/(w:tcW{w:w=2880,w:type=dxa},w:gridSpan{w:val=2}),w:p))",
            ),
            # neither have a width
            (
                "w:tr/(w:tc/w:p,w:tc/w:p)",
                0,
                2,
                "w:tr/(w:tc/(w:tcPr/w:gridSpan{w:val=2},w:p))",
            ),
            # only second one has a width
            (
                "w:tr/(w:tc/w:p,w:tc/(w:tcPr/w:tcW{w:w=1440,w:type=dxa},w:p))",
                0,
                2,
                "w:tr/(w:tc/(w:tcPr/w:gridSpan{w:val=2},w:p))",
            ),
            # only first one has a width
            (
                "w:tr/(w:tc/(w:tcPr/w:tcW{w:w=1440,w:type=dxa},w:p),w:tc/w:p)",
                0,
                2,
                "w:tr/(w:tc/(w:tcPr/(w:tcW{w:w=1440,w:type=dxa},w:gridSpan{w:val=2}),w:p))",
            ),
        ],
    )
    def it_adds_cell_widths_on_swallow(
        self, tr_cxml: str, tc_idx: int, grid_width: int, expected_cxml: str
    ):
        tr = cast(CT_Row, element(tr_cxml))
        tc = top_tc = tr.tc_lst[tc_idx]
        tc._swallow_next_tc(grid_width, top_tc)
        assert tr.xml == xml(expected_cxml)

    @pytest.mark.parametrize(
        ("tr_cxml", "tc_idx", "grid_width"),
        [
            ("w:tr/w:tc/w:p", 0, 2),
            ("w:tr/(w:tc/w:p,w:tc/(w:tcPr/w:gridSpan{w:val=2},w:p))", 0, 2),
        ],
    )
    def it_raises_on_invalid_swallow(self, tr_cxml: str, tc_idx: int, grid_width: int):
        tr = cast(CT_Row, element(tr_cxml))
        tc = top_tc = tr.tc_lst[tc_idx]

        with pytest.raises(InvalidSpanError):
            tc._swallow_next_tc(grid_width, top_tc)

    @pytest.mark.parametrize(
        ("tc_cxml", "tc_2_cxml", "expected_tc_cxml", "expected_tc_2_cxml"),
        [
            ("w:tc/w:p", "w:tc/w:p", "w:tc/w:p", "w:tc/w:p"),
            ("w:tc/w:p", "w:tc/w:p/w:r", "w:tc/w:p", "w:tc/w:p/w:r"),
            ("w:tc/w:p/w:r", "w:tc/w:p", "w:tc/w:p", "w:tc/w:p/w:r"),
            ("w:tc/(w:p/w:r,w:sdt)", "w:tc/w:p", "w:tc/w:p", "w:tc/(w:p/w:r,w:sdt)"),
            (
                "w:tc/(w:p/w:r,w:sdt)",
                "w:tc/(w:tbl,w:p)",
                "w:tc/w:p",
                "w:tc/(w:tbl,w:p/w:r,w:sdt)",
            ),
        ],
    )
    def it_can_move_its_content_to_help_merge(
        self, tc_cxml: str, tc_2_cxml: str, expected_tc_cxml: str, expected_tc_2_cxml: str
    ):
        tc, tc_2 = cast(CT_Tc, element(tc_cxml)), cast(CT_Tc, element(tc_2_cxml))

        tc._move_content_to(tc_2)

        assert tc.xml == xml(expected_tc_cxml)
        assert tc_2.xml == xml(expected_tc_2_cxml)

    @pytest.mark.parametrize(("snippet_idx", "row_idx", "col_idx"), [(0, 0, 0), (4, 0, 0)])
    def it_raises_on_tr_above(self, snippet_idx: int, row_idx: int, col_idx: int):
        tbl = cast(CT_Tbl, parse_xml(snippet_seq("tbl-cells")[snippet_idx]))
        tc = tbl.tr_lst[row_idx].tc_lst[col_idx]

        with pytest.raises(ValueError, match="no tr above topmost tr"):
            tc._tr_above

    # fixtures -------------------------------------------------------

    @pytest.fixture
    def grid_span_(self, request: FixtureRequest):
        return property_mock(request, CT_Tc, "grid_span")

    @pytest.fixture
    def _grow_to_(self, request: FixtureRequest):
        return method_mock(request, CT_Tc, "_grow_to")

    @pytest.fixture
    def _move_content_to_(self, request: FixtureRequest):
        return method_mock(request, CT_Tc, "_move_content_to")

    @pytest.fixture
    def _span_dimensions_(self, request: FixtureRequest):
        return method_mock(request, CT_Tc, "_span_dimensions")

    @pytest.fixture
    def _span_to_width_(self, request: FixtureRequest):
        return method_mock(request, CT_Tc, "_span_to_width", autospec=False)

    def _snippet_tbl(self, idx: int) -> CT_Tbl:
        """A <w:tbl> element for snippet at `idx` in 'tbl-cells' snippet file."""
        return cast(CT_Tbl, parse_xml(snippet_seq("tbl-cells")[idx]))

    @pytest.fixture
    def _swallow_next_tc_(self, request: FixtureRequest):
        return method_mock(request, CT_Tc, "_swallow_next_tc")

    @pytest.fixture
    def _tbl_(self, request: FixtureRequest):
        return property_mock(request, CT_Tc, "_tbl")

    @pytest.fixture
    def top_tc_(self, request: FixtureRequest):
        return instance_mock(request, CT_Tc)

    @pytest.fixture
    def tr_(self, request: FixtureRequest):
        return instance_mock(request, CT_Row)


class DescribeCT_Tbl:
    """Unit-test suite for `docx.oxml.table.CT_Tbl`."""

    def it_synthesizes_a_missing_tblGrid_from_the_widest_row(self):
        """`w:tblGrid` is required by the schema, but Word reads a table without one."""
        tbl = cast(
            CT_Tbl,
            element(
                "w:tbl/(w:tblPr,"
                "w:tr/(w:tc/(w:tcPr/w:tcW{w:w=1440,w:type=dxa},w:p),"
                "w:tc/(w:tcPr/(w:tcW{w:w=2880,w:type=dxa},w:gridSpan{w:val=2}),w:p)),"
                "w:tr/w:tc/w:p)"
            ),
        )

        tblGrid = tbl.tblGrid

        # -- the widest row occupies three grid columns; the merged cell's width is
        # -- divided evenly between the two it spans --
        assert [gridCol.w for gridCol in tblGrid.gridCol_lst] == [
            Twips(1440),
            Twips(1440),
            Twips(1440),
        ]
        assert tbl.col_count == 3

    def it_inserts_the_synthesized_tblGrid_in_schema_position(self):
        """Reading such a table repairs it, so saving writes a valid table back out."""
        tbl = cast(CT_Tbl, element("w:tbl/(w:tblPr,w:tr/w:tc/w:p)"))

        tbl.tblGrid

        assert tbl.xml == xml("w:tbl/(w:tblPr,w:tblGrid/w:gridCol,w:tr/w:tc/w:p)")

    def it_synthesizes_a_tblGrid_for_a_table_with_no_tblPr(self):
        tbl = cast(CT_Tbl, element("w:tbl/w:tr/w:tc/w:p"))

        tbl.tblGrid

        assert tbl.xml == xml("w:tbl/(w:tblGrid/w:gridCol,w:tr/w:tc/w:p)")

    def it_omits_the_width_of_a_column_whose_cell_has_none(self):
        tbl = cast(CT_Tbl, element("w:tbl/(w:tblPr,w:tr/(w:tc/w:p,w:tc/w:p))"))

        assert [gridCol.w for gridCol in tbl.tblGrid.gridCol_lst] == [None, None]

    def it_counts_the_grid_columns_a_row_leaves_unpopulated(self):
        """A row can start late or end early; those positions are still grid columns."""
        tbl = cast(
            CT_Tbl,
            element(
                "w:tbl/(w:tblPr,"
                "w:tr/(w:trPr/(w:gridBefore{w:val=1},w:gridAfter{w:val=2}),w:tc/w:p))"
            ),
        )

        assert tbl.tr_lst[0].grid_width() == 4
        assert tbl.col_count == 4

    def it_leaves_an_existing_tblGrid_alone(self):
        """Including a short one; it reports what the document actually says."""
        tbl_cxml = "w:tbl/(w:tblPr,w:tblGrid/w:gridCol,w:tr/(w:tc/w:p,w:tc/w:p))"
        tbl = cast(CT_Tbl, element(tbl_cxml))

        tbl.tblGrid

        assert tbl.xml == xml(tbl_cxml)

    def it_can_get_a_row_by_index_without_building_the_row_list(self):
        tbl = cast(CT_Tbl, element("w:tbl/(w:tblPr,w:tr/w:tc/w:p,w:tr/w:tc/w:p)"))

        assert tbl.tr_at_idx(0) is tbl.tr_lst[0]
        assert tbl.tr_at_idx(1) is tbl.tr_lst[1]
        assert tbl.tr_at_idx(-1) is tbl.tr_lst[-1]
        with pytest.raises(IndexError, match="out of range"):
            tbl.tr_at_idx(2)


class DescribeCT_Row_grid_offsets:
    """Unit-test suite for resolving a `w:tc` by layout-grid column."""

    @pytest.mark.parametrize(("grid_offset", "expected_tc_idx"), [(0, 0), (1, 1), (2, 1), (3, 2)])
    def it_returns_the_covering_tc_for_a_spanned_grid_offset(
        self, grid_offset: int, expected_tc_idx: int
    ):
        tr = cast(
            CT_Row,
            element("w:tr/(w:tc/w:p,w:tc/(w:tcPr/w:gridSpan{w:val=2},w:p),w:tc/w:p)"),
        )

        assert tr.tc_covering_grid_offset(grid_offset) is tr.tc_lst[expected_tc_idx]

    @pytest.mark.parametrize("grid_offset", [0, 3, 4])
    def it_raises_for_a_grid_offset_the_row_does_not_populate(self, grid_offset: int):
        """Word allows a row to start late or end early."""
        tr = cast(
            CT_Row,
            element("w:tr/(w:trPr/(w:gridBefore{w:val=1},w:gridAfter{w:val=1}),w:tc/w:p,w:tc/w:p)"),
        )

        with pytest.raises(ValueError, match="does not populate"):
            tr.tc_covering_grid_offset(grid_offset)


class DescribeCT_TrPr:
    """Unit-test suite for the row-property elements added for issue #106."""

    @pytest.mark.parametrize(
        ("trPr_cxml", "expected_cxml"),
        [
            # -- w:tblHeader sits between w:trHeight and w:tblCellSpacing. `w:val="1"`
            # -- is the ST_OnOff default, so it is not written. --
            ("w:trPr", "w:trPr/w:tblHeader"),
            (
                "w:trPr/w:trHeight{w:val=240}",
                "w:trPr/(w:trHeight{w:val=240},w:tblHeader)",
            ),
            (
                "w:trPr/w:jc{w:val=center}",
                "w:trPr/(w:tblHeader,w:jc{w:val=center})",
            ),
        ],
    )
    def it_inserts_tblHeader_in_schema_order(self, trPr_cxml: str, expected_cxml: str):
        trPr = cast(CT_TrPr, element(trPr_cxml))

        trPr.tblHeader_val = True

        assert trPr.xml == xml(expected_cxml)

    @pytest.mark.parametrize(
        ("trPr_cxml", "expected_cxml"),
        [
            ("w:trPr", "w:trPr/w:hidden"),
            (
                "w:trPr/w:jc{w:val=center}",
                "w:trPr/(w:jc{w:val=center},w:hidden)",
            ),
        ],
    )
    def it_inserts_hidden_after_jc(self, trPr_cxml: str, expected_cxml: str):
        trPr = cast(CT_TrPr, element(trPr_cxml))

        trPr.hidden_val = True

        assert trPr.xml == xml(expected_cxml)

    def it_inserts_wBefore_and_wAfter_between_gridAfter_and_cantSplit(self):
        trPr = cast(
            CT_TrPr,
            element("w:trPr/(w:gridBefore{w:val=1},w:cantSplit{w:val=1})"),
        )

        trPr.width_before = Twips(120)
        trPr.width_after = Twips(240)

        assert trPr.xml == xml(
            "w:trPr/(w:gridBefore{w:val=1},w:wBefore{w:w=120,w:type=dxa},"
            "w:wAfter{w:w=240,w:type=dxa},w:cantSplit{w:val=1})"
        )
        assert trPr.width_before == Twips(120)
        assert trPr.width_after == Twips(240)

    def it_inserts_tblCellSpacing_between_tblHeader_and_jc(self):
        trPr = cast(CT_TrPr, element("w:trPr/(w:tblHeader,w:jc{w:val=center})"))

        trPr.cell_spacing = Twips(15)

        assert trPr.xml == xml(
            "w:trPr/(w:tblHeader,w:tblCellSpacing{w:w=15,w:type=dxa},w:jc{w:val=center})"
        )

    @pytest.mark.parametrize("attr", ["tblHeader_val", "hidden_val"])
    def it_removes_the_element_when_assigned_None(self, attr: str):
        trPr = cast(CT_TrPr, element("w:trPr/(w:tblHeader,w:hidden)"))

        setattr(trPr, attr, None)

        assert getattr(trPr, attr) is None

    def it_reads_the_row_alignment(self):
        trPr = cast(CT_TrPr, element("w:trPr/w:jc{w:val=center}"))

        assert trPr.alignment == WD_TABLE_ALIGNMENT.CENTER


class DescribeCT_TblPr:
    """Unit-test suite for the table-property elements added for issues #97 and #107."""

    @pytest.mark.parametrize(
        ("tblPr_cxml", "expected_cxml"),
        [
            # -- w:tblW sits between w:tblStyleColBandSize and w:jc --
            ("w:tblPr", "w:tblPr/w:tblW{w:w=5000,w:type=pct}"),
            (
                "w:tblPr/w:jc{w:val=center}",
                "w:tblPr/(w:tblW{w:w=5000,w:type=pct},w:jc{w:val=center})",
            ),
            (
                "w:tblPr/w:tblStyle{w:val=X}",
                "w:tblPr/(w:tblStyle{w:val=X},w:tblW{w:w=5000,w:type=pct})",
            ),
        ],
    )
    def it_inserts_tblW_in_schema_order(self, tblPr_cxml: str, expected_cxml: str):
        tblPr = cast(CT_TblPr, element(tblPr_cxml))

        tblPr.get_or_add_tblW().value = Pct(100)

        assert tblPr.xml == xml(expected_cxml)

    def it_inserts_tblInd_between_tblCellSpacing_and_tblBorders(self):
        tblPr = cast(CT_TblPr, element("w:tblPr/w:tblBorders"))

        tblPr.get_or_add_tblInd().width = Twips(360)

        assert tblPr.xml == xml("w:tblPr/(w:tblInd{w:w=360,w:type=dxa},w:tblBorders)")

    def it_inserts_tblCellMar_and_tblLook_before_tblCaption(self):
        tblPr = cast(CT_TblPr, element("w:tblPr/w:tblCaption{w:val=T}"))

        tblPr.get_or_add_tblCellMar()
        tblPr.get_or_add_tblLook()

        assert tblPr.xml == xml("w:tblPr/(w:tblCellMar,w:tblLook,w:tblCaption{w:val=T})")


class DescribeCT_TblWidth:
    """Unit-test suite for the width readings added for issue #107."""

    @pytest.mark.parametrize(
        ("cxml", "expected"),
        [
            ("w:tblW{w:w=2880,w:type=dxa}", Twips(2880)),
            ("w:tblW{w:w=5000,w:type=pct}", Pct(100)),
            ("w:tblW{w:w=0,w:type=auto}", None),
            ("w:tblW{w:w=0,w:type=nil}", None),
        ],
    )
    def it_knows_the_width_it_expresses(self, cxml: str, expected: object):
        tblW = cast(CT_TblWidth, element(cxml))

        assert tblW.value == expected

    @pytest.mark.parametrize(
        ("value", "expected_cxml"),
        [
            (Twips(2880), "w:tblW{w:w=2880,w:type=dxa}"),
            (Pct(50), "w:tblW{w:w=2500,w:type=pct}"),
            (None, "w:tblW{w:w=0,w:type=auto}"),
        ],
    )
    def it_can_be_assigned_a_length_a_percentage_or_None(
        self, value: object, expected_cxml: str
    ):
        tblW = cast(CT_TblWidth, element("w:tblW{w:w=1,w:type=dxa}"))

        tblW.value = value  # pyright: ignore[reportAttributeAccessIssue]

        assert tblW.xml == xml(expected_cxml)

    def it_reads_a_percentage_written_with_a_percent_sign(self):
        """The schema admits `"50%"`; Word does not write it but other producers do."""
        tblW = cast(CT_TblWidth, parse_xml(
            '<w:tblW %s w:w="50%%" w:type="pct"/>' % nsdecls("w")
        ))

        assert tblW.value == Pct(50)

    def it_reads_a_universal_measure(self):
        tblW = cast(CT_TblWidth, parse_xml(
            '<w:tblW %s w:w="1.5in" w:type="dxa"/>' % nsdecls("w")
        ))

        assert tblW.value == Inches(1.5)


class DescribeCT_TblLook:
    """Unit-test suite for `w:tblLook`, issue #97."""

    def it_rewrites_the_legacy_bitmask_from_the_named_attributes(self):
        tblLook = cast(CT_TblLook, element("w:tblLook"))

        tblLook.firstRow = True
        tblLook.firstColumn = True
        tblLook.noVBand = True
        tblLook.update_val()

        # -- 0x0020 | 0x0080 | 0x0400, the value Word writes for a default table --
        assert tblLook.val == 0x04A0
        assert tblLook.xml == xml(
            "w:tblLook{w:firstRow=1,w:firstColumn=1,w:noVBand=1,w:val=04A0}"
        )

    def it_clears_the_bitmask_when_every_flag_is_off(self):
        tblLook = cast(CT_TblLook, element("w:tblLook{w:val=04A0}"))

        tblLook.update_val()

        assert tblLook.val == 0


class DescribeCT_TblCellMar:
    """Unit-test suite for `w:tblCellMar`, issue #107."""

    def it_inserts_its_edges_in_schema_order(self):
        tblCellMar = cast(CT_TblCellMar, element("w:tblCellMar"))

        tblCellMar.set_margin("right", Twips(108))
        tblCellMar.set_margin("top", Twips(0))
        tblCellMar.set_margin("left", Twips(108))

        assert tblCellMar.xml == xml(
            "w:tblCellMar/(w:top{w:w=0,w:type=dxa},w:left{w:w=108,w:type=dxa},"
            "w:right{w:w=108,w:type=dxa})"
        )

    def it_reads_an_edge_back(self):
        tblCellMar = cast(CT_TblCellMar, element("w:tblCellMar/w:left{w:w=108,w:type=dxa}"))

        assert tblCellMar.get_margin("left") == Twips(108)
        assert tblCellMar.get_margin("right") is None

    def it_removes_an_edge_assigned_None(self):
        tblCellMar = cast(CT_TblCellMar, element("w:tblCellMar/w:left{w:w=108,w:type=dxa}"))

        tblCellMar.set_margin("left", None)

        assert tblCellMar.xml == xml("w:tblCellMar")
