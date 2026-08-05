"""Duplicating content — a paragraph, a run, a table row, a whole table.

`copy.deepcopy(paragraph._p)` followed by an `addnext()` works for plain text and
quietly breaks for anything interesting. Everything this module does beyond the deep
copy is a repair of one of those breakages:

- a picture's `r:embed` names a relationship id belonging to the *source* part, so a
  copied image is either the wrong image or a dangling reference;
- a hyperlink's `r:id` has the same problem, and points at an external target that may
  not exist in the destination package;
- `wp:docPr/@id` must be unique document-wide, and a deep copy duplicates it;
- bookmark ids and names collide, and Word treats a duplicate bookmark name as a second
  bookmark competing for anything that refers to it;
- a copy into a *different* document carries a `w:pStyle` naming a style that may not be
  there, and a `w:numPr` naming a `numId` that certainly is not.

The two hard pieces already existed: `Styles.copy_style_from()` resolves the style
closure and carries numbering across, and `StoryPart.next_id` allocates non-colliding
drawing ids. This is what uses them.
"""

from __future__ import annotations

import copy as copymod
from typing import TYPE_CHECKING, Dict, Set

from docx.oxml.ns import qn

if TYPE_CHECKING:
    from docx.opc.part import Part
    from docx.oxml.xmlchemy import BaseOxmlElement
    from docx.parts.story import StoryPart

#: The attributes that name a relationship from inside copied content.
_REL_ATTRS = (qn("r:embed"), qn("r:id"), qn("r:link"))

#: What to do about a style the destination document does not define.
_MISSING_STYLE_POLICIES = ("copy", "drop", "raise")


def copy_content(
    element: BaseOxmlElement,
    source_part: StoryPart,
    dest_part: StoryPart,
    *,
    missing_style: str = "copy",
) -> BaseOxmlElement:
    """A deep copy of `element` fit to be inserted into `dest_part`.

    The copy is not attached to anything; the caller places it. See
    :meth:`.Paragraph.copy_to` for what `missing_style` means.
    """
    if missing_style not in _MISSING_STYLE_POLICIES:
        raise ValueError(
            "missing_style must be one of %s, got %r"
            % (", ".join(repr(p) for p in _MISSING_STYLE_POLICIES), missing_style)
        )

    new_element = copymod.deepcopy(element)

    _remap_relationships(new_element, source_part, dest_part)
    _reassign_drawing_ids(new_element, dest_part)
    _strip_bookmarks(new_element)

    if source_part is not dest_part:
        _carry_styles(new_element, source_part, dest_part, missing_style)
        _carry_numbering(new_element, source_part, dest_part)

    return new_element


def _remap_relationships(
    element: BaseOxmlElement, source_part: StoryPart, dest_part: StoryPart
) -> None:
    """Repoint every relationship reference in `element` at `dest_part`'s own rels.

    Within one part this is a no-op — the ids already mean what they say. Across parts,
    relating the same image blob into the destination gives the sha1 deduplication for
    free, so copying a picture into a document that already has it does not add a second
    copy of the bytes.
    """
    if source_part is dest_part:
        return

    remapped: Dict[str, str] = {}
    for node in element.iter():
        for attr in _REL_ATTRS:
            rId = node.get(attr)
            if rId is None:
                continue
            if rId not in remapped:
                remapped[rId] = _relate_into(rId, source_part, dest_part)
            node.set(attr, remapped[rId])


def _relate_into(rId: str, source_part: Part, dest_part: Part) -> str:
    """The `rId` in `dest_part` denoting what `rId` denotes in `source_part`.

    An unknown id is left as it is: a reference the source itself could not resolve is
    already broken there, and inventing a target here would be worse than carrying the
    break over.
    """
    rel = source_part.rels.get(rId)
    if rel is None:
        return rId
    if rel.is_external:
        return dest_part.relate_to(rel.target_ref, rel.reltype, is_external=True)
    return dest_part.relate_to(rel.target_part, rel.reltype)


