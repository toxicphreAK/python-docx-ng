"""Enumerations related to text in WordprocessingML files."""

from __future__ import annotations

import enum

from docx.enum.base import BaseEnum, BaseXmlEnum


class WD_PARAGRAPH_ALIGNMENT(BaseXmlEnum):
    """Alias: **WD_ALIGN_PARAGRAPH**

    Specifies paragraph justification type.

    Example::

        from docx.enum.text import WD_ALIGN_PARAGRAPH

        paragraph = document.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    """

    LEFT = (0, "left", "Left-aligned")
    """Left-aligned"""

    CENTER = (1, "center", "Center-aligned.")
    """Center-aligned."""

    RIGHT = (2, "right", "Right-aligned.")
    """Right-aligned."""

    JUSTIFY = (3, "both", "Fully justified.")
    """Fully justified."""

    DISTRIBUTE = (
        4,
        "distribute",
        "Paragraph characters are distributed to fill entire width of paragraph.",
    )
    """Paragraph characters are distributed to fill entire width of paragraph."""

    JUSTIFY_MED = (
        5,
        "mediumKashida",
        "Justified with a medium character compression ratio.",
    )
    """Justified with a medium character compression ratio."""

    JUSTIFY_HI = (
        7,
        "highKashida",
        "Justified with a high character compression ratio.",
    )
    """Justified with a high character compression ratio."""

    JUSTIFY_LOW = (8, "lowKashida", "Justified with a low character compression ratio.")
    """Justified with a low character compression ratio."""

    THAI_JUSTIFY = (
        9,
        "thaiDistribute",
        "Justified according to Thai formatting layout.",
    )
    """Justified according to Thai formatting layout."""


WD_ALIGN_PARAGRAPH = WD_PARAGRAPH_ALIGNMENT


class WD_BREAK_TYPE(enum.Enum):
    """Corresponds to WdBreakType enumeration.

    http://msdn.microsoft.com/en-us/library/office/ff195905.aspx.
    """

    COLUMN = 8
    LINE = 6
    LINE_CLEAR_LEFT = 9
    LINE_CLEAR_RIGHT = 10
    LINE_CLEAR_ALL = 11  # -- added for consistency, not in MS version --
    PAGE = 7
    SECTION_CONTINUOUS = 3
    SECTION_EVEN_PAGE = 4
    SECTION_NEXT_PAGE = 2
    SECTION_ODD_PAGE = 5
    TEXT_WRAPPING = 11


WD_BREAK = WD_BREAK_TYPE


class WD_COLOR_INDEX(BaseXmlEnum):
    """Specifies a standard preset color to apply.

    Used for font highlighting and perhaps other applications.

    * MS API name: `WdColorIndex`
    * URL: https://msdn.microsoft.com/EN-US/library/office/ff195343.aspx
    """

    INHERITED = (-1, None, "Color is inherited from the style hierarchy.")
    """Color is inherited from the style hierarchy."""

    NO_HIGHLIGHT = (-2, "none", "Explicitly not highlighted.")
    """Explicitly not highlighted.

    Distinct from |None|, which means no `w:highlight` element is present and the
    highlight is therefore inherited. `w:highlight` with `w:val="none"` overrides an
    inherited highlight and is written by Word when highlighting is cleared on a run
    that sits under a style supplying one.

    The MS API assigns `wdNoHighlight` the value 0, the same value as `wdAuto`. Two
    members cannot share a value here, so this member takes a distinct negative value
    in the manner of `INHERITED`.
    """

    AUTO = (0, "default", "Automatic color. Default; usually black.")
    """Automatic color. Default; usually black."""

    BLACK = (1, "black", "Black color.")
    """Black color."""

    BLUE = (2, "blue", "Blue color")
    """Blue color"""

    BRIGHT_GREEN = (4, "green", "Bright green color.")
    """Bright green color."""

    DARK_BLUE = (9, "darkBlue", "Dark blue color.")
    """Dark blue color."""

    DARK_RED = (13, "darkRed", "Dark red color.")
    """Dark red color."""

    DARK_YELLOW = (14, "darkYellow", "Dark yellow color.")
    """Dark yellow color."""

    GRAY_25 = (16, "lightGray", "25% shade of gray color.")
    """25% shade of gray color."""

    GRAY_50 = (15, "darkGray", "50% shade of gray color.")
    """50% shade of gray color."""

    GREEN = (11, "darkGreen", "Green color.")
    """Green color."""

    PINK = (5, "magenta", "Pink color.")
    """Pink color."""

    RED = (6, "red", "Red color.")
    """Red color."""

    TEAL = (10, "darkCyan", "Teal color.")
    """Teal color."""

    TURQUOISE = (3, "cyan", "Turquoise color.")
    """Turquoise color."""

    VIOLET = (12, "darkMagenta", "Violet color.")
    """Violet color."""

    WHITE = (8, "white", "White color.")
    """White color."""

    YELLOW = (7, "yellow", "Yellow color.")
    """Yellow color."""


