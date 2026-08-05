"""Bulk style import and extract, built on :func:`docx.styles.copy.copy_style`.

`copy_style_from()` moves one style and resolves its `w:basedOn` / `w:next` / `w:link`
closure and its numbering. That is the hard part and it is done. What people write by
hand on top of it is the two bulk operations: pull a whole house template's styles into
a generated document, and pull a set of styles out of a document into a template of
their own.

The naive loop over `copy_style_from()` is O(n) full closure resolutions with repeated
work, and re-imports shared numbering once per style that uses it. Both operations here
resolve the shared work once.
"""

from __future__ import annotations

import os
from typing import IO, TYPE_CHECKING, Dict, Iterable, List, Tuple

from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.styles import BabelFish

if TYPE_CHECKING:
    from docx.document import Document
    from docx.styles.style import BaseStyle
    from docx.styles.styles import Styles

#: What :meth:`.Styles.import_from` did with each style, keyed by UI name.
ImportReport = Dict[str, str]


def _as_document(source: str | os.PathLike[str] | IO[bytes] | Document) -> Document:
    """`source` as an open |Document|, opening it when it is a path or a stream.

    A `.dotx` is the common case for a house template and opens without special
    handling; a template holds the same main part as a document.
    """
    from docx.api import Document as open_document

    if hasattr(source, "styles"):
        return source  # pyright: ignore[reportReturnType]
    return open_document(source)  # pyright: ignore[reportArgumentType]


def import_styles(
    styles: Styles,
    source: str | os.PathLike[str] | IO[bytes] | Document,
    names: Iterable[str] | None = None,
    *,
    overwrite: bool = False,
    include_latent: bool = False,
) -> ImportReport:
    """Copy styles from `source` into `styles`; see :meth:`.Styles.import_from`."""
    source_document = _as_document(source)
    source_styles = source_document.styles

    wanted = (
        list(source_styles) if names is None else [source_styles[name] for name in names]
    )

    report: ImportReport = {}
    for style in wanted:
        name = style.name
        if name is None:
            continue
        present = name in styles
        if present and not overwrite:
            # -- nothing to do: the destination already defines this name, so a later
            # -- style based on it already resolves --
            report[name] = "skipped"
            continue
        styles.copy_style_from(style, on_collision="overwrite" if overwrite else "skip")
        report[name] = "replaced" if present else "added"

    if include_latent:
        _copy_all_latent_exceptions(source_styles, styles)

    return report


def _copy_all_latent_exceptions(source_styles: Styles, dest_styles: Styles) -> None:
    """Copy the whole `w:latentStyles` exception list from source to destination.

    Off by default in :meth:`.Styles.import_from`: this changes which of Word's built-in
    styles appear in the destination's gallery, which is rarely what "import these
    styles" was asked to mean.
    """
    import copy as copymod

    source_latent = source_styles._element.latentStyles  # pyright: ignore[reportPrivateUsage]
    if source_latent is None:
        return
    dest_latent = dest_styles._element.get_or_add_latentStyles()  # pyright: ignore[reportPrivateUsage]
    for lsdException in source_latent.lsdException_lst:
        if dest_latent.get_by_name(lsdException.name) is None:
            dest_latent.append(copymod.deepcopy(lsdException))


def _closure_names(styles: Styles, names: Iterable[str]) -> List[str]:
    """`names` plus the names of every style they transitively depend on.

    Resolved on ids, since that is what the XML references, and translated back to names
    at the boundary.
    """
    from docx.styles.copy import _dependency_closure  # pyright: ignore[reportPrivateUsage]

    styles_elm = styles._element  # pyright: ignore[reportPrivateUsage]
    ordered: List[str] = []
    seen: set[str] = set()
    for name in names:
        style_elm = styles_elm.get_by_name(BabelFish.ui2internal(name))
        if style_elm is None:
            raise KeyError("no style with name '%s'" % name)
        for dependency in _dependency_closure(style_elm, styles_elm):
            style_id = dependency.styleId
            if style_id is None or style_id in seen:
                continue
            seen.add(style_id)
            ordered.append(dependency.name_val or style_id)
    return ordered


def extract_styles(
    styles: Styles, names: Iterable[str] | None = None
) -> Tuple[Document, List[str]]:
    """A new empty document carrying `names` and their closure; see :meth:`.Styles.extract`.

    Returns the document and the UI names of the styles it received, in the order they
    were added.
    """
    from docx.api import Document as new_document

    source_names = (
        [s.name for s in styles if s.name is not None]
        if names is None
        else _closure_names(styles, names)
    )

    destination = new_document()
    # -- the bundled template defines 164 styles of its own; a styles-only document that
    # -- carried those as well would not be the extract that was asked for --
    destination.styles.remove_unused()

    added: List[str] = []
    for name in source_names:
        style: BaseStyle = styles[name]
        destination.styles.copy_style_from(style, on_collision="overwrite")
        added.append(name)
    return destination, added


def extract_styles_xml(styles: Styles, names: Iterable[str] | None = None) -> bytes:
    """The `styles.xml` bytes of the extract; see :meth:`.Styles.extract_xml`."""
    from docx.opc.oxml import serialize_part_xml

    destination, _ = extract_styles(styles, names)
    styles_part = destination.part.part_related_by(RT.STYLES)
    return serialize_part_xml(styles_part.element)  # pyright: ignore[reportAttributeAccessIssue]


def save_extract(
    styles: Styles,
    path_or_stream: str | os.PathLike[str] | IO[bytes],
    names: Iterable[str] | None = None,
    *,
    as_template: bool = False,
) -> List[str]:
    """Write the extract to `path_or_stream`; see :meth:`.Styles.extract`."""
    destination, added = extract_styles(styles, names)
    destination.save(path_or_stream, as_template=as_template)
    return added
