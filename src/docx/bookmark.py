"""The |Bookmark| and |Bookmarks| proxy objects.

A bookmark names a range of a document. It is the anchor mechanism everything that
refers to a place in a document is built on: internal hyperlinks, cross-references,
captions that renumber, and table-of-contents entries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator, Sequence, overload

from docx.oxml.bookmark import is_hidden_bookmark_name
from docx.oxml.ns import qn
from docx.shared import Parented

if TYPE_CHECKING:
    import docx.types as t
    from docx.oxml.bookmark import CT_BookmarkStart


class Bookmark(Parented):
    """Proxy for a `w:bookmarkStart` element and the range it names."""

    def __init__(self, bookmarkStart: CT_BookmarkStart, parent: t.ProvidesStoryPart):
        super(Bookmark, self).__init__(parent)
        self._element = self._bookmarkStart = bookmarkStart

    def __repr__(self) -> str:
        return "<%s %r id=%d>" % (type(self).__name__, self.name, self.id)

    def delete(self) -> None:
        """Remove this bookmark, leaving the content it named in place.

        Removes both delimiters, including an unmatched one.
        """
        bookmarkEnd = self._bookmarkStart.bookmarkEnd
        if bookmarkEnd is not None:
            bookmarkEnd.getparent().remove(bookmarkEnd)
        self._bookmarkStart.getparent().remove(self._bookmarkStart)

    @property
    def id(self) -> int:
        """The `w:id` pairing this bookmark's two delimiters.

        Unique across the document.
        """
        return self._bookmarkStart.id

    @property
    def is_closed(self) -> bool:
        """|True| when this bookmark has a matching `w:bookmarkEnd`.

        An unmatched start is invalid but appears in real documents, so it is reported
        rather than raised on. The `.text` of an unclosed bookmark is the empty string.
        """
        return self._bookmarkStart.bookmarkEnd is not None

    @property
    def is_hidden(self) -> bool:
        """|True| for a bookmark Word maintains for itself.

        `_GoBack` records the last edit position and `_Toc…` anchors a table-of-contents
        entry. |Bookmarks| leaves these out by default.
        """
        return is_hidden_bookmark_name(self.name)

    @property
    def name(self) -> str:
        """The name of this bookmark, as shown in Word's bookmark dialog."""
        return self._bookmarkStart.name

    @property
    def text(self) -> str:
        """The text of the content this bookmark spans.

        Paragraph boundaries inside the range become newlines, as they do for a table
        cell. The empty string when the bookmark is unclosed or spans no text.
        """
        bookmarkEnd = self._bookmarkStart.bookmarkEnd
        if bookmarkEnd is None:
            return ""

        # -- walk the whole tree in document order, collecting text between the two
        # -- delimiters. They can sit in different block containers, so nothing
        # -- structural can be assumed about what lies between them. --
        chunks: list[str] = []
        inside = False
        for element in self._bookmarkStart.getroottree().getroot().iter():
            if element is self._bookmarkStart:
                inside = True
                continue
            if element is bookmarkEnd:
                break
            if not inside:
                continue
            if element.tag == qn("w:t"):
                chunks.append(element.text or "")
            elif element.tag == qn("w:tab"):
                chunks.append("\t")
            elif element.tag in (qn("w:br"), qn("w:cr")):
                chunks.append("\n")
            elif element.tag == qn("w:p") and chunks:
                # -- a paragraph boundary inside the range --
                chunks.append("\n")
        return "".join(chunks)


class Bookmarks(Parented, Sequence[Bookmark]):
    """The bookmarks in a document, in document order.

    Supports ``len()``, iteration, indexed access and lookup by name::

        document.bookmarks["Introduction"].text

    Bookmarks Word maintains for itself, such as `_GoBack` and the `_Toc…` anchors, are
    left out; pass ``include_hidden=True`` to :meth:`.iter_all` to see them.
    """

    def __init__(self, element: t.ProvidesXmlPart, parent: t.ProvidesStoryPart):
        super(Bookmarks, self).__init__(parent)
        self._element = element

    def __contains__(self, name: object) -> bool:
        return any(bookmark.name == name for bookmark in self)

    @overload
    def __getitem__(self, key: int) -> Bookmark: ...

    @overload
    def __getitem__(self, key: str) -> Bookmark: ...

    def __getitem__(self, key: int | str) -> Bookmark:
        """Bookmark at index `key`, or the one named `key`.

        Raises |KeyError| when no bookmark has that name, or |IndexError| when the index
        is out of range.
        """
        if isinstance(key, str):
            for bookmark in self:
                if bookmark.name == key:
                    return bookmark
            raise KeyError("no bookmark named %r" % key)
        return list(self)[key]

    def __iter__(self) -> Iterator[Bookmark]:
        return (b for b in self.iter_all() if not b.is_hidden)

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def get(self, name: str, default: Bookmark | None = None) -> Bookmark | None:
        """The bookmark named `name`, or `default` when there is none."""
        try:
            return self[name]
        except KeyError:
            return default

    def iter_all(self, include_hidden: bool = True) -> Iterator[Bookmark]:
        """Generate every bookmark in the document, in document order.

        Includes Word's own bookmarks unless `include_hidden` is |False|, and includes a
        bookmark whose `w:bookmarkEnd` is missing.
        """
        for bookmarkStart in self._element.xpath("//w:bookmarkStart"):
            bookmark = Bookmark(bookmarkStart, self._parent)
            if include_hidden or not bookmark.is_hidden:
                yield bookmark
