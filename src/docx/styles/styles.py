"""Styles object, container for all objects in the styles part."""

from __future__ import annotations

import os
from typing import IO, TYPE_CHECKING, Dict, Iterable, List, Tuple, cast
from warnings import warn

from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.styles import CT_Styles
from docx.shared import ElementProxy
from docx.styles import BabelFish
from docx.styles.latent import LatentStyles
from docx.styles.style import BaseStyle, StyleFactory
from docx.text.font import Font
from docx.text.parfmt import ParagraphFormat

if TYPE_CHECKING:
    from docx.document import Document
    from docx.parts.document import DocumentPart
    from docx.styles.usage import StyleUsage


class Styles(ElementProxy):
    """Provides access to the styles defined in a document.

    Accessed using the :attr:`.Document.styles` property. Supports ``len()``, iteration,
    and dictionary-style access by style name.
    """

    def __init__(self, styles: CT_Styles, part: DocumentPart | None = None):
        super().__init__(styles)
        self._element = styles
        self._doc_part = part

    def __contains__(self, name):
        """Enables `in` operator on style name.

        Resolved exactly as `__getitem__` resolves it, minus the deprecated lookup by
        style id — a `__contains__` that disagrees with the subscript is worse than
        either answer on its own.
        """
        return self._element.get_by_name(BabelFish.ui2internal(name)) is not None

    def __getitem__(self, key: str):
        """Enables dictionary-style access by UI name.

        Lookup by style id is deprecated, triggers a warning, and will be removed in a
        near-future release.
        """
        style_elm = self._element.get_by_name(BabelFish.ui2internal(key))
        if style_elm is not None:
            return StyleFactory(style_elm, self._doc_part)

        style_elm = self._element.get_by_id(key)
        if style_elm is not None:
            msg = "style lookup by style_id is deprecated. Use style name as key instead."
            warn(msg, UserWarning, stacklevel=2)
            return StyleFactory(style_elm, self._doc_part)

        raise KeyError("no style with name '%s'" % key)

    def __iter__(self):
        return (StyleFactory(style, self._doc_part) for style in self._element.style_lst)

    def __len__(self):
        return len(self._element.style_lst)

    def add_style(self, name, style_type, builtin=False):
        """Return a newly added style object of `style_type` and identified by `name`.

        A builtin style can be defined by passing True for the optional `builtin`
        argument.
        """
        style_name = BabelFish.ui2internal(name)
        if style_name in self:
            raise ValueError("document already contains style '%s'" % name)
        style = self._element.add_style_of_type(style_name, style_type, builtin)
        return StyleFactory(style, self._doc_part)

    def copy_style_from(
        self,
        style: BaseStyle,
        *,
        name: str | None = None,
        on_collision: str = "skip",
        include_dependencies: bool = True,
        include_numbering: bool = True,
    ) -> BaseStyle:
        """Copy `style` from another document into this one and return the copy.

        Applying a style by name fails with `KeyError: no style with name 'X'` whenever
        the target document's style part lacks it, which is routine when content is
        assembled from several sources::

            template = Document("template.docx")
            report = Document()
            report.styles.copy_style_from(template.styles["Callout"])
            report.add_paragraph("note", style="Callout")

        **The dependency closure is the point.** A style is not a self-contained object:
        `w:basedOn` names the style it inherits from, `w:next` the style for the
        following paragraph, and `w:link` the paired character or paragraph style. A
        copied style whose `basedOn` target is missing renders as though it inherited
        from Normal, which is the failure people hit when they deep-copy one `w:style`
        element by hand. Those are followed and copied too unless `include_dependencies`
        is |False|.

        A list style references `numbering.xml`, so `include_numbering` also copies the
        `w:num` and `w:abstractNum` behind it and rewrites the reference to the new id.
        That needs the source document, which a style knows only when it came from
        :attr:`.Document.styles`; a style whose document is unknown has its numbering
        reference left alone, and it will not resolve here.

        `name` renames the style as it is copied; dependencies keep their own names.
        `on_collision` decides what happens when this document already has a style of
        that name:

        - ``"skip"`` (default) leaves the existing style alone and returns it.
        - ``"overwrite"`` replaces its definition.
        - ``"rename"`` copies it under a free name, "Callout 2" and so on.
        - ``"raise"`` raises |ValueError|.

        **Not carried over:** theme fonts. A style referencing `w:asciiTheme` resolves
        against *this* document's theme part, so a copied style can legitimately look
        different here. Latent-style visibility (`w:lsdException`) is copied when the
        source defines one for the style.
        """
        from docx.styles.copy import copy_style

        if on_collision not in ("skip", "overwrite", "rename", "raise"):
            raise ValueError(
                f"on_collision must be one of 'skip', 'overwrite', 'rename' or 'raise',"
                f" got {on_collision!r}"
            )
        return copy_style(
            self,
            style,
            name=name,
            on_collision=on_collision,
            include_dependencies=include_dependencies,
            include_numbering=include_numbering,
        )

    def default(self, style_type: WD_STYLE_TYPE):
        """Return the default style for `style_type` or |None| if no default is defined
        for that type (not common)."""
        style = self._element.default_for(style_type)
        if style is None:
            return None
        return StyleFactory(style, self._doc_part)

    def get_by_id(self, style_id: str | None, style_type: WD_STYLE_TYPE):
        """Return the style of `style_type` matching `style_id`.

        Returns the default for `style_type` if `style_id` is not found or is |None|, or
        if the style having `style_id` is not of `style_type`.
        """
        if style_id is None:
            return self.default(style_type)
        return self._get_by_id(style_id, style_type)

    def get_style_id(self, style_or_name, style_type):
        """Return the id of the style corresponding to `style_or_name`, or |None| if
        `style_or_name` is |None|.

        If `style_or_name` is not a style object, the style is looked up using
        `style_or_name` as a style name, raising |ValueError| if no style with that name
        is defined. Raises |ValueError| if the target style is not of `style_type`.
        """
        if style_or_name is None:
            return None
        elif isinstance(style_or_name, BaseStyle):
            return self._get_style_id_from_style(style_or_name, style_type)
        else:
            return self._get_style_id_from_name(style_or_name, style_type)

    @property
    def default_font(self) -> Font:
        """The document-wide default run formatting, `w:docDefaults/w:rPrDefault/w:rPr`.

        This is the bottom of the formatting inheritance chain: it applies to every run
        in the document that no style and no direct formatting overrides. For a document
        whose base font is set only here — which is most documents produced from a Word
        template — this is the only place `Font.name` is not |None|::

            document.styles.default_font.name = "Calibri"

        As with :attr:`.Styles.latent_styles`, the wrapping elements are created on first access
        so the returned |Font| always has somewhere to write.
        """
        docDefaults = self._element.get_or_add_docDefaults()
        return Font(docDefaults.get_or_add_rPrDefault())  # pyright: ignore[reportArgumentType]

    @property
    def default_paragraph_format(self) -> ParagraphFormat:
        """The document-wide default paragraph formatting, `w:docDefaults/w:pPrDefault`.

        The counterpart of :attr:`.default_font` for paragraph properties such as
        `space_after` and `line_spacing`.
        """
        docDefaults = self._element.get_or_add_docDefaults()
        return ParagraphFormat(docDefaults.get_or_add_pPrDefault())

    def import_from(
        self,
        source: str | os.PathLike[str] | IO[bytes] | Document,
        names: Iterable[str] | None = None,
        *,
        overwrite: bool = False,
        include_latent: bool = False,
    ) -> Dict[str, str]:
        """Copy styles from `source` into this document; return what was done to each.

        The bulk form of :meth:`copy_style_from`, which is what anyone generating
        documents from a corporate template ends up writing by hand::

            document.styles.import_from("house-template.dotx")
            document.styles.import_from(other_document, names=["Quote", "Caption"])
            document.styles.import_from(tmpl, overwrite=True)

        `source` may be a path, a file-like object or an open |Document|; a `.dotx` is
        the common case and opens without special handling. `names` of |None| means
        every style the source defines.

        Each style is copied with its `w:basedOn` / `w:next` / `w:link` closure and its
        numbering, as :meth:`copy_style_from` does.

        `overwrite` decides what happens to a name this document already has: |False|
        leaves the existing definition alone, |True| replaces it. The report says which
        happened for each name — ``"added"``, ``"replaced"`` or ``"skipped"`` — because
        "why is my heading still the wrong colour" is otherwise unanswerable.

        `include_latent` copies the source's whole `w:latentStyles` block. It is |False|
        by default because that changes which of Word's built-ins appear in *this*
        document's style gallery, which is rarely what was asked for.

        **Theme fonts are not resolved.** A style specifying `w:asciiTheme="minorHAnsi"`
        renders with this document's theme after import, which may not be what you saw
        in the source; :attr:`.Document.theme` is where to check.
        """
        from docx.styles.transfer import import_styles

        return import_styles(
            self, source, names, overwrite=overwrite, include_latent=include_latent
        )

    def extract(
        self,
        path_or_stream: str | os.PathLike[str] | IO[bytes],
        names: Iterable[str] | None = None,
        *,
        as_template: bool = False,
    ) -> List[str]:
        """Write `names` and their closure to a styles-only document; return what went.

        The other half of the round trip: pull the styles you like out of a document
        someone sent you, keep them as a template, and apply them to everything you
        generate::

            document.styles.extract("styles-only.docx", names=["Quote", "Caption"])
            document.styles.extract("house.dotx", as_template=True)

        The result is a valid, empty Word document carrying the named styles and
        everything they depend on, and nothing else — the 164 styles of the bundled
        template are pruned first, or the extract would be mostly them.

        `names` of |None| extracts every style this document defines.
        """
        from docx.styles.transfer import save_extract

        return save_extract(self, path_or_stream, names, as_template=as_template)

    def extract_xml(self, names: Iterable[str] | None = None) -> bytes:
        """The `styles.xml` bytes of the :meth:`extract`, without writing a package.

        For diffing two documents' styles, or putting them under version control.
        """
        from docx.styles.transfer import extract_styles_xml

        return extract_styles_xml(self, names)

    def usage(self, *, keep: Iterable[str] = (), seed_defaults: bool = True) -> StyleUsage:
        """A report of which styles this document defines and which it actually uses::

            >>> print(document.styles.usage())
            164 styles defined, 3 in use, 161 unused; 137 latent style exceptions

        "Used" is a reachability closure rather than a membership test. It starts from
        every style applied anywhere in the document — in the body, and in the headers,
        footers, footnotes, endnotes and comments, which are separate parts with their
        own references — and follows `w:basedOn`, `w:next`, `w:link` and the numbering
        and table-style references until it stops growing. A style used only as the
        `basedOn` of a used style *is* used.

        The `w:default="1"` styles are used by definition: they apply to content that
        names no style at all, so they have no direct references to count.

        `keep` names style ids to treat as used along with their own closure, for a
        caller who plans to apply a style nothing references yet.

        `seed_defaults` decides whether the `w:default="1"` styles count as used whether
        or not anything references them. The default of |True| is the truthful reading;
        |False| answers the narrower question of what is reachable by reference alone.

        Style *ids* are what the report holds, since ids are what the XML references;
        the names this collection is keyed on are the UI spelling of the same thing.
        """
        from docx.styles.usage import compute_usage

        return compute_usage(self._element, self._doc_part, keep, seed_defaults=seed_defaults)

    @property
    def unused(self) -> Tuple[BaseStyle, ...]:
        """The styles this document defines but does not use, in document order.

        The complement of :meth:`usage`. This is what :meth:`remove_unused` deletes.
        """
        unused_ids = set(self.usage().unused)
        return tuple(
            StyleFactory(style, self._doc_part)
            for style in self._element.style_lst
            if style.styleId in unused_ids
        )

    def remove_unused(
        self, *, keep: Iterable[str] = (), keep_defaults: bool = True
    ) -> Tuple[str, ...]:
        """Delete every style outside the reachability closure; return what was removed.

        Prunes a document down to the styles it actually uses::

            document.styles.remove_unused()
            document.styles.remove_unused(keep=["Quote", "Caption"])

        **This is destructive and the closure is the only thing standing between it and
        a broken document.** It deletes definitions, so a style the closure misses comes
        back as default formatting. The closure is the same one :meth:`usage` reports,
        deliberately — there is one implementation and one set of tests behind both.

        `keep` names styles to preserve along with their own dependencies, given as UI
        names or style ids. `keep_defaults` keeps the `w:default="1"` style of each type
        whatever the closure says, which is the safe default: those apply to content
        that names no style at all, so removing one silently changes how that content
        renders. Pass |False| to prune a default that nothing references.

        "Normal" is never removed whatever else is asked: Word repairs a document that
        lacks it, and the repair dialogue is worse than the bloat.

        Returns the ids removed, so the caller can report them. Latent styles are left
        alone; removing an `lsdException` changes whether a style appears in Word's
        gallery rather than how the document looks, which is a different risk — see
        :meth:`.LatentStyles.trim`.
        """
        keep_ids = {self._style_id_for(name) for name in keep}
        keep_ids.discard(None)
        usage = self.usage(keep=cast("set[str]", keep_ids), seed_defaults=keep_defaults)
        removable = set(usage.unused)

        removed: list[str] = []
        for style in list(self._element.style_lst):
            if style.styleId in removable:
                removed.append(style.styleId)
                style.delete()
        return tuple(removed)

    def _style_id_for(self, name_or_id: str) -> str | None:
        """The style id `name_or_id` denotes, or |None| when this document has no such style.

        Accepts either spelling, because a caller naming styles to keep thinks in UI
        names while the closure runs on ids.
        """
        style_elm = self._element.get_by_name(BabelFish.ui2internal(name_or_id))
        if style_elm is not None:
            return style_elm.styleId
        style_elm = self._element.get_by_id(name_or_id)
        return None if style_elm is None else style_elm.styleId

    @property
    def latent_styles(self):
        """A |LatentStyles| object providing access to the default behaviors for latent
        styles and the collection of |_LatentStyle| objects that define overrides of
        those defaults for a particular named latent style."""
        return LatentStyles(self._element.get_or_add_latentStyles())

    def _get_by_id(self, style_id: str | None, style_type: WD_STYLE_TYPE):
        """Return the style of `style_type` matching `style_id`.

        Returns the default for `style_type` if `style_id` is not found or if the style
        having `style_id` is not of `style_type`.
        """
        style = self._element.get_by_id(style_id) if style_id else None
        if style is None or style.type != style_type:
            return self.default(style_type)
        return StyleFactory(style, self._doc_part)

    def _get_style_id_from_name(self, style_name: str, style_type: WD_STYLE_TYPE) -> str | None:
        """Return the id of the style of `style_type` corresponding to `style_name`.

        Returns |None| if that style is the default style for `style_type`. Raises
        |ValueError| if the named style is not found in the document or does not match
        `style_type`.
        """
        return self._get_style_id_from_style(self[style_name], style_type)

    def _get_style_id_from_style(self, style: BaseStyle, style_type: WD_STYLE_TYPE) -> str | None:
        """Id of `style`, or |None| if it is the default style of `style_type`.

        Raises |ValueError| if style is not of `style_type`.
        """
        if style.type != style_type:
            raise ValueError("assigned style is type %s, need type %s" % (style.type, style_type))
        if style == self.default(style_type):
            return None
        return style.style_id
