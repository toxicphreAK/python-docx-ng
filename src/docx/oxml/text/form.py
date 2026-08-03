"""Custom element classes for the legacy form-field elements.

A legacy form field — FORMTEXT, FORMCHECKBOX or FORMDROPDOWN — is a complex field
spread across sibling runs::

    <w:r><w:fldChar w:fldCharType="begin"><w:ffData>…</w:ffData></w:fldChar></w:r>
    <w:r><w:instrText xml:space="preserve"> FORMTEXT </w:instrText></w:r>
    <w:r><w:fldChar w:fldCharType="separate"/></w:r>
    <w:r><w:t>the current value</w:t></w:r>
    <w:r><w:fldChar w:fldCharType="end"/></w:r>

The properties of the field live in `w:ffData` on the "begin" `w:fldChar`; the value of
a text field is the run content between "separate" and "end".

Only the container elements get element classes here. The leaf children of `w:ffData`
and its type-specific children are read and written through their `w:val` attribute
instead, because their tag names are reused elsewhere in the schema with other types —
`w:name` is a style name, `w:type` is a section-break type, and `w:default` is three
different types depending on which of `w:textInput`, `w:checkBox` and `w:ddList` it
appears in. lxml resolves an element class by tag name alone, so registering any of
them would silently change the type of an unrelated element.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, List

from docx.enum.text import WD_TEXT_FORM_FIELD_TYPE
from docx.oxml.ns import qn
from docx.oxml.parser import OxmlElement
from docx.oxml.simpletypes import ST_FldCharType, ST_OnOff, ST_String
from docx.oxml.xmlchemy import (
    BaseOxmlElement,
    OptionalAttribute,
    RequiredAttribute,
    ZeroOrMore,
    ZeroOrOne,
)

if TYPE_CHECKING:
    from lxml.etree import _Element  # pyright: ignore[reportPrivateUsage]

    from docx.oxml.text.run import CT_R


def _val(parent: BaseOxmlElement, tag: str) -> str | None:
    """The `w:val` attribute of the `tag` child of `parent`, or |None|.

    |None| is returned both when the child is absent and when it carries no `w:val`,
    which the schema permits for several of these elements.
    """
    child = parent.find(qn(tag))
    return None if child is None else child.get(qn("w:val"))


def _set_val(parent: BaseOxmlElement, tag: str, value: str | None, tag_seq: tuple[str, ...]):
    """Set the `w:val` attribute of the `tag` child of `parent` to `value`.

    The child is added in the position `tag_seq` gives it if not already present, and
    removed when `value` is |None|. Pass an empty `tag_seq` for a parent whose schema
    type is an `xsd:choice` rather than an `xsd:sequence`, where order is unconstrained.
    """
    child = parent.find(qn(tag))
    if value is None:
        if child is not None:
            parent.remove(child)
        return
    if child is None:
        child = OxmlElement(tag)
        successors = tag_seq[tag_seq.index(tag) + 1 :] if tag in tag_seq else ()
        parent.insert_element_before(child, *successors)
    child.set(qn("w:val"), value)


def _bool_val(parent: BaseOxmlElement, tag: str) -> bool | None:
    """The `w:val` of the `tag` child of `parent` read as `ST_OnOff`, or |None|.

    An `ST_OnOff` element defaults to |True| when present without a `w:val`, which is
    how Word writes `<w:enabled/>`.
    """
    child = parent.find(qn(tag))
    if child is None:
        return None
    val = child.get(qn("w:val"))
    return True if val is None else ST_OnOff.from_xml(val)


def _set_bool_val(parent: BaseOxmlElement, tag: str, value: bool | None, tag_seq: tuple[str, ...]):
    _set_val(parent, tag, None if value is None else ST_OnOff.to_xml(value), tag_seq)


class CT_FFCheckBox(BaseOxmlElement):
    """`w:checkBox` element, the check-box specifics of a form field."""

    _tag_seq = ("w:size", "w:sizeAuto", "w:default", "w:checked")

    @property
    def checked(self) -> bool | None:
        """Whether the box is currently ticked, or |None| when unspecified."""
        return _bool_val(self, "w:checked")

    @checked.setter
    def checked(self, value: bool | None):
        _set_bool_val(self, "w:checked", value, self._tag_seq)

    @property
    def default(self) -> bool | None:
        """Whether the box starts out ticked, or |None| when unspecified."""
        return _bool_val(self, "w:default")

    @default.setter
    def default(self, value: bool | None):
        _set_bool_val(self, "w:default", value, self._tag_seq)


class CT_FFDDList(BaseOxmlElement):
    """`w:ddList` element, the drop-down specifics of a form field."""

    _tag_seq = ("w:result", "w:default", "w:listEntry")

    @property
    def default(self) -> int | None:
        """Index of the entry selected initially, or |None| when unspecified."""
        return self._int_val("w:default")

    @default.setter
    def default(self, value: int | None):
        _set_val(self, "w:default", None if value is None else str(value), self._tag_seq)

    @property
    def listEntry_vals(self) -> List[str]:
        """The `w:val` of each `w:listEntry` child, in document order.

        A `w:listEntry` without a `w:val` contributes an empty string, which is what
        Word shows for it.
        """
        return [entry.get(qn("w:val")) or "" for entry in self.findall(qn("w:listEntry"))]

    @property
    def result(self) -> int | None:
        """Index of the entry currently selected, or |None| when unspecified."""
        return self._int_val("w:result")

    @result.setter
    def result(self, value: int | None):
        _set_val(self, "w:result", None if value is None else str(value), self._tag_seq)

    def _int_val(self, tag: str) -> int | None:
        val = _val(self, tag)
        if val is None:
            return None
        try:
            return int(val)
        except ValueError:
            return None


class CT_FFTextInput(BaseOxmlElement):
    """`w:textInput` element, the text-input specifics of a form field."""

    _tag_seq = ("w:type", "w:default", "w:maxLength", "w:format")

    @property
    def default(self) -> str | None:
        """The text the field starts out holding, or |None| when unspecified."""
        return _val(self, "w:default")

    @default.setter
    def default(self, value: str | None):
        _set_val(self, "w:default", value, self._tag_seq)

    @property
    def format(self) -> str | None:
        """Word's formatting string for the value, e.g. `"UPPERCASE"`, or |None|."""
        return _val(self, "w:format")

    @format.setter
    def format(self, value: str | None):
        _set_val(self, "w:format", value, self._tag_seq)

    @property
    def maxLength(self) -> int | None:
        """The most characters the field accepts, or |None| when unlimited."""
        val = _val(self, "w:maxLength")
        if val is None:
            return None
        try:
            return int(val)
        except ValueError:
            return None

    @maxLength.setter
    def maxLength(self, value: int | None):
        _set_val(self, "w:maxLength", None if value is None else str(value), self._tag_seq)

    @property
    def type(self) -> WD_TEXT_FORM_FIELD_TYPE | None:
        """Member of :ref:`WdTextFormFieldType`, or |None| when unspecified.

        Word treats an unspecified type as `REGULAR`.
        """
        val = _val(self, "w:type")
        return None if val is None else WD_TEXT_FORM_FIELD_TYPE.from_xml(val)

    @type.setter
    def type(self, value: WD_TEXT_FORM_FIELD_TYPE | None):
        _set_val(
            self,
            "w:type",
            None if value is None else WD_TEXT_FORM_FIELD_TYPE.to_xml(value),
            self._tag_seq,
        )


