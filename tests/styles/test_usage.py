# pyright: reportPrivateUsage=false

"""Unit test suite for style usage analysis, cleanup and bulk transfer."""

from __future__ import annotations

import io

import pytest

import docx
from docx.enum.style import WD_STYLE_TYPE


def _document_with_content():
    document = docx.Document()
    document.add_heading("H", 1)
    document.add_paragraph("body")
    return document


class DescribeStyleUsage:
    """Unit-test suite for `Styles.usage()`."""

    def it_reports_what_is_defined_and_what_is_used(self):
        document = _document_with_content()

        usage = document.styles.usage()

        assert len(usage.defined) == 164
        assert "Heading1" in usage.used
        assert "Normal" in usage.used
        assert len(usage.used) < len(usage.defined)

    def it_counts_direct_references(self):
        document = docx.Document()
        document.add_paragraph("a", style="Quote")
        document.add_paragraph("b", style="Quote")

        usage = document.styles.usage()

        assert usage.reference_counts["Quote"] == 2

    def it_follows_basedOn_so_an_inherited_style_counts_as_used(self):
        """`Heading 1` is based on `Normal` and links `Heading 1 Char`."""
        document = _document_with_content()

        used = set(document.styles.usage().used)

        assert "Heading1" in used
        assert "Normal" in used
        assert "Heading1Char" in used

    def and_it_counts_the_default_styles_which_nothing_names(self):
        document = docx.Document()

        used = set(document.styles.usage().used)
        default_para = document.styles.default(WD_STYLE_TYPE.PARAGRAPH)

        assert default_para is not None
        assert default_para.style_id in used
        assert document.styles.usage().reference_counts.get(default_para.style_id, 0) == 0

    def but_seed_defaults_False_asks_the_narrower_question(self):
        document = docx.Document()

        with_defaults = set(document.styles.usage().used)
        without = set(document.styles.usage(seed_defaults=False).used)

        assert without < with_defaults

    def it_reaches_styles_applied_only_in_a_header(self):
        """A header is a separate part with its own style references."""
        document = docx.Document()
        header = document.sections[0].header
        header.paragraphs[0].style = "Quote"

        assert "Quote" in document.styles.usage().used

    def and_styles_applied_only_in_a_footnote(self):
        document = docx.Document()
        footnote = document.footnotes.add_footnote("note")
        footnote.paragraphs[0].style = "Quote"

        assert "Quote" in document.styles.usage().used

    def it_reports_latent_styles_separately_from_defined_ones(self):
        usage = docx.Document().styles.usage()

        assert len(usage.latent) > 100
        # -- a latent style is a declaration about a style the document does *not*
        # -- define, so nothing may appear in both --
        assert not set(usage.latent) & set(usage.defined)

    def it_can_be_told_to_keep_extra_styles(self):
        document = docx.Document()

        usage = document.styles.usage(keep=["Quote"])

        assert "Quote" in usage.used

    def it_prints_a_summary(self):
        summary = str(_document_with_content().styles.usage())

        assert "styles defined" in summary
        assert "in use" in summary

    def it_lists_the_unused_styles(self):
        document = _document_with_content()

        unused = document.styles.unused

        assert len(unused) == len(document.styles.usage().unused)
        assert all(not s.in_use for s in unused)

    def it_answers_in_use_for_one_style(self):
        document = _document_with_content()

        assert document.styles["Heading 1"].in_use is True
        assert document.styles["Quote"].in_use is False


