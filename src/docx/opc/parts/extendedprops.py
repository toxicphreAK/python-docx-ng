"""Extended properties part, corresponds to ``/docProps/app.xml`` part in package."""

from __future__ import annotations

from typing import TYPE_CHECKING

from docx.opc.constants import CONTENT_TYPE as CT
from docx.opc.extendedprops import ExtendedProperties
from docx.opc.packuri import PackURI
from docx.opc.part import XmlPart
from docx.oxml.extendedprops import CT_ExtendedProperties

if TYPE_CHECKING:
    from docx.opc.package import OpcPackage


class ExtendedPropertiesPart(XmlPart):
    """Corresponds to part named ``/docProps/app.xml``.

    Holds the application-specific document properties, such as the word count and the
    producing application, as opposed to the Dublin-Core properties in
    ``/docProps/core.xml``.
    """

    @classmethod
    def default(cls, package: OpcPackage) -> ExtendedPropertiesPart:
        """Return a new |ExtendedPropertiesPart| with default values."""
        extended_properties_part = cls._new(package)
        extended_properties = extended_properties_part.extended_properties
        extended_properties.application = "python-docx-ng"
        return extended_properties_part

    @property
    def extended_properties(self) -> ExtendedProperties:
        """An |ExtendedProperties| object providing read/write access to the extended
        properties contained in this part."""
        return ExtendedProperties(self.element)

    @classmethod
    def _new(cls, package: OpcPackage) -> ExtendedPropertiesPart:
        partname = PackURI("/docProps/app.xml")
        content_type = CT.OFC_EXTENDED_PROPERTIES
        Properties = CT_ExtendedProperties.new()
        return ExtendedPropertiesPart(partname, content_type, Properties, package)
