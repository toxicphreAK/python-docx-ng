"""Image header parser for WebP images.

A WebP file is a RIFF container: `"RIFF"`, a four-byte file size, `"WEBP"`, and then a
chunk whose FourCC says which of the three bitstream variants follows. The image
dimensions live in a different place in each, which is the whole of the work here.

Word renders WebP natively from Microsoft 365 / Word 2021 onward. Earlier versions show
a placeholder instead, so a document that has to open in Word 2019 or earlier should
carry PNG or JPEG.
"""

from struct import Struct

from .constants import MIME_TYPE
from .exceptions import InvalidImageStreamError
from .image import BaseImageHeader

# -- WebP carries no resolution field, so dimensions are in pixels only. 72 is what the
# -- other resolution-free formats here assume. --
_WEBP_DPI = 72

_UINT16_LE = Struct("<H")
_UINT32_LE = Struct("<I")


class Webp(BaseImageHeader):
    """Image header parser for WebP images.

    Note that the WebP format carries no resolution (DPI) information. Both horizontal
    and vertical DPI default to 72.
    """

    @classmethod
    def from_stream(cls, stream):
        """Return |Webp| instance having header properties parsed from the WebP image in
        `stream`."""
        px_width, px_height = cls._dimensions_from_stream(stream)
        return cls(px_width, px_height, _WEBP_DPI, _WEBP_DPI)

    @property
    def content_type(self):
        """MIME content type for this image, unconditionally `image/webp` for WebP
        images."""
        return MIME_TYPE.WEBP

    @property
    def default_ext(self):
        """Default filename extension, always 'webp' for WebP images."""
        return "webp"

    @classmethod
    def _dimensions_from_stream(cls, stream):
        stream.seek(12)
        fourcc = stream.read(4)
        if fourcc == b"VP8 ":
            return cls._dimensions_from_lossy(stream)
        if fourcc == b"VP8L":
            return cls._dimensions_from_lossless(stream)
        if fourcc == b"VP8X":
            return cls._dimensions_from_extended(stream)
        raise InvalidImageStreamError(
            "unrecognized WebP bitstream chunk %r, expected 'VP8 ', 'VP8L' or 'VP8X'" % fourcc
        )

    @classmethod
    def _dimensions_from_extended(cls, stream):
        """Canvas dimensions of a `VP8X` (extended format) file.

        The chunk payload is one flags byte, three reserved bytes, then the canvas width
        and height each as a 24-bit little-endian value one less than the true size.
        This is what most encoders now emit, because it is the only variant that can
        carry alpha, animation, ICC profiles or EXIF.
        """
        stream.seek(24)
        payload = cls._read_exactly(stream, 6)
        width_minus_one = int.from_bytes(payload[:3], "little")
        height_minus_one = int.from_bytes(payload[3:], "little")
        return width_minus_one + 1, height_minus_one + 1

    @classmethod
    def _dimensions_from_lossless(cls, stream):
        """Dimensions of a `VP8L` (lossless) file.

        The payload opens with a one-byte signature followed by a 32-bit little-endian
        field packing the width and height as 14-bit values, each one less than the true
        size.
        """
        stream.seek(20)
        signature = cls._read_exactly(stream, 1)
        if signature != b"\x2f":
            raise InvalidImageStreamError(
                "invalid VP8L signature byte %r in WebP image" % signature
            )
        (bits,) = _UINT32_LE.unpack(cls._read_exactly(stream, 4))
        px_width = (bits & 0x3FFF) + 1
        px_height = ((bits >> 14) & 0x3FFF) + 1
        return px_width, px_height

    @classmethod
    def _dimensions_from_lossy(cls, stream):
        """Dimensions of a `VP8 ` (simple lossy) file.

        The payload is a VP8 key frame: a three-byte frame tag, the three-byte start
        code, then the width and height as 16-bit little-endian values whose top two
        bits are a scaling hint rather than part of the size.
        """
        stream.seek(23)
        start_code = cls._read_exactly(stream, 3)
        if start_code != b"\x9d\x01\x2a":
            raise InvalidImageStreamError(
                "invalid VP8 key-frame start code %r in WebP image" % start_code
            )
        (width_field,) = _UINT16_LE.unpack(cls._read_exactly(stream, 2))
        (height_field,) = _UINT16_LE.unpack(cls._read_exactly(stream, 2))
        return width_field & 0x3FFF, height_field & 0x3FFF

    @staticmethod
    def _read_exactly(stream, count):
        """`count` bytes read from `stream`, raising if the file ends first."""
        bytes_ = stream.read(count)
        if len(bytes_) != count:
            raise InvalidImageStreamError("unexpected end of WebP image stream")
        return bytes_
