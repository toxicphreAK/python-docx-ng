"""The list-numbering API — reading the number a list paragraph displays, and restarting.

The number a reader sees against a list paragraph — "1.", "a)", "iii." — is nowhere in
the document body. Word computes it from `numbering.xml` at display time, so anything
converting a document to text, Markdown or HTML has to compute it too. That computation
is :func:`compute_list_numbers`, and it is the part of this module worth being careful
about; the rest is a straightforward model over the numbering part.

The model mirrors the two-level indirection described in :mod:`docx.oxml.numbering`: a
|NumberingDefinition| is a `w:num`, a concrete list, and it resolves each of its nine
|NumberingLevel| objects from the `w:abstractNum` it points at, with any `w:lvlOverride`
of its own applied on top.

Restarting a list means creating a second `w:num` on the same `w:abstractNum` carrying a
`w:startOverride`, not resetting a counter; see :meth:`.Paragraph.restart_numbering`.

What is not computed here: a level whose format is one of the locale-specific ones —
Japanese counting, Korean chosung and the rest — falls back to decimal, because
rendering those correctly is a localisation problem rather than a document-model one.
:attr:`.NumberingLevel.is_renderable` says which is which.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Iterator, List, Mapping, Sequence, Tuple

from docx.enum.numbering import WD_NUMBER_FORMAT
from docx.oxml.ns import qn
from docx.shared import ElementProxy, Length

if TYPE_CHECKING:
    from docx.oxml.numbering import CT_AbstractNum, CT_Lvl, CT_Num, CT_Numbering
    from docx.oxml.text.paragraph import CT_P
    from docx.parts.document import DocumentPart

# -- the nine levels OOXML allows a list to have --
_MAX_LEVELS = 9

# -- how far the `w:numStyleLink` / `w:styleLink` indirection is followed before it is
# -- treated as a cycle. Word tolerates a chain; a document with a loop exists. --
_MAX_STYLE_LINK_DEPTH = 10

_ROMAN = (
    (1000, "M"),
    (900, "CM"),
    (500, "D"),
    (400, "CD"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
)

# -- the Chicago Manual of Style footnote-mark sequence, which repeats after four --
_CHICAGO = ("*", "†", "‡", "§")

# -- the formats `format_number` renders; anything else falls back to decimal --
_RENDERABLE = frozenset(
    (
        WD_NUMBER_FORMAT.DECIMAL,
        WD_NUMBER_FORMAT.DECIMAL_ZERO,
        WD_NUMBER_FORMAT.DECIMAL_HALF_WIDTH,
        WD_NUMBER_FORMAT.UPPER_ROMAN,
        WD_NUMBER_FORMAT.LOWER_ROMAN,
        WD_NUMBER_FORMAT.UPPER_LETTER,
        WD_NUMBER_FORMAT.LOWER_LETTER,
        WD_NUMBER_FORMAT.ORDINAL,
        WD_NUMBER_FORMAT.HEX,
        WD_NUMBER_FORMAT.CHICAGO,
        WD_NUMBER_FORMAT.BULLET,
        WD_NUMBER_FORMAT.NONE,
    )
)


def _to_roman(value: int) -> str:
    if value <= 0:
        return str(value)
    out: List[str] = []
    for magnitude, numeral in _ROMAN:
        count, value = divmod(value, magnitude)
        out.append(numeral * count)
    return "".join(out)


def _to_letter(value: int) -> str:
    """Word's letter sequence: A..Z, then AA, BB, CC — not AA, AB, AC.

    This surprises people, but it is what Word displays and what the specification
    describes, so matching it is the point.
    """
    if value <= 0:
        return str(value)
    index, repeat = (value - 1) % 26, (value - 1) // 26 + 1
    return chr(ord("A") + index) * repeat


def _to_ordinal(value: int) -> str:
    if 11 <= (value % 100) <= 13:
        return f"{value}th"
    return f"{value}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(value % 10, 'th') }"


class NumberingLevel:
    """One of the nine levels of a list, with any instance overrides applied.

    Reached through :attr:`.NumberingDefinition.levels` or
    :meth:`.NumberingDefinition.level`.
    """

    def __init__(self, ilvl: int, lvl: CT_Lvl | None, start_override: int | None = None):
        self._ilvl = ilvl
        self._lvl = lvl
        self._start_override = start_override

    def __repr__(self) -> str:
        return f"<docx.numbering.NumberingLevel ilvl={self._ilvl} text={self.level_text!r}>"

    @property
    def ilvl(self) -> int:
        """The zero-based level number, 0 being the outermost."""
        return self._ilvl

    @property
    def is_bullet(self) -> bool:
        """True when this level shows a bullet rather than a number."""
        return self.number_format == WD_NUMBER_FORMAT.BULLET

    @property
    def is_renderable(self) -> bool:
        """True when :meth:`format_number` can render this level's format faithfully.

        |False| for the locale-specific formats, where `format_number` falls back to
        decimal. Worth checking before presenting a computed number as authoritative.
        """
        return self.number_format in _RENDERABLE

    @property
    def level_text(self) -> str:
        """The pattern this level displays, e.g. `"%1."`.

        A `%n` is the counter of one-based level `n`. Defaults to `"%{ilvl+1}."`, which
        is what Word shows for a level that does not say.
        """
        if self._lvl is not None and self._lvl.lvl_text is not None:
            return self._lvl.lvl_text
        return "%%%d." % (self._ilvl + 1)

    @property
    def number_format(self) -> WD_NUMBER_FORMAT:
        """Member of :ref:`WdNumberFormat` this level renders its counter as.

        `DECIMAL` when the level does not say, which is Word's default.
        """
        if self._lvl is not None:
            num_fmt = self._lvl.num_fmt
            if num_fmt is not None:
                return num_fmt
        return WD_NUMBER_FORMAT.DECIMAL

    @property
    def restart_after_level(self) -> int | None:
        """The one-based level whose increment restarts this one.

        |None| means Word's default: restart whenever any higher level increments. 0
        means never restart.
        """
        return None if self._lvl is None else self._lvl.lvl_restart

    @property
    def start(self) -> int:
        """The number this level counts from.

        A `w:startOverride` on the concrete list wins over the abstract definition's
        `w:start`, which is how a restarted list begins again at 1. Defaults to 1.
        """
        if self._start_override is not None:
            return self._start_override
        if self._lvl is not None and self._lvl.start is not None:
            return self._lvl.start
        return 1

    @property
    def style_id(self) -> str | None:
        """The paragraph style linked to this level, or |None|.

        A paragraph with this style takes this level even with no `w:numPr` of its own.
        """
        return None if self._lvl is None else self._lvl.p_style

    @property
    def is_legal(self) -> bool:
        """True when this level renders every placeholder as decimal.

        Word's "legal numbering" option, which turns "1.a.i" into "1.1.1".
        """
        return False if self._lvl is None else self._lvl.is_lgl

    @property
    def suffix(self) -> str:
        """What separates the number from the text: `"tab"`, `"space"` or `"nothing"`.

        `"tab"` when the level does not say, which is Word's default.
        """
        if self._lvl is not None and self._lvl.suffix is not None:
            return self._lvl.suffix
        return "tab"

    @property
    def indent(self) -> Length | None:
        """The left indent this level applies, or |None| when it sets none."""
        pPr = None if self._lvl is None else self._lvl.pPr
        if pPr is None:
            return None
        return pPr.ind_left  # pyright: ignore[reportAttributeAccessIssue]

    @property
    def hanging_indent(self) -> Length | None:
        """The hanging indent this level applies, or |None| when it sets none.

        This is what keeps the wrapped text of a list item lined up under the first
        line rather than under the bullet.
        """
        pPr = None if self._lvl is None else self._lvl.pPr
        if pPr is None:
            return None
        first_line = pPr.first_line_indent  # pyright: ignore[reportAttributeAccessIssue]
        return None if first_line is None or first_line >= 0 else Length(-first_line)

    def set(
        self,
        *,
        start: int | None = None,
        number_format: WD_NUMBER_FORMAT | str | None = None,
        level_text: str | None = None,
        suffix: str | None = None,
        alignment: str | None = None,
        indent: Length | None = None,
        hanging_indent: Length | None = None,
        restart_after_level: int | None = None,
        style_id: str | None = None,
        is_legal: bool | None = None,
    ) -> NumberingLevel:
        """Change this level's definition; return self for chaining.

        Only the arguments given are written, so a call sets what it names and leaves
        the rest of the level alone::

            level.set(number_format=WD_NUMBER_FORMAT.LOWER_LETTER, level_text="%2)")

        The change is made to the *abstract* definition, which is shared: every list
        pointing at it changes with it. Use :meth:`.Numbering.add_definition` for a list
        of your own rather than editing a definition the document already had.

        Raises |ValueError| for a level that has no definition to write to — one of the
        nine levels an abstract definition does not define.
        """
        if self._lvl is None:
            raise ValueError(
                "level %d has no definition in this list; only levels the abstract"
                " definition defines can be changed" % self._ilvl
            )
        lvl = self._lvl

        if start is not None:
            lvl.start = start
        if number_format is not None:
            lvl.num_fmt = number_format
        if level_text is not None:
            lvl.lvl_text = level_text
        if suffix is not None:
            lvl.suffix = suffix
        if alignment is not None:
            lvl.jc = alignment
        if restart_after_level is not None:
            lvl.lvl_restart = restart_after_level
        if style_id is not None:
            lvl.p_style = style_id
        if is_legal is not None:
            lvl.is_lgl = is_legal
        if indent is not None or hanging_indent is not None:
            pPr = lvl.get_or_add_pPr()
            if indent is not None:
                pPr.ind_left = indent  # pyright: ignore[reportAttributeAccessIssue]
            if hanging_indent is not None:
                # -- a hanging indent is a negative first-line indent, which is how
                # -- `CT_PPr.first_line_indent` already spells it --
                pPr.first_line_indent = Length(  # pyright: ignore[reportAttributeAccessIssue]
                    -hanging_indent
                )
        return self

    def format_number(self, value: int) -> str:
        """`value` rendered in this level's number format.

        Falls back to decimal for a format this library does not render; see
        :attr:`is_renderable`.
        """
        fmt = self.number_format
        if fmt == WD_NUMBER_FORMAT.UPPER_ROMAN:
            return _to_roman(value)
        if fmt == WD_NUMBER_FORMAT.LOWER_ROMAN:
            return _to_roman(value).lower()
        if fmt == WD_NUMBER_FORMAT.UPPER_LETTER:
            return _to_letter(value)
        if fmt == WD_NUMBER_FORMAT.LOWER_LETTER:
            return _to_letter(value).lower()
        if fmt == WD_NUMBER_FORMAT.ORDINAL:
            return _to_ordinal(value)
        if fmt == WD_NUMBER_FORMAT.HEX:
            return format(value, "X")
        if fmt == WD_NUMBER_FORMAT.DECIMAL_ZERO:
            return f"{value:02d}"
        if fmt == WD_NUMBER_FORMAT.CHICAGO:
            return _CHICAGO[(value - 1) % len(_CHICAGO)] if value > 0 else str(value)
        if fmt == WD_NUMBER_FORMAT.NONE:
            return ""
        return str(value)


class NumberingDefinition:
    """A concrete list — a `w:num` — and the levels it resolves to.

    Two definitions pointing at the same abstract definition are two independent
    sequences that happen to look alike; that is how a restarted list is represented.
    """

    def __init__(self, num: CT_Num, numbering: Numbering):
        self._num = num
        self._numbering = numbering

    def __repr__(self) -> str:
        return f"<docx.numbering.NumberingDefinition num_id={self.num_id}>"

    @property
    def abstract_num_id(self) -> int | None:
        """The id of the abstract definition this list takes its formatting from."""
        abstractNumId = self._num.abstractNumId
        return None if abstractNumId is None else abstractNumId.val

    @property
    def num_id(self) -> int:
        """The id a paragraph's `w:numPr/w:numId` refers to this list by."""
        return self._num.numId

    @property
    def levels(self) -> List[NumberingLevel]:
        """The nine levels of this list, outermost first."""
        return [self.level(ilvl) for ilvl in range(_MAX_LEVELS)]

    def level(self, ilvl: int) -> NumberingLevel:
        """The level `ilvl` of this list, with any instance override applied.

        A level the definition says nothing about is still returned, carrying Word's
        defaults, because a paragraph can legitimately refer to it.
        """
        abstract = self._abstract_num
        lvl = None if abstract is None else abstract.lvl_having_ilvl(ilvl)

        start_override = None
        lvlOverride = self._num.lvlOverride_having_ilvl(ilvl)
        if lvlOverride is not None:
            start_override = lvlOverride.start_override
            if lvlOverride.lvl is not None:
                lvl = lvlOverride.lvl

        return NumberingLevel(ilvl, lvl, start_override)

    @property
    def _abstract_num(self) -> CT_AbstractNum | None:
        """The `w:abstractNum` this list resolves to, following `w:numStyleLink`.

        An abstract definition carrying `w:numStyleLink` holds no levels of its own and
        defers to the definition the named style points at. The chain is followed to a
        bounded depth so a document containing a loop does not hang.
        """
        abstract_num_id = self.abstract_num_id
        if abstract_num_id is None:
            return None
        abstract = self._numbering._element.abstractNum_having_abstractNumId(abstract_num_id)

        for _ in range(_MAX_STYLE_LINK_DEPTH):
            if abstract is None:
                return None
            style_id = abstract.num_style_link
            if style_id is None:
                return abstract
            linked = self._numbering._abstract_num_for_style_link(style_id)
            if linked is None or linked is abstract:
                return abstract
            abstract = linked
        return abstract


