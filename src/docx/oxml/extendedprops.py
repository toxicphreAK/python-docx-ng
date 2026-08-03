"""Custom element classes for extended (application) properties XML elements."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, cast

from docx.oxml.ns import nsdecls
from docx.oxml.parser import parse_xml
from docx.oxml.xmlchemy import BaseOxmlElement, ZeroOrOne

if TYPE_CHECKING:
    from lxml.etree import _Element as etree_Element  # pyright: ignore[reportPrivateUsage]


class CT_ExtendedProperties(BaseOxmlElement):
    """`<ep:Properties>` element, the root element of the Extended Properties part.

    Stored as `/docProps/app.xml`. These are the properties Word shows under
    File > Info > Properties that are not Dublin Core, such as the word count and the
    application that wrote the file.

    `CT_Properties` is declared `xsd:all` rather than `xsd:sequence`, so child order
    carries no meaning and every element is optional. Word writes them in its own order,
    which is not the order they appear in the schema. New elements are therefore simply
    appended, and no `successors` bookkeeping is needed.
    """

    get_or_add_Template: Callable[[], etree_Element]

    Template = ZeroOrOne("ep:Template", successors=())
    Manager = ZeroOrOne("ep:Manager", successors=())
    Company = ZeroOrOne("ep:Company", successors=())
    Pages = ZeroOrOne("ep:Pages", successors=())
    Words = ZeroOrOne("ep:Words", successors=())
    Characters = ZeroOrOne("ep:Characters", successors=())
    PresentationFormat = ZeroOrOne("ep:PresentationFormat", successors=())
    Lines = ZeroOrOne("ep:Lines", successors=())
    Paragraphs = ZeroOrOne("ep:Paragraphs", successors=())
    TotalTime = ZeroOrOne("ep:TotalTime", successors=())
    ScaleCrop = ZeroOrOne("ep:ScaleCrop", successors=())
    LinksUpToDate = ZeroOrOne("ep:LinksUpToDate", successors=())
    CharactersWithSpaces = ZeroOrOne("ep:CharactersWithSpaces", successors=())
    SharedDoc = ZeroOrOne("ep:SharedDoc", successors=())
    HyperlinkBase = ZeroOrOne("ep:HyperlinkBase", successors=())
    HyperlinksChanged = ZeroOrOne("ep:HyperlinksChanged", successors=())
    Application = ZeroOrOne("ep:Application", successors=())
    AppVersion = ZeroOrOne("ep:AppVersion", successors=())
    DocSecurity = ZeroOrOne("ep:DocSecurity", successors=())

    _Properties_tmpl = "<ep:Properties %s/>\n" % nsdecls("ep", "vt")

    @classmethod
    def new(cls) -> CT_ExtendedProperties:
        """Return a new `<ep:Properties>` element."""
        return cast(CT_ExtendedProperties, parse_xml(cls._Properties_tmpl))

    def text_of(self, property_name: str) -> str | None:
        """Text of the child element named `property_name`.

        |None| when the element is absent, distinguishing "not recorded" from a value
        that is genuinely the empty string.
        """
        element = getattr(self, property_name)
        if element is None:
            return None
        return element.text or ""

    def set_text_of(self, property_name: str, value: str | None) -> None:
        """Set the text of child element `property_name`, adding it if necessary.

        Assigning |None| removes the element.
        """
        if value is None:
            getattr(self, "_remove_%s" % property_name)()
            return
        element = getattr(self, "get_or_add_%s" % property_name)()
        element.text = value

    def int_of(self, property_name: str) -> int | None:
        """Integer value of child element `property_name`, or |None| if absent.

        Returns |None| rather than raising when the recorded text is not a valid
        integer; these values are written by other applications and a malformed count
        should not make the whole document unreadable.
        """
        text = self.text_of(property_name)
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None

    def set_int_of(self, property_name: str, value: int | None) -> None:
        self.set_text_of(property_name, None if value is None else str(value))

    def bool_of(self, property_name: str) -> bool | None:
        """Boolean value of child element `property_name`, or |None| if absent."""
        text = self.text_of(property_name)
        if not text:
            return None
        return text.strip().lower() in ("true", "1")

    def set_bool_of(self, property_name: str, value: bool | None) -> None:
        self.set_text_of(property_name, None if value is None else str(bool(value)).lower())
