# ruff: noqa: E402, I001

"""Initializes oxml sub-package.

This including registering custom element classes corresponding to Open XML elements.
"""

from __future__ import annotations

from docx.oxml.drawing import CT_Drawing
from docx.oxml.parser import OxmlElement, parse_xml, register_element_cls
from docx.oxml.shape import (
    CT_Anchor,
    CT_Blip,
    CT_BlipFillProperties,
    CT_GraphicalObject,
    CT_GraphicalObjectData,
    CT_Inline,
    CT_NonVisualDrawingProps,
    CT_Picture,
    CT_PictureNonVisual,
    CT_Point2D,
    CT_PosH,
    CT_PositiveSize2D,
    CT_PosV,
    CT_ShapeProperties,
    CT_SvgBlip,
    CT_Transform2D,
)
from docx.oxml.shared import CT_DecimalNumber, CT_OnOff, CT_String
from docx.oxml.text.form import (
    CT_FFCheckBox,
    CT_FFData,
    CT_FFDDList,
    CT_FFTextInput,
    CT_FldChar,
    CT_SimpleField,
)
from docx.oxml.text.hyperlink import CT_Hyperlink
from docx.oxml.text.pagebreak import CT_LastRenderedPageBreak
from docx.oxml.text.run import (
    CT_R,
    CT_Br,
    CT_Cr,
    CT_NoBreakHyphen,
    CT_PTab,
    CT_Text,
)

# -- `OxmlElement` and `parse_xml()` are not used in this module but several downstream
# -- "extension" packages expect to find them here and there's no compelling reason
# -- not to republish them here so those keep working.
__all__ = ["OxmlElement", "parse_xml"]

# ---------------------------------------------------------------------------
# DrawingML-related elements

register_element_cls("a:blip", CT_Blip)
register_element_cls("a:ext", CT_PositiveSize2D)
register_element_cls("a:graphic", CT_GraphicalObject)
register_element_cls("a:graphicData", CT_GraphicalObjectData)
register_element_cls("a:off", CT_Point2D)
register_element_cls("a:xfrm", CT_Transform2D)
register_element_cls("asvg:svgBlip", CT_SvgBlip)
register_element_cls("pic:blipFill", CT_BlipFillProperties)
register_element_cls("pic:cNvPr", CT_NonVisualDrawingProps)
register_element_cls("pic:nvPicPr", CT_PictureNonVisual)
register_element_cls("pic:pic", CT_Picture)
register_element_cls("pic:spPr", CT_ShapeProperties)
register_element_cls("w:drawing", CT_Drawing)
register_element_cls("wp:anchor", CT_Anchor)
register_element_cls("wp:docPr", CT_NonVisualDrawingProps)
register_element_cls("wp:extent", CT_PositiveSize2D)
register_element_cls("wp:inline", CT_Inline)
register_element_cls("wp:positionH", CT_PosH)
register_element_cls("wp:positionV", CT_PosV)
register_element_cls("wp:simplePos", CT_Point2D)

# ---------------------------------------------------------------------------
# hyperlink-related elements

register_element_cls("w:hyperlink", CT_Hyperlink)

# ---------------------------------------------------------------------------
# form-field-related elements
#
# The leaf children of `w:ffData` — `w:name`, `w:default`, `w:checked`, `w:result`,
# `w:listEntry` and the rest — deliberately get no element class. Their tag names are
# reused elsewhere in the schema with other types and lxml resolves an element class by
# tag name alone, so registering them would silently retype unrelated elements.

register_element_cls("w:checkBox", CT_FFCheckBox)
register_element_cls("w:ddList", CT_FFDDList)
register_element_cls("w:ffData", CT_FFData)
register_element_cls("w:fldChar", CT_FldChar)
register_element_cls("w:fldSimple", CT_SimpleField)
register_element_cls("w:instrText", CT_Text)
register_element_cls("w:textInput", CT_FFTextInput)

# ---------------------------------------------------------------------------
# text-related elements

