"""Unit test suite for docx.image.webp module."""

from __future__ import annotations

import io

import pytest

from docx.image.constants import MIME_TYPE
from docx.image.exceptions import InvalidImageStreamError
from docx.image.image import Image
from docx.image.webp import Webp

from ..unitutil.file import test_file


class DescribeWebp:
    def it_knows_its_content_type(self):
        webp = Webp(None, None, None, None)
        assert webp.content_type == MIME_TYPE.WEBP

    def it_knows_its_default_ext(self):
        webp = Webp(None, None, None, None)
        assert webp.default_ext == "webp"

    @pytest.mark.parametrize(
        ("filename", "expected_dimensions"),
        [
            # -- simple lossy, a bare VP8 key frame --
            ("webp-lossy.webp", (150, 214)),
            # -- lossless, dimensions packed as 14-bit fields --
            ("webp-lossless.webp", (24, 24)),
            # -- extended, the only variant that can carry alpha, animation or EXIF,
            # -- and what most encoders now emit --
            ("webp-extended.webp", (150, 214)),
        ],
    )
    def it_can_construct_from_each_container_variant(
        self, filename: str, expected_dimensions: tuple[int, int]
    ):
        with open(test_file(filename), "rb") as stream:
            webp = Webp.from_stream(stream)

        assert (webp.px_width, webp.px_height) == expected_dimensions

    def it_defaults_to_72_dpi_because_webp_carries_no_resolution(self):
        with open(test_file("webp-lossy.webp"), "rb") as stream:
            webp = Webp.from_stream(stream)

        assert (webp.horz_dpi, webp.vert_dpi) == (72, 72)

    def it_is_recognized_by_the_image_signature_matcher(self):
        """"WEBP" at offset 8 is what tells a WebP file from a WAV or an AVI."""
        image = Image.from_file(test_file("webp-lossless.webp"))

        assert isinstance(image._image_header, Webp)
        assert image.content_type == MIME_TYPE.WEBP
        assert image.ext == "webp"

    def it_raises_on_an_unrecognized_bitstream_chunk(self):
        stream = io.BytesIO(b"RIFF\x00\x00\x00\x00WEBPNOPE" + b"\x00" * 32)

        with pytest.raises(InvalidImageStreamError, match="unrecognized WebP bitstream"):
            Webp.from_stream(stream)

    def it_raises_on_a_malformed_lossy_key_frame(self):
        stream = io.BytesIO(b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 32)

        with pytest.raises(InvalidImageStreamError, match="start code"):
            Webp.from_stream(stream)

    def it_raises_on_a_malformed_lossless_signature(self):
        stream = io.BytesIO(b"RIFF\x00\x00\x00\x00WEBPVP8L" + b"\x00" * 32)

        with pytest.raises(InvalidImageStreamError, match="VP8L signature"):
            Webp.from_stream(stream)

    def it_raises_on_a_truncated_stream(self):
        stream = io.BytesIO(b"RIFF\x00\x00\x00\x00WEBPVP8X")

        with pytest.raises(InvalidImageStreamError, match="unexpected end"):
            Webp.from_stream(stream)
