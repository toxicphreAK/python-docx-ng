"""Removing the things a document carries that nothing points at.

Three separate kinds of dead weight, each reached the same way — find what is
referenced, drop the rest:

- **Styles.** A document created by this library defines 164 of them and a
  one-paragraph document references one. This is :meth:`.Styles.remove_unused`, built on
  the reachability closure in :mod:`docx.styles.usage`.
- **Numbering definitions.** A `w:abstractNum` no `w:num` points at, and a `w:num` no
  `w:numPr` points at, are both dead.
- **Orphan media.** An image part related from nothing, left behind when the run or
  shape that displayed it was deleted. The `.delete()` API added in 2.0.0 makes this
  reachable from ordinary use.

:func:`cleanup` runs the lot; the individual operations stay public, because "remove
unused styles but leave my media alone" is a reasonable thing to want.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, NamedTuple, Set, Tuple

from docx.opc.constants import RELATIONSHIP_TYPE as RT

if TYPE_CHECKING:
    from docx.parts.document import DocumentPart


class CleanupResult(NamedTuple):
    """What a :func:`cleanup` pass removed."""

    #: The style ids removed.
    styles: Tuple[str, ...]
    #: The `w:num` numIds removed.
    num_ids: Tuple[int, ...]
    #: The `w:abstractNum` abstractNumIds removed.
    abstract_num_ids: Tuple[int, ...]
    #: The partnames of the media parts removed.
    media: Tuple[str, ...]
    #: How many `w:lsdException` overrides were removed.
    latent_styles: int

    def __str__(self) -> str:
        return (
            "removed %d styles, %d numbering definitions, %d abstract numbering"
            " definitions, %d media parts and %d latent style exceptions"
            % (
                len(self.styles),
                len(self.num_ids),
                len(self.abstract_num_ids),
                len(self.media),
                self.latent_styles,
            )
        )


def _referenced_num_ids(document_part: DocumentPart) -> Set[int]:
    """The numIds any content in this document applies, across every story part.

    Includes the `w:numId` inside a style's `w:pPr/w:numPr`, which is how a list style
    applies numbering without any paragraph naming it.
    """
    from docx.styles.usage import _iter_style_parts  # pyright: ignore[reportPrivateUsage]

    num_ids: Set[int] = set()
    parts = list(_iter_style_parts(document_part))
    with contextlib.suppress(KeyError):
        parts.append(document_part.part_related_by(RT.STYLES))
    for part in parts:
        element = getattr(part, "element", None)
        if element is None:
            continue
        for val in element.xpath("//w:numPr/w:numId/@w:val"):
            try:
                num_ids.add(int(val))
            except ValueError:
                continue
    return num_ids


def remove_unused_numbering(document_part: DocumentPart) -> tuple[Tuple[int, ...], Tuple[int, ...]]:
    """Drop the numbering definitions nothing references; return (numIds, abstractNumIds).

    A `w:num` is dead when no `w:numPr` in any story part or style names its numId. A
    `w:abstractNum` is dead when no surviving `w:num` points at it *and* no surviving
    abstract definition chains to it through `w:numStyleLink`.

    Does nothing, and reports nothing removed, for a document with no numbering part —
    reading one would create it.
    """
    if not document_part.has_numbering_part:
        return (), ()

    numbering = document_part.numbering_part.element
    referenced = _referenced_num_ids(document_part)

    removed_num_ids: list[int] = []
    for num in list(numbering.num_lst):
        if num.numId not in referenced:
            removed_num_ids.append(num.numId)
            numbering.remove(num)

    live_abstract_ids = {num.abstractNumId.val for num in numbering.num_lst}
    # -- an abstract definition can point at another through `w:numStyleLink`, so the
    # -- survivors' own references have to be followed before deciding what is dead --
    by_id = {a.abstractNumId: a for a in numbering.abstractNum_lst}
    pending = set(live_abstract_ids)
    reachable: Set[int] = set()
    while pending:
        abstract_id = pending.pop()
        if abstract_id in reachable or abstract_id not in by_id:
            continue
        reachable.add(abstract_id)
        for style_id in by_id[abstract_id].xpath("./w:numStyleLink/@w:val"):
            for other in numbering.abstractNum_lst:
                if other.xpath("./w:styleLink/@w:val") == [style_id]:
                    pending.add(other.abstractNumId)

    removed_abstract_ids: list[int] = []
    for abstractNum in list(numbering.abstractNum_lst):
        if abstractNum.abstractNumId not in reachable:
            removed_abstract_ids.append(abstractNum.abstractNumId)
            numbering.remove(abstractNum)

    return tuple(removed_num_ids), tuple(removed_abstract_ids)


def remove_orphan_media(document_part: DocumentPart) -> Tuple[str, ...]:
    """Drop image relationships nothing in the document part's XML refers to.

    An `r:embed`, `r:link` or `r:id` naming the relationship is what keeps an image
    alive. Deleting a paragraph that held a picture leaves the relationship and the part
    behind; this is what removes them.

    Only the document part's own image relationships are considered. A picture in a
    header or a footnote belongs to that part's relationships and is not this pass's
    business — a header image is not orphaned by anything happening in the body.
    """
    referenced = set(
        document_part.element.xpath("//@r:embed | //@r:link | //@r:id")
    )
    removed: list[str] = []
    for rId, rel in list(document_part.rels.items()):
        if rel.reltype != RT.IMAGE or rel.is_external:
            continue
        if rId not in referenced:
            removed.append(str(rel.target_part.partname))
            document_part.drop_rel(rId)
    return tuple(removed)


def cleanup(
    document_part: DocumentPart,
    *,
    styles: bool = True,
    numbering: bool = True,
    media: bool = True,
    latent_styles: bool = False,
    keep: tuple[str, ...] = (),
) -> CleanupResult:
    """Remove what this document carries that nothing points at.

    Each flag turns one pass on or off; `keep` names styles to preserve along with their
    dependencies, as for :meth:`.Styles.remove_unused`.

    `latent_styles` is |False| by default and separate from `styles` on purpose:
    removing a `w:lsdException` changes what a user sees in Word's style gallery rather
    than how the document renders, which is a different kind of change from removing a
    style definition.

    Styles are pruned before numbering, so a numbering definition kept alive only by a
    style that is about to go is correctly seen as dead.
    """
    removed_styles: Tuple[str, ...] = ()
    if styles:
        removed_styles = document_part.styles.remove_unused(keep=keep)

    removed_nums: Tuple[int, ...] = ()
    removed_abstract_nums: Tuple[int, ...] = ()
    if numbering:
        removed_nums, removed_abstract_nums = remove_unused_numbering(document_part)

    removed_media: Tuple[str, ...] = ()
    if media:
        removed_media = remove_orphan_media(document_part)

    trimmed = 0
    if latent_styles:
        trimmed = document_part.styles.latent_styles.trim()

    return CleanupResult(
        styles=removed_styles,
        num_ids=removed_nums,
        abstract_num_ids=removed_abstract_nums,
        media=removed_media,
        latent_styles=trimmed,
    )
