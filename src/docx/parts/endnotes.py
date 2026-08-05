"""Contains the endnotes of the document."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, cast

from typing_extensions import Self

from docx.footnotes import Endnotes
from docx.opc.constants import CONTENT_TYPE as CT
from docx.opc.packuri import PackURI
from docx.oxml.parser import parse_xml
from docx.parts.story import StoryPart

if TYPE_CHECKING:
    from docx.oxml.footnotes import CT_Endnotes
    from docx.package import Package


class EndnotesPart(StoryPart):
    """Container part for the endnotes of the document.

    The endnote half of |FootnotesPart|; `word/endnotes.xml` holds the same shape of
    content as `word/footnotes.xml`.
    """

    def __init__(
        self, partname: PackURI, content_type: str, element: CT_Endnotes, package: Package
    ):
        super().__init__(partname, content_type, element, package)
        self._endnotes = element

    @classmethod
    def default(cls, package: Package) -> Self:
        """A newly created endnotes part.

        It holds the two structural endnotes Word requires — the separator and the
        continuation separator, at ids -1 and 0 — and no author endnotes.
        """
        partname = PackURI("/word/endnotes.xml")
        content_type = CT.WML_ENDNOTES
        element = cast("CT_Endnotes", parse_xml(cls._default_endnotes_xml()))
        return cls(partname, content_type, element, package)

    @property
    def endnotes(self) -> Endnotes:
        """An |Endnotes| proxy for the `w:endnotes` root element of this part."""
        return Endnotes(self._endnotes, self)

    @classmethod
    def _default_endnotes_xml(cls) -> bytes:
        """A byte-string containing XML for a default endnotes part."""
        path = os.path.join(os.path.split(__file__)[0], "..", "templates", "default-endnotes.xml")
        with open(path, "rb") as f:
            xml_bytes = f.read()
        return xml_bytes
