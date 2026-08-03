"""Custom element classes for bookmarks.

A bookmark is a named range delimited by a `w:bookmarkStart` and a matching
`w:bookmarkEnd`, paired by their `w:id`. The pair is not nested in anything: the two
elements sit as siblings of whatever content they surround, which is what lets a
bookmark span paragraphs, table cells and block containers without regard to the
structure in between.

It also means an unmatched start or end is structurally possible, and real documents
contain them, so nothing here treats a missing counterpart as an error.
"""

from __future__ import annotations

from docx.oxml.simpletypes import ST_DecimalNumber, ST_String
from docx.oxml.xmlchemy import BaseOxmlElement, RequiredAttribute

# -- Word's own bookmarks. `_GoBack` records the last edit position and `_Toc…` anchors
# -- a table-of-contents entry; neither is a bookmark the user made. --
_HIDDEN_BOOKMARK_PREFIXES = ("_GoBack", "_Toc", "_Ref", "_Hlk")


def is_hidden_bookmark_name(name: str) -> bool:
    """True for a bookmark Word maintains for itself rather than one a user made."""
    return name.startswith(_HIDDEN_BOOKMARK_PREFIXES)


class CT_BookmarkStart(BaseOxmlElement):
    """`w:bookmarkStart` element, the opening delimiter of a named range."""

    id: int = RequiredAttribute("w:id", ST_DecimalNumber)  # pyright: ignore[reportAssignmentType]
    name: str = RequiredAttribute("w:name", ST_String)  # pyright: ignore[reportAssignmentType]

    @property
    def bookmarkEnd(self) -> CT_BookmarkEnd | None:
        """The `w:bookmarkEnd` matching this start, or |None| when there is none.

        An unmatched start is common enough in documents produced by other tools that it
        is reported rather than raised on.
        """
        matches = self.xpath("//w:bookmarkEnd[@w:id='%d']" % self.id)
        return matches[0] if matches else None


class CT_BookmarkEnd(BaseOxmlElement):
    """`w:bookmarkEnd` element, the closing delimiter of a named range."""

    id: int = RequiredAttribute("w:id", ST_DecimalNumber)  # pyright: ignore[reportAssignmentType]
