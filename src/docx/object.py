"""The |EmbeddedObject| proxy — a file embedded in a document as an OLE object.

Word can embed a whole file inside a document and show it as an icon or a preview image
that opens the original application on double-click. The read side matters on its own:
for a document containing embedded attachments there was previously no way to discover
that they exist, let alone extract them.

This is a different thing from the two neighbouring features. `Document.add_alt_chunk()`
imports content and dissolves it into the document when Word opens the file; an OLE
object stays a distinct embedded file. `Run.add_picture()` embeds an image with no
underlying document.
"""

from __future__ import annotations

import os
import re
from typing import IO, TYPE_CHECKING

from docx.opc.constants import CONTENT_TYPE as CT
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.part import Part
from docx.oxml.ns import nsdecls
from docx.oxml.parser import parse_xml
from docx.shared import Emu, Length, StoryChild

if TYPE_CHECKING:
    import docx.types as t
    from docx.image.image import Image
    from docx.oxml.object import CT_Object

#: A shape id of the `_x0000_iNNNN` form Word writes for an OLE object's visual.
_SHAPE_ID_RE = re.compile(r"^_x0000_i(\d+)$")

#: The `ProgID` Word writes for an object it has no better name for. An object whose
#: `ProgID` names no installed application is one Word displays but cannot open, so a
#: caller who knows the right one should say so.
_DEFAULT_PROG_ID = "Package"


class EmbeddedObject(StoryChild):
    """An OLE object embedded in a run — a spreadsheet, a PDF, another document.

    Reached through :attr:`.Run.embedded_objects` or :attr:`.Document.embedded_objects`.
    """

    def __init__(self, object_elm: CT_Object, parent: t.ProvidesStoryPart):
        super().__init__(parent)
        self._element = object_elm
        self._object = object_elm

    def __repr__(self) -> str:
        return "<docx.object.EmbeddedObject prog_id=%r>" % self.prog_id

    @property
    def prog_id(self) -> str | None:
        """The application Word launches for this object, e.g. ``"Excel.Sheet.12"``.

        |None| when the object names none. This is what tells Word which application to
        open; an object whose `ProgID` names nothing installed is one Word shows but
        cannot open.
        """
        oleObject = self._object.oleObject
        return None if oleObject is None else oleObject.ProgID

    @property
    def is_linked(self) -> bool:
        """|True| when the object links to an external file rather than embedding it.

        A linked object's bytes are not in the package, so :attr:`blob` is |None|.
        """
        oleObject = self._object.oleObject
        return oleObject is not None and oleObject.Type == "Link"

    @property
    def shows_icon(self) -> bool:
        """|True| when Word shows this object as an icon rather than a preview."""
        oleObject = self._object.oleObject
        return oleObject is not None and oleObject.DrawAspect == "Icon"

    @property
    def embedded_part(self) -> Part | None:
        """The package part holding the embedded file, or |None|.

        |None| for a linked object, and for an embedded one whose relationship the
        document does not resolve — which is a broken document rather than an error
        here.
        """
        oleObject = self._object.oleObject
        if oleObject is None or oleObject.rId is None or self.is_linked:
            return None
        if oleObject.rId not in self.part.rels:
            return None
        return self.part.rels[oleObject.rId].target_part

    @property
    def blob(self) -> bytes | None:
        """The bytes of the embedded file, or |None| when there are none to give.

        This is the useful half — extracting an attachment from a document::

            for obj in document.embedded_objects:
                if obj.blob is not None:
                    Path(obj.filename or "attachment").write_bytes(obj.blob)
        """
        part = self.embedded_part
        return None if part is None else part.blob

    @property
    def content_type(self) -> str | None:
        """The content type of the embedded part, or |None| when there is no part."""
        part = self.embedded_part
        return None if part is None else part.content_type

    @property
    def filename(self) -> str | None:
        """The partname's basename, e.g. ``"oleObject1.bin"``, or |None|.

        OOXML does not record the original file name of an embedded object; this is the
        name of the part it landed in, which is what a caller extracting it has to work
        with.
        """
        part = self.embedded_part
        return None if part is None else os.path.basename(str(part.partname))

    @property
    def image(self) -> Image | None:
        """The icon or preview image Word displays for this object, or |None|.

        Every OLE object has one — Word cannot render the embedded file itself — so
        |None| means the document is missing it rather than that the object has none.
        """
        rId = self._object.image_rId
        if rId is None or rId not in self.part.rels:
            return None
        return getattr(self.part.rels[rId].target_part, "image", None)


