# pyright: reportPrivateUsage=false

"""Unit test suite for the docx.oxml.sdt module."""

from __future__ import annotations

from typing import cast

import pytest

from docx.enum.text import WD_CONTENT_CONTROL_TYPE
from docx.oxml.sdt import CT_Sdt, iter_block_content, iter_run_content
from docx.oxml.xmlchemy import BaseOxmlElement

from ..unitutil.cxml import element


class DescribeBlockContentWalking:
    """Unit-test suite for `docx.oxml.sdt.iter_block_content`."""

    @pytest.mark.parametrize(
        ("body_cxml", "expected"),
        [
            ("w:body", []),
            ("w:body/(w:p,w:tbl)", ["p", "tbl"]),
            # -- the content of a block-level `w:sdt` appears in its place --
            ("w:body/(w:p,w:sdt/w:sdtContent/w:p,w:p)", ["p", "p", "p"]),
            ("w:body/w:sdt/w:sdtContent/w:tbl", ["tbl"]),
            # -- nesting is followed to any depth --
            (
                "w:body/w:sdt/w:sdtContent/w:sdt/w:sdtContent/(w:p,w:tbl)",
                ["p", "tbl"],
            ),
            # -- a control with no content contributes nothing rather than raising --
            ("w:body/(w:sdt,w:p)", ["p"]),
            ("w:body/(w:sdt/w:sdtPr,w:p)", ["p"]),
        ],
    )
    def it_looks_through_a_block_level_content_control(self, body_cxml: str, expected: list[str]):
        body = cast(BaseOxmlElement, element(body_cxml))

        actual = [e.tag.split("}")[1] for e in iter_block_content(body)]

        assert actual == expected

    @pytest.mark.parametrize(
        ("body_cxml", "expected"),
        [
            # -- `CT_CustomXmlBlock` wraps whole paragraphs and tables --
            ("w:body/w:customXml/w:p", ["p"]),
            ("w:body/(w:p,w:customXml/(w:p,w:tbl),w:p)", ["p", "p", "tbl", "p"]),
            # -- nesting, and composing with a content control --
            ("w:body/w:customXml/w:customXml/w:p", ["p"]),
            ("w:body/w:sdt/w:sdtContent/w:customXml/w:p", ["p"]),
            ("w:body/w:customXml/w:sdt/w:sdtContent/w:p", ["p"]),
            # -- an empty wrapper contributes nothing rather than raising --
            ("w:body/(w:customXml,w:p)", ["p"]),
        ],
    )
    def it_looks_through_a_block_level_custom_xml_wrapper(
        self, body_cxml: str, expected: list[str]
    ):
        """Skipping it would drop the paragraphs it wraps from the document entirely."""
        body = cast(BaseOxmlElement, element(body_cxml))

        actual = [e.tag.split("}")[1] for e in iter_block_content(body)]

        assert actual == expected

    def it_leaves_a_sectPr_and_other_non_content_children_out(self):
        body = cast(BaseOxmlElement, element("w:body/(w:p,w:sectPr)"))

        assert [e.tag.split("}")[1] for e in iter_block_content(body)] == ["p"]


class DescribeRunContentWalking:
    """Unit-test suite for `docx.oxml.sdt.iter_run_content`."""

    @pytest.mark.parametrize(
        ("p_cxml", "expected"),
        [
            ("w:p", []),
            ("w:p/(w:r,w:hyperlink)", ["r", "hyperlink"]),
            ("w:p/(w:r,w:sdt/w:sdtContent/(w:r,w:r),w:r)", ["r", "r", "r", "r"]),
            ("w:p/w:sdt/w:sdtContent/w:hyperlink", ["hyperlink"]),
            ("w:p/w:sdt/w:sdtContent/w:sdt/w:sdtContent/w:r", ["r"]),
            # -- `w:pPr` is not inner content --
            ("w:p/(w:pPr,w:r)", ["r"]),
        ],
    )
    def it_looks_through_a_run_level_content_control(self, p_cxml: str, expected: list[str]):
        p = cast(BaseOxmlElement, element(p_cxml))

        actual = [e.tag.split("}")[1] for e in iter_run_content(p)]

        assert actual == expected

    @pytest.mark.parametrize(
        ("p_cxml", "expected"),
        [
            # -- the runs Word wraps around a recognised date, name or place --
            ("w:p/(w:r,w:smartTag/w:r,w:r)", ["r", "r", "r"]),
            ("w:p/w:smartTag/(w:r,w:r)", ["r", "r"]),
            # -- Word does nest them --
            ("w:p/w:smartTag/w:smartTag/w:r", ["r"]),
            # -- `w:customXml` has the same shape --
            ("w:p/(w:r,w:customXml/w:r)", ["r", "r"]),
            ("w:p/w:customXml/w:smartTag/w:r", ["r"]),
            # -- a hyperlink inside one is still a hyperlink --
            ("w:p/w:smartTag/w:hyperlink", ["hyperlink"]),
            # -- composes with the wrappers already looked through --
            ("w:p/w:smartTag/w:sdt/w:sdtContent/w:r", ["r"]),
            ("w:p/w:smartTag/w:ins/w:r", ["r"]),
            # -- and a deletion inside one is still skipped --
            ("w:p/w:smartTag/w:del/w:r", []),
        ],
    )
    def it_looks_through_a_smart_tag_and_custom_xml_wrapper(
        self, p_cxml: str, expected: list[str]
    ):
        """`w:smartTag` and `w:customXml` are transparent; their runs are ordinary runs."""
        p = cast(BaseOxmlElement, element(p_cxml))

        actual = [e.tag.split("}")[1] for e in iter_run_content(p)]

        assert actual == expected