class Numbering(ElementProxy):
    """The numbering definitions of a document.

    Reached through :attr:`.Document.numbering`. Supports ``len()``, iteration over the
    concrete list definitions, and lookup by `num_id`.
    """

    def __init__(self, numbering: CT_Numbering, part: DocumentPart):
        super().__init__(numbering)
        self._element = numbering
        self._part = part

    def __iter__(self) -> Iterator[NumberingDefinition]:
        return (NumberingDefinition(num, self) for num in self._element.num_lst)

    def __len__(self) -> int:
        return len(self._element.num_lst)

    def get(self, num_id: int) -> NumberingDefinition | None:
        """The list definition with `num_id`, or |None| when there is none."""
        try:
            num = self._element.num_having_numId(num_id)
        except KeyError:
            return None
        return NumberingDefinition(num, self)

    def add_definition(
        self,
        levels: Sequence[Mapping[str, object]] | None = None,
        *,
        multi_level_type: str | None = None,
    ) -> NumberingDefinition:
        """Define a new list and return it.

        Until now a list could be *applied* and *restarted* but not defined, so a format
        the template did not already contain — `1)` where the template has `1.`, a
        custom bullet character, a particular per-level indent — meant hand-building
        `w:abstractNum` XML::

            definition = document.numbering.add_definition([
                {"number_format": WD_NUMBER_FORMAT.DECIMAL, "level_text": "%1)"},
                {"number_format": WD_NUMBER_FORMAT.LOWER_LETTER, "level_text": "%2)"},
            ])
            paragraph.set_numbering(definition.num_id, level=0)

        `levels` is one mapping per level, outermost first, of the keyword arguments
        :meth:`.NumberingLevel.set` takes. A level given as an empty mapping takes the
        defaults. With `levels` of |None| the definition gets nine decimal levels, which
        is what Word's plain numbered list is; :meth:`add_bulleted_definition` and
        :meth:`add_numbered_definition` are the shorthands for the two common cases.

        `multi_level_type` is written to `w:multiLevelType` when given; Word uses it to
        decide how to present the list in its gallery and is content without it.

        A fresh `w:abstractNum` and a `w:num` pointing at it are created, both with ids
        free in this document. `w:nsid` and `w:tmpl` are deliberately not written — they
        are what Word uses to recognise a definition as one of its own gallery entries,
        and inventing values would claim a provenance this definition does not have.

        Raises |ValueError| for more than nine levels, which is all OOXML admits.
        """
        from docx.oxml.numbering import CT_AbstractNum

        if levels is None:
            levels = [{} for _ in range(_MAX_LEVELS)]
        elif len(levels) > _MAX_LEVELS:
            raise ValueError(
                "a list definition has at most %d levels, got %d"
                % (_MAX_LEVELS, len(levels))
            )

        abstract = CT_AbstractNum.new(self._next_abstract_num_id())
        self._insert_abstract_num(abstract)
        if multi_level_type is not None:
            abstract.multi_level_type = multi_level_type

        for ilvl, spec in enumerate(levels):
            lvl = abstract.add_level(ilvl)
            NumberingLevel(ilvl, lvl).set(
                **{
                    "number_format": WD_NUMBER_FORMAT.DECIMAL,
                    "level_text": "%%%d." % (ilvl + 1),
                    "start": 1,
                    **spec,  # pyright: ignore[reportArgumentType]
                }
            )

        num = self._element.add_num(abstract.abstractNumId)
        return NumberingDefinition(num, self)

    def add_numbered_definition(
        self,
        depth: int = 9,
        *,
        formats: Sequence[WD_NUMBER_FORMAT] | None = None,
        indent_step: Length | None = None,
    ) -> NumberingDefinition:
        """Define a decimal-with-sublevels list and return it.

        The tedious half of :meth:`add_definition` is assembling nine levels by hand, so
        this does it: each level shows its own counter followed by a period, in the
        format `formats` gives it, indented `indent_step` further than the level above.

        `formats` cycles when it is shorter than `depth`; the default of decimal, lower
        letter and lower roman is Word's familiar 1. / a. / i. alternation. For the
        cumulative "1.1.1" style, pass `levels` to :meth:`add_definition` with
        `level_text` of ``"%1.%2."`` and so on. `indent_step` defaults to a quarter
        inch, which is what Word uses.

        Raises |ValueError| for a `depth` above nine, as :meth:`add_definition` does.
        """
        from docx.shared import Inches

        if formats is None:
            formats = (
                WD_NUMBER_FORMAT.DECIMAL,
                WD_NUMBER_FORMAT.LOWER_LETTER,
                WD_NUMBER_FORMAT.LOWER_ROMAN,
            )
        step = Inches(0.25) if indent_step is None else indent_step

        levels: List[Dict[str, object]] = []
        for ilvl in range(depth):
            levels.append(
                {
                    "number_format": formats[ilvl % len(formats)],
                    "level_text": "%%%d." % (ilvl + 1),
                    "start": 1,
                    "indent": Length(step * (ilvl + 2)),
                    "hanging_indent": step,
                }
            )
        return self.add_definition(levels, multi_level_type="multilevel")

    def add_bulleted_definition(
        self,
        depth: int = 9,
        *,
        bullets: Sequence[str] = ("•", "o", "§"),
        indent_step: Length | None = None,
    ) -> NumberingDefinition:
        """Define a bulleted list and return it.

        `bullets` cycles when it is shorter than `depth`; the default is Word's own
        bullet, circle and square sequence. `indent_step` defaults to a quarter inch.
        Raises |ValueError| for a `depth` above nine.

        Note the bullet characters Word writes are glyphs of the Symbol and Wingdings
        fonts rather than the Unicode characters they resemble. The defaults here are
        the Unicode ones, which render in whatever font the paragraph uses and so do not
        depend on a font being installed.
        """
        from docx.shared import Inches

        step = Inches(0.25) if indent_step is None else indent_step

        levels: List[Dict[str, object]] = []
        for ilvl in range(depth):
            levels.append(
                {
                    "number_format": WD_NUMBER_FORMAT.BULLET,
                    "level_text": bullets[ilvl % len(bullets)],
                    "indent": Length(step * (ilvl + 2)),
                    "hanging_indent": step,
                }
            )
        return self.add_definition(levels, multi_level_type="hybridMultilevel")

    def _next_abstract_num_id(self) -> int:
        """The first unused `w:abstractNum/@w:abstractNumId` in this part."""
        used = {abstract.abstractNumId for abstract in self._element.abstractNum_lst}
        candidate = 0
        while candidate in used:
            candidate += 1
        return candidate

    def _insert_abstract_num(self, abstract: CT_AbstractNum) -> None:
        """Place `abstract` after the last `w:abstractNum` and before the first `w:num`.

        `CT_Numbering` is an `xsd:sequence`: every `w:abstractNum` precedes every
        `w:num`, and Word rejects a document that has them the other way round.
        """
        for child in self._element:
            if child.tag == qn("w:num"):
                child.addprevious(abstract)
                return
        self._element.append(abstract)

    def restart(self, num_id: int, ilvl: int = 0, start: int = 1) -> NumberingDefinition:
        """Return a new list definition restarting the list `num_id` at `start`.

        The new definition points at the same abstract definition, so it looks identical,
        and carries a `w:startOverride` for level `ilvl`. Assign its :attr:`num_id` to a
        paragraph to make the list begin again there; :meth:`.Paragraph.restart_numbering`
        does that in one step.

        Raises |KeyError| if `num_id` names no list.
        """
        source = self.get(num_id)
        if source is None:
            raise KeyError(f"no numbering definition with num_id {num_id}")
        abstract_num_id = source.abstract_num_id
        if abstract_num_id is None:
            raise KeyError(f"numbering definition {num_id} names no abstract definition")

        num = self._element.add_num(abstract_num_id)
        num.add_lvlOverride(ilvl).add_startOverride(start)
        return NumberingDefinition(num, self)

    def _abstract_num_for_style_link(self, style_id: str) -> CT_AbstractNum | None:
        """The abstract definition whose `w:styleLink` is `style_id`, or |None|.

        Resolved by matching `w:styleLink` directly rather than through the styles part:
        the style named by a `w:numStyleLink` is a list style whose whole purpose is to
        point back here, so the round trip through `styles.xml` adds nothing.
        """
        for abstract in self._element.abstractNum_lst:
            if abstract.style_link == style_id:
                return abstract
        return None


