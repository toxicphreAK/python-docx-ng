"""Test suite for docx.text.parfmt module, containing the ParagraphFormat object."""

import pytest

from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_SHADING_PATTERN
from docx.shared import Pt, RGBColor
from docx.text.parfmt import ParagraphFormat
from docx.text.tabstops import TabStops

from ..unitutil.cxml import element, xml
from ..unitutil.mock import class_mock, instance_mock


class DescribeParagraphFormat:
    @pytest.mark.parametrize(
        ("p_cxml", "expected_value"),
        [
            ("w:p", None),
            ("w:p/w:pPr", None),
            ("w:p/w:pPr/w:outlineLvl{w:val=0}", 0),
            ("w:p/w:pPr/w:outlineLvl{w:val=5}", 5),
            ("w:p/w:pPr/w:outlineLvl{w:val=9}", 9),
        ],
    )
    def it_knows_its_outline_level(self, p_cxml, expected_value):
        paragraph_format = ParagraphFormat(element(p_cxml))
        assert paragraph_format.outline_level == expected_value

    @pytest.mark.parametrize(
        ("p_cxml", "value", "expected_p_cxml"),
        [
            ("w:p", 0, "w:p/w:pPr/w:outlineLvl{w:val=0}"),
            ("w:p/w:pPr", 3, "w:p/w:pPr/w:outlineLvl{w:val=3}"),
            ("w:p/w:pPr/w:outlineLvl{w:val=1}", 4, "w:p/w:pPr/w:outlineLvl{w:val=4}"),
            ("w:p/w:pPr/w:outlineLvl{w:val=1}", None, "w:p/w:pPr"),
        ],
    )
    def it_can_change_its_outline_level(self, p_cxml, value, expected_p_cxml):
        paragraph_format = ParagraphFormat(element(p_cxml))
        expected_xml = xml(expected_p_cxml)

        paragraph_format.outline_level = value

        assert paragraph_format._element.xml == expected_xml

    @pytest.mark.parametrize("value", [-1, 10, 42])
    def it_rejects_an_outline_level_outside_the_valid_range(self, value):
        paragraph_format = ParagraphFormat(element("w:p"))

        with pytest.raises(ValueError, match="must be in range 0 to 9"):
            paragraph_format.outline_level = value

    @pytest.mark.parametrize(
        ("p_cxml", "expected_value"),
        [
            ("w:p", None),
            ("w:p/w:pPr", None),
            ("w:p/w:pPr/w:shd{w:val=clear,w:fill=C0C0C0}", RGBColor(0xC0, 0xC0, 0xC0)),
            ("w:p/w:pPr/w:shd{w:val=clear,w:fill=auto}", "auto"),
            # -- a `w:shd` written before 2.0.0, with no `w:val`, still reads --
            ("w:p/w:pPr/w:shd{w:fill=C0C0C0}", RGBColor(0xC0, 0xC0, 0xC0)),
            # -- a pattern with no fill is valid and reports no fill rather than raising --
            ("w:p/w:pPr/w:shd{w:val=pct25,w:color=FF0000}", None),
        ],
    )
    def it_knows_its_shading_fill(self, p_cxml, expected_value):
        paragraph_format = ParagraphFormat(element(p_cxml))
        assert paragraph_format.shading_fill == expected_value

    @pytest.mark.parametrize(
        ("p_cxml", "value", "expected_p_cxml"),
        [
            # -- `w:val` is required by the schema; a fill alone is not a valid `w:shd` --
            (
                "w:p",
                RGBColor(0xC0, 0xC0, 0xC0),
                "w:p/w:pPr/w:shd{w:val=clear,w:fill=C0C0C0}",
            ),
            ("w:p", "#FF0000", "w:p/w:pPr/w:shd{w:val=clear,w:fill=FF0000}"),
            ("w:p/w:pPr/w:shd{w:val=clear,w:fill=C0C0C0}", None, "w:p/w:pPr"),
            # -- "auto" is half of the ST_HexColor union; readable but not assignable --
            ("w:p", "auto", "w:p/w:pPr/w:shd{w:val=clear,w:fill=auto}"),
            # -- an existing pattern is preserved, not overwritten with "clear" --
            (
                "w:p/w:pPr/w:shd{w:val=pct25}",
                "C0C0C0",
                "w:p/w:pPr/w:shd{w:val=pct25,w:fill=C0C0C0}",
            ),
        ],
    )
    def it_can_change_its_shading_fill(self, p_cxml, value, expected_p_cxml):
        paragraph_format = ParagraphFormat(element(p_cxml))
        expected_xml = xml(expected_p_cxml)

        paragraph_format.shading_fill = value

        assert paragraph_format._element.xml == expected_xml

    @pytest.mark.parametrize(
        ("p_cxml", "expected_value"),
        [
            ("w:p", None),
            ("w:p/w:pPr", None),
            ("w:p/w:pPr/w:shd{w:val=clear,w:fill=C0C0C0}", WD_SHADING_PATTERN.CLEAR),
            ("w:p/w:pPr/w:shd{w:val=pct25}", WD_SHADING_PATTERN.PCT_25),
            ("w:p/w:pPr/w:shd{w:fill=C0C0C0}", WD_SHADING_PATTERN.CLEAR),
        ],
    )
    def it_knows_its_shading_pattern(self, p_cxml, expected_value):
        paragraph_format = ParagraphFormat(element(p_cxml))
        assert paragraph_format.shading_pattern == expected_value

    @pytest.mark.parametrize(
        ("p_cxml", "value", "expected_p_cxml"),
        [
            ("w:p", WD_SHADING_PATTERN.PCT_25, "w:p/w:pPr/w:shd{w:val=pct25}"),
            ("w:p", WD_SHADING_PATTERN.CLEAR, "w:p/w:pPr/w:shd{w:val=clear}"),
            ("w:p/w:pPr/w:shd{w:val=pct25}", None, "w:p/w:pPr"),
        ],
    )
    def it_can_change_its_shading_pattern(self, p_cxml, value, expected_p_cxml):
        paragraph_format = ParagraphFormat(element(p_cxml))
        expected_xml = xml(expected_p_cxml)

        paragraph_format.shading_pattern = value

        assert paragraph_format._element.xml == expected_xml

    def it_can_change_its_shading_color(self):
        paragraph_format = ParagraphFormat(element("w:p/w:pPr/w:shd{w:val=pct25}"))

        paragraph_format.shading_color = "FF0000"

        assert paragraph_format._element.xml == xml(
            "w:p/w:pPr/w:shd{w:val=pct25,w:color=FF0000}"
        )

    def it_inserts_shading_in_schema_order(self):
        """`w:shd` must precede `w:spacing`, or Word rejects the document."""
        paragraph_format = ParagraphFormat(element("w:p/w:pPr/w:spacing{w:after=240}"))

        paragraph_format.shading_fill = "C0C0C0"

        assert paragraph_format._element.xml == xml(
            "w:p/w:pPr/(w:shd{w:val=clear,w:fill=C0C0C0},w:spacing{w:after=240})"
        )

    def it_knows_its_alignment_value(self, alignment_get_fixture):
        paragraph_format, expected_value = alignment_get_fixture
        assert paragraph_format.alignment == expected_value

    def it_can_change_its_alignment_value(self, alignment_set_fixture):
        paragraph_format, value, expected_xml = alignment_set_fixture
        paragraph_format.alignment = value
        assert paragraph_format._element.xml == expected_xml

    def it_knows_its_space_before(self, space_before_get_fixture):
        paragraph_format, expected_value = space_before_get_fixture
        assert paragraph_format.space_before == expected_value

    def it_can_change_its_space_before(self, space_before_set_fixture):
        paragraph_format, value, expected_xml = space_before_set_fixture
        paragraph_format.space_before = value
        assert paragraph_format._element.xml == expected_xml

    def it_knows_its_space_after(self, space_after_get_fixture):
        paragraph_format, expected_value = space_after_get_fixture
        assert paragraph_format.space_after == expected_value

    def it_can_change_its_space_after(self, space_after_set_fixture):
        paragraph_format, value, expected_xml = space_after_set_fixture
        paragraph_format.space_after = value
        assert paragraph_format._element.xml == expected_xml

    def it_knows_its_line_spacing(self, line_spacing_get_fixture):
        paragraph_format, expected_value = line_spacing_get_fixture
        assert paragraph_format.line_spacing == expected_value

    def it_can_change_its_line_spacing(self, line_spacing_set_fixture):
        paragraph_format, value, expected_xml = line_spacing_set_fixture
        paragraph_format.line_spacing = value
        assert paragraph_format._element.xml == expected_xml

    def it_knows_its_line_spacing_rule(self, line_spacing_rule_get_fixture):
        paragraph_format, expected_value = line_spacing_rule_get_fixture
        assert paragraph_format.line_spacing_rule == expected_value

    def it_can_change_its_line_spacing_rule(self, line_spacing_rule_set_fixture):
        paragraph_format, value, expected_xml = line_spacing_rule_set_fixture
        paragraph_format.line_spacing_rule = value
        assert paragraph_format._element.xml == expected_xml

    def it_knows_its_first_line_indent(self, first_indent_get_fixture):
        paragraph_format, expected_value = first_indent_get_fixture
        assert paragraph_format.first_line_indent == expected_value

    def it_can_change_its_first_line_indent(self, first_indent_set_fixture):
        paragraph_format, value, expected_xml = first_indent_set_fixture
        paragraph_format.first_line_indent = value
        assert paragraph_format._element.xml == expected_xml

    def it_knows_its_left_indent(self, left_indent_get_fixture):
        paragraph_format, expected_value = left_indent_get_fixture
        assert paragraph_format.left_indent == expected_value

    def it_can_change_its_left_indent(self, left_indent_set_fixture):
        paragraph_format, value, expected_xml = left_indent_set_fixture
        paragraph_format.left_indent = value
        assert paragraph_format._element.xml == expected_xml

    def it_knows_its_right_indent(self, right_indent_get_fixture):
        paragraph_format, expected_value = right_indent_get_fixture
        assert paragraph_format.right_indent == expected_value

    def it_can_change_its_right_indent(self, right_indent_set_fixture):
        paragraph_format, value, expected_xml = right_indent_set_fixture
        paragraph_format.right_indent = value
        assert paragraph_format._element.xml == expected_xml

    def it_knows_its_on_off_prop_values(self, on_off_get_fixture):
        paragraph_format, prop_name, expected_value = on_off_get_fixture
        assert getattr(paragraph_format, prop_name) == expected_value

    def it_can_change_its_on_off_props(self, on_off_set_fixture):
        paragraph_format, prop_name, value, expected_xml = on_off_set_fixture
        setattr(paragraph_format, prop_name, value)
        assert paragraph_format._element.xml == expected_xml

    def it_provides_access_to_its_tab_stops(self, tab_stops_fixture):
        paragraph_format, TabStops_, pPr, tab_stops_ = tab_stops_fixture
        tab_stops = paragraph_format.tab_stops
        TabStops_.assert_called_once_with(pPr)
        assert tab_stops is tab_stops_

    # fixtures -------------------------------------------------------

    @pytest.fixture(
        params=[
            ("w:p", None),
            ("w:p/w:pPr", None),
            ("w:p/w:pPr/w:jc{w:val=center}", WD_ALIGN_PARAGRAPH.CENTER),
        ]
    )
    def alignment_get_fixture(self, request):
        p_cxml, expected_value = request.param
        paragraph_format = ParagraphFormat(element(p_cxml))
        return paragraph_format, expected_value

    @pytest.fixture(
        params=[
            ("w:p", WD_ALIGN_PARAGRAPH.LEFT, "w:p/w:pPr/w:jc{w:val=left}"),
            ("w:p/w:pPr", WD_ALIGN_PARAGRAPH.CENTER, "w:p/w:pPr/w:jc{w:val=center}"),
            (
                "w:p/w:pPr/w:jc{w:val=center}",
                WD_ALIGN_PARAGRAPH.RIGHT,
                "w:p/w:pPr/w:jc{w:val=right}",
            ),
            ("w:p/w:pPr/w:jc{w:val=right}", None, "w:p/w:pPr"),
            ("w:p", None, "w:p/w:pPr"),
        ]
    )
    def alignment_set_fixture(self, request):
        p_cxml, value, expected_cxml = request.param
        paragraph_format = ParagraphFormat(element(p_cxml))
        expected_xml = xml(expected_cxml)
        return paragraph_format, value, expected_xml

    @pytest.fixture(
        params=[
            ("w:p", None),
            ("w:p/w:pPr", None),
            ("w:p/w:pPr/w:ind", None),
            ("w:p/w:pPr/w:ind{w:firstLine=240}", Pt(12)),
            ("w:p/w:pPr/w:ind{w:hanging=240}", Pt(-12)),
        ]
    )
    def first_indent_get_fixture(self, request):
        p_cxml, expected_value = request.param
        paragraph_format = ParagraphFormat(element(p_cxml))
        return paragraph_format, expected_value

    @pytest.fixture(
        params=[
            ("w:p", Pt(36), "w:p/w:pPr/w:ind{w:firstLine=720}"),
            ("w:p", Pt(-36), "w:p/w:pPr/w:ind{w:hanging=720}"),
            ("w:p", 0, "w:p/w:pPr/w:ind{w:firstLine=0}"),
            ("w:p", None, "w:p/w:pPr"),
            ("w:p/w:pPr/w:ind{w:firstLine=240}", None, "w:p/w:pPr/w:ind"),
            (
                "w:p/w:pPr/w:ind{w:firstLine=240}",
                Pt(-18),
                "w:p/w:pPr/w:ind{w:hanging=360}",
            ),
            (
                "w:p/w:pPr/w:ind{w:hanging=240}",
                Pt(18),
                "w:p/w:pPr/w:ind{w:firstLine=360}",
            ),
        ]
    )
    def first_indent_set_fixture(self, request):
        p_cxml, value, expected_p_cxml = request.param
        paragraph_format = ParagraphFormat(element(p_cxml))
        expected_xml = xml(expected_p_cxml)
        return paragraph_format, value, expected_xml

    @pytest.fixture(
        params=[
            ("w:p", None),
            ("w:p/w:pPr", None),
            ("w:p/w:pPr/w:ind", None),
            ("w:p/w:pPr/w:ind{w:left=120}", Pt(6)),
            ("w:p/w:pPr/w:ind{w:left=-06.3pt}", Pt(-6.3)),
        ]
    )
    def left_indent_get_fixture(self, request):
        p_cxml, expected_value = request.param
        paragraph_format = ParagraphFormat(element(p_cxml))
        return paragraph_format, expected_value

    @pytest.fixture(
        params=[
            ("w:p", Pt(36), "w:p/w:pPr/w:ind{w:left=720}"),
            ("w:p", Pt(-3), "w:p/w:pPr/w:ind{w:left=-60}"),
            ("w:p", 0, "w:p/w:pPr/w:ind{w:left=0}"),
            ("w:p", None, "w:p/w:pPr"),
            ("w:p/w:pPr/w:ind{w:left=240}", None, "w:p/w:pPr/w:ind"),
        ]
    )
    def left_indent_set_fixture(self, request):
        p_cxml, value, expected_p_cxml = request.param
        paragraph_format = ParagraphFormat(element(p_cxml))
        expected_xml = xml(expected_p_cxml)
        return paragraph_format, value, expected_xml

    @pytest.fixture(
        params=[
            ("w:p", None),
            ("w:p/w:pPr", None),
            ("w:p/w:pPr/w:spacing", None),
            ("w:p/w:pPr/w:spacing{w:line=420}", 1.75),
            ("w:p/w:pPr/w:spacing{w:line=840,w:lineRule=exact}", Pt(42)),
            ("w:p/w:pPr/w:spacing{w:line=840,w:lineRule=atLeast}", Pt(42)),
        ]
    )
    def line_spacing_get_fixture(self, request):
        p_cxml, expected_value = request.param
        paragraph_format = ParagraphFormat(element(p_cxml))
        return paragraph_format, expected_value

    @pytest.fixture(
        params=[
            ("w:p", 1, "w:p/w:pPr/w:spacing{w:line=240,w:lineRule=auto}"),
            ("w:p", 2.0, "w:p/w:pPr/w:spacing{w:line=480,w:lineRule=auto}"),
            ("w:p", Pt(42), "w:p/w:pPr/w:spacing{w:line=840,w:lineRule=exact}"),
            ("w:p/w:pPr", 2, "w:p/w:pPr/w:spacing{w:line=480,w:lineRule=auto}"),
            (
                "w:p/w:pPr/w:spacing{w:line=360}",
                1,
                "w:p/w:pPr/w:spacing{w:line=240,w:lineRule=auto}",
            ),
            (
                "w:p/w:pPr/w:spacing{w:line=240,w:lineRule=exact}",
                1.75,
                "w:p/w:pPr/w:spacing{w:line=420,w:lineRule=auto}",
            ),
            (
                "w:p/w:pPr/w:spacing{w:line=240,w:lineRule=atLeast}",
                Pt(42),
                "w:p/w:pPr/w:spacing{w:line=840,w:lineRule=atLeast}",
            ),
            (
                "w:p/w:pPr/w:spacing{w:line=240,w:lineRule=exact}",
                None,
                "w:p/w:pPr/w:spacing",
            ),
            ("w:p/w:pPr", None, "w:p/w:pPr"),
        ]
    )
    def line_spacing_set_fixture(self, request):
        p_cxml, value, expected_p_cxml = request.param
        paragraph_format = ParagraphFormat(element(p_cxml))
        expected_xml = xml(expected_p_cxml)
        return paragraph_format, value, expected_xml

    @pytest.fixture(
        params=[
            ("w:p", None),
            ("w:p/w:pPr", None),
            ("w:p/w:pPr/w:spacing", None),
            ("w:p/w:pPr/w:spacing{w:line=240}", WD_LINE_SPACING.SINGLE),
            ("w:p/w:pPr/w:spacing{w:line=360}", WD_LINE_SPACING.ONE_POINT_FIVE),
            ("w:p/w:pPr/w:spacing{w:line=480}", WD_LINE_SPACING.DOUBLE),
            ("w:p/w:pPr/w:spacing{w:line=420}", WD_LINE_SPACING.MULTIPLE),
            ("w:p/w:pPr/w:spacing{w:lineRule=auto}", WD_LINE_SPACING.MULTIPLE),
            ("w:p/w:pPr/w:spacing{w:lineRule=exact}", WD_LINE_SPACING.EXACTLY),
            ("w:p/w:pPr/w:spacing{w:lineRule=atLeast}", WD_LINE_SPACING.AT_LEAST),
        ]
    )
    def line_spacing_rule_get_fixture(self, request):
        p_cxml, expected_value = request.param
        paragraph_format = ParagraphFormat(element(p_cxml))
        return paragraph_format, expected_value

    @pytest.fixture(
        params=[
            (
                "w:p",
                WD_LINE_SPACING.SINGLE,
                "w:p/w:pPr/w:spacing{w:line=240,w:lineRule=auto}",
            ),
            (
                "w:p",
                WD_LINE_SPACING.ONE_POINT_FIVE,
                "w:p/w:pPr/w:spacing{w:line=360,w:lineRule=auto}",
            ),
            (
                "w:p",
                WD_LINE_SPACING.DOUBLE,
                "w:p/w:pPr/w:spacing{w:line=480,w:lineRule=auto}",
            ),
            ("w:p", WD_LINE_SPACING.MULTIPLE, "w:p/w:pPr/w:spacing{w:lineRule=auto}"),
            ("w:p", WD_LINE_SPACING.EXACTLY, "w:p/w:pPr/w:spacing{w:lineRule=exact}"),
            (
                "w:p/w:pPr/w:spacing{w:line=280,w:lineRule=exact}",
                WD_LINE_SPACING.AT_LEAST,
                "w:p/w:pPr/w:spacing{w:line=280,w:lineRule=atLeast}",
            ),
        ]
    )
    def line_spacing_rule_set_fixture(self, request):
        p_cxml, value, expected_p_cxml = request.param
        paragraph_format = ParagraphFormat(element(p_cxml))
        expected_xml = xml(expected_p_cxml)
        return paragraph_format, value, expected_xml

    @pytest.fixture(
        params=[
            ("w:p", "keep_together", None),
            ("w:p/w:pPr/w:keepLines{w:val=on}", "keep_together", True),
            ("w:p/w:pPr/w:keepLines{w:val=0}", "keep_together", False),
            ("w:p", "keep_with_next", None),
            ("w:p/w:pPr/w:keepNext{w:val=1}", "keep_with_next", True),
            ("w:p/w:pPr/w:keepNext{w:val=false}", "keep_with_next", False),
            ("w:p", "page_break_before", None),
            ("w:p/w:pPr/w:pageBreakBefore", "page_break_before", True),
            ("w:p/w:pPr/w:pageBreakBefore{w:val=0}", "page_break_before", False),
            ("w:p", "widow_control", None),
            ("w:p/w:pPr/w:widowControl{w:val=true}", "widow_control", True),
            ("w:p/w:pPr/w:widowControl{w:val=off}", "widow_control", False),
        ]
    )
    def on_off_get_fixture(self, request):
        p_cxml, prop_name, expected_value = request.param
        paragraph_format = ParagraphFormat(element(p_cxml))
        return paragraph_format, prop_name, expected_value

    @pytest.fixture(
        params=[
            ("w:p", "keep_together", True, "w:p/w:pPr/w:keepLines"),
            ("w:p", "keep_with_next", True, "w:p/w:pPr/w:keepNext"),
            ("w:p", "page_break_before", True, "w:p/w:pPr/w:pageBreakBefore"),
            ("w:p", "widow_control", True, "w:p/w:pPr/w:widowControl"),
            (
                "w:p/w:pPr/w:keepLines",
                "keep_together",
                False,
                "w:p/w:pPr/w:keepLines{w:val=0}",
            ),
            (
                "w:p/w:pPr/w:keepNext",
                "keep_with_next",
                False,
                "w:p/w:pPr/w:keepNext{w:val=0}",
            ),
            (
                "w:p/w:pPr/w:pageBreakBefore",
                "page_break_before",
                False,
                "w:p/w:pPr/w:pageBreakBefore{w:val=0}",
            ),
            (
                "w:p/w:pPr/w:widowControl",
                "widow_control",
                False,
                "w:p/w:pPr/w:widowControl{w:val=0}",
            ),
            ("w:p/w:pPr/w:keepLines{w:val=0}", "keep_together", None, "w:p/w:pPr"),
            ("w:p/w:pPr/w:keepNext{w:val=0}", "keep_with_next", None, "w:p/w:pPr"),
            (
                "w:p/w:pPr/w:pageBreakBefore{w:val=0}",
                "page_break_before",
                None,
                "w:p/w:pPr",
            ),
            ("w:p/w:pPr/w:widowControl{w:val=0}", "widow_control", None, "w:p/w:pPr"),
        ]
    )
    def on_off_set_fixture(self, request):
        p_cxml, prop_name, value, expected_cxml = request.param
        paragraph_format = ParagraphFormat(element(p_cxml))
        expected_xml = xml(expected_cxml)
        return paragraph_format, prop_name, value, expected_xml

    @pytest.fixture(
        params=[
            ("w:p", None),
            ("w:p/w:pPr", None),
            ("w:p/w:pPr/w:ind", None),
            ("w:p/w:pPr/w:ind{w:right=160}", Pt(8)),
            ("w:p/w:pPr/w:ind{w:right=-4.2pt}", Pt(-4.2)),
        ]
    )
    def right_indent_get_fixture(self, request):
        p_cxml, expected_value = request.param
        paragraph_format = ParagraphFormat(element(p_cxml))
        return paragraph_format, expected_value

    @pytest.fixture(
        params=[
            ("w:p", Pt(36), "w:p/w:pPr/w:ind{w:right=720}"),
            ("w:p", Pt(-3), "w:p/w:pPr/w:ind{w:right=-60}"),
            ("w:p", 0, "w:p/w:pPr/w:ind{w:right=0}"),
            ("w:p", None, "w:p/w:pPr"),
            ("w:p/w:pPr/w:ind{w:right=240}", None, "w:p/w:pPr/w:ind"),
        ]
    )
    def right_indent_set_fixture(self, request):
        p_cxml, value, expected_p_cxml = request.param
        paragraph_format = ParagraphFormat(element(p_cxml))
        expected_xml = xml(expected_p_cxml)
        return paragraph_format, value, expected_xml

    @pytest.fixture(
        params=[
            ("w:p", None),
            ("w:p/w:pPr", None),
            ("w:p/w:pPr/w:spacing", None),
            ("w:p/w:pPr/w:spacing{w:after=240}", Pt(12)),
        ]
    )
    def space_after_get_fixture(self, request):
        p_cxml, expected_value = request.param
        paragraph_format = ParagraphFormat(element(p_cxml))
        return paragraph_format, expected_value

    @pytest.fixture(
        params=[
            ("w:p", Pt(12), "w:p/w:pPr/w:spacing{w:after=240}"),
            ("w:p", None, "w:p/w:pPr"),
            ("w:p/w:pPr", Pt(12), "w:p/w:pPr/w:spacing{w:after=240}"),
            ("w:p/w:pPr", None, "w:p/w:pPr"),
            ("w:p/w:pPr/w:spacing", Pt(12), "w:p/w:pPr/w:spacing{w:after=240}"),
            ("w:p/w:pPr/w:spacing", None, "w:p/w:pPr/w:spacing"),
            (
                "w:p/w:pPr/w:spacing{w:after=240}",
                Pt(42),
                "w:p/w:pPr/w:spacing{w:after=840}",
            ),
            ("w:p/w:pPr/w:spacing{w:after=840}", None, "w:p/w:pPr/w:spacing"),
        ]
    )
    def space_after_set_fixture(self, request):
        p_cxml, value, expected_p_cxml = request.param
        paragraph_format = ParagraphFormat(element(p_cxml))
        expected_xml = xml(expected_p_cxml)
        return paragraph_format, value, expected_xml

    @pytest.fixture(
        params=[
            ("w:p", None),
            ("w:p/w:pPr", None),
            ("w:p/w:pPr/w:spacing", None),
            ("w:p/w:pPr/w:spacing{w:before=420}", Pt(21)),
        ]
    )
    def space_before_get_fixture(self, request):
        p_cxml, expected_value = request.param
        paragraph_format = ParagraphFormat(element(p_cxml))
        return paragraph_format, expected_value

    @pytest.fixture(
        params=[
            ("w:p", Pt(12), "w:p/w:pPr/w:spacing{w:before=240}"),
            ("w:p", None, "w:p/w:pPr"),
            ("w:p/w:pPr", Pt(12), "w:p/w:pPr/w:spacing{w:before=240}"),
            ("w:p/w:pPr", None, "w:p/w:pPr"),
            ("w:p/w:pPr/w:spacing", Pt(12), "w:p/w:pPr/w:spacing{w:before=240}"),
            ("w:p/w:pPr/w:spacing", None, "w:p/w:pPr/w:spacing"),
            (
                "w:p/w:pPr/w:spacing{w:before=240}",
                Pt(42),
                "w:p/w:pPr/w:spacing{w:before=840}",
            ),
            ("w:p/w:pPr/w:spacing{w:before=840}", None, "w:p/w:pPr/w:spacing"),
        ]
    )
    def space_before_set_fixture(self, request):
        p_cxml, value, expected_p_cxml = request.param
        paragraph_format = ParagraphFormat(element(p_cxml))
        expected_xml = xml(expected_p_cxml)
        return paragraph_format, value, expected_xml

    @pytest.fixture
    def tab_stops_fixture(self, TabStops_, tab_stops_):
        p = element("w:p/w:pPr")
        pPr = p.pPr
        paragraph_format = ParagraphFormat(p, None)
        return paragraph_format, TabStops_, pPr, tab_stops_

    # fixture components ---------------------------------------------

    @pytest.fixture
    def TabStops_(self, request, tab_stops_):
        return class_mock(request, "docx.text.parfmt.TabStops", return_value=tab_stops_)

    @pytest.fixture
    def tab_stops_(self, request):
        return instance_mock(request, TabStops)