WD_COLOR = WD_COLOR_INDEX


class WD_CONTENT_CONTROL_TYPE(BaseEnum):
    """Specifies the kind of a structured document tag (`w:sdt`), aka content control.

    The kind is determined by which child of `w:sdtPr` is present, not by an attribute
    value, so these members have no XML value mapping.

    * MS API name: `WdContentControlType`
    * URL: https://learn.microsoft.com/en-us/office/vba/api/word.wdcontentcontroltype
    """

    RICH_TEXT = (0, "Formatted text, which may contain multiple paragraphs.")
    """Formatted text, which may contain multiple paragraphs."""

    TEXT = (1, "Plain text, a single run without formatting of its own.")
    """Plain text, a single run without formatting of its own."""

    PICTURE = (2, "A single picture.")
    """A single picture."""

    COMBO_BOX = (3, "A list of choices that also accepts typed text.")
    """A list of choices that also accepts typed text."""

    DROPDOWN_LIST = (4, "A list of choices, one of which must be selected.")
    """A list of choices, one of which must be selected."""

    BUILDING_BLOCK_GALLERY = (5, "A gallery of building blocks, e.g. a cover page.")
    """A gallery of building blocks, e.g. a cover page."""

    DATE = (6, "A date, entered through a calendar picker.")
    """A date, entered through a calendar picker."""

    GROUP = (7, "A grouping of content that is edited as a unit.")
    """A grouping of content that is edited as a unit."""

    CHECKBOX = (8, "A check box, checked or unchecked.")
    """A check box, checked or unchecked.

    Written by Word as the `w14:checkbox` extension element, not as part of the ISO
    schema.
    """

    REPEATING_SECTION = (9, "A section repeated once per item in a bound collection.")
    """A section repeated once per item in a bound collection."""


class WD_FONT_HINT(BaseXmlEnum):
    """Specifies which `w:rFonts` typeface slot Word prefers for ambiguous characters.

    A character that belongs to no particular script — a space, a digit, punctuation —
    could be rendered from more than one slot, and the hint settles it. Getting this
    wrong is a common cause of East Asian text rendering in the wrong typeface.

    There is no MS API enumeration for this; it corresponds to the `ST_Hint` schema type
    and the member values are this library's own.
    """

    DEFAULT = (0, "default", "Use the ASCII typeface for ambiguous characters.")
    """Use the ASCII typeface for ambiguous characters."""

    EAST_ASIA = (1, "eastAsia", "Use the East Asian typeface for ambiguous characters.")
    """Use the East Asian typeface for ambiguous characters."""

    COMPLEX_SCRIPT = (
        2,
        "cs",
        "Use the complex-script typeface for ambiguous characters.",
    )
    """Use the complex-script typeface for ambiguous characters."""


