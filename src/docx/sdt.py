"""The |ContentControl| proxy object for a structured document tag (`w:sdt`)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator, List

from docx.oxml.sdt import iter_block_content, iter_run_content
from docx.oxml.text.paragraph import CT_P
from docx.shared import Parented

if TYPE_CHECKING:
    import docx.types as t
    from docx.enum.text import WD_CONTENT_CONTROL_TYPE
    from docx.oxml.sdt import CT_Sdt
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    from docx.text.run import Run


class ContentControl(Parented):
    """Proxy for a `w:sdt` element, a structured document tag or "content control".

    Content controls are what Word uses for form fields in modern documents, for
    template placeholders, and for regions bound to a data source. Their content appears
    in `.paragraphs`, `.iter_inner_content()` and the rest of the read API as though the
    wrapper were not there; this object is how the wrapper itself is inspected.
    """

    def __init__(self, sdt: CT_Sdt, parent: t.ProvidesStoryPart):
        super(ContentControl, self).__init__(parent)
        self._element = self._sdt = sdt

    @property
    def alias(self) -> str | None:
        """The friendly name Word shows on this control, or |None| if not set."""
        return self._sdt.alias_val

    @property
    def id(self) -> int | None:
        """The numeric id of this control, or |None| if not set."""
        return self._sdt.id_val

    @property
    def is_block_level(self) -> bool:
        """|True| when this control wraps block-level content.

        A block-level control contains paragraphs or tables; a run-level control sits
        inside a paragraph and contains runs.
        """
        return bool(self.paragraphs) or bool(self.tables)

    def iter_inner_content(self) -> Iterator[Paragraph | Table]:
        """Generate each |Paragraph| or |Table| in this control, in document order.

        Yields nothing for a run-level control; use `.runs` for one.
        """
        from docx.table import Table
        from docx.text.paragraph import Paragraph

        sdtContent = self._sdt.sdtContent
        if sdtContent is None:
            return
        for element in iter_block_content(sdtContent):
            yield (Paragraph(element, self) if isinstance(element, CT_P) else Table(element, self))

    @property
    def paragraphs(self) -> List[Paragraph]:
        """The paragraphs directly inside this control, in document order."""
        from docx.text.paragraph import Paragraph

        return [Paragraph(p, self) for p in self._inner_block_elements if isinstance(p, CT_P)]

    @property
    def runs(self) -> List[Run]:
        """The runs directly inside this control, for a run-level control.

        Empty for a block-level control; the runs of such a control are reached through
        its paragraphs.
        """
        from docx.oxml.text.run import CT_R
        from docx.text.run import Run

        sdtContent = self._sdt.sdtContent
        if sdtContent is None:
            return []
        return [Run(r, self) for r in iter_run_content(sdtContent) if isinstance(r, CT_R)]

    @property
    def showing_placeholder(self) -> bool:
        """|True| when this control is currently displaying its placeholder text.

        The text of such a control is the prompt shown to the user, not a value they
        entered, which is worth distinguishing when harvesting values from a form.
        """
        return self._sdt.showing_placeholder

    @property
    def tables(self) -> List[Table]:
        """The tables directly inside this control, in document order."""
        from docx.oxml.table import CT_Tbl
        from docx.table import Table

        return [Table(t, self) for t in self._inner_block_elements if isinstance(t, CT_Tbl)]

    @property
    def tag(self) -> str | None:
        """The programmatic identifier of this control, or |None| if not set.

        Unlike `.alias`, the tag is not shown to the user; it is what code binding to a
        template matches on.
        """
        return self._sdt.tag_val

    @property
    def text(self) -> str:
        """All the text inside this control.

        Paragraphs are separated by newlines, as for a table cell.
        """
        return self._sdt.text

    @property
    def type(self) -> WD_CONTENT_CONTROL_TYPE | None:
        """Member of :ref:`WdContentControlType`, or |None| when the control names no
        kind.

        Word treats a control with no declared kind as rich text, but that is a default
        rather than a statement, so it is reported as |None| here.
        """
        return self._sdt.content_control_type

    @property
    def _inner_block_elements(self):
        """The block-level elements inside this control, or an empty list."""
        sdtContent = self._sdt.sdtContent
        return [] if sdtContent is None else list(iter_block_content(sdtContent))
