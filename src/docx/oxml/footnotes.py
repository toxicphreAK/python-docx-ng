"""Custom element classes related to document footnotes and endnotes.

Footnotes and endnotes are the same feature in two places. The schema gives both
`w:footnote` and `w:endnote` the type `CT_FtnEdn`, both parts wrap a sequence of those,
and `w:footnoteReference` and `w:endnoteReference` are both `CT_FtnEdnRef`. Only the tag
names and the reference-mark element differ, so this module models the pair once and
subclasses for the two spellings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, List, cast

from docx.oxml.ns import nsdecls, qn
from docx.oxml.parser import parse_xml
from docx.oxml.sdt import iter_block_content
from docx.oxml.simpletypes import ST_DecimalNumber, ST_FtnEdn, ST_OnOff
from docx.oxml.xmlchemy import BaseOxmlElement, OptionalAttribute, RequiredAttribute, ZeroOrMore

if TYPE_CHECKING:
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P

# -- a footnote with one of these `w:type` values is structural: Word uses it to draw
# -- the rule separating the footnotes from the body text, or to notify the reader that
# -- a footnote continues on the next page. It is not a footnote the author wrote. --
STRUCTURAL_FOOTNOTE_TYPES = ("separator", "continuationSeparator", "continuationNotice")


class _CT_FtnEdnCollection(BaseOxmlElement):
    """Common behavior of the `w:footnotes` and `w:endnotes` root elements.

    They differ only in the tag of their children, the reference-mark element that goes
    in a new note, and the styles Word applies to one; `_tag`, `_ref_tag`,
    `_para_style` and `_char_style` name those.
    """

    #: The child tag, e.g. `"w:footnote"`.
    _tag: str
    #: The reference-mark element a new note starts with, e.g. `"w:footnoteRef"`.
    _ref_tag: str
    #: The paragraph style Word applies to note content.
    _para_style: str
    #: The character style Word applies to the reference mark.
    _char_style: str

    @property
    def note_lst(self) -> List[CT_FtnEdn]:
        """The `w:footnote` or `w:endnote` children, in document order."""
        return self.findall(qn(self._tag))  # pyright: ignore[reportReturnType]

    def add_note(self) -> CT_FtnEdn:
        """Return a newly added note child of this element.

        The returned element is the minimum valid value: a `w:id` unique among the
        existing notes and a single paragraph holding the reference mark that Word
        renders as the note number. Content is added by adding runs to that paragraph
        and by adding further paragraphs.
        """
        next_id = self._next_available_note_id()
        note = cast(
            "CT_FtnEdn",
            parse_xml(
                f'<{self._tag} {nsdecls("w")} w:id="{next_id}">'
                f"  <w:p>"
                f"    <w:pPr>"
                f'      <w:pStyle w:val="{self._para_style}"/>'
                f"    </w:pPr>"
                f"    <w:r>"
                f"      <w:rPr>"
                f'        <w:rStyle w:val="{self._char_style}"/>'
                f"      </w:rPr>"
                f"      <{self._ref_tag}/>"
                f"    </w:r>"
                f"  </w:p>"
                f"</{self._tag}>"
            ),
        )
        self.append(note)
        return note

    def get_note_by_id(self, note_id: int) -> CT_FtnEdn | None:
        """The note element identified by `note_id`, or |None| if not found."""
        note_elms = self.xpath(f"(./{self._tag}[@w:id='{note_id}'])[1]")
        return note_elms[0] if note_elms else None

    def iter_authored_notes(self) -> List[CT_FtnEdn]:
        """The note elements an author wrote, in document order.

        The structural separator notes Word keeps at ids -1 and 0 are left out; see
        `STRUCTURAL_FOOTNOTE_TYPES`.
        """
        return [f for f in self.note_lst if not f.is_structural]

    def _next_available_note_id(self) -> int:
        """The next available note id.

        The schema allows any integer, and Word numbers author notes from 1 upward,
        having reserved -1 and 0 for the separators. As for comment ids, the default is
        `max() + 1`, falling back to the first unused non-negative integer if that would
        overflow a 32-bit signed integer.
        """
        used_ids = [int(x) for x in self.xpath(f"./{self._tag}/@w:id")]

        next_id = max(used_ids, default=0) + 1

        if next_id <= 2**31 - 1:
            return next_id

        # -- fall-back to enumerating all used ids to find the first unused one --
        for expected, actual in enumerate(sorted(i for i in used_ids if i >= 1), start=1):
            if expected != actual:
                return expected

        return len(used_ids)


class CT_Footnotes(_CT_FtnEdnCollection):
    """`w:footnotes` element, the root element for the footnotes part.

    Contains a `w:footnote` element for each footnote in the document, plus the
    structural separator footnotes Word keeps at ids -1 and 0.
    """

    # -- type-declarations to fill in the gaps for metaclass-added methods --
    footnote_lst: List[CT_FtnEdn]

    footnote = ZeroOrMore("w:footnote")

    _tag = "w:footnote"
    _ref_tag = "w:footnoteRef"
    _para_style = "FootnoteText"
    _char_style = "FootnoteReference"


class CT_Endnotes(_CT_FtnEdnCollection):
    """`w:endnotes` element, the root element for the endnotes part.

    The endnote half of `CT_Footnotes`; the two are the same complex type in the schema.
    """

    # -- type-declarations to fill in the gaps for metaclass-added methods --
    endnote_lst: List[CT_FtnEdn]

    endnote = ZeroOrMore("w:endnote")

    _tag = "w:endnote"
    _ref_tag = "w:endnoteRef"
    _para_style = "EndnoteText"
    _char_style = "EndnoteReference"


class CT_FtnEdn(BaseOxmlElement):
    """`w:footnote` or `w:endnote` element, a single note.

    A footnote is a "story" and can contain paragraphs and tables much like a table
    cell, so its content can be rich: multiple paragraphs, hyperlinks, images and
    tables.
    """

    # -- attributes on `w:footnote` --
    id: int = RequiredAttribute("w:id", ST_DecimalNumber)  # pyright: ignore[reportAssignmentType]
    type: str | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:type", ST_FtnEdn
    )

    # -- children --

    p = ZeroOrMore("w:p", successors=())
    tbl = ZeroOrMore("w:tbl", successors=())

    # -- type-declarations for methods added by metaclass --

    add_p: Callable[[], CT_P]
    p_lst: List[CT_P]
    tbl_lst: List[CT_Tbl]
    _insert_tbl: Callable[[CT_Tbl], CT_Tbl]

    @property
    def inner_content_elements(self) -> List[CT_P | CT_Tbl]:
        """All `w:p` and `w:tbl` elements in this footnote, in document order.

        Content inside a `w:sdt` (content control) wrapper is included.
        """
        return list(iter_block_content(self))

    @property
    def is_structural(self) -> bool:
        """|True| when this is one of Word's separator footnotes rather than an author's.

        These are the footnotes Word keeps at ids -1 and 0 to draw the rule above the
        footnote area and its continuation.
        """
        return self.type in STRUCTURAL_FOOTNOTE_TYPES


class CT_FtnEdnRef(BaseOxmlElement):
    """`w:footnoteReference` or `w:endnoteReference`, the mark that cites a note."""

    id: int = RequiredAttribute("w:id", ST_DecimalNumber)  # pyright: ignore[reportAssignmentType]
    customMarkFollows: bool | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:customMarkFollows", ST_OnOff
    )