register_element_cls("w:br", CT_Br)
register_element_cls("w:cr", CT_Cr)
register_element_cls("w:lastRenderedPageBreak", CT_LastRenderedPageBreak)
register_element_cls("w:noBreakHyphen", CT_NoBreakHyphen)
register_element_cls("w:ptab", CT_PTab)
register_element_cls("w:r", CT_R)
register_element_cls("w:t", CT_Text)

# ---------------------------------------------------------------------------
# header/footer-related mappings

register_element_cls("w:evenAndOddHeaders", CT_OnOff)
register_element_cls("w:titlePg", CT_OnOff)

# ---------------------------------------------------------------------------
# other custom element class mappings

from .bookmark import CT_BookmarkEnd, CT_BookmarkStart

register_element_cls("w:bookmarkEnd", CT_BookmarkEnd)
register_element_cls("w:bookmarkStart", CT_BookmarkStart)

from .comments import CT_Comments, CT_Comment

register_element_cls("w:comments", CT_Comments)
register_element_cls("w:comment", CT_Comment)

from .coreprops import CT_CoreProperties

register_element_cls("cp:coreProperties", CT_CoreProperties)

from .customprops import CT_CustomProperties, CT_Property

register_element_cls("cust:Properties", CT_CustomProperties)
register_element_cls("cust:property", CT_Property)

from .extendedprops import CT_ExtendedProperties

register_element_cls("ep:Properties", CT_ExtendedProperties)

from .footnotes import CT_Footnotes, CT_FtnEdn, CT_FtnEdnRef

# -- `w:footnote` is also the tag of the `CT_FtnEdnSepRef` children of `w:footnotePr` in
# -- a section or in the settings part. Those carry only a `w:id` attribute, which
# -- `CT_FtnEdn` reads the same way, so sharing the class costs nothing. --
register_element_cls("w:footnote", CT_FtnEdn)
register_element_cls("w:footnoteReference", CT_FtnEdnRef)
register_element_cls("w:footnotes", CT_Footnotes)

from .document import CT_AltChunk, CT_Body, CT_Document

register_element_cls("w:altChunk", CT_AltChunk)
register_element_cls("w:body", CT_Body)
register_element_cls("w:document", CT_Document)

from .numbering import CT_AbstractNum, CT_Lvl, CT_Num, CT_Numbering, CT_NumLvl, CT_NumPr

register_element_cls("w:abstractNum", CT_AbstractNum)
register_element_cls("w:abstractNumId", CT_DecimalNumber)
register_element_cls("w:ilvl", CT_DecimalNumber)
# -- `w:lvl` is CT_Lvl everywhere it appears. Its leaf children are deliberately not
# -- registered: `w:start` is already a table-cell border, and lxml resolves an element
# -- class by tag name alone, so claiming it here would retype every table border. --
register_element_cls("w:lvl", CT_Lvl)
register_element_cls("w:lvlOverride", CT_NumLvl)
register_element_cls("w:num", CT_Num)
register_element_cls("w:numId", CT_DecimalNumber)
register_element_cls("w:numPr", CT_NumPr)
register_element_cls("w:numbering", CT_Numbering)
register_element_cls("w:startOverride", CT_DecimalNumber)

from .section import (
    CT_Column,
    CT_Columns,
    CT_HdrFtr,
    CT_HdrFtrRef,
    CT_PageMar,
    CT_PageSz,
    CT_SectPr,
    CT_SectType,
)

register_element_cls("w:col", CT_Column)
register_element_cls("w:cols", CT_Columns)

register_element_cls("w:footerReference", CT_HdrFtrRef)
register_element_cls("w:ftr", CT_HdrFtr)
register_element_cls("w:hdr", CT_HdrFtr)
register_element_cls("w:headerReference", CT_HdrFtrRef)
register_element_cls("w:pgMar", CT_PageMar)
register_element_cls("w:pgSz", CT_PageSz)
register_element_cls("w:sectPr", CT_SectPr)
register_element_cls("w:type", CT_SectType)

from .settings import CT_Settings

register_element_cls("w:settings", CT_Settings)
register_element_cls("w:trackRevisions", CT_OnOff)
register_element_cls("w:updateFields", CT_OnOff)

