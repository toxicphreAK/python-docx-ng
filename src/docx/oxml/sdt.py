"""Custom element classes for structured document tags, aka "content controls".

A `w:sdt` element wraps a region of a document, marking it as a form field, a template
placeholder, a building block, or a region bound to a data source. Its content lives
inside a `w:sdtContent` child, so anything that walks a container's children without
looking through that wrapper simply does not see it.

The schema defines four `w:sdt` variants — block, run, row and cell — differing only in
the content model of `w:sdtContent`. lxml dispatches on tag name alone, so one element
class serves all four; what a particular `w:sdt` contains is discovered from its
children rather than declared.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Iterator, cast

from docx.enum.text import WD_CONTENT_CONTROL_TYPE
from docx.oxml.ns import qn
from docx.oxml.xmlchemy import BaseOxmlElement, ZeroOrOne

if TYPE_CHECKING:
    from docx.oxml.shared import CT_String
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.hyperlink import CT_Hyperlink
    from docx.oxml.text.paragraph import CT_P
    from docx.oxml.text.run import CT_R

# -- the `w:sdtPr` child identifying the kind of control. `w:sdtPr` holds at most one of
# -- these, per the xsd:choice in CT_SdtPr. `w14:checkbox` is the Word 2010 extension;
# -- it is not in the ISO schema but is what Word writes for a check box. --
_CONTROL_TYPE_TAGS = (
    ("w14:checkbox", WD_CONTENT_CONTROL_TYPE.CHECKBOX),
    ("w:comboBox", WD_CONTENT_CONTROL_TYPE.COMBO_BOX),
    ("w:date", WD_CONTENT_CONTROL_TYPE.DATE),
    ("w:docPartList", WD_CONTENT_CONTROL_TYPE.BUILDING_BLOCK_GALLERY),
    ("w:docPartObj", WD_CONTENT_CONTROL_TYPE.BUILDING_BLOCK_GALLERY),
    ("w:dropDownList", WD_CONTENT_CONTROL_TYPE.DROPDOWN_LIST),
    ("w:group", WD_CONTENT_CONTROL_TYPE.GROUP),
    ("w:picture", WD_CONTENT_CONTROL_TYPE.PICTURE),
    ("w:richText", WD_CONTENT_CONTROL_TYPE.RICH_TEXT),
    ("w:text", WD_CONTENT_CONTROL_TYPE.TEXT),
    ("w15:repeatingSection", WD_CONTENT_CONTROL_TYPE.REPEATING_SECTION),
)


# -- Wrappers that contribute nothing of their own and whose `w:r` children are ordinary
# -- runs one level down. `w:smartTag` is what Word puts around a recognised entity — a
# -- date, a name, a place; Word 2003 wrote them freely and they still round-trip
# -- through modern Word. `w:customXml` has the same shape. Both are transparent under
# -- either reading of a revised document, so they are shared with the original-text
# -- walk in `docx.oxml.revision` rather than listed twice. --
TRANSPARENT_WRAPPER_TAGS = (qn("w:smartTag"), qn("w:customXml"))

# -- run-level wrappers whose children are part of the text as the document now reads:
# -- a field's cached result, and an insertion --
_LOOK_THROUGH_TAGS = (
    qn("w:fldSimple"),
    qn("w:ins"),
    qn("w:moveTo"),
) + TRANSPARENT_WRAPPER_TAGS

# -- and one whose children are not: deleted text --
_SKIP_TAGS = (qn("w:del"), qn("w:moveFrom"))


def iter_block_content(element: BaseOxmlElement) -> Iterator[CT_P | CT_Tbl]:
    """Generate each `w:p` and `w:tbl` child of `element`, in document order.

    A `w:sdt` child is looked through rather than skipped: the block-level content of
    its `w:sdtContent` is generated in its place, recursively, so a content control
    nested in another content control is seen as well.

    So is a `w:customXml`, which the schema defines in a block-level flavour
    (`CT_CustomXmlBlock`) as well as the run-level one — it wraps whole paragraphs and
    tables, and skipping it drops them from the document entirely.
    """
    for child in element.iterchildren():
        if child.tag in (qn("w:p"), qn("w:tbl")):
            yield cast("CT_P | CT_Tbl", child)
        elif child.tag in TRANSPARENT_WRAPPER_TAGS:
            yield from iter_block_content(cast("BaseOxmlElement", child))
        elif child.tag == qn("w:sdt"):
            sdtContent = child.find(qn("w:sdtContent"))
            if sdtContent is not None:
                yield from iter_block_content(sdtContent)


def iter_run_content(element: BaseOxmlElement) -> Iterator[CT_R | CT_Hyperlink]:
    """Generate each `w:r` and `w:hyperlink` child of `element`, in document order.

    This is the document as it now reads, which for a document carrying tracked changes
    means with every revision accepted.

    As with :func:`iter_block_content`, a run-level `w:sdt` is looked through. So is a
    `w:fldSimple`, whose runs hold the result text the field displays; skipping it would
    drop a page number or a cross-reference from the paragraph's text. So is an
    insertion (`w:ins`, `w:moveTo`), whose runs are part of the text. A deletion
    (`w:del`, `w:moveFrom`) is skipped: its text is no longer part of the document, and
    it is held in `w:delText` rather than `w:t` for exactly that reason. Use
    :func:`docx.oxml.revision.iter_original_run_content` for the other reading.
    """
    for child in element.iterchildren():
        if child.tag in (qn("w:r"), qn("w:hyperlink")):
            yield cast("CT_R | CT_Hyperlink", child)
        elif child.tag in _LOOK_THROUGH_TAGS:
            yield from iter_run_content(cast("BaseOxmlElement", child))
        elif child.tag in _SKIP_TAGS:
            continue
        elif child.tag == qn("w:sdt"):
            sdtContent = child.find(qn("w:sdtContent"))
            if sdtContent is not None:
                yield from iter_run_content(sdtContent)


class CT_Sdt(BaseOxmlElement):
    """`w:sdt` element, a structured document tag ("content control")."""

    get_or_add_sdtPr: Callable[[], CT_SdtPr]
    get_or_add_sdtContent: Callable[[], CT_SdtContent]

    sdtPr: CT_SdtPr | None = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "w:sdtPr", successors=("w:sdtEndPr", "w:sdtContent")
    )
    sdtContent: CT_SdtContent | None = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "w:sdtContent", successors=()
    )

    @property
    def alias_val(self) -> str | None:
        """The friendly name shown on the control in Word, or |None| if not set."""
        return self._sdtPr_str_val("w:alias")

    @property
    def content_control_type(self) -> WD_CONTENT_CONTROL_TYPE | None:
        """Member of :ref:`WdContentControlType` this control is, or |None|.

        |None| when `w:sdtPr` is absent or names no type, which Word treats as a
        rich-text control but is not the same as saying so explicitly.
        """
        sdtPr = self.sdtPr
        if sdtPr is None:
            return None
        for nsptag, control_type in _CONTROL_TYPE_TAGS:
            if sdtPr.find(qn(nsptag)) is not None:
                return control_type
        return None

    @property
    def id_val(self) -> int | None:
        """Value of `./w:sdtPr/w:id/@w:val`, or |None| if not present.

        Read from the attribute directly rather than through a registered element class;
        `w:id` appears in several unrelated places in the schema and is not this
        library's to claim globally.
        """
        sdtPr = self.sdtPr
        if sdtPr is None:
            return None
        id = sdtPr.find(qn("w:id"))
        if id is None:
            return None
        val = id.get(qn("w:val"))
        return None if val is None else int(val)

    @property
    def showing_placeholder(self) -> bool:
        """True when the control currently displays its placeholder text.

        The text inside such a control is the prompt ("Click here to enter text."), not
        a value the user supplied.
        """
        sdtPr = self.sdtPr
        if sdtPr is None:
            return False
        showingPlcHdr = sdtPr.find(qn("w:showingPlcHdr"))
        if showingPlcHdr is None:
            return False
        val = showingPlcHdr.get(qn("w:val"))
        return val is None or val not in ("0", "false", "off")

    @property
    def tag_val(self) -> str | None:
        """Value of `./w:sdtPr/w:tag/@w:val`, or |None| if not present.

        The tag is the programmatic identifier of the control; unlike the alias it is
        not shown to the user and is what code binding to a template matches on.

        Named `tag_val` rather than `tag` because `.tag` is lxml's element tag name.
        """
        return self._sdtPr_str_val("w:tag")

    @property
    def text(self) -> str:  # pyright: ignore[reportIncompatibleMethodOverride]
        """The text of everything inside this content control."""
        sdtContent = self.sdtContent
        return "" if sdtContent is None else sdtContent.text

    def _sdtPr_str_val(self, nsptag: str) -> str | None:
        """Value of the `w:val` attribute of the `w:sdtPr` child named `nsptag`."""
        sdtPr = self.sdtPr
        if sdtPr is None:
            return None
        child = cast("CT_String | None", sdtPr.find(qn(nsptag)))
        return None if child is None else child.val


class CT_SdtContent(BaseOxmlElement):
    """`w:sdtContent` element, the content region of a `w:sdt`."""

    @property
    def text(self) -> str:  # pyright: ignore[reportIncompatibleMethodOverride]
        """The text of this content region.

        Block-level content contributes one line per paragraph, including paragraphs
        inside a table; run-level content is concatenated as it would be in a paragraph.
        """
        block_items = list(iter_block_content(self))
        if block_items:
            lines: list[str] = []
            for element in block_items:
                if element.tag == qn("w:p"):
                    lines.append(element.text)
                else:  # -- a `w:tbl`; take the text of each of its paragraphs --
                    lines.extend(p.text for p in element.xpath(".//w:p"))
            return "\n".join(lines)
        return "".join(e.text for e in iter_run_content(self))


class CT_SdtPr(BaseOxmlElement):
    """`w:sdtPr` element, the properties of a `w:sdt`."""
