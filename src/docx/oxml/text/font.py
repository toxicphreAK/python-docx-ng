# pyright: reportAssignmentType=false

"""Custom element classes related to run properties (font)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from docx.enum.dml import MSO_THEME_COLOR
from docx.enum.text import WD_COLOR_INDEX, WD_FONT_HINT, WD_UNDERLINE
from docx.oxml.ns import nsdecls
from docx.oxml.parser import parse_xml
from docx.oxml.simpletypes import (
    ST_HexColor,
    ST_HpsMeasure,
    ST_String,
    ST_TextScalePercent,
    ST_VerticalAlignRun,
)
from docx.oxml.xmlchemy import (
    BaseOxmlElement,
    OptionalAttribute,
    RequiredAttribute,
    ZeroOrOne,
)
from docx.shared import RGBColor

if TYPE_CHECKING:
    from docx.oxml.shared import CT_OnOff, CT_String
    from docx.shared import Length


class CT_Color(BaseOxmlElement):
    """`w:color` element, specifying the color of a font and perhaps other objects."""

    val: RGBColor | str = RequiredAttribute("w:val", ST_HexColor)
    themeColor: MSO_THEME_COLOR | None = OptionalAttribute("w:themeColor", MSO_THEME_COLOR)


class CT_Fonts(BaseOxmlElement):
    """`<w:rFonts>` element.

    Specifies typeface name for the various language types. The four independent slots —
    `w:ascii`, `w:hAnsi`, `w:eastAsia` and `w:cs` — are chosen between per character by
    Word, according to the script the character belongs to.
    """

    hint: WD_FONT_HINT | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:hint", WD_FONT_HINT
    )
    ascii: str | None = OptionalAttribute("w:ascii", ST_String)
    hAnsi: str | None = OptionalAttribute("w:hAnsi", ST_String)
    eastAsia: str | None = OptionalAttribute("w:eastAsia", ST_String)
    cs: str | None = OptionalAttribute("w:cs", ST_String)
    asciiTheme: str | None = OptionalAttribute("w:asciiTheme", ST_String)
    hAnsiTheme: str | None = OptionalAttribute("w:hAnsiTheme", ST_String)
    eastAsiaTheme: str | None = OptionalAttribute("w:eastAsiaTheme", ST_String)
    cstheme: str | None = OptionalAttribute("w:cstheme", ST_String)


class CT_Highlight(BaseOxmlElement):
    """`w:highlight` element, specifying font highlighting/background color."""

    val: WD_COLOR_INDEX = RequiredAttribute("w:val", WD_COLOR_INDEX)


class CT_Shd(BaseOxmlElement):
    """`w:shd` element, specifying the shading (background fill) behind content."""

    fill: RGBColor | str = RequiredAttribute("w:fill", ST_HexColor)


class CT_TextScale(BaseOxmlElement):
    """`w:w` element, specifying horizontal character scaling as a percentage."""

    val: int = RequiredAttribute("w:val", ST_TextScalePercent)


class CT_HpsMeasure(BaseOxmlElement):
    """Used for `<w:sz>` element and others, specifying font size in half-points."""

    val: Length = RequiredAttribute("w:val", ST_HpsMeasure)


class CT_RPr(BaseOxmlElement):
    """`<w:rPr>` element, containing the properties for a run."""

    get_or_add_color: Callable[[], CT_Color]
    get_or_add_highlight: Callable[[], CT_Highlight]
    get_or_add_rFonts: Callable[[], CT_Fonts]
    get_or_add_shd: Callable[[], CT_Shd]
    get_or_add_sz: Callable[[], CT_HpsMeasure]
    get_or_add_szCs: Callable[[], CT_HpsMeasure]
    get_or_add_vertAlign: Callable[[], CT_VerticalAlignRun]
    get_or_add_w: Callable[[], CT_TextScale]
    _add_rStyle: Callable[..., CT_String]
    _add_u: Callable[[], CT_Underline]
    _remove_color: Callable[[], None]
    _remove_highlight: Callable[[], None]
    _remove_rFonts: Callable[[], None]
    _remove_rStyle: Callable[[], None]
    _remove_shd: Callable[[], None]
    _remove_sz: Callable[[], None]
    _remove_szCs: Callable[[], None]
    _remove_u: Callable[[], None]
    _remove_vertAlign: Callable[[], None]
    _remove_w: Callable[[], None]

    _tag_seq = (
        "w:rStyle",
        "w:rFonts",
        "w:b",
        "w:bCs",
        "w:i",
        "w:iCs",
        "w:caps",
        "w:smallCaps",
        "w:strike",
        "w:dstrike",
        "w:outline",
        "w:shadow",
        "w:emboss",
        "w:imprint",
        "w:noProof",
        "w:snapToGrid",
        "w:vanish",
        "w:webHidden",
        "w:color",
        "w:spacing",
        "w:w",
        "w:kern",
        "w:position",
        "w:sz",
        "w:szCs",
        "w:highlight",
        "w:u",
        "w:effect",
        "w:bdr",
        "w:shd",
        "w:fitText",
        "w:vertAlign",
        "w:rtl",
        "w:cs",
        "w:em",
        "w:lang",
        "w:eastAsianLayout",
        "w:specVanish",
        "w:oMath",
    )
    rStyle: CT_String | None = ZeroOrOne("w:rStyle", successors=_tag_seq[1:])
    rFonts: CT_Fonts | None = ZeroOrOne("w:rFonts", successors=_tag_seq[2:])
    b: CT_OnOff | None = ZeroOrOne("w:b", successors=_tag_seq[3:])
    bCs = ZeroOrOne("w:bCs", successors=_tag_seq[4:])
    i = ZeroOrOne("w:i", successors=_tag_seq[5:])
    iCs = ZeroOrOne("w:iCs", successors=_tag_seq[6:])
    caps = ZeroOrOne("w:caps", successors=_tag_seq[7:])
    smallCaps = ZeroOrOne("w:smallCaps", successors=_tag_seq[8:])
    strike = ZeroOrOne("w:strike", successors=_tag_seq[9:])
    dstrike = ZeroOrOne("w:dstrike", successors=_tag_seq[10:])
    outline = ZeroOrOne("w:outline", successors=_tag_seq[11:])
    shadow = ZeroOrOne("w:shadow", successors=_tag_seq[12:])
    emboss = ZeroOrOne("w:emboss", successors=_tag_seq[13:])
    imprint = ZeroOrOne("w:imprint", successors=_tag_seq[14:])
    noProof = ZeroOrOne("w:noProof", successors=_tag_seq[15:])
    snapToGrid = ZeroOrOne("w:snapToGrid", successors=_tag_seq[16:])
    vanish = ZeroOrOne("w:vanish", successors=_tag_seq[17:])
    webHidden = ZeroOrOne("w:webHidden", successors=_tag_seq[18:])
    color: CT_Color | None = ZeroOrOne("w:color", successors=_tag_seq[19:])
    w: CT_TextScale | None = ZeroOrOne("w:w", successors=_tag_seq[21:])
    sz: CT_HpsMeasure | None = ZeroOrOne("w:sz", successors=_tag_seq[24:])
    szCs: CT_HpsMeasure | None = ZeroOrOne("w:szCs", successors=_tag_seq[25:])
    highlight: CT_Highlight | None = ZeroOrOne("w:highlight", successors=_tag_seq[26:])
    u: CT_Underline | None = ZeroOrOne("w:u", successors=_tag_seq[27:])
    shd: CT_Shd | None = ZeroOrOne("w:shd", successors=_tag_seq[30:])
    vertAlign: CT_VerticalAlignRun | None = ZeroOrOne("w:vertAlign", successors=_tag_seq[32:])
    rtl = ZeroOrOne("w:rtl", successors=_tag_seq[33:])
    cs = ZeroOrOne("w:cs", successors=_tag_seq[34:])
    specVanish = ZeroOrOne("w:specVanish", successors=_tag_seq[38:])
    oMath = ZeroOrOne("w:oMath", successors=_tag_seq[39:])
    del _tag_seq

    def _new_color(self):
        """Override metaclass method to set `w:color/@val` to RGB black on create."""
        return parse_xml('<w:color %s w:val="000000"/>' % nsdecls("w"))

    @property
    def highlight_val(self) -> WD_COLOR_INDEX | None:
        """Value of `./w:highlight/@val`.

        Specifies font's highlight color, or `None` if the text is not highlighted.
        """
        highlight = self.highlight
        if highlight is None:
            return None
        return highlight.val

    @highlight_val.setter
    def highlight_val(self, value: WD_COLOR_INDEX | None) -> None:
        if value is None:
            self._remove_highlight()
            return
        highlight = self.get_or_add_highlight()
        highlight.val = value

    @property
    def rFonts_ascii(self) -> str | None:
        """The value of `w:rFonts/@w:ascii` or |None| if not present.

        Represents the assigned typeface name. The rFonts element also specifies other
        special-case typeface names; this method handles the case where just the common
        name is required.
        """
        rFonts = self.rFonts
        if rFonts is None:
            return None
        return rFonts.ascii

    @rFonts_ascii.setter
    def rFonts_ascii(self, value: str | None) -> None:
        if value is None:
            self._remove_rFonts()
            return
        rFonts = self.get_or_add_rFonts()
        rFonts.ascii = value

    @property
    def rFonts_hAnsi(self) -> str | None:
        """The value of `w:rFonts/@w:hAnsi` or |None| if not present."""
        rFonts = self.rFonts
        if rFonts is None:
            return None
        return rFonts.hAnsi

    @rFonts_hAnsi.setter
    def rFonts_hAnsi(self, value: str | None):
        if value is None and self.rFonts is None:
            return
        rFonts = self.get_or_add_rFonts()
        rFonts.hAnsi = value

    @property
    def rFonts_eastAsia(self) -> str | None:
        """The value of `w:rFonts/@w:eastAsia` or |None| if not present.

        The typeface Word uses for East Asian characters in the run.
        """
        rFonts = self.rFonts
        if rFonts is None:
            return None
        return rFonts.eastAsia

    @rFonts_eastAsia.setter
    def rFonts_eastAsia(self, value: str | None):
        if value is None and self.rFonts is None:
            return
        self.get_or_add_rFonts().eastAsia = value

    @property
    def rFonts_cs(self) -> str | None:
        """The value of `w:rFonts/@w:cs` or |None| if not present.

        The typeface Word uses for complex-script characters in the run.
        """
        rFonts = self.rFonts
        if rFonts is None:
            return None
        return rFonts.cs

    @rFonts_cs.setter
    def rFonts_cs(self, value: str | None):
        if value is None and self.rFonts is None:
            return
        self.get_or_add_rFonts().cs = value

    @property
    def rFonts_hint(self) -> WD_FONT_HINT | None:
        """The value of `w:rFonts/@w:hint` or |None| if not present."""
        rFonts = self.rFonts
        if rFonts is None:
            return None
        return rFonts.hint

    @rFonts_hint.setter
    def rFonts_hint(self, value: WD_FONT_HINT | None):
        if value is None and self.rFonts is None:
            return
        self.get_or_add_rFonts().hint = value

    @property
    def rFonts_asciiTheme(self) -> str | None:
        """The value of `w:rFonts/@w:asciiTheme` or |None| if not present.

        Names a theme typeface slot, like "minorHAnsi", resolved against the theme part
        rather than naming a font directly.
        """
        rFonts = self.rFonts
        if rFonts is None:
            return None
        return rFonts.asciiTheme

    @rFonts_asciiTheme.setter
    def rFonts_asciiTheme(self, value: str | None):
        if value is None and self.rFonts is None:
            return
        rFonts = self.get_or_add_rFonts()
        rFonts.asciiTheme = value

    @property
    def rFonts_hAnsiTheme(self) -> str | None:
        """The value of `w:rFonts/@w:hAnsiTheme` or |None| if not present."""
        rFonts = self.rFonts
        if rFonts is None:
            return None
        return rFonts.hAnsiTheme

    @rFonts_hAnsiTheme.setter
    def rFonts_hAnsiTheme(self, value: str | None):
        if value is None and self.rFonts is None:
            return
        rFonts = self.get_or_add_rFonts()
        rFonts.hAnsiTheme = value

    @property
    def shd_fill(self) -> RGBColor | str | None:
        """Value of `./w:shd/@w:fill`, or |None| when no shading is applied."""
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
        shd.fill = value

    @property
    def w_val(self) -> int | None:
        """Value of `./w:w/@w:val`, the character scale percentage.

        |None| when no explicit scaling is applied and the value is inherited.
        """
        w = self.w
        if w is None:
            return None
        return w.val

    @w_val.setter
    def w_val(self, value: int | None) -> None:
        if value is None:
            self._remove_w()
            return
        self.get_or_add_w().val = value

    @property
    def style(self) -> str | None:
        """String in `./w:rStyle/@val`, or None if `w:rStyle` is not present."""
        rStyle = self.rStyle
        if rStyle is None:
            return None
        return rStyle.val

    @style.setter
    def style(self, style: str | None) -> None:
        """Set `./w:rStyle/@val` to `style`, adding the `w:rStyle` element if necessary.

        If `style` is |None|, remove `w:rStyle` element if present.
        """
        if style is None:
            self._remove_rStyle()
        elif self.rStyle is None:
            self._add_rStyle(val=style)
        else:
            self.rStyle.val = style

    @property
    def subscript(self) -> bool | None:
        """|True| if `./w:vertAlign/@w:val` is "subscript".

        |False| if `w:vertAlign/@w:val` contains any other value. |None| if
        `w:vertAlign` is not present.
        """
        vertAlign = self.vertAlign
        if vertAlign is None:
            return None
        return vertAlign.val == ST_VerticalAlignRun.SUBSCRIPT

    @subscript.setter
    def subscript(self, value: bool | None) -> None:
        if value is None:
            self._remove_vertAlign()
        elif bool(value) is True:
            self.get_or_add_vertAlign().val = ST_VerticalAlignRun.SUBSCRIPT
        # -- assert bool(value) is False --
        elif self.vertAlign is not None and self.vertAlign.val == ST_VerticalAlignRun.SUBSCRIPT:
            self._remove_vertAlign()

    @property
    def superscript(self) -> bool | None:
        """|True| if `w:vertAlign/@w:val` is 'superscript'.

        |False| if `w:vertAlign/@w:val` contains any other value. |None| if
        `w:vertAlign` is not present.
        """
        vertAlign = self.vertAlign
        if vertAlign is None:
            return None
        return vertAlign.val == ST_VerticalAlignRun.SUPERSCRIPT

    @superscript.setter
    def superscript(self, value: bool | None):
        if value is None:
            self._remove_vertAlign()
        elif bool(value) is True:
            self.get_or_add_vertAlign().val = ST_VerticalAlignRun.SUPERSCRIPT
        # -- assert bool(value) is False --
        elif self.vertAlign is not None and self.vertAlign.val == ST_VerticalAlignRun.SUPERSCRIPT:
            self._remove_vertAlign()

    @property
    def sz_val(self) -> Length | None:
        """The value of `w:sz/@w:val` or |None| if not present."""
        sz = self.sz
        if sz is None:
            return None
        return sz.val

    @sz_val.setter
    def sz_val(self, value: Length | None):
        if value is None:
            self._remove_sz()
            return
        sz = self.get_or_add_sz()
        sz.val = value

    @property
    def szCs_val(self) -> Length | None:
        """The value of `w:szCs/@w:val` or |None| if not present.

        This is the font size applied to complex-script text, which Word tracks
        separately from `w:sz`.
        """
        szCs = self.szCs
        if szCs is None:
            return None
        return szCs.val

    @szCs_val.setter
    def szCs_val(self, value: Length | None):
        if value is None:
            self._remove_szCs()
            return
        szCs = self.get_or_add_szCs()
        szCs.val = value

    @property
    def u_val(self) -> WD_UNDERLINE | None:
        """Value of `w:u/@val`, or None if not present.

        Values `WD_UNDERLINE.SINGLE` and `WD_UNDERLINE.NONE` are mapped to `True` and
        `False` respectively.
        """
        u = self.u
        if u is None:
            return None
        return u.val

    @u_val.setter
    def u_val(self, value: WD_UNDERLINE | None):
        self._remove_u()
        if value is not None:
            self._add_u().val = value

    def _get_bool_val(self, name: str) -> bool | None:
        """Value of boolean child with `name`, e.g. "w:b", "w:i", and "w:smallCaps"."""
        element = getattr(self, name)
        if element is None:
            return None
        return element.val

    def _set_bool_val(self, name: str, value: bool | None):
        if value is None:
            getattr(self, "_remove_%s" % name)()
            return
        element = getattr(self, "get_or_add_%s" % name)()
        element.val = value


class CT_Underline(BaseOxmlElement):
    """`<w:u>` element, specifying the underlining style for a run."""

    val: WD_UNDERLINE | None = OptionalAttribute("w:val", WD_UNDERLINE)


class CT_VerticalAlignRun(BaseOxmlElement):
    """`<w:vertAlign>` element, specifying subscript or superscript."""

    val: str = RequiredAttribute("w:val", ST_VerticalAlignRun)