from .revision import CT_TrackChange

# -- One class serves every position these tags appear in, as lxml dispatches on tag
# -- name alone. `w:ins` and `w:del` wrap content in a paragraph, mark a paragraph mark
# -- in `w:pPr/w:rPr`, and mark a row in `w:trPr`; all three carry the same attributes.
# -- `w:delText` is CT_Text so its text reads the same way `w:t` does. --
register_element_cls("w:del", CT_TrackChange)
register_element_cls("w:delText", CT_Text)
register_element_cls("w:ins", CT_TrackChange)
register_element_cls("w:moveFrom", CT_TrackChange)
register_element_cls("w:moveTo", CT_TrackChange)
register_element_cls("w:pPrChange", CT_TrackChange)
register_element_cls("w:rPrChange", CT_TrackChange)
register_element_cls("w:sectPrChange", CT_TrackChange)
register_element_cls("w:tblGridChange", CT_TrackChange)
register_element_cls("w:tblPrChange", CT_TrackChange)
register_element_cls("w:tcPrChange", CT_TrackChange)
register_element_cls("w:trPrChange", CT_TrackChange)

from .styles import CT_LatentStyles, CT_LsdException, CT_Style, CT_Styles

register_element_cls("w:basedOn", CT_String)
register_element_cls("w:latentStyles", CT_LatentStyles)
# -- `w:link` appears only in `CT_Style` in the schema, so claiming the tag globally is
# -- safe here in a way it is not for `w:name` or `w:start` --
register_element_cls("w:link", CT_String)
register_element_cls("w:locked", CT_OnOff)
register_element_cls("w:lsdException", CT_LsdException)
register_element_cls("w:name", CT_String)
register_element_cls("w:next", CT_String)
register_element_cls("w:qFormat", CT_OnOff)
register_element_cls("w:semiHidden", CT_OnOff)
register_element_cls("w:style", CT_Style)
register_element_cls("w:styles", CT_Styles)
register_element_cls("w:uiPriority", CT_DecimalNumber)
register_element_cls("w:unhideWhenUsed", CT_OnOff)

from .sdt import CT_Sdt, CT_SdtContent, CT_SdtPr

register_element_cls("w:alias", CT_String)
register_element_cls("w:sdt", CT_Sdt)
register_element_cls("w:sdtContent", CT_SdtContent)
register_element_cls("w:sdtPr", CT_SdtPr)
register_element_cls("w:tag", CT_String)

from .table import (
    CT_Border,
    CT_Height,
    CT_Row,
    CT_Tbl,
    CT_TblBorders,
    CT_TblGrid,
    CT_TblGridCol,
    CT_TblLayoutType,
    CT_TblPr,
    CT_TblPrEx,
    CT_TblWidth,
    CT_Tc,
    CT_TcBorders,
    CT_TcPr,
    CT_TrPr,
    CT_VMerge,
    CT_VerticalJc,
)

# -- The border edge tags below are also the child tag names of `w:tblCellMar` and
# -- `w:tcMar`, where the schema gives them type `CT_TblWidth` instead. lxml resolves an
# -- element class by tag name alone, so only one mapping can win; `CT_Border` is chosen
# -- because it also covers `w:pBdr` and `w:pgBorders`. Any future cell-margins API must
# -- therefore read `w:tcMar` children through `.get()` rather than element-class attrs.
register_element_cls("w:bottom", CT_Border)
register_element_cls("w:end", CT_Border)
register_element_cls("w:insideH", CT_Border)
register_element_cls("w:insideV", CT_Border)
register_element_cls("w:left", CT_Border)
register_element_cls("w:right", CT_Border)
register_element_cls("w:start", CT_Border)
register_element_cls("w:tblBorders", CT_TblBorders)
register_element_cls("w:tcBorders", CT_TcBorders)
register_element_cls("w:tl2br", CT_Border)
register_element_cls("w:top", CT_Border)
register_element_cls("w:tr2bl", CT_Border)

