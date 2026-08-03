"""Image header parser for EMF (Enhanced Metafile) images.

An EMF file opens with an `EMR_HEADER` record whose `ENHMETAHEADER` structure carries
both the physical extent of the picture and the resolution of the device it was recorded
against. Both are needed: the extent alone says how large the picture is, and the device
resolution is what turns that into a pixel count that agrees with what Word shows.
"""

from struct import Struct

from .constants import MIME_TYPE
from .exceptions import InvalidImageStreamError
from .image import BaseImageHeader

# -- `dSignature` in the EMF header, "ENHMETA_SIGNATURE"; the bytes read " EMF" --
_EMF_SIGNATURE = b" EMF"

# -- offsets into ENHMETAHEADER --
_RCL_FRAME_OFFSET = 24  # -- picture extent in 0.01 mm units, as (left, top, right, bottom)
_SIGNATURE_OFFSET = 40
_SZL_DEVICE_OFFSET = 72  # -- reference device size in pixels, as (cx, cy)
_SZL_MILLIMETERS_OFFSET = 80  # -- reference device size in millimeters, as (cx, cy)
_HEADER_LENGTH = 88

# -- the resolution to assume when the header records a device of no physical size,
# -- which some writers leave zeroed. 96 is the Windows default. --
_FALLBACK_DPI = 96

_MM_PER_INCH = 25.4

_RECTL = Struct("<4l")
_SIZEL = Struct("<2l")


class Emf(BaseImageHeader):
    """Image header parser for EMF images."""

    @classmethod
    def from_stream(cls, stream):
        """Return an |Emf| instance with header properties parsed from `stream`."""
        header = cls._read_header(stream)
        horz_dpi, vert_dpi = cls._dpi_from_header(header)
        inch_width, inch_height = cls._extents_in_inches(header)
        px_width = int(round(inch_width * horz_dpi))
        px_height = int(round(inch_height * vert_dpi))
        return cls(px_width, px_height, horz_dpi, vert_dpi)

    @property
    def content_type(self):
        """MIME content type for this image, unconditionally `image/x-emf` for EMF
        images."""
        return MIME_TYPE.EMF

    @property
    def default_ext(self):
        """Default filename extension, always 'emf' for EMF images."""
        return "emf"

    @classmethod
    def _dpi_from_header(cls, header):
        """The resolution of the device this metafile was recorded against.

        Derived from the reference device size, which the header gives twice, once in
        pixels and once in millimeters. A header that records no physical size — some
        writers leave it zeroed — falls back to 96 dpi.
        """
        device_cx, device_cy = _SIZEL.unpack_from(header, _SZL_DEVICE_OFFSET)
        mm_cx, mm_cy = _SIZEL.unpack_from(header, _SZL_MILLIMETERS_OFFSET)

        def dpi(px: int, mm: int) -> int:
            if px <= 0 or mm <= 0:
                return _FALLBACK_DPI
            return int(round(px / (mm / _MM_PER_INCH)))

        return dpi(device_cx, mm_cx), dpi(device_cy, mm_cy)

    @classmethod
    def _extents_in_inches(cls, header):
        """The width and height of the picture, in inches.

        `rclFrame` is in units of 0.01 mm. It is inclusive of its bounds in principle but
        the difference is a hundredth of a millimeter, well below anything that matters
        at document scale.
        """
        left, top, right, bottom = _RECTL.unpack_from(header, _RCL_FRAME_OFFSET)
        mm_width = abs(right - left) / 100.0
        mm_height = abs(bottom - top) / 100.0
        if mm_width == 0 or mm_height == 0:
            raise InvalidImageStreamError("EMF image has a zero-size picture frame")
        return mm_width / _MM_PER_INCH, mm_height / _MM_PER_INCH

    @classmethod
    def _read_header(cls, stream):
        """The `ENHMETAHEADER` bytes at the start of `stream`."""
        stream.seek(0)
        header = stream.read(_HEADER_LENGTH)
        if len(header) < _HEADER_LENGTH:
            raise InvalidImageStreamError("unexpected end of EMF image stream")
        signature = header[_SIGNATURE_OFFSET : _SIGNATURE_OFFSET + 4]
        if signature != _EMF_SIGNATURE:
            raise InvalidImageStreamError(
                "invalid EMF signature %r, expected %r" % (signature, _EMF_SIGNATURE)
            )
        return header