class DescribeParagraphFormatCharacterUnits:
    """Unit-test suite for the character- and line-unit measures, issue #104."""

    @pytest.mark.parametrize(
        ("p_cxml", "expected_value"),
        [
            ("w:p", None),
            ("w:p/w:pPr", None),
            ("w:p/w:pPr/w:ind", None),
            ("w:p/w:pPr/w:ind{w:firstLineChars=200}", 200),
            ("w:p/w:pPr/w:ind{w:hangingChars=150}", -150),
        ],
    )
    def it_knows_its_first_line_indent_in_characters(self, p_cxml, expected_value):
        paragraph_format = ParagraphFormat(element(p_cxml))

        assert paragraph_format.first_line_indent_chars == expected_value

    @pytest.mark.parametrize(
        ("p_cxml", "value", "expected_cxml"),
        [
            ("w:p", 200, "w:p/w:pPr/w:ind{w:firstLineChars=200}"),
            ("w:p", -150, "w:p/w:pPr/w:ind{w:hangingChars=150}"),
            ("w:p/w:pPr/w:ind{w:firstLineChars=200}", None, "w:p/w:pPr/w:ind"),
            ("w:p", None, "w:p"),
        ],
    )
    def it_can_change_its_first_line_indent_in_characters(self, p_cxml, value, expected_cxml):
        paragraph_format = ParagraphFormat(element(p_cxml))

        paragraph_format.first_line_indent_chars = value

        assert paragraph_format._element.xml == xml(expected_cxml)

    def it_clears_the_twips_sibling_so_the_two_cannot_disagree(self):
        """Word prefers the `Chars` value; leaving both changes the layout silently."""
        paragraph_format = ParagraphFormat(element("w:p/w:pPr/w:ind{w:firstLine=720}"))

        paragraph_format.first_line_indent_chars = 200

        assert paragraph_format._element.xml == xml("w:p/w:pPr/w:ind{w:firstLineChars=200}")

    def and_setting_the_twips_value_clears_the_character_sibling(self):
        paragraph_format = ParagraphFormat(element("w:p/w:pPr/w:ind{w:firstLineChars=200}"))

        paragraph_format.first_line_indent = Pt(36)

        assert paragraph_format._element.xml == xml("w:p/w:pPr/w:ind{w:firstLine=720}")

    @pytest.mark.parametrize(
        ("p_cxml", "expected_value"),
        [
            ("w:p/w:pPr/w:ind{w:leftChars=100}", 100),
            ("w:p/w:pPr/w:ind{w:startChars=100}", 100),
            ("w:p/w:pPr/w:ind", None),
        ],
    )
    def it_reads_the_left_indent_in_characters_under_either_spelling(
        self, p_cxml, expected_value
    ):
        paragraph_format = ParagraphFormat(element(p_cxml))

        assert paragraph_format.left_indent_chars == expected_value

    @pytest.mark.parametrize(
        ("p_cxml", "expected_value"),
        [
            ("w:p/w:pPr/w:ind{w:left=720}", Pt(36)),
            ("w:p/w:pPr/w:ind{w:start=720}", Pt(36)),
        ],
    )
    def it_reads_the_left_indent_under_either_spelling(self, p_cxml, expected_value):
        """`w:start` is what Word writes in files saved by recent versions."""
        paragraph_format = ParagraphFormat(element(p_cxml))

        assert paragraph_format.left_indent == expected_value

    def it_reads_the_right_indent_under_either_spelling(self):
        paragraph_format = ParagraphFormat(element("w:p/w:pPr/w:ind{w:end=720}"))

        assert paragraph_format.right_indent == Pt(36)

    def it_can_get_and_set_the_line_unit_spacing(self):
        paragraph_format = ParagraphFormat(element("w:p"))

        assert paragraph_format.space_after_lines is None

        paragraph_format.space_after_lines = 50
        paragraph_format.space_before_lines = 100

        assert paragraph_format.space_after_lines == 50
        assert paragraph_format.space_before_lines == 100
        assert paragraph_format._element.xml == xml(
            "w:p/w:pPr/w:spacing{w:afterLines=50,w:beforeLines=100}"
        )


