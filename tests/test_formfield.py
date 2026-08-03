# pyright: reportPrivateUsage=false

"""Unit test suite for the docx.formfield module."""

from __future__ import annotations

from typing import cast

import pytest

from docx.enum.text import WD_FORM_FIELD_TYPE, WD_TEXT_FORM_FIELD_TYPE
from docx.exceptions import InvalidXmlError
from docx.formfield import FormField, iter_form_fields
from docx.oxml.ns import nsdecls
from docx.oxml.parser import parse_xml
from docx.oxml.text.form import CT_FldChar
from docx.oxml.text.paragraph import CT_P
from docx.parts.document import DocumentPart
from docx.text.paragraph import Paragraph

from .unitutil.cxml import element
from .unitutil.mock import FixtureRequest, Mock, instance_mock

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _p(inner_xml: str) -> CT_P:
    """A `w:p` element built from `inner_xml`, with the `w` namespace declared."""
    return cast(CT_P, parse_xml("<w:p %s>%s</w:p>" % (nsdecls("w"), inner_xml)))


TEXT_FIELD = """
  <w:r><w:fldChar w:fldCharType="begin"><w:ffData>
    <w:name w:val="Applicant"/>
    <w:enabled/>
    <w:calcOnExit w:val="0"/>
    <w:helpText w:val="Your full name"/>
    <w:statusText w:val="Name"/>
    <w:textInput>
      <w:type w:val="regular"/>
      <w:default w:val="Type your name"/>
      <w:maxLength w:val="30"/>
    </w:textInput>
  </w:ffData></w:fldChar></w:r>
  <w:r><w:instrText xml:space="preserve"> FORMTEXT </w:instrText></w:r>
  <w:r><w:fldChar w:fldCharType="separate"/></w:r>
  <w:r><w:rPr><w:b/></w:rPr><w:t>Alice</w:t></w:r>
  <w:r><w:fldChar w:fldCharType="end"/></w:r>
"""

CHECK_BOX_FIELD = """
  <w:r><w:fldChar w:fldCharType="begin"><w:ffData>
    <w:name w:val="Agreed"/>
    <w:checkBox><w:sizeAuto/><w:default w:val="0"/><w:checked/></w:checkBox>
  </w:ffData></w:fldChar></w:r>
  <w:r><w:instrText> FORMCHECKBOX </w:instrText></w:r>
  <w:r><w:fldChar w:fldCharType="end"/></w:r>
"""

DROP_DOWN_FIELD = """
  <w:r><w:fldChar w:fldCharType="begin"><w:ffData>
    <w:name w:val="Colour"/>
    <w:ddList>
      <w:result w:val="1"/>
      <w:default w:val="0"/>
      <w:listEntry w:val="Red"/>
      <w:listEntry w:val="Green"/>
      <w:listEntry w:val="Blue"/>
    </w:ddList>
  </w:ffData></w:fldChar></w:r>
  <w:r><w:instrText> FORMDROPDOWN </w:instrText></w:r>
  <w:r><w:fldChar w:fldCharType="separate"/></w:r>
  <w:r><w:t>Green</w:t></w:r>
  <w:r><w:fldChar w:fldCharType="end"/></w:r>
"""


