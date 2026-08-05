"""Captions — a label, a self-renumbering sequence field, and a cross-reference target.

Everything a caption is built from already existed: `Paragraph.add_field()`, the `SEQ`
builder in :mod:`docx.fields`, `REF` for the reference, and bookmarks. What was missing
was the one call that puts them together, because assembling one by hand means:

1. insert a paragraph in the "Caption" style
2. add the literal label text and separator
3. add a `SEQ Figure \\* ARABIC` field
4. wrap the whole thing in a bookmark with a `_Ref`-prefixed name and an unused id
5. remember that name so a later `REF` field can point at it

Step 4 is the one people get wrong. Word's own cross-reference dialogue offers only
targets whose bookmark name follows the `_Ref` convention, so a caption bookmarked with
an arbitrary name is invisible in it — the caption works, and the user cannot reference
it from the UI.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from docx import fields

if TYPE_CHECKING:
    from docx.text.paragraph import Paragraph

#: The prefix Word's cross-reference dialogue looks for in a bookmark name.
_REF_PREFIX = "_Ref"

#: A `_Ref` bookmark name — the prefix and the nine digits Word writes after it.
_REF_NAME_RE = re.compile(r"^_Ref(\d+)$")

#: Word writes nine digits; staying in that shape keeps the names sorting sensibly
#: alongside the ones Word generates for itself.
_REF_NAME_DIGITS = 9


class Caption:
    """A caption paragraph, carrying the bookmark name a cross-reference points at.

    Returned by :meth:`.Document.add_caption`. It is a thin wrapper over the paragraph;
    :attr:`paragraph` is the |Paragraph| itself for any further formatting.
    """

    def __init__(self, paragraph: Paragraph, bookmark_name: str, label: str):
        self._paragraph = paragraph
        self._bookmark_name = bookmark_name
        self._label = label

    def __repr__(self) -> str:
        return "<docx.caption.Caption %r bookmark=%r>" % (self.text, self._bookmark_name)

    @property
    def paragraph(self) -> Paragraph:
        """The |Paragraph| this caption is."""
        return self._paragraph

    @property
    def bookmark_name(self) -> str:
        """The bookmark name a cross-reference to this caption uses::

            document.add_paragraph().add_field(
                fields.cross_reference(caption.bookmark_name)
            )

        Generated in Word's own `_Ref` shape, so Word's cross-reference dialogue offers
        this caption as a target. That shape also means the bookmark does not appear in
        :attr:`.Document.bookmarks`, which leaves out the ones Word maintains for
        itself; :meth:`.Bookmarks.iter_all` reaches it.
        """
        return self._bookmark_name

    @property
    def label(self) -> str:
        """The caption's series, e.g. ``"Figure"``. Word numbers each independently."""
        return self._label

    @property
    def text(self) -> str:
        """The caption's text as the document currently reads it.

        The number is a `SEQ` field, so it shows only once Word has computed it; before
        that this reads as the label and the caption text with the number missing.
        """
        return self._paragraph.text

    @property
    def number(self) -> str | None:
        """The number Word last computed for this caption, or |None|.

        A `SEQ` field's result is cached in the document, so this reads back after a
        round trip through Word. It is |None| for a caption this library has just
        written, which has no cached result yet.
        """
        for field in self._paragraph.fields:
            if field.type == "SEQ":
                return field.result_text or None
        return None


def next_ref_bookmark_name(document_element: object) -> str:
    """A `_Ref`-prefixed bookmark name unused in the document.

    Word derives its own from a timestamp; a counter is used here instead, since a
    timestamp would make the same document generate different bytes on each run and
    byte-reproducible output is something this library keeps.
    """
    highest = 0
    for name in document_element.xpath(  # pyright: ignore[reportAttributeAccessIssue]
        "//w:bookmarkStart/@w:name"
    ):
        match = _REF_NAME_RE.match(name)
        if match:
            highest = max(highest, int(match.group(1)))
    return "%s%0*d" % (_REF_PREFIX, _REF_NAME_DIGITS, highest + 1)


def add_caption(
    container: object,
    label: str,
    text: str = "",
    *,
    style: str | None = "Caption",
    separator: str = " ",
    restart_at_heading_level: int | None = None,
    before: Paragraph | None = None,
) -> Caption:
    """Build a caption paragraph in `container`; see :meth:`.Document.add_caption`."""
    from docx.text.paragraph import Paragraph

    paragraph = container.add_paragraph()  # pyright: ignore[reportAttributeAccessIssue]
    if before is not None:
        before._p.addprevious(paragraph._p)  # pyright: ignore[reportPrivateUsage]
    if style is not None:
        paragraph.style = style

    paragraph.add_run(label + " ")
    paragraph.add_field(
        fields.sequence(label, restart_at_heading_level=restart_at_heading_level)
    )
    if text:
        paragraph.add_run(separator + text)

    part = paragraph.part
    bookmark_name = next_ref_bookmark_name(part.element)
    paragraph._p.add_bookmark_around_content(  # pyright: ignore[reportPrivateUsage]
        part.next_bookmark_id, bookmark_name
    )

    assert isinstance(paragraph, Paragraph)
    return Caption(paragraph, bookmark_name, label)


def caption_bookmark_names(document_element: object) -> tuple[str, ...]:
    """Every `_Ref`-prefixed bookmark name in the document, in document order."""
    return tuple(
        name
        for name in document_element.xpath(  # pyright: ignore[reportAttributeAccessIssue]
            "//w:bookmarkStart/@w:name"
        )
        if _REF_NAME_RE.match(name)
    )