class DescribeParagraphFormatMarkFont:
    """Unit-test suite for `ParagraphFormat.mark_font`, issue #105."""

    def it_provides_access_to_the_paragraph_mark_run_properties(self):
        paragraph_format = ParagraphFormat(element("w:p"))

        paragraph_format.mark_font.size = Pt(8)

        assert paragraph_format._element.xml == xml("w:p/w:pPr/w:rPr/w:sz{w:val=16}")

    def it_inserts_the_rPr_in_schema_order(self):
        """`w:pPr/w:rPr` must precede `w:sectPr`."""
        paragraph_format = ParagraphFormat(element("w:p/w:pPr/w:sectPr"))

        paragraph_format.mark_font.bold = True

        assert paragraph_format._element.xml == xml("w:p/w:pPr/(w:rPr/w:b,w:sectPr)")

    def it_is_distinct_from_the_run_font(self):
        paragraph_format = ParagraphFormat(element("w:p/w:r/w:rPr/w:b"))

        assert paragraph_format.mark_font.bold is None


class DescribeParagraphFormatDirection:
    """Unit-test suite for `bidi` and `text_direction`, issue #108."""

    @pytest.mark.parametrize(
        ("p_cxml", "expected_value"),
        [
            ("w:p", None),
            ("w:p/w:pPr", None),
            ("w:p/w:pPr/w:bidi", True),
            ("w:p/w:pPr/w:bidi{w:val=0}", False),
        ],
    )
    def it_knows_its_base_direction(self, p_cxml, expected_value):
        paragraph_format = ParagraphFormat(element(p_cxml))

        assert paragraph_format.bidi == expected_value

    def it_inserts_bidi_in_schema_order(self):
        """`w:bidi` must precede `w:spacing`."""
        paragraph_format = ParagraphFormat(element("w:p/w:pPr/w:spacing{w:after=0}"))

        paragraph_format.bidi = True

        assert paragraph_format._element.xml == xml(
            "w:p/w:pPr/(w:bidi,w:spacing{w:after=0})"
        )

    def it_can_get_and_set_its_text_direction(self):
        from docx.enum.text import WD_TEXT_DIRECTION

        paragraph_format = ParagraphFormat(element("w:p/w:pPr/w:outlineLvl{w:val=0}"))

        paragraph_format.text_direction = WD_TEXT_DIRECTION.TB_RL

        assert paragraph_format.text_direction == WD_TEXT_DIRECTION.TB_RL
        # -- `w:textDirection` must precede `w:outlineLvl` --
        assert paragraph_format._element.xml == xml(
            "w:p/w:pPr/(w:textDirection{w:val=tbRl},w:outlineLvl{w:val=0})"
        )

    def but_it_writes_nothing_when_cleared_on_a_paragraph_without_a_pPr(self):
        paragraph_format = ParagraphFormat(element("w:p"))

        paragraph_format.bidi = None
        paragraph_format.text_direction = None

        assert paragraph_format._element.xml == xml("w:p")


