"""Paragraph-related proxy types."""

from __future__ import annotations

from typing import TYPE_CHECKING

from docx.borders import _Borders  # pyright: ignore[reportPrivateUsage]
from docx.enum.text import WD_LINE_SPACING, WD_SHADING_PATTERN
from docx.oxml.text.parfmt import CT_PBdr
from docx.shared import ElementProxy, Emu, Length, Pt, Twips, lazyproperty
from docx.text.font import Font
from docx.text.tabstops import TabStops

if TYPE_CHECKING:
    from docx.enum.text import WD_TEXT_DIRECTION
    from docx.oxml.table import _CT_BordersBase  # pyright: ignore[reportPrivateUsage]
    from docx.oxml.text.parfmt import CT_PPr


class _ParagraphBorders(_Borders):
    """The border edges of a paragraph, `paragraph_format.borders`."""

    def __init__(self, parfmt: ParagraphFormat):
        super().__init__(CT_PBdr.edges)
        self._parfmt = parfmt

    def clear(self) -> None:
        pPr = self._pPr
        if pPr is not None:
            pPr._remove_pBdr()  # pyright: ignore[reportPrivateUsage]

    @property
    def _element(self) -> _CT_BordersBase | None:
        pPr = self._pPr
        return None if pPr is None else pPr.pBdr

    def _get_or_add_element(self) -> _CT_BordersBase:
        return self._parfmt._element.get_or_add_pPr().get_or_add_pBdr()

    @property
    def _pPr(self) -> CT_PPr | None:
        return self._parfmt._element.pPr


