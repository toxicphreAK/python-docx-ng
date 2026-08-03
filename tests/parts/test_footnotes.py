"""Unit test suite for the docx.parts.footnotes module."""

from __future__ import annotations

from typing import cast

import pytest

from docx.footnotes import Footnotes
from docx.opc.constants import CONTENT_TYPE as CT
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.packuri import PackURI
from docx.opc.part import PartFactory
from docx.oxml.footnotes import CT_Footnotes
from docx.package import Package
from docx.parts.footnotes import FootnotesPart

from ..unitutil.cxml import element
from ..unitutil.mock import FixtureRequest, Mock, class_mock, instance_mock, method_mock


class DescribeFootnotesPart:
    """Unit test suite for `docx.parts.footnotes.FootnotesPart` objects."""

    def it_is_used_by_the_part_loader_to_construct_a_footnotes_part(
        self, package_: Mock, FootnotesPart_load_: Mock, footnotes_part_: Mock
    ):
        partname = PackURI("/word/footnotes.xml")
        content_type = CT.WML_FOOTNOTES
        reltype = RT.FOOTNOTES
        blob = b"<w:footnotes/>"
        FootnotesPart_load_.return_value = footnotes_part_

        part = PartFactory(partname, content_type, reltype, blob, package_)

        FootnotesPart_load_.assert_called_once_with(partname, content_type, blob, package_)
        assert part is footnotes_part_

    def it_provides_access_to_its_footnotes_collection(
        self, Footnotes_: Mock, footnotes_: Mock, package_: Mock
    ):
        Footnotes_.return_value = footnotes_
        footnotes_elm = cast(CT_Footnotes, element("w:footnotes"))
        footnotes_part = FootnotesPart(
            PackURI("/word/footnotes.xml"), CT.WML_FOOTNOTES, footnotes_elm, package_
        )

        footnotes = footnotes_part.footnotes

        Footnotes_.assert_called_once_with(footnotes_part.element, footnotes_part)
        assert footnotes is footnotes_

    def it_can_construct_a_default_footnotes_part(self, package_: Mock):
        footnotes_part = FootnotesPart.default(package_)

        assert footnotes_part.partname == "/word/footnotes.xml"
        assert footnotes_part.content_type == CT.WML_FOOTNOTES
        # -- the default part holds Word's two separator footnotes and nothing else --
        assert len(footnotes_part.element.footnote_lst) == 2
        assert [f.id for f in footnotes_part.element.footnote_lst] == [-1, 0]
        assert all(f.is_structural for f in footnotes_part.element.footnote_lst)
        assert len(footnotes_part.footnotes) == 0

    # fixtures -------------------------------------------------------

    @pytest.fixture
    def Footnotes_(self, request: FixtureRequest):
        return class_mock(request, "docx.parts.footnotes.Footnotes")

    @pytest.fixture
    def footnotes_(self, request: FixtureRequest):
        return instance_mock(request, Footnotes)

    @pytest.fixture
    def FootnotesPart_load_(self, request: FixtureRequest):
        return method_mock(request, FootnotesPart, "load", autospec=False)

    @pytest.fixture
    def footnotes_part_(self, request: FixtureRequest):
        return instance_mock(request, FootnotesPart)

    @pytest.fixture
    def package_(self, request: FixtureRequest):
        return instance_mock(request, Package)
