"""Collection providing access to the footnotes of the document."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

from docx.blkcntnr import BlockItemContainer

if TYPE_CHECKING:
    from docx.oxml.footnotes import CT_Footnotes, CT_FtnEdn
    from docx.parts.footnotes import FootnotesPart
    from docx.styles.style import ParagraphStyle
    from docx.text.paragraph import Paragraph


class Footnotes:
    """Collection containing the footnotes of this document.

    Only the footnotes an author wrote are in the collection. Word keeps two more in
    the same part, at ids -1 and 0, which hold the rule it draws above the footnote
    area and its continuation on the next page; those are structural and never appear
    here.
    """

    def __init__(self, footnotes_elm: CT_Footnotes, footnotes_part: FootnotesPart):
        self._footnotes_elm = footnotes_elm
        self._footnotes_part = footnotes_part

    def __iter__(self) -> Iterator[Footnote]:
        """Iterator over the footnotes in this collection, in document order."""
        return (
            Footnote(footnote_elm, self._footnotes_part)
            for footnote_elm in self._footnotes_elm.iter_authored_footnotes()
        )

    def __len__(self) -> int:
        """The number of footnotes in this collection."""
        return len(self._footnotes_elm.iter_authored_footnotes())

    def add_footnote(self, text: str = "") -> Footnote:
        """Add a new footnote to the document and return it.

        The footnote is added to the end of the footnotes collection and is assigned an
        id unique within it. Adding it does not place a reference to it in the body
        text; use `Run.add_footnote_reference()` for that. A footnote no run references
        does not appear in the rendered document.

        If `text` is provided it is added to the footnote, after the reference mark that
        Word renders as the footnote number. Multiple paragraphs can be added by
        separating their text with newlines (`"\\\\n"`); between newlines, text is
        interpreted as it is in `Document.add_paragraph(text=...)`.

        The default is a footnote holding only the reference mark, to which runs can be
        added with `footnote.paragraphs[0].add_run()` and further paragraphs with
        `.add_paragraph()`.
        """
        footnote = Footnote(self._footnotes_elm.add_footnote(), self._footnotes_part)

        if text == "":
            return footnote

        para_text_iter = iter(text.split("\n"))

        # -- the first paragraph already holds the reference mark, so its text is
        # -- appended to it rather than placed in a paragraph of its own --
        footnote.paragraphs[0].add_run(next(para_text_iter))

        for s in para_text_iter:
            footnote.add_paragraph(text=s)

        return footnote

    def get(self, footnote_id: int) -> Footnote | None:
        """The footnote identified by `footnote_id`, or |None| if there is none.

        |None| is also returned for the ids of Word's structural separator footnotes,
        which are not footnotes of this document in any sense an author would mean.
        """
        footnote_elm = self._footnotes_elm.get_footnote_by_id(footnote_id)
        if footnote_elm is None or footnote_elm.is_structural:
            return None
        return Footnote(footnote_elm, self._footnotes_part)


class Footnote(BlockItemContainer):
    """Proxy for a single footnote in the document.

    A footnote is a block-item container, like a table cell, so it can hold both
    paragraphs and tables and its paragraphs can hold rich text, hyperlinks and images.
    The common case is a single paragraph of plain text.
    """

    def __init__(self, footnote_elm: CT_FtnEdn, footnotes_part: FootnotesPart):
        super().__init__(footnote_elm, footnotes_part)
        self._footnote_elm = footnote_elm

    def add_paragraph(self, text: str = "", style: str | ParagraphStyle | None = None) -> Paragraph:
        """Return a paragraph newly added to the end of this footnote.

        The paragraph holds `text` in a single run if present and is given paragraph
        style `style`. When `style` is omitted or |None|, the "FootnoteText" paragraph
        style is applied, which is what Word uses for footnote content.
        """
        paragraph = super().add_paragraph(text, style)

        # -- assign the style directly to the element, since `paragraph.style` raises
        # -- when the style is not defined in the styles part and Word supplies this one
        # -- as a latent style
        if style is None:
            paragraph._p.style = "FootnoteText"  # pyright: ignore[reportPrivateUsage]

        return paragraph

    @property
    def footnote_id(self) -> int:
        """The identifier a `w:footnoteReference` uses to cite this footnote."""
        return self._footnote_elm.id

    @property
    def text(self) -> str:
        """The text content of this footnote as a string.

        Only content in paragraphs is included, and all emphasis and styling is
        stripped. Paragraph boundaries are indicated with a newline (`"\\\\n"`).
        """
        return "\n".join(p.text for p in self.paragraphs)
