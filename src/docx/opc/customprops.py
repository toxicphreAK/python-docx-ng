"""Provides CustomProperties, the arbitrary named values a document can carry.

These are the properties stored in `/docProps/custom.xml`, the third document-properties
part alongside the Dublin-Core properties in `core.xml` and the application properties
in `app.xml`. Word shows them under File > Info > Properties > Advanced, and a
`DOCPROPERTY` field in the document body refers to one by name.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Iterator, MutableMapping

if TYPE_CHECKING:
    from docx.oxml.customprops import CT_CustomProperties

CustomPropertyValue = "str | int | float | bool | dt.datetime | None"


class CustomProperties(MutableMapping[str, "str | int | float | bool | dt.datetime | None"]):
    """A mapping of custom document property name to value.

    Behaves as a |dict| of `str` to value::

        document.custom_properties["Matter number"] = 4242
        document.custom_properties["Reviewed"] = True
        del document.custom_properties["Draft"]

    A value may be a `str`, `int`, `float`, `bool` or `datetime`, which cover the
    variant types Word writes and read back as the same Python type. Assigning any other
    type raises |ValueError| rather than writing a file Word would refuse to open.

    A property whose value uses a variant this library does not model — a vector, array
    or blob — reads as the raw text of its element, so a document that carries one can
    still be read and re-saved without losing it.

    Property names are case-sensitive and must be unique; assigning to an existing name
    replaces its value and leaves its property id alone.
    """

    def __init__(self, element: CT_CustomProperties):
        self._element = element

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and self._element.get_by_name(name) is not None

    def __delitem__(self, name: str) -> None:
        property = self._element.get_by_name(name)
        if property is None:
            raise KeyError(name)
        self._element.remove(property)

    def __getitem__(self, name: str) -> str | int | float | bool | dt.datetime | None:
        property = self._element.get_by_name(name)
        if property is None:
            raise KeyError(name)
        return property.value

    def __iter__(self) -> Iterator[str]:
        for property in self._element.property_lst:
            if property.name is not None:
                yield property.name

    def __len__(self) -> int:
        return len(self._element.property_lst)

    def __repr__(self) -> str:
        return "%s(%r)" % (type(self).__name__, dict(self))

    def __setitem__(
        self, name: str, value: str | int | float | bool | dt.datetime | None
    ) -> None:
        property = self._element.get_by_name(name)
        if property is None:
            self._element.add_named_property(name, value)
            return
        property.value = value

    def lookup_by_pid(self, pid: int) -> str | int | float | bool | dt.datetime | None:
        """The value of the property having property id `pid`.

        Raises |KeyError| when no property has that id. Property ids matter only for
        documents that reference a property by id rather than name; the mapping
        interface is the ordinary way in.
        """
        for property in self._element.property_lst:
            if property.pid == pid:
                return property.value
        raise KeyError(pid)
