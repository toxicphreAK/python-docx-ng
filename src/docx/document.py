# pyright: reportImportCycles=false
# pyright: reportPrivateUsage=false

"""|Document| and closely related objects."""

from __future__ import annotations

import os
from typing import IO, TYPE_CHECKING, Iterator, List, Sequence, Tuple

from docx.altchunk import AltChunk
from docx.blkcntnr import BlockItemContainer
from docx.bookmark import Bookmarks
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_BREAK
from docx.formfield import FormField, iter_form_fields
from docx.opc.constants import CONTENT_TYPE as CT
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.section import Section, Sections
from docx.shared import ElementProxy, Emu, Inches, Length, Pt, lazyproperty
from docx.text.run import Run

if TYPE_CHECKING:
    import docx.types as t
    from docx.comments import Comment, Comments
    from docx.fields import Field
    from docx.footnotes import Endnotes, Footnotes
    from docx.image.image import Image
    from docx.math import Math
    from docx.numbering import Numbering
    from docx.opc.customprops import CustomProperties
    from docx.opc.parts.custom_xml import CustomXmlPart
    from docx.oxml.document import CT_Body, CT_Document
    from docx.parts.document import DocumentPart
    from docx.revisions import Revision
    from docx.sdt import ContentControl
    from docx.settings import Settings
    from docx.styles.style import ParagraphStyle, _TableStyle
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    from docx.theme import Theme
    from docx.watermark import Watermark