class CT_FFData(BaseOxmlElement):
    """`w:ffData` element, the properties of a legacy form field.

    Its schema type is an unbounded `xsd:choice`, not a sequence, so its children have
    no required order and no `successors` bookkeeping applies.
    """

    get_or_add_checkBox: Callable[[], CT_FFCheckBox]
    get_or_add_ddList: Callable[[], CT_FFDDList]
    get_or_add_textInput: Callable[[], CT_FFTextInput]

    checkBox: CT_FFCheckBox | None = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "w:checkBox", successors=()
    )
    ddList: CT_FFDDList | None = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "w:ddList", successors=()
    )
    textInput: CT_FFTextInput | None = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "w:textInput", successors=()
    )

    @property
    def calcOnExit(self) -> bool | None:
        """Whether Word recalculates fields when this one is left, or |None|."""
        return _bool_val(self, "w:calcOnExit")

    @calcOnExit.setter
    def calcOnExit(self, value: bool | None):
        _set_bool_val(self, "w:calcOnExit", value, ())

    @property
    def enabled(self) -> bool | None:
        """Whether the field can be edited, or |None| when unspecified.

        Word treats an unspecified value as enabled.
        """
        return _bool_val(self, "w:enabled")

    @enabled.setter
    def enabled(self, value: bool | None):
        _set_bool_val(self, "w:enabled", value, ())

    @property
    def helpText(self) -> str | None:
        """The text Word shows when F1 is pressed in the field, or |None|."""
        return _val(self, "w:helpText")

    @helpText.setter
    def helpText(self, value: str | None):
        _set_val(self, "w:helpText", value, ())

    @property
    def name(self) -> str | None:
        """The bookmark name of the field, or |None| when it has none."""
        return _val(self, "w:name")

    @name.setter
    def name(self, value: str | None):
        _set_val(self, "w:name", value, ())

    @property
    def statusText(self) -> str | None:
        """The text Word shows in the status bar for the field, or |None|."""
        return _val(self, "w:statusText")

    @statusText.setter
    def statusText(self, value: str | None):
        _set_val(self, "w:statusText", value, ())


class CT_FldChar(BaseOxmlElement):
    """`w:fldChar` element, a field-character marking a boundary of a complex field."""

    get_or_add_ffData: Callable[[], CT_FFData]

    ffData: CT_FFData | None = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "w:ffData", successors=()
    )

    fldCharType: str = RequiredAttribute(  # pyright: ignore[reportAssignmentType]
        "w:fldCharType", ST_FldCharType
    )
    fldLock: bool | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:fldLock", ST_OnOff
    )
    dirty: bool | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:dirty", ST_OnOff
    )

    @property
    def r(self) -> _Element | None:
        """The `w:r` element this field-character belongs to, or |None|.

        A `w:fldChar` is always a child of a run in a valid document, but a caller can
        detach one.
        """
        parent = self.getparent()
        return parent if parent is not None and parent.tag == qn("w:r") else None


class CT_SimpleField(BaseOxmlElement):
    """`w:fldSimple` element, a field whose instruction and result are one element.

    The instruction is an attribute and the cached result is the element's content, so
    unlike a complex field this is self-contained. Word writes a legacy form field as a
    complex field rather than a simple one, and `w:ffData` is not allowed here.
    """

    add_r: Callable[[], CT_R]
    r_lst: List[CT_R]

    r = ZeroOrMore("w:r", successors=())

    instr: str = RequiredAttribute(  # pyright: ignore[reportAssignmentType]
        "w:instr", ST_String
    )
    fldLock: bool | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:fldLock", ST_OnOff
    )
    dirty: bool | None = OptionalAttribute(  # pyright: ignore[reportAssignmentType]
        "w:dirty", ST_OnOff
    )

    @property
    def result_text(self) -> str:
        """The result text of this field, as Word last rendered it."""
        return "".join(str(t) for t in self.xpath(".//w:t"))

    @property
    def text(self) -> str:  # pyright: ignore[reportIncompatibleMethodOverride]
        """The text this field displays, which is its cached result."""
        return self.result_text