class ParagraphNumbering:
    """The list membership of a paragraph — which list it is in, and at what level.

    Reached through :attr:`.Paragraph.numbering`, which is |None| for a paragraph that
    is not in a list at all.
    """

    def __init__(self, num_id: int, level: int, numbering: Numbering, from_style: bool):
        self._num_id = num_id
        self._level = level
        self._numbering = numbering
        self._from_style = from_style

    def __repr__(self) -> str:
        return f"<docx.numbering.ParagraphNumbering num_id={self._num_id} level={self._level}>"

    @property
    def definition(self) -> NumberingDefinition | None:
        """The list this paragraph belongs to, |None| if `num_id` names none."""
        return self._numbering.get(self._num_id)

    @property
    def from_style(self) -> bool:
        """True when this numbering comes from the paragraph's style, not the paragraph.

        A paragraph numbered through its style has no `w:numPr` of its own, so changing
        its level means giving it one.
        """
        return self._from_style

    @property
    def level(self) -> int:
        """The zero-based list level of this paragraph, 0 being the outermost."""
        return self._level

    @property
    def level_definition(self) -> NumberingLevel | None:
        """The |NumberingLevel| governing this paragraph, |None| if unresolvable."""
        definition = self.definition
        return None if definition is None else definition.level(self._level)

    @property
    def num_id(self) -> int:
        """The id of the list this paragraph belongs to."""
        return self._num_id


