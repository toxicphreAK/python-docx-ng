"""Settings object, providing access to document-level settings."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from docx.shared import ElementProxy

if TYPE_CHECKING:
    import docx.types as t
    from docx.oxml.settings import CT_Settings
    from docx.oxml.xmlchemy import BaseOxmlElement


class Settings(ElementProxy):
    """Provides access to document-level settings for a document.

    Accessed using the :attr:`.Document.settings` property.
    """

    def __init__(self, element: BaseOxmlElement, parent: t.ProvidesXmlPart | None = None):
        super().__init__(element, parent)
        self._settings = cast("CT_Settings", element)

    @property
    def odd_and_even_pages_header_footer(self) -> bool:
        """True if this document has distinct odd and even page headers and footers.

        Read/write.
        """
        return self._settings.evenAndOddHeaders_val

    @odd_and_even_pages_header_footer.setter
    def odd_and_even_pages_header_footer(self, value: bool):
        self._settings.evenAndOddHeaders_val = value

    @property
    def update_fields_on_open(self) -> bool:
        """True when Word should recalculate every field when it opens this document.

        Read/write. This library cannot compute a field result — a table of contents
        added here is empty, and a `PAGE` field has no page number, because both depend
        on how Word lays the document out. Setting this asks Word to fill them in as
        soon as the document is opened, which is the only way to get a populated table
        of contents out of a generated document.

        Word prompts the reader before updating when the document has a table of
        contents, so a document saved with this set may show that prompt once.
        """
        return self._settings.updateFields_val

    @update_fields_on_open.setter
    def update_fields_on_open(self, value: bool):
        self._settings.updateFields_val = value
