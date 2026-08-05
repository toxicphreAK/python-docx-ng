# pyright: reportImportCycles=false

"""Block item container, used by body, cell, header, etc.

Block level items are things like paragraph and table, although there are a few other
specialized ones like structured document tags.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

from typing_extensions import TypeAlias

from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.shared import StoryChild
from docx.text.paragraph import Paragraph

if TYPE_CHECKING:
    import docx.types as t
    from docx.oxml.comments import CT_Comment
    from docx.oxml.document import CT_Body
    from docx.oxml.section import CT_HdrFtr
    from docx.oxml.table import CT_Tc
    from docx.sdt import ContentControl
    from docx.shared import Length
    from docx.styles.style import ParagraphStyle
    from docx.table import Table

BlockItemElement: TypeAlias = "CT_Body | CT_Comment | CT_HdrFtr | CT_Tc"


class BlockItemContainer(StoryChild):
    """Base class for proxy objects that can contain block items.

    These containers include _Body, _Cell, header, footer, footnote, endnote, comment,
    and text box objects. Provides the shared functionality to add a block item like a
    paragraph or table.
    """

    def __init__(self, element: BlockItemElement, parent: t.ProvidesStoryPart):
        super(BlockItemContainer, self).__init__(parent)
        self._element = element

    def add_paragraph(self, text: str = "", style: str | ParagraphStyle | None = None) -> Paragraph:
        """Return paragraph newly added to the end of the content in this container.

        The paragraph has `text` in a single run if present, and is given paragraph
        style `style`.

        If `style` is |None|, no paragraph style is applied, which has the same effect
        as applying the 'Normal' style.
        """
        paragraph = self._add_paragraph()
        if text:
            paragraph.add_run(text)
        if style is not None:
            paragraph.style = style
        return paragraph

    def add_table(
        self,
        rows: int,
        cols: int,
        width: Length,
        *,
        title: str | None = None,
        description: str | None = None,
    ) -> Table:
        """Return table of `width` having `rows` rows and `cols` columns.

        The table is appended appended at the end of the content in this container.

        `width` is evenly distributed between the table columns.

        `description` is the table's alternative text, which is what a screen reader
        announces and what an accessibility check looks for. `title` is the separate,
        caption-like field Word writes alongside it. Both are omitted from the XML when
        |None|, and are equivalent to assigning `Table.title` and `Table.description`
        after the fact.
        """
        from docx.table import Table

        tbl = CT_Tbl.new_tbl(rows, cols, width)
        self._element._insert_tbl(tbl)  # pyright: ignore[reportPrivateUsage]
        table = Table(tbl, self)
        if title is not None:
            table.title = title
        if description is not None:
            table.description = description
        return table

    def iter_inner_content(self) -> Iterator[Paragraph | Table]:
        """Generate each `Paragraph` or `Table` in this container in document order."""
        from docx.table import Table

        for element in self._element.inner_content_elements:
            yield (Paragraph(element, self) if isinstance(element, CT_P) else Table(element, self))

    @property
    def content_controls(self) -> list[ContentControl]:
        """The structured document tags (content controls) in this container.

        Nested controls are included, in document order, outermost first. The content of
        a control appears in `.paragraphs` and `.iter_inner_content()` as though the
        wrapper were not there; this is how the wrapper itself is reached.
        """
        from docx.sdt import ContentControl

        return [ContentControl(sdt, self) for sdt in self._element.xpath(".//w:sdt")]

    def iter_paragraphs(self, tables: bool = True) -> Iterator[Paragraph]:
        """Generate every |Paragraph| in this container, in document order.

        Unlike :attr:`paragraphs`, this descends into tables when `tables` is |True|,
        including tables nested inside other tables, so it reaches every paragraph in
        the container rather than only the top-level ones.
        """
        for item in self.iter_inner_content():
            if isinstance(item, Paragraph):
                yield item
            elif tables:
                for row in item.rows:
                    for cell in row.cells:
                        yield from cell.iter_paragraphs(tables=True)

    @property
    def paragraphs(self):
        """A list containing the paragraphs in this container, in document order.

        Includes paragraphs wrapped in a `w:sdt` (content control). Read-only.
        """
        return [
            Paragraph(p, self) for p in self._element.inner_content_elements if isinstance(p, CT_P)
        ]

    def replace_text(
        self,
        old: str,
        new: str,
        *,
        count: int = -1,
        regex: bool = False,
        flags: int = 0,
        tables: bool = True,
    ) -> int:
        """Replace occurrences of `old` with `new` in this container; return how many.

        Each paragraph is replaced in as described by :meth:`.Paragraph.replace_text`,
        which is where the details of matching and formatting are documented. Tables are
        included unless `tables` is |False|; `count` of -1 replaces every match and any
        other value is a limit on the total across the whole container.
        """
        from docx.text.search import compile_pattern, replace_in_paragraph

        if count == 0:
            return 0

        pattern = compile_pattern(old, regex, flags)
        replaced = 0
        for paragraph in self.iter_paragraphs(tables=tables):
            remaining = -1 if count < 0 else count - replaced
            replaced += replace_in_paragraph(
                paragraph._p,  # pyright: ignore[reportPrivateUsage]
                pattern,
                new,
                remaining,
                regex,
            )
            if count >= 0 and replaced >= count:
                break
        return replaced

    @property
    def tables(self):
        """A list containing the tables in this container, in document order.

        Includes tables wrapped in a `w:sdt` (content control). Read-only.
        """
        from docx.table import Table

        return [
            Table(tbl, self)
            for tbl in self._element.inner_content_elements
            if isinstance(tbl, CT_Tbl)
        ]

    def _add_paragraph(self):
        """Return paragraph newly added to the end of the content in this container."""
        return Paragraph(self._element.add_p(), self)