class WD_FORM_FIELD_TYPE(BaseEnum):
    """Specifies the kind of a legacy form field.

    The kind is determined by which child of `w:ffData` is present, not by an attribute
    value, so these members have no XML value mapping.

    * MS API name: `WdFieldType` (the form-field subset)
    * URL: https://learn.microsoft.com/en-us/office/vba/api/word.wdfieldtype
    """

    TEXT = (70, "A text input, which Word calls FORMTEXT.")
    """A text input, which Word calls FORMTEXT."""

    CHECK_BOX = (71, "A check box, which Word calls FORMCHECKBOX.")
    """A check box, which Word calls FORMCHECKBOX."""

    DROP_DOWN = (83, "A drop-down list, which Word calls FORMDROPDOWN.")
    """A drop-down list, which Word calls FORMDROPDOWN."""


class WD_LINE_SPACING(BaseXmlEnum):
    """Specifies a line spacing format to be applied to a paragraph.

    Example::

        from docx.enum.text import WD_LINE_SPACING

        paragraph = document.add_paragraph()
        paragraph.line_spacing_rule = WD_LINE_SPACING.EXACTLY


    MS API name: `WdLineSpacing`

    URL: http://msdn.microsoft.com/en-us/library/office/ff844910.aspx
    """

    SINGLE = (0, "UNMAPPED", "Single spaced (default).")
    """Single spaced (default)."""

    ONE_POINT_FIVE = (1, "UNMAPPED", "Space-and-a-half line spacing.")
    """Space-and-a-half line spacing."""

    DOUBLE = (2, "UNMAPPED", "Double spaced.")
    """Double spaced."""

    AT_LEAST = (
        3,
        "atLeast",
        "Minimum line spacing is specified amount. Amount is specified separately.",
    )
    """Minimum line spacing is specified amount. Amount is specified separately."""

    EXACTLY = (
        4,
        "exact",
        "Line spacing is exactly specified amount. Amount is specified separately.",
    )
    """Line spacing is exactly specified amount. Amount is specified separately."""

    MULTIPLE = (
        5,
        "auto",
        "Line spacing is specified as multiple of line heights. Changing font size"
        " will change line spacing proportionately.",
    )
    """Line spacing is specified as multiple of line heights. Changing font size will
       change the line spacing proportionately."""


