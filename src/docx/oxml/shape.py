"""Custom element classes for shape-related elements like `<w:inline>`."""

from __future__ import annotations

from typing import cast

from docx.enum.shape import (
    WD_ANCHOR_ALIGN_H,
    WD_ANCHOR_ALIGN_V,
    WD_ANCHOR_RELATIVE_FROM_H,
    WD_ANCHOR_RELATIVE_FROM_V,
    WD_WRAP_TYPE,
)
from docx.exceptions import InvalidXmlError
from docx.oxml.ns import nsdecls, qn
from docx.oxml.parser import OxmlElement, parse_xml
from docx.oxml.simpletypes import (
    ST_Coordinate,
    ST_DrawingElementId,
    ST_PositiveCoordinate,
    ST_RelationshipId,
    ST_WrapDistance,
    XsdBoolean,
    XsdString,
    XsdToken,
    XsdUnsignedInt,
)
from docx.oxml.xmlchemy import (
    BaseOxmlElement,
    OneAndOnlyOne,
    OptionalAttribute,
    RequiredAttribute,
    ZeroOrOne,
)
from docx.shared import Emu, Length


class CT_Anchor(BaseOxmlElement):
    """`<wp:anchor>` element, container for a "floating" shape.

    Where `wp:inline` puts a picture in the text flow like a character, `wp:anchor`
    detaches it: the picture is positioned against the page, the margin, the column or
    the paragraph, and text wraps around it.

    The schema type is an `xsd:sequence` and Word refuses to open a document whose
    children are out of order, so the `successors` bookkeeping below matters more than
    usual. The wrap element is one of an `xsd:choice` — exactly one must be present —
    which is why it is reached through :attr:`wrap_type` rather than as five separate
    declared children.
    """

    _tag_seq = (
        "wp:simplePos",
        "wp:positionH",
        "wp:positionV",
        "wp:extent",
        "wp:effectExtent",
        "wp:wrapNone",
        "wp:wrapSquare",
        "wp:wrapTight",
        "wp:wrapThrough",
        "wp:wrapTopAndBottom",
        "wp:docPr",
        "wp:cNvGraphicFramePr",
        "a:graphic",
    )
    # -- the five wrap elements are alternatives, so each is followed by everything
    # -- after the whole choice --
    _WRAP_SUCCESSORS = _tag_seq[10:]

    positionH: CT_PosH = OneAndOnlyOne("wp:positionH")  # pyright: ignore[reportAssignmentType]
    positionV: CT_PosV = OneAndOnlyOne("wp:positionV")  # pyright: ignore[reportAssignmentType]
    extent: CT_PositiveSize2D = OneAndOnlyOne("wp:extent")  # pyright: ignore[reportAssignmentType]
    docPr: CT_NonVisualDrawingProps = OneAndOnlyOne(  # pyright: ignore[reportAssignmentType]
        "wp:docPr"
    )
    graphic: CT_GraphicalObject = OneAndOnlyOne(  # pyright: ignore[reportAssignmentType]
        "a:graphic"
    )

    distT: int | None = OptionalAttribute("distT", ST_WrapDistance)  # pyright: ignore
    distB: int | None = OptionalAttribute("distB", ST_WrapDistance)  # pyright: ignore
    distL: int | None = OptionalAttribute("distL", ST_WrapDistance)  # pyright: ignore
    distR: int | None = OptionalAttribute("distR", ST_WrapDistance)  # pyright: ignore
    simplePos: bool | None = OptionalAttribute("simplePos", XsdBoolean)  # pyright: ignore
    relativeHeight: int = RequiredAttribute(  # pyright: ignore[reportAssignmentType]
        "relativeHeight", XsdUnsignedInt
    )
    behindDoc: bool = RequiredAttribute(  # pyright: ignore[reportAssignmentType]
        "behindDoc", XsdBoolean
    )
    locked: bool = RequiredAttribute("locked", XsdBoolean)  # pyright: ignore
    layoutInCell: bool = RequiredAttribute(  # pyright: ignore[reportAssignmentType]
        "layoutInCell", XsdBoolean
    )
    allowOverlap: bool = RequiredAttribute(  # pyright: ignore[reportAssignmentType]
        "allowOverlap", XsdBoolean
    )
    hidden: bool | None = OptionalAttribute("hidden", XsdBoolean)  # pyright: ignore

    @property
    def wrap_type(self) -> WD_WRAP_TYPE:
        """Member of :ref:`WdWrapType` describing how text wraps around this shape."""
        for member in WD_WRAP_TYPE:
            if self.find(qn(f"wp:{member.xml_value}")) is not None:
                return member
        raise InvalidXmlError(
            "`wp:anchor` has none of the five wrap elements; the schema requires"
            " exactly one and Word will not open a document without it"
        )

    @wrap_type.setter
    def wrap_type(self, value: WD_WRAP_TYPE):
        for member in WD_WRAP_TYPE:
            existing = self.find(qn(f"wp:{member.xml_value}"))
            if existing is not None:
                self.remove(existing)
        wrap = OxmlElement(f"wp:{value.xml_value}")
        self.insert_element_before(wrap, *self._WRAP_SUCCESSORS)

    @classmethod
    def new_pic_anchor(
        cls,
        shape_id: int,
        rId: str,
        filename: str,
        cx: Length,
        cy: Length,
        pos_x: Length,
        pos_y: Length,
        description: str | None = None,
        title: str | None = None,
        svg_rId: str | None = None,
    ) -> CT_Anchor:
        """Create a `wp:anchor` element containing a `pic:pic` element.

        The shape is positioned `pos_x` right of and `pos_y` below the column and
        paragraph it is anchored to, which is where Word puts a picture converted from
        inline to floating, and text wraps around its bounding rectangle.
        """
        pic_id = 0  # -- as with an inline picture, Word does not appear to use this --
        pic = CT_Picture.new(pic_id, filename, rId, cx, cy, svg_rId=svg_rId)
        anchor = cast(CT_Anchor, parse_xml(cls._anchor_xml()))
        anchor.extent.cx = cx
        anchor.extent.cy = cy
        anchor.positionH.offset = pos_x
        anchor.positionV.offset = pos_y
        anchor.docPr.id = shape_id
        anchor.docPr.name = "Picture %d" % shape_id
        if description is not None:
            anchor.docPr.descr = description
        if title is not None:
            anchor.docPr.title = title
        anchor.graphic.graphicData.uri = "http://schemas.openxmlformats.org/drawingml/2006/picture"
        anchor.graphic.graphicData._insert_pic(pic)  # pyright: ignore[reportPrivateUsage]
        return anchor

    @classmethod
    def _anchor_xml(cls) -> str:
        """A minimum viable `wp:anchor`, with every required attribute present.

        `relativeHeight` is the z-order; 0 puts a new shape at the bottom of the
        floating stack, which Word then adjusts as shapes are added. `simplePos="0"`
        tells Word to use `wp:positionH` and `wp:positionV` rather than the
        `wp:simplePos` coordinate, which Word itself never uses but the schema requires
        to be present.
        """
        return (
            "<wp:anchor %s\n"
            '           distT="0" distB="0" distL="114300" distR="114300"\n'
            '           simplePos="0" relativeHeight="0" behindDoc="0" locked="0"\n'
            '           layoutInCell="1" allowOverlap="1">\n'
            '  <wp:simplePos x="0" y="0"/>\n'
            '  <wp:positionH relativeFrom="column">\n'
            "    <wp:posOffset>0</wp:posOffset>\n"
            "  </wp:positionH>\n"
            '  <wp:positionV relativeFrom="paragraph">\n'
            "    <wp:posOffset>0</wp:posOffset>\n"
            "  </wp:positionV>\n"
            '  <wp:extent cx="914400" cy="914400"/>\n'
            '  <wp:effectExtent l="0" t="0" r="0" b="0"/>\n'
            '  <wp:wrapSquare wrapText="bothSides"/>\n'
            '  <wp:docPr id="666" name="unnamed"/>\n'
            "  <wp:cNvGraphicFramePr>\n"
            '    <a:graphicFrameLocks noChangeAspect="1"/>\n'
            "  </wp:cNvGraphicFramePr>\n"
            "  <a:graphic>\n"
            '    <a:graphicData uri="URI not set"/>\n'
            "  </a:graphic>\n"
            "</wp:anchor>" % nsdecls("wp", "a", "pic", "r")
        )


