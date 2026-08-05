"""What the bundled default template ships, and what it deliberately does not.

Pins the outcome of issues #113 and #117. The `.docx` and the unpacked
`default-docx-template/` directory are edited by hand and there is no build step
regenerating one from the other, so a test that they agree is what keeps them in step.
"""

from __future__ import annotations

import io
import pathlib
import zipfile

import pytest

import docx
from docx.enum.dml import MSO_THEME_COLOR
from docx.enum.style import WD_STYLE_TYPE

_TEMPLATE_DIR = pathlib.Path(docx.__file__).parent / "templates"
_DEFAULT_DOCX = _TEMPLATE_DIR / "default.docx"
_UNPACKED = _TEMPLATE_DIR / "default-docx-template"


class DescribeBundledTemplateContents:
    """Issue #113: three parts no generated document has any use for are gone."""

    @pytest.mark.parametrize(
        "member",
        [
            # -- the Word 2007 fallback copy of the styles part, 438 KB. Word 2013 and
            # -- later ignore it and do not write it.
            "word/stylesWithEffects.xml",
            # -- a rendered preview of the *template's* page, which file managers and
            # -- SharePoint would show as every generated document's thumbnail
            "docProps/thumbnail.jpeg",
            # -- an empty bibliography store from the template author's Word session,
            # -- which `Document.custom_xml_parts` would otherwise report
            "customXml/item1.xml",
            "customXml/itemProps1.xml",
            "customXml/_rels/item1.xml.rels",
        ],
    )
    def it_no_longer_ships(self, member: str):
        assert member not in zipfile.ZipFile(_DEFAULT_DOCX).namelist()

    def and_the_unpacked_template_agrees_with_the_docx(self):
        """The two are edited by hand; nothing regenerates one from the other."""
        packed = set(zipfile.ZipFile(_DEFAULT_DOCX).namelist())
        unpacked = {
            str(p.relative_to(_UNPACKED)).replace("\\", "/")
            for p in _UNPACKED.rglob("*")
            if p.is_file()
        }

        assert packed == unpacked

    def it_leaves_no_dangling_relationship_or_content_type(self):
        """Word repairs a package naming a part that is not there."""
        package = zipfile.ZipFile(_DEFAULT_DOCX)
        content_types = package.read("[Content_Types].xml").decode()
        package_rels = package.read("_rels/.rels").decode()
        document_rels = package.read("word/_rels/document.xml.rels").decode()

        for gone in ("stylesWithEffects", "thumbnail", "customXml"):
            assert gone not in content_types
            assert gone not in package_rels
            assert gone not in document_rels

    def it_produces_a_much_smaller_document(self):
        document = docx.Document()
        document.add_paragraph("hello")
        stream = io.BytesIO()
        document.save(stream)

        members = zipfile.ZipFile(io.BytesIO(stream.getvalue())).infolist()
        uncompressed = sum(i.file_size for i in members)

        # -- 826 KB before; the three removed parts were 447 KB of that --
        assert uncompressed < 450_000

    def and_a_generated_document_carries_no_custom_xml_store(self):
        assert docx.Document().custom_xml_parts == ()

    def and_it_still_opens_and_round_trips(self):
        document = docx.Document()
        document.add_heading("H", 1)
        document.add_paragraph("body")
        stream = io.BytesIO()
        document.save(stream)

        reopened = docx.Document(io.BytesIO(stream.getvalue()))

        assert [p.text for p in reopened.paragraphs] == ["H", "body"]
        assert reopened.paragraphs[0].style.name == "Heading 1"
        assert reopened.theme is not None


class DescribeBundledTemplateStyles:
    """Issue #117: three styles the library writes by name are now defined."""

    def it_defines_the_hyperlink_style(self):
        style = docx.Document().styles["Hyperlink"]

        assert style.type == WD_STYLE_TYPE.CHARACTER
        assert style.base_style.name == "Default Paragraph Font"
        assert style.font.underline is True
        # -- the real definition is theme-linked, not the hardcoded blue the library
        # -- used to synthesise --
        assert style.font.color.theme_color == MSO_THEME_COLOR.HYPERLINK

    @pytest.mark.parametrize(
        ("style_id", "style_type"),
        [
            ("CommentText", WD_STYLE_TYPE.PARAGRAPH),
            ("CommentTextChar", WD_STYLE_TYPE.CHARACTER),
            ("CommentReference", WD_STYLE_TYPE.CHARACTER),
        ],
    )
    def it_defines_the_comment_styles(self, style_id: str, style_type: WD_STYLE_TYPE):
        """Reached by id, which is what `Comment.add_paragraph()` writes. Their UI names
        differ from their internal ones ("annotation text"), as for every built-in whose
        two spellings diverge."""
        styles_elm = docx.Document().styles._element  # pyright: ignore[reportPrivateUsage]

        style = styles_elm.get_by_id(style_id)

        assert style is not None
        assert style.type == style_type

    def and_none_of_them_has_a_dangling_basedOn_or_link(self):
        styles_elm = docx.Document().styles._element  # pyright: ignore[reportPrivateUsage]

        for style_id in ("Hyperlink", "CommentText", "CommentTextChar", "CommentReference"):
            style = styles_elm.get_by_id(style_id)
            assert style is not None
            for referenced in (style.basedOn_val, style.link_val, style.next_val):
                if referenced is not None:
                    assert styles_elm.get_by_id(referenced) is not None, referenced

    def it_carries_no_rsid_from_the_document_they_were_lifted_from(self):
        """`w:rsid` records the editing session Word wrote the style in; it means
        nothing here and this library does not maintain rsids."""
        styles_xml = zipfile.ZipFile(_DEFAULT_DOCX).read("word/styles.xml").decode()

        assert 'w:rsid w:val="00530387"' not in styles_xml

    def it_applies_the_hyperlink_style_without_synthesising_one(self):
        document = docx.Document()
        before = len(document.styles)

        link = document.add_paragraph().add_hyperlink("x", "https://example.com/")

        assert link.runs[0].style.name == "Hyperlink"
        assert len(document.styles) == before

    def the_styles_only_default_part_defines_them_too(self):
        """`StylesPart.default()` serves a document opened without a styles part."""
        from docx.opc.package import OpcPackage
        from docx.parts.styles import StylesPart

        styles_elm = StylesPart.default(OpcPackage()).element

        for style_id in ("Hyperlink", "CommentText", "CommentTextChar", "CommentReference"):
            assert styles_elm.get_by_id(style_id) is not None
