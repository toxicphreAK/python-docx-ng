"""Unit test suite for the docx.theme module and the theme part."""

from __future__ import annotations

import pytest

import docx
from docx.oxml.ns import nsdecls
from docx.oxml.parser import parse_xml
from docx.parts.theme import ThemePart
from docx.shared import RGBColor
from docx.theme import Theme

from .unitutil.cxml import element

# -- a theme with an empty colour scheme and empty script slots, which is legal and is
# -- what a hand-authored or stripped-down theme part looks like --
_MINIMAL_THEME_XML = (
    '<a:theme %s>\n'
    "  <a:themeElements>\n"
    "    <a:clrScheme/>\n"
    "    <a:fontScheme>\n"
    "      <a:majorFont>\n"
    '        <a:latin typeface="X"/><a:ea typeface=""/><a:cs typeface=""/>\n'
    "      </a:majorFont>\n"
    "      <a:minorFont>\n"
    '        <a:latin typeface="Y"/><a:ea typeface=""/><a:cs typeface=""/>\n'
    "      </a:minorFont>\n"
    "    </a:fontScheme>\n"
    "  </a:themeElements>\n"
    "</a:theme>"
) % nsdecls("a")


class DescribeThemePart:
    """The theme part is loaded from the package rather than created on demand."""

    def it_is_reached_through_the_document(self):
        document = docx.Document()

        assert isinstance(document.theme, Theme)

    def it_is_typed_as_a_ThemePart_by_the_part_factory(self):
        document = docx.Document()

        theme_parts = [
            part for part in document.part.package.iter_parts() if isinstance(part, ThemePart)
        ]

        assert len(theme_parts) == 1

    def but_the_document_reports_None_when_there_is_no_theme_part(self):
        """A theme is a design a document was authored against, so it is never
        synthesised — an empty one would answer the typeface question with a fiction."""
        document = docx.Document()
        document_part = document.part
        rIds = [
            rId
            for rId, rel in document_part.rels.items()
            if rel.reltype.endswith("/theme")
        ]
        for rId in rIds:
            document_part.drop_rel(rId)

        assert document.theme is None


class DescribeTheme:
    """Unit-test suite for `docx.theme.Theme`."""

    def it_knows_its_name(self):
        assert docx.Document().theme.name == "Office Theme"

    def it_knows_its_major_and_minor_typefaces(self):
        theme = docx.Document().theme

        assert theme.minor_font.latin == "Cambria"
        assert theme.major_font.latin == "Calibri"

    def and_an_empty_typeface_slot_reads_as_None(self):
        """The default Office theme leaves `a:ea` and `a:cs` empty."""
        theme = docx.Document().theme

        assert theme.minor_font.east_asian is None
        assert theme.minor_font.complex_script is None

    @pytest.mark.parametrize(
        ("token", "expected_value"),
        [
            ("minorHAnsi", "Cambria"),
            ("minorAscii", "Cambria"),
            ("majorHAnsi", "Calibri"),
            ("majorAscii", "Calibri"),
            # -- the theme leaves these slots empty --
            ("minorEastAsia", None),
            ("majorBidi", None),
            # -- not a theme token at all --
            ("nonsense", None),
        ],
    )
    def it_resolves_a_theme_token_to_a_typeface(self, token: str, expected_value: str | None):
        assert docx.Document().theme.typeface(token) == expected_value

    def it_resolves_a_theme_color_to_an_rgb_value(self):
        theme = docx.Document().theme

        assert theme.color("accent1") == RGBColor(0x4F, 0x81, 0xBD)
        assert theme.color("hlink") == RGBColor(0x00, 0x00, 0xFF)

    def and_a_system_color_reports_the_value_it_was_last_resolved_to(self):
        """`a:dk1` is `a:sysClr val="windowText"`; `@lastClr` is the only concrete value."""
        assert docx.Document().theme.color("dk1") == RGBColor(0x00, 0x00, 0x00)

    def it_provides_all_twelve_colors_at_once(self):
        colors = docx.Document().theme.colors

        assert list(colors) == [
            "dk1",
            "lt1",
            "dk2",
            "lt2",
            "accent1",
            "accent2",
            "accent3",
            "accent4",
            "accent5",
            "accent6",
            "hlink",
            "folHlink",
        ]

    def it_rejects_a_color_slot_that_does_not_exist(self):
        with pytest.raises(ValueError, match="no theme color 'accent7'"):
            docx.Document().theme.color("accent7")

    def it_reports_None_for_a_color_slot_the_theme_omits(self):
        theme = Theme(parse_xml(_MINIMAL_THEME_XML))

        assert theme.color("accent1") is None

    def and_it_reports_None_for_an_empty_typeface_slot(self):
        theme = Theme(parse_xml(_MINIMAL_THEME_XML))

        assert theme.minor_font.latin == "Y"
        assert theme.minor_font.east_asian is None


class DescribeFontThemeTypeface:
    """Unit-test suite for `Font.theme_typeface`, the point of the theme part."""

    def it_resolves_the_runs_theme_token_to_a_real_typeface(self):
        document = docx.Document()
        run = document.add_paragraph().add_run("x")

        run.font.theme = "minorHAnsi"

        assert run.font.theme == "minorHAnsi"
        assert run.font.theme_typeface == "Cambria"

    def and_it_is_None_when_the_run_has_no_theme_token(self):
        document = docx.Document()
        run = document.add_paragraph().add_run("x")

        assert run.font.theme_typeface is None

    def and_it_is_None_for_a_font_with_no_part_behind_it(self):
        """`Font` is routinely built over a bare element in tests and by callers."""
        from docx.text.font import Font

        font = Font(element("w:r/w:rPr/w:rFonts{w:asciiTheme=minorHAnsi}"))

        assert font.theme == "minorHAnsi"
        assert font.theme_typeface is None
