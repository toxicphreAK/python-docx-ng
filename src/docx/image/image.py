"""Provides objects that can characterize image streams.

That characterization is as to content type and size, as a required step in including
them in a document.
"""

from __future__ import annotations

import hashlib
import io
import os
from typing import IO, Tuple

from docx.image.exceptions import UnrecognizedImageError
from docx.shared import Emu, Inches, Length, lazyproperty

#: The EXIF `Orientation` values that exchange the image's width and height — the two
#: quarter turns, and the two mirrored quarter turns.
_QUARTER_TURN_ORIENTATIONS = (5, 6, 7, 8)

#: DrawingML rotation, in 60000ths of a degree, and horizontal flip, for each EXIF
#: `Orientation`. A mirrored value is expressed as a flip plus a rotation, which is how
#: DrawingML spells one; there is no vertical-flip case, since flipping vertically is
#: flipping horizontally and turning 180 degrees.
_TRANSFORM_BY_ORIENTATION = {
    1: (0, False),
    2: (0, True),
    3: (180 * 60000, False),
    4: (180 * 60000, True),
    5: (270 * 60000, True),
    6: (90 * 60000, False),
    7: (90 * 60000, True),
    8: (270 * 60000, False),
}


class Image:
    """Graphical image stream such as JPEG, PNG, or GIF with properties and methods
    required by ImagePart."""

    def __init__(self, blob: bytes, filename: str, image_header: BaseImageHeader):
        super(Image, self).__init__()
        self._blob = blob
        self._filename = filename
        self._image_header = image_header

    @classmethod
    def from_blob(cls, blob: bytes) -> Image:
        """Return a new |Image| subclass instance parsed from the image binary contained
        in `blob`."""
        stream = io.BytesIO(blob)
        return cls._from_stream(stream, blob)

    @classmethod
    def from_file(cls, image_descriptor: str | IO[bytes]):
        """Return a new |Image| subclass instance loaded from the image file identified
        by `image_descriptor`, a path or file-like object."""
        if isinstance(image_descriptor, str):
            path = image_descriptor
            with open(path, "rb") as f:
                blob = f.read()
                stream = io.BytesIO(blob)
            filename = os.path.basename(path)
        else:
            stream = image_descriptor
            stream.seek(0)
            blob = stream.read()
            filename = None
        return cls._from_stream(stream, blob, filename)

    @property
    def blob(self):
        """The bytes of the image 'file'."""
        return self._blob

    @property
    def content_type(self) -> str:
        """MIME content type for this image, e.g. ``'image/jpeg'`` for a JPEG image."""
        return self._image_header.content_type

    @lazyproperty
    def ext(self):
        """The file extension for the image.

        If an actual one is available from a load filename it is used. Otherwise a
        canonical extension is assigned based on the content type. Does not contain the
        leading period, e.g. 'jpg', not '.jpg'.
        """
        return os.path.splitext(self._filename)[1][1:]

    @property
    def filename(self):
        """Original image file name, if loaded from disk, or a generic filename if
        loaded from an anonymous stream."""
        return self._filename

    @property
    def px_width(self) -> int:
        """The horizontal pixel dimension of the image."""
        return self._image_header.px_width

    @property
    def px_height(self) -> int:
        """The vertical pixel dimension of the image."""
        return self._image_header.px_height

    @property
    def horz_dpi(self) -> int:
        """Integer dots per inch for the width of this image.

        Defaults to 72 when not present in the file, as is often the case.
        """
        return self._image_header.horz_dpi

    @property
    def vert_dpi(self) -> int:
        """Integer dots per inch for the height of this image.

        Defaults to 72 when not present in the file, as is often the case.
        """
        return self._image_header.vert_dpi

    @property
    def orientation(self) -> int:
        """The EXIF `Orientation` of this image, 1 through 8.

        1 when the image declares none, which is every format but JPEG and TIFF and most
        files even of those. The eight values are: 1 normal, 2 mirrored, 3 rotated 180°,
        4 mirrored and 180°, 5 mirrored and 90° counter-clockwise, 6 rotated 90°
        clockwise, 7 mirrored and 90° clockwise, 8 rotated 90° counter-clockwise. 6 and
        8 are the common ones, and the two that exchange width and height.
        """
        return self._image_header.orientation

    @property
    def is_rotated(self) -> bool:
        """|True| when this image's EXIF orientation exchanges its width and height."""
        return self.orientation in _QUARTER_TURN_ORIENTATIONS

    @property
    def px_display_width(self) -> int:
        """Width in pixels *as displayed*, honouring the EXIF orientation.

        The same as :attr:`px_width` unless the orientation is a quarter turn, in which
        case the two are exchanged. This is the one to scale from: a portrait photo off
        a phone is stored landscape with an `Orientation` of 6, and computing a height
        from :attr:`px_width` gives an aspect ratio nothing will render at.
        """
        return self.px_height if self.is_rotated else self.px_width

    @property
    def px_display_height(self) -> int:
        """Height in pixels *as displayed*, honouring the EXIF orientation.

        See :attr:`px_display_width`.
        """
        return self.px_width if self.is_rotated else self.px_height

    @property
    def width(self) -> Inches:
        """A |Length| value representing the native width of the image, calculated from
        the values of `px_width` and `horz_dpi`.

        The *stored* width; see :attr:`display_width` for the width after the EXIF
        orientation is applied.
        """
        return Inches(self.px_width / self.horz_dpi)

    @property
    def height(self) -> Inches:
        """A |Length| value representing the native height of the image, calculated from
        the values of `px_height` and `vert_dpi`.

        The *stored* height; see :attr:`display_height`.
        """
        return Inches(self.px_height / self.vert_dpi)

    @property
    def display_width(self) -> Inches:
        """The native width of the image as displayed, honouring the EXIF orientation.

        The dpi values are exchanged along with the pixel counts, since a quarter turn
        takes the stored rows to the displayed columns.
        """
        if not self.is_rotated:
            return self.width
        return Inches(self.px_height / self.vert_dpi)

    @property
    def display_height(self) -> Inches:
        """The native height of the image as displayed, honouring the EXIF orientation."""
        if not self.is_rotated:
            return self.height
        return Inches(self.px_width / self.horz_dpi)

    @property
    def drawingml_transform(self) -> Tuple[int, bool]:
        """The (rotation, flip_h) pair expressing this image's EXIF orientation.

        Rotation is in 60000ths of a degree, the unit `a:xfrm/@rot` uses; `flip_h` maps
        to `@flipH`. `(0, False)` for an image that needs no transform.

        The rotation goes in the DrawingML rather than into the pixels: rotating the
        bytes would mean a JPEG decode/encode dependency this library does not have,
        would lose quality, and would break the sha1-based part deduplication in
        `package.py` that keeps one copy of an image used twice.
        """
        return _TRANSFORM_BY_ORIENTATION.get(self.orientation, (0, False))

    def scaled_dimensions(
        self,
        width: int | Length | None = None,
        height: int | Length | None = None,
        *,
        honor_exif_orientation: bool = True,
    ) -> Tuple[Length, Length]:
        """(cx, cy) pair representing scaled dimensions of this image.

        The native dimensions of the image are scaled by applying the following rules to
        the `width` and `height` arguments.

        * If both `width` and `height` are specified, the return value is (`width`,
        `height`); no scaling is performed.
        * If only one is specified, it is used to compute a scaling factor that is then
        applied to the unspecified dimension, preserving the aspect ratio of the image.
        * If both `width` and `height` are |None|, the native dimensions are returned.

        The native dimensions are calculated using the dots-per-inch (dpi) value
        embedded in the image, defaulting to 72 dpi if no value is specified, as is
        often the case. The returned values are both |Length| objects.

        The *display* dimensions are used, so a photo carrying an EXIF orientation that
        turns it a quarter is scaled to the aspect ratio it will be rendered at rather
        than the one its stored pixels have. Pass `honor_exif_orientation=False` for the
        stored dimensions — for an image whose pixels are already rotated *and* which
        carries the tag anyway, which some encoders produce and nothing can detect.
        """
        native_width = self.display_width if honor_exif_orientation else self.width
        native_height = self.display_height if honor_exif_orientation else self.height

        if width is None and height is None:
            return native_width, native_height

        if width is None:
            assert height is not None
            scaling_factor = float(height) / float(native_height)
            width = round(native_width * scaling_factor)

        if height is None:
            scaling_factor = float(width) / float(native_width)
            height = round(native_height * scaling_factor)

        return Emu(width), Emu(height)

    @lazyproperty
    def sha1(self):
        """SHA1 hash digest of the image blob."""
        return hashlib.sha1(self._blob).hexdigest()

    @classmethod
    def _from_stream(
        cls,
        stream: IO[bytes],
        blob: bytes,
        filename: str | None = None,
    ) -> Image:
        """Return an instance of the |Image| subclass corresponding to the format of the
        image in `stream`."""
        image_header = _ImageHeaderFactory(stream)
        if filename is None:
            filename = "image.%s" % image_header.default_ext
        return cls(blob, filename, image_header)


