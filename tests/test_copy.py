# pyright: reportPrivateUsage=false

"""Unit test suite for `copy_to()` on paragraphs, runs, rows and tables."""

from __future__ import annotations

import io

import pytest

import docx
from docx.oxml.ns import qn
from docx.shared import Inches

from .unitutil.file import test_file

_IMAGE = test_file("monty-truth.png")


def _reopened(document):
    stream = io.BytesIO()
    document.save(stream)
    return docx.Document(io.BytesIO(stream.getvalue()))


class DescribeParagraphCopyTo:
    """Unit-test suite for `Paragraph.copy_to()`."""

    def it_copies_the_text_and_formatting(self):
        document = docx.Document()
        paragraph = document.add_paragraph("hello", style="Heading 1")
        paragraph.add_run(" bold").bold = True

        copy = paragraph.copy_to(document)

        assert copy.text == "hello bold"
        assert copy.style.name == "Heading 1"
        assert copy.runs[1].bold is True

    def and_the_original_is_untouched(self):
        document = docx.Document()
        paragraph = document.add_paragraph("hello")

        paragraph.copy_to(document)

        assert paragraph.text == "hello"
        assert len(document.paragraphs) == 2

    def it_appends_by_default(self):
        document = docx.Document()
        first = document.add_paragraph("one")
        document.add_paragraph("two")

        first.copy_to(document)

        assert [p.text for p in document.paragraphs] == ["one", "two", "one"]

    def it_can_place_the_copy_before_an_existing_paragraph(self):
        document = docx.Document()
        first = document.add_paragraph("one")
        second = document.add_paragraph("two")

        first.copy_to(document, before=second)

        assert [p.text for p in document.paragraphs] == ["one", "one", "two"]

    def and_after_one(self):
        document = docx.Document()
        first = document.add_paragraph("one")
        document.add_paragraph("two")

        first.copy_to(document, after=first)

        assert [p.text for p in document.paragraphs] == ["one", "one", "two"]

    def it_rejects_both_before_and_after(self):
        document = docx.Document()
        paragraph = document.add_paragraph("one")

        with pytest.raises(ValueError, match="at most one"):
            paragraph.copy_to(document, before=paragraph, after=paragraph)

    def it_can_copy_into_a_table_cell(self):
        document = docx.Document()
        paragraph = document.add_paragraph("hello")
        cell = document.add_table(1, 1).cell(0, 0)

        paragraph.copy_to(cell)

        assert [p.text for p in cell.paragraphs] == ["", "hello"]

    def it_appends_before_a_trailing_sectPr(self):
        """A `w:sectPr` must stay last in the body or Word repairs the document."""
        document = docx.Document()
        paragraph = document.add_paragraph("one")

        paragraph.copy_to(document)

        body = document._body._element
        assert body[-1].tag == qn("w:sectPr")