def _reassign_drawing_ids(element: BaseOxmlElement, dest_part: StoryPart) -> None:
    """Give every copied drawing a `wp:docPr/@id` unused in the destination.

    The id must be unique document-wide, and a deep copy duplicates whatever the source
    had. Ids are allocated one at a time rather than in a batch because `next_id` reads
    the destination's XML, and the copy is not in it yet.

    `@name` is left alone. Only the id has to be unique, and the name is the shape's own
    — the source file name for a picture, "Chart 1" for a chart — so overwriting it
    would discard information and mislabel anything that is not a picture. A drawing
    with no name at all gets one, since Word shows the field in its selection pane.
    """
    docPrs = element.xpath(".//wp:docPr")
    if not docPrs:
        return
    next_id = dest_part.next_id
    for offset, docPr in enumerate(docPrs):
        docPr.id = next_id + offset
        if not docPr.name:
            docPr.name = "Picture %d" % (next_id + offset)


def _strip_bookmarks(element: BaseOxmlElement) -> None:
    """Remove the bookmarks from a copy rather than duplicating their names.

    A bookmark name is document-wide and a duplicate is not a copy of a bookmark: Word
    treats it as a second bookmark of the same name, and anything referring to the name
    — a cross-reference, a table-of-contents entry — then resolves to whichever it finds
    first. Dropping them is the only outcome that is not silently wrong; use
    `Paragraph.add_bookmark()` on the copy to bookmark it afresh.
    """
    for tag in ("w:bookmarkStart", "w:bookmarkEnd"):
        for node in element.xpath(".//%s" % tag):
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)


def _carry_styles(
    element: BaseOxmlElement, source_part: StoryPart, dest_part: StoryPart, policy: str
) -> None:
    """Make each style the copy names resolvable in the destination document.

    Under `"copy"` a missing style is copied across with its dependency closure, which
    is what `Styles.copy_style_from()` is for. Under `"drop"` the reference is removed
    and the content falls back to the destination's default. Under `"raise"` the caller
    hears about it.
    """
    source_styles = source_part.document_part.styles
    dest_styles = dest_part.document_part.styles

    for node in element.xpath(".//w:pStyle | .//w:rStyle | .//w:tblStyle"):
        style_id = node.get(qn("w:val"))
        if style_id is None:
            continue
        if dest_styles._element.get_by_id(style_id) is not None:  # pyright: ignore
            continue

        source_style_elm = source_styles._element.get_by_id(style_id)  # pyright: ignore
        if source_style_elm is None:
            # -- a reference the source cannot resolve either; already broken there --
            continue

        if policy == "raise":
            raise ValueError(
                "destination document has no style with id %r; pass"
                " missing_style='copy' to bring it across or 'drop' to discard the"
                " reference" % style_id
            )
        if policy == "drop":
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)
            continue

        from docx.styles.style import StyleFactory

        copied = dest_styles.copy_style_from(
            StyleFactory(source_style_elm, source_part.document_part)
        )
        # -- `copy_style_from()` frees a colliding id, so the reference may need to move
        node.set(qn("w:val"), copied.style_id)


def _carry_numbering(
    element: BaseOxmlElement, source_part: StoryPart, dest_part: StoryPart
) -> None:
    """Copy the numbering definitions the copy names and repoint it at them.

    A `w:numId` means something else in the destination, so leaving it alone numbers the
    content according to whatever list happens to hold that id — a silent wrong answer
    rather than a visible failure.
    """
    numIds = element.xpath(".//w:numPr/w:numId")
    if not numIds:
        return

    source_doc_part = source_part.document_part
    dest_doc_part = dest_part.document_part
    if not source_doc_part.has_numbering_part:
        return

    source_numbering = source_doc_part.numbering_part.element
    dest_numbering = dest_doc_part.numbering_part.element
    num_id_map: Dict[int, int] = {}
    abstract_id_map: Dict[int, int] = {}

    for numId in numIds:
        val = numId.get(qn("w:val"))
        if val is None:
            continue
        try:
            source_num_id = int(val)
        except ValueError:
            continue
        if source_num_id not in num_id_map:
            new_num_id = _copy_num(
                source_num_id, source_numbering, dest_numbering, abstract_id_map
            )
            if new_num_id is None:
                continue
            num_id_map[source_num_id] = new_num_id
        numId.set(qn("w:val"), str(num_id_map[source_num_id]))


