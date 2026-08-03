# pyright: reportPrivateUsage=false

"""Test suite for the docx.text.run module."""

from __future__ import annotations

from typing import cast

import pytest
from _pytest.fixtures import FixtureRequest

from docx.dml.color import ColorFormat
from docx.enum.text import WD_COLOR, WD_COLOR_INDEX, WD_FONT_HINT, WD_UNDERLINE
from docx.oxml.text.run import CT_R
from docx.shared import Emu, Length, Pt, RGBColor
from docx.text.font import Font

from ..unitutil.cxml import element, xml
from ..unitutil.mock import Mock, class_mock, instance_mock


class DescribeFont:
    """Unit-test suite for `docx.text.font.Font`."""

    def it_provides_access_to_its_color_object(self, ColorFormat_: Mock, color_: Mock):
        r = cast(CT_R, element("w:r"))
        font = Font(r)

        color = font.color

        ColorFormat_.assert_called_once_with(font.element)
        assert color is color_

    @pytest.mark.parametrize(
        ("r_cxml", "expected_value"),
        [
            ("w:r", None),
            ("w:r/w:rPr", None),
            ("w:r/w:rPr/w:rFonts", None),
            ("w:r/w:rPr/w:rFonts{w:ascii=Arial}", "Arial"),
        ],
    )
    def it_knows_its_typeface_name(self, r_cxml: str, expected_value: str | None):
        r = cast(CT_R, element(r_cxml))
        font = Font(r)
        assert font.name == expected_value

    @pytest.mark.parametrize(
        ("r_cxml", "value", "expected_r_cxml"),
        [
            ("w:r", "Foo", "w:r/w:rPr/w:rFonts{w:ascii=Foo,w:hAnsi=Foo}"),
            ("w:r/w:rPr", "Foo", "w:r/w:rPr/w:rFonts{w:ascii=Foo,w:hAnsi=Foo}"),
            (
                "w:r/w:rPr/w:rFonts{w:hAnsi=Foo}",
                "Bar",
                "w:r/w:rPr/w:rFonts{w:ascii=Bar,w:hAnsi=Bar}",
            ),
            (
                "w:r/w:rPr/w:rFonts{w:ascii=Foo,w:hAnsi=Foo}",
                "Bar",
                "w:r/w:rPr/w:rFonts{w:ascii=Bar,w:hAnsi=Bar}",
            ),
        ],
    )
    def it_can_change_its_typeface_name(self, r_cxml: str, value: str, expected_r_cxml: str):
        r = cast(CT_R, element(r_cxml))
        font = Font(r)
        expected_xml = xml(expected_r_cxml)

        font.name = value

        assert font._element.xml == expected_xml

    @pytest.mark.parametrize(
        ("r_cxml", "expected_value"),
        [
            ("w:r", None),
            ("w:r/w:rPr", None),
            ("w:r/w:rPr/w:rFonts", None),
            ("w:r/w:rPr/w:rFonts{w:asciiTheme=minorHAnsi}", "minorHAnsi"),
        ],
    )
    def it_knows_its_theme_typeface(self, r_cxml: str, expected_value: str | None):
        font = Font(cast(CT_R, element(r_cxml)))
        assert font.theme == expected_value

    @pytest.mark.parametrize(
        ("r_cxml", "value", "expected_r_cxml"),
        [
            (
                "w:r",
                "majorHAnsi",
                "w:r/w:rPr/w:rFonts{w:asciiTheme=majorHAnsi,w:hAnsiTheme=majorHAnsi}",
            ),
            (
                "w:r/w:rPr/w:rFonts{w:asciiTheme=minorHAnsi,w:hAnsiTheme=minorHAnsi}",
                "majorHAnsi",
                "w:r/w:rPr/w:rFonts{w:asciiTheme=majorHAnsi,w:hAnsiTheme=majorHAnsi}",
            ),
        ],
    )
    def it_can_change_its_theme_typeface(
        self, r_cxml: str, value: str, expected_r_cxml: str
    ):
        font = Font(cast(CT_R, element(r_cxml)))
        expected_xml = xml(expected_r_cxml)

        font.theme = value

        assert font._element.xml == expected_xml

    @pytest.mark.parametrize(
        ("r_cxml", "expected_value"),
        [
            ("w:r", None),
            ("w:r/w:rPr", None),
            ("w:r/w:rPr/w:w{w:val=100}", 100),
            ("w:r/w:rPr/w:w{w:val=50}", 50),
        ],
    )
    def it_knows_its_character_scaling(self, r_cxml: str, expected_value: int | None):
        font = Font(cast(CT_R, element(r_cxml)))
        assert font.scaling == expected_value

    @pytest.mark.parametrize(
        ("r_cxml", "value", "expected_r_cxml"),
        [
            ("w:r", 200, "w:r/w:rPr/w:w{w:val=200}"),
            ("w:r/w:rPr", 50, "w:r/w:rPr/w:w{w:val=50}"),
            ("w:r/w:rPr/w:w{w:val=50}", 150, "w:r/w:rPr/w:w{w:val=150}"),
            ("w:r/w:rPr/w:w{w:val=50}", None, "w:r/w:rPr"),
        ],
    )
    def it_can_change_its_character_scaling(
        self, r_cxml: str, value: int | None, expected_r_cxml: str
    ):
        font = Font(cast(CT_R, element(r_cxml)))
        expected_xml = xml(expected_r_cxml)

        font.scaling = value

        assert font._element.xml == expected_xml

    @pytest.mark.parametrize("value", [0, 601, -5])
    def it_rejects_a_character_scaling_outside_the_valid_range(self, value: int):
        font = Font(cast(CT_R, element("w:r")))

        with pytest.raises(ValueError, match="must be in range 1 to 600"):
            font.scaling = value

    def it_inserts_character_scaling_in_schema_order(self):
        """`w:w` must precede `w:sz`, or Word rejects the document."""
        font = Font(cast(CT_R, element("w:r/w:rPr/w:sz{w:val=28}")))

        font.scaling = 150

        assert font._element.xml == xml("w:r/w:rPr/(w:w{w:val=150},w:sz{w:val=28})")

    @pytest.mark.parametrize(
        ("r_cxml", "expected_value"),
        [
            ("w:r", None),
            ("w:r/w:rPr", None),
            ("w:r/w:rPr/w:shd{w:fill=FF0000}", RGBColor(0xFF, 0x00, 0x00)),
            ("w:r/w:rPr/w:shd{w:fill=auto}", "auto"),
        ],
    )
    def it_knows_its_shading_fill(self, r_cxml: str, expected_value: object):
        font = Font(cast(CT_R, element(r_cxml)))
        assert font.shading_fill == expected_value

    @pytest.mark.parametrize(
        ("r_cxml", "value", "expected_r_cxml"),
        [
            ("w:r", RGBColor(0xFF, 0x00, 0x00), "w:r/w:rPr/w:shd{w:fill=FF0000}"),
            ("w:r", "00FF00", "w:r/w:rPr/w:shd{w:fill=00FF00}"),
            ("w:r", "#0000FF", "w:r/w:rPr/w:shd{w:fill=0000FF}"),
            ("w:r/w:rPr/w:shd{w:fill=FF0000}", None, "w:r/w:rPr"),
        ],
    )
    def it_can_change_its_shading_fill(
        self, r_cxml: str, value: object, expected_r_cxml: str
    ):
        font = Font(cast(CT_R, element(r_cxml)))
        expected_xml = xml(expected_r_cxml)

        font.shading_fill = value  # pyright: ignore[reportAttributeAccessIssue]

        assert font._element.xml == expected_xml

    def it_keeps_shading_and_highlighting_independent(self):
        """Both are valid at once; Word draws highlighting over shading."""
        font = Font(cast(CT_R, element("w:r")))

        font.shading_fill = "FF0000"
        font.highlight_color = WD_COLOR_INDEX.YELLOW

        assert font.shading_fill == RGBColor(0xFF, 0x00, 0x00)
        assert font.highlight_color == WD_COLOR_INDEX.YELLOW

    @pytest.mark.parametrize(
        ("r_cxml", "expected_value"),
        [
            ("w:r", None),
            ("w:r/w:rPr", None),
            ("w:r/w:rPr/w:sz{w:val=28}", Pt(14)),
            # -- a fractional half-point count is written by some non-Word generators --
            ("w:r/w:rPr/w:sz{w:val=21.5}", Emu(136525)),
            ("w:r/w:rPr/w:sz{w:val=21.3}", Emu(135255)),
        ],
    )
    def it_knows_its_size(self, r_cxml: str, expected_value: Length | None):
        r = cast(CT_R, element(r_cxml))
        font = Font(r)
        assert font.size == expected_value

    def it_rounds_a_fractional_half_point_size_to_the_nearest_half_point_on_write(self):
        """A half-point count is an integer in the schema, so writing rounds to one."""
        font = Font(cast(CT_R, element("w:r/w:rPr/w:sz{w:val=21.5}")))

        size = font.size
        font.size = size

        assert font._element.xml == xml("w:r/w:rPr/w:sz{w:val=22}")

    def it_round_trips_an_integral_half_point_size_unchanged(self):
        font = Font(cast(CT_R, element("w:r/w:rPr/w:sz{w:val=23}")))

        font.size = font.size

        assert font._element.xml == xml("w:r/w:rPr/w:sz{w:val=23}")

    @pytest.mark.parametrize(
        ("r_cxml", "value", "expected_r_cxml"),
        [
            ("w:r", Pt(12), "w:r/w:rPr/w:sz{w:val=24}"),
            ("w:r/w:rPr", Pt(12), "w:r/w:rPr/w:sz{w:val=24}"),
            ("w:r/w:rPr/w:sz{w:val=24}", Pt(18), "w:r/w:rPr/w:sz{w:val=36}"),
            ("w:r/w:rPr/w:sz{w:val=36}", None, "w:r/w:rPr"),
        ],
    )
    def it_can_change_its_size(self, r_cxml: str, value: Length | None, expected_r_cxml: str):
        r = cast(CT_R, element(r_cxml))
        font = Font(r)
        expected_xml = xml(expected_r_cxml)

        font.size = value

        assert font._element.xml == expected_xml

    @pytest.mark.parametrize(
        ("r_cxml", "bool_prop_name", "expected_value"),
        [
            ("w:r/w:rPr", "all_caps", None),
            ("w:r/w:rPr/w:caps", "all_caps", True),
            ("w:r/w:rPr/w:caps{w:val=on}", "all_caps", True),
            ("w:r/w:rPr/w:caps{w:val=off}", "all_caps", False),
            ("w:r/w:rPr/w:b{w:val=1}", "bold", True),
            ("w:r/w:rPr/w:i{w:val=0}", "italic", False),
            ("w:r/w:rPr/w:cs{w:val=true}", "complex_script", True),
            ("w:r/w:rPr/w:bCs{w:val=false}", "cs_bold", False),
            ("w:r/w:rPr/w:iCs{w:val=on}", "cs_italic", True),
            ("w:r/w:rPr/w:dstrike{w:val=off}", "double_strike", False),
            ("w:r/w:rPr/w:emboss{w:val=1}", "emboss", True),
            ("w:r/w:rPr/w:vanish{w:val=0}", "hidden", False),
            ("w:r/w:rPr/w:i{w:val=true}", "italic", True),
            ("w:r/w:rPr/w:imprint{w:val=false}", "imprint", False),
            ("w:r/w:rPr/w:oMath{w:val=on}", "math", True),
            ("w:r/w:rPr/w:noProof{w:val=off}", "no_proof", False),
            ("w:r/w:rPr/w:outline{w:val=1}", "outline", True),
            ("w:r/w:rPr/w:rtl{w:val=0}", "rtl", False),
            ("w:r/w:rPr/w:shadow{w:val=true}", "shadow", True),
            ("w:r/w:rPr/w:smallCaps{w:val=false}", "small_caps", False),
            ("w:r/w:rPr/w:snapToGrid{w:val=on}", "snap_to_grid", True),
            ("w:r/w:rPr/w:specVanish{w:val=off}", "spec_vanish", False),
            ("w:r/w:rPr/w:strike{w:val=1}", "strike", True),
            ("w:r/w:rPr/w:webHidden{w:val=0}", "web_hidden", False),
        ],
    )
    def it_knows_its_bool_prop_states(
        self, r_cxml: str, bool_prop_name: str, expected_value: bool | None
    ):
        r = cast(CT_R, element(r_cxml))
        font = Font(r)
        assert getattr(font, bool_prop_name) == expected_value

    @pytest.mark.parametrize(
        ("r_cxml", "prop_name", "value", "expected_cxml"),
        [
            # nothing to True, False, and None ---------------------------
            ("w:r", "all_caps", True, "w:r/w:rPr/w:caps"),
            ("w:r", "bold", False, "w:r/w:rPr/w:b{w:val=0}"),
            ("w:r", "italic", None, "w:r/w:rPr"),
            # default to True, False, and None ---------------------------
            ("w:r/w:rPr/w:cs", "complex_script", True, "w:r/w:rPr/w:cs"),
            ("w:r/w:rPr/w:bCs", "cs_bold", False, "w:r/w:rPr/w:bCs{w:val=0}"),
            ("w:r/w:rPr/w:iCs", "cs_italic", None, "w:r/w:rPr"),
            # True to True, False, and None ------------------------------
            (
                "w:r/w:rPr/w:dstrike{w:val=1}",
                "double_strike",
                True,
                "w:r/w:rPr/w:dstrike",
            ),
            (
                "w:r/w:rPr/w:emboss{w:val=on}",
                "emboss",
                False,
                "w:r/w:rPr/w:emboss{w:val=0}",
            ),
            ("w:r/w:rPr/w:vanish{w:val=1}", "hidden", None, "w:r/w:rPr"),
            # False to True, False, and None -----------------------------
            ("w:r/w:rPr/w:i{w:val=false}", "italic", True, "w:r/w:rPr/w:i"),
            (
                "w:r/w:rPr/w:imprint{w:val=0}",
                "imprint",
                False,
                "w:r/w:rPr/w:imprint{w:val=0}",
            ),
            ("w:r/w:rPr/w:oMath{w:val=off}", "math", None, "w:r/w:rPr"),
            # random mix -------------------------------------------------
            (
                "w:r/w:rPr/w:noProof{w:val=1}",
                "no_proof",
                False,
                "w:r/w:rPr/w:noProof{w:val=0}",
            ),
            ("w:r/w:rPr", "outline", True, "w:r/w:rPr/w:outline"),
            ("w:r/w:rPr/w:rtl{w:val=true}", "rtl", False, "w:r/w:rPr/w:rtl{w:val=0}"),
            ("w:r/w:rPr/w:shadow{w:val=on}", "shadow", True, "w:r/w:rPr/w:shadow"),
            (
                "w:r/w:rPr/w:smallCaps",
                "small_caps",
                False,
                "w:r/w:rPr/w:smallCaps{w:val=0}",
            ),
            ("w:r/w:rPr/w:snapToGrid", "snap_to_grid", True, "w:r/w:rPr/w:snapToGrid"),
            ("w:r/w:rPr/w:specVanish", "spec_vanish", None, "w:r/w:rPr"),
            ("w:r/w:rPr/w:strike{w:val=foo}", "strike", True, "w:r/w:rPr/w:strike"),
            (
                "w:r/w:rPr/w:webHidden",
                "web_hidden",
                False,
                "w:r/w:rPr/w:webHidden{w:val=0}",
            ),
        ],
    )
    def it_can_change_its_bool_prop_settings(
        self, r_cxml: str, prop_name: str, value: bool | None, expected_cxml: str
    ):
        r = cast(CT_R, element(r_cxml))
        font = Font(r)
        expected_xml = xml(expected_cxml)

        setattr(font, prop_name, value)

        assert font._element.xml == expected_xml

    @pytest.mark.parametrize(
        ("r_cxml", "expected_value"),
        [
            ("w:r", None),
            ("w:r/w:rPr", None),
            ("w:r/w:rPr/w:vertAlign{w:val=baseline}", False),
            ("w:r/w:rPr/w:vertAlign{w:val=subscript}", True),
            ("w:r/w:rPr/w:vertAlign{w:val=superscript}", False),
        ],
    )
    def it_knows_whether_it_is_subscript(self, r_cxml: str, expected_value: bool | None):
        r = cast(CT_R, element(r_cxml))
        font = Font(r)
        assert font.subscript == expected_value

    @pytest.mark.parametrize(
        ("r_cxml", "value", "expected_r_cxml"),
        [
            ("w:r", True, "w:r/w:rPr/w:vertAlign{w:val=subscript}"),
            ("w:r", False, "w:r/w:rPr"),
            ("w:r", None, "w:r/w:rPr"),
            (
                "w:r/w:rPr/w:vertAlign{w:val=subscript}",
                True,
                "w:r/w:rPr/w:vertAlign{w:val=subscript}",
            ),
            ("w:r/w:rPr/w:vertAlign{w:val=subscript}", False, "w:r/w:rPr"),
            ("w:r/w:rPr/w:vertAlign{w:val=subscript}", None, "w:r/w:rPr"),
            (
                "w:r/w:rPr/w:vertAlign{w:val=superscript}",
                True,
                "w:r/w:rPr/w:vertAlign{w:val=subscript}",
            ),
            (
                "w:r/w:rPr/w:vertAlign{w:val=superscript}",
                False,
                "w:r/w:rPr/w:vertAlign{w:val=superscript}",
            ),
            ("w:r/w:rPr/w:vertAlign{w:val=superscript}", None, "w:r/w:rPr"),
            (
                "w:r/w:rPr/w:vertAlign{w:val=baseline}",
                True,
                "w:r/w:rPr/w:vertAlign{w:val=subscript}",
            ),
        ],
    )
    def it_can_change_whether_it_is_subscript(
        self, r_cxml: str, value: bool | None, expected_r_cxml: str
    ):
        r = cast(CT_R, element(r_cxml))
        font = Font(r)
        expected_xml = xml(expected_r_cxml)

        font.subscript = value

        assert font._element.xml == expected_xml

    @pytest.mark.parametrize(
        ("r_cxml", "expected_value"),
        [
            ("w:r", None),
            ("w:r/w:rPr", None),
            ("w:r/w:rPr/w:vertAlign{w:val=baseline}", False),
            ("w:r/w:rPr/w:vertAlign{w:val=subscript}", False),
            ("w:r/w:rPr/w:vertAlign{w:val=superscript}", True),
        ],
    )
    def it_knows_whether_it_is_superscript(self, r_cxml: str, expected_value: bool | None):
        r = cast(CT_R, element(r_cxml))
        font = Font(r)
        assert font.superscript == expected_value

    @pytest.mark.parametrize(
        ("r_cxml", "value", "expected_r_cxml"),
        [
            ("w:r", True, "w:r/w:rPr/w:vertAlign{w:val=superscript}"),
            ("w:r", False, "w:r/w:rPr"),
            ("w:r", None, "w:r/w:rPr"),
            (
                "w:r/w:rPr/w:vertAlign{w:val=superscript}",
                True,
                "w:r/w:rPr/w:vertAlign{w:val=superscript}",
            ),
            ("w:r/w:rPr/w:vertAlign{w:val=superscript}", False, "w:r/w:rPr"),
            ("w:r/w:rPr/w:vertAlign{w:val=superscript}", None, "w:r/w:rPr"),
            (
                "w:r/w:rPr/w:vertAlign{w:val=subscript}",
                True,
                "w:r/w:rPr/w:vertAlign{w:val=superscript}",
            ),
            (
                "w:r/w:rPr/w:vertAlign{w:val=subscript}",
                False,
                "w:r/w:rPr/w:vertAlign{w:val=subscript}",
            ),
            ("w:r/w:rPr/w:vertAlign{w:val=subscript}", None, "w:r/w:rPr"),
            (
                "w:r/w:rPr/w:vertAlign{w:val=baseline}",
                True,
                "w:r/w:rPr/w:vertAlign{w:val=superscript}",
            ),
        ],
    )
    def it_can_change_whether_it_is_superscript(
        self, r_cxml: str, value: bool | None, expected_r_cxml: str
    ):
        r = cast(CT_R, element(r_cxml))
        font = Font(r)
        expected_xml = xml(expected_r_cxml)

        font.superscript = value

        assert font._element.xml == expected_xml

    @pytest.mark.parametrize(
        ("r_cxml", "expected_value"),
        [
            ("w:r", None),
            ("w:r/w:rPr/w:u", None),
            ("w:r/w:rPr/w:u{w:val=single}", True),
            ("w:r/w:rPr/w:u{w:val=none}", False),
            ("w:r/w:rPr/w:u{w:val=double}", WD_UNDERLINE.DOUBLE),
            ("w:r/w:rPr/w:u{w:val=wave}", WD_UNDERLINE.WAVY),
        ],
    )
    def it_knows_its_underline_type(self, r_cxml: str, expected_value: WD_UNDERLINE | bool | None):
        r = cast(CT_R, element(r_cxml))
        font = Font(r)
        assert font.underline is expected_value

    @pytest.mark.parametrize(
        ("r_cxml", "value", "expected_r_cxml"),
        [
            ("w:r", True, "w:r/w:rPr/w:u{w:val=single}"),
            ("w:r", False, "w:r/w:rPr/w:u{w:val=none}"),
            ("w:r", None, "w:r/w:rPr"),
            ("w:r", WD_UNDERLINE.SINGLE, "w:r/w:rPr/w:u{w:val=single}"),
            ("w:r", WD_UNDERLINE.THICK, "w:r/w:rPr/w:u{w:val=thick}"),
            ("w:r/w:rPr/w:u{w:val=single}", True, "w:r/w:rPr/w:u{w:val=single}"),
            ("w:r/w:rPr/w:u{w:val=single}", False, "w:r/w:rPr/w:u{w:val=none}"),
            ("w:r/w:rPr/w:u{w:val=single}", None, "w:r/w:rPr"),
            (
                "w:r/w:rPr/w:u{w:val=single}",
                WD_UNDERLINE.SINGLE,
                "w:r/w:rPr/w:u{w:val=single}",
            ),
            (
                "w:r/w:rPr/w:u{w:val=single}",
                WD_UNDERLINE.DOTTED,
                "w:r/w:rPr/w:u{w:val=dotted}",
            ),
        ],
    )
    def it_can_change_its_underline_type(
        self, r_cxml: str, value: bool | None, expected_r_cxml: str
    ):
        r = cast(CT_R, element(r_cxml))
        font = Font(r)
        expected_xml = xml(expected_r_cxml)

        font.underline = value

        assert font._element.xml == expected_xml

    @pytest.mark.parametrize(
        ("r_cxml", "expected_value"),
        [
            ("w:r", None),
            ("w:r/w:rPr", None),
            ("w:r/w:rPr/w:highlight{w:val=default}", WD_COLOR.AUTO),
            ("w:r/w:rPr/w:highlight{w:val=blue}", WD_COLOR.BLUE),
            ("w:r/w:rPr/w:highlight{w:val=none}", WD_COLOR.NO_HIGHLIGHT),
        ],
    )
    def it_knows_its_highlight_color(self, r_cxml: str, expected_value: WD_COLOR | None):
        r = cast(CT_R, element(r_cxml))
        font = Font(r)
        assert font.highlight_color is expected_value

    @pytest.mark.parametrize(
        ("r_cxml", "value", "expected_r_cxml"),
        [
            ("w:r", WD_COLOR.AUTO, "w:r/w:rPr/w:highlight{w:val=default}"),
            ("w:r/w:rPr", WD_COLOR.BRIGHT_GREEN, "w:r/w:rPr/w:highlight{w:val=green}"),
            (
                "w:r/w:rPr/w:highlight{w:val=green}",
                WD_COLOR.YELLOW,
                "w:r/w:rPr/w:highlight{w:val=yellow}",
            ),
            ("w:r/w:rPr/w:highlight{w:val=yellow}", None, "w:r/w:rPr"),
            ("w:r/w:rPr", None, "w:r/w:rPr"),
            ("w:r", None, "w:r/w:rPr"),
            (
                "w:r/w:rPr/w:highlight{w:val=yellow}",
                WD_COLOR.NO_HIGHLIGHT,
                "w:r/w:rPr/w:highlight{w:val=none}",
            ),
        ],
    )
    def it_can_change_its_highlight_color(
        self, r_cxml: str, value: WD_COLOR | None, expected_r_cxml: str
    ):
        r = cast(CT_R, element(r_cxml))
        font = Font(r)
        expected_xml = xml(expected_r_cxml)

        font.highlight_color = value

        assert font._element.xml == expected_xml

    def it_distinguishes_an_explicit_no_highlight_from_an_absent_one(self):
        """`w:val="none"` overrides an inherited highlight; absence inherits it."""
        explicit = Font(cast(CT_R, element("w:r/w:rPr/w:highlight{w:val=none}")))
        absent = Font(cast(CT_R, element("w:r/w:rPr")))

        assert explicit.highlight_color == WD_COLOR.NO_HIGHLIGHT
        assert absent.highlight_color is None

    # -- fixtures ----------------------------------------------------

    @pytest.fixture
    def color_(self, request: FixtureRequest):
        return instance_mock(request, ColorFormat)

    @pytest.fixture
    def ColorFormat_(self, request: FixtureRequest, color_: Mock):
        return class_mock(request, "docx.text.font.ColorFormat", return_value=color_)


