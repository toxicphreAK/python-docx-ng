"""The |FormField| object, a legacy Word form field."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Iterator, List, cast

from docx.enum.text import WD_FORM_FIELD_TYPE
from docx.exceptions import InvalidXmlError
from docx.oxml.ns import nsmap, qn
from docx.oxml.parser import OxmlElement
from docx.shared import StoryChild

if TYPE_CHECKING:
    from lxml.etree import _Element  # pyright: ignore[reportPrivateUsage]

    import docx.types as t
    from docx.enum.text import WD_TEXT_FORM_FIELD_TYPE
    from docx.oxml.text.form import CT_FFData, CT_FldChar
    from docx.oxml.text.run import CT_R

# -- an XPath finding the "begin" field-character of every legacy form field in a
# -- subtree; an ordinary field such as PAGE or TOC has no `w:ffData` and is skipped --
_FORM_FIELD_XPATH = './/w:fldChar[@w:fldCharType="begin"][w:ffData]'


def iter_form_fields(element: _Element, parent: t.ProvidesStoryPart) -> Iterator[FormField]:
    """Generate a |FormField| for each legacy form field in the subtree of `element`."""
    for fldChar in cast("List[CT_FldChar]", element.xpath(_FORM_FIELD_XPATH)):
        yield FormField(fldChar, parent)


class FormField(StoryChild):
    """A legacy form field — a text input, check box or drop-down.

    Word writes a form field as a complex field: a "begin" field-character carrying the
    field properties in `w:ffData`, the field instruction, a "separate" field-character,
    the current value, and an "end" field-character, each in its own run. This object
    proxies the "begin" field-character and reaches the rest through it.

    Legacy form fields are what Word's Developer ribbon calls "Legacy Forms". They are
    distinct from content controls (`w:sdt`), which :class:`.ContentControl` covers.

    The whole field is expected to sit in one paragraph, which is how Word writes a
    legacy form field — it does not let a paragraph break be typed into one. Reading or
    writing :attr:`value` on a field whose "end" field-character is in a later paragraph
    raises |InvalidXmlError| rather than returning a partial value.
    """

    def __init__(self, fldChar: CT_FldChar, parent: t.ProvidesStoryPart):
        super().__init__(parent)
        self._element = self._fldChar = fldChar

    @property
    def calc_on_exit(self) -> bool | None:
        """Whether Word recalculates its fields when this one is left.

        |None| when the document does not say, which Word treats as |False|.
        """
        return self._ffData.calcOnExit

    @calc_on_exit.setter
    def calc_on_exit(self, value: bool | None):
        self._ffData.calcOnExit = value

    @property
    def default(self) -> str | bool | None:
        """The value this field starts out holding, |None| when it has no default.

        A |bool| for a check box, the text for a text input, and the selected entry for
        a drop-down, matching :attr:`value`. Assigning an entry a drop-down does not
        offer raises |ValueError|, as it does for :attr:`value`; assigning |None|
        removes the default.
        """
        field_type = self.type
        if field_type == WD_FORM_FIELD_TYPE.CHECK_BOX:
            return self._checkBox.default
        if field_type == WD_FORM_FIELD_TYPE.DROP_DOWN:
            return self._entry_at(self._ddList.default)
        return self._textInput.default

    @default.setter
    def default(self, value: str | bool | None):
        field_type = self.type
        if field_type == WD_FORM_FIELD_TYPE.CHECK_BOX:
            self._checkBox.default = None if value is None else bool(value)
        elif field_type == WD_FORM_FIELD_TYPE.DROP_DOWN:
            self._ddList.default = None if value is None else self._require_entry_index(value)
        else:
            self._textInput.default = None if value is None else str(value)

    @property
    def enabled(self) -> bool | None:
        """Whether the field can be edited.

        |None| when the document does not say, which Word treats as enabled.
        """
        return self._ffData.enabled

    @enabled.setter
    def enabled(self, value: bool | None):
        self._ffData.enabled = value

    @property
    def help_text(self) -> str | None:
        """The text Word shows when F1 is pressed in this field, or |None|."""
        return self._ffData.helpText

    @help_text.setter
    def help_text(self, value: str | None):
        self._ffData.helpText = value

    @property
    def items(self) -> tuple[str, ...]:
        """The entries of a drop-down field, in the order Word lists them.

        Empty for a field that is not a drop-down.
        """
        if self.type != WD_FORM_FIELD_TYPE.DROP_DOWN:
            return ()
        return tuple(self._ddList.listEntry_vals)

    @property
    def max_length(self) -> int | None:
        """The most characters a text field accepts, |None| when unlimited.

        |None| for a field that is not a text input.
        """
        if self.type != WD_FORM_FIELD_TYPE.TEXT:
            return None
        return self._textInput.maxLength

    @max_length.setter
    def max_length(self, value: int | None):
        self._require_text_field("max_length")
        self._textInput.maxLength = value

    @property
    def name(self) -> str | None:
        """The bookmark name Word knows this field by, or |None| when it has none.

        This is the name shown in the "Bookmark" box of the form-field properties
        dialog and the one a `REF` field or a macro would use.
        """
        return self._ffData.name

    @name.setter
    def name(self, value: str | None):
        self._ffData.name = value

    @property
    def status_text(self) -> str | None:
        """The text Word shows in the status bar for this field, or |None|."""
        return self._ffData.statusText

    @status_text.setter
    def status_text(self, value: str | None):
        self._ffData.statusText = value

    @property
    def text_type(self) -> WD_TEXT_FORM_FIELD_TYPE | None:
        """Member of :ref:`WdTextFormFieldType` a text field accepts, or |None|.

        |None| both for a field that is not a text input and for a text input that does
        not say, which Word treats as `REGULAR_TEXT`.
        """
        if self.type != WD_FORM_FIELD_TYPE.TEXT:
            return None
        return self._textInput.type

    @text_type.setter
    def text_type(self, value: WD_TEXT_FORM_FIELD_TYPE | None):
        self._require_text_field("text_type")
        self._textInput.type = value

    @property
    def type(self) -> WD_FORM_FIELD_TYPE:
        """Member of :ref:`WdFormFieldType` telling what kind of field this is."""
        ffData = self._ffData
        if ffData.checkBox is not None:
            return WD_FORM_FIELD_TYPE.CHECK_BOX
        if ffData.ddList is not None:
            return WD_FORM_FIELD_TYPE.DROP_DOWN
        if ffData.textInput is not None:
            return WD_FORM_FIELD_TYPE.TEXT
        raise InvalidXmlError(
            "`w:ffData` has none of `w:checkBox`, `w:ddList` or `w:textInput`, so the"
            " kind of form field it describes cannot be determined"
        )

    @property
    def value(self) -> str | bool:
        """The value this field currently holds.

        A |bool| for a check box; for a drop-down the selected entry, the empty string
        when nothing is selected; for a text input the result text Word last rendered,
        which is the empty string for an empty field.

        Note that Word renders an empty text field as five spaces or similar filler
        text; that filler is what this returns, because it is what the document
        contains. Compare against :attr:`default` to tell an untouched field apart.
        """
        field_type = self.type
        if field_type == WD_FORM_FIELD_TYPE.CHECK_BOX:
            checked = self._checkBox.checked
            if checked is not None:
                return checked
            return bool(self._checkBox.default)
        if field_type == WD_FORM_FIELD_TYPE.DROP_DOWN:
            entry = self._entry_at(self._ddList.result)
            if entry is not None:
                return entry
            return self._entry_at(self._ddList.default) or ""
        return self._result_text

    @value.setter
    def value(self, value: str | bool):
        field_type = self.type
        if field_type == WD_FORM_FIELD_TYPE.CHECK_BOX:
            self._checkBox.checked = bool(value)
            return
        if field_type == WD_FORM_FIELD_TYPE.DROP_DOWN:
            index = self._require_entry_index(value)
            self._ddList.result = index
            self._set_result_text(self.items[index])
            return
        self._set_result_text(str(value))

    # -- private ------------------------------------------------------

    @property
    def _checkBox(self):
        return self._ffData.get_or_add_checkBox()

    @property
    def _ddList(self):
        return self._ffData.get_or_add_ddList()

    @property
    def _ffData(self) -> CT_FFData:
        ffData = self._fldChar.ffData
        if ffData is None:
            raise InvalidXmlError("this `w:fldChar` has no `w:ffData`, so is not a form field")
        return ffData

    @property
    def _textInput(self):
        return self._ffData.get_or_add_textInput()

    def _entry_at(self, index: int | None) -> str | None:
        """The drop-down entry at `index`, or |None| when there is none there."""
        if index is None:
            return None
        entries = self._ddList.listEntry_vals
        return entries[index] if 0 <= index < len(entries) else None

    def _require_entry_index(self, value: str | bool) -> int:
        """The index of drop-down entry `value`.

        Raises |ValueError| naming the entries on offer rather than silently leaving the
        field unchanged, since a value the list does not contain is always a mistake.
        """
        entries = self._ddList.listEntry_vals
        try:
            return entries.index(str(value))
        except ValueError:
            raise ValueError(
                "'%s' is not one of the entries of this drop-down; it offers %s"
                % (value, ", ".join(repr(e) for e in entries) or "none")
            ) from None

    def _field_runs(self) -> tuple[_Element | None, List[_Element], _Element]:
        """`(separate_r, result_elms, end_r)` for this field.

        `separate_r` is the run holding the "separate" field-character, |None| when the
        field has none. `result_elms` are the elements between it and the "end"
        field-character, which is in `end_r`. A field nested in the result contributes
        its own elements to `result_elms`, as it does to the rendered value.
        """
        begin_r = self._fldChar.r
        if begin_r is None:
            raise InvalidXmlError("this `w:fldChar` is not inside a `w:r`")

        depth = 1
        separate_r: _Element | None = None
        result_elms: List[_Element] = []
        for sibling in begin_r.itersiblings():
            fldCharType = _fldCharType_of(sibling)
            if fldCharType == "begin":
                depth += 1
            elif fldCharType == "end":
                depth -= 1
                if depth == 0:
                    return separate_r, result_elms, sibling
            elif fldCharType == "separate" and depth == 1:
                separate_r = sibling
                result_elms = []
                continue
            if separate_r is not None:
                result_elms.append(sibling)

        raise InvalidXmlError("this form field has no `w:fldChar` of type 'end'")

    @property
    def _result_text(self) -> str:
        """The text Word last rendered as the value of this field."""
        _, result_elms, _ = self._field_runs()
        return "".join(str(t) for elm in result_elms for t in elm.xpath(".//w:t", namespaces=nsmap))

    def _require_text_field(self, prop_name: str) -> None:
        field_type = self.type
        if field_type != WD_FORM_FIELD_TYPE.TEXT:
            raise ValueError(
                "`.%s` applies only to a text form field, this one is %s"
                % (prop_name, field_type.name)
            )

    def _set_result_text(self, text: str) -> None:
        """Replace the rendered value of this field with `text`.

        The formatting of the first existing result run is kept, since that is what
        Word applies to what the user types. A field with no "separate"
        field-character has never been rendered; one is added so the value has
        somewhere to live.
        """
        separate_r, result_elms, end_r = self._field_runs()

        if separate_r is None:
            separate_r = _new_fldChar_r("separate")
            end_r.addprevious(separate_r)
            result_elms = []

        result_runs = [elm for elm in result_elms if elm.tag == qn("w:r")]
        if result_runs:
            value_r = cast("CT_R", result_runs[0])
            for elm in result_elms:
                if elm is not value_r:
                    cast("_Element", elm.getparent()).remove(elm)
        else:
            value_r = cast("CT_R", OxmlElement("w:r"))
            begin_r = cast("_Element", self._fldChar.r)
            rPr = begin_r.find(qn("w:rPr"))
            if rPr is not None:
                value_r.append(deepcopy(rPr))
            for elm in result_elms:
                cast("_Element", elm.getparent()).remove(elm)
            separate_r.addnext(value_r)

        value_r.text = text


def _fldCharType_of(element: _Element) -> str | None:
    """The `w:fldCharType` of the field-character `element` holds, else |None|.

    `element` is a sibling in a paragraph, so it may be anything from a run to a
    bookmark marker; only a run whose first field-character child is present counts.
    """
    if element.tag != qn("w:r"):
        return None
    fldChar = element.find(qn("w:fldChar"))
    return None if fldChar is None else fldChar.get(qn("w:fldCharType"))


def _new_fldChar_r(fldCharType: str) -> _Element:
    """A new `w:r` holding a `w:fldChar` of `fldCharType`."""
    r = OxmlElement("w:r")
    fldChar = OxmlElement("w:fldChar")
    fldChar.set(qn("w:fldCharType"), fldCharType)
    r.append(fldChar)
    return r
