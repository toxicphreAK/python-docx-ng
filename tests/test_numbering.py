"""Unit test suite for the docx.numbering module."""

from __future__ import annotations

import io
from typing import List, Tuple

import pytest

import docx
from docx.enum.numbering import WD_NUMBER_FORMAT
from docx.numbering import NumberingLevel
from docx.oxml.ns import nsdecls, qn
from docx.oxml.parser import parse_xml


def _lvl_xml(ilvl: int, fmt: str, text: str, start: int = 1, extra: str = "") -> str:
    return (
        f'<w:lvl w:ilvl="{ilvl}"><w:start w:val="{start}"/>{extra}'
        f'<w:numFmt w:val="{fmt}"/><w:lvlText w:val="{text}"/></w:lvl>'
    )


def _document_with_list(*lvl_xml: str) -> Tuple[docx.document.Document, int]:
    """A document carrying an abstract definition of `lvl_xml`, and its `num_id`."""
    document = docx.Document()
    numbering = document.numbering._element
    numbering.insert(
        0,
        parse_xml(
            f'<w:abstractNum {nsdecls("w")} w:abstractNumId="100">'
            f'<w:multiLevelType w:val="multilevel"/>{"".join(lvl_xml)}</w:abstractNum>'
        ),
    )
    return document, numbering.add_num(100).numId


def _numbers(document: docx.document.Document) -> List[str]:
    return [number for _, number in document.list_numbers]


class DescribeNumberFormatting:
    """Unit-test suite for `NumberingLevel.format_number`."""

    @pytest.mark.parametrize(
        ("fmt", "values", "expected"),
        [
            (WD_NUMBER_FORMAT.DECIMAL, [1, 9, 10], ["1", "9", "10"]),
            (WD_NUMBER_FORMAT.DECIMAL_ZERO, [1, 9, 10], ["01", "09", "10"]),
            (WD_NUMBER_FORMAT.UPPER_ROMAN, [1, 4, 9, 14, 1990], ["I", "IV", "IX", "XIV", "MCMXC"]),
            (WD_NUMBER_FORMAT.LOWER_ROMAN, [1, 4, 9], ["i", "iv", "ix"]),
            # -- Word's letter sequence repeats the letter rather than counting in
            # -- base 26: after Z comes AA, then BB --
            (WD_NUMBER_FORMAT.UPPER_LETTER, [1, 26, 27, 28], ["A", "Z", "AA", "BB"]),
            (WD_NUMBER_FORMAT.LOWER_LETTER, [1, 26, 27], ["a", "z", "aa"]),
            (
                WD_NUMBER_FORMAT.ORDINAL,
                [1, 2, 3, 4, 11, 12, 13, 21],
                ["1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st"],
            ),
            (WD_NUMBER_FORMAT.HEX, [10, 15, 16], ["A", "F", "10"]),
            (WD_NUMBER_FORMAT.CHICAGO, [1, 2, 4, 5], ["*", "†", "§", "*"]),
            (WD_NUMBER_FORMAT.NONE, [1, 2], ["", ""]),
        ],
    )
    def it_renders_the_format(self, fmt: WD_NUMBER_FORMAT, values: List[int], expected: List[str]):
        lvl = parse_xml(
            f'<w:lvl {nsdecls("w")} w:ilvl="0"><w:numFmt w:val="{fmt.xml_value}"/></w:lvl>'
        )
        level = NumberingLevel(0, lvl)

        assert [level.format_number(v) for v in values] == expected

    def it_falls_back_to_decimal_for_a_format_it_cannot_render(self):
        lvl = parse_xml(
            f'<w:lvl {nsdecls("w")} w:ilvl="0"><w:numFmt w:val="japaneseCounting"/></w:lvl>'
        )
        level = NumberingLevel(0, lvl)

        assert level.number_format == WD_NUMBER_FORMAT.JAPANESE_COUNTING
        assert level.is_renderable is False
        assert level.format_number(3) == "3"

    def it_tolerates_a_number_format_outside_the_enumeration(self):
        """Word accepts vendor extensions; the document should stay readable."""
        lvl = parse_xml(f'<w:lvl {nsdecls("w")} w:ilvl="0"><w:numFmt w:val="vendorish"/></w:lvl>')
        level = NumberingLevel(0, lvl)

        assert level.number_format == WD_NUMBER_FORMAT.DECIMAL


