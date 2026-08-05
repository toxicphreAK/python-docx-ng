"""The custom XML data store parts, `customXml/itemN.xml` and its properties sidecar.

A `.docx` can carry arbitrary XML in the custom XML data store, and bind document
content to it through `w:dataBinding` inside a `w:sdt`. This is how most
document-generation pipelines that are not string substitution actually work: the data
lives in the store, the content controls display it, and Word keeps the two in sync.

This is a different thing from the custom *document properties* in `docProps/custom.xml`
(`docx.opc.customprops`), which are a flat list of named scalars.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lxml import etree

from docx.opc.constants import CONTENT_TYPE as CT
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.packuri import PackURI
from docx.opc.part import XmlPart
from docx.oxml.customxml import CT_DatastoreItem

if TYPE_CHECKING:
    from docx.opc.package import OpcPackage
    from docx.oxml.xmlchemy import BaseOxmlElement


class CustomXmlPropertiesPart(XmlPart):
    """A `customXml/itemPropsN.xml` part, the sidecar of a data store item.

    Carries the GUID Word identifies the item by and the namespaces of the schemas it
    claims to conform to.
    """

    @classmethod
    def new(
        cls, package: OpcPackage, partname: PackURI, item_id: str, schema_refs: tuple[str, ...]
    ) -> CustomXmlPropertiesPart:
        """A newly created properties part for a store item."""
        return cls(
            partname,
            CT.OFC_CUSTOM_XML_PROPERTIES,
            CT_DatastoreItem.new(item_id, schema_refs),
            package,
        )

    @property
    def item_id(self) -> str:
        """The GUID Word identifies the store item by, e.g. ``"{EF278816-...}"``."""
        return self.element.itemID  # pyright: ignore[reportAttributeAccessIssue]

    @property
    def schema_refs(self) -> tuple[str, ...]:
        """The schema namespaces the store item claims, in document order."""
        return self.element.schema_ref_uris  # pyright: ignore[reportAttributeAccessIssue]


class CustomXmlPart(XmlPart):
    """A `customXml/itemN.xml` part, one item of the custom XML data store.

    The content is arbitrary caller-supplied XML, so it has no element classes of its
    own; :attr:`element` is a plain parsed tree and :attr:`xml` its serialization.
    """

    @classmethod
    def new(cls, package: OpcPackage, partname: PackURI, element: BaseOxmlElement) -> CustomXmlPart:
        """A newly created store item part holding `element`."""
        return cls(partname, CT.XML, element, package)

    @property
    def item_id(self) -> str | None:
        """The GUID this item is identified by, or |None| when it has no props part.

        A store item without a properties part is out of spec but does occur; Word
        ignores such an item rather than repairing the document.
        """
        props = self._props_part
        return None if props is None else props.item_id

    @property
    def schema_refs(self) -> tuple[str, ...]:
        """The schema namespaces this item claims, empty when it has no props part."""
        props = self._props_part
        return () if props is None else props.schema_refs

    @property
    def xml(self) -> str:
        """The item's XML as a string.

        Serialized with lxml directly rather than through `BaseOxmlElement.xml`: the
        content is arbitrary caller-supplied XML, so its root arrives as a plain
        `lxml.etree._Element` with none of this library's element classes behind it.
        """
        return etree.tostring(self.element, encoding="unicode", pretty_print=True)

    @property
    def _props_part(self) -> CustomXmlPropertiesPart | None:
        """The `itemPropsN.xml` part of this item, or |None| when there is none."""
        try:
            part = self.part_related_by(RT.CUSTOM_XML_PROPS)
        except KeyError:
            return None
        return part if isinstance(part, CustomXmlPropertiesPart) else None
