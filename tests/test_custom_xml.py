# pyright: reportPrivateUsage=false

"""Unit test suite for the custom XML data store parts."""

from __future__ import annotations

import io

import docx
from docx.opc.constants import CONTENT_TYPE as CT
from docx.opc.parts.custom_xml import CustomXmlPart, CustomXmlPropertiesPart
from docx.oxml.customxml import CT_DatastoreItem

from .unitutil.cxml import element

_INVOICE = "<invoice><total>42.00</total></invoice>"


def _document_with_store():
    """A document carrying one data store item, saved and reopened.

    The bundled template ships no data store of its own, so a document that has one must
    be built. Reopening is what exercises the load path: the parts are typed by the
    relationship rather than by content type, since a store item is `application/xml`.
    """
    document = docx.Document()
    document.add_custom_xml_part(_INVOICE, ("urn:example:invoice",))
    stream = io.BytesIO()
    document.save(stream)
    return docx.Document(io.BytesIO(stream.getvalue()))


class DescribeCustomXmlParts:
    """Reading the data store of a document that has one."""

    def it_exposes_the_data_store_items_of_a_document(self):
        document = _document_with_store()

        parts = document.custom_xml_parts

        assert len(parts) == 1
        assert isinstance(parts[0], CustomXmlPart)
        assert str(parts[0].partname) == "/customXml/item1.xml"

    def and_a_document_with_no_store_reports_none(self):
        """The bundled template carried the template author's bibliography store until
        it was removed; a generated document now has no store it did not ask for."""
        assert docx.Document().custom_xml_parts == ()

    def it_reads_the_item_id_and_schema_refs_from_the_props_sidecar(self):
        part = _document_with_store().custom_xml_parts[0]

        assert part.item_id is not None
        assert part.item_id.startswith("{")
        assert part.schema_refs == ("urn:example:invoice",)

    def it_exposes_the_item_xml(self):
        part = _document_with_store().custom_xml_parts[0]

        assert part.xml.startswith("<invoice>")
        assert part.element is not None

    def it_types_the_props_part_as_a_CustomXmlPropertiesPart(self):
        document = _document_with_store()

        props = [
            p
            for p in document.part.package.iter_parts()
            if isinstance(p, CustomXmlPropertiesPart)
        ]

        assert len(props) == 1


class DescribeAddCustomXmlPart:
    """Unit-test suite for `Document.add_custom_xml_part()`."""

    def it_adds_an_item_and_its_props_sidecar(self):
        document = docx.Document()

        part = document.add_custom_xml_part(_INVOICE, ("urn:example:invoice",))

        assert str(part.partname) == "/customXml/item1.xml"
        assert part.schema_refs == ("urn:example:invoice",)
        # -- the sidecar is numbered after its item, as Word pairs them --
        props = part.part_related_by(
            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/customXmlProps"
        )
        assert str(props.partname) == "/customXml/itemProps1.xml"
        assert props.content_type == CT.OFC_CUSTOM_XML_PROPERTIES

    def it_generates_a_guid_item_id(self):
        document = docx.Document()

        part = document.add_custom_xml_part(_INVOICE)

        assert part.item_id is not None
        assert part.item_id.startswith("{")
        assert part.item_id.endswith("}")
        assert len(part.item_id) == 38

    def it_accepts_bytes_as_well_as_a_string(self):
        document = docx.Document()

        part = document.add_custom_xml_part(_INVOICE.encode("utf-8"))

        assert "42.00" in part.xml

    def it_round_trips_through_a_save(self):
        reopened = _document_with_store()

        parts = reopened.custom_xml_parts
        assert len(parts) == 1
        assert "42.00" in parts[0].xml
        assert parts[0].schema_refs == ("urn:example:invoice",)

    def it_leaves_an_existing_store_undisturbed_on_open_and_save(self):
        """A data store is an opaque payload; merely rewriting must not touch it."""
        document = _document_with_store()
        before = document.custom_xml_parts[0].xml
        before_id = document.custom_xml_parts[0].item_id

        stream = io.BytesIO()
        document.save(stream)
        reopened = docx.Document(io.BytesIO(stream.getvalue()))

        assert reopened.custom_xml_parts[0].xml == before
        assert reopened.custom_xml_parts[0].item_id == before_id

    def it_numbers_a_second_item_after_the_first(self):
        document = docx.Document()

        first = document.add_custom_xml_part("<a/>")
        second = document.add_custom_xml_part("<b/>")

        assert str(first.partname) == "/customXml/item1.xml"
        assert str(second.partname) == "/customXml/item2.xml"
        assert first.item_id != second.item_id

    def but_a_caller_can_supply_the_item_id(self):
        """A generated GUID is the one thing in this library's output that is not a
        function of its input, so a caller who needs reproducible bytes can pass one."""
        item_id = "{00000000-0000-0000-0000-00000000002A}"
        document = docx.Document()

        part = document.add_custom_xml_part(_INVOICE, item_id=item_id)

        assert part.item_id == item_id

    def and_that_makes_the_output_byte_reproducible(self):
        item_id = "{00000000-0000-0000-0000-00000000002A}"

        def build() -> bytes:
            document = docx.Document()
            document.add_custom_xml_part(_INVOICE, ("urn:example:invoice",), item_id=item_id)
            stream = io.BytesIO()
            document.save(stream)
            return stream.getvalue()

        assert build() == build()


class DescribeCT_DatastoreItem:
    """Unit-test suite for the `ds:datastoreItem` element class."""

    def it_can_be_created_with_schema_refs(self):
        datastoreItem = CT_DatastoreItem.new("{ABC}", ("urn:a", "urn:b"))

        assert datastoreItem.itemID == "{ABC}"
        assert datastoreItem.schema_ref_uris == ("urn:a", "urn:b")

    def and_without_them(self):
        datastoreItem = CT_DatastoreItem.new("{ABC}")

        assert datastoreItem.schemaRefs is None
        assert datastoreItem.schema_ref_uris == ()

    def it_reads_schema_refs_from_an_existing_element(self):
        datastoreItem = element(
            "ds:datastoreItem{ds:itemID=X}/ds:schemaRefs/ds:schemaRef{ds:uri=urn:a}"
        )

        assert datastoreItem.schema_ref_uris == ("urn:a",)