class WD_SHADING_PATTERN(BaseXmlEnum):
    """Specifies the pattern drawn over the background of shaded content.

    The pattern is drawn in the shading *color* over the shading *fill*. The common
    case is |CLEAR|, which draws no pattern and leaves the fill as a solid background.

    * ISO/IEC 29500-1 §17.18.78 (`ST_Shd`)
    """

    NIL = (0, "nil", "No shading. Equivalent to no `w:shd` element at all.")
    """No shading. Equivalent to no `w:shd` element at all."""

    CLEAR = (1, "clear", "No pattern; the fill color forms a solid background.")
    """No pattern; the fill color forms a solid background.

    This is what Word writes for an ordinary background color, and what this library
    writes when shading is applied without naming a pattern.
    """

    SOLID = (2, "solid", "The pattern color entirely covers the fill color.")
    """The pattern color entirely covers the fill color.

    Note the reversal: with |SOLID| the visible background is the shading *color*, not
    the fill.
    """

    HORZ_STRIPE = (3, "horzStripe", "Horizontal stripes.")
    """Horizontal stripes."""

    VERT_STRIPE = (4, "vertStripe", "Vertical stripes.")
    """Vertical stripes."""

    REVERSE_DIAG_STRIPE = (5, "reverseDiagStripe", "Diagonal stripes, upward to right.")
    """Diagonal stripes running upward to the right."""

    DIAG_STRIPE = (6, "diagStripe", "Diagonal stripes, downward to right.")
    """Diagonal stripes running downward to the right."""

    HORZ_CROSS = (7, "horzCross", "A horizontal and vertical crosshatch.")
    """A horizontal and vertical crosshatch."""

    DIAG_CROSS = (8, "diagCross", "A diagonal crosshatch.")
    """A diagonal crosshatch."""

    THIN_HORZ_STRIPE = (9, "thinHorzStripe", "Narrow horizontal stripes.")
    """Narrow horizontal stripes."""

    THIN_VERT_STRIPE = (10, "thinVertStripe", "Narrow vertical stripes.")
    """Narrow vertical stripes."""

    THIN_REVERSE_DIAG_STRIPE = (
        11,
        "thinReverseDiagStripe",
        "Narrow diagonal stripes, upward to right.",
    )
    """Narrow diagonal stripes running upward to the right."""

    THIN_DIAG_STRIPE = (12, "thinDiagStripe", "Narrow diagonal stripes, downward to right.")
    """Narrow diagonal stripes running downward to the right."""

    THIN_HORZ_CROSS = (13, "thinHorzCross", "A narrow horizontal and vertical crosshatch.")
    """A narrow horizontal and vertical crosshatch."""

    THIN_DIAG_CROSS = (14, "thinDiagCross", "A narrow diagonal crosshatch.")
    """A narrow diagonal crosshatch."""

    PCT_5 = (15, "pct5", "5% of the pattern color over the fill color.")
    """5% of the pattern color over the fill color."""

    PCT_10 = (16, "pct10", "10% of the pattern color over the fill color.")
    """10% of the pattern color over the fill color."""

    PCT_12 = (17, "pct12", "12.5% of the pattern color over the fill color.")
    """12.5% of the pattern color over the fill color."""

    PCT_15 = (18, "pct15", "15% of the pattern color over the fill color.")
    """15% of the pattern color over the fill color."""

    PCT_20 = (19, "pct20", "20% of the pattern color over the fill color.")
    """20% of the pattern color over the fill color."""

    PCT_25 = (20, "pct25", "25% of the pattern color over the fill color.")
    """25% of the pattern color over the fill color."""

    PCT_30 = (21, "pct30", "30% of the pattern color over the fill color.")
    """30% of the pattern color over the fill color."""

    PCT_35 = (22, "pct35", "35% of the pattern color over the fill color.")
    """35% of the pattern color over the fill color."""

    PCT_37 = (23, "pct37", "37.5% of the pattern color over the fill color.")
    """37.5% of the pattern color over the fill color."""

    PCT_40 = (24, "pct40", "40% of the pattern color over the fill color.")
    """40% of the pattern color over the fill color."""

    PCT_45 = (25, "pct45", "45% of the pattern color over the fill color.")
    """45% of the pattern color over the fill color."""

    PCT_50 = (26, "pct50", "50% of the pattern color over the fill color.")
    """50% of the pattern color over the fill color."""

    PCT_55 = (27, "pct55", "55% of the pattern color over the fill color.")
    """55% of the pattern color over the fill color."""

    PCT_60 = (28, "pct60", "60% of the pattern color over the fill color.")
    """60% of the pattern color over the fill color."""

    PCT_62 = (29, "pct62", "62.5% of the pattern color over the fill color.")
    """62.5% of the pattern color over the fill color."""

    PCT_65 = (30, "pct65", "65% of the pattern color over the fill color.")
    """65% of the pattern color over the fill color."""

    PCT_70 = (31, "pct70", "70% of the pattern color over the fill color.")
    """70% of the pattern color over the fill color."""

    PCT_75 = (32, "pct75", "75% of the pattern color over the fill color.")
    """75% of the pattern color over the fill color."""

    PCT_80 = (33, "pct80", "80% of the pattern color over the fill color.")
    """80% of the pattern color over the fill color."""

    PCT_85 = (34, "pct85", "85% of the pattern color over the fill color.")
    """85% of the pattern color over the fill color."""

    PCT_87 = (35, "pct87", "87.5% of the pattern color over the fill color.")
    """87.5% of the pattern color over the fill color."""

    PCT_90 = (36, "pct90", "90% of the pattern color over the fill color.")
    """90% of the pattern color over the fill color."""

    PCT_95 = (37, "pct95", "95% of the pattern color over the fill color.")
    """95% of the pattern color over the fill color."""


