"""Custom element classes for the custom document properties part.

Stored as `/docProps/custom.xml`, this is the third and last of the document-properties
parts, after the Dublin-Core properties in `core.xml` and the application properties in
`app.xml`. It holds arbitrary named values, which is what document-management systems,
contract tooling and mail-merge pipelines use to carry their own keys, and what a
`DOCPROPERTY` field in the document body refers to.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Callable, List, cast

from docx.oxml.ns import nsdecls
from docx.oxml.parser import OxmlElement, parse_xml
from docx.oxml.simpletypes import XsdInt, XsdString
from docx.oxml.xmlchemy import BaseOxmlElement, OptionalAttribute, RequiredAttribute, ZeroOrMore

if TYPE_CHECKING:
    from lxml.etree import _Element as etree_Element  # pyright: ignore[reportPrivateUsage]

# -- every user-defined custom property carries this fixed format id --
FMTID_USER_DEFINED = "{D5CDD505-2E9C-101B-9397-08002B2CF9AE}"

# -- `pid` values 0 and 1 are reserved, so user properties start here --
_FIRST_PID = 2

class CT_Property(BaseOxmlElement):
    """`<property>` element, one custom document property.

    The value is carried by a single child element from the `vt:` variant namespace,
    whose tag names the type. Writing the wrong variant for a value produces a file Word
    refuses to open, so the mapping is deliberate and narrow.
    """

    fmtid: str = RequiredAttribute("fmtid", XsdString)  # pyright: ignore[reportAssignmentType]
    pid: int = RequiredAttribute("pid", XsdInt)  # pyright: ignore[reportAssignmentType]
    name: str | None = OptionalAttribute("name", XsdString)
    linkTarget: str | None = OptionalAttribute("linkTarget", XsdString)

    @property
    def value(self) -> str | int | float | bool | dt.datetime | None:
        """The Python value of this property, or |None| for an empty or null variant.

        A variant this library does not model — a vector, array or blob — reads as the
        raw text of the element, so nothing in a document is silently dropped, but such
        a property cannot be written back through a Python value.
        """
        variant = self._variant
        if variant is None:
            return None
        localname = variant.tag.split("}")[1]
        text = variant.text or ""

        if localname in ("empty", "null"):
            return None
        if localname == "bool":
            return text.strip() in ("1", "true", "TRUE", "True")
        if localname in _INT_VARIANTS:
            return int(text)
        if localname in _FLOAT_VARIANTS:
            return float(text)
        if localname == "filetime":
            return _parse_filetime(text)
        return text

    @value.setter
    def value(self, value: str | int | float | bool | dt.datetime | None) -> None:
        variant = self._variant
        if variant is not None:
            self.remove(variant)
        self.append(_new_variant(value))

    @property
    def _variant(self) -> etree_Element | None:
        """The `vt:` child carrying this property's value, or |None| if absent."""
        children = list(self)
        return children[0] if children else None


class CT_CustomProperties(BaseOxmlElement):
    """`<Properties>` element, the root of the custom document properties part."""

    add_property: Callable[[], CT_Property]
    property_lst: List[CT_Property]

    # -- note this shadows the `property` builtin inside the class body, which is why
    # -- `next_pid` below is a method rather than a property --
    property = ZeroOrMore("cust:property", successors=())

    _Properties_tmpl = "<cust:Properties %s/>\n" % nsdecls("cust", "vt")

    @classmethod
    def new(cls) -> CT_CustomProperties:
        """Return a new, empty `<Properties>` element."""
        return cast(CT_CustomProperties, parse_xml(cls._Properties_tmpl))

    def add_named_property(self, name: str, value: object) -> CT_Property:
        """Return a new `<property>` element for `name`, appended to this part."""
        # -- compute the pid before adding; the new element has none yet and the scan
        # -- would trip over it --
        pid = self.next_pid()
        property = self.add_property()
        property.fmtid = FMTID_USER_DEFINED
        property.pid = pid
        property.name = name
        property.value = cast("str | int | float | bool | dt.datetime | None", value)
        return property

    def get_by_name(self, name: str) -> CT_Property | None:
        """The `<property>` element named `name`, or |None| if there is none."""
        for property in self.property_lst:
            if property.name == name:
                return property
        return None

    def next_pid(self) -> int:
        """The property id to give the next property added.

        One greater than the highest in use. Gaps left by deleted properties are not
        reused and existing properties are never renumbered: a `pid` need only be
        unique, and rewriting them would churn the file for no gain.
        """
        pids = [property.pid for property in self.property_lst]
        return max(pids) + 1 if pids else _FIRST_PID


# -- the `vt:` variants that carry an integer or a floating-point value. Only `i4` and
# -- `r8` are ever written, but any of these can be read from a document written by
# -- something else. --
_INT_VARIANTS = frozenset(
    ("i1", "i2", "i4", "i8", "int", "ui1", "ui2", "ui4", "ui8", "uint")
)
_FLOAT_VARIANTS = frozenset(("r4", "r8", "decimal"))


def _new_variant(value: str | int | float | bool | dt.datetime | None) -> etree_Element:
    """A new `vt:` element carrying `value`, typed by the Python type of `value`.

    `bool` is tested before `int` because it is a subclass of it.
    """
    if value is None:
        return OxmlElement("vt:null")
    if isinstance(value, bool):
        variant = OxmlElement("vt:bool")
        variant.text = "true" if value else "false"
    elif isinstance(value, int):
        variant = OxmlElement("vt:i4")
        variant.text = str(value)
    elif isinstance(value, float):
        variant = OxmlElement("vt:r8")
        variant.text = repr(value)
    elif isinstance(value, dt.datetime):
        variant = OxmlElement("vt:filetime")
        variant.text = _format_filetime(value)
    elif isinstance(value, str):
        variant = OxmlElement("vt:lpwstr")
        variant.text = value
    else:
        raise ValueError(
            "custom property value must be str, int, float, bool, datetime or None,"
            " got %s" % type(value).__name__
        )
    return variant


def _format_filetime(value: dt.datetime) -> str:
    """`value` as the UTC ISO-8601 string a `vt:filetime` element carries.

    A naive datetime is taken to be UTC already, matching how the core properties treat
    one.
    """
    if value.tzinfo is not None:
        value = value.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return value.replace(microsecond=0).isoformat() + "Z"


def _parse_filetime(text: str) -> dt.datetime | None:
    """The datetime in `text`, or |None| when it is not a form we recognize.

    Returned naive and in UTC, as |CoreProperties| does.
    """
    text = text.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            return dt.datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None
