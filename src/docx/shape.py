"""Objects related to shapes.

A shape is a visual object that appears on the drawing layer of a document.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from docx.enum.shape import (
    WD_ANCHOR_ALIGN_H,
    WD_ANCHOR_ALIGN_V,
    WD_ANCHOR_RELATIVE_FROM_H,
    WD_ANCHOR_RELATIVE_FROM_V,
    WD_INLINE_SHAPE,
    WD_WRAP_TYPE,
)
from docx.oxml.ns import nsmap
from docx.shared import Emu, Parented

if TYPE_CHECKING:
    import docx.types as t
    from docx.image.image import Image
    from docx.oxml.document import CT_Body
    from docx.oxml.shape import CT_Anchor, CT_Blip, CT_GraphicalObjectData, CT_Inline
    from docx.parts.story import StoryPart
    from docx.shared import Length


def _picture_blip(graphicData: CT_GraphicalObjectData) -> CT_Blip | None:
    """The `a:blip` of a picture shape, or |None| when the shape is not a picture.

    A chart, a SmartArt diagram and an embedded object all live in the same
    `a:graphicData` wrapper as a picture and are told apart by its `@uri`. Only the
    picture case has a `pic:pic` child to reach a blip through.
    """
    if graphicData.uri != nsmap["pic"]:
        return None
    return graphicData.pic.blipFill.blip


def _image_from_rId(part: StoryPart, rId: str | None) -> Image | None:
    """The |Image| of the image part `rId` names, or |None| when there is none.

    |None| rather than |KeyError| for a relationship the part does not resolve, and for
    one resolving to something that is not an image part. Both occur in real documents —
    a relationship whose target was missing from the package is dropped on load — and
    neither is the caller's fault, so `.image` reports "nothing to give" as it does for
    a chart or a linked picture.
    """
    if rId is None or rId not in part.rels:
        return None
    return getattr(part.rels[rId].target_part, "image", None)


class _PictureShape:
    """The picture-extraction half of an inline or floating shape.

    Both `wp:inline` and `wp:anchor` wrap the same `a:graphic` subtree, so finding the
    image behind them is one implementation rather than two.
    """

    _parent: t.ProvidesStoryPart | None

    @property
    def image(self) -> Image | None:
        """The |Image| this shape displays, or |None| when there is no image to return.

        This is the counterpart of :meth:`.Run.add_picture` — extracting the pictures
        from a document without walking the relationships by hand::

            for shape in document.inline_shapes:
                if shape.image is not None:
                    Path(f"{shape.image.sha1}.{shape.image.ext}").write_bytes(
                        shape.image.blob
                    )

        |None| in three cases, each of which is a real document rather than an error:

        - the shape is not a picture at all — a chart, a SmartArt diagram or an
          embedded object;
        - the picture is *linked* rather than embedded, so the bytes are not in the
          package and there is nothing to hand back;
        - the shape was constructed without a parent, so there is no part to resolve
          the relationship against.

        For an SVG picture this returns the raster fallback, which is what every
        consumer can decode; :attr:`svg_image` returns the vector source.

        Several shapes can share one image part, so the |Image| returned for two shapes
        may be the same object.
        """
        blip = self._blip
        return None if blip is None else _image_from_rId(self._story_part, blip.embed)

    @property
    def svg_image(self) -> Image | None:
        """The SVG source of this picture, or |None| when it has none.

        Word records an SVG picture as an `asvg:svgBlip` extension *alongside* a raster
        rendering of it, rather than in place of one. :attr:`image` returns the raster
        fallback; this returns the vector original.
        """
        blip = self._blip
        if blip is None:
            return None
        svgBlip = blip.svgBlip
        return None if svgBlip is None else _image_from_rId(self._story_part, svgBlip.embed)

    @property
    def _blip(self) -> CT_Blip | None:
        """The `a:blip` of this shape, or |None| when it is not a picture."""
        raise NotImplementedError  # pragma: no cover

    @property
    def _story_part(self) -> StoryPart:
        """The story part this shape belongs to.

        Raises |ValueError| when the shape was constructed without a parent, which no
        longer happens for shapes reached through the public API.
        """
        if self._parent is None:
            raise ValueError(
                "shape has no parent part; reach it through Document.inline_shapes,"
                " Document.floating_shapes or Run.add_picture()"
            )
        return self._parent.part


class InlineShapes(Parented):
    """Sequence of |InlineShape| instances, supporting len(), iteration, and indexed access."""

    def __init__(self, body_elm: CT_Body, parent: StoryPart):
        super(InlineShapes, self).__init__(parent)
        self._body = body_elm

    def __getitem__(self, idx: int):
        """Provide indexed access, e.g. 'inline_shapes[idx]'."""
        try:
            inline = self._inline_lst[idx]
        except IndexError:
            msg = "inline shape index [%d] out of range" % idx
            raise IndexError(msg)

        return InlineShape(inline, self)

    def __iter__(self):
        return (InlineShape(inline, self) for inline in self._inline_lst)

    def __len__(self):
        return len(self._inline_lst)

    @property
    def _inline_lst(self):
        body = self._body
        xpath = "//w:p/w:r/w:drawing/wp:inline"
        return body.xpath(xpath)


class FloatingShapes(Parented):
    """Sequence of |FloatingShape| instances, supporting len(), iteration and indexing.

    A floating shape is anchored rather than inline: it is positioned against the page,
    the margin, the column or the paragraph, and text wraps around it. These are a
    distinct collection from :class:`InlineShapes` rather than part of it, because
    almost nothing that is true of an inline shape's position is true of a floating
    one's, and silently mixing the two is how code that walks `inline_shapes` starts
    reporting nonsense positions.
    """

    def __init__(self, body_elm: CT_Body, parent: StoryPart):
        super().__init__(parent)
        self._body = body_elm

    def __getitem__(self, idx: int) -> FloatingShape:
        try:
            anchor = self._anchor_lst[idx]
        except IndexError:
            raise IndexError("floating shape index [%d] out of range" % idx) from None
        return FloatingShape(anchor, self)

    def __iter__(self):
        return (FloatingShape(anchor, self) for anchor in self._anchor_lst)

    def __len__(self) -> int:
        return len(self._anchor_lst)

    @property
    def _anchor_lst(self):
        return self._body.xpath("//w:p/w:r/w:drawing/wp:anchor")


class FloatingShape(_PictureShape):
    """Proxy for a `<wp:anchor>` element, a shape that text flows around.

    Reached through :attr:`.Document.floating_shapes` or returned by
    :meth:`.Run.add_float_picture`.
    """

    def __init__(self, anchor: CT_Anchor, parent: t.ProvidesStoryPart | None = None):
        self._anchor = anchor
        self._parent = parent

    @property
    def _blip(self) -> CT_Blip | None:
        return _picture_blip(self._anchor.graphic.graphicData)

    @property
    def allow_overlap(self) -> bool:
        """Whether this shape may overlap another floating shape. Read/write."""
        return self._anchor.allowOverlap

    @allow_overlap.setter
    def allow_overlap(self, value: bool):
        self._anchor.allowOverlap = bool(value)

    @property
    def behind_text(self) -> bool:
        """Whether this shape is drawn behind the document text rather than over it.

        Read/write. This is what "put the watermark behind the text" means; it takes
        effect only with :attr:`wrap_type` of `WD_WRAP_TYPE.NONE`, since any other wrap
        setting keeps text out of the shape's way in the first place.
        """
        return self._anchor.behindDoc

    @behind_text.setter
    def behind_text(self, value: bool):
        self._anchor.behindDoc = bool(value)

    @property
    def description(self) -> str | None:
        """The alternative text of this shape, |None| if not set. Read/write."""
        return self._anchor.docPr.descr

    @description.setter
    def description(self, value: str | None):
        self._anchor.docPr.descr = value

    @property
    def height(self) -> Length:
        """The display height of this shape as an |Emu| instance. Read/write."""
        return self._anchor.extent.cy

    @height.setter
    def height(self, cy: Length):
        self._anchor.extent.cy = cy
        self._anchor.graphic.graphicData.pic.spPr.cy = cy

    @property
    def horizontal_align(self) -> WD_ANCHOR_ALIGN_H | None:
        """Named horizontal alignment of this shape, |None| when an offset is used.

        Read/write. Assigning an alignment replaces any :attr:`left` offset, and vice
        versa: the schema allows only one of the two, and Word ignores a shape that has
        both. Assigning |None| leaves the shape with neither, which Word treats as an
        offset of zero.
        """
        return self._anchor.positionH.align

    @horizontal_align.setter
    def horizontal_align(self, value: WD_ANCHOR_ALIGN_H | None):
        self._anchor.positionH.align = value

    @property
    def left(self) -> Length | None:
        """Horizontal offset from :attr:`relative_from_h`, |None| when aligned instead.

        Read/write. See :attr:`horizontal_align` for how the two interact.
        """
        return self._anchor.positionH.offset

    @left.setter
    def left(self, value: Length | int | None):
        self._anchor.positionH.offset = value

    @property
    def relative_from_h(self) -> WD_ANCHOR_RELATIVE_FROM_H:
        """What :attr:`left` and :attr:`horizontal_align` are measured from. Read/write."""
        return self._anchor.positionH.relativeFrom

    @relative_from_h.setter
    def relative_from_h(self, value: WD_ANCHOR_RELATIVE_FROM_H):
        self._anchor.positionH.relativeFrom = value

    @property
    def relative_from_v(self) -> WD_ANCHOR_RELATIVE_FROM_V:
        """What :attr:`top` and :attr:`vertical_align` are measured from. Read/write."""
        return self._anchor.positionV.relativeFrom

    @relative_from_v.setter
    def relative_from_v(self, value: WD_ANCHOR_RELATIVE_FROM_V):
        self._anchor.positionV.relativeFrom = value

    @property
    def title(self) -> str | None:
        """The title of this shape, |None| if not set. Read/write."""
        return self._anchor.docPr.title

    @title.setter
    def title(self, value: str | None):
        self._anchor.docPr.title = value

    @property
    def top(self) -> Length | None:
        """Vertical offset from :attr:`relative_from_v`, |None| when aligned instead.

        Read/write.
        """
        return self._anchor.positionV.offset

    @top.setter
    def top(self, value: Length | int | None):
        self._anchor.positionV.offset = value

    @property
    def vertical_align(self) -> WD_ANCHOR_ALIGN_V | None:
        """Named vertical alignment of this shape, |None| when an offset is used.

        Read/write. See :attr:`horizontal_align`.
        """
        return self._anchor.positionV.align

    @vertical_align.setter
    def vertical_align(self, value: WD_ANCHOR_ALIGN_V | None):
        self._anchor.positionV.align = value

    @property
    def width(self) -> Length:
        """The display width of this shape as an |Emu| instance. Read/write."""
        return self._anchor.extent.cx

    @width.setter
    def width(self, cx: Length):
        self._anchor.extent.cx = cx
        self._anchor.graphic.graphicData.pic.spPr.cx = cx

    @property
    def wrap_distance(self) -> tuple[Length, Length, Length, Length]:
        """Space held clear of this shape as `(top, right, bottom, left)`. Read-only.

        Set the individual distances with :meth:`set_wrap_distance`.
        """
        anchor = self._anchor
        return (
            Emu(anchor.distT or 0),
            Emu(anchor.distR or 0),
            Emu(anchor.distB or 0),
            Emu(anchor.distL or 0),
        )

    def set_wrap_distance(
        self,
        top: Length | int | None = None,
        right: Length | int | None = None,
        bottom: Length | int | None = None,
        left: Length | int | None = None,
    ) -> None:
        """Set the space held clear of this shape when text wraps around it.

        Each argument left as |None| is unchanged. Word's own default is no clearance
        above and below and 0.13cm to each side, which is what a new floating picture
        gets here.
        """
        anchor = self._anchor
        if top is not None:
            anchor.distT = int(top)
        if right is not None:
            anchor.distR = int(right)
        if bottom is not None:
            anchor.distB = int(bottom)
        if left is not None:
            anchor.distL = int(left)

    @property
    def wrap_type(self) -> WD_WRAP_TYPE:
        """Member of :ref:`WdWrapType` describing how text wraps around this shape.

        Read/write.
        """
        return self._anchor.wrap_type

    @wrap_type.setter
    def wrap_type(self, value: WD_WRAP_TYPE):
        self._anchor.wrap_type = value

    @property
    def z_order(self) -> int:
        """Position of this shape in the stack of floating shapes. Read/write.

        A higher value is drawn on top of a lower one. Independent of
        :attr:`behind_text`, which decides whether the whole floating layer this shape
        is in sits in front of the text or behind it.
        """
        return self._anchor.relativeHeight

    @z_order.setter
    def z_order(self, value: int):
        self._anchor.relativeHeight = int(value)


class InlineShape(_PictureShape):
    """Proxy for an ``<wp:inline>`` element, representing the container for an inline
    graphical object."""

    def __init__(self, inline: CT_Inline, parent: t.ProvidesStoryPart | None = None):
        super(InlineShape, self).__init__()
        self._inline = inline
        self._parent = parent

    @property
    def _blip(self) -> CT_Blip | None:
        return _picture_blip(self._inline.graphic.graphicData)

    @property
    def description(self) -> str | None:
        """Read/write.

        The alternative text of this shape, |None| if not set.

        This is what a screen reader announces in place of the picture, and what an
        automated accessibility check looks for. Word's "Alt Text" pane writes this
        field. Assigning |None| removes it.
        """
        return self._inline.docPr.descr

    @description.setter
    def description(self, value: str | None):
        self._inline.docPr.descr = value

    @property
    def height(self) -> Length:
        """Read/write.

        The display height of this inline shape as an |Emu| instance.
        """
        return self._inline.extent.cy

    @height.setter
    def height(self, cy: Length):
        self._inline.extent.cy = cy
        self._inline.graphic.graphicData.pic.spPr.cy = cy

    @property
    def type(self):
        """The type of this inline shape as a member of
        ``docx.enum.shape.WD_INLINE_SHAPE``, e.g. ``LINKED_PICTURE``.

        Read-only.
        """
        graphicData = self._inline.graphic.graphicData
        uri = graphicData.uri
        if uri == nsmap["pic"]:
            blip = graphicData.pic.blipFill.blip
            if blip.link is not None:
                return WD_INLINE_SHAPE.LINKED_PICTURE
            return WD_INLINE_SHAPE.PICTURE
        if uri == nsmap["c"]:
            return WD_INLINE_SHAPE.CHART
        if uri == nsmap["dgm"]:
            return WD_INLINE_SHAPE.SMART_ART
        return WD_INLINE_SHAPE.NOT_IMPLEMENTED

    @property
    def title(self) -> str | None:
        """Read/write.

        The title of this shape, |None| if not set.

        Word presents this separately from the alternative text and screen readers do
        not generally announce it; `.description` is the one accessibility depends on.
        Assigning |None| removes it.
        """
        return self._inline.docPr.title

    @title.setter
    def title(self, value: str | None):
        self._inline.docPr.title = value

    @property
    def width(self):
        """Read/write.

        The display width of this inline shape as an |Emu| instance.
        """
        return self._inline.extent.cx

    @width.setter
    def width(self, cx: Length):
        self._inline.extent.cx = cx
        self._inline.graphic.graphicData.pic.spPr.cx = cx