def get_paragraph_numbering(p: CT_P, part: DocumentPart) -> Tuple[int, int, bool] | None:
    """`(num_id, ilvl, from_style)` for `p`, or |None| when it is not in a list.

    A direct `w:pPr/w:numPr` on the paragraph wins. Failing that the paragraph's style
    hierarchy is walked — a style's own `w:numPr`, then the style it is based on — which
    is how the built-in "List Number" and "List Bullet" styles number a paragraph that
    carries no numbering markup at all.

    `w:numId` of 0 means "explicitly not numbered" and is honoured as such: Word uses it
    to switch numbering off for a paragraph whose style would otherwise apply it.
    """
    pPr = p.pPr
    if pPr is not None:
        numPr = pPr.numPr
        if numPr is not None:
            num_id = numPr.numId_val
            if num_id is not None:
                if num_id == 0:
                    return None
                return num_id, numPr.ilvl_val or 0, False

    style_id = p.style
    if style_id is None:
        return None
    resolved = _numbering_from_style(style_id, part)
    if resolved is None:
        return None
    num_id, ilvl = resolved
    if num_id == 0:
        return None
    return num_id, ilvl, True


def _numbering_from_style(style_id: str, part: DocumentPart) -> Tuple[int, int] | None:
    """`(num_id, ilvl)` the style `style_id` applies, or |None|.

    Walks the `w:basedOn` chain, since a style based on "List Number" inherits its
    numbering. The walk is bounded: a `w:basedOn` cycle is invalid but does occur.
    """
    styles = part.styles._element  # pyright: ignore[reportPrivateUsage]
    seen: List[str] = []

    while style_id is not None and style_id not in seen:
        seen.append(style_id)
        style = styles.get_by_id(style_id)
        if style is None:
            return None
        pPr = style.pPr
        if pPr is not None and pPr.numPr is not None:
            num_id = pPr.numPr.numId_val
            if num_id is not None:
                return num_id, pPr.numPr.ilvl_val or 0
        style_id = style.basedOn_val  # pyright: ignore[reportAssignmentType]

    return None


