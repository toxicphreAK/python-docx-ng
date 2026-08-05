"""The |Math| proxy, giving access to the equations in a document."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator, List

from docx.oxml.ns import qn
from docx.shared import StoryChild

if TYPE_CHECKING:
    import docx.types as t
    from docx.oxml.math import CT_OMath
    from docx.oxml.xmlchemy import BaseOxmlElement


class Math(StoryChild):
    """Proxy for an `m:oMath` element, one equation.

    Reached through :attr:`.Paragraph.math` or :attr:`.Document.math`.

    Word stores equations in OMML, a notation of its own with no overlap with the
    wordprocessing run content. This exposes the equation's XML and the characters in
    it; it deliberately does not model the notation, which would be a substantially
    larger piece of work with nothing to render the result.
    """

    def __init__(self, oMath: CT_OMath, parent: t.ProvidesStoryPart):
        super().__init__(parent)
        self._element = oMath
        self._oMath = oMath

    @property
    def text(self) -> str:
        """The characters of this equation, with none of its structure.

        A fraction reads as its numerator followed by its denominator, a superscript as
        its base followed by its exponent. This is what a plain-text extraction can
        offer; it is not a rendering of the equation and will not round-trip.
        """
        return self._oMath.text

    @property
    def xml(self) -> str:
        """The OMML source of this equation.

        The reliable representation, and what to hand to anything that understands OMML
        — an XSLT to MathML, say.
        """
        return self._oMath.xml

    @property
    def is_display(self) -> bool:
        """|True| when this equation is displayed on a line of its own.

        Word wraps a display equation in an `m:oMathPara`; an inline one sits directly
        among the runs of its paragraph.
        """
        parent = self._oMath.getparent()
        return parent is not None and parent.tag == qn("m:oMathPara")


def iter_math(element: BaseOxmlElement, parent: t.ProvidesStoryPart) -> Iterator[Math]:
    """Generate a |Math| for each equation under `element`, in document order.

    Both the inline `m:oMath` and the `m:oMath` children of a display `m:oMathPara` are
    found, and each is yielded once.
    """
    for oMath in element.iter(qn("m:oMath")):
        yield Math(oMath, parent)  # pyright: ignore[reportArgumentType]


def math_list(element: BaseOxmlElement, parent: t.ProvidesStoryPart) -> List[Math]:
    """The equations under `element`, in document order."""
    return list(iter_math(element, parent))