class DescribeCopyRelationshipRemapping:
    """The half a hand-written deep copy gets wrong."""

    def it_keeps_a_copied_picture_pointing_at_the_right_image(self):
        document = docx.Document()
        paragraph = document.add_paragraph()
        paragraph.add_run().add_picture(_IMAGE, width=Inches(1))

        copy = paragraph.copy_to(document)

        assert len(document.inline_shapes) == 2
        embeds = copy._p.xpath(".//a:blip/@r:embed")
        assert len(embeds) == 1
        assert document.part.rels[embeds[0]].target_part.image.content_type == "image/png"

    def and_within_one_document_the_media_is_not_duplicated(self):
        document = docx.Document()
        paragraph = document.add_paragraph()
        paragraph.add_run().add_picture(_IMAGE)

        paragraph.copy_to(document)

        assert len(document.images) == 1

    def and_across_documents_the_image_comes_with_it(self):
        source = docx.Document()
        paragraph = source.add_paragraph()
        paragraph.add_run().add_picture(_IMAGE)
        destination = docx.Document()

        paragraph.copy_to(destination)

        assert len(destination.images) == 1
        reopened = _reopened(destination)
        assert reopened.inline_shapes[0].image is not None
        assert reopened.inline_shapes[0].image.content_type == "image/png"

    def it_reassigns_the_drawing_id(self):
        """`wp:docPr/@id` must be unique document-wide."""
        document = docx.Document()
        paragraph = document.add_paragraph()
        paragraph.add_run().add_picture(_IMAGE)

        copy = paragraph.copy_to(document)

        original_id = paragraph._p.xpath(".//wp:docPr/@id")[0]
        copy_id = copy._p.xpath(".//wp:docPr/@id")[0]
        assert original_id != copy_id

    def it_remaps_a_hyperlink_across_documents(self):
        source = docx.Document()
        paragraph = source.add_paragraph()
        paragraph.add_hyperlink("link", "https://example.com/")
        destination = docx.Document()

        copy = paragraph.copy_to(destination)

        rId = copy._p.xpath("./w:hyperlink/@r:id")[0]
        assert destination.part.rels[rId].target_ref == "https://example.com/"
        assert destination.part.rels[rId].is_external is True

    def it_drops_bookmarks_rather_than_duplicating_their_names(self):
        """A duplicate bookmark name is a second bookmark competing for references."""
        document = docx.Document()
        paragraph = document.add_paragraph("text")
        paragraph.add_bookmark("Target")

        copy = paragraph.copy_to(document)

        assert copy._p.xpath(".//w:bookmarkStart") == []
        assert [b.name for b in document.bookmarks] == ["Target"]


class DescribeCrossDocumentCopy:
    """Copying into a different document has to resolve what the content refers to."""

    def it_brings_a_missing_style_across_with_its_closure(self):
        source = docx.Document()
        paragraph = source.add_paragraph("quoted", style="Quote")
        destination = docx.Document()
        destination.styles.remove_unused()
        assert "Quote" not in destination.styles

        copy = paragraph.copy_to(destination)

        assert "Quote" in destination.styles
        # -- `Quote Char` is the `w:link` of `Quote` and comes with it --
        assert "Quote Char" in destination.styles
        assert copy.style.name == "Quote"

    def it_can_drop_the_style_reference_instead(self):
        source = docx.Document()
        paragraph = source.add_paragraph("quoted", style="Quote")
        destination = docx.Document()
        destination.styles.remove_unused()

        copy = paragraph.copy_to(destination, missing_style="drop")

        assert "Quote" not in destination.styles
        assert copy.style.name == "Normal"

    def it_can_raise_instead(self):
        source = docx.Document()
        paragraph = source.add_paragraph("quoted", style="Quote")
        destination = docx.Document()
        destination.styles.remove_unused()

        with pytest.raises(ValueError, match="no style with id"):
            paragraph.copy_to(destination, missing_style="raise")

    def it_rejects_an_unknown_policy(self):
        document = docx.Document()
        paragraph = document.add_paragraph("x")

        with pytest.raises(ValueError, match="missing_style must be one of"):
            paragraph.copy_to(document, missing_style="nonsense")

    def it_carries_numbering_across_and_repoints_it(self):
        """Leaving the numId alone joins whatever list holds that id here."""
        source = docx.Document()
        paragraph = source.add_paragraph("item")
        paragraph.set_numbering(1, level=0)
        source_num_id = paragraph.numbering.num_id
        destination = docx.Document()

        copy = paragraph.copy_to(destination)

        assert copy.numbering is not None
        assert destination.numbering.get(copy.numbering.num_id) is not None
        # -- the definition was copied rather than the id reused --
        assert copy.numbering.num_id != source_num_id or (
            destination.numbering.get(copy.numbering.num_id) is not None
        )

    def and_the_result_survives_a_save(self):
        source = docx.Document()
        paragraph = source.add_paragraph("item", style="Quote")
        paragraph.set_numbering(1, level=0)
        destination = docx.Document()

        paragraph.copy_to(destination)
        reopened = _reopened(destination)

        assert reopened.paragraphs[0].text == "item"
        assert reopened.paragraphs[0].style.name == "Quote"
        assert reopened.paragraphs[0].numbering is not None

    def it_leaves_a_style_the_destination_already_has_alone(self):
        source = docx.Document()
        paragraph = source.add_paragraph("q", style="Quote")
        destination = docx.Document()
        before = len(destination.styles)

        copy = paragraph.copy_to(destination)

        assert len(destination.styles) == before
        assert copy.style.name == "Quote"