class _CT_PosBase(BaseOxmlElement):
    """Common behavior of `wp:positionH` and `wp:positionV`.

    Both hold an `xsd:choice` of `wp:align` or `wp:posOffset` — a named alignment such
    as "center", or an absolute distance in EMU. Setting one removes the other, since
    the schema allows only one to be present and Word ignores a document that has both.
    """

    _align_enum: type[WD_ANCHOR_ALIGN_H] | type[WD_ANCHOR_ALIGN_V]

    @property
    def align(self):
        """The named alignment of this position, or |None| when an offset is used."""
        align = self.find(qn("wp:align"))
        if align is None or not align.text:
            return None
        return self._align_enum.from_xml(align.text.strip())

    @align.setter
    def align(self, value: WD_ANCHOR_ALIGN_H | WD_ANCHOR_ALIGN_V | None):
        self._remove_choice()
        if value is None:
            return
        align = OxmlElement("wp:align")
        align.text = self._align_enum.to_xml(value)
        self.append(align)

    @property
    def offset(self) -> Length | None:
        """The absolute offset of this position, or |None| when an alignment is used."""
        posOffset = self.find(qn("wp:posOffset"))
        if posOffset is None or not posOffset.text:
            return None
        return Emu(int(posOffset.text))

    @offset.setter
    def offset(self, value: Length | int | None):
        self._remove_choice()
        if value is None:
            return
        posOffset = OxmlElement("wp:posOffset")
        posOffset.text = str(int(value))
        self.append(posOffset)

    def _remove_choice(self) -> None:
        for tag in ("wp:align", "wp:posOffset"):
            child = self.find(qn(tag))
            if child is not None:
                self.remove(child)


