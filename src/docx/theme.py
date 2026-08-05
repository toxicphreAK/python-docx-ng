"""The |Theme| object, the document's theme fonts and colours."""

from __future__ import annotations

from typing import TYPE_CHECKING

from docx.shared import ElementProxy

if TYPE_CHECKING:
    from docx.oxml.theme import CT_OfficeStyleSheet
    from docx.shared import RGBColor

#: The `w:rFonts/@w:*Theme` tokens, split into the font collection they name and the
#: script slot within it. `minorHAnsi` and `minorAscii` both resolve to the Latin
#: typeface: Word keeps the ASCII and high-ANSI slots separate for the *document*'s
#: fonts, but a theme's font collection has one Latin entry serving both.
_THEME_TOKENS = {
    "majorAscii": ("major", "latin"),
    "majorHAnsi": ("major", "latin"),
    "majorEastAsia": ("major", "ea"),
    "majorBidi": ("major", "cs"),
    "minorAscii": ("minor", "latin"),
    "minorHAnsi": ("minor", "latin"),
    "minorEastAsia": ("minor", "ea"),
    "minorBidi": ("minor", "cs"),
}


class _ThemeFont:
    """One font collection of a theme — its major or minor fonts."""

    def __init__(self, fontCollection: object):
        self._fontCollection = fontCollection

    @property
    def latin(self) -> str | None:
        """The Latin typeface of this collection, e.g. ``"Calibri"``.

        This is what a `minorHAnsi` or `majorHAnsi` theme token resolves to, and the one
        that matters for a Western document.
        """
        return self._fontCollection.typeface_for("latin")  # pyright: ignore[reportAttributeAccessIssue]

    @property
    def east_asian(self) -> str | None:
        """The East Asian typeface of this collection, or |None| when it sets none.

        The default Office theme leaves this empty and relies on the `a:font` script
        entries instead, so |None| here is ordinary rather than exceptional.
        """
        return self._fontCollection.typeface_for("ea")  # pyright: ignore[reportAttributeAccessIssue]

    @property
    def complex_script(self) -> str | None:
        """The complex-script typeface of this collection, or |None| when it sets none."""
        return self._fontCollection.typeface_for("cs")  # pyright: ignore[reportAttributeAccessIssue]

    def __repr__(self) -> str:
        return "<docx.theme._ThemeFont latin=%r>" % self.latin


class Theme(ElementProxy):
    """The document's theme: its major and minor fonts and its twelve theme colours.

    Reached through :attr:`.Document.theme`, which is |None| for a document carrying no
    theme part.

    The point of exposing it is :attr:`.Font.theme_typeface`: a run whose font is set
    only by a theme token reports ``None`` for :attr:`.Font.name`, and this is where the
    concrete typeface behind that token lives.
    """

    def __init__(self, theme: CT_OfficeStyleSheet, part: object = None):
        super().__init__(theme)  # pyright: ignore[reportArgumentType]
        self._element = theme

    @property
    def name(self) -> str | None:
        """The theme's name, e.g. ``"Office Theme"``, or |None| when it has none."""
        return self._element.name

    @property
    def major_font(self) -> _ThemeFont:
        """The theme's major fonts, which Word applies to headings."""
        return _ThemeFont(self._element.themeElements.fontScheme.majorFont)

    @property
    def minor_font(self) -> _ThemeFont:
        """The theme's minor fonts, which Word applies to body text."""
        return _ThemeFont(self._element.themeElements.fontScheme.minorFont)

    def typeface(self, theme_token: str) -> str | None:
        """The concrete typeface `theme_token` names, or |None| when there is none.

        `theme_token` is a `w:rFonts/@w:asciiTheme`-style value such as ``"minorHAnsi"``.
        An unrecognised token, and a token whose slot the theme leaves empty, both give
        |None|.
        """
        try:
            collection, script = _THEME_TOKENS[theme_token]
        except KeyError:
            return None
        font = self.major_font if collection == "major" else self.minor_font
        return {"latin": font.latin, "ea": font.east_asian, "cs": font.complex_script}[script]

    def color(self, name: str) -> RGBColor | str | None:
        """The RGB value of theme colour `name`, or |None| when the theme has none.

        `name` is one of ``dk1``, ``lt1``, ``dk2``, ``lt2``, ``accent1`` through
        ``accent6``, ``hlink`` and ``folHlink`` — the slot names as they appear in the
        XML. A |MSO_THEME_COLOR| member's own spelling differs; this takes the XML one
        because that is what the theme part is keyed on.

        A system colour such as ``dk1`` reports the RGB value the producing application
        last resolved it to, which is the only concrete value available outside that
        operating system.
        """
        clrScheme = self._element.themeElements.clrScheme
        if name not in clrScheme.slots:
            raise ValueError(
                "no theme color %r; must be one of %s" % (name, ", ".join(clrScheme.slots))
            )
        color = clrScheme.color(name)
        return None if color is None else color.rgb

    @property
    def colors(self) -> dict[str, RGBColor | str | None]:
        """The twelve theme colours, keyed by slot name, in schema order."""
        return {name: self.color(name) for name in self._element.themeElements.clrScheme.slots}
