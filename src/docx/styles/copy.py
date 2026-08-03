"""Copying a style definition from one document into another.

The public entry point is :meth:`.Styles.copy_style_from`; this module holds the work.

The hard part is not moving the `w:style` element — a deep copy does that, and it is
what people already do by hand. The hard part is the closure around it. A style names
other styles (`w:basedOn`, `w:next`, `w:link`) and may name a numbering definition in a
different part altogether, and every one of those references is an id that means
something else, or nothing, in the destination document. A copy that carries the element
but not the closure produces a style that renders wrongly, or a document Word rejects.

So: resolve the graph, copy what is reachable, and rewrite every id that changed.
"""

from __future__ import annotations

import copy as copymod
from typing import TYPE_CHECKING, Dict, List, Set

from docx.oxml.styles import CT_Style
from docx.styles.style import BaseStyle, StyleFactory

if TYPE_CHECKING:
    from docx.oxml.numbering import CT_Numbering
    from docx.parts.document import DocumentPart
    from docx.styles.styles import Styles

# -- a rename loop that gets this far is not going to terminate usefully --
_MAX_RENAME_ATTEMPTS = 1000


def copy_style(
    styles: Styles,
    style: BaseStyle,
    *,
    name: str | None = None,
    on_collision: str = "skip",
    include_dependencies: bool = True,
    include_numbering: bool = True,
) -> BaseStyle:
    """Copy `style` into `styles`; see :meth:`.Styles.copy_style_from`."""
    source_styles = style._element.getparent()  # pyright: ignore[reportPrivateUsage]
    if source_styles is None:
        raise ValueError("the style being copied is not attached to a styles part")

    dest = styles._element  # pyright: ignore[reportPrivateUsage]
    if source_styles is dest:
        raise ValueError("the style being copied is already in this document")

    to_copy = (
        _dependency_closure(style._element, source_styles)  # pyright: ignore[reportPrivateUsage]
        if include_dependencies
        else [style._element]  # pyright: ignore[reportPrivateUsage]
    )

    # -- style ids that changed on the way in, so references can be rewritten --
    id_map: Dict[str, str] = {}
    copied: Dict[str, CT_Style] = {}
    result: CT_Style | None = None

    for source_style in to_copy:
        is_target = source_style is style._element  # pyright: ignore[reportPrivateUsage]
        new_name = name if (is_target and name is not None) else source_style.name_val

        existing = _find_existing(dest, new_name)
        if existing is not None:
            # -- `on_collision` is about the style asked for. A dependency that already
            # -- exists is reused whatever the policy says: renaming or overwriting
            # -- "Normal" because a copied style happens to be based on it would be a
            # -- surprising thing to do to the destination document. --
            policy = on_collision if is_target else "skip"
            if policy == "raise":
                raise ValueError(f"document already contains style '{new_name}'")
            if policy == "skip":
                if is_target:
                    result = existing
                if source_style.styleId and existing.styleId:
                    id_map[source_style.styleId] = existing.styleId
                continue
            if policy == "rename":
                new_name = _free_name(dest, new_name or "Style")
            else:  # -- "overwrite" --
                dest.remove(existing)

        new_style = copymod.deepcopy(source_style)
        new_style.name_val = new_name
        new_style.styleId = _free_style_id(dest, new_style.styleId or "Style")
        if source_style.styleId:
            id_map[source_style.styleId] = new_style.styleId
        dest.append(new_style)
        copied[new_style.styleId] = new_style
        if is_target:
            result = new_style

    _rewrite_style_references(copied.values(), id_map)
    _copy_latent_style_exceptions(source_styles, dest, to_copy)

    if include_numbering:
        _copy_numbering(copied.values(), style.document_part, styles._doc_part)  # pyright: ignore[reportPrivateUsage]

    if result is None:  # pragma: no cover -- every branch above assigns it
        raise ValueError("the style could not be copied")
    return StyleFactory(result, styles._doc_part)  # pyright: ignore[reportPrivateUsage]


def _dependency_closure(style: CT_Style, source_styles) -> List[CT_Style]:
    """`style` and every style it transitively depends on, dependencies first.

    Dependencies first so that a `w:basedOn` target already exists by the time the style
    referring to it is added, which keeps the result readable and keeps a partial failure
    from leaving a dangling reference.
    """
    ordered: List[CT_Style] = []
    seen: Set[str] = set()

    def visit(current: CT_Style) -> None:
        style_id = current.styleId
        if style_id is not None:
            if style_id in seen:
                return
            seen.add(style_id)

        for referenced_id in (current.basedOn_val, current.next_val, current.link_val):
            if referenced_id is None:
                continue
            referenced = source_styles.get_by_id(referenced_id)
            # -- a reference to a style the source does not define is already broken
            # -- there; carrying the break over is better than inventing a style --
            if referenced is not None and referenced is not current:
                visit(referenced)

        ordered.append(current)

    visit(style)
    return ordered