class DescribeRemoveUnusedStyles:
    """Unit-test suite for `Styles.remove_unused()`."""

    def it_prunes_to_the_reachable_closure(self):
        document = _document_with_content()
        before = len(document.styles)

        removed = document.styles.remove_unused()

        assert len(removed) > 100
        assert len(document.styles) == before - len(removed)
        assert "Heading 1" in document.styles
        assert "Quote" not in document.styles

    def and_the_document_still_renders_as_it_did(self):
        document = _document_with_content()
        document.styles.remove_unused()

        stream = io.BytesIO()
        document.save(stream)
        reopened = docx.Document(io.BytesIO(stream.getvalue()))

        assert reopened.paragraphs[0].style.name == "Heading 1"
        assert reopened.paragraphs[1].text == "body"

    def it_keeps_the_styles_named_in_keep_and_their_dependencies(self):
        document = _document_with_content()

        document.styles.remove_unused(keep=["Quote"])

        assert "Quote" in document.styles
        # -- `Quote Char` is the `w:link` of `Quote` and comes with it --
        assert "Quote Char" in document.styles

    def it_never_removes_Normal(self):
        document = docx.Document()

        document.styles.remove_unused(keep_defaults=False)

        assert "Normal" in document.styles

    def it_keeps_the_default_styles_by_default(self):
        document = _document_with_content()

        document.styles.remove_unused()

        assert document.styles.default(WD_STYLE_TYPE.PARAGRAPH) is not None
        assert document.styles.default(WD_STYLE_TYPE.CHARACTER) is not None

    def but_keep_defaults_False_prunes_the_ones_nothing_references(self):
        document = _document_with_content()

        with_defaults = docx.Document()
        with_defaults.add_heading("H", 1)
        with_defaults.add_paragraph("body")
        with_defaults.styles.remove_unused()

        document.styles.remove_unused(keep_defaults=False)

        assert len(document.styles) < len(with_defaults.styles)


class DescribeDocumentCleanup:
    """Unit-test suite for `Document.cleanup()`."""

    def it_removes_unused_styles_numbering_and_media(self):
        document = _document_with_content()
        document.add_picture("tests/test_files/monty-truth.png")
        document.paragraphs[-1].delete()

        result = document.cleanup()

        assert len(result.styles) > 100
        assert len(result.num_ids) > 0
        assert result.media == ("/word/media/image1.png",)

    def but_it_keeps_media_a_shape_still_refers_to(self):
        document = docx.Document()
        document.add_picture("tests/test_files/monty-truth.png")

        result = document.cleanup()

        assert result.media == ()
        assert len(document.inline_shapes) == 1
        assert document.inline_shapes[0].image is not None

    def it_leaves_latent_styles_alone_unless_asked(self):
        document = _document_with_content()

        result = document.cleanup()

        assert result.latent_styles == 0
        assert len(document.styles.latent_styles) > 100

    def and_trims_them_when_asked(self):
        document = _document_with_content()

        result = document.cleanup(latent_styles=True)

        assert result.latent_styles > 100
        assert len(document.styles.latent_styles) == 0

    def each_pass_can_be_turned_off(self):
        document = _document_with_content()

        result = document.cleanup(styles=False, numbering=False, media=False)

        assert result.styles == ()
        assert result.num_ids == ()
        assert result.media == ()

    def it_produces_a_much_smaller_document(self):
        document = _document_with_content()
        before = io.BytesIO()
        document.save(before)

        document.cleanup(latent_styles=True)
        after = io.BytesIO()
        document.save(after)

        assert len(after.getvalue()) < len(before.getvalue())

    def and_the_result_still_opens(self):
        document = _document_with_content()
        document.cleanup(latent_styles=True)
        stream = io.BytesIO()
        document.save(stream)

        reopened = docx.Document(io.BytesIO(stream.getvalue()))

        assert [p.text for p in reopened.paragraphs] == ["H", "body"]
        assert reopened.paragraphs[0].style.name == "Heading 1"

    def it_prints_a_summary(self):
        assert "removed" in str(_document_with_content().cleanup())


class DescribeUnusedNumberingRemoval:
    """Numbering a document actually applies must survive the cleanup."""

    def it_keeps_a_numbering_definition_a_paragraph_uses(self):
        document = docx.Document()
        paragraph = document.add_paragraph("item")
        paragraph.set_numbering(1, level=0)
        num_id = paragraph.numbering.num_id if paragraph.numbering else None

        result = document.cleanup()

        assert num_id not in result.num_ids
        assert document.numbering.get(num_id) is not None

    def and_removes_ones_nothing_applies(self):
        document = docx.Document()

        result = document.cleanup()

        assert len(result.num_ids) > 0


