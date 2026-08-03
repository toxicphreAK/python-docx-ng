"""Enumerations related to tables in WordprocessingML files."""

from docx.enum.base import BaseEnum, BaseXmlEnum


class WD_CELL_VERTICAL_ALIGNMENT(BaseXmlEnum):
    """Alias: **WD_ALIGN_VERTICAL**

    Specifies the vertical alignment of text in one or more cells of a table.

    Example::

        from docx.enum.table import WD_ALIGN_VERTICAL

        table = document.add_table(3, 3)
        table.cell(0, 0).vertical_alignment = WD_ALIGN_VERTICAL.BOTTOM

    MS API name: `WdCellVerticalAlignment`

    https://msdn.microsoft.com/en-us/library/office/ff193345.aspx
    """

    TOP = (0, "top", "Text is aligned to the top border of the cell.")
    """Text is aligned to the top border of the cell."""

    CENTER = (1, "center", "Text is aligned to the center of the cell.")
    """Text is aligned to the center of the cell."""

    BOTTOM = (3, "bottom", "Text is aligned to the bottom border of the cell.")
    """Text is aligned to the bottom border of the cell."""

    BOTH = (
        101,
        "both",
        "This is an option in the OpenXml spec, but not in Word itself. It's not"
        " clear what Word behavior this setting produces. If you find out please"
        " let us know and we'll update this documentation. Otherwise, probably best"
        " to avoid this option.",
    )
    """This is an option in the OpenXml spec, but not in Word itself.

    It's not clear what Word behavior this setting produces. If you find out please let
    us know and we'll update this documentation. Otherwise, probably best to avoid this
    option.
    """


WD_ALIGN_VERTICAL = WD_CELL_VERTICAL_ALIGNMENT


class WD_ROW_HEIGHT_RULE(BaseXmlEnum):
    """Alias: **WD_ROW_HEIGHT**

    Specifies the rule for determining the height of a table row

    Example::

        from docx.enum.table import WD_ROW_HEIGHT_RULE

        table = document.add_table(3, 3)
        table.rows[0].height_rule = WD_ROW_HEIGHT_RULE.EXACTLY

    MS API name: `WdRowHeightRule`

    https://msdn.microsoft.com/en-us/library/office/ff193620.aspx
    """

    AUTO = (
        0,
        "auto",
        "The row height is adjusted to accommodate the tallest value in the row.",
    )
    """The row height is adjusted to accommodate the tallest value in the row."""

    AT_LEAST = (1, "atLeast", "The row height is at least a minimum specified value.")
    """The row height is at least a minimum specified value."""

    EXACTLY = (2, "exact", "The row height is an exact value.")
    """The row height is an exact value."""


WD_ROW_HEIGHT = WD_ROW_HEIGHT_RULE


