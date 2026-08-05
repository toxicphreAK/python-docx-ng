"""Custom element classes related to the numbering part.

The numbering model has two levels of indirection, and getting them the wrong way round
is what most reimplementations of it do:

- A paragraph's `w:numPr/w:numId` names a `w:num`, a *concrete* list instance.
- The `w:num` names a `w:abstractNum` through `w:abstractNumId`. The abstract definition
  holds the formatting of each of the nine levels: the start value, the number format
  and the level text.
- The `w:num` may carry `w:lvlOverride` children that override parts of the abstract
  definition for this instance, `w:startOverride` in particular.

Two `w:num` elements pointing at the same `w:abstractNum` are two independent sequences
that happen to look alike. That is precisely how Word restarts a list: it does not reset
a counter, it creates a second `w:num` with a `w:startOverride`.

Leaf values here are read from their `w:val` attribute rather than through registered
element classes, because the tag names are reused elsewhere in the schema with other
types — `w:start` is a table-cell border, and lxml resolves an element class by tag name
alone, so registering it would silently change the type of every table border in the
document.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, List

from docx.oxml.ns import qn
from docx.oxml.parser import OxmlElement
from docx.oxml.shared import CT_DecimalNumber
from docx.oxml.simpletypes import ST_DecimalNumber
from docx.oxml.xmlchemy import (
    BaseOxmlElement,
    OneAndOnlyOne,
    RequiredAttribute,
    ZeroOrMore,
    ZeroOrOne,
)

if TYPE_CHECKING:
    from docx.enum.numbering import WD_NUMBER_FORMAT


def _val(parent: BaseOxmlElement, tag: str) -> str | None:
    """The `w:val` attribute of the `tag` child of `parent`, or |None|.

    |None| both when the child is absent and when it carries no `w:val`.
    """
    child = parent.find(qn(tag))
    return None if child is None else child.get(qn("w:val"))


def _int_val(parent: BaseOxmlElement, tag: str) -> int | None:
    """The `w:val` of the `tag` child of `parent` as an int, or |None|."""
    val = _val(parent, tag)
    if val is None:
        return None
    try:
        return int(val)
    except ValueError:
        return None


def _set_val(parent: BaseOxmlElement, tag: str, value: object, tag_seq: tuple[str, ...]) -> None:
    """Set the `w:val` of the `tag` child of `parent`, creating it in schema order.

    Removes the child when `value` is |None|. The children here are not registered
    element classes — their tag names are reused elsewhere in the schema with other
    types — so they are created and placed by hand rather than through `ZeroOrOne`.
    """
    child = parent.find(qn(tag))
    if value is None:
        if child is not None:
            parent.remove(child)
        return
    if child is None:
        child = OxmlElement(tag)
        _insert_in_order(parent, child, tag, tag_seq)
    child.set(qn("w:val"), str(value))


def _insert_in_order(
    parent: BaseOxmlElement, child: BaseOxmlElement, tag: str, tag_seq: tuple[str, ...]
) -> None:
    """Insert `child` at the position `tag` occupies in `tag_seq`.

    `CT_Lvl` and `CT_AbstractNum` are both `xsd:sequence`, and Word rejects a document
    whose child order violates the schema.
    """
    for successor_tag in tag_seq[tag_seq.index(tag) + 1 :]:
        successor = parent.find(qn(successor_tag))
        if successor is not None:
            successor.addprevious(child)
            return
    parent.append(child)


class CT_Lvl(BaseOxmlElement):
    """`w:lvl` element, the definition of one of the nine levels of a list."""

    _tag_seq = (
        "w:start",
        "w:numFmt",
        "w:lvlRestart",
        "w:pStyle",
        "w:isLgl",
        "w:suff",
        "w:lvlText",
        "w:lvlPicBulletId",
        "w:legacy",
        "w:lvlJc",
        "w:pPr",
        "w:rPr",
    )

    ilvl: int = RequiredAttribute("w:ilvl", ST_DecimalNumber)  # pyright: ignore

    @property
    def start(self) -> int | None:
        """The number this level counts from, or |None| when it does not say.

        Word treats an unspecified start as 1.
        """
        return _int_val(self, "w:start")

    @start.setter
    def start(self, value: int | None) -> None:
        _set_val(self, "w:start", value, self._tag_seq)

    @property
    def num_fmt(self) -> WD_NUMBER_FORMAT | None:
        """Member of :ref:`WdNumberFormat` this level renders its counter as.

        |None| when the level does not say, or when it names a format outside the
        enumeration — Word accepts vendor extensions here and a document using one
        should still be readable.
        """
        from docx.enum.numbering import WD_NUMBER_FORMAT

        val = _val(self, "w:numFmt")
        if val is None:
            return None
        try:
            return WD_NUMBER_FORMAT.from_xml(val)
        except ValueError:
            return None

    @num_fmt.setter
    def num_fmt(self, value: WD_NUMBER_FORMAT | str | None) -> None:
        from docx.enum.numbering import WD_NUMBER_FORMAT

        if isinstance(value, WD_NUMBER_FORMAT):
            value = WD_NUMBER_FORMAT.to_xml(value)
        _set_val(self, "w:numFmt", value, self._tag_seq)

    @property
    def lvl_restart(self) -> int | None:
        """The one-based level whose increment restarts this one, or |None|.

        |None| means the default: this level restarts whenever any higher level
        increments. A value of 0 means it never restarts.
        """
        return _int_val(self, "w:lvlRestart")

    @lvl_restart.setter
    def lvl_restart(self, value: int | None) -> None:
        _set_val(self, "w:lvlRestart", value, self._tag_seq)

    @property
    def lvl_text(self) -> str | None:
        """The pattern this level displays, e.g. `"%1."` or `"%1.%2"`, or |None|.

        A `%n` placeholder is replaced by the counter of the one-based level `n`. For a
        bullet level the text is the bullet character itself and holds no placeholder.
        """
        return _val(self, "w:lvlText")

    @lvl_text.setter
    def lvl_text(self, value: str | None) -> None:
        _set_val(self, "w:lvlText", value, self._tag_seq)

    @property
    def is_lgl(self) -> bool:
        """True when this level renders all its placeholders as decimal.

        The "legal numbering" option, which turns "1.a.i" into "1.1.1" without changing
        the underlying formats.
        """
        isLgl = self.find(qn("w:isLgl"))
        if isLgl is None:
            return False
        val = isLgl.get(qn("w:val"))
        return val is None or val not in ("0", "false", "off")

    @is_lgl.setter
    def is_lgl(self, value: bool) -> None:
        isLgl = self.find(qn("w:isLgl"))
        if not value:
            if isLgl is not None:
                self.remove(isLgl)
            return
        if isLgl is None:
            isLgl = OxmlElement("w:isLgl")
            _insert_in_order(self, isLgl, "w:isLgl", self._tag_seq)

    @property
    def p_style(self) -> str | None:
        """The style id this level is linked to, or |None|.

        A paragraph with this style takes this numbering level even without its own
        `w:numPr`, which is how the built-in "List Number" styles work.
        """
        return _val(self, "w:pStyle")

    @p_style.setter
    def p_style(self, value: str | None) -> None:
        _set_val(self, "w:pStyle", value, self._tag_seq)

    @property
    def suffix(self) -> str | None:
        """What separates the number from the text: `"tab"`, `"space"` or `"nothing"`.

        |None| when the level does not say, which Word treats as `"tab"`. This is the
        gap between the bullet or number and the paragraph text, and setting it to
        `"space"` is the usual way to tighten up a compact list.
        """
        return _val(self, "w:suff")

    @suffix.setter
    def suffix(self, value: str | None) -> None:
        if value is not None and value not in ("tab", "space", "nothing"):
            raise ValueError(
                "suffix must be one of 'tab', 'space' or 'nothing', got %r" % value
            )
        _set_val(self, "w:suff", value, self._tag_seq)

    @property
    def jc(self) -> str | None:
        """Alignment of the number within its indent: `"left"`, `"center"`, `"right"`.

        |None| when the level does not say, which Word treats as left.
        """
        return _val(self, "w:lvlJc")

    @jc.setter
    def jc(self, value: str | None) -> None:
        _set_val(self, "w:lvlJc", value, self._tag_seq)

    @property
    def pPr(self) -> BaseOxmlElement | None:
        """The `w:pPr` of this level, or |None| when it has none.

        This is where a level's indent lives, as an ordinary `w:ind`.
        """
        return self.find(qn("w:pPr"))

    def get_or_add_pPr(self) -> BaseOxmlElement:
        """The `w:pPr` of this level, added in schema order if not already there."""
        pPr = self.pPr
        if pPr is None:
            pPr = OxmlElement("w:pPr")
            _insert_in_order(self, pPr, "w:pPr", self._tag_seq)
        return pPr

    @classmethod
    def new(cls, ilvl: int) -> CT_Lvl:
        """A new empty `w:lvl` for level `ilvl`."""
        lvl = OxmlElement("w:lvl")
        lvl.set(qn("w:ilvl"), str(ilvl))
        return lvl  # pyright: ignore[reportReturnType]


class CT_AbstractNum(BaseOxmlElement):
    """`w:abstractNum` element, the shared definition behind one or more `w:num`."""

    lvl_lst: List[CT_Lvl]

    _tag_seq = (
        "w:nsid",
        "w:multiLevelType",
        "w:tmpl",
        "w:name",
        "w:styleLink",
        "w:numStyleLink",
        "w:lvl",
    )

    lvl = ZeroOrMore("w:lvl", successors=())

    abstractNumId: int = RequiredAttribute(  # pyright: ignore[reportAssignmentType]
        "w:abstractNumId", ST_DecimalNumber
    )

    @property
    def multi_level_type(self) -> str | None:
        """`"singleLevel"`, `"multilevel"` or `"hybridMultilevel"`, or |None|."""
        return _val(self, "w:multiLevelType")

    @multi_level_type.setter
    def multi_level_type(self, value: str | None) -> None:
        valid = ("singleLevel", "multilevel", "hybridMultilevel")
        if value is not None and value not in valid:
            raise ValueError("multi_level_type must be one of %s, got %r" % (valid, value))
        _set_val(self, "w:multiLevelType", value, self._tag_seq)

    @classmethod
    def new(cls, abstract_num_id: int) -> CT_AbstractNum:
        """A new empty `w:abstractNum` with `abstract_num_id`.

        `w:nsid` and `w:tmpl` are deliberately not written. They are what Word uses to
        recognise a definition as one of its own list-gallery entries; inventing values
        for them would claim a provenance this definition does not have, and Word opens
        a document without them perfectly well.
        """
        abstractNum = OxmlElement("w:abstractNum")
        abstractNum.set(qn("w:abstractNumId"), str(abstract_num_id))
        return abstractNum  # pyright: ignore[reportReturnType]

    def add_level(self, ilvl: int) -> CT_Lvl:
        """A `w:lvl` for level `ilvl`, newly added in ascending `w:ilvl` order.

        Word rejects an abstract definition whose levels are out of order.
        """
        existing = self.lvl_having_ilvl(ilvl)
        if existing is not None:
            return existing
        lvl = CT_Lvl.new(ilvl)
        for sibling in self.lvl_lst:
            if sibling.ilvl > ilvl:
                sibling.addprevious(lvl)
                return lvl
        _insert_in_order(self, lvl, "w:lvl", self._tag_seq)
        return lvl

    @property
    def num_style_link(self) -> str | None:
        """The style id this definition defers to, or |None|.

        An abstract definition carrying this holds no levels of its own; the numbering
        actually comes from the definition the named style points at. Word writes this
        for a list style shared between several lists.
        """
        return _val(self, "w:numStyleLink")

    @property
    def style_link(self) -> str | None:
        """The style id this definition is the numbering for, or |None|."""
        return _val(self, "w:styleLink")

    def lvl_having_ilvl(self, ilvl: int) -> CT_Lvl | None:
        """The `w:lvl` child for level `ilvl`, or |None| when it has none."""
        return next(iter(self.xpath('./w:lvl[@w:ilvl="%d"]' % ilvl)), None)


class CT_Num(BaseOxmlElement):
    """``<w:num>`` element, which represents a concrete list definition instance, having
    a required child <w:abstractNumId> that references an abstract numbering definition
    that defines most of the formatting details."""

    lvlOverride_lst: List[CT_NumLvl]

    abstractNumId = OneAndOnlyOne("w:abstractNumId")
    lvlOverride = ZeroOrMore("w:lvlOverride")
    numId = RequiredAttribute("w:numId", ST_DecimalNumber)

    def add_lvlOverride(self, ilvl):
        """Return a newly added CT_NumLvl (<w:lvlOverride>) element having its ``ilvl``
        attribute set to `ilvl`."""
        return self._add_lvlOverride(ilvl=ilvl)

    def lvlOverride_having_ilvl(self, ilvl: int) -> CT_NumLvl | None:
        """The `w:lvlOverride` child for level `ilvl`, or |None| when there is none."""
        return next(iter(self.xpath('./w:lvlOverride[@w:ilvl="%d"]' % ilvl)), None)

    @classmethod
    def new(cls, num_id, abstractNum_id):
        """Return a new ``<w:num>`` element having numId of `num_id` and having a
        ``<w:abstractNumId>`` child with val attribute set to `abstractNum_id`."""
        num = OxmlElement("w:num")
        num.numId = num_id
        abstractNumId = CT_DecimalNumber.new("w:abstractNumId", abstractNum_id)
        num.append(abstractNumId)
        return num


class CT_NumLvl(BaseOxmlElement):
    """``<w:lvlOverride>`` element, which identifies a level in a list definition to
    override with settings it contains."""

    get_or_add_startOverride: Callable[[], CT_DecimalNumber]

    startOverride = ZeroOrOne("w:startOverride", successors=("w:lvl",))
    ilvl = RequiredAttribute("w:ilvl", ST_DecimalNumber)

    def add_startOverride(self, val):
        """Return a newly added CT_DecimalNumber element having tagname
        ``w:startOverride`` and ``val`` attribute set to `val`."""
        return self._add_startOverride(val=val)

    @property
    def lvl(self) -> CT_Lvl | None:
        """The `w:lvl` override of this level, or |None| when it overrides only start."""
        return self.find(qn("w:lvl"))

    @property
    def start_override(self) -> int | None:
        """The number this level counts from in this instance, or |None|."""
        return _int_val(self, "w:startOverride")


class CT_NumPr(BaseOxmlElement):
    """A ``<w:numPr>`` element, a container for numbering properties applied to a
    paragraph."""

    get_or_add_ilvl: Callable[[], CT_DecimalNumber]
    get_or_add_numId: Callable[[], CT_DecimalNumber]
    _remove_ilvl: Callable[[], None]
    _remove_numId: Callable[[], None]

    ilvl: CT_DecimalNumber | None = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "w:ilvl", successors=("w:numId", "w:numberingChange", "w:ins")
    )
    numId: CT_DecimalNumber | None = ZeroOrOne(  # pyright: ignore[reportAssignmentType]
        "w:numId", successors=("w:numberingChange", "w:ins")
    )

    @property
    def ilvl_val(self) -> int | None:
        """Value of `w:ilvl/@w:val`, or |None| when absent."""
        ilvl = self.ilvl
        return None if ilvl is None else ilvl.val

    @ilvl_val.setter
    def ilvl_val(self, value: int | None):
        if value is None:
            self._remove_ilvl()
            return
        self.get_or_add_ilvl().val = value

    @property
    def numId_val(self) -> int | None:
        """Value of `w:numId/@w:val`, or |None| when absent."""
        numId = self.numId
        return None if numId is None else numId.val

    @numId_val.setter
    def numId_val(self, value: int | None):
        if value is None:
            self._remove_numId()
            return
        self.get_or_add_numId().val = value


class CT_Numbering(BaseOxmlElement):
    """``<w:numbering>`` element, the root element of a numbering part, i.e.
    numbering.xml."""

    abstractNum_lst: List[CT_AbstractNum]
    num_lst: List[CT_Num]

    _tag_seq = ("w:numPicBullet", "w:abstractNum", "w:num", "w:numIdMacAtCleanup")
    abstractNum = ZeroOrMore("w:abstractNum", successors=_tag_seq[2:])
    num = ZeroOrMore("w:num", successors=_tag_seq[3:])
    del _tag_seq

    def add_num(self, abstractNum_id):
        """Return a newly added CT_Num (<w:num>) element referencing the abstract
        numbering definition identified by `abstractNum_id`."""
        next_num_id = self._next_numId
        num = CT_Num.new(next_num_id, abstractNum_id)
        return self._insert_num(num)

    def abstractNum_having_abstractNumId(self, abstractNumId: int) -> CT_AbstractNum | None:
        """The `w:abstractNum` child with `abstractNumId`, or |None| if not found."""
        xpath = './w:abstractNum[@w:abstractNumId="%d"]' % abstractNumId
        return next(iter(self.xpath(xpath)), None)

    def num_having_numId(self, numId):
        """Return the ``<w:num>`` child element having ``numId`` attribute matching
        `numId`."""
        xpath = './w:num[@w:numId="%d"]' % numId
        try:
            return self.xpath(xpath)[0]
        except IndexError:
            raise KeyError("no <w:num> element with numId %d" % numId)

    @property
    def _next_numId(self):
        """The first ``numId`` unused by a ``<w:num>`` element, starting at 1 and
        filling any gaps in numbering between existing ``<w:num>`` elements."""
        numId_strs = self.xpath("./w:num/@w:numId")
        num_ids = [int(numId_str) for numId_str in numId_strs]
        for num in range(1, len(num_ids) + 2):
            if num not in num_ids:
                break
        return num