def _copy_num(
    source_num_id: int, source_numbering, dest_numbering, abstract_id_map: Dict[int, int]
) -> int | None:
    """Copy the `w:num` with `source_num_id` and its abstract definition; new numId.

    |None| when the source has no such definition, which leaves the reference alone.
    """
    try:
        source_num = source_numbering.num_having_numId(source_num_id)
    except KeyError:
        return None

    source_abstract_id = source_num.abstractNumId.val
    if source_abstract_id not in abstract_id_map:
        source_abstract = source_numbering.abstractNum_having_abstractNumId(source_abstract_id)
        if source_abstract is None:
            return None
        new_abstract = copymod.deepcopy(source_abstract)
        new_abstract.abstractNumId = _next_abstract_num_id(dest_numbering)
        # -- `w:nsid` is what Word uses to recognise a definition as one of its own;
        # -- carrying the source's over makes the destination's list gallery show two
        # -- definitions as the same list --
        for nsid in new_abstract.xpath("./w:nsid"):
            new_abstract.remove(nsid)
        dest_numbering.insert(_abstract_num_insert_index(dest_numbering), new_abstract)
        abstract_id_map[source_abstract_id] = new_abstract.abstractNumId

    new_num = dest_numbering.add_num(abstract_id_map[source_abstract_id])
    return new_num.numId


def _next_abstract_num_id(numbering) -> int:
    """The first unused `w:abstractNum/@w:abstractNumId` in `numbering`."""
    used: Set[int] = {int(v) for v in numbering.xpath("./w:abstractNum/@w:abstractNumId")}
    candidate = 0
    while candidate in used:
        candidate += 1
    return candidate


def _abstract_num_insert_index(numbering) -> int:
    """Where a new `w:abstractNum` goes: after the last one, before the first `w:num`.

    `CT_Numbering` is an `xsd:sequence` — every `w:abstractNum` precedes every `w:num` —
    and Word rejects a document that has them the other way round.
    """
    children = list(numbering)
    for index, child in enumerate(children):
        if child.tag == qn("w:num"):
            return index
    return len(children)


def destination_for(container: object) -> tuple[StoryPart, BaseOxmlElement]:
    """The `(part, element)` a copy goes into for `container`.

    A |Document| is not itself a block-item container — its body is — so it is
    unwrapped here rather than at each call site.
    """
    from docx.document import Document

    if isinstance(container, Document):
        body = container._body  # pyright: ignore[reportPrivateUsage]
        return container.part, body._element  # pyright: ignore[reportPrivateUsage]
    return (
        container.part,  # pyright: ignore[reportAttributeAccessIssue]
        container._element,  # pyright: ignore[reportAttributeAccessIssue,reportPrivateUsage]
    )


def place(
    new_element: BaseOxmlElement,
    dest_element: BaseOxmlElement,
    before: object = None,
    after: object = None,
) -> None:
    """Insert `new_element` into `dest_element`, relative to `before` or `after`.

    With neither, the copy is appended. A body ending in a `w:sectPr` appends before it,
    since the section properties must stay last.
    """
    if before is not None and after is not None:
        raise ValueError("pass at most one of `before` and `after`")

    if before is not None:
        _element_of(before).addprevious(new_element)
        return
    if after is not None:
        _element_of(after).addnext(new_element)
        return

    sectPr = dest_element.find(qn("w:sectPr"))
    if sectPr is not None:
        sectPr.addprevious(new_element)
    else:
        dest_element.append(new_element)


def _element_of(proxy: object) -> BaseOxmlElement:
    """The oxml element behind a |Paragraph| or |Table| proxy."""
    return proxy._element  # pyright: ignore[reportAttributeAccessIssue,reportPrivateUsage]
