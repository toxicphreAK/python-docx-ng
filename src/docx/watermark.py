"""Watermark support — the faint "DRAFT" or "CONFIDENTIAL" behind a document's content.

Word implements a watermark as a VML shape inside a header, not as DrawingML. VML is
deprecated in the specification, but this is what current versions of Word write and
what they render correctly; a DrawingML equivalent does not display the same way, and a
watermark that looks wrong is worse than none. So VML it is, and `docx.oxml.ns` carries
the `v:`, `o:` and `w10:` namespaces for it.

A watermark is a header artefact, so which pages show one follows from which header
applies to them. Both API entry points therefore write into all three header types —
default, first-page and even-page — because a watermark that vanishes on page 1 of a
document with a distinct first-page header reads as a bug rather than as a setting.

Scope:

- :meth:`.Document.add_text_watermark` applies the watermark to the whole document.
- :meth:`.Section.add_text_watermark` applies it to one section. Where that section's
  headers are inherited from an earlier one, the watermark goes into the header actually
  in force, which the earlier section shares — a header that is inherited is the same
  header, and there is no way to mark up one section's copy of it alone without first
  breaking the link.
"""

from __future__ import annotations

from typing import IO, TYPE_CHECKING, Iterable, Iterator, List

from docx.oxml.ns import nsdecls, qn
from docx.oxml.parser import parse_xml
from docx.shared import Emu, Length, Pt

if TYPE_CHECKING:
    from lxml.etree import _Element  # pyright: ignore[reportPrivateUsage]

    from docx.section import Section, _BaseHeaderFooter  # pyright: ignore[reportPrivateUsage]

# -- the WordArt "Plain Text" shape type. Word emits this definition alongside every
# -- text watermark; the shape refers to it by id and does not render without it. The
# -- formulas are the WordArt geometry and are reproduced verbatim from Word's output. --
_TEXT_SHAPETYPE_XML = """\
<v:shapetype id="_x0000_t136" coordsize="21600,21600" o:spt="136" adj="10800"
    path="m@7,0l@8,0m@5,21600l@6,21600e">
  <v:formulas>
    <v:f eqn="sum #0 0 10800"/><v:f eqn="prod #0 2 1"/><v:f eqn="sum 21600 0 @1"/>
    <v:f eqn="sum 0 0 @2"/><v:f eqn="sum 21600 0 @3"/><v:f eqn="if @0 @3 0"/>
    <v:f eqn="if @0 21600 @1"/><v:f eqn="if @0 0 @2"/><v:f eqn="if @0 @4 21600"/>
    <v:f eqn="mid @5 @6"/><v:f eqn="mid @8 @5"/><v:f eqn="mid @7 @8"/>
    <v:f eqn="mid @6 @7"/><v:f eqn="sum @6 0 @5"/>
  </v:formulas>
  <v:path textpathok="t" o:connecttype="custom"
      o:connectlocs="@9,0;@10,10800;@11,21600;@12,10800" o:connectangles="270,180,90,0"/>
  <v:textpath on="t" fitshape="t"/>
  <v:handles><v:h position="#0,bottomRight" xrange="6629,14971"/></v:handles>
  <o:lock v:ext="edit" text="t" shapetype="t"/>
</v:shapetype>"""

# -- the picture-frame shape type, the image-watermark counterpart of the above --
_IMAGE_SHAPETYPE_XML = """\
<v:shapetype id="_x0000_t75" coordsize="21600,21600" o:spt="75" o:preferrelative="t"
    path="m@4@5l@4@11@9@11@9@5xe" filled="f" stroked="f">
  <v:stroke joinstyle="miter"/>
  <v:formulas>
    <v:f eqn="if lineDrawn pixelLineWidth 0"/><v:f eqn="sum @0 1 0"/>
    <v:f eqn="sum 0 0 @1"/><v:f eqn="prod @2 1 2"/>
    <v:f eqn="prod @3 21600 pixelWidth"/><v:f eqn="prod @3 21600 pixelHeight"/>
    <v:f eqn="sum @0 0 1"/><v:f eqn="prod @6 1 2"/>
    <v:f eqn="prod @7 21600 pixelWidth"/><v:f eqn="sum @8 21600 0"/>
    <v:f eqn="prod @7 21600 pixelHeight"/><v:f eqn="sum @10 21600 0"/>
  </v:formulas>
  <v:path o:extrusionok="f" gradientshapeok="t" o:connecttype="rect"/>
  <o:lock v:ext="edit" aspectratio="t"/>
</v:shapetype>"""

# -- Word names the shape this and finds an existing watermark by the name; matching it
# -- means a watermark added here is the one Word's own "Remove Watermark" removes --
_TEXT_SHAPE_ID = "PowerPlusWaterMarkObject"
_IMAGE_SHAPE_ID = "WordPictureWatermark"

