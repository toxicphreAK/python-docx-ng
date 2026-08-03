"""Shared bookkeeping for removing content from a document.

Removing an element is one line of lxml. Removing it *safely* is not: the content may
have carried the only reference to a hyperlink relationship, or one half of a comment
range or bookmark, and dropping it without tidying those leaves a document Word either
repairs on open or refuses outright.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from docx.oxml.ns import qn

if TYPE_CHECKING:
    from docx.opc.part import Part
    from docx.oxml.xmlchemy import BaseOxmlElement

# -- the range-marker pairs whose halves must be removed together. Each entry is
# -- (start tag, end tag); the two are paired by their `w:id` attribute. --
_RANGE_MARKER_PAIRS = (
    ("w:bookmarkStart", "w:bookmarkEnd"),
    ("w:commentRangeStart", "w:commentRangeEnd"),
)


def delete_element(element: BaseOxmlElement, part: Part | None) -> None:
    """Remove `element` from its tree, tidying what it referred to.

    Any relationship referenced only from inside `element` is dropped, and the surviving
    half of any range marker whose partner is inside `element` is removed too, so no
    dangling `w:bookmarkStart` or `w:commentRangeStart` is left behind.

    `part` may be |None| for an element not attached to a package, in which case the
    relationship cleanup is skipped.
    """
    _remove_orphaned_range_markers(element)
    rIds = _rIds_within(element) if part is not None else []

    parent = element.getparent()
    if parent is not None:
        parent.remove(element)

    if part is not None:
        for rId in rIds:
            # -- the element is gone, so a remaining reference is a real one. Note this
            # -- is not `Part.drop_rel()`, whose threshold assumes the caller's own
            # -- reference is still in the XML. --
            if rId in part.rels and _rel_ref_count(part, rId) == 0:
                del part.rels[rId]


def _rel_ref_count(part: Part, rId: str) -> int:
    """The number of references to `rId` remaining in `part`'s XML."""
    rIds = part.element.xpath("//@r:id")
    return sum(1 for candidate in rIds if candidate == rId)


def _rIds_within(element: BaseOxmlElement) -> list[str]:
    """The relationship ids referenced from inside `element`, without duplicates."""
    rIds = element.xpath(".//@r:id | ./@r:id")
    return list(dict.fromkeys(rIds))


def _remove_orphaned_range_markers(element: BaseOxmlElement) -> None:
    """Remove range markers outside `element` whose partner is inside it.

    A `w:bookmarkStart` whose `w:bookmarkEnd` is about to disappear would otherwise be
    left unmatched.
    """
    root = element.getroottree().getroot()
    for start_tag, end_tag in _RANGE_MARKER_PAIRS:
        for inner_tag, outer_tag in ((start_tag, end_tag), (end_tag, start_tag)):
            for marker in element.iter(qn(inner_tag)):
                id = marker.get(qn("w:id"))
                if id is None:
                    continue
                for partner in root.iter(qn(outer_tag)):
                    if partner.get(qn("w:id")) != id:
                        continue
                    # -- leave a partner that is itself inside `element`; it goes with
                    # -- the rest of it --
                    if _is_within(partner, element):
                        continue
                    partner.getparent().remove(partner)


def _is_within(element: BaseOxmlElement, ancestor: BaseOxmlElement) -> bool:
    """True if `element` is `ancestor` or a descendant of it."""
    for candidate in element.iterancestors():
        if candidate is ancestor:
            return True
    return element is ancestor
