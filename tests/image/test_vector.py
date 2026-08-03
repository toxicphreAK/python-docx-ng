"""Unit test suite for the vector image header parsers: SVG, EMF and WMF.

`frame-2x1in.emf` is a synthetic but valid EMF — an `EMR_HEADER` followed by an
`EMR_EOF` — describing a 2in x 1in picture recorded against a 1920x1080 / 508x286mm
device, which is 96 dpi. `file(1)` identifies it as an Enhanced Metafile. Building it
rather than converting one keeps the header values known exactly, which is the point of
the test.
"""

from __future__ import annotations

import io

import pytest

from docx.image.constants import MIME_TYPE
from docx.image.emf import Emf
from docx.image.exceptions import InvalidImageStreamError, UnrecognizedImageError
from docx.image.image import Image
from docx.image.svg import Svg
from docx.image.wmf import Wmf

from ..unitutil.file import test_file


class DescribeSvg:
    """Unit-test suite for `docx.image.svg.Svg`."""

    def it_knows_its_content_type_and_extension(self):
        svg = Svg(None, None, None, None)
        assert svg.content_type == MIME_TYPE.SVG
        assert svg.default_ext == "svg"

    @pytest.mark.parametrize(
        ("filename", "expected_inches"),
        [
            # -- absolute width and height, in points --
            ("python-logo.svg", (2.0, 1.0)),
            # -- percentage width and height: the size is only in the viewBox, which is
            # -- what an icon meant to scale to its container looks like --
            ("icon-viewbox.svg", (0.25, 0.25)),
            # -- physical units --
            ("metric.svg", (4 / 2.54, 2 / 2.54)),
        ],
    )
    def it_reads_the_display_size_from_the_root_element(
        self, filename: str, expected_inches: tuple[float, float]
    ):
        with open(test_file(filename), "rb") as stream:
            svg = Svg.from_stream(stream)

        # -- px is an integer, so the inch value carries at most half a pixel of
        # -- rounding, as it does for every other format here --
        assert svg.px_width / svg.horz_dpi == pytest.approx(expected_inches[0], abs=0.01)
        assert svg.px_height / svg.vert_dpi == pytest.approx(expected_inches[1], abs=0.01)

    def it_reports_96_dpi_because_a_user_unit_is_a_css_pixel(self):
        with open(test_file("python-logo.svg"), "rb") as stream:
            svg = Svg.from_stream(stream)

        assert (svg.horz_dpi, svg.vert_dpi) == (96, 96)

    @pytest.mark.parametrize(
        ("width", "height", "expected_px"),
        [
            ("96", "48", (96, 48)),  # -- bare number is a user unit --
            ("96px", "48px", (96, 48)),
            ("72pt", "36pt", (96, 48)),
            ("1in", "0.5in", (96, 48)),
            ("6pc", "3pc", (96, 48)),
            ("25.4mm", "12.7mm", (96, 48)),
        ],
    )
    def it_understands_the_absolute_css_length_units(
        self, width: str, height: str, expected_px: tuple[int, int]
    ):
        stream = _svg_stream('width="%s" height="%s"' % (width, height))

        svg = Svg.from_stream(stream)

        assert (svg.px_width, svg.px_height) == expected_px

    @pytest.mark.parametrize(
        "attrs",
        [
            # -- font-relative units cannot be resolved without a rendering context --
            'width="10em" height="5em" viewBox="0 0 96 48"',
            # -- a percentage is relative to a viewport this file does not have --
            'width="100%" height="100%" viewBox="0 0 96 48"',
            # -- no width or height at all --
            'viewBox="0 0 96 48"',
            # -- one absolute and one not --
            'width="96" viewBox="0 0 96 48"',
        ],
    )
    def it_falls_back_to_the_viewBox_for_a_length_it_cannot_resolve(self, attrs: str):
        svg = Svg.from_stream(_svg_stream(attrs))

        assert (svg.px_width, svg.px_height) == (96, 48)

    def it_raises_when_the_display_size_cannot_be_determined(self):
        with pytest.raises(InvalidImageStreamError, match="no absolute width and height"):
            Svg.from_stream(_svg_stream('width="100%" height="100%"'))

    def it_raises_on_xml_that_is_not_an_svg(self):
        stream = io.BytesIO(b'<?xml version="1.0"?><html xmlns="urn:x"><body/></html>')

        with pytest.raises(InvalidImageStreamError, match="expected an `svg` element"):
            Svg.from_stream(stream)

    def it_raises_on_malformed_xml(self):
        with pytest.raises(InvalidImageStreamError, match="not well-formed XML"):
            Svg.from_stream(io.BytesIO(b"<svg><unclosed>"))

    def it_does_not_resolve_external_entities(self):
        """An SVG arrives through the same door as any other image, from anywhere."""
        stream = io.BytesIO(
            b'<?xml version="1.0"?>'
            b'<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
            b'<svg xmlns="http://www.w3.org/2000/svg" width="96" height="48">'
            b"<desc>&xxe;</desc></svg>"
        )

        svg = Svg.from_stream(stream)

        assert (svg.px_width, svg.px_height) == (96, 48)

    @pytest.mark.parametrize(
        ("blob", "expected_value"),
        [
            (b'<svg xmlns="http://www.w3.org/2000/svg"/>', True),
            (b'<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg"/>', True),
            (b"<!-- a comment -->\n<svg/>", True),
            (b"<?xml version='1.0'?><!DOCTYPE svg><svg />", True),
            # -- an XHTML document that merely contains an inline SVG is not one --
            (b"<html><body><svg/></body></html>", False),
            (b'<?xml version="1.0"?><rss><channel/></rss>', False),
            (b"\x89PNG\x0d\x0a\x1a\x0a", False),
            (b"", False),
        ],
    )
    def it_sniffs_an_svg_root_element(self, blob: bytes, expected_value: bool):
        """SVG has no magic number, so detection is by finding the root element."""
        assert Svg.sniff(blob) is expected_value