def _ImageHeaderFactory(stream: IO[bytes]):
    """A |BaseImageHeader| subclass instance that can parse headers of image in `stream`.

    Most formats are identified by a magic number at a fixed offset. A format that has
    no such number — SVG, being XML — is identified by a sniffer function instead, and
    only after every signature has failed to match, so sniffing can never shadow an
    exact identification.
    """
    from docx.image import SIGNATURES, SNIFFERS

    stream.seek(0)
    header = stream.read(_HEADER_SAMPLE_LENGTH)

    for cls, offset, signature_bytes in SIGNATURES:
        end = offset + len(signature_bytes)
        if header[offset:end] == signature_bytes:
            return cls.from_stream(stream)

    for cls, sniff in SNIFFERS:
        if sniff(header):
            return cls.from_stream(stream)

    raise UnrecognizedImageError


# -- how much of a file to sample for format detection. A signature match needs only the
# -- first 44 bytes, but a sniffer may have to look past an XML declaration, a DOCTYPE
# -- and comments to find the root element. --
_HEADER_SAMPLE_LENGTH = 4096


class BaseImageHeader:
    """Base class for image header subclasses like |Jpeg| and |Tiff|."""

    def __init__(
        self,
        px_width: int,
        px_height: int,
        horz_dpi: int,
        vert_dpi: int,
        orientation: int = 1,
    ):
        self._px_width = px_width
        self._px_height = px_height
        self._horz_dpi = horz_dpi
        self._vert_dpi = vert_dpi
        self._orientation = orientation

    @property
    def orientation(self) -> int:
        """The EXIF `Orientation` of this image, 1 through 8; 1 when it declares none.

        Only JPEG and TIFF carry the tag; every other format reports 1.
        """
        return self._orientation

    @property
    def content_type(self) -> str:
        """Abstract property definition, must be implemented by all subclasses."""
        msg = "content_type property must be implemented by all subclasses of BaseImageHeader"
        raise NotImplementedError(msg)

    @property
    def default_ext(self) -> str:
        """Default filename extension for images of this type.

        An abstract property definition, must be implemented by all subclasses.
        """
        raise NotImplementedError(
            "default_ext property must be implemented by all subclasses of BaseImageHeader"
        )

    @property
    def px_width(self):
        """The horizontal pixel dimension of the image."""
        return self._px_width

    @property
    def px_height(self):
        """The vertical pixel dimension of the image."""
        return self._px_height

    @property
    def horz_dpi(self):
        """Integer dots per inch for the width of this image.

        Defaults to 72 when not present in the file, as is often the case.
        """
        return self._horz_dpi

    @property
    def vert_dpi(self):
        """Integer dots per inch for the height of this image.

        Defaults to 72 when not present in the file, as is often the case.
        """
        return self._vert_dpi