class CT_PosH(_CT_PosBase):
    """`<wp:positionH>` element, the horizontal position of a floating shape."""

    _align_enum = WD_ANCHOR_ALIGN_H

    relativeFrom: WD_ANCHOR_RELATIVE_FROM_H = RequiredAttribute(  # pyright: ignore
        "relativeFrom", WD_ANCHOR_RELATIVE_FROM_H
    )


class CT_PosV(_CT_PosBase):
    """`<wp:positionV>` element, the vertical position of a floating shape."""

    _align_enum = WD_ANCHOR_ALIGN_V

    relativeFrom: WD_ANCHOR_RELATIVE_FROM_V = RequiredAttribute(  # pyright: ignore
        "relativeFrom", WD_ANCHOR_RELATIVE_FROM_V
    )


class CT_Blip(BaseOxmlElement):
    """``<a:blip>`` element, specifies image source and adjustments such as alpha and
    tint."""

    embed: str | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "r:embed", ST_RelationshipId
    )
    link: str | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "r:link", ST_RelationshipId
    )

    @property
    def svgBlip(self) -> CT_SvgBlip | None:
        """The `asvg:svgBlip` extension of this blip, or |None| when there is none.

        Reached by xpath rather than a declared child, because `a:ext` is already
        registered as the extent element of `a:xfrm` and lxml dispatches on tag name
        alone; the same tag means two different things in DrawingML.
        """
        matches = self.xpath("./a:extLst/a:ext/asvg:svgBlip")
        return matches[0] if matches else None