def _rewrite_style_references(new_styles, id_map: Dict[str, str]) -> None:
    """Point each copied style's `w:basedOn`, `w:next` and `w:link` at the new ids."""
    for new_style in new_styles:
        for getter, setter in (
            ("basedOn_val", "basedOn_val"),
            ("next_val", "next_val"),
            ("link_val", "link_val"),
        ):
            old = getattr(new_style, getter)
            if old is not None and old in id_map:
                setattr(new_style, setter, id_map[old])


def _copy_latent_style_exceptions(source_styles, dest, copied: List[CT_Style]) -> None:
    """Copy any `w:lsdException` the source defines for each copied style.

    A latent-style exception controls whether the style shows in Word's style gallery
    and where it sorts. Leaving it behind makes a copied style invisible in the UI even
    though it applies correctly, which reads as the copy having failed.
    """
    source_latent = source_styles.latentStyles
    if source_latent is None:
        return

    names = [s.name_val for s in copied if s.name_val]
    exceptions = [lsd for lsd in (source_latent.get_by_name(n) for n in names) if lsd is not None]
    if not exceptions:
        return

    dest_latent = dest.get_or_add_latentStyles()
    for lsdException in exceptions:
        if dest_latent.get_by_name(lsdException.name) is None:
            dest_latent.append(copymod.deepcopy(lsdException))


def _copy_numbering(
    new_styles,
    source_part: DocumentPart | None,
    dest_part: DocumentPart | None,
) -> None:
    """Copy the numbering definition behind each copied style and repoint it.

    Without this a list style keeps a `w:numId` that means something else here, so it
    numbers according to whatever list happens to hold that id — a silent wrong answer
    rather than a visible failure. Both documents have to be known to do it; when either
    is not, the reference is left as it is and will simply not resolve.
    """
    numbered = [s for s in new_styles if s.numId_val is not None]
    if not numbered or source_part is None or dest_part is None:
        return
    if not source_part.has_numbering_part:
        return

    source_numbering = source_part.numbering_part.element
    dest_numbering = dest_part.numbering_part.element

    # -- one abstract definition may back several of the copied styles; copy it once --
    abstract_id_map: Dict[int, int] = {}

    for new_style in numbered:
        num_id = new_style.numId_val
        assert num_id is not None
        try:
            source_num = source_numbering.num_having_numId(num_id)
        except KeyError:
            # -- the source's own reference is already dangling --
            continue

        source_abstract_id = source_num.abstractNumId.val
        if source_abstract_id is None:
            continue

        if source_abstract_id not in abstract_id_map:
            source_abstract = source_numbering.abstractNum_having_abstractNumId(source_abstract_id)
            if source_abstract is None:
                continue
            new_abstract = copymod.deepcopy(source_abstract)
            new_abstract.abstractNumId = _free_abstract_num_id(dest_numbering)
            # -- a `w:numStyleLink` points at a style, not an id, so it survives the
            # -- copy only if that style came too; leave it and let it dangle rather
            # -- than silently flattening the definition --
            #
            # -- inserted rather than appended: `CT_Numbering` is an xsd:sequence and
            # -- every `w:abstractNum` must precede every `w:num`, or Word refuses to
            # -- open the document --
            dest_numbering._insert_abstractNum(  # pyright: ignore[reportPrivateUsage]
                new_abstract
            )
            abstract_id_map[source_abstract_id] = new_abstract.abstractNumId

        new_num = dest_numbering.add_num(abstract_id_map[source_abstract_id])
        for lvlOverride in source_num.lvlOverride_lst:
            new_num.append(copymod.deepcopy(lvlOverride))
        new_style.numId_val = new_num.numId


def _find_existing(dest, name: str | None) -> CT_Style | None:
    """The `w:style` in `dest` named `name`, or |None|."""
    return None if name is None else dest.get_by_name(name)


def _free_name(dest, name: str) -> str:
    """`name` with a numeric suffix that no style in `dest` already uses."""
    for suffix in range(2, _MAX_RENAME_ATTEMPTS + 2):
        candidate = f"{name} {suffix}"
        if dest.get_by_name(candidate) is None:
            return candidate
    raise ValueError(f"could not find a free name based on '{name}'")


def _free_style_id(dest, style_id: str) -> str:
    """`style_id` if `dest` has no style with it, else that id with a numeric suffix."""
    if dest.get_by_id(style_id) is None:
        return style_id
    for suffix in range(2, _MAX_RENAME_ATTEMPTS + 2):
        candidate = f"{style_id}{suffix}"
        if dest.get_by_id(candidate) is None:
            return candidate
    raise ValueError(f"could not find a free style id based on '{style_id}'")


def _free_abstract_num_id(numbering: CT_Numbering) -> int:
    """The first `abstractNumId` no `w:abstractNum` in `numbering` uses."""
    used = {a.abstractNumId for a in numbering.abstractNum_lst}
    candidate = 0
    while candidate in used:
        candidate += 1
    return candidate