class Document(ElementProxy):
    """WordprocessingML (WML) document.

    Not intended to be constructed directly. Use :func:`docx.Document` to open or create
    a document.
    """

    def __init__(self, element: CT_Document, part: DocumentPart):
        super(Document, self).__init__(element)
        self._element = element
        self._part = part
        self.__body = None

    def add_alt_chunk(self, chunk: bytes | str | IO[bytes], content_type: str) -> AltChunk:
        """Return an |AltChunk| newly added at the end of the document body.

        `chunk` is the embedded document, given as bytes, as a path to a file, or as a
        file-like object open for binary read. `content_type` states its format, e.g.
        `"text/html"`, `"application/rtf"` or
        `"application/vnd.openxmlformats-officedocument.wordprocessingml.document"`;
        Word chooses an importer from it, so it must be right.

        Word performs the import when it opens the document, which means the embedded
        content is not visible to this library. Its paragraphs and tables do not appear
        in `Document.paragraphs`, `Document.tables` or `Document.iter_inner_content()`,
        and it contributes no styles, numbering or images to this document until Word
        has rewritten the file.
        """
        blob = chunk if isinstance(chunk, bytes) else _read_blob(chunk)
        rId = self._part.add_alt_chunk_part(blob, content_type)
        altChunk = self._element.body.add_altChunk()
        altChunk.rId = rId
        return AltChunk(altChunk, self._part)

    def add_comment(
        self,
        runs: Run | Sequence[Run],
        text: str | None = "",
        author: str = "",
        initials: str | None = "",
    ) -> Comment:
        """Add a comment to the document, anchored to the specified runs.

        `runs` can be a single `Run` object or a non-empty sequence of `Run` objects. Only the
        first and last run of a sequence are used, it's just more convenient to pass a whole
        sequence when that's what you have handy, like `paragraph.runs` for example. When `runs`
        contains a single `Run` object, that run serves as both the first and last run.

        A comment can be anchored only on an even run boundary, meaning the text the comment
        "references" must be a non-zero integer number of consecutive runs. The runs need not be
        _contiguous_ per se, like the first can be in one paragraph and the last in the next
        paragraph, but all runs between the first and the last will be included in the reference.

        The comment reference range is delimited by placing a `w:commentRangeStart` element before
        the first run and a `w:commentRangeEnd` element after the last run. This is why only the
        first and last run are required and why a single run can serve as both first and last.
        Word works out which text to highlight in the UI based on these range markers.

        `text` allows the contents of a simple comment to be provided in the call, providing for
        the common case where a comment is a single phrase or sentence without special formatting
        such as bold or italics. More complex comments can be added using the returned `Comment`
        object in much the same way as a `Document` or (table) `Cell` object, using methods like
        `.add_paragraph()`, .add_run()`, etc.

        The `author` and `initials` parameters allow that metadata to be set for the comment.
        `author` is a required attribute on a comment and is the empty string by default.
        `initials` is optional on a comment and may be omitted by passing |None|, but Word adds an
        `initials` attribute by default and we follow that convention by using the empty string
        when no `initials` argument is provided.
        """
        # -- normalize `runs` to a sequence of runs --
        runs = [runs] if isinstance(runs, Run) else runs
        first_run = runs[0]
        last_run = runs[-1]

        # -- Note that comments can only appear in the document part --
        comment = self.comments.add_comment(text=text, author=author, initials=initials)

        # -- let the first run orchestrate placement of the comment range start and end --
        first_run.mark_comment_range(last_run, comment.comment_id)

        return comment

    def add_heading(self, text: str = "", level: int = 1):
        """Return a heading paragraph newly added to the end of the document.

        The heading paragraph will contain `text` and have its paragraph style
        determined by `level`. If `level` is 0, the style is set to `Title`. If `level`
        is 1 (or omitted), `Heading 1` is used. Otherwise the style is set to `Heading
        {level}`. Raises |ValueError| if `level` is outside the range 0-9.
        """
        if not 0 <= level <= 9:
            raise ValueError("level must be in range 0-9, got %d" % level)
        style = "Title" if level == 0 else "Heading %d" % level
        return self.add_paragraph(text, style)

    def add_page_break(self):
        """Return newly |Paragraph| object containing only a page break."""
        paragraph = self.add_paragraph()
        paragraph.add_run().add_break(WD_BREAK.PAGE)
        return paragraph

    def add_paragraph(self, text: str = "", style: str | ParagraphStyle | None = None) -> Paragraph:
        """Return paragraph newly added to the end of the document.

        The paragraph is populated with `text` and having paragraph style `style`.

        `text` can contain tab (``\\t``) characters, which are converted to the
        appropriate XML form for a tab. `text` can also include newline (``\\n``) or
        carriage return (``\\r``) characters, each of which is converted to a line
        break.
        """
        return self._body.add_paragraph(text, style)

    def add_picture(
        self,
        image_path_or_stream: str | IO[bytes],
        width: int | Length | None = None,
        height: int | Length | None = None,
        description: str | None = None,
        title: str | None = None,
        svg_fallback: str | IO[bytes] | None = None,
    ):
        """Return new picture shape added in its own paragraph at end of the document.

        The picture contains the image at `image_path_or_stream`, scaled based on
        `width` and `height`. If neither width nor height is specified, the picture
        appears at its native size. If only one is specified, it is used to compute a
        scaling factor that is then applied to the unspecified dimension, preserving the
        aspect ratio of the image. The native size of the picture is calculated using
        the dots-per-inch (dpi) value specified in the image file, defaulting to 72 dpi
        if no value is specified, as is often the case.

        `description` is the picture's alternative text, which is what a screen reader
        announces and what an accessibility check looks for; `title` is the separate
        caption-like field Word writes alongside it.

        `svg_fallback` is the raster image shown in place of an SVG wherever the vector
        source cannot be rendered; see `Run.add_picture()`.
        """
        run = self.add_paragraph().add_run()
        return run.add_picture(
            image_path_or_stream,
            width,
            height,
            description=description,
            title=title,
            svg_fallback=svg_fallback,
        )

    def add_section(self, start_type: WD_SECTION = WD_SECTION.NEW_PAGE):
        """Return a |Section| object newly added at the end of the document.

        The optional `start_type` argument must be a member of the :ref:`WdSectionStart`
        enumeration, and defaults to ``WD_SECTION.NEW_PAGE`` if not provided.
        """
        new_sectPr = self._element.body.add_section_break()
        new_sectPr.start_type = start_type
        return Section(new_sectPr, self._part)

    def add_table(
        self,
        rows: int,
        cols: int,
        style: str | _TableStyle | None = None,
        *,
        title: str | None = None,
        description: str | None = None,
    ):
        """Add a table having row and column counts of `rows` and `cols` respectively.

        `style` may be a table style object or a table style name. If `style` is |None|,
        the table inherits the default table style of the document.

        `description` is the table's alternative text, which is what a screen reader
        announces and what an accessibility check looks for. `title` is the separate,
        caption-like field Word writes alongside it. Both are omitted from the XML when
        |None|.
        """
        table = self._body.add_table(
            rows, cols, self._block_width, title=title, description=description
        )
        table.style = style
        return table

    @property
    def alt_chunks(self) -> List[AltChunk]:
        """The |AltChunk| objects in the document body, in document order.

        Only alt-chunks that are direct children of the body appear here; the schema
        also allows one inside a table cell or other block container.
        """
        return [AltChunk(altChunk, self._part) for altChunk in self._element.body.altChunk_lst]

    @lazyproperty
    def bookmarks(self) -> Bookmarks:
        """The |Bookmarks| in this document, in document order.

        Bookmarks Word maintains for itself, such as `_GoBack` and the `_Toc…` anchors,
        are left out of the collection; reach them through `.iter_all()`.
        """
        return Bookmarks(self._element, self._part)

    @property
    def comments(self) -> Comments:
        """A |Comments| object providing access to comments added to the document."""
        return self._part.comments

    @property
    def custom_properties(self) -> CustomProperties:
        """A |CustomProperties| object providing the arbitrary named values attached to
        this document.

        Behaves as a mutable mapping of name to value. The part holding them is created
        the first time this is used, so a document that never touches it gains no
        `/docProps/custom.xml`.
        """
        return self._part.package.custom_properties

    @property
    def core_properties(self):
        """A |CoreProperties| object providing Dublin Core properties of document."""
        return self._part.core_properties

    @property
    def extended_properties(self):
        """An |ExtendedProperties| object providing the application-specific properties
        of the document, such as word count and producing application."""
        return self._part.package.extended_properties

    @property
    def footnotes(self) -> Footnotes:
        """A |Footnotes| object providing access to the footnotes of this document.

        The footnotes part is created the first time this is used, so a document that
        never touches it gains no `/word/footnotes.xml`.
        """
        return self._part.footnotes

    def add_custom_xml_part(
        self, xml: str | bytes, schema_refs: Tuple[str, ...] = ()
    ) -> CustomXmlPart:
        """Add an item to the custom XML data store and return its part.

        The custom XML data store is where a document-generation pipeline keeps its
        data: whole XML documents against a caller-supplied schema, which content
        controls in the document bind to through `w:dataBinding` and Word keeps in step
        with what it displays::

            document.add_custom_xml_part(
                "<invoice><total>42.00</total></invoice>",
                schema_refs=("urn:example:invoice",),
            )

        This is a different thing from :attr:`custom_properties`, which is a flat list
        of named scalars in `docProps/custom.xml`.

        A `customXml/itemN.xml` part is created for `xml`, along with the
        `itemPropsN.xml` sidecar Word identifies it by, carrying a freshly generated
        GUID and the namespaces named in `schema_refs`.
        """
        return self._part.add_custom_xml_part(xml, schema_refs)

    @property
    def custom_xml_parts(self) -> Tuple[CustomXmlPart, ...]:
        """The custom XML data store items of this document, in relationship order.

        Each part offers `.item_id`, `.schema_refs`, `.element` and `.xml`. The item
        content is arbitrary caller-supplied XML, so `.element` is a plain parsed tree
        with no element classes of its own.
        """
        return self._part.custom_xml_parts

    @property
    def has_macros(self) -> bool:
        """|True| when this document carries a VBA project.

        The cheap predicate; :attr:`vba_project` is what reads the bytes.
        """
        return self._part.has_macros

    @property
    def vba_project(self) -> bytes | None:
        """The macro project of this document as bytes, or |None| when it has none.

        A `.docm` or `.dotm` carries its macros in `word/vbaProject.bin`, an OLE
        compound file. This library does not parse it, but it round-trips untouched, so
        the two operations people actually want are expressible:

        **Strip the macros** from a document received from elsewhere::

            del document.vba_project
            document.save("clean.docx")

        **Transplant a project** authored in Word into a generated document::

            document.vba_project = donor.vba_project

        Assigning switches the main part to the macro-enabled content type, and removing
        switches it back. Word silently ignores macros in a document whose main part
        does not claim to be macro-enabled, and warns the user about macros in one that
        claims to be but is not, so the two are kept in step rather than left to the
        caller.

        Note this sets the content type; it does not choose the file extension for you.
        A macro-enabled document conventionally has a `.docm` extension.
        """
        return self._part.vba_project

    @vba_project.setter
    def vba_project(self, blob: bytes | None) -> None:
        self._part.vba_project = blob

    @vba_project.deleter
    def vba_project(self) -> None:
        self._part.remove_vba_project()

    def remove_vba_project(self) -> int:
        """Remove this document's VBA project; return how many parts were removed.

        The `word/vbaData.xml` sibling, which holds command-bar and macro-name
        customisations, goes with it rather than being left orphaned. Zero for a
        document that carries no project. Equivalent to ``del document.vba_project``.
        """
        return self._part.remove_vba_project()

    @property
    def endnotes(self) -> Endnotes:
        """An |Endnotes| object providing access to the endnotes of this document.

        The endnotes part is created the first time this is used, so a document that
        never touches it gains no `/word/endnotes.xml`.
        """
        return self._part.endnotes

    @property
    def fields(self) -> List[Field]:
        """A |Field| for each field in the document body, in document order.

        Outermost first, so a `PAGEREF` nested in a table-of-contents entry follows the
        `TOC` field containing it. Fields in a header or footer are not in the document
        part and so are not included; reach those through the paragraphs of the header
        or footer.
        """
        from docx.fields import iter_fields

        return list(iter_fields(self._element, self._part))

    @property
    def form_fields(self) -> List[FormField]:
        """A |FormField| instance for each legacy form field in the document body.

        Fields appear in document order, including those inside tables. Fields in a
        header or footer are not in the document part and so are not included; reach
        those through the paragraphs of the header or footer.
        """
        return list(iter_form_fields(self._element, self._part))

    @property
    def floating_shapes(self):
        """The |FloatingShapes| collection for this document.

        A floating shape is anchored rather than inline: it is positioned against the
        page, the margin, the column or the paragraph, and text wraps around it. These
        do not appear in :attr:`inline_shapes`, whose position properties would be
        meaningless for them.
        """
        return self._part.floating_shapes

    @property
    def images(self) -> Tuple[Image, ...]:
        """The distinct images embedded in this document's body, in relationship order.

        This is the package-level view, the counterpart of reaching an image through the
        shape that displays it. Several shapes can share one image part, so this is
        shorter than :attr:`inline_shapes` whenever a picture is used twice, and it
        includes images no shape displays — a picture left behind when its paragraph was
        deleted, for instance.

        Only images related from the main document part appear here. A picture in a
        header, a footer or a comment belongs to that part's relationships instead.

        A *linked* image is not included: its bytes are not in the package.
        """
        return tuple(
            rel.target_part.image
            for rel in self._part.rels.values()
            if rel.reltype == RT.IMAGE and not rel.is_external
        )

    @property
    def theme(self) -> Theme | None:
        """The document's |Theme|, or |None| when it carries no theme part.

        The theme is where a theme typeface token such as ``"minorHAnsi"`` becomes a
        real font name, and where a theme colour becomes an RGB value::

            document.theme.minor_font.latin   # -> 'Calibri'
            document.theme.color("accent1")

        For the large class of documents that set no explicit ``w:rFonts/@w:ascii``
        anywhere, this is the only place the typeface the text is actually rendered in
        can be found; see also :attr:`.Font.theme_typeface`.
        """
        return self._part.theme

    @property
    def inline_shapes(self):
        """The |InlineShapes| collection for this document.

        An inline shape is a graphical object, such as a picture, contained in a run of
        text and behaving like a character glyph, being flowed like other text in a
        paragraph.
        """
        return self._part.inline_shapes

    @property
    def content_controls(self) -> List[ContentControl]:
        """The structured document tags (content controls) in the document body.

        In document order, outermost first. The content of a control appears in
        `.paragraphs`, `.tables` and `.iter_inner_content()` as though the wrapper were
        not there; this is how the wrapper itself is reached.
        """
        return self._body.content_controls

    def iter_inner_content(self) -> Iterator[Paragraph | Table]:
        """Generate each `Paragraph` or `Table` in this document in document order."""
        return self._body.iter_inner_content()

    @property
    def math(self) -> List[Math]:
        """The equations in the document body, in document order.

        Equations in a header, a footer, a footnote or a comment are in those parts
        rather than the body and are not included; reach them through the container
        concerned. See :attr:`.Paragraph.math` for why equation text is not part of
        :attr:`.Paragraph.text`.
        """
        return self._body.math

    @property
    def numbering(self) -> Numbering:
        """A |Numbering| object providing access to the list definitions of this document.

        The numbering part is created the first time this is used, so a document that
        never touches it gains no `/word/numbering.xml`.
        """
        from docx.numbering import Numbering

        return Numbering(self._part.numbering_part.element, self._part)

    @property
    def list_numbers(self) -> List[tuple[Paragraph, str]]:
        """`(paragraph, number)` for each list paragraph in the body, in document order.

        The number is what a reader sees — "1.", "a)", "iii." — which Word computes from
        `numbering.xml` at display time rather than storing in the body::

            for paragraph, number in document.list_numbers:
                print(number, paragraph.text)

        Paragraphs inside tables are included, since they count towards the same lists.
        This walks the document once, which is why it exists alongside
        :attr:`.Paragraph.list_number`: reading that for every paragraph is quadratic.
        """
        from docx.numbering import compute_list_numbers, iter_story_paragraphs
        from docx.text.paragraph import Paragraph

        return [
            (Paragraph(p, self._body), number)
            for p, number in compute_list_numbers(iter_story_paragraphs(self._element), self._part)
        ]

    @property
    def paragraphs(self) -> List[Paragraph]:
        """The |Paragraph| instances in the document, in document order.

        A paragraph wrapped in a `w:sdt` (content control) appears in this list, in the
        position of its wrapper.

        A revision mark such as `w:ins` or `w:del` wraps runs rather than paragraphs, so
        it does not affect which paragraphs appear here; it affects their text. See
        :attr:`.Paragraph.text` and :attr:`.Paragraph.original_text`.
        """
        return self._body.paragraphs

    @property
    def part(self) -> DocumentPart:
        """The |DocumentPart| object of this document."""
        return self._part

    def replace_text(
        self,
        old: str,
        new: str,
        *,
        count: int = -1,
        regex: bool = False,
        flags: int = 0,
        tables: bool = True,
        headers_footers: bool = False,
        footnotes: bool = False,
    ) -> int:
        """Replace occurrences of `old` with `new` in this document; return how many.

        The match is made against each paragraph's text as a whole, so it succeeds
        whether or not Word split the text across runs; see
        :meth:`.Paragraph.replace_text` for what happens to formatting.

        What gets searched is explicit rather than incidental, because "replace it
        everywhere" means different things to different callers and getting it wrong is
        invisible until someone reads the header::

            document.replace_text("{{name}}", "Ada")                        # body only
            document.replace_text("{{name}}", "Ada", headers_footers=True)  # and those

        The document body, including tables unless `tables` is |False|, is always
        searched. Headers and footers of every section — default, first-page and
        even-page alike — are searched when `headers_footers` is |True|, and footnotes
        and endnotes when `footnotes` is |True|. Comments are never searched: a comment
        is somebody's remark about the document rather than part of it.

        `count` of -1 replaces every match; any other value limits the total across
        everything searched, in the order given above. `regex` and `flags` are as for
        :meth:`.Paragraph.replace_text`.
        """
        if count == 0:
            return 0

        containers: List[BlockItemContainer] = [self._body]
        if headers_footers:
            for section in self.sections:
                # -- a header that inherits from the prior section has no definition of
                # -- its own; searching it would visit the inherited one a second time,
                # -- and merely reaching for it would create a part in the first section
                containers.extend(
                    hdrftr
                    for hdrftr in section.iter_headers_footers()
                    if not hdrftr.is_linked_to_previous
                )
        if footnotes and self._part.has_footnotes_part:
            containers.extend(self.footnotes)
        if footnotes and self._part.has_endnotes_part:
            containers.extend(self.endnotes)

        replaced = 0
        for container in containers:
            replaced += container.replace_text(
                old,
                new,
                count=-1 if count < 0 else count - replaced,
                regex=regex,
                flags=flags,
                tables=tables,
            )
            if count >= 0 and replaced >= count:
                break

        return replaced

    @property
    def is_template(self) -> bool:
        """|True| when this document is a Word template, a ``.dotx`` or ``.dotm``.

        A template holds the same markup as a document and differs only in the content
        type of its main part, which is what tells Word to start a new document from it
        rather than open it for editing.
        """
        return self._part.content_type in (
            CT.WML_TEMPLATE_MAIN,
            CT.WML_TEMPLATE_MACRO_ENABLED_MAIN,
        )

    def save(
        self,
        path_or_stream: str | os.PathLike[str] | IO[bytes],
        as_template: bool | None = None,
    ):
        """Save this document to `path_or_stream`.

        `path_or_stream` can be either a path to a filesystem location (a string or
        ``os.PathLike``) or a file-like object.

        `as_template` selects whether the result is a Word template (``.dotx`` /
        ``.dotm``) or an ordinary document (``.docx`` / ``.docm``). The default of
        |None| keeps whichever this document already is, so a template opened and saved
        is still a template. Pass ``False`` to generate a document from a template, or
        ``True`` to turn a document into one. Macro-enabled input stays macro-enabled
        either way.

        Note this sets the content type; it does not choose the file extension for you.
        """
        if as_template is not None:
            self._part.content_type = _document_content_type(
                self._part.content_type, as_template=as_template
            )
        if isinstance(path_or_stream, os.PathLike):
            path_or_stream = os.fspath(path_or_stream)
        self._part.save(path_or_stream)

    @property
    def revisions(self) -> List[Revision]:
        """A |Revision| for each tracked change in the document body, in document order.

        Empty for a document that has not been through review. Revisions in a header,
        footer or footnote are not in the document part and so are not included; reach
        those through the paragraphs of the story concerned.
        """
        from docx.revisions import iter_revisions

        return list(iter_revisions(self._element, self._part))

    def accept_all_revisions(self) -> int:
        """Accept every tracked change in the document body; return how many.

        Insertions become ordinary text, deletions go, formatting-change records are
        dropped leaving the current formatting, and a deleted paragraph mark merges its
        paragraph with the one after it. The result is the document as
        :attr:`.Paragraph.text` already reads it.
        """
        from docx.revisions import apply_all

        return apply_all(self._element, self._part, accept=True)

    def reject_all_revisions(self) -> int:
        """Reject every tracked change in the document body; return how many.

        The reverse of :meth:`accept_all_revisions`: the result is the document as
        :attr:`.Paragraph.original_text` reads it.
        """
        from docx.revisions import apply_all

        return apply_all(self._element, self._part, accept=False)

    @property
    def sections(self) -> Sections:
        """|Sections| object providing access to each section in this document."""
        return Sections(self._element, self._part)

    def add_text_watermark(
        self,
        text: str,
        *,
        font: str = "Calibri",
        font_size: Length | int | None = None,
        color: str = "C0C0C0",
        opacity: float | None = None,
        angle: float = 315,
        width: Length | int = Pt(468),
        height: Length | int = Pt(234),
        bold: bool = False,
        italic: bool = False,
    ) -> List[Watermark]:
        """Add a text watermark to the whole document, returning the watermarks added.

        The faint "DRAFT" or "CONFIDENTIAL" behind the content::

            document.add_text_watermark("DRAFT")
            document.add_text_watermark("CONFIDENTIAL", color="FF0000", angle=0)

        Every section is covered, and within each the default, first-page and even-page
        headers alike, so the watermark does not disappear on a page that uses a
        different header. A header shared between sections is written to once.

        The arguments are as for :meth:`.Section.add_text_watermark`, which is also how
        a watermark is applied to one section rather than the whole document.
        """
        from docx.watermark import add_text_watermark, iter_watermark_headers

        return add_text_watermark(
            iter_watermark_headers(self.sections),
            text,
            font=font,
            font_size=font_size,
            color=color,
            opacity=opacity,
            angle=angle,
            width=width,
            height=height,
            bold=bold,
            italic=italic,
        )

    def add_image_watermark(
        self,
        image_path_or_stream: str | IO[bytes],
        *,
        width: Length | int | None = None,
        height: Length | int | None = None,
        washout: bool = True,
        scale: float = 1.0,
    ) -> List[Watermark]:
        """Add an image watermark to the whole document; see :meth:`add_text_watermark`.

        `washout` applies Word's brightness-and-contrast correction, which is what makes
        a logo read as a background rather than sitting opaquely over the text.
        """
        from docx.watermark import add_image_watermark, iter_watermark_headers

        return add_image_watermark(
            iter_watermark_headers(self.sections),
            image_path_or_stream,
            width=width,
            height=height,
            washout=washout,
            scale=scale,
        )

    def remove_watermark(self) -> int:
        """Remove every watermark from the document, returning how many were removed."""
        from docx.watermark import iter_watermark_headers, remove_watermarks

        return remove_watermarks(iter_watermark_headers(self.sections))

    @property
    def watermarks(self) -> List[Watermark]:
        """Every watermark in the document, in section and header order.

        Empty when the document has none. Ordinarily one per header rather than one per
        document, since a watermark is a shape in a header and each header carries its
        own.
        """
        from docx.watermark import iter_watermark_headers, iter_watermarks

        return [w for hdr in iter_watermark_headers(self.sections) for w in iter_watermarks(hdr)]

    @property
    def settings(self) -> Settings:
        """A |Settings| object providing access to the document-level settings."""
        return self._part.settings

    @property
    def styles(self):
        """A |Styles| object providing access to the styles in this document."""
        return self._part.styles

    @property
    def tables(self) -> List[Table]:
        """All |Table| instances in the document, in document order.

        Note that only tables appearing at the top level of the document appear in this
        list; a table nested inside a table cell does not appear. A table wrapped in a
        `w:sdt` (content control) does appear. A row marked as inserted or deleted
        appears as an ordinary row; see :attr:`revisions`.
        """
        return self._body.tables

    @property
    def _block_width(self) -> Length:
        """A |Length| object specifying the space between margins in last section."""
        section = self.sections[-1]
        page_width = section.page_width or Inches(8.5)
        left_margin = section.left_margin or Inches(1)
        right_margin = section.right_margin or Inches(1)
        return Emu(page_width - left_margin - right_margin)

    @property
    def _body(self) -> _Body:
        """The |_Body| instance containing the content for this document."""
        if self.__body is None:
            self.__body = _Body(self._element.body, self)
        return self.__body


