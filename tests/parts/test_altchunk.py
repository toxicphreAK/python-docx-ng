# pyright: reportPrivateUsage=false

"""Unit test suite for the docx.parts.altchunk module."""

from __future__ import annotations

import io

import pytest

from docx.opc.constants import CONTENT_TYPE as CT
from docx.opc.packuri import PackURI
from docx.package import Package
from docx.parts.altchunk import AltChunkPart

from ..unitutil.mock import FixtureRequest, Mock, instance_mock


class DescribeAltChunkPart:
    @pytest.mark.parametrize(
        ("content_type", "expected_partname"),
        [
            ("text/html", "/word/afchunk1.html"),
            ("text/plain", "/word/afchunk1.txt"),
            ("application/rtf", "/word/afchunk1.rtf"),
            ("application/xhtml+xml", "/word/afchunk1.xhtml"),
            ("message/rfc822", "/word/afchunk1.mht"),
            (CT.WML_DOCUMENT, "/word/afchunk1.docx"),
            # -- an unmapped content type still works; only the extension is generic --
            ("application/x-made-up", "/word/afchunk1.bin"),
        ],
    )
    def it_names_its_part_after_the_content_type(
        self, content_type: str, expected_partname: str, package_: Mock
    ):
        package_.iter_parts.return_value = iter([])

        alt_chunk_part = AltChunkPart.new(package_, b"chunk-bytes", content_type)

        assert alt_chunk_part.partname == expected_partname
        assert alt_chunk_part.content_type == content_type
        assert alt_chunk_part.blob == b"chunk-bytes"

    def it_numbers_its_part_without_regard_to_extension(
        self, request: FixtureRequest, package_: Mock
    ):
        existing = instance_mock(request, AltChunkPart, partname=PackURI("/word/afchunk1.html"))
        package_.iter_parts.return_value = iter([existing])

        alt_chunk_part = AltChunkPart.new(package_, b"x", "application/rtf")

        assert alt_chunk_part.partname == "/word/afchunk2.rtf"

    def it_can_be_created_from_a_stream(self, package_: Mock):
        package_.iter_parts.return_value = iter([])

        alt_chunk_part = AltChunkPart.new_from_stream(package_, io.BytesIO(b"<html/>"), "text/html")

        assert alt_chunk_part.blob == b"<html/>"

    def and_it_can_be_created_from_a_file_path(self, package_: Mock, tmp_path):
        package_.iter_parts.return_value = iter([])
        path = tmp_path / "chunk.html"
        path.write_bytes(b"<html/>")

        alt_chunk_part = AltChunkPart.new_from_stream(package_, str(path), "text/html")

        assert alt_chunk_part.blob == b"<html/>"

    # fixtures -------------------------------------------------------

    @pytest.fixture
    def package_(self, request: FixtureRequest):
        return instance_mock(request, Package)
