"""The tracked-changes API — reading, accepting and rejecting revisions.

Any document that has been through review carries revision markup, and before this
existed the library's handling of it was silently wrong rather than loudly broken:
inserted text was dropped, deleted text was dropped, and `Paragraph.text` returned
something that matched neither the original nor the final version of the document.

The text model is now defined:

- :attr:`.Paragraph.text` is the document **as it now reads** — every revision accepted.
  Insertions are included; deletions are not. This is what almost every caller wants and
  what makes `.text` consistent with what a reader sees with markup hidden.
- :attr:`.Paragraph.original_text` is the document **as it read before** the revisions.
  Deletions are included; insertions are not.

Accepting a revision makes the first reading permanent; rejecting it makes the second.

**In scope:** `w:ins`, `w:del`, `w:moveFrom` and `w:moveTo`, whether they wrap content,
mark a paragraph mark as inserted or deleted (which is how a paragraph split or merge is
tracked), or mark a table row; and the `*Change` elements recording a formatting change.

**Not in scope:** `w:numberingChange`, and the cell-level merge revisions
(`w:cellMerge`). Both are rare and neither has a well-defined accept that this library
could perform without guessing.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Iterator, List

from docx.enum.revision import WD_REVISION_TYPE
from docx.oxml.ns import qn
from docx.oxml.parser import OxmlElement
from docx.oxml.revision import (
    DELETED_TAGS,
    INSERTED_TAGS,
    PROPERTY_CHANGE_TAGS,
    iter_revision_elements,
)
from docx.shared import StoryChild

if TYPE_CHECKING:
    from lxml.etree import _Element  # pyright: ignore[reportPrivateUsage]

    import docx.types as t
    from docx.oxml.revision import CT_TrackChange
    from docx.oxml.xmlchemy import BaseOxmlElement

# -- the properties element each `*Change` records the previous state of --
_CHANGE_TARGET = {
    "w:rPrChange": "w:rPr",
    "w:pPrChange": "w:pPr",
    "w:tblPrChange": "w:tblPr",
    "w:trPrChange": "w:trPr",
    "w:tcPrChange": "w:tcPr",
    "w:sectPrChange": "w:sectPr",
    "w:tblGridChange": "w:tblGrid",
}


class Revision(StoryChild):
    """One tracked change — an insertion, a deletion, a move or a formatting change.

    Not constructed directly; reached through :attr:`.Document.revisions` or
    :attr:`.Paragraph.revisions`.
    """

    def __init__(self, element: CT_TrackChange, parent: t.ProvidesStoryPart):
        super().__init__(parent)
        self._element = element

    def __repr__(self) -> str:
        return f"<docx.revisions.Revision {self.type.name} by {self.author!r}>"

    @property
    def author(self) -> str:
        """The name of whoever made this change.

        The empty string when the document does not say, which is the case for a
        `w:tblGridChange` and for a document stripped of personal information.
        """
        return self._element.author

    @property
    def date(self) -> dt.datetime | None:
        """When the change was made, |None| when the document does not say.

        |None| too for an unparseable timestamp, which an anonymised document has.
        """
        return self._element.date

    @property
    def id(self) -> int | None:
        """The `w:id` of this revision, |None| when it carries none.

        Unique among the revisions of a document when present.
        """
        return self._element.id

    @property
    def is_paragraph_mark(self) -> bool:
        """True when this revision is of a paragraph mark rather than of content.

        An inserted paragraph mark is a paragraph split; a deleted one is a merge with
        the paragraph that follows. Accepting or rejecting one therefore joins or splits
        paragraphs rather than adding or removing text.
        """
        parent = self._element.getparent()
        if parent is None or parent.tag != qn("w:rPr"):
            return False
        grandparent = parent.getparent()
        return grandparent is not None and grandparent.tag == qn("w:pPr")

    @property
    def is_row(self) -> bool:
        """True when this revision marks a whole table row as inserted or deleted."""
        parent = self._element.getparent()
        return parent is not None and parent.tag == qn("w:trPr")

    @property
    def text(self) -> str:
        """The text this revision covers, the empty string when it covers none.

        Empty for a paragraph-mark revision, a row revision and a formatting change,
        none of which cover text of their own.
        """
        return self._element.text

    @property
    def type(self) -> WD_REVISION_TYPE:
        """Member of :ref:`WdRevisionType` saying what kind of change this is."""
        local = self._element.tag.split("}")[1]
        if f"w:{local}" in PROPERTY_CHANGE_TAGS:
            return WD_REVISION_TYPE.FORMATTING
        return WD_REVISION_TYPE.from_xml(local)

    def accept(self) -> None:
        """Keep this change, and remove the record of it.

        An insertion's content stays and stops being marked as new; a deletion's content
        goes; a formatting change's record goes, leaving the current formatting in
        place. Accepting a deleted paragraph mark merges the paragraph with the one
        after it, which is what the deletion recorded.
        """
        self._apply(accept=True)

    def reject(self) -> None:
        """Undo this change, and remove the record of it.

        An insertion's content goes; a deletion's content comes back, its `w:delText`
        turned back into `w:t`; a formatting change puts the recorded previous
        properties back. Rejecting an inserted paragraph mark merges the paragraph with
        the one after it, undoing the split.
        """
        self._apply(accept=False)

    # -- private ------------------------------------------------------

    def _apply(self, accept: bool) -> None:
        element = self._element
        local = f"w:{element.tag.split('}')[1]}"

        if local in PROPERTY_CHANGE_TAGS:
            self._apply_property_change(accept)
            return

        keep_content = (local in INSERTED_TAGS) == accept

        if self.is_paragraph_mark:
            # -- "keeping" a paragraph mark leaves the paragraphs separate; not keeping
            # -- it joins them. Both need the paragraph found before the marker is
            # -- detached, since afterwards it has no ancestors to search. --
            p = _ancestor(element, "w:p")
            _remove(element)
            if not keep_content and p is not None:
                _merge_with_following_paragraph(p)
            return

        if self.is_row:
            tr = _ancestor(element, "w:tr")
            _remove(element)
            if not keep_content and tr is not None:
                _remove(tr)
            return

        if keep_content:
            _unwrap(element, restore_deleted_text=local in DELETED_TAGS)
        else:
            _remove(element)

    def _apply_property_change(self, accept: bool) -> None:
        """Drop the record of a formatting change, or put the old properties back.

        Every `*Change` has the same shape: it sits inside the properties element it
        describes and holds a copy of that element as it was before the change. So
        rejecting is uniform — swap the current children for the recorded ones — and
        the recorded order comes with them, which matters because these are schema
        sequences.
        """
        element = self._element
        local = f"w:{element.tag.split('}')[1]}"
        properties = element.getparent()

        if accept or properties is None:
            _remove(element)
            return

        target_tag = _CHANGE_TARGET.get(local)
        previous = None if target_tag is None else element.find(qn(target_tag))

        _remove(element)
        if previous is None:
            # -- nothing was recorded, so there is nothing to put back; dropping the
            # -- record is the most that can be done without inventing formatting --
            return

        for child in list(properties):
            properties.remove(child)
        for child in list(previous):
            properties.append(child)


def iter_revisions(element: BaseOxmlElement, parent: t.ProvidesStoryPart) -> Iterator[Revision]:
    """Generate a |Revision| for each tracked change in the subtree of `element`."""
    for revision_elm in iter_revision_elements(element):
        yield Revision(revision_elm, parent)


def apply_all(element: BaseOxmlElement, parent: t.ProvidesStoryPart, accept: bool) -> int:
    """Accept or reject every revision in `element`, returning how many were applied.

    Applied innermost-last and in reverse document order, so that unwrapping or removing
    one revision cannot invalidate another that has not been reached yet — a nested
    revision is dealt with before the one containing it.
    """
    revisions = list(iter_revisions(element, parent))
    for revision in reversed(revisions):
        # -- a revision whose container was already removed is no longer in the tree --
        if revision._element.getparent() is None:  # pyright: ignore[reportPrivateUsage]
            continue
        if accept:
            revision.accept()
        else:
            revision.reject()
    return len(revisions)


# -- tree surgery -------------------------------------------------------


def _remove(element: _Element) -> None:
    """Remove `element` from its parent, if it still has one."""
    parent = element.getparent()
    if parent is not None:
        parent.remove(element)


def _unwrap(element: _Element, restore_deleted_text: bool = False) -> None:
    """Replace `element` with its children, in its position.

    When `restore_deleted_text`, each `w:delText` becomes a `w:t`: the text is part of
    the document again, and a consumer looks for it under the ordinary tag.
    """
    parent = element.getparent()
    if parent is None:
        return
    if restore_deleted_text:
        for delText in element.findall(f".//{qn('w:delText')}"):
            _rename_delText(delText)

    index = list(parent).index(element)
    for offset, child in enumerate(list(element)):
        parent.insert(index + offset, child)
    parent.remove(element)


def _rename_delText(delText: _Element) -> None:
    """Replace a `w:delText` with a `w:t` holding the same text."""
    t = OxmlElement("w:t")
    t.text = delText.text
    space = delText.get(qn("xml:space"))
    if space is not None:
        t.set(qn("xml:space"), space)
    parent = delText.getparent()
    if parent is None:
        return
    parent.insert(list(parent).index(delText), t)
    parent.remove(delText)


def _ancestor(element: _Element, nsptag: str) -> _Element | None:
    """The nearest ancestor of `element` with tag `nsptag`, or |None|."""
    for ancestor in element.iterancestors():
        if ancestor.tag == qn(nsptag):
            return ancestor
    return None


def _merge_with_following_paragraph(p: _Element) -> None:
    """Join paragraph `p` with the one after it.

    This is what a deleted paragraph mark means: the two paragraphs are one. The
    following paragraph's content moves up and the paragraph itself goes; the surviving
    paragraph keeps its own properties, as Word does.
    """
    following = p.getnext()
    if following is None or following.tag != qn("w:p"):
        return

    for child in list(following):
        if child.tag == qn("w:pPr"):
            continue
        p.append(child)
    _remove(following)


def collect_authors(revisions: List[Revision]) -> List[str]:
    """The distinct authors of `revisions`, in the order they first appear."""
    authors: List[str] = []
    for revision in revisions:
        if revision.author not in authors:
            authors.append(revision.author)
    return authors
