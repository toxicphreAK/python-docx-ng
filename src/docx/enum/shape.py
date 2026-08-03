"""Enumerations related to DrawingML shapes in WordprocessingML files."""

import enum

from docx.enum.base import BaseXmlEnum


class WD_INLINE_SHAPE_TYPE(enum.Enum):
    """Corresponds to WdInlineShapeType enumeration.

    http://msdn.microsoft.com/en-us/library/office/ff192587.aspx.
    """

    CHART = 12
    LINKED_PICTURE = 4
    PICTURE = 3
    SMART_ART = 15
    NOT_IMPLEMENTED = -6


WD_INLINE_SHAPE = WD_INLINE_SHAPE_TYPE


class WD_WRAP_TYPE(BaseXmlEnum):
    """Specifies how text wraps around a floating (anchored) shape.

    Example::

        from docx.enum.shape import WD_WRAP_TYPE

        shape = paragraph.add_float_picture("logo.png")
        shape.wrap_type = WD_WRAP_TYPE.SQUARE

    MS API name: `WdWrapType`

    https://learn.microsoft.com/en-us/office/vba/api/word.wdwraptype
    """

    NONE = (
        3,
        "wrapNone",
        "Text does not wrap. The shape floats over the text, or behind it when"
        " `behind_text` is set, which is how a watermark is placed.",
    )
    """Text does not wrap; the shape floats over or behind it."""

    SQUARE = (0, "wrapSquare", "Text wraps around the shape's bounding rectangle.")
    """Text wraps around the shape's bounding rectangle."""

    TIGHT = (
        1,
        "wrapTight",
        "Text wraps around the shape's outline rather than its bounding rectangle,"
        " following the wrap polygon Word derives from the image.",
    )
    """Text wraps around the shape's outline rather than its bounding rectangle."""

    THROUGH = (
        2,
        "wrapThrough",
        "As TIGHT, but text also flows into any open region within the outline.",
    )
    """As TIGHT, but text also flows into open regions within the outline."""

    TOP_BOTTOM = (
        4,
        "wrapTopAndBottom",
        "Text stops above the shape and resumes below it, leaving the sides clear.",
    )
    """Text stops above the shape and resumes below it."""


class WD_ANCHOR_RELATIVE_FROM_H(BaseXmlEnum):
    """What the horizontal position of a floating shape is measured from.

    MS API name: `WdRelativeHorizontalPosition`
    """

    MARGIN = (0, "margin", "Relative to the text margin.")
    """Relative to the text margin."""

    PAGE = (1, "page", "Relative to the edge of the page.")
    """Relative to the edge of the page."""

    COLUMN = (2, "column", "Relative to the text column.")
    """Relative to the text column."""

    CHARACTER = (3, "character", "Relative to the character the anchor sits at.")
    """Relative to the character the anchor sits at."""

    LEFT_MARGIN = (4, "leftMargin", "Relative to the left margin.")
    """Relative to the left margin."""

    RIGHT_MARGIN = (5, "rightMargin", "Relative to the right margin.")
    """Relative to the right margin."""

    INSIDE_MARGIN = (
        6,
        "insideMargin",
        "Relative to the inside margin — the left margin on an odd page and the right"
        " margin on an even one, in a document laid out for double-sided printing.",
    )
    """Relative to the inside margin of a double-sided layout."""

    OUTSIDE_MARGIN = (7, "outsideMargin", "Relative to the outside margin.")
    """Relative to the outside margin of a double-sided layout."""


class WD_ANCHOR_RELATIVE_FROM_V(BaseXmlEnum):
    """What the vertical position of a floating shape is measured from.

    MS API name: `WdRelativeVerticalPosition`
    """

    MARGIN = (0, "margin", "Relative to the text margin.")
    """Relative to the text margin."""

    PAGE = (1, "page", "Relative to the edge of the page.")
    """Relative to the edge of the page."""

    PARAGRAPH = (2, "paragraph", "Relative to the paragraph the anchor sits in.")
    """Relative to the paragraph the anchor sits in."""

    LINE = (3, "line", "Relative to the line the anchor sits on.")
    """Relative to the line the anchor sits on."""

    TOP_MARGIN = (4, "topMargin", "Relative to the top margin.")
    """Relative to the top margin."""

    BOTTOM_MARGIN = (5, "bottomMargin", "Relative to the bottom margin.")
    """Relative to the bottom margin."""

    INSIDE_MARGIN = (6, "insideMargin", "Relative to the inside margin.")
    """Relative to the inside margin of a double-sided layout."""

    OUTSIDE_MARGIN = (7, "outsideMargin", "Relative to the outside margin.")
    """Relative to the outside margin of a double-sided layout."""


class WD_ANCHOR_ALIGN_H(BaseXmlEnum):
    """Horizontal alignment of a floating shape within what it is positioned against.

    An alternative to an absolute offset: `LEFT` against
    `WD_ANCHOR_RELATIVE_FROM_H.PAGE` puts the shape at the left edge of the page
    whatever the page size turns out to be.
    """

    LEFT = (0, "left", "Aligned to the left edge.")
    """Aligned to the left edge."""

    CENTER = (1, "center", "Centred.")
    """Centred."""

    RIGHT = (2, "right", "Aligned to the right edge.")
    """Aligned to the right edge."""

    INSIDE = (3, "inside", "Aligned to the inside edge of a double-sided layout.")
    """Aligned to the inside edge of a double-sided layout."""

    OUTSIDE = (4, "outside", "Aligned to the outside edge of a double-sided layout.")
    """Aligned to the outside edge of a double-sided layout."""


class WD_ANCHOR_ALIGN_V(BaseXmlEnum):
    """Vertical alignment of a floating shape within what it is positioned against."""

    TOP = (0, "top", "Aligned to the top edge.")
    """Aligned to the top edge."""

    CENTER = (1, "center", "Centred.")
    """Centred."""

    BOTTOM = (2, "bottom", "Aligned to the bottom edge.")
    """Aligned to the bottom edge."""

    INSIDE = (3, "inside", "Aligned to the inside edge of a double-sided layout.")
    """Aligned to the inside edge of a double-sided layout."""

    OUTSIDE = (4, "outside", "Aligned to the outside edge of a double-sided layout.")
    """Aligned to the outside edge of a double-sided layout."""
