"""|ThemePart| and closely related objects."""

from __future__ import annotations

from typing import TYPE_CHECKING

from docx.opc.part import XmlPart
from docx.shared import lazyproperty

if TYPE_CHECKING:
    from docx.theme import Theme


class ThemePart(XmlPart):
    """Proxy for `word/theme/theme1.xml`, the theme a document resolves against.

    A document that sets no explicit `w:rFonts/@w:ascii` anywhere — which is most
    documents produced from a Word template — has its actual typefaces here, reached
    through the `minorHAnsi`-style tokens in `Font.theme`.
    """

    @lazyproperty
    def theme(self) -> Theme:
        """The |Theme| object for this part."""
        from docx.theme import Theme

        return Theme(self.element, self)
