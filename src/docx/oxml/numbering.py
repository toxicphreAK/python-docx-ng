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

    @property
    def lvl_restart(self) -> int | None:
        """The one-based level whose increment restarts this one, or |None|.

        |None| means the default: this level restarts whenever any higher level
        increments. A value of 0 means it never restarts.
        """
        return _int_val(self, "w:lvlRestart")

    @property
    def lvl_text(self) -> str | None:
        """The pattern this level displays, e.g. `"%1."` or `"%1.%2"`, or |None|.

        A `%n` placeholder is replaced by the counter of the one-based level `n`. For a
        bullet level the text is the bullet character itself and holds no placeholder.
        """
        return _val(self, "w:lvlText")

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

    @property
    def p_style(self) -> str | None:
        """The style id this level is linked to, or |None|.

        A paragraph with this style takes this numbering level even without its own
        `w:numPr`, which is how the built-in "List Number" styles work.
        """
        return _val(self, "w:pStyle")


class CT_AbstractNum(BaseOxmlElement):
    """`w:abstractNum` element, the shared definition behind one or more `w:num`."""

    lvl_lst: List[CT_Lvl]

    lvl = ZeroOrMore("w:lvl", successors=())

    abstractNumId: int = RequiredAttribute(  # pyright: ignore[reportAssignmentType]
        "w:abstractNumId", ST_DecimalNumber
    )

    @property
    def multi_level_type(self) -> str | None:
        """`"singleLevel"`, `"multilevel"` or `"hybridMultilevel"`, or |None|."""
        return _val(self, "w:multiLevelType")

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