# -- the z-order Word gives a watermark: a large negative value, putting it behind the
# -- document text rather than over it --
_Z_INDEX = -251658752

# -- Word's own default watermark box. The text is stretched to fill it (`fitshape`),
# -- so these proportions are what makes a watermark look like Word's. --
_DEFAULT_WIDTH = Pt(468)
_DEFAULT_HEIGHT = Pt(234)

# -- Word's "washout" picture correction: brightness up, contrast down, which is what
# -- turns a logo into a pale background image --
_WASHOUT_ATTRS = 'gain="19661f" blacklevel="22938f"'


def _pt(value: Length) -> str:
    """`value` as the point measurement VML style strings use."""
    return f"{round(Emu(int(value)).pt, 2):g}pt"


class Watermark:
    """A watermark in a header — the faint text or image behind the document content.

    Not constructed directly; reached through :attr:`.Section.watermark` or returned by
    :meth:`.Section.add_text_watermark` and :meth:`.Section.add_image_watermark`.
    """

    def __init__(self, shape: _Element):
        self._shape = shape

    def __repr__(self) -> str:
        kind = "image" if self.is_image else f"text {self.text!r}"
        return f"<docx.watermark.Watermark {kind}>"

    @property
    def is_image(self) -> bool:
        """True when this is an image watermark rather than a text one."""
        return self._shape.find(qn("v:imagedata")) is not None

    @property
    def text(self) -> str | None:
        """The watermark text, or |None| for an image watermark."""
        textpath = self._shape.find(qn("v:textpath"))
        return None if textpath is None else (textpath.get("string") or "")

    def remove(self) -> None:
        """Remove this watermark from the document.

        The whole `w:pict` is removed, and the run holding it too when that leaves the
        run empty, so nothing is left behind that Word would render as a stray space.
        """
        pict = self._shape.getparent()
        if pict is None:
            return
        r = pict.getparent()
        if r is None:
            return
        r.remove(pict)
        if r.tag == qn("w:r") and len(r.xpath("./*[not(self::w:rPr)]")) == 0:
            parent = r.getparent()
            if parent is not None:
                parent.remove(r)


def iter_watermarks(hdrftr: _BaseHeaderFooter) -> Iterator[Watermark]:
    """Generate a |Watermark| for each watermark shape in `hdrftr`."""
    for shape in hdrftr.part.element.xpath(
        f'.//w:pict/v:shape[starts-with(@id, "{_TEXT_SHAPE_ID}")]'
        f' | .//w:pict/v:shape[starts-with(@id, "{_IMAGE_SHAPE_ID}")]'
    ):
        yield Watermark(shape)


def iter_watermark_headers(sections: Iterable[Section]) -> Iterator[_BaseHeaderFooter]:
    """Generate the header objects a watermark should be written into for `sections`.

    All three header types of each section, skipping any whose definition has already
    been generated. A header inherited from an earlier section *is* that earlier
    section's header, so writing to both would give it two watermarks.
    """
    seen: List[int] = []
    for section in sections:
        for header in (section.header, section.first_page_header, section.even_page_header):
            part_id = id(header.part)
            if part_id in seen:
                continue
            seen.append(part_id)
            yield header


def add_text_watermark(
    headers: Iterable[_BaseHeaderFooter],
    text: str,
    font: str = "Calibri",
    font_size: Length | int | None = None,
    color: str = "C0C0C0",
    opacity: float | None = None,
    angle: float = 315,
    width: Length | int = _DEFAULT_WIDTH,
    height: Length | int = _DEFAULT_HEIGHT,
    bold: bool = False,
    italic: bool = False,
) -> List[Watermark]:
    """Add a text watermark to each of `headers`, returning the watermarks added."""
    return [
        Watermark(
            _add_shape(
                header,
                _TEXT_SHAPETYPE_XML,
                _text_shape_xml(
                    text, font, font_size, color, opacity, angle, width, height, bold, italic
                ),
            )
        )
        for header in headers
    ]


def add_image_watermark(
    headers: Iterable[_BaseHeaderFooter],
    image_descriptor: str | IO[bytes],
    width: Length | int | None = None,
    height: Length | int | None = None,
    washout: bool = True,
    scale: float = 1.0,
) -> List[Watermark]:
    """Add an image watermark to each of `headers`, returning the watermarks added.

    The image is related to each header part separately, since a relationship belongs to
    the part that refers to it.
    """
    watermarks: List[Watermark] = []
    for header in headers:
        rId, image = header.part.get_or_add_image(image_descriptor)
        cx, cy = image.scaled_dimensions(width, height)
        watermarks.append(
            Watermark(
                _add_shape(
                    header,
                    _IMAGE_SHAPETYPE_XML,
                    _image_shape_xml(
                        rId, image.filename, Emu(int(cx * scale)), Emu(int(cy * scale)), washout
                    ),
                )
            )
        )
    return watermarks


