"""The |AltChunk| object, an embedded document Word imports when it opens the file."""

from __future__ import annotations

from typing import TYPE_CHECKING

from docx.shared import StoryChild

if TYPE_CHECKING:
    import docx.types as t
    from docx.oxml.document import CT_AltChunk
    from docx.parts.altchunk import AltChunkPart


class AltChunk(StoryChild):
    """Proxy for a `w:altChunk` element, an "alternative format import".

    An alt-chunk holds a document in a format other than WordprocessingML — HTML, RTF,
    plain text, MHTML, or another .docx. Word converts it and splices the result into
    the document at this position when it opens the file.

    The conversion is Word's, and it happens on open. This library stores and returns
    the embedded bytes unchanged and does not read into them, so the paragraphs and
    tables the alt-chunk will eventually contribute do not appear in
    `Document.paragraphs`, `Document.tables` or `Document.iter_inner_content()`.
    """

    def __init__(self, altChunk: CT_AltChunk, parent: t.ProvidesStoryPart):
        super().__init__(parent)
        self._element = self._altChunk = altChunk

    @property
    def blob(self) -> bytes:
        """The bytes of the embedded document, exactly as they were provided."""
        return self._part.blob

    @property
    def content_type(self) -> str:
        """The content type of the embedded document, e.g. `"text/html"`."""
        return self._part.content_type

    @property
    def _part(self) -> AltChunkPart:
        """The |AltChunkPart| holding the embedded document."""
        rId = self._altChunk.rId
        if rId is None:
            raise ValueError("this `w:altChunk` element has no `r:id`, so names no content")
        return self.part.related_parts[rId]