class DescribeFormField:
    """Unit-test suite for `docx.formfield.FormField`."""

    @pytest.mark.parametrize(
        ("field_xml", "expected_value"),
        [
            (TEXT_FIELD, WD_FORM_FIELD_TYPE.TEXT),
            (CHECK_BOX_FIELD, WD_FORM_FIELD_TYPE.CHECK_BOX),
            (DROP_DOWN_FIELD, WD_FORM_FIELD_TYPE.DROP_DOWN),
        ],
    )
    def it_knows_what_kind_of_field_it_is(
        self, field_xml: str, expected_value: WD_FORM_FIELD_TYPE, parent_: Mock
    ):
        form_field = self._only_field(field_xml, parent_)

        assert form_field.type == expected_value

    def but_it_raises_when_the_ffData_says_nothing_about_the_kind(self, parent_: Mock):
        form_field = self._only_field(
            '<w:r><w:fldChar w:fldCharType="begin"><w:ffData/></w:fldChar></w:r>'
            '<w:r><w:fldChar w:fldCharType="end"/></w:r>',
            parent_,
        )

        with pytest.raises(InvalidXmlError, match="kind of form field"):
            form_field.type

    def it_knows_its_properties(self, parent_: Mock):
        form_field = self._only_field(TEXT_FIELD, parent_)

        assert form_field.name == "Applicant"
        assert form_field.enabled is True
        assert form_field.calc_on_exit is False
        assert form_field.help_text == "Your full name"
        assert form_field.status_text == "Name"
        assert form_field.max_length == 30
        assert form_field.text_type == WD_TEXT_FORM_FIELD_TYPE.REGULAR_TEXT

    def and_a_property_the_document_omits_is_None(self, parent_: Mock):
        form_field = self._only_field(CHECK_BOX_FIELD, parent_)

        assert form_field.enabled is None
        assert form_field.calc_on_exit is None
        assert form_field.help_text is None
        assert form_field.status_text is None
        # -- these two apply only to a text field --
        assert form_field.max_length is None
        assert form_field.text_type is None

    def it_can_change_its_properties(self, parent_: Mock):
        form_field = self._only_field(CHECK_BOX_FIELD, parent_)

        form_field.name = "Accepted"
        form_field.enabled = False
        form_field.calc_on_exit = True
        form_field.help_text = "Tick to accept"
        form_field.status_text = "Accept"

        assert form_field.name == "Accepted"
        assert form_field.enabled is False
        assert form_field.calc_on_exit is True
        assert form_field.help_text == "Tick to accept"
        assert form_field.status_text == "Accept"

    def and_assigning_None_removes_the_property_element(self, parent_: Mock):
        form_field = self._only_field(TEXT_FIELD, parent_)

        form_field.help_text = None

        assert form_field.help_text is None
        assert form_field._ffData.find("{%s}helpText" % _W) is None

    @pytest.mark.parametrize(
        ("prop_name", "value"),
        [("max_length", 5), ("text_type", WD_TEXT_FORM_FIELD_TYPE.DATE_TEXT)],
    )
    def it_raises_on_setting_a_text_only_property_of_another_kind_of_field(
        self, prop_name: str, value: object, parent_: Mock
    ):
        form_field = self._only_field(CHECK_BOX_FIELD, parent_)

        with pytest.raises(ValueError, match="applies only to a text form field"):
            setattr(form_field, prop_name, value)

    @pytest.mark.parametrize(
        ("field_xml", "expected_value"),
        [(TEXT_FIELD, "Alice"), (CHECK_BOX_FIELD, True), (DROP_DOWN_FIELD, "Green")],
    )
    def it_knows_its_value(self, field_xml: str, expected_value: object, parent_: Mock):
        form_field = self._only_field(field_xml, parent_)

        assert form_field.value == expected_value

    @pytest.mark.parametrize(
        ("field_xml", "expected_value"),
        [(TEXT_FIELD, "Type your name"), (CHECK_BOX_FIELD, False), (DROP_DOWN_FIELD, "Red")],
    )
    def it_knows_its_default(self, field_xml: str, expected_value: object, parent_: Mock):
        form_field = self._only_field(field_xml, parent_)

        assert form_field.default == expected_value

    def it_falls_back_to_the_default_when_no_value_is_recorded(self, parent_: Mock):
        # -- a check box Word has never rendered has `w:default` but no `w:checked` --
        form_field = self._only_field(
            '<w:r><w:fldChar w:fldCharType="begin"><w:ffData>'
            '<w:checkBox><w:default w:val="1"/></w:checkBox>'
            '</w:ffData></w:fldChar></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r>',
            parent_,
        )

        assert form_field.value is True

    def it_can_change_the_value_of_a_text_field(self, parent_: Mock):
        form_field = self._only_field(TEXT_FIELD, parent_)

        form_field.value = "Bob"

        assert form_field.value == "Bob"
        # -- the formatting of the run holding the value is kept --
        assert form_field._fldChar.getparent().getparent().xml.count("<w:b/>") == 1

    def and_it_adds_a_separate_field_character_when_the_field_has_none(self, parent_: Mock):
        form_field = self._only_field(
            '<w:r><w:rPr><w:i/></w:rPr><w:fldChar w:fldCharType="begin"><w:ffData>'
            "<w:textInput/></w:ffData></w:fldChar></w:r>"
            "<w:r><w:instrText> FORMTEXT </w:instrText></w:r>"
            '<w:r><w:fldChar w:fldCharType="end"/></w:r>',
            parent_,
        )

        form_field.value = "hello"

        p = form_field._fldChar.getparent().getparent()
        assert form_field.value == "hello"
        assert p.xml.count('w:fldCharType="separate"') == 1
        # -- the new value run inherits the formatting of the field --
        assert p.xml.count("<w:i/>") == 2

    def and_it_replaces_every_run_of_a_multi_run_value(self, parent_: Mock):
        form_field = self._only_field(
            '<w:r><w:fldChar w:fldCharType="begin"><w:ffData>'
            "<w:textInput/></w:ffData></w:fldChar></w:r>"
            '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
            "<w:r><w:t>one </w:t></w:r><w:r><w:t>two</w:t></w:r>"
            '<w:r><w:fldChar w:fldCharType="end"/></w:r>',
            parent_,
        )
        assert form_field.value == "one two"

        form_field.value = "three"

        assert form_field.value == "three"

    def it_can_change_the_value_of_a_check_box(self, parent_: Mock):
        form_field = self._only_field(CHECK_BOX_FIELD, parent_)

        form_field.value = False

        assert form_field.value is False

    def it_can_change_the_value_of_a_drop_down(self, parent_: Mock):
        form_field = self._only_field(DROP_DOWN_FIELD, parent_)

        form_field.value = "Blue"

        assert form_field.value == "Blue"
        # -- the rendered result follows the selection --
        assert form_field._result_text == "Blue"

    def but_it_raises_on_a_value_that_is_not_one_of_the_entries(self, parent_: Mock):
        form_field = self._only_field(DROP_DOWN_FIELD, parent_)

        with pytest.raises(ValueError, match="not one of the entries"):
            form_field.value = "Purple"

    def it_can_change_its_default(self, parent_: Mock):
        text_field = self._only_field(TEXT_FIELD, parent_)
        check_box = self._only_field(CHECK_BOX_FIELD, parent_)
        drop_down = self._only_field(DROP_DOWN_FIELD, parent_)

        text_field.default = "Anonymous"
        check_box.default = True
        drop_down.default = "Blue"

        assert text_field.default == "Anonymous"
        assert check_box.default is True
        assert drop_down.default == "Blue"

    def and_a_default_that_is_not_one_of_the_entries_raises(self, parent_: Mock):
        drop_down = self._only_field(DROP_DOWN_FIELD, parent_)

        with pytest.raises(ValueError, match="not one of the entries"):
            drop_down.default = "Purple"

        # -- and the existing default is left alone rather than silently cleared --
        assert drop_down.default == "Red"

    def but_None_clears_the_default(self, parent_: Mock):
        drop_down = self._only_field(DROP_DOWN_FIELD, parent_)

        drop_down.default = None

        assert drop_down.default is None

    @pytest.mark.parametrize(
        ("field_xml", "expected_value"),
        [
            (DROP_DOWN_FIELD, ("Red", "Green", "Blue")),
            # -- a field of another kind has no entries --
            (TEXT_FIELD, ()),
        ],
    )
    def it_knows_the_entries_of_a_drop_down(
        self, field_xml: str, expected_value: tuple[str, ...], parent_: Mock
    ):
        form_field = self._only_field(field_xml, parent_)

        assert form_field.items == expected_value

    def it_raises_when_its_field_is_never_ended(self, parent_: Mock):
        form_field = self._only_field(
            '<w:r><w:fldChar w:fldCharType="begin"><w:ffData>'
            "<w:textInput/></w:ffData></w:fldChar></w:r>",
            parent_,
        )

        with pytest.raises(InvalidXmlError, match="no `w:fldChar` of type 'end'"):
            form_field.value

    def it_skips_over_a_field_nested_in_its_value(self, parent_: Mock):
        p = _p(
            '<w:r><w:fldChar w:fldCharType="begin"><w:ffData>'
            "<w:textInput/></w:ffData></w:fldChar></w:r>"
            '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
            '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
            "<w:r><w:instrText> PAGE </w:instrText></w:r>"
            '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
            "<w:r><w:t>7</w:t></w:r>"
            '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
            '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
        )
        # -- the inner field has no `w:ffData`, so is not itself a form field --
        form_fields = list(iter_form_fields(p, parent_))

        assert len(form_fields) == 1
        assert form_fields[0].value == "7"

    # fixtures -------------------------------------------------------

    @staticmethod
    def _only_field(field_xml: str, parent: Mock) -> FormField:
        return list(iter_form_fields(_p(field_xml), parent))[0]

    @pytest.fixture
    def parent_(self, request: FixtureRequest):
        return instance_mock(request, DocumentPart)