class DescribeStyleImportAndExtract:
    """Unit-test suite for `Styles.import_from()`, `.extract()` and `.extract_xml()`."""

    def it_imports_named_styles_from_another_document(self):
        source = docx.Document()
        document = docx.Document()
        document.styles.remove_unused()

        report = document.styles.import_from(source, names=["Quote", "Caption"])

        assert report == {"Quote": "added", "Caption": "added"}
        assert "Quote" in document.styles
        assert "Caption" in document.styles

    def and_it_brings_their_dependencies_with_them(self):
        source = docx.Document()
        document = docx.Document()
        document.styles.remove_unused()

        document.styles.import_from(source, names=["Quote"])

        # -- `Quote Char` is the `w:link` of `Quote` --
        assert "Quote Char" in document.styles

    def it_skips_a_name_already_present_by_default(self):
        source = docx.Document()
        document = docx.Document()

        report = document.styles.import_from(source, names=["Quote"])

        assert report == {"Quote": "skipped"}

    def but_overwrite_replaces_it(self):
        source = docx.Document()
        document = docx.Document()

        report = document.styles.import_from(source, names=["Quote"], overwrite=True)

        assert report == {"Quote": "replaced"}

    def it_imports_every_style_when_no_names_are_given(self):
        source = docx.Document()
        document = docx.Document()
        document.styles.remove_unused()
        before = len(document.styles)

        report = document.styles.import_from(source)

        assert len(report) == len(source.styles)
        assert len(document.styles) > before

    def it_accepts_a_path(self, tmp_path):
        source_path = tmp_path / "source.docx"
        docx.Document().save(str(source_path))
        document = docx.Document()
        document.styles.remove_unused()

        report = document.styles.import_from(str(source_path), names=["Quote"])

        assert report["Quote"] == "added"

    def it_does_not_copy_the_whole_latent_style_block_unless_asked(self):
        """`copy_style_from()` carries the exception for each style it copies; what
        `include_latent` adds is the source's whole block, which changes which of Word's
        built-ins appear in *this* document's gallery."""
        source = docx.Document()
        document = docx.Document()
        document.styles.latent_styles.trim()

        document.styles.import_from(source, names=["Quote"], overwrite=True)
        without = len(document.styles.latent_styles)

        assert without < 10

    def and_include_latent_copies_it(self):
        source = docx.Document()
        document = docx.Document()
        document.styles.latent_styles.trim()

        document.styles.import_from(source, names=["Quote"], include_latent=True)

        assert len(document.styles.latent_styles) > 100

    def it_extracts_named_styles_to_a_styles_only_document(self):
        source = docx.Document()
        stream = io.BytesIO()

        added = source.styles.extract(stream, names=["Quote"])

        assert "Quote" in added
        extracted = docx.Document(io.BytesIO(stream.getvalue()))
        assert "Quote" in extracted.styles
        assert "Quote Char" in extracted.styles
        # -- and none of the 164 the bundled template would otherwise bring --
        assert "Subtitle" not in extracted.styles
        assert len(extracted.paragraphs) == 0

    def it_can_extract_as_a_template(self, tmp_path):
        from docx.opc.constants import CONTENT_TYPE as CT

        source = docx.Document()
        path = tmp_path / "house.dotx"

        source.styles.extract(str(path), names=["Quote"], as_template=True)

        extracted = docx.Document(str(path))
        assert extracted.part.content_type == CT.WML_TEMPLATE_MAIN

    def it_gives_back_the_styles_xml_directly(self):
        source = docx.Document()

        xml_bytes = source.styles.extract_xml(names=["Quote"])

        assert xml_bytes.startswith(b"<?xml")
        assert b"Quote" in xml_bytes

    def it_raises_for_a_name_the_source_does_not_have(self):
        source = docx.Document()

        with pytest.raises(KeyError, match="Nonexistent"):
            source.styles.extract_xml(names=["Nonexistent"])
