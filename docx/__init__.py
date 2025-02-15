# encoding: utf-8

from docx.api import Document  # noqa

__version__ = "0.9.8"


# register custom Part classes with opc package reader

from docx.opc.constants import CONTENT_TYPE as CT, RELATIONSHIP_TYPE as RT
from docx.opc.part import PartFactory
from docx.opc.parts.coreprops import CorePropertiesPart
from docx.opc.parts.extendedprops import ExtendedPropertiesPart

from docx.parts.document import DocumentPart
from docx.parts.hdrftr import FooterPart, HeaderPart
from docx.parts.image import ImagePart
from docx.parts.altchunk import AltchunkPart
from docx.parts.numbering import NumberingPart
from docx.parts.settings import SettingsPart
from docx.parts.styles import StylesPart
from docx.parts.comment import CommentPart
from docx.parts.footnote import FootnotePart


def part_class_selector(content_type, reltype):
    if reltype == RT.A_F_CHUNK:
        return AltchunkPart
    if reltype == RT.IMAGE:
        return ImagePart
    return None


PartFactory.part_class_selector = part_class_selector
PartFactory.part_type_for[CT.WML_COMMENTS] = CommentPart
PartFactory.part_type_for[CT.OPC_CORE_PROPERTIES] = CorePropertiesPart
PartFactory.part_type_for[CT.OFC_EXTENDED_PROPERTIES] = ExtendedPropertiesPart
PartFactory.part_type_for[CT.WML_DOCUMENT_MAIN] = DocumentPart
PartFactory.part_type_for[CT.WML_DOCUMENT_MACRO_ENABLED_MAIN] = DocumentPart
PartFactory.part_type_for[CT.WML_FOOTER] = FooterPart
PartFactory.part_type_for[CT.WML_HEADER] = HeaderPart
PartFactory.part_type_for[CT.WML_NUMBERING] = NumberingPart
PartFactory.part_type_for[CT.WML_SETTINGS] = SettingsPart
PartFactory.part_type_for[CT.WML_STYLES] = StylesPart
PartFactory.part_type_for[CT.WML_FOOTNOTES] = FootnotePart

del (
    CT,
    CorePropertiesPart,
    ExtendedPropertiesPart,
    DocumentPart,
    FooterPart,
    HeaderPart,
    FootnotePart,
    CommentPart,
    NumberingPart,
    PartFactory,
    SettingsPart,
    StylesPart,
    part_class_selector,
)
