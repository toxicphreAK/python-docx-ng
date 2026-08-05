"""Custom element classes for the custom XML data store's properties part.

`customXml/itemProps1.xml` is the sidecar of `customXml/item1.xml`: it carries the GUID
Word identifies the store item by, and the namespaces of the schemas the item claims to
conform to. The item itself is arbitrary caller-supplied XML with no element classes of
its own.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, List

from docx.oxml.ns import nsdecls, qn
from docx.oxml.parser import parse_xml
from docx.oxml.simpletypes import XsdString
from docx.oxml.xmlchemy import (
    BaseOxmlElement,
    RequiredAttribute,
    ZeroOrMore,
    ZeroOrOne,
)

if TYPE_CHECKING:
    pass


class CT_DatastoreSchemaRef(BaseOxmlElement):
    """`ds:schemaRef` element, naming one schema namespace the store item uses."""

    uri: str = RequiredAttribute("ds:uri", XsdString)  # pyright: ignore[reportAssignmentType]


class CT_DatastoreSchemaRefs(BaseOxmlElement):
    """`ds:schemaRefs` element, the set of schemas a store item claims to conform to."""

    schemaRef_lst: List[CT_DatastoreSchemaRef]
    add_schemaRef: Callable[[], CT_DatastoreSchemaRef]

    schemaRef = ZeroOrMore("ds:schemaRef", successors=())


class CT_DatastoreItem(BaseOxmlElement):
    """`ds:datastoreItem`, the root element of a `customXml/itemPropsN.xml` part."""

    get_or_add_schemaRefs: Callable[[], CT_DatastoreSchemaRefs]

    itemID: str = RequiredAttribute(  # pyright: ignore[reportAssignmentType]
        "ds:itemID", XsdString
    )
    schemaRefs: CT_DatastoreSchemaRefs | None = ZeroOrOne(  # pyright: ignore
        "ds:schemaRefs", successors=()
    )

    @classmethod
    def new(cls, item_id: str, schema_refs: tuple[str, ...] = ()) -> CT_DatastoreItem:
        """A newly created `ds:datastoreItem` for `item_id` naming `schema_refs`."""
        datastoreItem = parse_xml(
            '<ds:datastoreItem %s ds:itemID="%s"/>' % (nsdecls("ds"), item_id)
        )
        if schema_refs:
            schemaRefs = datastoreItem.get_or_add_schemaRefs()
            for uri in schema_refs:
                schemaRefs.add_schemaRef().uri = uri
        return datastoreItem

    @property
    def schema_ref_uris(self) -> tuple[str, ...]:
        """The schema namespaces this item claims, in document order."""
        schemaRefs = self.schemaRefs
        if schemaRefs is None:
            return ()
        return tuple(ref.uri for ref in schemaRefs.schemaRef_lst)


def is_datastore_item(element: object) -> bool:
    """|True| when `element` is a `ds:datastoreItem` root element."""
    return getattr(element, "tag", None) == qn("ds:datastoreItem")
