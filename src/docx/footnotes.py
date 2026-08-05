"""Collections providing access to the footnotes and endnotes of the document.

Footnotes and endnotes are the same feature placed differently — a footnote at the foot
of its page, an endnote at the end of the document or section. They share a complex type
in the schema and share their implementation here; see `docx.oxml.footnotes`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

from docx.blkcntnr import BlockItemContainer

if TYPE_CHECKING:
    from docx.oxml.footnotes import (
        CT_FtnEdn,
        _CT_FtnEdnCollection,  # pyright: ignore[reportPrivateUsage]
    )
    from docx.parts.story import StoryPart
    from docx.styles.style import ParagraphStyle
    from docx.text.paragraph import Paragraph


class _Notes:
    """Common behavior of the |Footnotes| and |Endnotes| collections.

    Only the notes an author wrote are in the collection. Word keeps two more in the
    same part, at ids -1 and 0, which hold the rule it draws above the note area and its
    continuation on the next page; those are structural and never appear here.
    """

    #: The proxy class wrapping one note element.
    _note_cls: type[_Note]

    def __init__(self, notes_elm: _CT_FtnEdnCollection, notes_part: StoryPart):
        self._notes_elm = notes_elm
        self._notes_part = notes_part

    def __iter__(self) -> Iterator[_Note]:
        """Iterator over the notes in this collection, in document order."""
        return (
            self._note_cls(note_elm, self._notes_part)
            for note_elm in self._notes_elm.iter_authored_notes()
        )

    def __len__(self) -> int:
        """The number of notes in this collection."""
        return len(self._notes_elm.iter_authored_notes())

    def _add_note(self, text: str) -> _Note:
        """Add a note holding `text` and return it.

        See :meth:`Footnotes.add_footnote` for what `text` means.
        """
        note = self._note_cls(self._notes_elm.add_note(), self._notes_part)

        if text == "":
            return note

        para_text_iter = iter(text.split("\n"))

        # -- the first paragraph already holds the reference mark, so its text is
        # -- appended to it rather than placed in a paragraph of its own --
        note.paragraphs[0].add_run(next(para_text_iter))

        for s in para_text_iter:
            note.add_paragraph(text=s)

        return note

    def _get(self, note_id: int) -> _Note | None:
        """The note identified by `note_id`, or |None| if there is none."""
        note_elm = self._notes_elm.get_note_by_id(note_id)
        if note_elm is None or note_elm.is_structural:
            return None
        return self._note_cls(note_elm, self._notes_part)


class _Note(BlockItemContainer):
    """Common behavior of the |Footnote| and |Endnote| proxies.

    A note is a block-item container, like a table cell, so it can hold both paragraphs
    and tables and its paragraphs can hold rich text, hyperlinks and images. The common
    case is a single paragraph of plain text.
    """

    #: The paragraph style Word applies to note content.
    _para_style: str

    def __init__(self, note_elm: CT_FtnEdn, notes_part: StoryPart):
        super().__init__(note_elm, notes_part)
        self._note_elm = note_elm

    def add_paragraph(self, text: str = "", style: str | ParagraphStyle | None = None) -> Paragraph:
        """Return a paragraph newly added to the end of this note.

        The paragraph holds `text` in a single run if present and is given paragraph
        style `style`. When `style` is omitted or |None|, the style Word uses for this
        kind of note's content is applied — "FootnoteText" or "EndnoteText".
        """
        paragraph = super().add_paragraph(text, style)

        # -- assign the style directly to the element, since `paragraph.style` raises
        # -- when the style is not defined in the styles part and Word supplies this one
        # -- as a latent style
        if style is None:
            paragraph._p.style = self._para_style  # pyright: ignore[reportPrivateUsage]

        return paragraph

    @property
    def text(self) -> str:
        """The text content of this note as a string.

        Only content in paragraphs is included, and all emphasis and styling is
        stripped. Paragraph boundaries are indicated with a newline (`"\\\\n"`).
        """
        return "\n".join(p.text for p in self.paragraphs)


class Footnote(_Note):
    """Proxy for a single footnote in the document."""

    _para_style = "FootnoteText"

    @property
    def footnote_id(self) -> int:
        """The identifier a `w:footnoteReference` uses to cite this footnote."""
        return self._note_elm.id


class Endnote(_Note):
    """Proxy for a single endnote in the document."""

    _para_style = "EndnoteText"

    @property
    def endnote_id(self) -> int:
        """The identifier a `w:endnoteReference` uses to cite this endnote."""
        return self._note_elm.id


class Footnotes(_Notes):
    """Collection containing the footnotes of this document.

    Only the footnotes an author wrote are in the collection. Word keeps two more in
    the same part, at ids -1 and 0, which hold the rule it draws above the footnote
    area and its continuation on the next page; those are structural and never appear
    here.
    """

    _note_cls = Footnote

    def __iter__(self) -> Iterator[Footnote]:
        return super().__iter__()  # pyright: ignore[reportReturnType]

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
        return self._add_note(text)  # pyright: ignore[reportReturnType]

    def get(self, footnote_id: int) -> Footnote | None:
        """The footnote identified by `footnote_id`, or |None| if there is none.

        |None| is also returned for the ids of Word's structural separator footnotes,
        which are not footnotes of this document in any sense an author would mean.
        """
        return self._get(footnote_id)  # pyright: ignore[reportReturnType]


class Endnotes(_Notes):
    """Collection containing the endnotes of this document.

    The endnote counterpart of |Footnotes|, and identical to it in behavior. Where an
    endnote appears — end of section or end of document — is a document setting, in
    `w:sectPr/w:endnotePr` and `w:settings/w:endnotePr`, and is not exposed here.
    """

    _note_cls = Endnote

    def __iter__(self) -> Iterator[Endnote]:
        return super().__iter__()  # pyright: ignore[reportReturnType]

    def add_endnote(self, text: str = "") -> Endnote:
        """Add a new endnote to the document and return it.

        As for `Footnotes.add_footnote()`: the endnote is given an id unique within the
        collection, and adding it does not place a reference to it in the body text —
        use `Run.add_endnote_reference()` for that. An endnote no run references does
        not appear in the rendered document.
        """
        return self._add_note(text)  # pyright: ignore[reportReturnType]

    def get(self, endnote_id: int) -> Endnote | None:
        """The endnote identified by `endnote_id`, or |None| if there is none."""
        return self._get(endnote_id)  # pyright: ignore[reportReturnType]