class DescribeParagraphBorders:
    """Unit-test suite for `ParagraphFormat.borders`, issue #123."""

    def it_provides_access_to_each_paragraph_border_edge(self):
        paragraph_format = ParagraphFormat(element("w:p"))

        assert list(paragraph_format.borders) == [
            "top",
            "left",
            "bottom",
            "right",
            "between",
            "bar",
        ]

    def it_can_draw_a_horizontal_rule(self):
        from docx.enum.table import WD_LINE_STYLE

        paragraph_format = ParagraphFormat(element("w:p"))

        paragraph_format.borders["bottom"].line = WD_LINE_STYLE.SINGLE

        assert paragraph_format._element.xml == xml(
            "w:p/w:pPr/w:pBdr/w:bottom{w:val=single}"
        )

    def it_inserts_pBdr_in_schema_order(self):
        """`w:pBdr` must sit between `w:numPr` and `w:shd`."""
        from docx.enum.table import WD_LINE_STYLE

        paragraph_format = ParagraphFormat(element("w:p/w:pPr/w:shd{w:val=clear}"))

        paragraph_format.borders["top"].line = WD_LINE_STYLE.SINGLE

        assert paragraph_format._element.xml == xml(
            "w:p/w:pPr/(w:pBdr/w:top{w:val=single},w:shd{w:val=clear})"
        )

    def it_removes_the_pBdr_when_the_last_edge_goes(self):
        from docx.enum.table import WD_LINE_STYLE

        paragraph_format = ParagraphFormat(element("w:p"))
        paragraph_format.borders["bottom"].line = WD_LINE_STYLE.SINGLE

        paragraph_format.borders["bottom"].line = None

        assert paragraph_format._element.xml == xml("w:p/w:pPr")

    def it_rejects_an_edge_a_paragraph_does_not_admit(self):
        paragraph_format = ParagraphFormat(element("w:p"))

        with pytest.raises(KeyError, match="no border edge 'insideH'"):
            paragraph_format.borders["insideH"]
