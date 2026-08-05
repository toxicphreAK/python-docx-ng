"""Custom element classes for embedded OLE objects — `w:object`.

Word can embed a whole file inside a document — a spreadsheet, a PDF, another document —
displayed as an icon or a preview image that opens the original application on
double-click. The markup is a `w:object` in a run, holding a VML `v:shape` for the
visual and an `o:OLEObject` naming the relationship to the embedded part under
`word/embeddings/`.

The visual is VML, not DrawingML, so none of the `Run.add_picture()` machinery applies.
VML attribute names are not namespace-qualified the way the `w:` ones are, and their
case is inconsistent — `ProgID`, `ShapeID`, `DrawAspect` — so they are taken from
`ref/xsd/vml-officeDrawing.xsd` rather than from a sample document.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from docx.oxml.ns import qn
from docx.oxml.simpletypes import ST_RelationshipId, XsdString
from docx.oxml.xmlchemy import BaseOxmlElement, OptionalAttribute

if TYPE_CHECKING:
    pass


class CT_OLEObject(BaseOxmlElement):
    """`o:OLEObject`, the element identifying the embedded file and its application."""

    Type: str | None = OptionalAttribute("Type", XsdString)  # pyright: ignore
    ProgID: str | None = OptionalAttribute("ProgID", XsdString)  # pyright: ignore
    ShapeID: str | None = OptionalAttribute("ShapeID", XsdString)  # pyright: ignore
    DrawAspect: str | None = OptionalAttribute("DrawAspect", XsdString)  # pyright: ignore
    ObjectID: str | None = OptionalAttribute("ObjectID", XsdString)  # pyright: ignore
    rId: str | None = OptionalAttribute("r:id", ST_RelationshipId)  # pyright: ignore
    UpdateMode: str | None = OptionalAttribute("UpdateMode", XsdString)  # pyright: ignore


class CT_Object(BaseOxmlElement):
    """`w:object`, the run-level container for an embedded or linked OLE object."""

    @property
    def oleObject(self) -> CT_OLEObject | None:
        """The `o:OLEObject` child, or |None| for a `w:object` that has none.

        Reached by `find` rather than a declared child because `w:object` admits any
        `v:` or `o:` element in any order, so there is no schema sequence to place a
        `ZeroOrOne` against.
        """
        return self.find(qn("o:OLEObject"))  # pyright: ignore[reportReturnType]

    @property
    def shape(self) -> BaseOxmlElement | None:
        """The `v:shape` holding the object's visual, or |None| when there is none."""
        return self.find(qn("v:shape"))

    @property
    def image_rId(self) -> str | None:
        """The relationship id of the icon or preview image, or |None|.

        The image is a `v:imagedata` inside the shape, related in its own right — an
        embedded object is at minimum two relationships plus the run XML.
        """
        shape = self.shape
        if shape is None:
            return None
        imagedata = shape.find(qn("v:imagedata"))
        if imagedata is None:
            return None
        return imagedata.get(qn("r:id"))


def iter_objects(element: BaseOxmlElement) -> List[CT_Object]:
    """The `w:object` elements under `element`, in document order."""
    return element.xpath(".//w:object")