class CT_SvgBlip(BaseOxmlElement):
    """`<asvg:svgBlip>` element, the SVG source of a picture.

    A Word 2016 extension. It accompanies rather than replaces the raster blip: a
    consumer that does not understand the extension renders the raster one instead.
    """

    embed: str | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "r:embed", ST_RelationshipId
    )


class CT_BlipFillProperties(BaseOxmlElement):
    """``<pic:blipFill>`` element, specifies picture properties."""

    blip: CT_Blip = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "a:blip", successors=("a:srcRect", "a:tile", "a:stretch")
    )


class CT_GraphicalObject(BaseOxmlElement):
    """``<a:graphic>`` element, container for a DrawingML object."""

    graphicData: CT_GraphicalObjectData = OneAndOnlyOne(  # pyright: ignore[reportAssignmentType]
        "a:graphicData"
    )


class CT_GraphicalObjectData(BaseOxmlElement):
    """``<a:graphicData>`` element, container for the XML of a DrawingML object."""

    pic: CT_Picture = ZeroOrOne("pic:pic")  # pyright: ignore[reportAssignmentType]
    uri: str = RequiredAttribute("uri", XsdToken)  # pyright: ignore[reportAssignmentType]


class CT_Inline(BaseOxmlElement):
    """`<wp:inline>` element, container for an inline shape."""

    extent: CT_PositiveSize2D = OneAndOnlyOne("wp:extent")  # pyright: ignore[reportAssignmentType]
    docPr: CT_NonVisualDrawingProps = OneAndOnlyOne(  # pyright: ignore[reportAssignmentType]
        "wp:docPr"
    )
    graphic: CT_GraphicalObject = OneAndOnlyOne(  # pyright: ignore[reportAssignmentType]
        "a:graphic"
    )

    @classmethod
    def new(cls, cx: Length, cy: Length, shape_id: int, pic: CT_Picture) -> CT_Inline:
        """Return a new ``<wp:inline>`` element populated with the values passed as
        parameters."""
        inline = cast(CT_Inline, parse_xml(cls._inline_xml()))
        inline.extent.cx = cx
        inline.extent.cy = cy
        inline.docPr.id = shape_id
        inline.docPr.name = "Picture %d" % shape_id
        inline.graphic.graphicData.uri = "http://schemas.openxmlformats.org/drawingml/2006/picture"
        inline.graphic.graphicData._insert_pic(pic)
        return inline

    @classmethod
    def new_pic_inline(
        cls,
        shape_id: int,
        rId: str,
        filename: str,
        cx: Length,
        cy: Length,
        description: str | None = None,
        title: str | None = None,
        svg_rId: str | None = None,
    ) -> CT_Inline:
        """Create `wp:inline` element containing a `pic:pic` element.

        The contents of the `pic:pic` element is taken from the argument values.
        `description` and `title` are the alternative text of the picture and are
        omitted when |None|. `svg_rId`, when given, identifies the SVG source of the
        picture, making `rId` its raster fallback.
        """
        pic_id = 0  # Word doesn't seem to use this, but does not omit it
        pic = CT_Picture.new(pic_id, filename, rId, cx, cy, svg_rId=svg_rId)
        inline = cls.new(cx, cy, shape_id, pic)
        if description is not None:
            inline.docPr.descr = description
        if title is not None:
            inline.docPr.title = title
        return inline

    @classmethod
    def _inline_xml(cls):
        return (
            "<wp:inline %s>\n"
            '  <wp:extent cx="914400" cy="914400"/>\n'
            '  <wp:docPr id="666" name="unnamed"/>\n'
            "  <wp:cNvGraphicFramePr>\n"
            '    <a:graphicFrameLocks noChangeAspect="1"/>\n'
            "  </wp:cNvGraphicFramePr>\n"
            "  <a:graphic>\n"
            '    <a:graphicData uri="URI not set"/>\n'
            "  </a:graphic>\n"
            "</wp:inline>" % nsdecls("wp", "a", "pic", "r")
        )