class _Body(BlockItemContainer):
    """Proxy for `<w:body>` element in this document.

    It's primary role is a container for document content.
    """

    def __init__(self, body_elm: CT_Body, parent: t.ProvidesStoryPart):
        super(_Body, self).__init__(body_elm, parent)
        self._body = body_elm

    def clear_content(self) -> _Body:
        """Return this |_Body| instance after clearing it of all content.

        Section properties for the main document story, if present, are preserved.
        """
        self._body.clear_content()
        return self


# -- the content type of a main document part, paired with its template counterpart.
# -- The two forms of each pair hold identical markup; only Word's treatment differs. --
_TEMPLATE_CONTENT_TYPE_BY_DOCUMENT = {
    CT.WML_DOCUMENT_MAIN: CT.WML_TEMPLATE_MAIN,
    CT.WML_DOCUMENT_MACRO_ENABLED_MAIN: CT.WML_TEMPLATE_MACRO_ENABLED_MAIN,
}
_DOCUMENT_CONTENT_TYPE_BY_TEMPLATE = {
    template: document for document, template in _TEMPLATE_CONTENT_TYPE_BY_DOCUMENT.items()
}


def _document_content_type(content_type: str, as_template: bool) -> str:
    """The `content_type` counterpart that is or is not a template, per `as_template`.

    Returns `content_type` unchanged when it is already the requested form, so a
    macro-enabled document stays macro-enabled.
    """
    mapping = (
        _TEMPLATE_CONTENT_TYPE_BY_DOCUMENT if as_template else _DOCUMENT_CONTENT_TYPE_BY_TEMPLATE
    )
    return mapping.get(content_type, content_type)


def _read_blob(chunk: str | IO[bytes]) -> bytes:
    """The bytes of `chunk`, a path to a file or a file-like object open for read."""
    if isinstance(chunk, str):
        with open(chunk, "rb") as f:
            return f.read()
    return chunk.read()