def add_embedded_object(
    run: object,
    path_or_stream: str | os.PathLike[str] | IO[bytes],
    *,
    icon: str | os.PathLike[str] | IO[bytes],
    prog_id: str | None = None,
    width: Length | None = None,
    height: Length | None = None,
) -> EmbeddedObject:
    """Embed `path_or_stream` in `run` as an OLE object; see :meth:`.Run.add_embedded_object`."""
    part = run.part  # pyright: ignore[reportAttributeAccessIssue]
    package = part.package
    assert package is not None

    blob = _read_blob(path_or_stream)
    partname = package.next_partname("/word/embeddings/oleObject%d.bin")
    object_part = Part(partname, CT.OFC_OLE_OBJECT, blob, package)
    object_rId = part.relate_to(object_part, RT.OLE_OBJECT)

    icon_rId, icon_image = part.get_or_add_image(icon)
    cx = width if width is not None else icon_image.width
    cy = height if height is not None else icon_image.height

    ordinal = _next_shape_ordinal(part)
    # -- the shape id must be unique in the document, and `o:OLEObject/@ShapeID` names
    # -- it, so the two are generated together --
    shape_id = "_x0000_i%04d" % ordinal

    object_elm = parse_xml(
        "<w:object %s>\n"
        '  <v:shape id="%s" type="#_x0000_t75" style="width:%.2fpt;height:%.2fpt">\n'
        '    <v:imagedata r:id="%s" o:title=""/>\n'
        "  </v:shape>\n"
        '  <o:OLEObject Type="Embed" ProgID="%s" ShapeID="%s" DrawAspect="Icon"'
        ' ObjectID="_%d" r:id="%s"/>\n'
        "</w:object>"
        % (
            nsdecls("w", "v", "o", "r"),
            shape_id,
            Emu(cx).pt,
            Emu(cy).pt,
            icon_rId,
            prog_id or _DEFAULT_PROG_ID,
            shape_id,
            ordinal,
            object_rId,
        )
    )
    run._r.append(object_elm)  # pyright: ignore[reportPrivateUsage]
    return EmbeddedObject(object_elm, run)  # pyright: ignore[reportArgumentType]


def _next_shape_ordinal(part: object) -> int:
    """The next free number for a `v:shape/@id` of the `_x0000_iNNNN` form.

    `StoryPart.next_id` cannot serve here: it reads unprefixed `id` attributes and keeps
    only the ones that are entirely digits, so a VML shape id is invisible to it and
    every object would be given the same number. The two id spaces are counted
    separately for the same reason `next_bookmark_id` is separate from `next_id`.
    """
    used = {
        int(match.group(1))
        for match in (
            _SHAPE_ID_RE.match(shape_id)
            for shape_id in part.element.xpath(  # pyright: ignore[reportAttributeAccessIssue]
                "//v:shape/@id"
            )
        )
        if match
    }
    return max(used, default=0) + 1


def _read_blob(path_or_stream: str | os.PathLike[str] | IO[bytes]) -> bytes:
    """The bytes of `path_or_stream`, a path or a file-like object open for read."""
    if isinstance(path_or_stream, (str, os.PathLike)):
        with open(os.fspath(path_or_stream), "rb") as f:
            return f.read()
    path_or_stream.seek(0)
    return path_or_stream.read()


def iter_embedded_objects(
    element: object, parent: t.ProvidesStoryPart
) -> list[EmbeddedObject]:
    """The |EmbeddedObject| instances under `element`, in document order."""
    return [
        EmbeddedObject(obj, parent)
        for obj in element.xpath(".//w:object")  # pyright: ignore[reportAttributeAccessIssue]
    ]