class DescribeEmf:
    """Unit-test suite for `docx.image.emf.Emf`."""

    def it_knows_its_content_type_and_extension(self):
        emf = Emf(None, None, None, None)
        assert emf.content_type == MIME_TYPE.EMF
        assert emf.default_ext == "emf"

    def it_reads_the_picture_extent_from_the_header(self):
        with open(test_file("frame-2x1in.emf"), "rb") as stream:
            emf = Emf.from_stream(stream)

        assert (emf.px_width, emf.px_height) == (192, 96)
        assert emf.px_width / emf.horz_dpi == 2.0
        assert emf.px_height / emf.vert_dpi == 1.0

    def it_derives_the_resolution_from_the_reference_device(self):
        """Hardcoding a resolution scales the picture wrongly on insert."""
        with open(test_file("frame-2x1in.emf"), "rb") as stream:
            emf = Emf.from_stream(stream)

        # -- 1920 px over 508 mm is 96 dpi --
        assert (emf.horz_dpi, emf.vert_dpi) == (96, 96)

    def it_falls_back_to_96_dpi_when_the_device_has_no_physical_size(self):
        """Some writers leave szlMillimeters zeroed."""
        blob = bytearray(_emf_blob())
        blob[80:88] = (0).to_bytes(4, "little") + (0).to_bytes(4, "little")

        emf = Emf.from_stream(io.BytesIO(bytes(blob)))

        assert (emf.horz_dpi, emf.vert_dpi) == (96, 96)
        assert (emf.px_width, emf.px_height) == (192, 96)

    def it_raises_on_a_bad_signature(self):
        blob = bytearray(_emf_blob())
        blob[40:44] = b"NOPE"

        with pytest.raises(InvalidImageStreamError, match="invalid EMF signature"):
            Emf.from_stream(io.BytesIO(bytes(blob)))

    def it_raises_on_a_truncated_header(self):
        with pytest.raises(InvalidImageStreamError, match="unexpected end"):
            Emf.from_stream(io.BytesIO(_emf_blob()[:60]))

    def it_raises_on_a_zero_size_picture_frame(self):
        blob = bytearray(_emf_blob())
        blob[24:40] = b"\x00" * 16

        with pytest.raises(InvalidImageStreamError, match="zero-size picture frame"):
            Emf.from_stream(io.BytesIO(bytes(blob)))


