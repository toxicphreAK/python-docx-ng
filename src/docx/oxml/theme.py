"""Custom element classes for the theme part, `word/theme/theme1.xml`.

Only the two subtrees that a word-processing document actually resolves against are
modelled: `a:fontScheme`, which is where a theme typeface such as `minorHAnsi` turns
into a real font name, and `a:clrScheme`, which is where a theme colour turns into an
RGB value. `a:fmtScheme` — the fill, line and effect matrices — is a drawing-formatting
model of its own and is left as opaque XML.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from docx.oxml.simpletypes import ST_HexColor, ST_String, XsdString
from docx.oxml.xmlchemy import (
    BaseOxmlElement,
    OneAndOnlyOne,
    OptionalAttribute,
    RequiredAttribute,
    ZeroOrOne,
)

if TYPE_CHECKING:
    from docx.shared import RGBColor


class CT_TextFont(BaseOxmlElement):
    """`a:latin`, `a:ea` and `a:cs`, each naming one typeface of a font collection."""

    typeface: str = RequiredAttribute(  # pyright: ignore[reportAssignmentType]
        "typeface", XsdString
    )


class CT_FontCollection(BaseOxmlElement):
    """`a:majorFont` or `a:minorFont`, the typefaces of one half of the font scheme.

    `a:latin` is the one a `w:rFonts/@w:asciiTheme` of `majorHAnsi` or `minorHAnsi`
    resolves to; `a:ea` and `a:cs` serve the East Asian and complex-script slots.
    """

    latin: CT_TextFont = OneAndOnlyOne("a:latin")  # pyright: ignore[reportAssignmentType]
    ea: CT_TextFont = OneAndOnlyOne("a:ea")  # pyright: ignore[reportAssignmentType]
    cs: CT_TextFont = OneAndOnlyOne("a:cs")  # pyright: ignore[reportAssignmentType]

    def typeface_for(self, script: str) -> str | None:
        """The typeface for `script`, one of `"latin"`, `"ea"` or `"cs"`.

        |None| when the slot carries the empty typeface Word writes to mean "no
        override", which is what `a:ea` and `a:cs` hold in the default Office theme.
        """
        textFont = getattr(self, script)
        return textFont.typeface or None


class CT_FontScheme(BaseOxmlElement):
    """`a:fontScheme`, the major and minor font collections of a theme."""

    majorFont: CT_FontCollection = OneAndOnlyOne(  # pyright: ignore[reportAssignmentType]
        "a:majorFont"
    )
    minorFont: CT_FontCollection = OneAndOnlyOne(  # pyright: ignore[reportAssignmentType]
        "a:minorFont"
    )

    name: str | None = OptionalAttribute("name", XsdString)  # pyright: ignore


class CT_SRgbColor(BaseOxmlElement):
    """`a:srgbClr`, a colour given as an explicit RGB value."""

    val: RGBColor | str = RequiredAttribute(  # pyright: ignore[reportAssignmentType]
        "val", ST_HexColor
    )


class CT_SystemColor(BaseOxmlElement):
    """`a:sysClr`, a colour taken from the operating system's palette.

    `@lastClr` is the RGB value the producing application last resolved it to, which is
    the only concrete value available to a consumer that is not the operating system in
    question.
    """

    val: str = RequiredAttribute("val", ST_String)  # pyright: ignore[reportAssignmentType]
    lastClr: RGBColor | str | None = OptionalAttribute(  # pyright: ignore
        "lastClr", ST_HexColor
    )


class CT_ThemeColor(BaseOxmlElement):
    """One slot of `a:clrScheme`, e.g. `a:accent1`.

    The colour itself is one of several child element types; only the two Word writes
    for a theme are modelled.
    """

    get_or_add_srgbClr: Callable[[], CT_SRgbColor]

    srgbClr: CT_SRgbColor | None = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "a:srgbClr", successors=()
    )
    sysClr: CT_SystemColor | None = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "a:sysClr", successors=()
    )

    @property
    def rgb(self) -> RGBColor | str | None:
        """The RGB value of this colour slot, or |None| when there is none to give.

        A system colour reports the `@lastClr` the producing application resolved it to;
        that is the closest thing to a concrete value a consumer outside that operating
        system can have.
        """
        srgbClr = self.srgbClr
        if srgbClr is not None:
            return srgbClr.val
        sysClr = self.sysClr
        return None if sysClr is None else sysClr.lastClr


class CT_ColorScheme(BaseOxmlElement):
    """`a:clrScheme`, the twelve theme colours."""

    _tag_seq = (
        "a:dk1",
        "a:lt1",
        "a:dk2",
        "a:lt2",
        "a:accent1",
        "a:accent2",
        "a:accent3",
        "a:accent4",
        "a:accent5",
        "a:accent6",
        "a:hlink",
        "a:folHlink",
    )
    slots = tuple(tag[2:] for tag in _tag_seq)
    del _tag_seq

    name: str | None = OptionalAttribute("name", XsdString)  # pyright: ignore

    def color(self, slot: str) -> CT_ThemeColor | None:
        """The `a:{slot}` child, or |None| when the scheme does not define it."""
        from docx.oxml.ns import qn

        return self.find(qn("a:%s" % slot))  # pyright: ignore[reportReturnType]


class CT_BaseStyles(BaseOxmlElement):
    """`a:themeElements`, the part of a theme that documents resolve against."""

    clrScheme: CT_ColorScheme = OneAndOnlyOne(  # pyright: ignore[reportAssignmentType]
        "a:clrScheme"
    )
    fontScheme: CT_FontScheme = OneAndOnlyOne(  # pyright: ignore[reportAssignmentType]
        "a:fontScheme"
    )


class CT_OfficeStyleSheet(BaseOxmlElement):
    """`a:theme`, the root element of a theme part."""

    themeElements: CT_BaseStyles = OneAndOnlyOne(  # pyright: ignore[reportAssignmentType]
        "a:themeElements"
    )

    name: str | None = OptionalAttribute("name", XsdString)  # pyright: ignore
