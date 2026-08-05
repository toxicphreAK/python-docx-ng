"""Custom element classes for OMML, the Office Math Markup Language.

Word stores an equation as `m:oMath`, in the math namespace rather than the
wordprocessing one. It sits among the runs of a paragraph, or inside an `m:oMathPara`
wrapper when the equation is displayed on a line of its own.

Only enough of OMML is modelled to find an equation and read its text and XML. A full
object model of the notation — fractions, radicals, matrices, delimiters, accents, some
hundreds of elements in `ref/xsd/shared-math.xsd` — is a substantially larger piece of
work, and one that would not pay for itself until there were something to render it
with.
"""

from __future__ import annotations

from typing import List

from docx.oxml.ns import qn
from docx.oxml.xmlchemy import BaseOxmlElement, ZeroOrMore


class CT_OMath(BaseOxmlElement):
    """`m:oMath` element, one equation.

    Equation text lives in `m:t` inside `m:r`, not in `w:t` inside `w:r`, so nothing
    that walks the wordprocessing run content finds it.
    """

    @property
    def text(self) -> str:
        """The concatenated text of this equation's `m:t` descendants.

        This is the equation's *characters* with none of its structure: a fraction reads
        as its numerator followed by its denominator, a superscript as the base followed
        by the exponent. It is what a plain-text extraction can offer, and is not a
        rendering of the equation.
        """
        return "".join(t.text or "" for t in self.iter(qn("m:t")))


class CT_OMathPara(BaseOxmlElement):
    """`m:oMathPara` element, a group of equations displayed on their own line.

    Holds one or more `m:oMath` children. Word writes this rather than a bare `m:oMath`
    when the equation is "display" rather than "inline".
    """

    oMath_lst: List[CT_OMath]

    oMath = ZeroOrMore("m:oMath", successors=())