class WD_TAB_ALIGNMENT(BaseXmlEnum):
    """Specifies the tab stop alignment to apply.

    MS API name: `WdTabAlignment`

    URL: https://msdn.microsoft.com/EN-US/library/office/ff195609.aspx
    """

    LEFT = (0, "left", "Left-aligned.")
    """Left-aligned."""

    CENTER = (1, "center", "Center-aligned.")
    """Center-aligned."""

    RIGHT = (2, "right", "Right-aligned.")
    """Right-aligned."""

    DECIMAL = (3, "decimal", "Decimal-aligned.")
    """Decimal-aligned."""

    BAR = (4, "bar", "Bar-aligned.")
    """Bar-aligned."""

    LIST = (6, "list", "List-aligned. (deprecated)")
    """List-aligned. (deprecated)"""

    CLEAR = (101, "clear", "Clear an inherited tab stop.")
    """Clear an inherited tab stop."""

    END = (102, "end", "Right-aligned.  (deprecated)")
    """Right-aligned.  (deprecated)"""

    NUM = (103, "num", "Left-aligned.  (deprecated)")
    """Left-aligned.  (deprecated)"""

    START = (104, "start", "Left-aligned.  (deprecated)")
    """Left-aligned.  (deprecated)"""


class WD_TAB_LEADER(BaseXmlEnum):
    """Specifies the character to use as the leader with formatted tabs.

    MS API name: `WdTabLeader`

    URL: https://msdn.microsoft.com/en-us/library/office/ff845050.aspx
    """

    SPACES = (0, "none", "Spaces. Default.")
    """Spaces. Default."""

    DOTS = (1, "dot", "Dots.")
    """Dots."""

    DASHES = (2, "hyphen", "Dashes.")
    """Dashes."""

    LINES = (3, "underscore", "Double lines.")
    """Double lines."""

    HEAVY = (4, "heavy", "A heavy line.")
    """A heavy line."""

    MIDDLE_DOT = (5, "middleDot", "A vertically-centered dot.")
    """A vertically-centered dot."""


class WD_TEXT_DIRECTION(BaseXmlEnum):
    """Specifies the flow direction of text within a paragraph, section or table cell.

    This is the writing direction — which way the lines run and whether the glyphs are
    rotated — and is a different thing from `bidi`, which is the base *reading* direction
    of a right-to-left paragraph.

    Example::

        from docx.enum.text import WD_TEXT_DIRECTION

        cell.text_direction = WD_TEXT_DIRECTION.BT_LR   # rotated header cell

    The names spell out the two axes in the order Word writes them: `LR_TB` is
    left-to-right within a line, top-to-bottom between lines, which is ordinary
    horizontal Western layout.
    """

    LR_TB = (0, "lrTb", "Horizontal, left to right. Ordinary Western layout.")
    """Horizontal, left to right. Ordinary Western layout."""

    TB_RL = (1, "tbRl", "Vertical, right to left. Ordinary East Asian vertical layout.")
    """Vertical, right to left. Ordinary East Asian vertical layout."""

    BT_LR = (2, "btLr", "Rotated 90 degrees counter-clockwise. A rotated table header.")
    """Rotated 90 degrees counter-clockwise. A rotated table header."""

    LR_TB_V = (3, "lrTbV", "Horizontal, with each glyph rotated 90 degrees clockwise.")
    """Horizontal, with each glyph rotated 90 degrees clockwise."""

    TB_RL_V = (4, "tbRlV", "Vertical, with each glyph rotated 90 degrees clockwise.")
    """Vertical, with each glyph rotated 90 degrees clockwise."""

    TB_LR_V = (5, "tbLrV", "Vertical, left to right, with glyphs rotated.")
    """Vertical, left to right, with glyphs rotated."""


