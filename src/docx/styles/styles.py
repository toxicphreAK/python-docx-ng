"""Styles object, container for all objects in the styles part."""

from __future__ import annotations

from typing import TYPE_CHECKING
from warnings import warn

from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.styles import CT_Styles
from docx.shared import ElementProxy
from docx.styles import BabelFish
from docx.styles.latent import LatentStyles
from docx.styles.style import BaseStyle, StyleFactory

if TYPE_CHECKING:
    from docx.parts.document import DocumentPart


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
        """Enables `in` operator on style name."""
        internal_name = BabelFish.ui2internal(name)
        return any(style.name_val == internal_name for style in self._element.style_lst)

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