class DescribeNumberingLevel:
    """Unit-test suite for `docx.numbering.NumberingLevel`."""

    def it_defaults_to_words_own_defaults(self):
        level = NumberingLevel(2, None)

        assert level.start == 1
        assert level.number_format == WD_NUMBER_FORMAT.DECIMAL
        assert level.level_text == "%3."
        assert level.restart_after_level is None
        assert level.is_bullet is False

    def it_prefers_a_start_override_to_the_abstract_start(self):
        lvl = parse_xml(f'<w:lvl {nsdecls("w")} w:ilvl="0"><w:start w:val="5"/></w:lvl>')

        assert NumberingLevel(0, lvl).start == 5
        assert NumberingLevel(0, lvl, start_override=1).start == 1

    def it_knows_a_bullet_level(self):
        lvl = parse_xml(
            f'<w:lvl {nsdecls("w")} w:ilvl="0"><w:numFmt w:val="bullet"/>'
            '<w:lvlText w:val="•"/></w:lvl>'
        )
        level = NumberingLevel(0, lvl)

        assert level.is_bullet is True
        assert level.level_text == "•"


class DescribeParagraphNumbering:
    """Unit-test suite for `docx.text.paragraph.Paragraph.numbering`."""

    def it_is_none_for_a_paragraph_not_in_a_list(self):
        document = docx.Document()

        assert document.add_paragraph("plain").numbering is None

    def it_resolves_numbering_applied_by_the_paragraph_style(self):
        """This is how "List Number" numbers a paragraph with no numbering markup."""
        document = docx.Document()

        paragraph = document.add_paragraph("one", style="List Number")

        assert paragraph.numbering is not None
        assert paragraph.numbering.from_style is True
        assert paragraph.numbering.level == 0
        assert paragraph._p.xpath("./w:pPr/w:numPr") == [], "the style carries it"

    def it_prefers_numbering_applied_directly_to_the_paragraph(self):
        document, num_id = _document_with_list(_lvl_xml(0, "decimal", "%1."))
        paragraph = document.add_paragraph("one", style="List Number")

        paragraph.set_numbering(num_id, level=2)

        assert paragraph.numbering.num_id == num_id
        assert paragraph.numbering.level == 2
        assert paragraph.numbering.from_style is False

    def it_resolves_numbering_through_a_based_on_style_chain(self):
        document = docx.Document()
        derived = document.styles.add_style("Derived", docx.enum.style.WD_STYLE_TYPE.PARAGRAPH)
        derived.base_style = document.styles["List Number"]

        paragraph = document.add_paragraph("one", style="Derived")

        assert paragraph.numbering is not None
        assert paragraph.numbering.from_style is True

    def it_treats_a_num_id_of_zero_as_not_numbered(self):
        """Word writes numId 0 to switch a style's numbering off for one paragraph."""
        document = docx.Document()
        paragraph = document.add_paragraph("one", style="List Number")

        paragraph.remove_numbering()

        assert paragraph.numbering is None
        assert paragraph._p.xpath("./w:pPr/w:numPr/w:numId")[0].get(qn("w:val")) == "0"

    def it_removes_direct_numbering_outright(self):
        document, num_id = _document_with_list(_lvl_xml(0, "decimal", "%1."))
        paragraph = document.add_paragraph("one")
        paragraph.set_numbering(num_id)

        paragraph.remove_numbering()

        assert paragraph.numbering is None
        assert paragraph._p.xpath("./w:pPr/w:numPr") == []

    def it_exposes_the_level_definition_governing_the_paragraph(self):
        document, num_id = _document_with_list(
            _lvl_xml(0, "decimal", "%1."), _lvl_xml(1, "lowerLetter", "%2)", start=3)
        )
        paragraph = document.add_paragraph("x")
        paragraph.set_numbering(num_id, level=1)

        level = paragraph.numbering.level_definition
        assert level.number_format == WD_NUMBER_FORMAT.LOWER_LETTER
        assert level.start == 3


