"""Which styles a document actually uses.

The interesting part is getting "used" right. A naive scan of `w:pStyle` in
`word/document.xml` gets the wrong answer in several ways, and each of them is a real
document:

- **Every story part, not just the body.** Headers, footers, footnotes, endnotes and
  comments are separate parts with their own content and their own style references.
- **Indirect references.** A style can be reachable without ever being applied — as the
  `w:basedOn` of a used style, as its `w:next`, as its `w:link`, from a numbering
  level's `w:pStyle`, or from the `w:tblStylePr` conditional formatting inside a table
  style.
- **The default styles.** The style carrying `w:default="1"` applies to every paragraph
  with no `w:pStyle` at all. It is used by definition and has zero direct references.

So "used" is a **reachability closure**, not a membership test: seed from the direct
applications, then follow the reference edges until the set stops growing.

The closure runs on style *ids*, which is what the XML references;
:class:`docx.styles.styles.Styles` keys on *names*, which is what the API exposes, and
`BabelFish` translates the built-ins between the two spellings. Mixing the two is a
recurring source of bugs, so the translation happens only at the boundary.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Iterable, Iterator, NamedTuple, Set, Tuple

from docx.enum.style import WD_STYLE_TYPE
from docx.opc.constants import RELATIONSHIP_TYPE as RT

if TYPE_CHECKING:
    from docx.opc.part import XmlPart
    from docx.oxml.styles import CT_Style, CT_Styles
    from docx.parts.document import DocumentPart

#: Relationship types of the parts that hold styled content beyond the main document
#: part. Each is a story of its own with its own `w:pStyle` references.
_STORY_RELTYPES = (
    RT.HEADER,
    RT.FOOTER,
    RT.FOOTNOTES,
    RT.ENDNOTES,
    RT.COMMENTS,
)

#: The attributes that name a style id in content: `w:pStyle` and `w:rStyle` on a
#: paragraph or run, and `w:tblStyle` on a table.
_CONTENT_STYLE_XPATH = (
    "//w:pStyle/@w:val | //w:rStyle/@w:val | //w:tblStyle/@w:val"
    # -- a numbering level can apply a paragraph style, reached from `numbering.xml` --
    " | //w:lvl/w:pStyle/@w:val"
)

#: The child elements of a `w:style` that name another style.
_STYLE_REFERENCE_TAGS = ("w:basedOn", "w:next", "w:link", "w:styleLink", "w:numStyleLink")


class StyleUsage(NamedTuple):
    """A report of which styles a document defines and which of them it uses.

    Iterating yields the style ids in use. ``str()`` gives the one-paragraph summary
    that :func:`print` shows.
    """

    #: Style ids defined in the styles part, in document order.
    defined: Tuple[str, ...]
    #: Style ids in the reachability closure of what the document actually applies.
    used: Tuple[str, ...]
    #: How many times each style id is directly applied to content. A style reachable
    #: only indirectly has a count of zero.
    reference_counts: Dict[str, int]
    #: Names declared in `w:latentStyles` that are *not* defined. Latent styles are a
    #: behavior declaration for styles the document does not define, so they are neither
    #: used nor unused; they are reported separately.
    latent: Tuple[str, ...]

    @property
    def unused(self) -> Tuple[str, ...]:
        """Style ids defined but not reachable, in document order."""
        used = set(self.used)
        return tuple(style_id for style_id in self.defined if style_id not in used)

    def __iter__(self) -> Iterator[str]:  # pyright: ignore[reportIncompatibleMethodOverride]
        return iter(self.used)

    def __str__(self) -> str:
        return (
            "%d styles defined, %d in use, %d unused; %d latent style exceptions"
            % (len(self.defined), len(self.used), len(self.unused), len(self.latent))
        )


def _iter_style_parts(document_part: DocumentPart) -> Iterator[XmlPart]:
    """Generate every part whose XML can carry a style reference.

    The main document part, every header and footer, the footnotes, endnotes and
    comments parts, and `numbering.xml` — whose levels can apply a paragraph style.
    Reached through the relationship graph rather than by creating parts, so asking
    which styles a document uses does not add parts to it.
    """
    yield document_part
    seen = {id(document_part)}
    for rel in document_part.rels.values():
        if rel.is_external or rel.reltype not in _STORY_RELTYPES:
            continue
        part = rel.target_part
        if id(part) not in seen and hasattr(part, "element"):
            seen.add(id(part))
            yield part
    # -- numbering is not a story but its levels name paragraph styles --
    for rel in document_part.rels.values():
        if not rel.is_external and rel.reltype == RT.NUMBERING:
            part = rel.target_part
            if id(part) not in seen and hasattr(part, "element"):
                seen.add(id(part))
                yield part


def _direct_reference_counts(document_part: DocumentPart) -> Dict[str, int]:
    """How many times each style id is applied to content, across every story part."""
    counts: Dict[str, int] = {}
    for part in _iter_style_parts(document_part):
        for style_id in part.element.xpath(_CONTENT_STYLE_XPATH):
            counts[style_id] = counts.get(style_id, 0) + 1
    return counts


def _style_edges(style: CT_Style) -> Iterator[str]:
    """Generate the style ids `style` references.

    `w:basedOn`, `w:next`, `w:link`, `w:styleLink` and `w:numStyleLink`, plus any
    `w:pStyle` or `w:rStyle` inside the style's own formatting — a table style's
    `w:tblStylePr` conditional formatting can name one.
    """
    for tag in _STYLE_REFERENCE_TAGS:
        for val in style.xpath("./%s/@w:val" % tag):
            yield val
    for val in style.xpath(".//w:pStyle/@w:val | .//w:rStyle/@w:val"):
        yield val


def _default_style_ids(styles_elm: CT_Styles) -> Set[str]:
    """The ids of the `w:default="1"` styles, which apply whether referenced or not."""
    ids: Set[str] = set()
    for style_type in WD_STYLE_TYPE:
        default = styles_elm.default_for(style_type)
        if default is not None and default.styleId:
            ids.add(default.styleId)
    return ids


def compute_usage(
    styles_elm: CT_Styles,
    document_part: DocumentPart | None,
    keep: Iterable[str] = (),
    *,
    seed_defaults: bool = True,
) -> StyleUsage:
    """The style-usage report for `styles_elm` as used by `document_part`.

    `keep` names extra style ids to treat as used along with their own closure — for a
    caller who plans to apply a style that nothing references yet.

    `seed_defaults` puts the `w:default="1"` styles into the closure whether or not
    anything references them, which is the truthful reading: they apply to content that
    names no style at all. Passing |False| answers the narrower question of what is
    reachable by reference alone, which is what a caller deliberately pruning the
    defaults needs.

    With no `document_part` there is no content to scan, so only the defaults and `keep`
    seed the closure. That is the honest answer for a styles part reached on its own
    rather than a claim that nothing is used.
    """
    by_id = {s.styleId: s for s in styles_elm.style_lst if s.styleId}
    defined = tuple(s.styleId for s in styles_elm.style_lst if s.styleId)

    counts = _direct_reference_counts(document_part) if document_part is not None else {}

    # -- seed: everything directly applied, every default style, and `keep` --
    pending = set(counts) | set(keep)
    if seed_defaults:
        pending |= _default_style_ids(styles_elm)
    # -- Word's "Normal" is repaired into a document that lacks it, and the repair
    # -- dialogue is worse than the bloat, so it is never dropped --
    if "Normal" in by_id:
        pending.add("Normal")

    # -- reachability closure. A dangling edge — a `w:basedOn` naming a style that is
    # -- not defined — is a dead end rather than an error; it is legal and common. The
    # -- visited set is what makes cycles terminate, and `w:next` pointing at its own
    # -- style is the normal case rather than a pathology. --
    used: Set[str] = set()
    while pending:
        style_id = pending.pop()
        if style_id in used or style_id not in by_id:
            continue
        used.add(style_id)
        pending.update(_style_edges(by_id[style_id]))

    latent = tuple(
        name
        for name in styles_elm.xpath("./w:latentStyles/w:lsdException/@w:name")
        if name not in by_id
    )

    return StyleUsage(
        defined=defined,
        used=tuple(style_id for style_id in defined if style_id in used),
        reference_counts=counts,
        latent=latent,
    )


def latent_exception_names(styles_elm: CT_Styles) -> Tuple[str, ...]:
    """Every `w:lsdException/@w:name` in the latent-styles block, defined or not."""
    return tuple(styles_elm.xpath("./w:latentStyles/w:lsdException/@w:name"))


def is_default_style(styles_elm: CT_Styles, style: CT_Style) -> bool:
    """|True| when `style` is the `w:default="1"` style of its type."""
    return bool(style.styleId) and style.styleId in _default_style_ids(styles_elm)