def compute_list_numbers(paragraphs: Iterator[CT_P], part: DocumentPart) -> List[Tuple[CT_P, str]]:
    """`(paragraph_element, number)` for each numbered paragraph, in document order.

    `paragraphs` must be every paragraph of the story in document order, since a list
    number depends on everything before it. Paragraphs that are not in a list contribute
    no entry.

    The elements are returned rather than used as dictionary keys because an lxml element
    proxy is created on demand and may be collected and its `id()` reused; holding the
    element in the result is what keeps the association valid.

    The counters follow ISO/IEC 29500 §17.9. For each numbered paragraph the counter of
    its own level increments, and every deeper level is restarted — unless its
    `w:lvlRestart` says otherwise, where 0 means never restart and *n* means restart only
    when the one-based level *n* increments. Counters are kept per `w:num` rather than
    per abstract definition, which is what makes two lists sharing a definition count
    independently and what makes a `w:startOverride` restart work.
    """
    if not part.has_numbering_part:
        # -- no numbering part means no list can resolve; say so without adding one --
        return []
    numbering = Numbering(part.numbering_part.element, part)

    # -- counters[num_id][ilvl] is the last number shown at that level. A level absent
    # -- from the dict has not started yet and takes its `start` value next. --
    counters: Dict[int, Dict[int, int]] = {}
    numbers: List[Tuple[CT_P, str]] = []

    for p in paragraphs:
        resolved = get_paragraph_numbering(p, part)
        if resolved is None:
            continue
        num_id, ilvl, _ = resolved

        definition = numbering.get(num_id)
        if definition is None:
            continue

        level = definition.level(ilvl)
        list_counters = counters.setdefault(num_id, {})

        if ilvl in list_counters:
            list_counters[ilvl] += 1
        else:
            list_counters[ilvl] = level.start

        _restart_deeper_levels(definition, list_counters, ilvl)
        numbers.append((p, _render(definition, level, list_counters, ilvl)))

    return numbers


