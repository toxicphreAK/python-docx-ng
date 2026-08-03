# pyright: reportPrivateUsage=false

"""Unit test suite for the custom document properties."""

from __future__ import annotations

import datetime as dt
import io

import pytest

import docx
from docx.opc.customprops import CustomProperties
from docx.oxml.customprops import FMTID_USER_DEFINED, CT_CustomProperties


class DescribeCustomProperties:
    """Unit-test suite for `docx.opc.customprops.CustomProperties`."""

    @pytest.mark.parametrize(
        ("value", "expected_variant"),
        [
            ("Acme Corporation", "lpwstr"),
            (4242, "i4"),
            (1250.5, "r8"),
            (True, "bool"),
            (dt.datetime(2026, 8, 3, 9, 30), "filetime"),
            (None, "null"),
        ],
    )
    def it_writes_the_variant_matching_the_python_type(
        self, value: object, expected_variant: str, custom_properties: CustomProperties
    ):
        """The wrong variant for a value produces a file Word refuses to open."""
        custom_properties["Key"] = value  # pyright: ignore[reportArgumentType]

        property = custom_properties._element.get_by_name("Key")
        assert property is not None
        assert property._variant.tag.split("}")[1] == expected_variant

    @pytest.mark.parametrize(
        "value",
        [
            "Acme Corporation",
            4242,
            1250.5,
            True,
            False,
            dt.datetime(2026, 8, 3, 9, 30),
            None,
        ],
    )
    def it_round_trips_a_value_as_the_same_python_type(
        self, value: object, custom_properties: CustomProperties
    ):
        custom_properties["Key"] = value  # pyright: ignore[reportArgumentType]

        read_back = custom_properties["Key"]

        assert read_back == value
        assert type(read_back) is type(value)

    def it_rejects_a_value_of_an_unsupported_type(self, custom_properties: CustomProperties):
        with pytest.raises(ValueError, match="must be str, int, float, bool, datetime"):
            custom_properties["Key"] = [1, 2, 3]  # pyright: ignore[reportArgumentType]

    def it_behaves_as_a_mapping(self, custom_properties: CustomProperties):
        custom_properties["A"] = "one"
        custom_properties["B"] = "two"

        assert len(custom_properties) == 2
        assert list(custom_properties) == ["A", "B"]
        assert dict(custom_properties) == {"A": "one", "B": "two"}
        assert "A" in custom_properties
        assert "C" not in custom_properties

        del custom_properties["A"]

        assert list(custom_properties) == ["B"]

    def it_raises_KeyError_for_a_property_that_is_not_there(
        self, custom_properties: CustomProperties
    ):
        with pytest.raises(KeyError):
            custom_properties["absent"]
        with pytest.raises(KeyError):
            del custom_properties["absent"]

    def it_replaces_a_value_without_disturbing_its_property_id(
        self, custom_properties: CustomProperties
    ):
        custom_properties["A"] = "one"
        custom_properties["B"] = "two"
        original_pid = custom_properties._element.get_by_name("A").pid

        custom_properties["A"] = "changed"

        assert custom_properties["A"] == "changed"
        assert custom_properties._element.get_by_name("A").pid == original_pid
        assert len(custom_properties) == 2

    def it_allocates_property_ids_from_two_upward(self, custom_properties: CustomProperties):
        """0 and 1 are reserved, and a pid need only be unique."""
        for name in ("A", "B", "C"):
            custom_properties[name] = name

        assert [p.pid for p in custom_properties._element.property_lst] == [2, 3, 4]

    def it_does_not_reuse_the_property_id_of_a_deleted_property(
        self, custom_properties: CustomProperties
    ):
        """Reusing one would be legal but renumbering churns the file for no gain."""
        for name in ("A", "B", "C"):
            custom_properties[name] = name

        del custom_properties["B"]
        custom_properties["D"] = "D"

        assert [p.pid for p in custom_properties._element.property_lst] == [2, 4, 5]

    def it_gives_every_property_the_user_defined_format_id(
        self, custom_properties: CustomProperties
    ):
        custom_properties["A"] = "one"

        assert custom_properties._element.get_by_name("A").fmtid == FMTID_USER_DEFINED

    def it_can_look_a_property_up_by_its_id(self, custom_properties: CustomProperties):
        custom_properties["A"] = "one"

        assert custom_properties.lookup_by_pid(2) == "one"
        with pytest.raises(KeyError):
            custom_properties.lookup_by_pid(99)

    def it_reads_a_variant_it_does_not_model_as_raw_text(self):
        """A document carrying a vector or blob must still be readable."""
        from docx.oxml.parser import parse_xml

        element = parse_xml(
            '<cust:Properties xmlns:cust="http://schemas.openxmlformats.org/'
            'officeDocument/2006/custom-properties" xmlns:vt="http://schemas.'
            'openxmlformats.org/officeDocument/2006/docPropsVTypes">'
            '<cust:property fmtid="%s" pid="2" name="Weird">'
            "<vt:cy>1234.5678</vt:cy></cust:property></cust:Properties>" % FMTID_USER_DEFINED
        )

        assert CustomProperties(element)["Weird"] == "1234.5678"

    # fixtures ---------------------------------------------

    @pytest.fixture
    def custom_properties(self) -> CustomProperties:
        return CustomProperties(CT_CustomProperties.new())


class DescribeCustomPropertiesPart:
    """Integration-test suite for the `/docProps/custom.xml` part."""

    def it_is_created_on_demand(self):
        """Most documents have none, and one that never uses them should gain none."""
        import zipfile

        document = docx.Document()
        untouched = io.BytesIO()
        document.save(untouched)

        with zipfile.ZipFile(untouched) as z:
            assert "docProps/custom.xml" not in z.namelist()

        document.custom_properties["Key"] = "value"
        touched = io.BytesIO()
        document.save(touched)

        with zipfile.ZipFile(touched) as z:
            assert "docProps/custom.xml" in z.namelist()

    def it_survives_a_round_trip(self):
        document = docx.Document()
        document.custom_properties.update(
            {
                "Matter number": 4242,
                "Client": "Acme Corporation",
                "Rate": 1250.5,
                "Reviewed": True,
                "Signed on": dt.datetime(2026, 8, 3, 9, 30),
            }
        )

        stream = io.BytesIO()
        document.save(stream)
        stream.seek(0)

        assert dict(docx.Document(stream).custom_properties) == {
            "Matter number": 4242,
            "Client": "Acme Corporation",
            "Rate": 1250.5,
            "Reviewed": True,
            "Signed on": dt.datetime(2026, 8, 3, 9, 30),
        }
