"""Run-splitting primitives and the cross-run text replacement built on them.

Word splits a paragraph into runs for reasons that have nothing to do with formatting —
spell-check state, language tagging, revision marks, the rsid bookkeeping it uses to
track editing sessions. A string a reader sees as one word is routinely three runs, so
anything that searches or edits paragraph text one run at a time misses most matches.

The primitive here is :func:`isolate_range`: given a character range measured against
`CT_P.text`, split the runs covering it so that the range is covered by whole runs and
nothing else, with each original run's `w:rPr` carried onto the pieces it was divided
into. Everything else — replacement, and reformatting a range — builds on that.

Offsets are measured in the same character space as `CT_P.text`, so `w:tab` counts as
one character and a text-wrapping `w:br` as one newline. A `w:instrText` contributes
nothing: it holds a field instruction rather than document text, and splitting one
corrupts the field.
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Iterator, List, NamedTuple, Sequence, cast

from docx.oxml.ns import qn
from docx.oxml.parser import OxmlElement
from docx.oxml.sdt import iter_run_content

if TYPE_CHECKING:
    from docx.oxml.text.paragraph import CT_P
    from docx.oxml.text.run import CT_R
    from docx.oxml.xmlchemy import BaseOxmlElement

# -- the run children that contribute characters to `CT_R.text`, in the order that
# -- property reads them. Keep in step with `CT_R.text`. --
_TEXT_CHILD_XPATH = "w:br | w:cr | w:noBreakHyphen | w:ptab | w:t | w:tab"


class _Atom(NamedTuple):
    """One text-bearing run child, located in the paragraph's character space."""

    r: CT_R
    element: BaseOxmlElement
    start: int
    text: str

    @property
    def end(self) -> int:
        return self.start + len(self.text)

    @property
    def is_divisible(self) -> bool:
        """True when this atom's text can be cut at an interior offset.

        Only `w:t` holds a string of arbitrary length. Every other text-bearing child
        maps to a fixed one-character string — a tab is one "\\t" — so a boundary can
        fall on either side of it but never inside it.
        """
        return self.element.tag == qn("w:t")


def iter_runs(element: BaseOxmlElement) -> Iterator[CT_R]:
    """Generate each `w:r` contributing text to `element`, in document order.

    A `w:hyperlink` is descended into, since its runs are part of the paragraph's text,
    and a `w:sdt` is looked through the same way :func:`iter_run_content` does.
    """
    for item in iter_run_content(element):
        if item.tag == qn("w:r"):
            yield cast("CT_R", item)
        else:  # -- a `w:hyperlink`, which holds runs of its own --
            yield from iter_runs(item)


def _iter_atoms(p: CT_P) -> Iterator[_Atom]:
    """Generate an `_Atom` for each text-bearing run child of `p`, in document order."""
    offset = 0
    for r in iter_runs(p):
        for element in r.xpath(_TEXT_CHILD_XPATH):
            text = str(element)
            yield _Atom(r, element, offset, text)
            offset += len(text)


def _set_space_preserve(t: BaseOxmlElement) -> None:
    """Add `xml:space="preserve"` to `t` when its text has significant whitespace.

    Without it an XML parser is free to collapse the leading or trailing space, which is
    how splitting a run at a word boundary silently loses the space between two words.
    """
    text = t.text or ""
    if text != text.strip():
        t.set(qn("xml:space"), "preserve")


def _divide_t(t: BaseOxmlElement, offset: int) -> BaseOxmlElement:
    """Split `t` at `offset`, returning the new `w:t` holding the text from `offset` on.

    The new element is inserted as the immediate sibling of `t`, so the run's text is
    unchanged; only its division into elements differs.
    """
    text = t.text or ""
    new_t = OxmlElement("w:t")
    new_t.text = text[offset:]
    t.text = text[:offset]
    for element in (t, new_t):
        _set_space_preserve(element)
    t.addnext(new_t)
    return new_t


def _divide_at(p: CT_P, offset: int) -> None:
    """Divide the `w:t` straddling `offset`, if one does.

    Afterwards no text-bearing element of `p` spans `offset`; the offset falls between
    two elements, or at the very start or end of the paragraph's text.
    """
    for atom in _iter_atoms(p):
        if atom.start < offset < atom.end:
            # -- only a `w:t` can be longer than one character, so only a `w:t` can be
            # -- straddled. Anything else here would mean `_TEXT_CHILD_XPATH` and the
            # -- `__str__` of a run child had drifted apart. --
            assert atom.is_divisible, f"cannot divide {atom.element.tag} at {offset}"
            _divide_t(atom.element, offset - atom.start)
            return