register_element_cls("w:bidiVisual", CT_OnOff)
register_element_cls("w:cantSplit", CT_OnOff)
register_element_cls("w:gridAfter", CT_DecimalNumber)
register_element_cls("w:gridBefore", CT_DecimalNumber)
register_element_cls("w:gridCol", CT_TblGridCol)
register_element_cls("w:gridSpan", CT_DecimalNumber)
register_element_cls("w:tbl", CT_Tbl)
register_element_cls("w:tblGrid", CT_TblGrid)
register_element_cls("w:tblLayout", CT_TblLayoutType)
register_element_cls("w:tblPr", CT_TblPr)
register_element_cls("w:tblPrEx", CT_TblPrEx)
register_element_cls("w:tblStyle", CT_String)
register_element_cls("w:tc", CT_Tc)
register_element_cls("w:tcPr", CT_TcPr)
register_element_cls("w:tcW", CT_TblWidth)
register_element_cls("w:tr", CT_Row)
register_element_cls("w:trHeight", CT_Height)
register_element_cls("w:trPr", CT_TrPr)
register_element_cls("w:vAlign", CT_VerticalJc)
register_element_cls("w:vMerge", CT_VMerge)

from .text.font import (
    CT_Color,
    CT_Fonts,
    CT_Highlight,
    CT_HpsMeasure,
    CT_RPr,
    CT_Shd,
    CT_TextScale,
    CT_Underline,
    CT_VerticalAlignRun,
)

register_element_cls("w:b", CT_OnOff)
register_element_cls("w:bCs", CT_OnOff)
register_element_cls("w:caps", CT_OnOff)
register_element_cls("w:color", CT_Color)
register_element_cls("w:cs", CT_OnOff)
register_element_cls("w:dstrike", CT_OnOff)
register_element_cls("w:emboss", CT_OnOff)
register_element_cls("w:highlight", CT_Highlight)
register_element_cls("w:i", CT_OnOff)
register_element_cls("w:iCs", CT_OnOff)
register_element_cls("w:imprint", CT_OnOff)
register_element_cls("w:noProof", CT_OnOff)
register_element_cls("w:oMath", CT_OnOff)
register_element_cls("w:outline", CT_OnOff)
register_element_cls("w:rFonts", CT_Fonts)
register_element_cls("w:rPr", CT_RPr)
register_element_cls("w:rStyle", CT_String)
register_element_cls("w:rtl", CT_OnOff)
register_element_cls("w:shadow", CT_OnOff)
register_element_cls("w:shd", CT_Shd)
register_element_cls("w:smallCaps", CT_OnOff)
register_element_cls("w:snapToGrid", CT_OnOff)
register_element_cls("w:specVanish", CT_OnOff)
register_element_cls("w:strike", CT_OnOff)
register_element_cls("w:sz", CT_HpsMeasure)
register_element_cls("w:szCs", CT_HpsMeasure)
register_element_cls("w:u", CT_Underline)
register_element_cls("w:vanish", CT_OnOff)
register_element_cls("w:vertAlign", CT_VerticalAlignRun)
register_element_cls("w:w", CT_TextScale)
register_element_cls("w:webHidden", CT_OnOff)

from .text.paragraph import CT_P

register_element_cls("w:p", CT_P)

from .text.parfmt import (
    CT_Ind,
    CT_Jc,
    CT_PPr,
    CT_Spacing,
    CT_TabStop,
    CT_TabStops,
)

register_element_cls("w:ind", CT_Ind)
register_element_cls("w:jc", CT_Jc)
register_element_cls("w:keepLines", CT_OnOff)
register_element_cls("w:keepNext", CT_OnOff)
register_element_cls("w:outlineLvl", CT_DecimalNumber)
register_element_cls("w:pageBreakBefore", CT_OnOff)
register_element_cls("w:pPr", CT_PPr)
register_element_cls("w:pStyle", CT_String)
register_element_cls("w:spacing", CT_Spacing)
register_element_cls("w:tab", CT_TabStop)
register_element_cls("w:tabs", CT_TabStops)
register_element_cls("w:widowControl", CT_OnOff)