class WD_TEXT_FORM_FIELD_TYPE(BaseXmlEnum):
    """Specifies what a text form field accepts.

    Example::

        from docx.enum.text import WD_TEXT_FORM_FIELD_TYPE

        form_field.text_type = WD_TEXT_FORM_FIELD_TYPE.NUMBER_TEXT

    * MS API name: `WdTextFormFieldType`
    * URL: https://learn.microsoft.com/en-us/office/vba/api/word.wdtextformfieldtype
    """

    REGULAR_TEXT = (0, "regular", "Any text.")
    """Any text."""

    NUMBER_TEXT = (1, "number", "A number.")
    """A number."""

    DATE_TEXT = (2, "date", "A date.")
    """A date."""

    CURRENT_DATE_TEXT = (3, "currentDate", "The current date, filled in by Word.")
    """The current date, filled in by Word."""

    CURRENT_TIME_TEXT = (4, "currentTime", "The current time, filled in by Word.")
    """The current time, filled in by Word."""

    CALCULATION_TEXT = (5, "calculated", "The result of an expression, computed by Word.")
    """The result of an expression, computed by Word."""


class WD_UNDERLINE(BaseXmlEnum):
    """Specifies the style of underline applied to a run of characters.

    MS API name: `WdUnderline`

    URL: http://msdn.microsoft.com/en-us/library/office/ff822388.aspx
    """

    INHERITED = (-1, None, "Inherit underline setting from containing paragraph.")
    """Inherit underline setting from containing paragraph."""

    NONE = (
        0,
        "none",
        "No underline.\n\nThis setting overrides any inherited underline value, so can"
        " be used to remove underline from a run that inherits underlining from its"
        " containing paragraph. Note this is not the same as assigning |None| to"
        " Run.underline. |None| is a valid assignment value, but causes the run to"
        " inherit its underline value. Assigning `WD_UNDERLINE.NONE` causes"
        " underlining to be unconditionally turned off.",
    )
    """No underline.

    This setting overrides any inherited underline value, so can be used to remove
    underline from a run that inherits underlining from its containing paragraph. Note
    this is not the same as assigning |None| to Run.underline. |None| is a valid
    assignment value, but causes the run to inherit its underline value. Assigning
    ``WD_UNDERLINE.NONE`` causes underlining to be unconditionally turned off.
    """

    SINGLE = (
        1,
        "single",
        "A single line.\n\nNote that this setting is write-only in the sense that"
        " |True| (rather than `WD_UNDERLINE.SINGLE`) is returned for a run having"
        " this setting.",
    )
    """A single line.

    Note that this setting is write-only in the sense that |True|
    (rather than ``WD_UNDERLINE.SINGLE``) is returned for a run having this setting.
    """

    WORDS = (2, "words", "Underline individual words only.")
    """Underline individual words only."""

    DOUBLE = (3, "double", "A double line.")
    """A double line."""

    DOTTED = (4, "dotted", "Dots.")
    """Dots."""

    THICK = (6, "thick", "A single thick line.")
    """A single thick line."""

    DASH = (7, "dash", "Dashes.")
    """Dashes."""

    DOT_DASH = (9, "dotDash", "Alternating dots and dashes.")
    """Alternating dots and dashes."""

    DOT_DOT_DASH = (10, "dotDotDash", "An alternating dot-dot-dash pattern.")
    """An alternating dot-dot-dash pattern."""

    WAVY = (11, "wave", "A single wavy line.")
    """A single wavy line."""

    DOTTED_HEAVY = (20, "dottedHeavy", "Heavy dots.")
    """Heavy dots."""

    DASH_HEAVY = (23, "dashedHeavy", "Heavy dashes.")
    """Heavy dashes."""

    DOT_DASH_HEAVY = (25, "dashDotHeavy", "Alternating heavy dots and heavy dashes.")
    """Alternating heavy dots and heavy dashes."""

    DOT_DOT_DASH_HEAVY = (
        26,
        "dashDotDotHeavy",
        "An alternating heavy dot-dot-dash pattern.",
    )
    """An alternating heavy dot-dot-dash pattern."""

    WAVY_HEAVY = (27, "wavyHeavy", "A heavy wavy line.")
    """A heavy wavy line."""

    DASH_LONG = (39, "dashLong", "Long dashes.")
    """Long dashes."""

    WAVY_DOUBLE = (43, "wavyDouble", "A double wavy line.")
    """A double wavy line."""

    DASH_LONG_HEAVY = (55, "dashLongHeavy", "Long heavy dashes.")
    """Long heavy dashes."""