class DescribeComputedListNumbers:
    """Unit-test suite for the computed list number."""

    def it_numbers_a_simple_list(self):
        document = docx.Document()
        for text in ("one", "two", "three"):
            document.add_paragraph(text, style="List Number")

        assert _numbers(document) == ["1.", "2.", "3."]

    def it_skips_paragraphs_that_are_not_in_a_list(self):
        document = docx.Document()
        document.add_paragraph("intro")
        document.add_paragraph("one", style="List Number")
        document.add_paragraph("aside")
        document.add_paragraph("two", style="List Number")

        assert [(p.text, n) for p, n in document.list_numbers] == [("one", "1."), ("two", "2.")]

    def it_restarts_a_deeper_level_under_a_higher_one(self):
        document, num_id = _document_with_list(
            _lvl_xml(0, "decimal", "%1."), _lvl_xml(1, "decimal", "%2)")
        )
        for level in (0, 1, 1, 0, 1):
            document.add_paragraph("x").set_numbering(num_id, level)

        assert _numbers(document) == ["1.", "1)", "2)", "2.", "1)"]

    def it_honors_lvl_restart_of_zero_as_never_restart(self):
        document, num_id = _document_with_list(
            _lvl_xml(0, "decimal", "%1."),
            _lvl_xml(1, "decimal", "%2)", extra='<w:lvlRestart w:val="0"/>'),
        )
        for level in (0, 1, 1, 0, 1):
            document.add_paragraph("x").set_numbering(num_id, level)

        assert _numbers(document) == ["1.", "1)", "2)", "2.", "3)"]

    def it_composes_a_multi_level_pattern_from_each_levels_format(self):
        """A "%1.%2.%3" pattern takes each level's own format, not the deepest one."""
        document, num_id = _document_with_list(
            _lvl_xml(0, "decimal", "%1."),
            _lvl_xml(1, "lowerLetter", "%2."),
            _lvl_xml(2, "lowerRoman", "%1.%2.%3"),
        )
        for level in (0, 1, 1, 2, 2):
            document.add_paragraph("x").set_numbering(num_id, level)

        assert _numbers(document) == ["1.", "a.", "b.", "1.b.i", "1.b.ii"]

    def it_starts_at_the_levels_start_value(self):
        document, num_id = _document_with_list(_lvl_xml(0, "upperLetter", "%1)", start=5))
        for _ in range(3):
            document.add_paragraph("x").set_numbering(num_id, 0)

        assert _numbers(document) == ["E)", "F)", "G)"]

    def it_renders_a_bullet_level_as_its_literal_text(self):
        document, num_id = _document_with_list(_lvl_xml(0, "bullet", "•"))
        for _ in range(2):
            document.add_paragraph("x").set_numbering(num_id, 0)

        assert _numbers(document) == ["•", "•"]

    def it_renders_legal_numbering_as_all_decimal(self):
        document, num_id = _document_with_list(
            _lvl_xml(0, "decimal", "%1."),
            _lvl_xml(1, "lowerLetter", "%1.%2", extra="<w:isLgl/>"),
        )
        for level in (0, 1):
            document.add_paragraph("x").set_numbering(num_id, level)

        assert _numbers(document) == ["1.", "1.1"], "the lowerLetter level shows as decimal"

    def it_counts_two_lists_on_the_same_definition_independently(self):
        """This is what makes a restarted list a separate sequence."""
        document, num_id_a = _document_with_list(_lvl_xml(0, "decimal", "%1."))
        num_id_b = document.numbering._element.add_num(100).numId

        document.add_paragraph("a1").set_numbering(num_id_a, 0)
        document.add_paragraph("b1").set_numbering(num_id_b, 0)
        document.add_paragraph("a2").set_numbering(num_id_a, 0)

        assert _numbers(document) == ["1.", "1.", "2."]

    def it_counts_paragraphs_inside_tables(self):
        document, num_id = _document_with_list(_lvl_xml(0, "decimal", "%1."))
        document.add_paragraph("one").set_numbering(num_id, 0)
        cell = document.add_table(rows=1, cols=1).cell(0, 0)
        cell.paragraphs[0].text = "two"
        cell.paragraphs[0].set_numbering(num_id, 0)

        assert _numbers(document) == ["1.", "2."]

    def it_is_empty_for_a_document_with_no_lists(self):
        document = docx.Document()
        document.add_paragraph("plain")

        assert document.list_numbers == []

    def it_does_not_add_a_numbering_part_that_was_absent(self):
        """The bundled template happens to have one; a document in the wild may not."""
        document = docx.Document()
        rIds = [rId for rId, rel in document.part.rels.items() if "numbering" in rel.reltype]
        for rId in rIds:
            document.part.drop_rel(rId)
        document.part.__dict__.pop("numbering_part", None)
        assert document.part.has_numbering_part is False

        document.add_paragraph("one", style="List Number")

        assert document.list_numbers == []
        assert document.part.has_numbering_part is False

    def it_agrees_with_the_per_paragraph_property(self):
        document = docx.Document()
        document.add_paragraph("intro")
        for text in ("one", "two"):
            document.add_paragraph(text, style="List Number")

        assert [p.list_number for p in document.paragraphs] == [None, "1.", "2."]