def remove_watermarks(headers: Iterable[_BaseHeaderFooter]) -> int:
    """Remove every watermark from each of `headers`, returning how many were removed."""
    removed = 0
    for header in headers:
        for watermark in list(iter_watermarks(header)):
            watermark.remove()
            removed += 1
    return removed


def _add_shape(hdrftr: _BaseHeaderFooter, shapetype_xml: str, shape_xml: str) -> _Element:
    """Add a `w:pict` holding `shapetype_xml` and `shape_xml` to `hdrftr`.

    The watermark goes in the header's first paragraph, which is where Word puts one. A
    header always has at least one paragraph, but one is added if this header somehow
    has none rather than producing a `w:hdr` the schema does not allow.
    """
    hdr = hdrftr.part.element
    p = next(iter(hdr.xpath("./w:p")), None)
    if p is None:
        p = hdrftr.add_paragraph()._p  # pyright: ignore[reportPrivateUsage]

    pict = parse_xml(f"<w:pict {nsdecls('w', 'v', 'o', 'r')}>{shapetype_xml}{shape_xml}</w:pict>")
    r = parse_xml(f"<w:r {nsdecls('w')}/>")
    r.append(pict)
    p.append(r)
    # -- `w:pict` has no registered element class, so it is a plain lxml element with no
    # -- namespace map of its own; reach the shape by qualified name rather than xpath --
    shape = pict.find(qn("v:shape"))
    assert shape is not None
    return shape


def _text_shape_xml(
    text: str,
    font: str,
    font_size: Length | int | None,
    color: str,
    opacity: float | None,
    angle: float,
    width: Length | int,
    height: Length | int,
    bold: bool,
    italic: bool,
) -> str:
    """The `v:shape` XML for a text watermark.

    With no `font_size` the text is stretched to fill the shape (`fitshape="t"`, which
    the shape type sets), which is how Word sizes a watermark and why the shape's
    proportions matter more than the point size. Giving a `font_size` turns that off and
    renders the text at that size instead.
    """
    style = ";".join(
        (
            "position:absolute",
            "margin-left:0",
            "margin-top:0",
            f"width:{_pt(Emu(int(width)))}",
            f"height:{_pt(Emu(int(height)))}",
            f"rotation:{angle:g}",
            f"z-index:{_Z_INDEX}",
            "mso-position-horizontal:center",
            "mso-position-horizontal-relative:margin",
            "mso-position-vertical:center",
            "mso-position-vertical-relative:margin",
        )
    )
    textpath_style = ";".join(
        part
        for part in (
            f"font-family:&quot;{font}&quot;",
            "font-size:1pt" if font_size is None else f"font-size:{_pt(Emu(int(font_size)))}",
            "font-weight:bold" if bold else "",
            "font-style:italic" if italic else "",
        )
        if part
    )
    fit = "" if font_size is None else ' fitshape="f"'
    fill = "" if opacity is None else f'<v:fill opacity="{opacity:g}"/>'

    return (
        f'<v:shape id="{_TEXT_SHAPE_ID}" o:spid="_x0000_s2049" type="#_x0000_t136"'
        f' style="{style}" o:allowincell="f" fillcolor="#{color.lstrip("#")}"'
        f' stroked="f">{fill}'
        f'<v:textpath style="{textpath_style}"{fit} string="{_escape(text)}"/>'
        "</v:shape>"
    )


def _image_shape_xml(rId: str, filename: str, cx: Length, cy: Length, washout: bool) -> str:
    """The `v:shape` XML for an image watermark."""
    style = ";".join(
        (
            "position:absolute",
            "margin-left:0",
            "margin-top:0",
            f"width:{_pt(cx)}",
            f"height:{_pt(cy)}",
            f"z-index:{_Z_INDEX}",
            "mso-position-horizontal:center",
            "mso-position-horizontal-relative:margin",
            "mso-position-vertical:center",
            "mso-position-vertical-relative:margin",
        )
    )
    washout_attrs = f" {_WASHOUT_ATTRS}" if washout else ""
    return (
        f'<v:shape id="{_IMAGE_SHAPE_ID}" o:spid="_x0000_s2050" type="#_x0000_t75"'
        f' style="{style}" o:allowincell="f">'
        f'<v:imagedata r:id="{rId}" o:title="{_escape(filename)}"{washout_attrs}/>'
        "</v:shape>"
    )


def _escape(value: str) -> str:
    """`value` escaped for use in an XML attribute built by string concatenation."""
    return (
        value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )
