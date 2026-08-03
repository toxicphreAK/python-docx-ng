"""Provides ExtendedProperties, the application-specific document properties.

These are the properties stored in `/docProps/app.xml`, such as the word count, the
editing time and the application that produced the document. They complement the
Dublin-Core properties in `/docProps/core.xml` exposed by |CoreProperties|.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from docx.oxml.extendedprops import CT_ExtendedProperties


class ExtendedProperties:
    """Corresponds to part named ``/docProps/app.xml``.

    Every property reads |None| when the corresponding element is absent from the XML,
    which is the normal state for most of them. Assigning |None| removes the element.

    Word maintains the statistics properties (`pages`, `words`, `characters`,
    `characters_with_spaces`, `lines`, `paragraphs`) itself and recalculates them when
    the document is next opened and repaginated. Values written here are what a reader
    sees before that happens; this library does not compute them.
    """

    def __init__(self, element: CT_ExtendedProperties):
        self._element = element

    @property
    def template(self) -> str | None:
        """Name of the template attached to the document, e.g. "Normal.dotm"."""
        return self._element.text_of("Template")

    @template.setter
    def template(self, value: str | None) -> None:
        self._element.set_text_of("Template", value)

    @property
    def manager(self) -> str | None:
        """Name of the manager recorded for the document."""
        return self._element.text_of("Manager")

    @manager.setter
    def manager(self, value: str | None) -> None:
        self._element.set_text_of("Manager", value)

    @property
    def company(self) -> str | None:
        """Name of the company recorded for the document."""
        return self._element.text_of("Company")

    @company.setter
    def company(self, value: str | None) -> None:
        self._element.set_text_of("Company", value)

    @property
    def application(self) -> str | None:
        """Name of the application that produced the document."""
        return self._element.text_of("Application")

    @application.setter
    def application(self, value: str | None) -> None:
        self._element.set_text_of("Application", value)

    @property
    def app_version(self) -> str | None:
        """Version of the producing application, formatted "MM.mmmm"."""
        return self._element.text_of("AppVersion")

    @app_version.setter
    def app_version(self, value: str | None) -> None:
        self._element.set_text_of("AppVersion", value)

    @property
    def presentation_format(self) -> str | None:
        """Intended presentation format. Rarely set by Word."""
        return self._element.text_of("PresentationFormat")

    @presentation_format.setter
    def presentation_format(self, value: str | None) -> None:
        self._element.set_text_of("PresentationFormat", value)

    @property
    def hyperlink_base(self) -> str | None:
        """Base path that relative hyperlinks in the document resolve against."""
        return self._element.text_of("HyperlinkBase")

    @hyperlink_base.setter
    def hyperlink_base(self, value: str | None) -> None:
        self._element.set_text_of("HyperlinkBase", value)

    @property
    def pages(self) -> int | None:
        """Page count last recorded by the producing application."""
        return self._element.int_of("Pages")

    @pages.setter
    def pages(self, value: int | None) -> None:
        self._element.set_int_of("Pages", value)

    @property
    def words(self) -> int | None:
        """Word count last recorded by the producing application."""
        return self._element.int_of("Words")

    @words.setter
    def words(self, value: int | None) -> None:
        self._element.set_int_of("Words", value)

    @property
    def characters(self) -> int | None:
        """Character count excluding spaces."""
        return self._element.int_of("Characters")

    @characters.setter
    def characters(self, value: int | None) -> None:
        self._element.set_int_of("Characters", value)

    @property
    def characters_with_spaces(self) -> int | None:
        """Character count including spaces."""
        return self._element.int_of("CharactersWithSpaces")

    @characters_with_spaces.setter
    def characters_with_spaces(self, value: int | None) -> None:
        self._element.set_int_of("CharactersWithSpaces", value)

    @property
    def lines(self) -> int | None:
        """Line count last recorded by the producing application."""
        return self._element.int_of("Lines")

    @lines.setter
    def lines(self, value: int | None) -> None:
        self._element.set_int_of("Lines", value)

    @property
    def paragraphs(self) -> int | None:
        """Paragraph count last recorded by the producing application."""
        return self._element.int_of("Paragraphs")

    @paragraphs.setter
    def paragraphs(self, value: int | None) -> None:
        self._element.set_int_of("Paragraphs", value)

    @property
    def total_time(self) -> int | None:
        """Cumulative editing time in minutes."""
        return self._element.int_of("TotalTime")

    @total_time.setter
    def total_time(self, value: int | None) -> None:
        self._element.set_int_of("TotalTime", value)

    @property
    def doc_security(self) -> int | None:
        """Document security flags, e.g. 1 for password-protected, 2 for read-only.

        This records the intent of the producing application. It is not enforced by this
        library and provides no security guarantee.
        """
        return self._element.int_of("DocSecurity")

    @doc_security.setter
    def doc_security(self, value: int | None) -> None:
        self._element.set_int_of("DocSecurity", value)

    @property
    def scale_crop(self) -> bool | None:
        """|True| when the document thumbnail is scaled, |False| when cropped."""
        return self._element.bool_of("ScaleCrop")

    @scale_crop.setter
    def scale_crop(self, value: bool | None) -> None:
        self._element.set_bool_of("ScaleCrop", value)

    @property
    def links_up_to_date(self) -> bool | None:
        """|True| when hyperlinks in the document are known to be current."""
        return self._element.bool_of("LinksUpToDate")

    @links_up_to_date.setter
    def links_up_to_date(self, value: bool | None) -> None:
        self._element.set_bool_of("LinksUpToDate", value)

    @property
    def shared_doc(self) -> bool | None:
        """|True| when the document is flagged as shared between multiple authors."""
        return self._element.bool_of("SharedDoc")

    @shared_doc.setter
    def shared_doc(self, value: bool | None) -> None:
        self._element.set_bool_of("SharedDoc", value)

    @property
    def hyperlinks_changed(self) -> bool | None:
        """|True| when hyperlinks changed and the producing application should update."""
        return self._element.bool_of("HyperlinksChanged")

    @hyperlinks_changed.setter
    def hyperlinks_changed(self, value: bool | None) -> None:
        self._element.set_bool_of("HyperlinksChanged", value)
