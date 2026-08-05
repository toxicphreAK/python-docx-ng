"""Custom element classes for tracked changes (revisions).

A revision is recorded in one of two shapes:

**Content revisions** wrap the content they affect. `w:ins` holds runs that were added,
`w:del` runs that were removed — with their text in `w:delText` rather than `w:t`, so a
consumer that does not understand deletions does not show it. `w:moveTo` and `w:moveFrom`
are the two halves of a move, and behave as an insertion and a deletion respectively::

    <w:ins w:id="1" w:author="Ada" w:date="2026-01-02T10:00:00Z">
      <w:r><w:t>added</w:t></w:r>
    </w:ins>
    <w:del w:id="2" w:author="Ada" w:date="2026-01-02T10:00:00Z">
      <w:r><w:delText>removed</w:delText></w:r>
    </w:del>

**Property revisions** record what the formatting *used to be*: `w:rPrChange` holds the
previous `w:rPr`, `w:pPrChange` the previous `w:pPr`, and so on. Accepting one means
dropping the record; rejecting it means putting the recorded properties back.

The same `w:ins` and `w:del` tag names are also used as empty markers — in `w:pPr/w:rPr`
they say the paragraph mark itself was inserted or deleted, which is how a paragraph
split or merge is tracked, and in `w:trPr` they say a table row was. lxml resolves an
element class by tag name alone, so one class serves every position; whether a given
`w:ins` wraps content is discovered from its children rather than declared.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Iterator, List, cast

from docx.oxml.ns import qn
from docx.oxml.sdt import TRANSPARENT_WRAPPER_TAGS
from docx.oxml.simpletypes import ST_DecimalNumber, ST_String
from docx.oxml.xmlchemy import BaseOxmlElement, OptionalAttribute

if TYPE_CHECKING:
    from docx.oxml.text.hyperlink import CT_Hyperlink
    from docx.oxml.text.run import CT_R

# -- content revisions that add text. Their content is part of the document as it now
# -- reads, and is not part of the document as it read before. --
INSERTED_TAGS = ("w:ins", "w:moveTo")

# -- content revisions that remove text: the other way round --
DELETED_TAGS = ("w:del", "w:moveFrom")

# -- property revisions, each holding the properties as they were before the change --
PROPERTY_CHANGE_TAGS = (
    "w:rPrChange",
    "w:pPrChange",
    "w:tblPrChange",
    "w:trPrChange",
    "w:tcPrChange",
    "w:sectPrChange",
    "w:tblGridChange",
)

# -- every tag that records a revision --
ALL_REVISION_TAGS = INSERTED_TAGS + DELETED_TAGS + PROPERTY_CHANGE_TAGS

# -- run children contributing text to the document as it read *before* the revisions;
# -- `w:delText` is here and `w:t` is too, because a run outside any revision keeps its
# -- text in both readings --
_ORIGINAL_TEXT_XPATH = "w:br | w:cr | w:noBreakHyphen | w:ptab | w:t | w:delText | w:tab"


class CT_TrackChange(BaseOxmlElement):
    """A revision element — `w:ins`, `w:del`, `w:moveFrom`, `w:moveTo` or a `*Change`.

    Serves every position these tag names appear in, since lxml dispatches on tag name
    alone. A content revision has run children; a paragraph-mark or table-row marker has
    none; a property revision has the previous properties element.
    """

    # -- `w:author` and `w:id` are required of most of these types but not of all:
    # -- `w:tblGridChange` carries only `w:id`, and a document stripped of personal
    # -- information has the author blanked. Reading one is not the moment to raise. --
    author: str = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:author", ST_String, default=""
    )
    id: int | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:id", ST_DecimalNumber
    )
    date_str: str | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:date", ST_String
    )

    @property
    def date(self) -> dt.datetime | None:
        """When the revision was made, or |None| when the document does not say.

        |None| too when the timestamp is not a valid ISO 8601 datetime. Word writes
        `w:date` in that form, but an anonymised document has it stripped or blanked and
        that is not a reason to refuse to read the revision.
        """
        value = self.date_str
        if not value:
            return None
        try:
            # -- Word writes a trailing "Z"; `fromisoformat` only learned to parse that
            # -- in Python 3.11, and this package supports 3.9 --
            return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    @property
    def is_content_revision(self) -> bool:
        """True when this revision wraps content rather than marking a position."""
        return self.tag in (qn(t) for t in INSERTED_TAGS + DELETED_TAGS)

    @property
    def text(self) -> str:  # pyright: ignore[reportIncompatibleMethodOverride]
        """The text this revision covers, the empty string when it covers none.

        Both `w:t` and `w:delText` count: the point of a deletion is the text it removed,
        and reporting nothing for it would make the revision useless to read.
        """
        return "".join(str(e) for e in self.xpath(f".//*[{_text_child_predicate()}]"))


def _text_child_predicate() -> str:
    """An XPath predicate matching any text-bearing run child."""
    return " or ".join(f"self::{tag}" for tag in _ORIGINAL_TEXT_XPATH.split(" | "))


def run_original_text(r: CT_R) -> str:
    """The text of `r` as the document read before its revisions.

    Differs from `CT_R.text` only for a run inside a deletion, whose text is in
    `w:delText` and so does not appear in the document as it now reads.
    """
    return "".join(str(e) for e in r.xpath(_ORIGINAL_TEXT_XPATH))


def iter_original_run_content(element: BaseOxmlElement) -> Iterator[CT_R | CT_Hyperlink]:
    """Generate the runs of `element` as the document read before its revisions.

    Deletions are descended into and insertions skipped — the opposite of
    :func:`docx.oxml.sdt.iter_run_content`, which generates the document as it now
    reads.
    """
    deleted = tuple(qn(t) for t in DELETED_TAGS)
    inserted = tuple(qn(t) for t in INSERTED_TAGS)

    for child in element.iterchildren():
        tag = child.tag
        if tag in (qn("w:r"), qn("w:hyperlink")):
            yield cast("CT_R | CT_Hyperlink", child)
        elif tag in inserted:
            continue  # -- not there before the revision --
        elif tag in deleted or tag == qn("w:fldSimple") or tag in TRANSPARENT_WRAPPER_TAGS:
            yield from iter_original_run_content(cast(BaseOxmlElement, child))
        elif tag == qn("w:sdt"):
            sdtContent = child.find(qn("w:sdtContent"))
            if sdtContent is not None:
                yield from iter_original_run_content(cast(BaseOxmlElement, sdtContent))


def iter_revision_elements(element: BaseOxmlElement) -> List[CT_TrackChange]:
    """Every revision element in the subtree of `element`, in document order."""
    xpath = " | ".join(f".//{tag}" for tag in ALL_REVISION_TAGS)
    return cast("List[CT_TrackChange]", element.xpath(xpath))