class CT_NonVisualDrawingProps(BaseOxmlElement):
    """Used for ``<wp:docPr>`` element, and perhaps others.

    Specifies the id and name of a DrawingML drawing, and its alternative text.
    """

    id = RequiredAttribute("id", ST_DrawingElementId)
    name = RequiredAttribute("name", XsdString)
    # -- `descr` is what a screen reader announces; Word's modern "Alt Text" pane
    # -- writes this one. `title` is the separate caption-like field of older Word. --
    descr: str | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "descr", XsdString
    )
    title: str | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "title", XsdString
    )


class CT_NonVisualPictureProperties(BaseOxmlElement):
    """``<pic:cNvPicPr>`` element, specifies picture locking and resize behaviors."""


class CT_Picture(BaseOxmlElement):
    """``<pic:pic>`` element, a DrawingML picture."""

    nvPicPr: CT_PictureNonVisual = OneAndOnlyOne(  # pyright: ignore[reportAssignmentType]
        "pic:nvPicPr"
    )
    blipFill: CT_BlipFillProperties = OneAndOnlyOne(  # pyright: ignore[reportAssignmentType]
        "pic:blipFill"
    )
    spPr: CT_ShapeProperties = OneAndOnlyOne("pic:spPr")  # pyright: ignore[reportAssignmentType]

    @classmethod
    def new(
        cls,
        pic_id: int,
        filename: str,
        rId: str,
        cx: Length,
        cy: Length,
        svg_rId: str | None = None,
    ) -> CT_Picture:
        """A new minimum viable `<pic:pic>` (picture) element.

        `rId` identifies the image the raster blip refers to. When `svg_rId` is given
        the picture also carries an `asvg:svgBlip` extension referring to that SVG, and
        `rId` is the raster fallback shown by anything that does not understand the
        extension.
        """
        pic = parse_xml(cls._pic_xml_svg() if svg_rId else cls._pic_xml())
        pic.nvPicPr.cNvPr.id = pic_id
        pic.nvPicPr.cNvPr.name = filename
        pic.blipFill.blip.embed = rId
        if svg_rId:
            svgBlip = pic.blipFill.blip.svgBlip
            assert svgBlip is not None
            svgBlip.embed = svg_rId
        pic.spPr.cx = cx
        pic.spPr.cy = cy
        return pic

    @classmethod
    def _pic_xml_svg(cls):
        """The `pic:pic` XML for a picture whose source is an SVG.

        The extension `uri` is the fixed GUID Word writes for the SVG extension; a
        consumer matches on it to find the vector source.
        """
        return (
            "<pic:pic %s>\n"
            "  <pic:nvPicPr>\n"
            '    <pic:cNvPr id="666" name="unnamed"/>\n'
            "    <pic:cNvPicPr/>\n"
            "  </pic:nvPicPr>\n"
            "  <pic:blipFill>\n"
            "    <a:blip>\n"
            "      <a:extLst>\n"
            '        <a:ext uri="{96DAC541-7B7A-43D3-8B79-37D633B846F1}">\n'
            "          <asvg:svgBlip/>\n"
            "        </a:ext>\n"
            "      </a:extLst>\n"
            "    </a:blip>\n"
            "    <a:stretch>\n"
            "      <a:fillRect/>\n"
            "    </a:stretch>\n"
            "  </pic:blipFill>\n"
            "  <pic:spPr>\n"
            "    <a:xfrm>\n"
            '      <a:off x="0" y="0"/>\n'
            '      <a:ext cx="914400" cy="914400"/>\n'
            "    </a:xfrm>\n"
            '    <a:prstGeom prst="rect"/>\n'
            "  </pic:spPr>\n"
            "</pic:pic>" % nsdecls("pic", "a", "r", "asvg")
        )

    @classmethod
    def _pic_xml(cls):
        return (
            "<pic:pic %s>\n"
            "  <pic:nvPicPr>\n"
            '    <pic:cNvPr id="666" name="unnamed"/>\n'
            "    <pic:cNvPicPr/>\n"
            "  </pic:nvPicPr>\n"
            "  <pic:blipFill>\n"
            "    <a:blip/>\n"
            "    <a:stretch>\n"
            "      <a:fillRect/>\n"
            "    </a:stretch>\n"
            "  </pic:blipFill>\n"
            "  <pic:spPr>\n"
            "    <a:xfrm>\n"
            '      <a:off x="0" y="0"/>\n'
            '      <a:ext cx="914400" cy="914400"/>\n'
            "    </a:xfrm>\n"
            '    <a:prstGeom prst="rect"/>\n'
            "  </pic:spPr>\n"
            "</pic:pic>" % nsdecls("pic", "a", "r")
        )