class WD_LINE_STYLE(BaseXmlEnum):
    """Specifies the line style of a table or cell border.

    Example::

        from docx.enum.table import WD_LINE_STYLE
        from docx.shared import Pt

        table = document.add_table(3, 3)
        table.borders["top"].line = WD_LINE_STYLE.SINGLE
        table.borders["top"].size = Pt(1)

    Only the structural line styles are members here. The `ST_Border` schema type also
    admits some 170 decorative "page border art" values such as `"apples"` and
    `"zigZagStitch"`; those are meaningful only on a page border, and Word does not
    offer or write them for a table or cell border.

    MS API name: `WdLineStyle`

    https://learn.microsoft.com/en-us/office/vba/api/word.wdlinestyle
    """

    NONE = (0, "none", "No border.")
    """No border."""

    SINGLE = (1, "single", "A single solid line.")
    """A single solid line."""

    DOT = (2, "dotted", "A dotted line.")
    """A dotted line."""

    DASH_SMALL_GAP = (3, "dashSmallGap", "A dashed line with small gaps.")
    """A dashed line with small gaps."""

    DASH_LARGE_GAP = (4, "dashed", "A dashed line with large gaps.")
    """A dashed line with large gaps."""

    DASH_DOT = (5, "dotDash", "A line of alternating dashes and dots.")
    """A line of alternating dashes and dots."""

    DASH_DOT_DOT = (6, "dotDotDash", "A line of dashes each followed by two dots.")
    """A line of dashes each followed by two dots."""

    DOUBLE = (7, "double", "Two parallel solid lines.")
    """Two parallel solid lines."""

    TRIPLE = (8, "triple", "Three parallel solid lines.")
    """Three parallel solid lines."""

    THIN_THICK_SMALL_GAP = (
        9,
        "thinThickSmallGap",
        "A thin line and a thick line separated by a small gap.",
    )
    """A thin line and a thick line separated by a small gap."""

    THICK_THIN_SMALL_GAP = (
        10,
        "thickThinSmallGap",
        "A thick line and a thin line separated by a small gap.",
    )
    """A thick line and a thin line separated by a small gap."""

    THIN_THICK_THIN_SMALL_GAP = (
        11,
        "thinThickThinSmallGap",
        "A thin, a thick and a thin line separated by small gaps.",
    )
    """A thin, a thick and a thin line separated by small gaps."""

    THIN_THICK_MED_GAP = (
        12,
        "thinThickMediumGap",
        "A thin line and a thick line separated by a medium gap.",
    )
    """A thin line and a thick line separated by a medium gap."""

    THICK_THIN_MED_GAP = (
        13,
        "thickThinMediumGap",
        "A thick line and a thin line separated by a medium gap.",
    )
    """A thick line and a thin line separated by a medium gap."""

    THIN_THICK_THIN_MED_GAP = (
        14,
        "thinThickThinMediumGap",
        "A thin, a thick and a thin line separated by medium gaps.",
    )
    """A thin, a thick and a thin line separated by medium gaps."""

    THIN_THICK_LARGE_GAP = (
        15,
        "thinThickLargeGap",
        "A thin line and a thick line separated by a large gap.",
    )
    """A thin line and a thick line separated by a large gap."""

    THICK_THIN_LARGE_GAP = (
        16,
        "thickThinLargeGap",
        "A thick line and a thin line separated by a large gap.",
    )
    """A thick line and a thin line separated by a large gap."""

    THIN_THICK_THIN_LARGE_GAP = (
        17,
        "thinThickThinLargeGap",
        "A thin, a thick and a thin line separated by large gaps.",
    )
    """A thin, a thick and a thin line separated by large gaps."""

    SINGLE_WAVY = (18, "wave", "A single wavy line.")
    """A single wavy line."""

    DOUBLE_WAVY = (19, "doubleWave", "Two parallel wavy lines.")
    """Two parallel wavy lines."""

    DASH_DOT_STROKED = (20, "dashDotStroked", "A line of slanting dashes and dots.")
    """A line of slanting dashes and dots."""

    EMBOSS_3D = (21, "threeDEmboss", "A line that appears embossed.")
    """A line that appears embossed."""

    ENGRAVE_3D = (22, "threeDEngrave", "A line that appears engraved.")
    """A line that appears engraved."""

    OUTSET = (23, "outset", "A line that makes the enclosed area appear raised.")
    """A line that makes the enclosed area appear raised."""

    INSET = (24, "inset", "A line that makes the enclosed area appear sunken.")
    """A line that makes the enclosed area appear sunken."""

    THICK = (
        100,
        "thick",
        "A single thick solid line. This is an OpenXml value with no `WdLineStyle`"
        " counterpart; Word renders it as a heavier `SINGLE`.",
    )
    """A single thick solid line.

    This is an OpenXml value with no `WdLineStyle` counterpart; Word renders it as a
    heavier `SINGLE`.
    """

    NIL = (
        101,
        "nil",
        "No border, and no space reserved for one. Distinct from `NONE` only in that"
        " `NONE` is the value Word writes when a border is explicitly turned off,"
        " whereas `nil` also appears as the default in a table style.",
    )
    """No border, and no space reserved for one.

    Distinct from `NONE` only in that `NONE` is the value Word writes when a border is
    explicitly turned off, whereas `nil` also appears as the default in a table style.
    """


class WD_TABLE_ALIGNMENT(BaseXmlEnum):
    """Specifies table justification type.

    Example::

        from docx.enum.table import WD_TABLE_ALIGNMENT

        table = document.add_table(3, 3)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

    MS API name: `WdRowAlignment`

    http://office.microsoft.com/en-us/word-help/HV080607259.aspx
    """

    LEFT = (0, "left", "Left-aligned")
    """Left-aligned"""

    CENTER = (1, "center", "Center-aligned.")
    """Center-aligned."""

    RIGHT = (2, "right", "Right-aligned.")
    """Right-aligned."""


class WD_TABLE_DIRECTION(BaseEnum):
    """Specifies the direction in which an application orders cells in the specified
    table or row.

    Example::

        from docx.enum.table import WD_TABLE_DIRECTION

        table = document.add_table(3, 3)
        table.direction = WD_TABLE_DIRECTION.RTL

    MS API name: `WdTableDirection`

    http://msdn.microsoft.com/en-us/library/ff835141.aspx
    """

    LTR = (
        0,
        "The table or row is arranged with the first column in the leftmost position.",
    )
    """The table or row is arranged with the first column in the leftmost position."""

    RTL = (
        1,
        "The table or row is arranged with the first column in the rightmost position.",
    )
    """The table or row is arranged with the first column in the rightmost position."""