class DescribeCT_Sdt:
    """Unit-test suite for `docx.oxml.sdt.CT_Sdt`."""

    def it_knows_its_tag_and_alias(self):
        sdt = cast(
            CT_Sdt,
            element("w:sdt/w:sdtPr/(w:alias{w:val=Client name},w:tag{w:val=client})"),
        )

        assert sdt.alias_val == "Client name"
        assert sdt.tag_val == "client"

    def it_reports_none_for_a_property_the_control_does_not_carry(self):
        sdt = cast(CT_Sdt, element("w:sdt"))

        assert sdt.alias_val is None
        assert sdt.tag_val is None
        assert sdt.id_val is None
        assert sdt.content_control_type is None
        assert sdt.showing_placeholder is False
        assert sdt.text == ""

    def it_knows_its_id(self):
        sdt = cast(CT_Sdt, element("w:sdt/w:sdtPr/w:id{w:val=42}"))

        assert sdt.id_val == 42

    @pytest.mark.parametrize(
        ("sdtPr_child_cxml", "expected_value"),
        [
            ("w:text", WD_CONTENT_CONTROL_TYPE.TEXT),
            ("w:richText", WD_CONTENT_CONTROL_TYPE.RICH_TEXT),
            ("w:picture", WD_CONTENT_CONTROL_TYPE.PICTURE),
            ("w:comboBox", WD_CONTENT_CONTROL_TYPE.COMBO_BOX),
            ("w:dropDownList", WD_CONTENT_CONTROL_TYPE.DROPDOWN_LIST),
            ("w:date", WD_CONTENT_CONTROL_TYPE.DATE),
            ("w:group", WD_CONTENT_CONTROL_TYPE.GROUP),
            ("w:docPartObj", WD_CONTENT_CONTROL_TYPE.BUILDING_BLOCK_GALLERY),
            ("w:docPartList", WD_CONTENT_CONTROL_TYPE.BUILDING_BLOCK_GALLERY),
            # -- the check box is a Word 2010 extension, not part of the ISO schema --
            ("w14:checkbox", WD_CONTENT_CONTROL_TYPE.CHECKBOX),
            ("w15:repeatingSection", WD_CONTENT_CONTROL_TYPE.REPEATING_SECTION),
        ],
    )
    def it_knows_what_kind_of_control_it_is(
        self, sdtPr_child_cxml: str, expected_value: WD_CONTENT_CONTROL_TYPE
    ):
        sdt = cast(CT_Sdt, element("w:sdt/w:sdtPr/%s" % sdtPr_child_cxml))

        assert sdt.content_control_type == expected_value

    @pytest.mark.parametrize(
        ("showingPlcHdr_cxml", "expected_value"),
        [
            ("w:showingPlcHdr", True),
            ("w:showingPlcHdr{w:val=1}", True),
            ("w:showingPlcHdr{w:val=0}", False),
            ("w:showingPlcHdr{w:val=false}", False),
        ],
    )
    def it_knows_whether_it_is_showing_its_placeholder(
        self, showingPlcHdr_cxml: str, expected_value: bool
    ):
        """The text of such a control is the prompt, not a value the user entered."""
        sdt = cast(CT_Sdt, element("w:sdt/w:sdtPr/%s" % showingPlcHdr_cxml))

        assert sdt.showing_placeholder is expected_value

    def it_knows_the_text_of_its_block_level_content(self):
        sdt = cast(
            CT_Sdt,
            element('w:sdt/w:sdtContent/(w:p/w:r/w:t"one",w:p/w:r/w:t"two")'),
        )

        assert sdt.text == "one\ntwo"

    def it_knows_the_text_of_its_run_level_content(self):
        sdt = cast(CT_Sdt, element('w:sdt/w:sdtContent/(w:r/w:t"one",w:r/w:t"two")'))

        assert sdt.text == "onetwo"

    def it_includes_the_text_of_a_table_it_wraps(self):
        sdt = cast(
            CT_Sdt,
            element(
                "w:sdt/w:sdtContent/w:tbl/(w:tblPr,w:tblGrid/w:gridCol,"
                'w:tr/w:tc/w:p/w:r/w:t"celltext")'
            ),
        )

        assert sdt.text == "celltext"
