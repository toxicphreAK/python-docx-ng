"""|DocumentPart| and closely related objects."""

from __future__ import annotations

import os
import uuid
from typing import IO, TYPE_CHECKING, cast

from docx.document import Document
from docx.exceptions import StrictOoxmlNotSupportedError
from docx.opc.constants import CONTENT_TYPE as CT
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.packuri import PackURI
from docx.opc.part import Part
from docx.opc.parts.custom_xml import CustomXmlPart, CustomXmlPropertiesPart
from docx.oxml.ns import is_strict_ooxml_tag
from docx.oxml.parser import parse_xml
from docx.parts.altchunk import AltChunkPart
from docx.parts.comments import CommentsPart
from docx.parts.endnotes import EndnotesPart
from docx.parts.footnotes import FootnotesPart
from docx.parts.hdrftr import FooterPart, HeaderPart
from docx.parts.numbering import NumberingPart
from docx.parts.settings import SettingsPart
from docx.parts.story import StoryPart
from docx.parts.styles import StylesPart
from docx.shape import FloatingShapes, InlineShapes
from docx.shared import lazyproperty
from docx.styles.styles import Styles

if TYPE_CHECKING:
    from docx.comments import Comments
    from docx.enum.style import WD_STYLE_TYPE
    from docx.footnotes import Endnotes, Footnotes
    from docx.opc.coreprops import CoreProperties
    from docx.parts.theme import ThemePart
    from docx.settings import Settings
    from docx.styles.style import BaseStyle
    from docx.theme import Theme


class DocumentPart(StoryPart):
    """Main document part of a WordprocessingML (WML) package, aka a .docx file.

    Acts as broker to other parts such as image, core properties, and style parts. It
    also acts as a convenient delegate when a mid-document object needs a service
    involving a remote ancestor. The `Parented.part` property inherited by many content
    objects provides access to this part object for that purpose.
    """

    def add_alt_chunk_part(self, blob: bytes, content_type: str) -> str:
        """Return the rId of a newly-created alt-chunk part holding `blob`.

        Each call adds a new part; alt-chunk content is not deduplicated the way image
        content is, because two embedded documents with identical bytes are rare and
        Word rewrites them independently on import.
        """
        alt_chunk_part = AltChunkPart.new(self.package, blob, content_type)
        return self.relate_to(alt_chunk_part, RT.A_F_CHUNK)

    def add_custom_xml_part(
        self,
        xml: str | bytes,
        schema_refs: tuple[str, ...] = (),
        *,
        item_id: str | None = None,
    ) -> CustomXmlPart:
        """Add a custom XML data store item holding `xml` and return its part.

        Creates the `customXml/itemN.xml` part, its `itemPropsN.xml` sidecar carrying the
        item GUID, and both relationships. `item_id` is that GUID; one is generated at
        random when it is omitted. See :meth:`.Document.add_custom_xml_part`.
        """
        package = self.package
        assert package is not None

        blob = xml.encode("utf-8") if isinstance(xml, str) else xml
        item_partname = package.next_partname("/customXml/item%d.xml")
        # -- the props part takes its number from its item rather than being numbered
        # -- independently; Word pairs the two by number --
        props_partname = PackURI(str(item_partname).replace("/item", "/itemProps"))

        item_part = CustomXmlPart.new(package, item_partname, parse_xml(blob))
        props_part = CustomXmlPropertiesPart.new(
            package,
            props_partname,
            item_id if item_id is not None else "{%s}" % str(uuid.uuid4()).upper(),
            schema_refs,
        )
        item_part.relate_to(props_part, RT.CUSTOM_XML_PROPS)
        self.relate_to(item_part, RT.CUSTOM_XML)
        return item_part

    @property
    def custom_xml_parts(self) -> tuple[CustomXmlPart, ...]:
        """The custom XML data store items related from this document part.

        In relationship-id order, which is the order Word writes them and the order the
        `itemN.xml` numbering follows.
        """
        return tuple(
            rel.target_part
            for rel in self.rels.values()
            if rel.reltype == RT.CUSTOM_XML and not rel.is_external
        )

    @property
    def vba_project(self) -> bytes | None:
        """The bytes of `word/vbaProject.bin`, or |None| when there is no macro project."""
        part = self._vba_project_part
        return None if part is None else part.blob

    @vba_project.setter
    def vba_project(self, blob: bytes | None) -> None:
        if blob is None:
            self.remove_vba_project()
            return

        package = self.package
        assert package is not None

        part = self._vba_project_part
        if part is not None:
            part._blob = blob  # pyright: ignore[reportPrivateUsage]
        else:
            part = Part(
                PackURI("/word/vbaProject.bin"), CT.MS_VBA_PROJECT, blob, package
            )
            self.relate_to(part, RT.VBA_PROJECT)
        # -- a project on a plain `.docx` is silently ignored by Word unless the main
        # -- part says the document is macro-enabled --
        self.content_type = _macro_enabled_content_type(self.content_type)

    def remove_vba_project(self) -> int:
        """Remove the VBA project and its `vbaData.xml` sibling; return how many parts went.

        The main part's content type is switched back to the non-macro-enabled form, so
        the document does not claim to carry macros it no longer has — Word warns the
        user about those.
        """
        removed = 0
        for reltype in (RT.VBA_PROJECT, RT.VBA_DATA):
            for rId in [rId for rId, rel in self.rels.items() if rel.reltype == reltype]:
                self.drop_rel(rId)
                removed += 1
        if removed:
            self.content_type = _plain_content_type(self.content_type)
        return removed

    @property
    def has_macros(self) -> bool:
        """|True| when this document carries a VBA project."""
        return self._vba_project_part is not None

    @property
    def _vba_project_part(self) -> Part | None:
        """The `word/vbaProject.bin` part, or |None| when there is none."""
        try:
            return self.part_related_by(RT.VBA_PROJECT)
        except KeyError:
            return None

    def add_footer_part(self):
        """Return (footer_part, rId) pair for newly-created footer part."""
        footer_part = FooterPart.new(self.package)
        rId = self.relate_to(footer_part, RT.FOOTER)
        return footer_part, rId

    def add_header_part(self):
        """Return (header_part, rId) pair for newly-created header part."""
        header_part = HeaderPart.new(self.package)
        rId = self.relate_to(header_part, RT.HEADER)
        return header_part, rId

    @property
    def comments(self) -> Comments:
        """|Comments| object providing access to the comments added to this document."""
        return self._comments_part.comments

    @property
    def footnotes(self) -> Footnotes:
        """|Footnotes| object providing access to the footnotes of this document."""
        return self._footnotes_part.footnotes

    @property
    def endnotes(self) -> Endnotes:
        """|Endnotes| object providing access to the endnotes of this document."""
        return self._endnotes_part.endnotes

    @property
    def has_endnotes_part(self) -> bool:
        """|True| when this document already has an endnotes part.

        The endnote counterpart of :attr:`has_footnotes_part`, and used the same way.
        """
        try:
            self.part_related_by(RT.ENDNOTES)
        except KeyError:
            return False
        return True

    @property
    def has_footnotes_part(self) -> bool:
        """|True| when this document already has a footnotes part.

        Reading :attr:`footnotes` creates the part when it is absent, so code that only
        wants to look at footnotes that exist — a document-wide search, say — asks this
        first rather than adding `/word/footnotes.xml` to every document it touches.
        """
        try:
            self.part_related_by(RT.FOOTNOTES)
        except KeyError:
            return False
        return True

    @property
    def core_properties(self) -> CoreProperties:
        """A |CoreProperties| object providing read/write access to the core properties
        of this document."""
        return self.package.core_properties

    @property
    def document(self):
        """A |Document| object providing access to the content of this document.

        Raises |StrictOoxmlNotSupportedError| if the package is an ISO Strict document.
        """
        if is_strict_ooxml_tag(self._element.tag):
            raise StrictOoxmlNotSupportedError(
                "this document is in the ISO/IEC 29500 Strict format, which is not"
                " supported. Its markup uses the Strict namespaces"
                " (http://purl.oclc.org/ooxml/...) rather than the Transitional ones."
                ' Re-save it from Word as "Word Document (.docx)" to convert it.'
            )
        return Document(self._element, self)

    def drop_header_part(self, rId: str) -> None:
        """Remove related header part identified by `rId`."""
        self.drop_rel(rId)

    def footer_part(self, rId: str):
        """Return |FooterPart| related by `rId`."""
        return self.related_parts[rId]

    def get_style(self, style_id: str | None, style_type: WD_STYLE_TYPE) -> BaseStyle:
        """Return the style in this document matching `style_id`.

        Returns the default style for `style_type` if `style_id` is |None| or does not
        match a defined style of `style_type`.
        """
        return self.styles.get_by_id(style_id, style_type)

    def get_style_id(self, style_or_name, style_type):
        """Return the style_id (|str|) of the style of `style_type` matching
        `style_or_name`.

        Returns |None| if the style resolves to the default style for `style_type` or if
        `style_or_name` is itself |None|. Raises if `style_or_name` is a style of the
        wrong type or names a style not present in the document.
        """
        return self.styles.get_style_id(style_or_name, style_type)

    def header_part(self, rId: str):
        """Return |HeaderPart| related by `rId`."""
        return self.related_parts[rId]

    @lazyproperty
    def floating_shapes(self):
        """The |FloatingShapes| instance containing the anchored shapes in the document."""
        return FloatingShapes(self._element.body, self)

    @lazyproperty
    def inline_shapes(self):
        """The |InlineShapes| instance containing the inline shapes in the document."""
        return InlineShapes(self._element.body, self)

    @property
    def has_numbering_part(self) -> bool:
        """|True| when this document already has a numbering part.

        Reading :attr:`numbering_part` creates one when it is absent, so code that only
        wants to look at numbering that exists asks this first rather than adding an
        empty `/word/numbering.xml` to every document it touches.
        """
        try:
            self.part_related_by(RT.NUMBERING)
        except KeyError:
            return False
        return True

    @lazyproperty
    def numbering_part(self) -> NumberingPart:
        """A |NumberingPart| object providing access to the numbering definitions for this document.

        Creates an empty numbering part if one is not present.
        """
        try:
            return cast(NumberingPart, self.part_related_by(RT.NUMBERING))
        except KeyError:
            numbering_part = NumberingPart.new()
            self.relate_to(numbering_part, RT.NUMBERING)
            return numbering_part

    def save(self, path_or_stream: str | os.PathLike[str] | IO[bytes]):
        """Save this document to `path_or_stream`, which can be either a path to a
        filesystem location (a string or ``os.PathLike``) or a file-like object."""
        if isinstance(path_or_stream, os.PathLike):
            path_or_stream = os.fspath(path_or_stream)
        self.package.save(path_or_stream)

    @property
    def settings(self) -> Settings:
        """A |Settings| object providing access to the settings in the settings part of
        this document."""
        return self._settings_part.settings

    @property
    def theme(self) -> Theme | None:
        """A |Theme| object for this document, or |None| when it has no theme part.

        Unlike the styles and settings parts, a theme part is *not* created on demand.
        A theme is a design a document was authored against; synthesising an empty one
        would answer "what typeface is this actually in" with a fiction.
        """
        try:
            theme_part = cast("ThemePart", self.part_related_by(RT.THEME))
        except KeyError:
            return None
        return theme_part.theme

    @property
    def styles(self):
        """A |Styles| object providing access to the styles in the styles part of this
        document.

        The collection is told which document part it belongs to, so a style taken out
        of it can find its own numbering definitions when copied into another document.
        """
        return Styles(self._styles_part.element, self)

    @property
    def _comments_part(self) -> CommentsPart:
        """A |CommentsPart| object providing access to the comments added to this document.

        Creates a default comments part if one is not present.
        """
        try:
            return cast(CommentsPart, self.part_related_by(RT.COMMENTS))
        except KeyError:
            assert self.package is not None
            comments_part = CommentsPart.default(self.package)
            self.relate_to(comments_part, RT.COMMENTS)
            return comments_part

    @property
    def _endnotes_part(self) -> EndnotesPart:
        """An |EndnotesPart| object providing access to the endnotes of this document.

        Creates a default endnotes part if one is not present.
        """
        try:
            return cast(EndnotesPart, self.part_related_by(RT.ENDNOTES))
        except KeyError:
            package = self.package
            assert package is not None
            endnotes_part = EndnotesPart.default(package)
            self.relate_to(endnotes_part, RT.ENDNOTES)
            return endnotes_part

    @property
    def _footnotes_part(self) -> FootnotesPart:
        """A |FootnotesPart| object providing access to the footnotes of this document.

        Creates a default footnotes part if one is not present.
        """
        try:
            return cast(FootnotesPart, self.part_related_by(RT.FOOTNOTES))
        except KeyError:
            package = self.package
            assert package is not None
            footnotes_part = FootnotesPart.default(package)
            self.relate_to(footnotes_part, RT.FOOTNOTES)
            return footnotes_part

    @property
    def _settings_part(self) -> SettingsPart:
        """A |SettingsPart| object providing access to the document-level settings for
        this document.

        Creates a default settings part if one is not present.
        """
        try:
            return cast(SettingsPart, self.part_related_by(RT.SETTINGS))
        except KeyError:
            settings_part = SettingsPart.default(self.package)
            self.relate_to(settings_part, RT.SETTINGS)
            return settings_part

    @property
    def _styles_part(self) -> StylesPart:
        """Instance of |StylesPart| for this document.

        Creates an empty styles part if one is not present.
        """
        try:
            return cast(StylesPart, self.part_related_by(RT.STYLES))
        except KeyError:
            package = self.package
            assert package is not None
            styles_part = StylesPart.default(package)
            self.relate_to(styles_part, RT.STYLES)
            return styles_part


# -- the content type of a main document part, paired with its macro-enabled
# -- counterpart. The two hold identical markup; the difference is whether Word looks
# -- for and runs a VBA project. --
_MACRO_ENABLED_CONTENT_TYPE = {
    CT.WML_DOCUMENT_MAIN: CT.WML_DOCUMENT_MACRO_ENABLED_MAIN,
    CT.WML_TEMPLATE_MAIN: CT.WML_TEMPLATE_MACRO_ENABLED_MAIN,
}
_PLAIN_CONTENT_TYPE = {
    macro_enabled: plain for plain, macro_enabled in _MACRO_ENABLED_CONTENT_TYPE.items()
}


def _macro_enabled_content_type(content_type: str) -> str:
    """The macro-enabled counterpart of `content_type`, or it unchanged."""
    return _MACRO_ENABLED_CONTENT_TYPE.get(content_type, content_type)


def _plain_content_type(content_type: str) -> str:
    """The non-macro-enabled counterpart of `content_type`, or it unchanged."""
    return _PLAIN_CONTENT_TYPE.get(content_type, content_type)