def _restart_deeper_levels(
    definition: NumberingDefinition, counters: Dict[int, int], ilvl: int
) -> None:
    """Drop the counters of every level deeper than `ilvl` that restarts under it.

    Dropping rather than resetting is deliberate: a level that has not appeared since
    its restart should take its `start` value when it next does, and `start` is not
    always 1.
    """
    for deeper in range(ilvl + 1, _MAX_LEVELS):
        if deeper not in counters:
            continue
        restart_after = definition.level(deeper).restart_after_level
        if restart_after == 0:
            continue  # -- this level never restarts --
        if restart_after is None or restart_after - 1 >= ilvl:
            # -- default: restart under any higher level. Explicit `n`: restart only
            # -- when the one-based level `n` (zero-based n-1) increments or above. --
            del counters[deeper]


def _render(
    definition: NumberingDefinition,
    level: NumberingLevel,
    counters: Dict[int, int],
    ilvl: int,
) -> str:
    """The text `level` displays with `counters` in their current state.

    Each `%n` in the level text is replaced by the counter of one-based level `n`,
    rendered in *that* level's format — a "1.a.i" pattern takes the format of each level
    it names, not of the level being displayed. Under legal numbering every placeholder
    is decimal instead.
    """
    text = level.level_text
    if level.is_bullet or "%" not in text:
        return text

    out: List[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == "%" and index + 1 < len(text) and text[index + 1].isdigit():
            placeholder = int(text[index + 1])
            out.append(_counter_text(definition, level, counters, placeholder - 1, ilvl))
            index += 2
            continue
        out.append(char)
        index += 1
    return "".join(out)


def _counter_text(
    definition: NumberingDefinition,
    level: NumberingLevel,
    counters: Dict[int, int],
    placeholder_ilvl: int,
    ilvl: int,
) -> str:
    """The rendered counter for `placeholder_ilvl` within the text of level `ilvl`."""
    if not 0 <= placeholder_ilvl < _MAX_LEVELS:
        return ""
    if placeholder_ilvl > ilvl:
        # -- a level text referring to a level deeper than its own; Word shows nothing --
        return ""

    placeholder_level = definition.level(placeholder_ilvl)
    value = counters.get(placeholder_ilvl, placeholder_level.start)
    if level.is_legal:
        return str(value)
    return placeholder_level.format_number(value)


def iter_story_paragraphs(element) -> Iterator[CT_P]:
    """Generate every `w:p` in `element` in document order, tables included.

    List numbering counts paragraphs in the order Word lays them out, and a numbered
    paragraph inside a table cell counts towards the same list as one outside it.
    """
    for p in element.iter(qn("w:p")):
        yield p