class DescribeWmf:
    """Unit-test suite for `docx.image.wmf.Wmf`."""

    def it_knows_its_content_type_and_extension(self):
        wmf = Wmf(None, None, None, None)
        assert wmf.content_type == MIME_TYPE.WMF
        assert wmf.default_ext == "wmf"

    def it_reads_the_display_size_from_the_placeable_header(self):
        with open(test_file("CVS_LOGO.WMF"), "rb") as stream:
            wmf = Wmf.from_stream(stream)

        # -- a 1243x493 bounding box at 600 metafile units to the inch --
        assert wmf.px_width / wmf.horz_dpi == pytest.approx(1243 / 600, abs=0.01)
        assert wmf.px_height / wmf.vert_dpi == pytest.approx(493 / 600, abs=0.01)
        assert (wmf.horz_dpi, wmf.vert_dpi) == (96, 96)

    def it_refuses_a_wmf_without_a_placeable_header(self):
        """A bare WMF says nothing about how large the picture should be."""
        stream = io.BytesIO(b"\x01\x00\x09\x00" + b"\x00" * 32)

        with pytest.raises(InvalidImageStreamError, match="no Aldus Placeable"):
            Wmf.from_stream(stream)

    def it_raises_on_zero_metafile_units_per_inch(self):
        blob = bytearray(_wmf_blob())
        blob[14:16] = (0).to_bytes(2, "little")

        with pytest.raises(InvalidImageStreamError, match="zero metafile units"):
            Wmf.from_stream(io.BytesIO(bytes(blob)))

    def it_raises_on_a_truncated_header(self):
        with pytest.raises(InvalidImageStreamError, match="unexpected end"):
            Wmf.from_stream(io.BytesIO(_wmf_blob()[:10]))


class DescribeVectorImageDetection:
    """The formats must be recognized through the ordinary factory."""

    @pytest.mark.parametrize(
        ("filename", "expected_cls", "expected_content_type"),
        [
            ("python-logo.svg", Svg, MIME_TYPE.SVG),
            ("frame-2x1in.emf", Emf, MIME_TYPE.EMF),
            ("CVS_LOGO.WMF", Wmf, MIME_TYPE.WMF),
        ],
    )
    def it_recognizes_each_vector_format(
        self, filename: str, expected_cls: type, expected_content_type: str
    ):
        image = Image.from_file(test_file(filename))

        assert isinstance(image._image_header, expected_cls)
        assert image.content_type == expected_content_type

    def it_does_not_let_sniffing_shadow_a_signature_match(self):
        """A signature is exact; a sniffer is a guess, so it goes last."""
        image = Image.from_file(test_file("monty-truth.png"))

        assert image.content_type == MIME_TYPE.PNG

    def it_still_rejects_something_that_is_not_an_image(self):
        with pytest.raises(UnrecognizedImageError):
            Image.from_blob(b"this is not an image, nor is it XML")


def _svg_stream(root_attrs: str) -> io.BytesIO:
    """A one-element SVG document whose root carries `root_attrs`."""
    return io.BytesIO(
        ('<svg xmlns="http://www.w3.org/2000/svg" %s/>' % root_attrs).encode("utf-8")
    )


def _emf_blob() -> bytes:
    with open(test_file("frame-2x1in.emf"), "rb") as f:
        return f.read()


def _wmf_blob() -> bytes:
    with open(test_file("CVS_LOGO.WMF"), "rb") as f:
        return f.read()