class DescribeFontTypefaceSlots:
    """`w:rFonts` has four independent typeface slots, chosen between per character."""

    @pytest.mark.parametrize(
        ("r_cxml", "expected_name", "expected_east_asia", "expected_cs"),
        [
            ("w:r", None, None, None),
            ("w:r/w:rPr", None, None, None),
            ("w:r/w:rPr/w:rFonts{w:ascii=Calibri}", "Calibri", None, None),
            ("w:r/w:rPr/w:rFonts{w:eastAsia=SimSun}", None, "SimSun", None),
            ("w:r/w:rPr/w:rFonts{w:cs=Arial}", None, None, "Arial"),
            (
                "w:r/w:rPr/w:rFonts{w:ascii=Calibri,w:eastAsia=SimSun,w:cs=Arial}",
                "Calibri",
                "SimSun",
                "Arial",
            ),
        ],
    )
    def it_knows_the_typeface_of_each_slot(
        self,
        r_cxml: str,
        expected_name: str | None,
        expected_east_asia: str | None,
        expected_cs: str | None,
    ):
        """`.name` reports only the ASCII slot; it does not fall back to the others."""
        font = Font(cast(CT_R, element(r_cxml)))

        assert font.name == expected_name
        assert font.east_asia_name == expected_east_asia
        assert font.cs_name == expected_cs

    def it_writes_the_ascii_and_hAnsi_slots_together(self):
        """This is what Word does, and the two are almost never set independently."""
        font = Font(cast(CT_R, element("w:r")))

        font.name = "Calibri"

        assert font._element.xml == xml(
            "w:r/w:rPr/w:rFonts{w:ascii=Calibri,w:hAnsi=Calibri}"
        )

    @pytest.mark.parametrize(
        ("prop_name", "value", "expected_r_cxml"),
        [
            ("east_asia_name", "SimSun", "w:r/w:rPr/w:rFonts{w:eastAsia=SimSun}"),
            ("cs_name", "Arial", "w:r/w:rPr/w:rFonts{w:cs=Arial}"),
        ],
    )
    def it_can_set_a_slot_without_disturbing_the_others(
        self, prop_name: str, value: str, expected_r_cxml: str
    ):
        font = Font(cast(CT_R, element("w:r")))

        setattr(font, prop_name, value)

        assert font._element.xml == xml(expected_r_cxml)

    def it_round_trips_a_run_with_every_slot_set(self):
        r_cxml = (
            "w:r/w:rPr/w:rFonts{w:hint=eastAsia,w:ascii=Calibri,w:hAnsi=Calibri,"
            "w:eastAsia=SimSun,w:cs=Arial}"
        )
        font = Font(cast(CT_R, element(r_cxml)))

        font.name = font.name
        font.east_asia_name = font.east_asia_name
        font.cs_name = font.cs_name
        font.hint = font.hint

        assert font._element.xml == xml(r_cxml)

    @pytest.mark.parametrize(
        ("r_cxml", "expected_value"),
        [
            ("w:r", None),
            ("w:r/w:rPr/w:rFonts", None),
            ("w:r/w:rPr/w:rFonts{w:hint=default}", WD_FONT_HINT.DEFAULT),
            ("w:r/w:rPr/w:rFonts{w:hint=eastAsia}", WD_FONT_HINT.EAST_ASIA),
            ("w:r/w:rPr/w:rFonts{w:hint=cs}", WD_FONT_HINT.COMPLEX_SCRIPT),
        ],
    )
    def it_knows_its_font_hint(self, r_cxml: str, expected_value: WD_FONT_HINT | None):
        assert Font(cast(CT_R, element(r_cxml))).hint == expected_value

    def it_can_change_its_font_hint(self):
        font = Font(cast(CT_R, element("w:r/w:rPr/w:rFonts{w:eastAsia=SimSun}")))

        font.hint = WD_FONT_HINT.EAST_ASIA

        assert font._element.xml == xml(
            "w:r/w:rPr/w:rFonts{w:hint=eastAsia,w:eastAsia=SimSun}"
        )

    @pytest.mark.parametrize(
        ("r_cxml", "expected_value"),
        [
            ("w:r", None),
            ("w:r/w:rPr", None),
            ("w:r/w:rPr/w:szCs{w:val=28}", Pt(14)),
        ],
    )
    def it_knows_its_complex_script_size(self, r_cxml: str, expected_value: Length | None):
        """Word tracks the complex-script size separately, in `w:szCs`."""
        assert Font(cast(CT_R, element(r_cxml))).cs_size == expected_value

    @pytest.mark.parametrize(
        ("r_cxml", "value", "expected_r_cxml"),
        [
            ("w:r", Pt(12), "w:r/w:rPr/w:szCs{w:val=24}"),
            ("w:r/w:rPr/w:szCs{w:val=24}", Pt(18), "w:r/w:rPr/w:szCs{w:val=36}"),
            ("w:r/w:rPr/w:szCs{w:val=24}", None, "w:r/w:rPr"),
        ],
    )
    def it_can_change_its_complex_script_size(
        self, r_cxml: str, value: Length | None, expected_r_cxml: str
    ):
        font = Font(cast(CT_R, element(r_cxml)))

        font.cs_size = value

        assert font._element.xml == xml(expected_r_cxml)

    def it_keeps_the_two_sizes_independent(self):
        font = Font(cast(CT_R, element("w:r")))

        font.size = Pt(10)
        font.cs_size = Pt(14)

        assert font.size == Pt(10)
        assert font.cs_size == Pt(14)
        assert font._element.xml == xml(
            "w:r/w:rPr/(w:sz{w:val=20},w:szCs{w:val=28})"
        )
