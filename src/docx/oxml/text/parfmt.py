"""Custom element classes related to paragraph properties (CT_PPr)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from docx.enum.text import (
    WD_ALIGN_PARAGRAPH,
    WD_LINE_SPACING,
    WD_SHADING_PATTERN,
    WD_TAB_ALIGNMENT,
    WD_TAB_LEADER,
    WD_TEXT_DIRECTION,
)
from docx.oxml.shared import CT_DecimalNumber
from docx.oxml.simpletypes import (
    ST_DecimalNumber,
    ST_SignedTwipsMeasure,
    ST_TwipsMeasure,
)
from docx.oxml.table import _CT_BordersBase  # pyright: ignore[reportPrivateUsage]
from docx.oxml.text.font import _ensure_shd_val, _shd_val
from docx.oxml.xmlchemy import (
    BaseOxmlElement,
    OneOrMore,
    OptionalAttribute,
    RequiredAttribute,
    ZeroOrOne,
)
from docx.shared import Length, RGBColor

if TYPE_CHECKING:
    from docx.oxml.section import CT_SectPr
    from docx.oxml.shared import CT_OnOff, CT_String
    from docx.oxml.table import CT_Border
    from docx.oxml.text.font import CT_RPr, CT_Shd


class CT_Ind(BaseOxmlElement):
    """``<w:ind>`` element, specifying paragraph indentation.

    Two unit systems live side by side here. The `w:left`, `w:right`, `w:firstLine` and
    `w:hanging` attributes are absolute twips measures. The `*Chars` attributes beside
    them are in hundredths of a character — the unit Word's paragraph dialogue offers
    for a CJK document — and are *not* |Length| values: a character has no fixed size,
    so there is nothing to convert them to.

    `w:start` and `w:end` are the newer writing-direction synonyms of `w:left` and
    `w:right`. Word writes them in files saved by recent versions; a document using them
    reads as unindented if only `w:left` is consulted.
    """

    left: Length | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:left", ST_SignedTwipsMeasure
    )
    right: Length | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:right", ST_SignedTwipsMeasure
    )
    start: Length | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:start", ST_SignedTwipsMeasure
    )
    end: Length | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:end", ST_SignedTwipsMeasure
    )
    firstLine: Length | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:firstLine", ST_TwipsMeasure
    )
    hanging: Length | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:hanging", ST_TwipsMeasure
    )
    leftChars: int | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:leftChars", ST_DecimalNumber
    )
    rightChars: int | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:rightChars", ST_DecimalNumber
    )
    startChars: int | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:startChars", ST_DecimalNumber
    )
    endChars: int | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:endChars", ST_DecimalNumber
    )
    firstLineChars: int | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:firstLineChars", ST_DecimalNumber
    )
    hangingChars: int | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:hangingChars", ST_DecimalNumber
    )


class CT_Jc(BaseOxmlElement):
    """``<w:jc>`` element, specifying paragraph justification."""

    val: WD_ALIGN_PARAGRAPH = RequiredAttribute(  # pyright: ignore[reportAssignmentType]
        "w:val", WD_ALIGN_PARAGRAPH
    )


class CT_TextDirection(BaseOxmlElement):
    """`w:textDirection` element, specifying the flow direction of text.

    One class serves the `w:pPr`, `w:sectPr` and `w:tcPr` occurrences; the element is
    identical in all three.
    """

    val: WD_TEXT_DIRECTION = RequiredAttribute(  # pyright: ignore[reportAssignmentType]
        "w:val", WD_TEXT_DIRECTION
    )


class CT_PBdr(_CT_BordersBase):
    """`w:pBdr` element, the set of border edges of a paragraph.

    Two of the six edges have no table counterpart. `w:between` is the border drawn
    between consecutive paragraphs that share identical border settings, rather than an
    edge of any one paragraph; `w:bar` is the vertical bar drawn beside the paragraph.
    """

    get_or_add_top: Callable[[], CT_Border]
    get_or_add_left: Callable[[], CT_Border]
    get_or_add_bottom: Callable[[], CT_Border]
    get_or_add_right: Callable[[], CT_Border]
    get_or_add_between: Callable[[], CT_Border]
    get_or_add_bar: Callable[[], CT_Border]
    _remove_top: Callable[[], None]
    _remove_left: Callable[[], None]
    _remove_bottom: Callable[[], None]
    _remove_right: Callable[[], None]
    _remove_between: Callable[[], None]
    _remove_bar: Callable[[], None]

    _tag_seq = ("w:top", "w:left", "w:bottom", "w:right", "w:between", "w:bar")
    top: CT_Border | None = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "w:top", successors=_tag_seq[1:]
    )
    left: CT_Border | None = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "w:left", successors=_tag_seq[2:]
    )
    bottom: CT_Border | None = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "w:bottom", successors=_tag_seq[3:]
    )
    right: CT_Border | None = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "w:right", successors=_tag_seq[4:]
    )
    between: CT_Border | None = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "w:between", successors=_tag_seq[5:]
    )
    bar: CT_Border | None = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "w:bar", successors=_tag_seq[6:]
    )

    edges = tuple(tag[2:] for tag in _tag_seq)
    del _tag_seq


class CT_PPr(BaseOxmlElement):
    """``<w:pPr>`` element, containing the properties for a paragraph."""

    get_or_add_bidi: Callable[[], CT_OnOff]
    get_or_add_ind: Callable[[], CT_Ind]
    get_or_add_outlineLvl: Callable[[], CT_DecimalNumber]
    get_or_add_pBdr: Callable[[], CT_PBdr]
    get_or_add_pStyle: Callable[[], CT_String]
    get_or_add_rPr: Callable[[], CT_RPr]
    get_or_add_sectPr: Callable[[], CT_SectPr]
    get_or_add_shd: Callable[[], CT_Shd]
    get_or_add_textDirection: Callable[[], CT_TextDirection]
    _insert_sectPr: Callable[[CT_SectPr], None]
    _remove_bidi: Callable[[], None]
    _remove_outlineLvl: Callable[[], None]
    _remove_pBdr: Callable[[], None]
    _remove_pStyle: Callable[[], None]
    _remove_sectPr: Callable[[], None]
    _remove_shd: Callable[[], None]
    _remove_textDirection: Callable[[], None]

    _tag_seq = (
        "w:pStyle",
        "w:keepNext",
        "w:keepLines",
        "w:pageBreakBefore",
        "w:framePr",
        "w:widowControl",
        "w:numPr",
        "w:suppressLineNumbers",
        "w:pBdr",
        "w:shd",
        "w:tabs",
        "w:suppressAutoHyphens",
        "w:kinsoku",
        "w:wordWrap",
        "w:overflowPunct",
        "w:topLinePunct",
        "w:autoSpaceDE",
        "w:autoSpaceDN",
        "w:bidi",
        "w:adjustRightInd",
        "w:snapToGrid",
        "w:spacing",
        "w:ind",
        "w:contextualSpacing",
        "w:mirrorIndents",
        "w:suppressOverlap",
        "w:jc",
        "w:textDirection",
        "w:textAlignment",
        "w:textboxTightWrap",
        "w:outlineLvl",
        "w:divId",
        "w:cnfStyle",
        "w:rPr",
        "w:sectPr",
        "w:pPrChange",
    )
    pStyle: CT_String | None = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "w:pStyle", successors=_tag_seq[1:]
    )
    keepNext = ZeroOrOne("w:keepNext", successors=_tag_seq[2:])
    keepLines = ZeroOrOne("w:keepLines", successors=_tag_seq[3:])
    pageBreakBefore = ZeroOrOne("w:pageBreakBefore", successors=_tag_seq[4:])
    widowControl = ZeroOrOne("w:widowControl", successors=_tag_seq[6:])
    numPr = ZeroOrOne("w:numPr", successors=_tag_seq[7:])
    pBdr: CT_PBdr | None = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "w:pBdr", successors=_tag_seq[9:]
    )
    shd: CT_Shd | None = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "w:shd", successors=_tag_seq[10:]
    )
    tabs = ZeroOrOne("w:tabs", successors=_tag_seq[11:])
    bidi: CT_OnOff | None = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "w:bidi", successors=_tag_seq[19:]
    )
    spacing = ZeroOrOne("w:spacing", successors=_tag_seq[22:])
    ind: CT_Ind | None = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "w:ind", successors=_tag_seq[23:]
    )
    jc = ZeroOrOne("w:jc", successors=_tag_seq[27:])
    textDirection: CT_TextDirection | None = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "w:textDirection", successors=_tag_seq[28:]
    )
    outlineLvl: CT_DecimalNumber = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "w:outlineLvl", successors=_tag_seq[31:]
    )
    # -- `w:pPr/w:rPr` is `CT_ParaRPr`, not `CT_RPr`: it admits `w:ins`, `w:del`,
    # -- `w:moveFrom` and `w:moveTo` ahead of the run properties. lxml resolves an
    # -- element class by tag name alone, so this arrives typed as `CT_RPr` and no
    # -- separate class is reachable. That is sound for reading and writing the run
    # -- properties themselves, which is all the API exposes; nothing here adds the four
    # -- revision children, which `CT_RPr._tag_seq` does not know how to place.
    rPr: CT_RPr | None = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "w:rPr", successors=_tag_seq[34:]
    )
    sectPr = ZeroOrOne("w:sectPr", successors=_tag_seq[35:])
    del _tag_seq

    @property
    def outlineLvl_val(self) -> int | None:
        """Value of `./w:outlineLvl/@w:val`, or |None| if not present."""
        outlineLvl = self.outlineLvl
        if outlineLvl is None:
            return None
        return outlineLvl.val

    @outlineLvl_val.setter
    def outlineLvl_val(self, value: int | None) -> None:
        if value is None:
            self._remove_outlineLvl()
            return
        self.get_or_add_outlineLvl().val = value

    @property
    def shd_fill(self) -> RGBColor | str | None:
        """Value of `./w:shd/@w:fill`, or |None| when there is none.

        |None| both when there is no `w:shd` at all and when it carries a pattern but no
        fill, which is valid — `<w:shd w:val="pct25" w:color="FF0000"/>` for instance.
        """
        shd = self.shd
        if shd is None:
            return None
        return shd.fill

    @shd_fill.setter
    def shd_fill(self, value: RGBColor | str | None) -> None:
        if value is None:
            self._remove_shd()
            return
        if isinstance(value, str) and value != "auto":
            value = RGBColor.from_string(value)
        shd = self.get_or_add_shd()
        _ensure_shd_val(shd)
        shd.fill = value

    @property
    def shd_val(self) -> WD_SHADING_PATTERN | None:
        """The `w:shd/@w:val` shading pattern, or |None| when no shading is applied."""
        return _shd_val(self.shd)

    @shd_val.setter
    def shd_val(self, value: WD_SHADING_PATTERN | None) -> None:
        if value is None:
            self._remove_shd()
            return
        self.get_or_add_shd().val = value

    @property
    def shd_color(self) -> RGBColor | str | None:
        """Value of `./w:shd/@w:color`, the pattern foreground, or |None|."""
        shd = self.shd
        if shd is None:
            return None
        return shd.color

    @shd_color.setter
    def shd_color(self, value: RGBColor | str | None) -> None:
        if value is None:
            if self.shd is not None:
                self.shd.color = None
            return
        if isinstance(value, str) and value != "auto":
            value = RGBColor.from_string(value)
        shd = self.get_or_add_shd()
        _ensure_shd_val(shd)
        shd.color = value

    @property
    def first_line_indent(self) -> Length | None:
        """A |Length| value calculated from the values of `w:ind/@w:firstLine` and
        `w:ind/@w:hanging`.

        Returns |None| if the `w:ind` child is not present.
        """
        ind = self.ind
        if ind is None:
            return None
        hanging = ind.hanging
        if hanging is not None:
            return Length(-hanging)
        firstLine = ind.firstLine
        if firstLine is None:
            return None
        return firstLine

    @first_line_indent.setter
    def first_line_indent(self, value: Length | None):
        if self.ind is None and value is None:
            return
        ind = self.get_or_add_ind()
        ind.firstLine = ind.hanging = None
        # -- Word prefers the character-unit value where both are present, so a stale
        # -- `w:firstLineChars` would silently win over what was just assigned. --
        ind.firstLineChars = ind.hangingChars = None
        if value is None:
            return
        elif value < 0:
            ind.hanging = -value
        else:
            ind.firstLine = value

    @property
    def first_line_indent_chars(self) -> int | None:
        """The first-line indent in hundredths of a character, or |None| if not present.

        Derived from `w:ind/@w:firstLineChars` and `@w:hangingChars` the way
        `.first_line_indent` is derived from their twips counterparts: a negative value
        means a hanging indent.
        """
        ind = self.ind
        if ind is None:
            return None
        hangingChars = ind.hangingChars
        if hangingChars is not None:
            return -hangingChars
        return ind.firstLineChars

    @first_line_indent_chars.setter
    def first_line_indent_chars(self, value: int | None) -> None:
        if self.ind is None and value is None:
            return
        ind = self.get_or_add_ind()
        # -- Word prefers the `Chars` value over its twips sibling, so leaving the two
        # -- disagreeing silently changes the layout; clear the sibling as well.
        ind.firstLineChars = ind.hangingChars = None
        ind.firstLine = ind.hanging = None
        if value is None:
            return
        elif value < 0:
            ind.hangingChars = -value
        else:
            ind.firstLineChars = value

    @property
    def ind_left(self) -> Length | None:
        """The value of `w:ind/@w:left` or |None| if not present.

        Falls back to `@w:start`, the writing-direction synonym Word writes in files
        saved by recent versions.
        """
        ind = self.ind
        if ind is None:
            return None
        return ind.left if ind.left is not None else ind.start

    @ind_left.setter
    def ind_left(self, value: Length | None):
        if value is None and self.ind is None:
            return
        ind = self.get_or_add_ind()
        ind.left = value
        ind.start = None
        ind.leftChars = ind.startChars = None

    @property
    def ind_right(self) -> Length | None:
        """The value of `w:ind/@w:right` or |None| if not present.

        Falls back to `@w:end`, the writing-direction synonym.
        """
        ind = self.ind
        if ind is None:
            return None
        return ind.right if ind.right is not None else ind.end

    @ind_right.setter
    def ind_right(self, value: Length | None):
        if value is None and self.ind is None:
            return
        ind = self.get_or_add_ind()
        ind.right = value
        ind.end = None
        ind.rightChars = ind.endChars = None

    @property
    def ind_left_chars(self) -> int | None:
        """`w:ind/@w:leftChars` in hundredths of a character, or |None| if not present.

        Falls back to `@w:startChars`, its writing-direction synonym.
        """
        ind = self.ind
        if ind is None:
            return None
        return ind.leftChars if ind.leftChars is not None else ind.startChars

    @ind_left_chars.setter
    def ind_left_chars(self, value: int | None) -> None:
        if value is None and self.ind is None:
            return
        ind = self.get_or_add_ind()
        ind.leftChars = value
        ind.startChars = None
        ind.left = ind.start = None

    @property
    def ind_right_chars(self) -> int | None:
        """`w:ind/@w:rightChars` in hundredths of a character, or |None| if not present.

        Falls back to `@w:endChars`, its writing-direction synonym.
        """
        ind = self.ind
        if ind is None:
            return None
        return ind.rightChars if ind.rightChars is not None else ind.endChars

    @ind_right_chars.setter
    def ind_right_chars(self, value: int | None) -> None:
        if value is None and self.ind is None:
            return
        ind = self.get_or_add_ind()
        ind.rightChars = value
        ind.endChars = None
        ind.right = ind.end = None

    @property
    def bidi_val(self) -> bool | None:
        """Value of `./w:bidi/@w:val`, or |None| if the element is absent."""
        bidi = self.bidi
        return None if bidi is None else bidi.val

    @bidi_val.setter
    def bidi_val(self, value: bool | None) -> None:
        if value is None:
            self._remove_bidi()
            return
        self.get_or_add_bidi().val = value

    @property
    def textDirection_val(self) -> WD_TEXT_DIRECTION | None:
        """Value of `./w:textDirection/@w:val`, or |None| if the element is absent."""
        textDirection = self.textDirection
        return None if textDirection is None else textDirection.val

    @textDirection_val.setter
    def textDirection_val(self, value: WD_TEXT_DIRECTION | None) -> None:
        if value is None:
            self._remove_textDirection()
            return
        self.get_or_add_textDirection().val = value

    @property
    def jc_val(self) -> WD_ALIGN_PARAGRAPH | None:
        """Value of the `<w:jc>` child element or |None| if not present."""
        return self.jc.val if self.jc is not None else None

    @jc_val.setter
    def jc_val(self, value):
        if value is None:
            self._remove_jc()
            return
        self.get_or_add_jc().val = value

    @property
    def keepLines_val(self):
        """The value of `keepLines/@val` or |None| if not present."""
        keepLines = self.keepLines
        if keepLines is None:
            return None
        return keepLines.val

    @keepLines_val.setter
    def keepLines_val(self, value):
        if value is None:
            self._remove_keepLines()
        else:
            self.get_or_add_keepLines().val = value

    @property
    def keepNext_val(self):
        """The value of `keepNext/@val` or |None| if not present."""
        keepNext = self.keepNext
        if keepNext is None:
            return None
        return keepNext.val

    @keepNext_val.setter
    def keepNext_val(self, value):
        if value is None:
            self._remove_keepNext()
        else:
            self.get_or_add_keepNext().val = value

    @property
    def pageBreakBefore_val(self):
        """The value of `pageBreakBefore/@val` or |None| if not present."""
        pageBreakBefore = self.pageBreakBefore
        if pageBreakBefore is None:
            return None
        return pageBreakBefore.val

    @pageBreakBefore_val.setter
    def pageBreakBefore_val(self, value):
        if value is None:
            self._remove_pageBreakBefore()
        else:
            self.get_or_add_pageBreakBefore().val = value

    @property
    def spacing_after(self):
        """The value of `w:spacing/@w:after` or |None| if not present."""
        spacing = self.spacing
        if spacing is None:
            return None
        return spacing.after

    @spacing_after.setter
    def spacing_after(self, value):
        if value is None and self.spacing is None:
            return
        self.get_or_add_spacing().after = value

    @property
    def spacing_before(self):
        """The value of `w:spacing/@w:before` or |None| if not present."""
        spacing = self.spacing
        if spacing is None:
            return None
        return spacing.before

    @spacing_before.setter
    def spacing_before(self, value):
        if value is None and self.spacing is None:
            return
        self.get_or_add_spacing().before = value

    @property
    def spacing_after_lines(self) -> int | None:
        """`w:spacing/@w:afterLines` in hundredths of a line, or |None| if not present."""
        spacing = self.spacing
        return None if spacing is None else spacing.afterLines

    @spacing_after_lines.setter
    def spacing_after_lines(self, value: int | None) -> None:
        if value is None and self.spacing is None:
            return
        self.get_or_add_spacing().afterLines = value

    @property
    def spacing_before_lines(self) -> int | None:
        """`w:spacing/@w:beforeLines` in hundredths of a line, or |None| if not present."""
        spacing = self.spacing
        return None if spacing is None else spacing.beforeLines

    @spacing_before_lines.setter
    def spacing_before_lines(self, value: int | None) -> None:
        if value is None and self.spacing is None:
            return
        self.get_or_add_spacing().beforeLines = value

    @property
    def spacing_line(self):
        """The value of `w:spacing/@w:line` or |None| if not present."""
        spacing = self.spacing
        if spacing is None:
            return None
        return spacing.line

    @spacing_line.setter
    def spacing_line(self, value):
        if value is None and self.spacing is None:
            return
        self.get_or_add_spacing().line = value

    @property
    def spacing_lineRule(self):
        """The value of `w:spacing/@w:lineRule` as a member of the :ref:`WdLineSpacing`
        enumeration.

        Only the `MULTIPLE`, `EXACTLY`, and `AT_LEAST` members are used. It is the
        responsibility of the client to calculate the use of `SINGLE`, `DOUBLE`, and
        `MULTIPLE` based on the value of `w:spacing/@w:line` if that behavior is
        desired.
        """
        spacing = self.spacing
        if spacing is None:
            return None
        lineRule = spacing.lineRule
        if lineRule is None and spacing.line is not None:
            return WD_LINE_SPACING.MULTIPLE
        return lineRule

    @spacing_lineRule.setter
    def spacing_lineRule(self, value):
        if value is None and self.spacing is None:
            return
        self.get_or_add_spacing().lineRule = value

    @property
    def style(self) -> str | None:
        """String contained in `./w:pStyle/@val`, or None if child is not present."""
        pStyle = self.pStyle
        if pStyle is None:
            return None
        return pStyle.val

    @style.setter
    def style(self, style: str | None):
        """Set `./w:pStyle/@val` `style`, adding a new element if necessary.

        If `style` is |None|, remove `./w:pStyle` when present.
        """
        if style is None:
            self._remove_pStyle()
            return
        pStyle = self.get_or_add_pStyle()
        pStyle.val = style

    @property
    def widowControl_val(self):
        """The value of `widowControl/@val` or |None| if not present."""
        widowControl = self.widowControl
        if widowControl is None:
            return None
        return widowControl.val

    @widowControl_val.setter
    def widowControl_val(self, value):
        if value is None:
            self._remove_widowControl()
        else:
            self.get_or_add_widowControl().val = value


class CT_Spacing(BaseOxmlElement):
    """``<w:spacing>`` element, specifying paragraph spacing attributes such as space
    before and line spacing.

    `w:beforeLines` and `w:afterLines` are the line-relative counterparts of `w:before`
    and `w:after`, in hundredths of a line. Like the `*Chars` attributes on `w:ind` they
    are not |Length| values — a line has no fixed height.
    """

    after = OptionalAttribute("w:after", ST_TwipsMeasure)
    before = OptionalAttribute("w:before", ST_TwipsMeasure)
    afterLines: int | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:afterLines", ST_DecimalNumber
    )
    beforeLines: int | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:beforeLines", ST_DecimalNumber
    )
    line = OptionalAttribute("w:line", ST_SignedTwipsMeasure)
    lineRule = OptionalAttribute("w:lineRule", WD_LINE_SPACING)


class CT_TabStop(BaseOxmlElement):
    """`<w:tab>` element, representing an individual tab stop.

    Overloaded to use for a tab-character in a run, which also uses the w:tab tag but
    only needs a __str__ method.
    """

    val: WD_TAB_ALIGNMENT = RequiredAttribute(  # pyright: ignore[reportAssignmentType]
        "w:val", WD_TAB_ALIGNMENT
    )
    leader: WD_TAB_LEADER | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:leader", WD_TAB_LEADER, default=WD_TAB_LEADER.SPACES
    )
    pos: Length = RequiredAttribute(  # pyright: ignore[reportAssignmentType]
        "w:pos", ST_SignedTwipsMeasure
    )

    def __str__(self) -> str:
        """Text equivalent of a `w:tab` element appearing in a run.

        Allows text of run inner-content to be accessed consistently across all text
        inner-content.
        """
        return "\t"


class CT_TabStops(BaseOxmlElement):
    """``<w:tabs>`` element, container for a sorted sequence of tab stops."""

    tab = OneOrMore("w:tab", successors=())

    def insert_tab_in_order(self, pos, align, leader):
        """Insert a newly created `w:tab` child element in `pos` order."""
        new_tab = self._new_tab()
        new_tab.pos, new_tab.val, new_tab.leader = pos, align, leader
        for tab in self.tab_lst:
            if new_tab.pos < tab.pos:
                tab.addprevious(new_tab)
                return new_tab
        self.append(new_tab)
        return new_tab