class DescribeFormFieldDiscovery:
    """Unit-test suite for the `.form_fields` accessors."""

    def it_finds_the_form_fields_of_a_paragraph(self, parent_: Mock):
        paragraph = Paragraph(_p(TEXT_FIELD + CHECK_BOX_FIELD), parent_)

        form_fields = paragraph.form_fields

        assert [f.name for f in form_fields] == ["Applicant", "Agreed"]
        assert all(isinstance(f, FormField) for f in form_fields)

    def but_an_ordinary_field_is_not_a_form_field(self, parent_: Mock):
        paragraph = Paragraph(
            _p(
                '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
                "<w:r><w:instrText> PAGE </w:instrText></w:r>"
                '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
            ),
            parent_,
        )

        assert paragraph.form_fields == []

    # fixtures -------------------------------------------------------

    @pytest.fixture
    def parent_(self, request: FixtureRequest):
        return instance_mock(request, DocumentPart)


class DescribeCT_FldChar:
    """Unit-test suite for `docx.oxml.text.form.CT_FldChar`."""

    def it_knows_the_run_it_belongs_to(self):
        r = element("w:r/w:fldChar{w:fldCharType=begin}")
        fldChar = cast(CT_FldChar, r[0])

        assert fldChar.r is r

    def but_its_run_is_None_when_it_has_been_detached(self):
        fldChar = cast(CT_FldChar, element("w:fldChar{w:fldCharType=begin}"))

        assert fldChar.r is None
