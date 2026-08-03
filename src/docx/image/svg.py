"""Image header parser for SVG images.

SVG is XML, so there is no fixed-offset magic number to match and no binary header to
unpack. Size comes from the `width` and `height` attributes of the root `<svg>` element,
which are CSS lengths and may carry any of the usual units, or — when those are absent
or given as percentages, which is common for icons meant to scale — from the `viewBox`.

One SVG user unit is one CSS pixel, 1/96 inch, which is why the resolution reported here
is 96 rather than the 72 the resolution-free raster formats assume.
"""

from __future__ import annotations

import re

from lxml import etree

from .constants import MIME_TYPE
from .exceptions import InvalidImageStreamError
from .image import BaseImageHeader

_SVG_NAMESPACE = "http://www.w3.org/2000/svg"

# -- one SVG user unit is one CSS pixel --
_SVG_DPI = 96

# -- CSS absolute length units, in inches. A bare number, and `px`, are user units. --
_INCHES_PER_UNIT = {
    "": 1 / _SVG_DPI,
    "px": 1 / _SVG_DPI,
    "pt": 1 / 72,
    "pc": 1 / 6,
    "in": 1.0,
    "cm": 1 / 2.54,
    "mm": 1 / 25.4,
    "q": 1 / 101.6,
}

_LENGTH_RE = re.compile(r"^\s*([+-]?[0-9]*\.?[0-9]+(?:[eE][+-]?[0-9]+)?)\s*([a-z%]*)\s*$")

# -- how far into the file to look for the root element when sniffing. Enough for an XML
# -- declaration, a DOCTYPE and a comment or two ahead of `<svg`. --
_SNIFF_LENGTH = 4096

_SVG_ROOT_RE = re.compile(rb"<svg[\s>/]", re.IGNORECASE)


class Svg(BaseImageHeader):
    """Image header parser for SVG images."""

    @classmethod
    def sniff(cls, header: bytes) -> bool:
        """True when `header` looks like the start of an SVG document.

        SVG has no magic number, so detection is by finding an `<svg` root element ahead
        of any other element. Matched against the leading bytes of the file rather than
        at a fixed offset, because an XML declaration, a DOCTYPE and comments may all
        precede the root.
        """
        prefix = header[:_SNIFF_LENGTH]
        match = _SVG_ROOT_RE.search(prefix)
        if match is None:
            return False
        # -- reject a document whose root is something else that merely contains an
        # -- embedded `<svg>`, such as XHTML --
        first_element = re.search(rb"<[A-Za-z]", prefix)
        return first_element is not None and first_element.start() == match.start()

    @classmethod
    def from_stream(cls, stream):
        """Return an |Svg| instance with header properties parsed from `stream`."""
        root = cls._parse_root(stream)
        inch_width, inch_height = cls._extents_in_inches(root)
        px_width = int(round(inch_width * _SVG_DPI))
        px_height = int(round(inch_height * _SVG_DPI))
        return cls(px_width, px_height, _SVG_DPI, _SVG_DPI)

    @property
    def content_type(self):
        """MIME content type for this image, unconditionally `image/svg+xml` for SVG
        images."""
        return MIME_TYPE.SVG

    @property
    def default_ext(self):
        """Default filename extension, always 'svg' for SVG images."""
        return "svg"

    @classmethod
    def _extents_in_inches(cls, root: etree._Element) -> tuple[float, float]:
        """The width and height of `root`, in inches.

        The `width` and `height` attributes win when both give an absolute length. A
        percentage is relative to a viewport this file does not have, so it falls back
        to the `viewBox`, as does an SVG that omits the attributes entirely — which is
        what an icon meant to scale to its container looks like.
        """
        width = cls._length_in_inches(root.get("width"))
        height = cls._length_in_inches(root.get("height"))
        if width is not None and height is not None:
            return width, height

        viewbox = cls._viewbox_in_inches(root.get("viewBox"))
        if viewbox is None:
            raise InvalidImageStreamError(
                "SVG image has no absolute width and height and no viewBox, so its"
                " display size is unknown"
            )
        return (
            width if width is not None else viewbox[0],
            height if height is not None else viewbox[1],
        )

    @classmethod
    def _length_in_inches(cls, value: str | None) -> float | None:
        """`value` as a length in inches, or |None| when it is not an absolute length.

        |None| covers an absent attribute, a percentage, and the font-relative units
        (`em`, `ex`, `rem`, `ch`), none of which can be resolved without a rendering
        context.
        """
        if value is None:
            return None
        match = _LENGTH_RE.match(value)
        if match is None:
            return None
        magnitude, unit = match.group(1), match.group(2).lower()
        if unit not in _INCHES_PER_UNIT:
            return None
        inches = float(magnitude) * _INCHES_PER_UNIT[unit]
        return inches if inches > 0 else None

    @classmethod
    def _parse_root(cls, stream) -> etree._Element:
        """The root element of the SVG document in `stream`.

        Parsed with entity resolution and network access off. This is user-supplied XML
        arriving through the same door as any other image, and an SVG carrying an
        external entity would otherwise be a file-disclosure vector.
        """
        stream.seek(0)
        parser = etree.XMLParser(
            resolve_entities=False, no_network=True, huge_tree=False, recover=False
        )
        try:
            root = etree.parse(stream, parser).getroot()
        except etree.XMLSyntaxError as err:
            raise InvalidImageStreamError("SVG image is not well-formed XML") from err
        if root.tag != "{%s}svg" % _SVG_NAMESPACE:
            raise InvalidImageStreamError(
                "root element of SVG image is %r, expected an `svg` element in the SVG"
                " namespace" % root.tag
            )
        return root

    @classmethod
    def _viewbox_in_inches(cls, value: str | None) -> tuple[float, float] | None:
        """The width and height of `value`, a `viewBox` attribute, in inches.

        A `viewBox` is four numbers in user units; the last two are the size.
        """
        if value is None:
            return None
        parts = value.replace(",", " ").split()
        if len(parts) != 4:
            return None
        try:
            width, height = float(parts[2]), float(parts[3])
        except ValueError:
            return None
        if width <= 0 or height <= 0:
            return None
        return width / _SVG_DPI, height / _SVG_DPI
