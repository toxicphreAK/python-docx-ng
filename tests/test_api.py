"""Test suite for the docx.api module."""

import io
import zipfile

import pytest

from docx.api import Document as DocumentFactoryFn
from docx.document import Document as DocumentCls
from docx.opc.constants import CONTENT_TYPE as CT

from .unitutil.file import test_file
from .unitutil.mock import FixtureRequest, Mock, class_mock, function_mock, instance_mock


class DescribeDocument:
    """Unit-test suite for `docx.api.Document` factory function."""

    def it_opens_a_docx_file(self, Package_: Mock, document_: Mock):
        document_part = Package_.open.return_value.main_document_part
        document_part.document = document_
        document_part.content_type = CT.WML_DOCUMENT_MAIN

        document = DocumentFactoryFn("foobar.docx")

        Package_.open.assert_called_once_with("foobar.docx")
        assert document is document_

    def it_opens_the_default_docx_if_none_specified(
        self, _default_docx_path_: Mock, Package_: Mock, document_: Mock
    ):
        _default_docx_path_.return_value = "default-document.docx"
        document_part = Package_.open.return_value.main_document_part
        document_part.document = document_
        document_part.content_type = CT.WML_DOCUMENT_MAIN

        document = DocumentFactoryFn()

        Package_.open.assert_called_once_with("default-document.docx")
        assert document is document_

    def it_opens_a_macro_enabled_docm_file(self, Package_: Mock, document_: Mock):
        document_part = Package_.open.return_value.main_document_part
        document_part.document = document_
        document_part.content_type = CT.WML_DOCUMENT_MACRO_ENABLED_MAIN

        document = DocumentFactoryFn("foobar.docm")

        Package_.open.assert_called_once_with("foobar.docm")
        assert document is document_

    def it_raises_on_not_a_Word_file(self, Package_: Mock):
        Package_.open.return_value.main_document_part.content_type = "BOGUS"

        with pytest.raises(ValueError, match="file 'foobar.xlsx' is not a Word file,"):
            DocumentFactoryFn("foobar.xlsx")

    # -- fixtures --------------------------------------------------------------------------------

    @pytest.fixture
    def _default_docx_path_(self, request: FixtureRequest):
        return function_mock(request, "docx.api._default_docx_path")

    @pytest.fixture
    def document_(self, request: FixtureRequest):
        return instance_mock(request, DocumentCls)

    @pytest.fixture
    def Package_(self, request: FixtureRequest):
        return class_mock(request, "docx.api.Package")


class DescribeMacroEnabledDocuments:
    """Integration-test suite for `.docm` support."""

    def it_can_open_and_edit_a_docm_file(self):
        document = DocumentFactoryFn(test_file("macro-enabled.docm"))

        document.add_paragraph("Hello")

        assert document.paragraphs[-1].text == "Hello"

    def it_preserves_the_macro_storage_when_saving(self):
        """The vbaProject part has no API but must survive a round trip intact."""
        document = DocumentFactoryFn(test_file("macro-enabled.docm"))
        with zipfile.ZipFile(test_file("macro-enabled.docm")) as z:
            original_vba = z.read("word/vbaProject.bin")

        stream = io.BytesIO()
        document.save(stream)

        with zipfile.ZipFile(stream) as z:
            assert z.read("word/vbaProject.bin") == original_vba

    def it_keeps_the_macro_enabled_content_type_when_saving(self):
        """Re-saving as a plain document content type would break macros in Word."""
        document = DocumentFactoryFn(test_file("macro-enabled.docm"))

        stream = io.BytesIO()
        document.save(stream)

        with zipfile.ZipFile(stream) as z:
            content_types = z.read("[Content_Types].xml").decode("utf-8")
        assert CT.WML_DOCUMENT_MACRO_ENABLED_MAIN in content_types