class DescribeRestartNumbering:
    """Unit-test suite for `docx.text.paragraph.Paragraph.restart_numbering`."""

    def it_restarts_the_list_from_that_paragraph_on(self):
        document, num_id = _document_with_list(_lvl_xml(0, "decimal", "%1."))
        for text in ("a", "b", "c", "d"):
            document.add_paragraph(text).set_numbering(num_id, 0)
        third = document.paragraphs[2]

        third.restart_numbering()

        assert _numbers(document) == ["1.", "2.", "1.", "2."]

    def it_creates_a_new_definition_rather_than_resetting_a_counter(self):
        document, num_id = _document_with_list(_lvl_xml(0, "decimal", "%1."))
        for text in ("a", "b"):
            document.add_paragraph(text).set_numbering(num_id, 0)

        new_num_id = document.paragraphs[1].restart_numbering()

        assert new_num_id != num_id
        new_definition = document.numbering.get(new_num_id)
        assert new_definition.abstract_num_id == 100, "same look, separate sequence"
        assert new_definition.level(0).start == 1

    def it_can_restart_at_a_number_other_than_one(self):
        document, num_id = _document_with_list(_lvl_xml(0, "decimal", "%1."))
        for text in ("a", "b", "c"):
            document.add_paragraph(text).set_numbering(num_id, 0)

        document.paragraphs[1].restart_numbering(start=10)

        assert _numbers(document) == ["1.", "10.", "11."]

    def it_keeps_each_repointed_paragraphs_own_level(self):
        document, num_id = _document_with_list(
            _lvl_xml(0, "decimal", "%1."), _lvl_xml(1, "decimal", "%2)")
        )
        for level in (0, 0, 1):
            document.add_paragraph("x").set_numbering(num_id, level)

        document.paragraphs[1].restart_numbering()

        assert [p.numbering.level for p in document.paragraphs] == [0, 0, 1]
        assert _numbers(document) == ["1.", "1.", "1)"]

    def it_raises_for_a_paragraph_not_in_a_list(self):
        document = docx.Document()

        with pytest.raises(ValueError, match="not in a list"):
            document.add_paragraph("plain").restart_numbering()


class DescribeNumberingCollection:
    """Unit-test suite for `docx.numbering.Numbering`."""

    def it_supports_len_iteration_and_lookup(self):
        document, num_id = _document_with_list(_lvl_xml(0, "decimal", "%1."))

        numbering = document.numbering
        assert len(numbering) >= 1
        assert num_id in [d.num_id for d in numbering]
        assert numbering.get(num_id).abstract_num_id == 100

    def it_returns_none_for_an_unknown_num_id(self):
        assert docx.Document().numbering.get(9999) is None

    def it_raises_when_restarting_an_unknown_list(self):
        with pytest.raises(KeyError, match="no numbering definition"):
            docx.Document().numbering.restart(9999)

    def it_resolves_a_num_style_link_to_the_definition_holding_the_levels(self):
        """An abstract definition with `w:numStyleLink` holds no levels of its own."""
        document = docx.Document()
        numbering = document.numbering._element
        numbering.insert(
            0,
            parse_xml(
                f'<w:abstractNum {nsdecls("w")} w:abstractNumId="200">'
                '<w:styleLink w:val="MyListStyle"/>'
                f"{_lvl_xml(0, 'upperRoman', '%1.')}</w:abstractNum>"
            ),
        )
        numbering.insert(
            1,
            parse_xml(
                f'<w:abstractNum {nsdecls("w")} w:abstractNumId="201">'
                '<w:numStyleLink w:val="MyListStyle"/></w:abstractNum>'
            ),
        )
        num_id = numbering.add_num(201).numId

        level = document.numbering.get(num_id).level(0)
        assert level.number_format == WD_NUMBER_FORMAT.UPPER_ROMAN

    def it_survives_a_round_trip(self):
        document, num_id = _document_with_list(_lvl_xml(0, "lowerRoman", "%1)"))
        for text in ("a", "b"):
            document.add_paragraph(text).set_numbering(num_id, 0)

        stream = io.BytesIO()
        document.save(stream)
        stream.seek(0)

        assert _numbers(docx.Document(stream)) == ["i)", "ii)"]
