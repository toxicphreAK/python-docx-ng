# pyright: reportPrivateUsage=false

"""Unit test suite for the `docx.math` module — OMML equation access."""

from __future__ import annotations

import docx
from docx.oxml.ns import nsdecls
from docx.oxml.parser import parse_xml

# -- `x` superscript `2`, inline: `m:t` holds the characters, `w:t` holds none of them --
_INLINE_EQUATION = (
    "<m:oMath %s>"
    "<m:r><m:t>x</m:t></m:r>"
    "<m:sSup><m:e><m:r><m:t>2</m:t></m:r></m:e>"
    "<m:sup><m:r><m:t>n</m:t></m:r></m:sup></m:sSup>"
    "</m:oMath>"
) % nsdecls("m")

# -- the same equation displayed on its own line --
_DISPLAY_EQUATION = (
    "<m:oMathPara %s>"
    "<m:oMath><m:r><m:t>E</m:t></m:r><m:r><m:t>=</m:t></m:r>"
    "<m:r><m:t>mc</m:t></m:r></m:oMath>"
    "</m:oMathPara>"
) % nsdecls("m")


def _paragraph_with(equation_xml: str):
    document = docx.Document()
    paragraph = document.add_paragraph("The result is ")
    paragraph._p.append(parse_xml(equation_xml))
    paragraph.add_run(" for all n")
    return document, paragraph


class DescribeParagraphMath:
    """Unit-test suite for `Paragraph.math`."""

    def it_finds_an_inline_equation(self):
        _, paragraph = _paragraph_with(_INLINE_EQUATION)

        equations = paragraph.math

        assert len(equations) == 1
        assert equations[0].text == "x2n"

    def and_it_finds_a_display_equation(self):
        _, paragraph = _paragraph_with(_DISPLAY_EQUATION)

        equations = paragraph.math

        assert len(equations) == 1
        assert equations[0].text == "E=mc"

    def it_knows_whether_an_equation_is_displayed_on_its_own_line(self):
        _, inline = _paragraph_with(_INLINE_EQUATION)
        _, display = _paragraph_with(_DISPLAY_EQUATION)

        assert inline.math[0].is_display is False
        assert display.math[0].is_display is True

    def it_provides_the_omml_source(self):
        _, paragraph = _paragraph_with(_INLINE_EQUATION)

        assert paragraph.math[0].xml.startswith("<m:oMath")
        assert "<m:sSup>" in paragraph.math[0].xml

    def but_equation_text_is_not_part_of_the_paragraph_text(self):
        """A deliberate decision: `replace_text()` offsets are measured against `.text`
        and can only cut at run boundaries, so text it cannot reach would mis-target
        every later replacement in the paragraph."""
        _, paragraph = _paragraph_with(_INLINE_EQUATION)

        assert paragraph.text == "The result is  for all n"

    def and_an_equation_is_not_a_run(self):
        _, paragraph = _paragraph_with(_INLINE_EQUATION)

        assert [r.text for r in paragraph.runs] == ["The result is ", " for all n"]

    def it_is_empty_for_a_paragraph_with_no_equations(self):
        document = docx.Document()

        assert document.add_paragraph("plain").math == []


class DescribeDocumentMath:
    """Unit-test suite for `Document.math` and `BlockItemContainer.math`."""

    def it_collects_the_equations_of_the_body_in_document_order(self):
        document, _ = _paragraph_with(_INLINE_EQUATION)
        second = document.add_paragraph()
        second._p.append(parse_xml(_DISPLAY_EQUATION))

        assert [m.text for m in document.math] == ["x2n", "E=mc"]

    def it_reaches_equations_inside_a_table(self):
        document = docx.Document()
        table = document.add_table(1, 1)
        paragraph = table.cell(0, 0).paragraphs[0]
        paragraph._p.append(parse_xml(_INLINE_EQUATION))

        assert [m.text for m in document.math] == ["x2n"]

    def it_survives_a_save_and_reopen(self):
        import io

        document, _ = _paragraph_with(_INLINE_EQUATION)
        stream = io.BytesIO()
        document.save(stream)

        reopened = docx.Document(io.BytesIO(stream.getvalue()))

        assert [m.text for m in reopened.math] == ["x2n"]
