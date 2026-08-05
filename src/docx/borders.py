"""The border-edge proxy objects shared by tables, cells, paragraphs and pages.

Four containers in WordprocessingML carry a set of border edges — `w:tblBorders`,
`w:tcBorders`, `w:pBdr` and `w:pgBorders` — and they differ only in which edges they
admit and where the element lives. The mapping proxy and the per-edge proxy are defined
here once so all four spell the same; each container supplies its own small subclass
naming its edges and saying how to reach its element.
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Mapping
from typing import TYPE_CHECKING, Iterator

from docx.shared import RGBColor

if TYPE_CHECKING:
    from docx.enum.table import WD_LINE_STYLE
    from docx.oxml.table import (
        CT_Border,
        _CT_BordersBase,  # pyright: ignore[reportPrivateUsage]
    )
    from docx.shared import Length


class _Border:
    """One border edge of a table, cell, paragraph or page, e.g. `table.borders["top"]`.

    A border edge that is not set has |None| for every property, meaning the effective
    appearance of that edge is inherited from the style hierarchy. Assigning to any
    property other than :attr:`line` on an edge that is not set creates it with a line
    style of `WD_LINE_STYLE.SINGLE`, because a border with no line style is not valid
    XML. Assigning |None| to :attr:`line` removes the edge entirely.
    """

    def __init__(self, borders: _Borders, edge: str):
        self._borders = borders
        self._edge = edge

    @property
    def color(self) -> RGBColor | None:
        """|RGBColor| of this border edge, or |None| when it has no explicit color.

        As for |ColorFormat|, a border whose color is the automatic color reads as
        |None|; Word chooses that color at render time, so there is no RGB value to
        report.
        """
        border = self._element
        if border is None:
            return None
        color = border.color
        if not isinstance(color, RGBColor):
            return None
        return color

    @color.setter
    def color(self, value: RGBColor | None):
        if value is None:
            border = self._element
            if border is not None:
                border.color = None
            return
        self._get_or_add_element().color = value

    @property
    def line(self) -> WD_LINE_STYLE | None:
        """Member of :ref:`WdLineStyle`, or |None| when this edge is not set."""
        border = self._element
        return None if border is None else border.val

    @line.setter
    def line(self, value: WD_LINE_STYLE | None):
        if value is None:
            self._borders._remove_edge(self._edge)  # pyright: ignore[reportPrivateUsage]
            return
        self._get_or_add_element().val = value

    @property
    def size(self) -> Length | None:
        """Width of this border line, or |None| when it has no explicit width.

        The underlying `w:sz` attribute counts eighths of a point, so an assigned value
        is rounded to the nearest eighth of a point.
        """
        border = self._element
        return None if border is None else border.sz

    @size.setter
    def size(self, value: Length | None):
        if value is None:
            border = self._element
            if border is not None:
                border.sz = None
            return
        self._get_or_add_element().sz = value

    @property
    def space(self) -> Length | None:
        """Offset of this border from the content it surrounds, or |None| when not set.

        The underlying `w:space` attribute counts whole points, so an assigned value is
        rounded to the nearest point.
        """
        border = self._element
        return None if border is None else border.space

    @space.setter
    def space(self, value: Length | None):
        if value is None:
            border = self._element
            if border is not None:
                border.space = None
            return
        self._get_or_add_element().space = value

    @property
    def _element(self) -> CT_Border | None:
        """The `w:{edge}` element for this edge, or |None| when this edge is not set."""
        borders = self._borders._element  # pyright: ignore[reportPrivateUsage]
        return None if borders is None else borders.get_border(self._edge)

    def _get_or_add_element(self) -> CT_Border:
        """The `w:{edge}` element for this edge, adding it if not already present."""
        borders = self._borders._get_or_add_element()  # pyright: ignore[reportPrivateUsage]
        return borders.get_or_add_border(self._edge)


class _Borders(Mapping[str, _Border]):
    """The border edges of a table, cell, paragraph or page, keyed by edge name.

    A read-only mapping in the sense that the set of keys is fixed; the |_Border| object
    each key maps to is what you assign through::

        table.borders["top"].line = WD_LINE_STYLE.SINGLE

    Every edge admitted by the schema is always a key, whether or not it is set, so
    iterating yields edges with a :attr:`_Border.line` of |None| as well.

    Edge names are the local names used in the XML. A table admits `top`, `start`,
    `left`, `bottom`, `end`, `right`, `insideH` and `insideV`; a cell adds `tl2br` and
    `tr2bl`; a paragraph has `top`, `left`, `bottom`, `right`, `between` and `bar`; a
    page has the plain four. Word writes `left` and `right` for a left-to-right table
    and `start` and `end` for a right-to-left one.
    """

    def __init__(self, edges: tuple[str, ...]):
        self._edges = edges

    def __getitem__(self, edge: str) -> _Border:
        if edge not in self._edges:
            raise KeyError(
                "no border edge '%s'; must be one of %s" % (edge, ", ".join(self._edges))
            )
        return _Border(self, edge)

    def __iter__(self) -> Iterator[str]:
        return iter(self._edges)

    def __len__(self) -> int:
        return len(self._edges)

    @abstractmethod
    def clear(self) -> None:
        """Remove every border edge, restoring inheritance from the style hierarchy."""

    @property
    @abstractmethod
    def _element(self) -> _CT_BordersBase | None:
        """The borders element itself, or |None| when it is not present."""

    @abstractmethod
    def _get_or_add_element(self) -> _CT_BordersBase:
        """The borders element, adding it and any required ancestor if not present."""

    def _remove_edge(self, edge: str) -> None:
        """Remove the `w:{edge}` child, and the borders element if that empties it.

        An element carrying attributes of its own is kept even with no edges left —
        `w:pgBorders` holds `w:offsetFrom` and friends, which are settings the caller
        made deliberately and did not ask to remove.
        """
        borders = self._element
        if borders is None:
            return
        borders.remove_border(edge)
        if len(borders) == 0 and not borders.attrib:
            self.clear()