class DescribeRunCopyTo:
    """Unit-test suite for `Run.copy_to()`."""

    def it_copies_a_run_into_a_paragraph(self):
        document = docx.Document()
        paragraph = document.add_paragraph()
        run = paragraph.add_run("x")
        run.bold = True

        copy = run.copy_to(paragraph)

        assert paragraph.text == "xx"
        assert copy.bold is True

    def it_can_place_the_copy_before_an_existing_run(self):
        document = docx.Document()
        paragraph = document.add_paragraph()
        first = paragraph.add_run("a")
        second = paragraph.add_run("b")

        second.copy_to(paragraph, before=first)

        assert paragraph.text == "bab"

    def and_after_one(self):
        document = docx.Document()
        paragraph = document.add_paragraph()
        first = paragraph.add_run("a")
        paragraph.add_run("b")

        first.copy_to(paragraph, after=first)

        assert paragraph.text == "aab"

    def it_can_copy_into_another_paragraph(self):
        document = docx.Document()
        source_paragraph = document.add_paragraph()
        run = source_paragraph.add_run("x")
        target = document.add_paragraph("before ")

        run.copy_to(target)

        assert target.text == "before x"


class DescribeRowCopyTo:
    """Unit-test suite for `_Row.copy_to()` — duplicating a template row."""

    def it_copies_a_row_into_its_own_table(self):
        document = docx.Document()
        table = document.add_table(1, 2)
        table.cell(0, 0).text = "a"
        table.cell(0, 1).text = "b"

        copy = table.rows[0].copy_to(table)

        assert len(table.rows) == 2
        assert [c.text for c in copy.cells] == ["a", "b"]

    def it_can_be_repeated_to_fill_a_table(self):
        document = docx.Document()
        table = document.add_table(1, 1)
        template = table.rows[0]

        for _ in range(9):
            template.copy_to(table)

        assert len(table.rows) == 10

    def it_can_place_the_copy_before_an_existing_row(self):
        document = docx.Document()
        table = document.add_table(2, 1)
        table.cell(0, 0).text = "first"
        table.cell(1, 0).text = "second"

        table.rows[1].copy_to(table, before=table.rows[0])

        assert [r.cells[0].text for r in table.rows] == ["second", "first", "second"]

    def it_keeps_the_row_formatting(self):
        document = docx.Document()
        table = document.add_table(1, 1)
        table.rows[0].repeat_as_header = True

        copy = table.rows[0].copy_to(table)

        assert copy.repeat_as_header is True


class DescribeTableCopyTo:
    """Unit-test suite for `Table.copy_to()`."""

    def it_copies_a_table_into_a_document(self):
        document = docx.Document()
        table = document.add_table(2, 2, style="Table Grid")
        table.cell(0, 0).text = "a"

        copy = table.copy_to(document)

        assert len(document.tables) == 2
        assert copy.cell(0, 0).text == "a"
        assert copy.style.name == "Table Grid"

    def and_across_documents_with_its_style(self):
        source = docx.Document()
        table = source.add_table(1, 1, style="Table Grid")
        destination = docx.Document()
        destination.styles.remove_unused()

        copy = table.copy_to(destination)

        assert "Table Grid" in destination.styles
        assert copy.style.name == "Table Grid"

    def it_can_place_the_copy_before_a_paragraph(self):
        document = docx.Document()
        table = document.add_table(1, 1)
        paragraph = document.add_paragraph("after")

        table.copy_to(document, before=paragraph)

        body = list(document.iter_inner_content())
        assert [type(item).__name__ for item in body] == ["Table", "Table", "Paragraph"]

    def it_carries_a_picture_inside_a_cell(self):
        document = docx.Document()
        table = document.add_table(1, 1)
        table.cell(0, 0).paragraphs[0].add_run().add_picture(_IMAGE)

        table.copy_to(document)

        assert len(document.inline_shapes) == 2
        assert len(document.images) == 1