def _split_run_before(r: CT_R, child: BaseOxmlElement) -> CT_R:
    """Move `child` and its following siblings into a new run inserted after `r`.

    The new run gets a copy of `r`'s `w:rPr`, so the text looks exactly as it did. The
    new run is returned; `r` keeps the children preceding `child`.
    """
    new_r = cast("CT_R", OxmlElement("w:r"))
    rPr = r.rPr
    if rPr is not None:
        new_r.append(copy.deepcopy(rPr))

    # -- collect before moving; appending to `new_r` detaches from `r` and would
    # -- otherwise cut the sibling chain being walked --
    moving: List[BaseOxmlElement] = []
    sibling = child
    while sibling is not None:
        moving.append(sibling)
        sibling = sibling.getnext()
    for element in moving:
        new_r.append(element)

    r.addnext(new_r)
    return new_r


def _split_at(p: CT_P, offset: int) -> None:
    """Split runs of `p` so that no run straddles `offset`."""
    _divide_at(p, offset)
    for atom in _iter_atoms(p):
        if atom.start != offset:
            continue
        # -- `offset` starts this atom; the run needs splitting only when the atom is
        # -- not already the run's first content child --
        content = atom.r.xpath("./*[not(self::w:rPr)]")
        if content and content[0] is not atom.element:
            _split_run_before(atom.r, atom.element)
        return


def isolate_range(p: CT_P, start: int, end: int) -> List[CT_R]:
    """Split the runs of `p` so `[start, end)` is covered by whole runs, and return them.

    Each returned run lies entirely within the range, and together they cover it. The
    formatting of every original run is preserved on each piece it was divided into.

    An empty list is returned for an empty range, and for a range beyond the end of the
    paragraph's text. Raises |ValueError| for a reversed or negative range.
    """
    if start < 0 or end < start:
        raise ValueError(f"invalid character range ({start}, {end})")
    if start == end:
        return []

    _split_at(p, start)
    _split_at(p, end)

    # -- a run is in range when its atoms are; a run holding no text at all (an image,
    # -- a field character) is not part of the matched text and is left alone --
    runs: List[CT_R] = []
    for atom in _iter_atoms(p):
        if start <= atom.start and atom.end <= end and atom.r not in runs:
            runs.append(atom.r)
    return runs


def _content_elements_for(text: str) -> List[BaseOxmlElement]:
    """The run inner-content elements representing `text`.

    Tabs and newlines become `w:tab` and `w:br` exactly as they do when assigning to
    `Run.text`, so replacement text behaves the same way as text written any other way.
    """
    from docx.oxml.text.run import _RunContentAppender  # pyright: ignore[reportPrivateUsage]

    tmp_r = cast("CT_R", OxmlElement("w:r"))
    _RunContentAppender.append_to_run_from_text(tmp_r, text)
    return list(tmp_r)


def _clear_placeholder(element: BaseOxmlElement) -> None:
    """Drop `w:showingPlcHdr` from any content control containing `element`.

    A control showing its placeholder displays prompt text rather than a value; text
    written into one is a value, and leaving the flag set makes Word discard it the
    first time the control is clicked.
    """
    for sdtPr in element.xpath("ancestor::w:sdt/w:sdtPr"):
        for showingPlcHdr in sdtPr.findall(qn("w:showingPlcHdr")):
            sdtPr.remove(showingPlcHdr)


def replace_range(p: CT_P, start: int, end: int, text: str) -> None:
    """Replace the characters of `p` in `[start, end)` with `text`.

    The replacement takes the formatting of the run holding the first replaced
    character, which is what Word's own Find and Replace does and what callers expect.
    When the range spans several runs the remaining matched text is removed from each of
    them and their formatting goes with it; the runs themselves are left in place, so a
    hyperlink, bookmark or field partly covered by the range keeps its structure.
    """
    if start < 0 or end < start:
        raise ValueError(f"invalid character range ({start}, {end})")

    _divide_at(p, start)
    _divide_at(p, end)

    atoms = [a for a in _iter_atoms(p) if start <= a.start and a.end <= end and a.text]
    new_elements = _content_elements_for(text)

    if atoms:
        anchor = atoms[0].element
        for element in new_elements:
            anchor.addprevious(element)
        for atom in atoms:
            parent = atom.element.getparent()
            if parent is not None:
                parent.remove(atom.element)
        _clear_placeholder(atoms[0].r)
        return

    # -- an empty range: there is nothing to remove, only a position to insert at --
    if not new_elements:
        return
    _insert_at(p, start, new_elements)


def _insert_at(p: CT_P, offset: int, elements: Sequence[BaseOxmlElement]) -> None:
    """Insert `elements` into `p` at character `offset`.

    The insertion joins the run whose text begins at `offset`; at the end of the
    paragraph it joins the last run, so inserted text inherits the formatting of the
    text it is written next to.
    """
    for atom in _iter_atoms(p):
        if atom.start == offset and atom.text:
            for element in elements:
                atom.element.addprevious(element)
            _clear_placeholder(atom.r)
            return

    runs = list(iter_runs(p))
    r = runs[-1] if runs else cast("CT_R", p.add_r())
    for element in elements:
        r.append(element)
    _clear_placeholder(r)
