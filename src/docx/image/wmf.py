"""Image header parser for WMF (Windows Metafile) images.

A bare WMF records only drawing commands in metafile units and says nothing about how
large the result should be. The physical size comes from the Aldus Placeable Metafile
header, a 22-byte prefix carrying a bounding box and the number of metafile units per
inch. Only a placeable WMF is recognized here, because a bare one gives us nothing to
size the picture with.
"""

from struct import Struct

from .constants import MIME_TYPE
from .exceptions import InvalidImageStreamError
from .image import BaseImageHeader

# -- the Aldus Placeable Metafile key, 0x9AC6CDD7 little-endian --
_APM_KEY = b"\xd7\xcd\xc6\x9a"

# -- Key(4) HWmf(2) BoundingBox(8) Inch(2) Reserved(4) Checksum(2) --
_APM_HEADER = Struct("<4sH4hHIH")
_APM_HEADER_LENGTH = _APM_HEADER.size

# -- WMF carries no device resolution, so a rendering resolution has to be assumed;
# -- 96 dpi is what Windows and Word use for metafiles. --
_WMF_DPI = 96


class Wmf(BaseImageHeader):
    """Image header parser for WMF images having an Aldus Placeable Metafile header."""

    @classmethod
    def from_stream(cls, stream):
        """Return a |Wmf| instance with header properties parsed from `stream`."""
        stream.seek(0)
        header = stream.read(_APM_HEADER_LENGTH)
        if len(header) < _APM_HEADER_LENGTH:
            raise InvalidImageStreamError("unexpected end of WMF image stream")

        key, _hwmf, left, top, right, bottom, inch, _reserved, _checksum = (
            _APM_HEADER.unpack(header)
        )
        if key != _APM_KEY:
            raise InvalidImageStreamError(
                "WMF image has no Aldus Placeable Metafile header, so its display size"
                " is unknown"
            )
        if inch == 0:
            raise InvalidImageStreamError(
                "WMF image declares zero metafile units per inch"
            )

        # -- the bounding box is in metafile units, `inch` of them to the inch --
        inch_width = abs(right - left) / inch
        inch_height = abs(bottom - top) / inch
        if inch_width == 0 or inch_height == 0:
            raise InvalidImageStreamError("WMF image has a zero-size bounding box")

        px_width = int(round(inch_width * _WMF_DPI))
        px_height = int(round(inch_height * _WMF_DPI))
        return cls(px_width, px_height, _WMF_DPI, _WMF_DPI)

    @property
    def content_type(self):
        """MIME content type for this image, unconditionally `image/x-wmf` for WMF
        images."""
        return MIME_TYPE.WMF

    @property
    def default_ext(self):
        """Default filename extension, always 'wmf' for WMF images."""
        return "wmf"
