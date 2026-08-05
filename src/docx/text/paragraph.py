"""Paragraph-related proxy types."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator, List, cast

from docx.enum.style import WD_STYLE_TYPE
from docx.formfield import FormField, iter_form_fields
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml.deletion import delete_element
from docx.oxml.ns import qn
from docx.oxml.parser import OxmlElement
from docx.oxml.text.run import CT_R
from docx.shared import StoryChild
from docx.styles.style import ParagraphStyle
from docx.text.hyperlink import Hyperlink
from docx.text.pagebreak import RenderedPageBreak
from docx.text.parfmt import ParagraphFormat
from docx.text.run import Run

if TYPE_CHECKING:
    import docx.types as t
    from docx.bookmark import Bookmark
    from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
    from docx.fields import Field
    from docx.math import Math
    from docx.numbering import ParagraphNumbering
    from docx.oxml.text.form import CT_FldChar, CT_SimpleField
    from docx.oxml.text.paragraph import CT_P
    from docx.revisions import Revision
    from docx.sdt import ContentControl
    from docx.styles.style import CharacterStyle
    from docx.text.hyperlink import Hyperlink


# -- the character style Word applies to hyperlink text, and adds to a document the
# -- first time a link is inserted into one --
_HYPERLINK_STYLE_NAME = "Hyperlink"


class Paragraph(StoryChild):
    """Proxy object wrapping a `<w:p>` element."""

    def __init__(self, p: CT_P, parent: t.ProvidesStoryPart):
        super(Paragraph, self).__init__(parent)
        self._p = self._element = p

    def add_run(self, text: str | None = None, style: str | CharacterStyle | None = None) -> Run:
        """Append run containing `text` and having character-style `style`.

        `text` can contain tab (``\\t``) characters, which are converted to the
        appropriate XML form for a tab. `text` can also include newline (``\\n``) or
        carriage return (``\\r``) characters, each of which is converted to a line
        break. When `text` is `None`, the new run is empty.
        """
        r = self._p.add_r()
        run = Run(r, self)
        if text:
            run.text = text
        if style:
            run.style = style
        return run

    @property
    def alignment(self) -> WD_PARAGRAPH_ALIGNMENT | None:
        """A member of the :ref:`WdParagraphAlignment` enumeration specifying the
        justification setting for this paragraph.

        A value of |None| indicates the paragraph has no directly-applied alignment
        value and will inherit its alignment value from its style hierarchy. Assigning
        |None| to this property removes any directly-applied alignment value.
        """
        return self._p.alignment

    @alignment.setter
    def alignment(self, value: WD_PARAGRAPH_ALIGNMENT):
        self._p.alignment = value

    def delete(self) -> None:
        """Remove this paragraph from the document.

        Any hyperlink relationship referenced only from this paragraph is dropped, and
        the surviving half of any comment range or bookmark that started or ended here
        is removed, so nothing is left pointing at content that is gone.

        Raises |ValueError| when this is the only paragraph in a table cell: a `w:tc`
        must contain at least one block-level element and a cell without one produces a
        document Word refuses to open. Use `_Cell.text = ""` to empty such a cell.
        """
        self._p.assert_deletable()
        delete_element(self._p, self.part)

    def clear(self):
        """Return this same paragraph after removing all its content.

        Paragraph-level formatting, such as style, is preserved.
        """
        self._p.clear_content()
        return self

    @property
    def contains_page_break(self) -> bool:
        """`True` when one or more rendered page-breaks occur in this paragraph."""
        return bool(self._p.lastRenderedPageBreaks)

    def add_hyperlink(
        self,
        text: str,
        address: str | None = None,
        fragment: str | None = None,
        style: str | CharacterStyle | None = "Hyperlink",
    ) -> Hyperlink:
        """Append a hyperlink displaying `text` and return it.

        `address` is the target URL. `fragment` is the part of a URL after the "#", and
        is also how an internal link names its target: pass `fragment` alone, with no
        `address`, to link to a bookmark elsewhere in this document, which is what a
        cross-reference or a table-of-contents entry is.

        `style` is the character style applied to the link text, "Hyperlink" by
        default, which is the style Word uses. A document that does not define it — the
        bundled default template among them — has it added, blue and underlined as Word
        defines it, since an unstyled hyperlink is indistinguishable from body text.
        Pass |None| to skip styling deliberately, or the name of another character
        style to use that instead.

        The returned |Hyperlink| exposes its `.runs`, so the link text can be formatted
        further::

            link = paragraph.add_hyperlink("python-docx", "https://example.com/")
            link.runs[0].font.bold = True

        Raises |ValueError| when neither `address` nor `fragment` is given, which would
        produce a link that goes nowhere.
        """
        from docx.text.hyperlink import Hyperlink

        if not address and not fragment:
            raise ValueError("hyperlink requires an address, a fragment, or both")

        hyperlink = self._p.add_hyperlink()
        if address:
            # -- reuses the rId of an existing relationship to the same address --
            hyperlink.rId = self.part.relate_to(address, RT.HYPERLINK, is_external=True)
        if fragment:
            hyperlink.anchor = fragment

        run = Run(hyperlink.add_r(), self)
        run.text = text
        if style is not None:
            self._apply_hyperlink_style(run, style)
        return Hyperlink(hyperlink, self._parent)

    def _apply_hyperlink_style(self, run: Run, style: str | CharacterStyle) -> None:
        """Apply `style` to `run`, defining the default hyperlink style if it is absent.

        Word adds the "Hyperlink" style to a document the first time a link is inserted
        into it, and a link that inherits body-text formatting does not look like a
        link at all. Any other named style that is missing is the caller's problem and
        raises, as assigning a missing style always has.
        """
        try:
            run.style = style
        except KeyError:
            if style != _HYPERLINK_STYLE_NAME:
                raise
            run.style = self._add_default_hyperlink_style()

    def _add_default_hyperlink_style(self) -> CharacterStyle:
        """Add and return the "Hyperlink" character style, blue and underlined."""
        from docx.enum.style import WD_STYLE_TYPE
        from docx.enum.text import WD_UNDERLINE
        from docx.shared import RGBColor

        style = cast(
            "CharacterStyle",
            self.part.document.styles.add_style(
                _HYPERLINK_STYLE_NAME, WD_STYLE_TYPE.CHARACTER, builtin=True
            ),
        )
        style.font.color.rgb = RGBColor(0x05, 0x63, 0xC1)
        style.font.underline = WD_UNDERLINE.SINGLE
        style.priority = 99
        style.unhide_when_used = True
        return style

    def add_bookmark(self, name: str) -> Bookmark:
        """Return a |Bookmark| named `name` spanning the content of this paragraph.

        Use `Run.mark_bookmark_range()` to bookmark a narrower range. `name` must be
        unique in the document; Word treats a duplicate name as a second bookmark and
        the two then compete for anything referring to the name.
        """
        from docx.bookmark import Bookmark

        bookmarkStart = self._p.add_bookmark_around_content(self.part.next_bookmark_id, name)
        return Bookmark(bookmarkStart, self)

    @property
    def content_controls(self) -> List[ContentControl]:
        """The run-level content controls in this paragraph, in document order.

        The runs inside them appear in `.runs` as though the wrapper were not there;
        this is how the wrapper itself is reached.
        """
        from docx.sdt import ContentControl

        return [ContentControl(sdt, self) for sdt in self._p.xpath("./w:sdt")]

    def add_field(
        self,
        instruction: str,
        *,
        dirty: bool = True,
        simple: bool = False,
        result: str | None = None,
    ) -> Field:
        """Append a field for `instruction` and return it.

        `instruction` is the field code including its switches, for example
        ``"PAGE"`` or ``r'TOC \\o "1-3" \\h'``. The builders in :mod:`docx.fields` write
        the ones people usually want::

            from docx import fields

            paragraph.add_field(fields.page_number())
            paragraph.add_field(fields.table_of_contents(levels=(1, 2)))
            paragraph.add_field(fields.cross_reference("intro"))

        **The result is not computed here and cannot be.** A `PAGE` field has no page
        number and a `TOC` is empty until Word opens the document and works them out.
        `dirty` sets `w:dirty`, asking Word to refresh this field on open; setting
        :attr:`.Settings.update_fields_on_open` asks it to refresh every field, which is
        what a generated table of contents needs.

        A complex field is written by default, as Word does. Pass `simple` to write a
        `w:fldSimple` instead, which is more compact and equally valid but which some
        other consumers handle less well. `result` supplies a cached result to display
        until Word refreshes the field; it is only meaningful for a simple field, and
        passing it for a complex one raises |ValueError|.
        """
        from docx.fields import Field, new_complex_field

        instruction = f" {instruction.strip()} "

        if simple:
            fldSimple = cast("CT_SimpleField", OxmlElement("w:fldSimple"))
            fldSimple.instr = instruction
            if dirty:
                fldSimple.dirty = True
            if result:
                Run(fldSimple.add_r(), self).text = result
            self._p.append(fldSimple)
            return Field(fldSimple, self, instruction, result or "")

        if result is not None:
            raise ValueError(
                "`result` applies only to a simple field; a complex field's cached"
                " result is the content between its 'separate' and 'end' field"
                " characters, which Word writes when it computes the result"
            )

        runs = new_complex_field(instruction, dirty=dirty)
        for r in runs:
            self._p.append(r)
        begin = cast("CT_FldChar", runs[0][0])
        return Field(begin, self, instruction, "")

    @property
    def fields(self) -> List[Field]:
        """A |Field| for each field in this paragraph, in document order.

        Outermost first: a field nested in the result of another — a `PAGEREF` inside a
        table-of-contents entry — follows the field containing it.

        A complex field can begin in one paragraph and end in a later one, which is what
        a table of contents does. Such a field does not appear here, in any of the
        paragraphs it covers, because its extent cannot be determined from one paragraph
        alone; use :attr:`.Document.fields`, which searches the whole body. The fields
        wholly inside this paragraph, including those in a table-of-contents entry, do
        appear.
        """
        from docx.fields import iter_fields

        return list(iter_fields(self._p, self))

    @property
    def form_fields(self) -> List[FormField]:
        """A |FormField| instance for each legacy form field in this paragraph.

        A form field is a complex field, so it may begin in one paragraph and end in
        another; it is listed with the paragraph its "begin" field-character is in.
        """
        return list(iter_form_fields(self._p, self))

    @property
    def hyperlinks(self) -> List[Hyperlink]:
        """A |Hyperlink| instance for each hyperlink in this paragraph."""
        return [Hyperlink(hyperlink, self) for hyperlink in self._p.hyperlink_lst]

    def insert_paragraph_before(
        self, text: str | None = None, style: str | ParagraphStyle | None = None
    ) -> Paragraph:
        """Return a newly created paragraph, inserted directly before this paragraph.

        If `text` is supplied, the new paragraph contains that text in a single run. If
        `style` is provided, that style is assigned to the new paragraph.
        """
        paragraph = self._insert_paragraph_before()
        if text:
            paragraph.add_run(text)
        if style is not None:
            paragraph.style = style
        return paragraph

    def iter_inner_content(self) -> Iterator[Run | Hyperlink]:
        """Generate the runs and hyperlinks in this paragraph, in the order they appear.

        The content in a paragraph consists of both runs and hyperlinks. This method
        allows accessing each of those separately, in document order, for when the
        precise position of the hyperlink within the paragraph text is important. Note
        that a hyperlink itself contains runs.
        """
        for r_or_hlink in self._p.inner_content_elements:
            yield (
                Run(r_or_hlink, self)
                if isinstance(r_or_hlink, CT_R)
                else Hyperlink(r_or_hlink, self)
            )

    def isolate_run(self, start: int, end: int) -> Run:
        """Return the character range `[start, end)` of this paragraph as a single run.

        The runs covering the range are split as needed so that the range is exactly one
        run, which can then be formatted independently of the text around it::

            paragraph.text = "the important part matters"
            paragraph.isolate_run(4, 13).bold = True

        Offsets are measured against :attr:`text`, so a tab counts as one character and
        a line break as one newline.

        Word splits a paragraph into runs for reasons unrelated to formatting, so the
        range being asked for is very often not a run already; that is what this is for.
        Where the range already lies within one run and covers all of it, that run is
        returned unchanged.

        When the range spans runs with different formatting they are merged, and the
        formatting of the run containing `start` applies to the whole range. Raises
        |ValueError| if the range spans a hyperlink boundary, where merging would move
        text into or out of the link: replace or format the parts separately, or use
        :meth:`replace_text`, which handles such a range without merging.
        """
        from docx.oxml.text.isolate import isolate_range

        runs = isolate_range(self._p, start, end)
        if not runs:
            raise ValueError(
                f"character range ({start}, {end}) is empty or lies beyond the end of"
                " the paragraph text"
            )

        first = runs[0]
        parent = first.getparent()
        if any(r.getparent() is not parent for r in runs[1:]):
            raise ValueError(
                f"character range ({start}, {end}) spans a hyperlink or similar"
                " boundary and cannot be isolated into a single run"
            )

        for r in runs[1:]:
            for element in r.xpath("./*[not(self::w:rPr)]"):
                first.append(element)
            parent.remove(r)

        return Run(first, self)

    @property
    def numbering(self) -> ParagraphNumbering | None:
        """The list membership of this paragraph, |None| when it is not in a list.

        Exposes the list this paragraph belongs to and its level within it::

            if paragraph.numbering:
                print(paragraph.numbering.num_id, paragraph.numbering.level)

        Numbering applied by the paragraph's style is resolved too — that is how the
        built-in "List Number" and "List Bullet" styles number a paragraph carrying no
        numbering markup of its own — and :attr:`.ParagraphNumbering.from_style` says
        which it was.
        """
        from docx.numbering import Numbering, ParagraphNumbering, get_paragraph_numbering

        part = self.part.document_part
        resolved = get_paragraph_numbering(self._p, part)
        if resolved is None:
            return None
        num_id, level, from_style = resolved
        if not part.has_numbering_part:
            return None
        return ParagraphNumbering(
            num_id, level, Numbering(part.numbering_part.element, part), from_style
        )

    def set_numbering(self, num_id: int, level: int = 0) -> None:
        """Put this paragraph in the list `num_id` at `level`.

        This is how a paragraph joins an existing list, or starts one, without editing
        the numbering part by hand::

            first = document.add_paragraph("one", style="List Number")
            second = document.add_paragraph("two")
            second.set_numbering(first.numbering.num_id)

        `num_id` must name a list already defined in the numbering part; use
        :attr:`.Document.numbering` to find one. Applying numbering directly like this
        overrides whatever the paragraph's style would apply.
        """
        numPr = self._p.get_or_add_pPr().get_or_add_numPr()
        numPr.numId_val = num_id
        numPr.ilvl_val = level

    def remove_numbering(self) -> None:
        """Take this paragraph out of any list it is in.

        Where the numbering comes from the paragraph's style rather than the paragraph,
        a `w:numId` of 0 is written, which is how Word switches numbering off for one
        paragraph without changing its style.
        """
        pPr = self._p.pPr
        if pPr is None:
            return
        if self.numbering is not None and self.numbering.from_style:
            numPr = pPr.get_or_add_numPr()
            numPr.numId_val = 0
            numPr.ilvl_val = None
            return
        pPr._remove_numPr()  # pyright: ignore[reportPrivateUsage]

    def restart_numbering(self, start: int = 1) -> int:
        """Restart the list this paragraph is in, so it begins again at `start`.

        Returns the `num_id` of the new list. Raises |ValueError| when this paragraph is
        not in a list.

        In OOXML a list is not restarted by resetting a counter — there is no counter to
        reset. A second `w:num` is created on the same abstract definition, carrying a
        `w:startOverride`, and the paragraphs that should begin again are pointed at it.
        This paragraph and every later one in the same list are repointed, which is what
        Word's own "Restart at 1" does; paragraphs before it keep the original sequence.
        """
        from docx.numbering import Numbering

        numbering_info = self.numbering
        if numbering_info is None:
            raise ValueError("this paragraph is not in a list, so has no numbering to restart")

        part = self.part.document_part
        numbering = Numbering(part.numbering_part.element, part)
        new_definition = numbering.restart(
            numbering_info.num_id, ilvl=numbering_info.level, start=start
        )

        # -- each repointed paragraph keeps its own level; a restart changes which list
        # -- a paragraph is in, not how deeply nested it is --
        for p, ilvl in self._following_paragraphs_in_list(numbering_info.num_id):
            Paragraph(p, self._parent).set_numbering(new_definition.num_id, ilvl)

        return new_definition.num_id

    def _following_paragraphs_in_list(self, num_id: int) -> List[tuple[CT_P, int]]:
        """`(paragraph, level)` for this paragraph and each later one in list `num_id`."""
        from docx.numbering import get_paragraph_numbering, iter_story_paragraphs

        part = self.part.document_part
        found: List[tuple[CT_P, int]] = []
        reached_self = False
        for p in iter_story_paragraphs(part.element):
            if p is self._p:
                reached_self = True
            if not reached_self:
                continue
            resolved = get_paragraph_numbering(p, part)
            if resolved is not None and resolved[0] == num_id:
                found.append((p, resolved[1]))
        return found

    @property
    def list_number(self) -> str | None:
        """The number this paragraph displays as a list item, e.g. `"2."` or `"a)"`.

        |None| when the paragraph is not in a list. The number is nowhere in the
        document body — Word computes it from `numbering.xml` at display time — so it is
        computed here the same way, honouring the level, the start value, `w:lvlRestart`
        and any `w:startOverride`.

        Computing it means walking every paragraph before this one, because a list
        number depends on all of them. Reading this for every paragraph of a document is
        therefore quadratic; use :attr:`.Document.list_numbers`, which walks once.

        A level whose format is one of the locale-specific ones falls back to decimal;
        see :attr:`.NumberingLevel.is_renderable`.
        """
        from docx.numbering import compute_list_numbers, iter_story_paragraphs

        part = self.part.document_part
        for p, number in compute_list_numbers(iter_story_paragraphs(part.element), part):
            if p is self._p:
                return number
        return None

    @property
    def math(self) -> List[Math]:
        """The equations in this paragraph, in document order.

        Word stores an equation as OMML (`m:oMath`), a notation of its own with no
        overlap with the wordprocessing run content, so an equation appears in neither
        :attr:`runs` nor :attr:`text`::

            >>> paragraph.text
            'The result is  for all n'
            >>> [m.text for m in paragraph.math]
            ['x2+y2']

        **Equation text is deliberately not part of** :attr:`text`. Including it would
        be more truthful about what the document says, but :meth:`replace_text` and the
        run-isolating machinery underneath it measure offsets against :attr:`text` and
        can only cut at run boundaries — text they cannot reach would silently
        mis-target every replacement after the first equation in a paragraph. A wrong
        edit is worse than a missing character.
        """
        from docx.math import math_list

        return math_list(self._p, self)

    @property
    def paragraph_format(self):
        """The |ParagraphFormat| object providing access to the formatting properties
        for this paragraph, such as line spacing and indentation."""
        return ParagraphFormat(self._element)

    def replace_text(
        self,
        old: str,
        new: str,
        *,
        count: int = -1,
        regex: bool = False,
        flags: int = 0,
    ) -> int:
        """Replace occurrences of `old` with `new` in this paragraph; return how many.

        The match is made against :attr:`text`, so it succeeds whether or not Word split
        the text across runs — which it routinely does, for spell-check state, language
        tagging and revision marks. This is why assigning to `run.text` so often appears
        to do nothing.

        `new` takes the formatting of the run holding the first replaced character. When
        the match spans runs formatted differently, the rest of the matched text is
        removed along with its formatting; the runs themselves stay, so a hyperlink,
        bookmark, comment range or field only partly covered keeps its structure.

        `count` limits the number of replacements, -1 meaning all of them. Set `regex`
        to treat `old` as a regular expression, in which case `new` may refer to capture
        groups as ``\\1`` or ``\\g<name>``; `flags` is passed to :func:`re.compile`.
        Without `regex`, `old` is matched literally however many metacharacters it
        contains.

        Text inside a content control is replaced too, and a control showing its
        placeholder is marked as holding a real value, since that is what it now holds.
        A field instruction (`w:instrText`) is never matched or altered — it is not
        document text, and editing one breaks the field.
        """
        from docx.text.search import compile_pattern, replace_in_paragraph

        pattern = compile_pattern(old, regex, flags)
        return replace_in_paragraph(self._p, pattern, new, count, regex)

    @property
    def original_text(self) -> str:
        """This paragraph's text as it read before its tracked changes.

        Deleted text is included and inserted text is not — the reverse of :attr:`text`,
        which is the document as it now reads. Identical to :attr:`text` for a paragraph
        carrying no revisions.

        Neither is "the text with markup shown": Word displays deletions struck through
        alongside insertions, which is a rendering rather than a string. These two are
        the two readings that are actually well defined.
        """
        from docx.oxml.revision import iter_original_run_content, run_original_text

        return "".join(
            run_original_text(e) if e.tag == qn("w:r") else _original_text_of(e)
            for e in iter_original_run_content(self._p)
        )

    @property
    def revisions(self) -> List[Revision]:
        """A |Revision| for each tracked change in this paragraph, in document order.

        Includes a revision of the paragraph mark itself, which records that the
        paragraph was split off from, or merged with, the one after it.
        """
        from docx.revisions import iter_revisions

        return list(iter_revisions(self._p, self))

    def accept_all_revisions(self) -> int:
        """Accept every tracked change in this paragraph; return how many were applied.

        See :meth:`.Revision.accept`.
        """
        from docx.revisions import apply_all

        return apply_all(self._p, self, accept=True)

    def reject_all_revisions(self) -> int:
        """Reject every tracked change in this paragraph; return how many were applied.

        See :meth:`.Revision.reject`.
        """
        from docx.revisions import apply_all

        return apply_all(self._p, self, accept=False)

    @property
    def rendered_page_breaks(self) -> List[RenderedPageBreak]:
        """All rendered page-breaks in this paragraph.

        Most often an empty list, sometimes contains one page-break, but can contain
        more than one is rare or contrived cases.
        """
        return [RenderedPageBreak(lrpb, self) for lrpb in self._p.lastRenderedPageBreaks]

    @property
    def runs(self) -> List[Run]:
        """Sequence of |Run| instances corresponding to the <w:r> elements in this
        paragraph.

        Includes runs wrapped in a run-level `w:sdt` (content control); the content of
        such a control would otherwise be invisible.
        """
        return [r for r in self.iter_inner_content() if isinstance(r, Run)]

    @property
    def style(self) -> ParagraphStyle | None:
        """Read/Write.

        |_ParagraphStyle| object representing the style assigned to this paragraph. If
        no explicit style is assigned to this paragraph, its value is the default
        paragraph style for the document. A paragraph style name can be assigned in lieu
        of a paragraph style object. Assigning |None| removes any applied style, making
        its effective value the default paragraph style for the document.
        """
        style_id = self._p.style
        style = self.part.get_style(style_id, WD_STYLE_TYPE.PARAGRAPH)
        return cast(ParagraphStyle, style)

    @style.setter
    def style(self, style_or_name: str | ParagraphStyle | None):
        style_id = self.part.get_style_id(style_or_name, WD_STYLE_TYPE.PARAGRAPH)
        self._p.style = style_id

    @property
    def text(self) -> str:
        """The textual content of this paragraph.

        The text includes the visible-text portion of any hyperlinks in the paragraph.
        Tabs and line breaks in the XML are mapped to ``\\t`` and ``\\n`` characters
        respectively.

        For a paragraph carrying tracked changes this is the text as the document now
        reads — with every revision accepted, so inserted text is included and deleted
        text is not. :attr:`original_text` is the reading from before the changes.

        Assigning text to this property causes all existing paragraph content to be
        replaced with a single run containing the assigned text. A ``\\t`` character in
        the text is mapped to a ``<w:tab/>`` element and each ``\\n`` or ``\\r``
        character is mapped to a line break. Paragraph-level formatting, such as style,
        is preserved. All run-level formatting, such as bold or italic, is removed.
        """
        return self._p.text

    @text.setter
    def text(self, text: str | None):
        self.clear()
        self.add_run(text)

    def _insert_paragraph_before(self):
        """Return a newly created paragraph, inserted directly before this paragraph."""
        p = self._p.add_p_before()
        return Paragraph(p, self._parent)


def _original_text_of(element) -> str:
    """The pre-revision text of a `w:hyperlink`, which holds runs of its own."""
    from docx.oxml.revision import iter_original_run_content, run_original_text

    return "".join(
        run_original_text(e) if e.tag == qn("w:r") else _original_text_of(e)
        for e in iter_original_run_content(element)
    )
