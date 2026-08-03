"""The |Field| object and the instruction builders that go with it.

A field is how Word represents anything it works out for itself: page numbers, a table
of contents, cross-references, captions that renumber, dates, and references to document
properties. Every one of those is the same feature with a different instruction string.

Word writes a field in one of two forms. A **simple field** is self-contained — the
instruction is an attribute of `w:fldSimple` and the cached result is its content::

    <w:fldSimple w:instr=" PAGE ">
      <w:r><w:t>7</w:t></w:r>
    </w:fldSimple>

A **complex field** is spread across sibling runs, delimited by field characters::

    <w:r><w:fldChar w:fldCharType="begin"/></w:r>
    <w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>
    <w:r><w:fldChar w:fldCharType="separate"/></w:r>
    <w:r><w:t>7</w:t></w:r>
    <w:r><w:fldChar w:fldCharType="end"/></w:r>

Both forms are read here and |Field| presents them the same way. Complex fields nest —
a `TOC` result is full of `PAGEREF` fields — and the nesting is tracked, so an inner
field is a field in its own right and its text also counts towards the outer field's
result.

**This library cannot compute a field result.** A table of contents added here is empty,
a `PAGE` field has no number, and a cross-reference shows nothing, because all three
depend on how Word lays the document out. Fields are written with `w:dirty="true"` so
Word refreshes them when it opens the document; setting
:attr:`.Settings.update_fields_on_open` asks it to refresh every field in the document,
which is what a generated table of contents needs. No amount of API changes this.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator, List, cast

from docx.oxml.ns import qn
from docx.oxml.parser import OxmlElement
from docx.shared import StoryChild

if TYPE_CHECKING:
    from lxml.etree import _Element  # pyright: ignore[reportPrivateUsage]

    import docx.types as t
    from docx.oxml.text.form import CT_FldChar, CT_SimpleField

# -- everything that marks or contributes to a field, in one document-order sweep.
# -- `w:t`, `w:tab` and `w:br` are here because a field's cached result is the text
# -- between its "separate" and "end" markers, wherever in the tree that falls. --
_FIELD_NODE_XPATH = ".//w:fldSimple | .//w:fldChar | .//w:instrText | .//w:t | .//w:tab | .//w:br"


class Field(StoryChild):
    """A field in a document — a page number, a table of contents, a cross-reference.

    Not constructed directly; reached through :attr:`.Paragraph.fields`,
    :attr:`.Document.fields` or as the return value of :meth:`.Paragraph.add_field`.
    """

    def __init__(
        self,
        element: CT_SimpleField | CT_FldChar,
        parent: t.ProvidesStoryPart,
        instruction: str = "",
        result_text: str = "",
    ):
        super().__init__(parent)
        self._element = element
        self._instruction = instruction
        self._result_text = result_text

    def __repr__(self) -> str:
        return f"<docx.fields.Field {self.type or '?'} {self.instruction!r}>"

    @property
    def dirty(self) -> bool:
        """True when Word will refresh this field the next time it opens the document.

        Read/write. A field written by this library is dirty by default, since its
        cached result is empty and only Word can fill it in.
        """
        return bool(self._element.dirty)

    @dirty.setter
    def dirty(self, value: bool):
        self._element.dirty = True if value else None

    @property
    def instruction(self) -> str:
        """The field instruction, e.g. ``' TOC \\\\o "1-3" \\\\h '``.

        This is the whole instruction including its switches, with the surrounding
        spaces Word writes. It is the concatenation of every `w:instrText` of a complex
        field, so an instruction Word split across runs reads as one string here.
        """
        return self._instruction

    @property
    def is_simple(self) -> bool:
        """True when this is a `w:fldSimple` rather than a complex field."""
        return self._element.tag == qn("w:fldSimple")

    @property
    def result_text(self) -> str:
        """The result Word last rendered for this field, the empty string if none.

        A field this library has just added has no result: only Word can compute one.
        """
        return self._result_text

    @property
    def text(self) -> str:
        """The text this field displays, which is its :attr:`result_text`."""
        return self._result_text

    @property
    def type(self) -> str | None:
        """The field type in upper case — ``"PAGE"``, ``"TOC"``, ``"REF"`` — or |None|.

        This is the first token of the instruction. |None| when the instruction is empty
        or begins with a switch, which is malformed but does occur.

        A plain string rather than an enumeration: ISO/IEC 29500 defines around ninety
        field types and Word accepts more, so a closed set would reject valid documents.
        """
        tokens = self._instruction.split()
        if not tokens or tokens[0].startswith("\\"):
            return None
        return tokens[0].upper()


def iter_fields(element: _Element, parent: t.ProvidesStoryPart) -> Iterator[Field]:
    """Generate a |Field| for each field in the subtree of `element`.

    Fields appear in document order, outermost first. A complex field nested inside
    another — a `PAGEREF` in a table-of-contents entry — is generated in its own right,
    after the field containing it.

    A complex field with no "end" field-character is malformed and is skipped rather
    than raising: such a document exists in the wild and reading the fields that are
    well-formed is more useful than refusing the whole document.
    """
    stack: List[_ComplexFieldBuilder] = []
    complete: List[tuple[int, Field]] = []

    for position, node in enumerate(cast("List[_Element]", element.xpath(_FIELD_NODE_XPATH))):
        tag = node.tag

        if tag == qn("w:fldSimple"):
            simple = cast("CT_SimpleField", node)
            # -- read `w:instr` off the attribute rather than through the declared
            # -- required attribute, which raises for the malformed `w:fldSimple`
            # -- lacking one; a missing instruction is an empty one here --
            instr = node.get(qn("w:instr")) or ""
            complete.append((position, Field(simple, parent, instr, simple.result_text)))
            continue

        if tag == qn("w:fldChar"):
            fldChar = cast("CT_FldChar", node)
            fldCharType = node.get(qn("w:fldCharType"))
            if fldCharType == "begin":
                stack.append(_ComplexFieldBuilder(fldChar, position))
            elif fldCharType == "separate":
                if stack:
                    stack[-1].separate_seen = True
            elif fldCharType == "end" and stack:
                builder = stack.pop()
                complete.append((builder.position, builder.build(parent)))
            continue

        if tag == qn("w:instrText"):
            # -- an instruction belongs to the innermost field that has not yet reached
            # -- its "separate"; past that point the field is showing its result --
            for builder in reversed(stack):
                if not builder.separate_seen:
                    builder.instruction_parts.append(str(node))
                    break
            continue

        # -- a text-bearing element: part of the result of every enclosing field that
        # -- has passed its "separate" marker --
        for builder in stack:
            if builder.separate_seen:
                builder.result_parts.append(str(node))

    return (field for _, field in sorted(complete, key=lambda pair: pair[0]))


class _ComplexFieldBuilder:
    """Accumulates the parts of one complex field while its subtree is walked."""

    def __init__(self, begin: CT_FldChar, position: int):
        self.begin = begin
        self.position = position
        self.separate_seen = False
        self.instruction_parts: List[str] = []
        self.result_parts: List[str] = []

    def build(self, parent: t.ProvidesStoryPart) -> Field:
        return Field(
            self.begin,
            parent,
            "".join(self.instruction_parts),
            "".join(self.result_parts),
        )


def new_complex_field(instruction: str, dirty: bool = True) -> List[_Element]:
    """The runs of a complex field for `instruction`, ready to append to a paragraph.

    No "separate" field-character is written, because there is no cached result to put
    after one; Word adds both when it computes the result. `dirty` sets `w:dirty` on the
    "begin" field-character, asking Word to refresh the field when it opens the file.
    """
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    if dirty:
        begin.set(qn("w:dirty"), "true")

    instrText = OxmlElement("w:instrText")
    instrText.set(qn("xml:space"), "preserve")
    instrText.text = instruction

    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")

    runs: List[_Element] = []
    for child in (begin, instrText, end):
        r = OxmlElement("w:r")
        r.append(child)
        runs.append(r)
    return runs


# ------------------------------------------------------------------------------------
# Instruction builders
#
# A field instruction is a small language of its own, documented in ISO/IEC 29500
# §17.16. These build the instructions people actually ask for, so that callers do not
# have to get the quoting and the switches right by hand. Any other field is reachable
# by passing its instruction to `add_field()` directly.


def _switches(*parts: str | None) -> str:
    """Join `parts`, dropping the ones that are |None|, into an instruction body."""
    return " ".join(part for part in parts if part)


def _quote(value: str) -> str:
    """`value` quoted for a field instruction if it needs to be.

    Word requires quotes around an argument containing a space, and doubles an embedded
    quote to escape it.
    """
    escaped = value.replace('"', '""')
    return f'"{escaped}"' if (escaped != value or " " in value or not value) else value


def page_number() -> str:
    """A `PAGE` field instruction — the number of the page the field is on."""
    return " PAGE "


def page_count() -> str:
    """A `NUMPAGES` field instruction — the number of pages in the document."""
    return " NUMPAGES "


def table_of_contents(
    levels: tuple[int, int] = (1, 3),
    hyperlinks: bool = True,
    use_outline_levels: bool = True,
    hide_tab_and_page_numbers_in_web: bool = True,
) -> str:
    """A `TOC` field instruction, the switches matching what Word's own dialog writes.

    `levels` is the inclusive range of heading levels to include. `hyperlinks` makes
    each entry a link to its heading (`\\h`), `use_outline_levels` includes paragraphs
    given an outline level without a heading style (`\\u`), and
    `hide_tab_and_page_numbers_in_web` is Word's `\\z`, which suppresses the leader and
    page number in web layout where there are no pages.

    The table is empty until Word builds it; see the module docstring.
    """
    first, last = levels
    if not 1 <= first <= last <= 9:
        raise ValueError(f"levels must be a range within 1-9, got {levels!r}")
    return " TOC {} ".format(
        _switches(
            f'\\o "{first}-{last}"',
            "\\h" if hyperlinks else None,
            "\\z" if hide_tab_and_page_numbers_in_web else None,
            "\\u" if use_outline_levels else None,
        )
    )


def cross_reference(
    bookmark: str, hyperlink: bool = True, insert_paragraph_number: bool = False
) -> str:
    """A `REF` field instruction referring to `bookmark`.

    `hyperlink` makes the reference clickable (`\\h`), and `insert_paragraph_number`
    shows the referenced paragraph's number rather than its text (`\\n`).

    The bookmark must exist in the document, or Word displays "Error! Bookmark not
    defined." See :meth:`.Paragraph.add_bookmark` for creating one.
    """
    return " REF {} ".format(
        _switches(
            _quote(bookmark),
            "\\h" if hyperlink else None,
            "\\n" if insert_paragraph_number else None,
        )
    )


def page_reference(bookmark: str, hyperlink: bool = True) -> str:
    """A `PAGEREF` field instruction — the page number `bookmark` appears on."""
    return " PAGEREF {} ".format(_switches(_quote(bookmark), "\\h" if hyperlink else None))


def sequence(name: str, restart_at_heading_level: int | None = None) -> str:
    """A `SEQ` field instruction — the caption numbering of the `name` series.

    `name` is the caption label, conventionally "Figure", "Table" or "Equation". Word
    numbers each series independently and renumbers the whole series when one is
    inserted, which is the point of using a field rather than a typed number.

    `restart_at_heading_level` restarts numbering at each heading of that level (`\\s`),
    giving the "Figure 3-2" style of numbering.
    """
    return " SEQ {} ".format(
        _switches(
            _quote(name),
            "\\* ARABIC",
            None if restart_at_heading_level is None else f"\\s {restart_at_heading_level}",
        )
    )


def date(format: str | None = None, save_date: bool = False) -> str:
    """A `DATE` field instruction, or `SAVEDATE` when `save_date` is |True|.

    `format` is a Word date-time picture such as ``"d MMMM yyyy"``; the document's
    default format is used when it is omitted. Note a `DATE` field shows the date the
    document was *opened*, not the date it was generated — for a fixed date, write the
    text rather than a field.
    """
    keyword = "SAVEDATE" if save_date else "DATE"
    return " {} ".format(_switches(keyword, None if format is None else f'\\@ "{format}"'))


def doc_property(name: str) -> str:
    """A `DOCPROPERTY` field instruction showing document property `name`.

    `name` is a built-in property such as ``"Title"`` or ``"Author"``, or the name of a
    custom property; see :attr:`.Document.core_properties` and
    :attr:`.Document.custom_properties`.
    """
    return f" DOCPROPERTY {_quote(name)} "


def styleref(style_name: str, search_from_bottom: bool = False) -> str:
    """A `STYLEREF` field instruction showing the nearest text in `style_name`.

    This is how a running header repeats the current chapter title.
    """
    return " STYLEREF {} ".format(
        _switches(_quote(style_name), "\\l" if search_from_bottom else None)
    )
