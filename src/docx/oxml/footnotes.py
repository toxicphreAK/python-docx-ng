"""Custom element classes related to document footnotes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, List, cast

from docx.oxml.ns import nsdecls
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


class CT_Footnotes(BaseOxmlElement):
    """`w:footnotes` element, the root element for the footnotes part.

    Contains a `w:footnote` element for each footnote in the document, plus the
    structural separator footnotes Word keeps at ids -1 and 0.
    """

    # -- type-declarations to fill in the gaps for metaclass-added methods --
    footnote_lst: List[CT_FtnEdn]

    footnote = ZeroOrMore("w:footnote")

    def add_footnote(self) -> CT_FtnEdn:
        """Return newly added `w:footnote` child of this `w:footnotes`.

        The returned element is the minimum valid value: a `w:id` unique among the
        existing footnotes and a single paragraph holding the reference mark that Word
        renders as the footnote number. Content is added by adding runs to that
        paragraph and by adding further paragraphs.
        """
        next_id = self._next_available_footnote_id()
        footnote = cast(
            "CT_FtnEdn",
            parse_xml(
                f'<w:footnote {nsdecls("w")} w:id="{next_id}">'
                f"  <w:p>"
                f"    <w:pPr>"
                f'      <w:pStyle w:val="FootnoteText"/>'
                f"    </w:pPr>"
                f"    <w:r>"
                f"      <w:rPr>"
                f'        <w:rStyle w:val="FootnoteReference"/>'
                f"      </w:rPr>"
                f"      <w:footnoteRef/>"
                f"    </w:r>"
                f"  </w:p>"
                f"</w:footnote>"
            ),
        )
        self.append(footnote)
        return footnote

    def get_footnote_by_id(self, footnote_id: int) -> CT_FtnEdn | None:
        """The `w:footnote` element identified by `footnote_id`, or |None| if not found."""
        footnote_elms = self.xpath(f"(./w:footnote[@w:id='{footnote_id}'])[1]")
        return footnote_elms[0] if footnote_elms else None

    def iter_authored_footnotes(self) -> List[CT_FtnEdn]:
        """The `w:footnote` elements an author wrote, in document order.

        The structural separator footnotes Word keeps at ids -1 and 0 are left out; see
        `STRUCTURAL_FOOTNOTE_TYPES`.
        """
        return [f for f in self.footnote_lst if not f.is_structural]

    def _next_available_footnote_id(self) -> int:
        """The next available footnote id.

        The schema allows any integer, and Word numbers author footnotes from 1 upward,
        having reserved -1 and 0 for the separators. As for comment ids, the default is
        `max() + 1`, falling back to the first unused non-negative integer if that would
        overflow a 32-bit signed integer.
        """
        used_ids = [int(x) for x in self.xpath("./w:footnote/@w:id")]

        next_id = max(used_ids, default=0) + 1

        if next_id <= 2**31 - 1:
            return next_id

        # -- fall-back to enumerating all used ids to find the first unused one --
        for expected, actual in enumerate(sorted(i for i in used_ids if i >= 1), start=1):
            if expected != actual:
                return expected

        return len(used_ids)


class CT_FtnEdn(BaseOxmlElement):
    """`w:footnote` element, a single footnote.

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
    """`w:footnoteReference` element, the mark in the body text that cites a footnote."""

    id: int = RequiredAttribute("w:id", ST_DecimalNumber)  # pyright: ignore[reportAssignmentType]
    customMarkFollows: bool | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:customMarkFollows", ST_OnOff
    )