class CT_PictureNonVisual(BaseOxmlElement):
    """``<pic:nvPicPr>`` element, non-visual picture properties."""

    cNvPr = OneAndOnlyOne("pic:cNvPr")


class CT_Point2D(BaseOxmlElement):
    """Used for ``<a:off>`` element, and perhaps others.

    Specifies an x, y coordinate (point).
    """

    x = RequiredAttribute("x", ST_Coordinate)
    y = RequiredAttribute("y", ST_Coordinate)


class CT_PositiveSize2D(BaseOxmlElement):
    """Used for ``<wp:extent>`` element, and perhaps others later.

    Specifies the size of a DrawingML drawing.
    """

    cx: Length = RequiredAttribute(  # pyright: ignore[reportAssignmentType]
        "cx", ST_PositiveCoordinate
    )
    cy: Length = RequiredAttribute(  # pyright: ignore[reportAssignmentType]
        "cy", ST_PositiveCoordinate
    )


class CT_PresetGeometry2D(BaseOxmlElement):
    """``<a:prstGeom>`` element, specifies an preset autoshape geometry, such as
    ``rect``."""


class CT_RelativeRect(BaseOxmlElement):
    """``<a:fillRect>`` element, specifying picture should fill containing rectangle
    shape."""


class CT_ShapeProperties(BaseOxmlElement):
    """``<pic:spPr>`` element, specifies size and shape of picture container."""

    xfrm = ZeroOrOne(
        "a:xfrm",
        successors=(
            "a:custGeom",
            "a:prstGeom",
            "a:ln",
            "a:effectLst",
            "a:effectDag",
            "a:scene3d",
            "a:sp3d",
            "a:extLst",
        ),
    )

    @property
    def cx(self):
        """Shape width as an instance of Emu, or None if not present."""
        xfrm = self.xfrm
        if xfrm is None:
            return None
        return xfrm.cx

    @cx.setter
    def cx(self, value):
        xfrm = self.get_or_add_xfrm()
        xfrm.cx = value

    @property
    def cy(self):
        """Shape height as an instance of Emu, or None if not present."""
        xfrm = self.xfrm
        if xfrm is None:
            return None
        return xfrm.cy

    @cy.setter
    def cy(self, value):
        xfrm = self.get_or_add_xfrm()
        xfrm.cy = value


class CT_StretchInfoProperties(BaseOxmlElement):
    """``<a:stretch>`` element, specifies how picture should fill its containing
    shape."""


class CT_Transform2D(BaseOxmlElement):
    """``<a:xfrm>`` element, specifies size and shape of picture container."""

    off = ZeroOrOne("a:off", successors=("a:ext",))
    ext = ZeroOrOne("a:ext", successors=())

    @property
    def cx(self):
        ext = self.ext
        if ext is None:
            return None
        return ext.cx

    @cx.setter
    def cx(self, value):
        ext = self.get_or_add_ext()
        ext.cx = value

    @property
    def cy(self):
        ext = self.ext
        if ext is None:
            return None
        return ext.cy

    @cy.setter
    def cy(self, value):
        ext = self.get_or_add_ext()
        ext.cy = value