class ParagraphFormat(ElementProxy):
    """Provides access to paragraph formatting such as justification, indentation, line
    spacing, space before and after, and widow/orphan control."""

    @property
    def alignment(self):
        """A member of the :ref:`WdParagraphAlignment` enumeration specifying the
        justification setting for this paragraph.

        A value of |None| indicates paragraph alignment is inherited from the style
        hierarchy.
        """
        pPr = self._element.pPr
        if pPr is None:
            return None
        return pPr.jc_val

    @alignment.setter
    def alignment(self, value):
        pPr = self._element.get_or_add_pPr()
        pPr.jc_val = value

    @property
    def first_line_indent(self):
        """|Length| value specifying the relative difference in indentation for the
        first line of the paragraph.

        A positive value causes the first line to be indented. A negative value produces
        a hanging indent. |None| indicates first line indentation is inherited from the
        style hierarchy.
        """
        pPr = self._element.pPr
        if pPr is None:
            return None
        return pPr.first_line_indent

    @first_line_indent.setter
    def first_line_indent(self, value):
        pPr = self._element.get_or_add_pPr()
        pPr.first_line_indent = value

    @property
    def bidi(self) -> bool | None:
        """|True| when this paragraph's base direction is right-to-left.

        This is the paragraph's *reading* direction — which edge the text starts from,
        where the punctuation lands, which way the indents and the list bullet face.
        Setting `Font.rtl` on the runs is not a substitute: the runs render right-to-left
        inside a paragraph still laid out left-to-right, which is subtly rather than
        obviously wrong.

        |None| indicates the value is inherited, from the section's own `bidi` and
        ultimately from the style hierarchy — it does not mean |False|.
        """
        pPr = self._element.pPr
        return None if pPr is None else pPr.bidi_val

    @bidi.setter
    def bidi(self, value: bool | None) -> None:
        if value is None and self._element.pPr is None:
            return
        self._element.get_or_add_pPr().bidi_val = value

    @lazyproperty
    def borders(self) -> _ParagraphBorders:
        """The border edges of this paragraph, as a mapping keyed by edge name::

            paragraph.paragraph_format.borders["bottom"].line = WD_LINE_STYLE.SINGLE

        A paragraph with only a bottom border and no text is how Word draws a horizontal
        rule; there is no other way to draw one.

        Beyond the four sides, a paragraph admits two edges a table does not. `between`
        is the border drawn *between* consecutive paragraphs that share identical border
        settings, rather than an edge of any one paragraph, and `bar` is the vertical bar
        drawn beside it.
        """
        return _ParagraphBorders(self)

    @property
    def first_line_indent_chars(self) -> int | None:
        """First-line indent in hundredths of a character, or |None| when not set.

        The character-unit counterpart of :attr:`first_line_indent`. Word's paragraph
        dialogue offers "2 ch" as the first-line indent unit for a CJK document and
        writes `w:firstLineChars="200"`, often with no twips companion — on such a
        document :attr:`first_line_indent` is |None| although Word plainly shows an
        indent.

        **The value is in hundredths**, matching the XML: 2 characters reads as ``200``,
        not ``2.0``. These are deliberately not |Length| values, since a character has
        no fixed size and nothing on |Length| could express one.

        A negative value means a hanging indent, as for :attr:`first_line_indent`.
        Assigning clears the twips attributes, because Word prefers the character value
        where both are present and leaving the two disagreeing changes the layout.
        """
        pPr = self._element.pPr
        return None if pPr is None else pPr.first_line_indent_chars

    @first_line_indent_chars.setter
    def first_line_indent_chars(self, value: int | None) -> None:
        if value is None and self._element.pPr is None:
            return
        self._element.get_or_add_pPr().first_line_indent_chars = value

    @property
    def left_indent_chars(self) -> int | None:
        """Left indent in hundredths of a character, or |None| when not set.

        See :attr:`first_line_indent_chars` for the unit. Assigning clears the twips
        sibling.
        """
        pPr = self._element.pPr
        return None if pPr is None else pPr.ind_left_chars

    @left_indent_chars.setter
    def left_indent_chars(self, value: int | None) -> None:
        if value is None and self._element.pPr is None:
            return
        self._element.get_or_add_pPr().ind_left_chars = value

    @lazyproperty
    def mark_font(self) -> Font:
        """The run properties of the paragraph mark — the ¶ itself.

        These are neither the properties of any run in the paragraph nor the paragraph's
        style: they are the formatting of the mark character, stored in `w:pPr/w:rPr`::

            paragraph.paragraph_format.mark_font.size = Pt(8)

        It matters more than it sounds. The mark's font size participates in the line
        height of the paragraph's last line, so a paragraph whose runs are all 8pt but
        whose mark is 24pt renders with a tall final line. An empty paragraph has no runs
        at all, so the mark's properties are the only place its formatting lives — the
        height of a blank spacer paragraph is not expressible any other way. And
        assigning `Paragraph.text` discards the runs and rebuilds them while the mark's
        properties survive, which can leave a rewritten paragraph looking wrong.

        Named `mark_font` rather than `font` because "the paragraph's font" reads as the
        font of the paragraph's text, which this is not.
        """
        return Font(self._element.get_or_add_pPr())  # pyright: ignore[reportArgumentType]

    @property
    def right_indent_chars(self) -> int | None:
        """Right indent in hundredths of a character, or |None| when not set.

        See :attr:`first_line_indent_chars` for the unit. Assigning clears the twips
        sibling.
        """
        pPr = self._element.pPr
        return None if pPr is None else pPr.ind_right_chars

    @right_indent_chars.setter
    def right_indent_chars(self, value: int | None) -> None:
        if value is None and self._element.pPr is None:
            return
        self._element.get_or_add_pPr().ind_right_chars = value

    @property
    def space_after_lines(self) -> int | None:
        """Space after the paragraph in hundredths of a line, or |None| when not set.

        The line-relative counterpart of :attr:`space_after`, in the same hundredths unit
        as :attr:`first_line_indent_chars` — ``50`` is half a line. Word writes this for
        a CJK document alongside, or instead of, the twips value.
        """
        pPr = self._element.pPr
        return None if pPr is None else pPr.spacing_after_lines

    @space_after_lines.setter
    def space_after_lines(self, value: int | None) -> None:
        if value is None and self._element.pPr is None:
            return
        self._element.get_or_add_pPr().spacing_after_lines = value

    @property
    def space_before_lines(self) -> int | None:
        """Space before the paragraph in hundredths of a line, or |None| when not set.

        See :attr:`space_after_lines`.
        """
        pPr = self._element.pPr
        return None if pPr is None else pPr.spacing_before_lines

    @space_before_lines.setter
    def space_before_lines(self, value: int | None) -> None:
        if value is None and self._element.pPr is None:
            return
        self._element.get_or_add_pPr().spacing_before_lines = value

    @property
    def text_direction(self) -> WD_TEXT_DIRECTION | None:
        """Flow direction of the text in this paragraph, or |None| when inherited.

        This is the vertical-writing knob, and a different thing from :attr:`bidi`: it
        says which way the lines run and whether the glyphs are rotated, not which
        direction the text reads in.
        """
        pPr = self._element.pPr
        return None if pPr is None else pPr.textDirection_val

    @text_direction.setter
    def text_direction(self, value: WD_TEXT_DIRECTION | None) -> None:
        if value is None and self._element.pPr is None:
            return
        self._element.get_or_add_pPr().textDirection_val = value

    @property
    def keep_together(self):
        """|True| if the paragraph should be kept "in one piece" and not broken across a
        page boundary when the document is rendered.

        |None| indicates its effective value is inherited from the style hierarchy.
        """
        pPr = self._element.pPr
        if pPr is None:
            return None
        return pPr.keepLines_val

    @keep_together.setter
    def keep_together(self, value):
        self._element.get_or_add_pPr().keepLines_val = value

    @property
    def keep_with_next(self):
        """|True| if the paragraph should be kept on the same page as the subsequent
        paragraph when the document is rendered.

        For example, this property could be used to keep a section heading on the same
        page as its first paragraph. |None| indicates its effective value is inherited
        from the style hierarchy.
        """
        pPr = self._element.pPr
        if pPr is None:
            return None
        return pPr.keepNext_val

    @keep_with_next.setter
    def keep_with_next(self, value):
        self._element.get_or_add_pPr().keepNext_val = value

    @property
    def left_indent(self):
        """|Length| value specifying the space between the left margin and the left side
        of the paragraph.

        |None| indicates the left indent value is inherited from the style hierarchy.
        Use an |Inches| value object as a convenient way to apply indentation in units
        of inches.
        """
        pPr = self._element.pPr
        if pPr is None:
            return None
        return pPr.ind_left

    @left_indent.setter
    def left_indent(self, value):
        pPr = self._element.get_or_add_pPr()
        pPr.ind_left = value

    @property
    def line_spacing(self):
        """|float| or |Length| value specifying the space between baselines in
        successive lines of the paragraph.

        A value of |None| indicates line spacing is inherited from the style hierarchy.
        A float value, e.g. ``2.0`` or ``1.75``, indicates spacing is applied in
        multiples of line heights. A |Length| value such as ``Pt(12)`` indicates spacing
        is a fixed height. The |Pt| value class is a convenient way to apply line
        spacing in units of points. Assigning |None| resets line spacing to inherit from
        the style hierarchy.
        """
        pPr = self._element.pPr
        if pPr is None:
            return None
        return self._line_spacing(pPr.spacing_line, pPr.spacing_lineRule)

    @line_spacing.setter
    def line_spacing(self, value):
        pPr = self._element.get_or_add_pPr()
        if value is None:
            pPr.spacing_line = None
            pPr.spacing_lineRule = None
        elif isinstance(value, Length):
            pPr.spacing_line = value
            if pPr.spacing_lineRule != WD_LINE_SPACING.AT_LEAST:
                pPr.spacing_lineRule = WD_LINE_SPACING.EXACTLY
        else:
            pPr.spacing_line = Emu(value * Twips(240))
            pPr.spacing_lineRule = WD_LINE_SPACING.MULTIPLE

    @property
    def line_spacing_rule(self):
        """A member of the :ref:`WdLineSpacing` enumeration indicating how the value of
        :attr:`line_spacing` should be interpreted.

        Assigning any of the :ref:`WdLineSpacing` members :attr:`SINGLE`,
        :attr:`DOUBLE`, or :attr:`ONE_POINT_FIVE` will cause the value of
        :attr:`line_spacing` to be updated to produce the corresponding line spacing.
        """
        pPr = self._element.pPr
        if pPr is None:
            return None
        return self._line_spacing_rule(pPr.spacing_line, pPr.spacing_lineRule)

    @line_spacing_rule.setter
    def line_spacing_rule(self, value):
        pPr = self._element.get_or_add_pPr()
        if value == WD_LINE_SPACING.SINGLE:
            pPr.spacing_line = Twips(240)
            pPr.spacing_lineRule = WD_LINE_SPACING.MULTIPLE
        elif value == WD_LINE_SPACING.ONE_POINT_FIVE:
            pPr.spacing_line = Twips(360)
            pPr.spacing_lineRule = WD_LINE_SPACING.MULTIPLE
        elif value == WD_LINE_SPACING.DOUBLE:
            pPr.spacing_line = Twips(480)
            pPr.spacing_lineRule = WD_LINE_SPACING.MULTIPLE
        else:
            pPr.spacing_lineRule = value

    @property
    def outline_level(self) -> int | None:
        """Outline level of this paragraph, from 0 (top level) to 9.

        The outline level drives the document map that navigation panes and PDF
        bookmarks are built from. Level 9 is Word's "Body Text", meaning the paragraph
        is deliberately excluded from the outline; |None| means no level is set here and
        the effective value is inherited from the style hierarchy.

        Setting this does not change how the paragraph is rendered.
        """
        pPr = self._element.pPr
        if pPr is None:
            return None
        return pPr.outlineLvl_val

    @outline_level.setter
    def outline_level(self, value: int | None) -> None:
        if value is not None and not 0 <= value <= 9:
            raise ValueError("outline level must be in range 0 to 9, got %r" % (value,))
        self._element.get_or_add_pPr().outlineLvl_val = value

    @property
    def shading_fill(self):
        """Background shading color applied behind the whole paragraph.

        An |RGBColor| value, the string "auto", or |None| when no shading is applied.
        Assigning a hex string such as "FF0000" or "#FF0000" is also accepted.

        Use `Font.shading_fill` to shade individual runs instead.
        """
        pPr = self._element.pPr
        if pPr is None:
            return None
        return pPr.shd_fill

    @shading_fill.setter
    def shading_fill(self, value) -> None:
        self._element.get_or_add_pPr().shd_fill = value

    @property
    def shading_pattern(self) -> WD_SHADING_PATTERN | None:
        """The pattern drawn over the shading behind the whole paragraph.

        A |WD_SHADING_PATTERN| member, or |None| when no shading is applied. Word writes
        |WD_SHADING_PATTERN.CLEAR| for an ordinary background color, which is what
        `.shading_fill` produces on its own.

        Assigning |None| removes the shading entirely, the same as assigning |None| to
        `.shading_fill`.
        """
        pPr = self._element.pPr
        if pPr is None:
            return None
        return pPr.shd_val

    @shading_pattern.setter
    def shading_pattern(self, value: WD_SHADING_PATTERN | None) -> None:
        self._element.get_or_add_pPr().shd_val = value

    @property
    def shading_color(self):
        """The foreground color of the shading pattern behind this paragraph.

        An |RGBColor| value, the string "auto", or |None|. This is the color the
        `.shading_pattern` is drawn *in*; `.shading_fill` is the color behind it. For
        the usual |WD_SHADING_PATTERN.CLEAR| pattern nothing is drawn and this has no
        visible effect.
        """
        pPr = self._element.pPr
        if pPr is None:
            return None
        return pPr.shd_color

    @shading_color.setter
    def shading_color(self, value) -> None:
        self._element.get_or_add_pPr().shd_color = value

    @property
    def page_break_before(self):
        """|True| if the paragraph should appear at the top of the page following the
        prior paragraph.

        |None| indicates its effective value is inherited from the style hierarchy.
        """
        pPr = self._element.pPr
        if pPr is None:
            return None
        return pPr.pageBreakBefore_val

    @page_break_before.setter
    def page_break_before(self, value):
        self._element.get_or_add_pPr().pageBreakBefore_val = value

    @property
    def right_indent(self):
        """|Length| value specifying the space between the right margin and the right
        side of the paragraph.

        |None| indicates the right indent value is inherited from the style hierarchy.
        Use a |Cm| value object as a convenient way to apply indentation in units of
        centimeters.
        """
        pPr = self._element.pPr
        if pPr is None:
            return None
        return pPr.ind_right

    @right_indent.setter
    def right_indent(self, value):
        pPr = self._element.get_or_add_pPr()
        pPr.ind_right = value

    @property
    def space_after(self):
        """|Length| value specifying the spacing to appear between this paragraph and
        the subsequent paragraph.

        |None| indicates this value is inherited from the style hierarchy. |Length|
        objects provide convenience properties, such as :attr:`~.Length.pt` and
        :attr:`~.Length.inches`, that allow easy conversion to various length units.
        """
        pPr = self._element.pPr
        if pPr is None:
            return None
        return pPr.spacing_after

    @space_after.setter
    def space_after(self, value):
        self._element.get_or_add_pPr().spacing_after = value

    @property
    def space_before(self):
        """|Length| value specifying the spacing to appear between this paragraph and
        the prior paragraph.

        |None| indicates this value is inherited from the style hierarchy. |Length|
        objects provide convenience properties, such as :attr:`~.Length.pt` and
        :attr:`~.Length.cm`, that allow easy conversion to various length units.
        """
        pPr = self._element.pPr
        if pPr is None:
            return None
        return pPr.spacing_before

    @space_before.setter
    def space_before(self, value):
        self._element.get_or_add_pPr().spacing_before = value

    @lazyproperty
    def tab_stops(self):
        """|TabStops| object providing access to the tab stops defined for this
        paragraph format."""
        pPr = self._element.get_or_add_pPr()
        return TabStops(pPr)

    @property
    def widow_control(self):
        """|True| if the first and last lines in the paragraph remain on the same page
        as the rest of the paragraph when Word repaginates the document.

        |None| indicates its effective value is inherited from the style hierarchy.
        """
        pPr = self._element.pPr
        if pPr is None:
            return None
        return pPr.widowControl_val

    @widow_control.setter
    def widow_control(self, value):
        self._element.get_or_add_pPr().widowControl_val = value

    @staticmethod
    def _line_spacing(spacing_line, spacing_lineRule):
        """Return the line spacing value calculated from the combination of
        `spacing_line` and `spacing_lineRule`.

        Returns a |float| number of lines when `spacing_lineRule` is
        ``WD_LINE_SPACING.MULTIPLE``, otherwise a |Length| object of absolute line
        height is returned. Returns |None| when `spacing_line` is |None|.
        """
        if spacing_line is None:
            return None
        if spacing_lineRule == WD_LINE_SPACING.MULTIPLE:
            return spacing_line / Pt(12)
        return spacing_line

    @staticmethod
    def _line_spacing_rule(line, lineRule):
        """Return the line spacing rule value calculated from the combination of `line`
        and `lineRule`.

        Returns special members of the :ref:`WdLineSpacing` enumeration when line
        spacing is single, double, or 1.5 lines.
        """
        if lineRule == WD_LINE_SPACING.MULTIPLE:
            if line == Twips(240):
                return WD_LINE_SPACING.SINGLE
            if line == Twips(360):
                return WD_LINE_SPACING.ONE_POINT_FIVE
            if line == Twips(480):
                return WD_LINE_SPACING.DOUBLE
        return lineRule
