"""Unit test suite for floating (anchored) shapes."""

from __future__ import annotations

import io

import pytest

import docx
from docx.enum.shape import (
    WD_ANCHOR_ALIGN_H,
    WD_ANCHOR_ALIGN_V,
    WD_ANCHOR_RELATIVE_FROM_H,
    WD_ANCHOR_RELATIVE_FROM_V,
    WD_WRAP_TYPE,
)
from docx.exceptions import InvalidXmlError
from docx.oxml.ns import qn
from docx.shape import FloatingShape
from docx.shared import Cm, Emu

_IMAGE = "tests/test_files/python-icon.png"

# -- the `wp:anchor` child sequence the schema requires, less the optional ones --
_REQUIRED_CHILD_ORDER = [
    "simplePos",
    "positionH",
    "positionV",
    "extent",
    "effectExtent",
    "docPr",
    "cNvGraphicFramePr",
    "graphic",
]


@pytest.fixture
def shape() -> FloatingShape:
    document = docx.Document()
    return document.add_paragraph().add_run().add_float_picture(_IMAGE, width=Cm(3))


class DescribeAddFloatPicture:
    """Unit-test suite for `docx.text.run.Run.add_float_picture`."""

    def it_adds_an_anchored_drawing(self, shape: FloatingShape):
        anchor = shape._anchor

        assert anchor.tag == qn("wp:anchor")
        assert anchor.getparent().tag == qn("w:drawing")

    def it_writes_the_children_in_schema_order(self, shape: FloatingShape):
        """Word refuses to open a document whose `wp:anchor` children are out of order."""
        local_names = [child.tag.split("}")[1] for child in shape._anchor]

        wrap_index = local_names.index("wrapSquare")
        assert local_names[:wrap_index] + local_names[wrap_index + 1 :] == (_REQUIRED_CHILD_ORDER)
        assert wrap_index == 5, "the wrap element follows effectExtent"

    def it_scales_the_picture_the_same_way_an_inline_one_is_scaled(self):
        document = docx.Document()

        shape = document.add_paragraph().add_run().add_float_picture(_IMAGE, width=Cm(3))

        assert shape.width == Cm(3)
        assert shape.height == Cm(3), "the aspect ratio of a square icon is preserved"

    def it_defaults_to_square_wrap_anchored_to_the_column_and_paragraph(self, shape: FloatingShape):
        assert shape.wrap_type == WD_WRAP_TYPE.SQUARE
        assert shape.relative_from_h == WD_ANCHOR_RELATIVE_FROM_H.COLUMN
        assert shape.relative_from_v == WD_ANCHOR_RELATIVE_FROM_V.PARAGRAPH
        assert shape.behind_text is False

    def it_places_the_picture_at_the_requested_offset(self):
        document = docx.Document()

        shape = (
            document.add_paragraph()
            .add_run()
            .add_float_picture(
                _IMAGE,
                width=Cm(3),
                left=Cm(2),
                top=Cm(1),
                relative_from_h=WD_ANCHOR_RELATIVE_FROM_H.PAGE,
                relative_from_v=WD_ANCHOR_RELATIVE_FROM_V.PAGE,
            )
        )

        assert shape.left == Cm(2)
        assert shape.top == Cm(1)
        assert shape.relative_from_h == WD_ANCHOR_RELATIVE_FROM_H.PAGE
        assert shape.relative_from_v == WD_ANCHOR_RELATIVE_FROM_V.PAGE

    def it_carries_the_alt_text_through(self):
        document = docx.Document()

        shape = (
            document.add_paragraph()
            .add_run()
            .add_float_picture(_IMAGE, description="a logo", title="Logo")
        )

        assert shape.description == "a logo"
        assert shape.title == "Logo"


class DescribeFloatingShape:
    """Unit-test suite for `docx.shape.FloatingShape`."""

    @pytest.mark.parametrize(
        ("wrap_type", "expected_tag"),
        [
            (WD_WRAP_TYPE.NONE, "wrapNone"),
            (WD_WRAP_TYPE.SQUARE, "wrapSquare"),
            (WD_WRAP_TYPE.TIGHT, "wrapTight"),
            (WD_WRAP_TYPE.THROUGH, "wrapThrough"),
            (WD_WRAP_TYPE.TOP_BOTTOM, "wrapTopAndBottom"),
        ],
    )
    def it_can_change_the_wrap_type(
        self, shape: FloatingShape, wrap_type: WD_WRAP_TYPE, expected_tag: str
    ):
        shape.wrap_type = wrap_type

        assert shape.wrap_type == wrap_type
        assert shape._anchor.find(qn(f"wp:{expected_tag}")) is not None
        # -- exactly one wrap element: the schema choice allows only one --
        wrap_children = [c for c in shape._anchor if c.tag.split("}")[1].startswith("wrap")]
        assert len(wrap_children) == 1

    def it_keeps_the_wrap_element_in_its_schema_position_when_changed(self, shape: FloatingShape):
        shape.wrap_type = WD_WRAP_TYPE.TOP_BOTTOM

        local_names = [child.tag.split("}")[1] for child in shape._anchor]
        assert local_names.index("wrapTopAndBottom") == 5

    def it_raises_for_an_anchor_with_no_wrap_element(self, shape: FloatingShape):
        anchor = shape._anchor
        anchor.remove(anchor.find(qn("wp:wrapSquare")))

        with pytest.raises(InvalidXmlError, match="none of the five wrap elements"):
            _ = shape.wrap_type

    def it_can_be_put_behind_the_text(self, shape: FloatingShape):
        shape.wrap_type = WD_WRAP_TYPE.NONE
        shape.behind_text = True

        assert shape.behind_text is True
        assert shape._anchor.get("behindDoc") == "1"

    def it_can_be_aligned_instead_of_offset(self, shape: FloatingShape):
        shape.horizontal_align = WD_ANCHOR_ALIGN_H.CENTER
        shape.vertical_align = WD_ANCHOR_ALIGN_V.TOP

        assert shape.horizontal_align == WD_ANCHOR_ALIGN_H.CENTER
        assert shape.vertical_align == WD_ANCHOR_ALIGN_V.TOP

    def it_drops_the_offset_when_an_alignment_is_assigned(self, shape: FloatingShape):
        """The schema allows one of the two; Word ignores a shape carrying both."""
        shape.left = Cm(2)
        assert shape.left == Cm(2)

        shape.horizontal_align = WD_ANCHOR_ALIGN_H.RIGHT

        assert shape.left is None
        assert len(shape._anchor.positionH.findall(qn("wp:posOffset"))) == 0

    def it_drops_the_alignment_when_an_offset_is_assigned(self, shape: FloatingShape):
        shape.horizontal_align = WD_ANCHOR_ALIGN_H.RIGHT

        shape.left = Cm(2)

        assert shape.horizontal_align is None
        assert shape.left == Cm(2)

    def it_can_change_its_size(self, shape: FloatingShape):
        shape.width = Cm(5)
        shape.height = Cm(4)

        assert (shape.width, shape.height) == (Cm(5), Cm(4))
        # -- the picture's own extent tracks the shape's, or Word shows it cropped --
        spPr = shape._anchor.graphic.graphicData.pic.spPr
        assert (spPr.cx, spPr.cy) == (Cm(5), Cm(4))

    def it_knows_and_sets_the_wrap_distance(self, shape: FloatingShape):
        assert shape.wrap_distance == (Emu(0), Emu(114300), Emu(0), Emu(114300))

        shape.set_wrap_distance(top=Cm(1), bottom=Cm(1))

        assert shape.wrap_distance == (Cm(1), Emu(114300), Cm(1), Emu(114300))

    def it_knows_and_sets_its_z_order(self, shape: FloatingShape):
        assert shape.z_order == 0

        shape.z_order = 5

        assert shape.z_order == 5

    def it_can_allow_or_prevent_overlap(self, shape: FloatingShape):
        assert shape.allow_overlap is True

        shape.allow_overlap = False

        assert shape.allow_overlap is False


class DescribeFloatingShapes:
    """Unit-test suite for the `Document.floating_shapes` collection."""

    def it_is_empty_for_a_document_with_no_floating_shapes(self):
        document = docx.Document()
        document.add_paragraph().add_run().add_picture(_IMAGE)

        assert len(document.floating_shapes) == 0
        assert len(document.inline_shapes) == 1

    def it_keeps_floating_and_inline_shapes_in_separate_collections(self):
        document = docx.Document()
        run = document.add_paragraph().add_run()
        run.add_picture(_IMAGE)
        run.add_float_picture(_IMAGE)

        assert len(document.inline_shapes) == 1
        assert len(document.floating_shapes) == 1

    def it_supports_len_iteration_and_indexed_access(self):
        document = docx.Document()
        for _ in range(3):
            document.add_paragraph().add_run().add_float_picture(_IMAGE)

        assert len(document.floating_shapes) == 3
        assert len(list(document.floating_shapes)) == 3
        assert document.floating_shapes[1].width is not None

    def it_raises_on_an_out_of_range_index(self):
        document = docx.Document()

        with pytest.raises(IndexError, match=r"floating shape index \[0\] out of range"):
            document.floating_shapes[0]

    def it_survives_a_round_trip(self):
        document = docx.Document()
        document.add_paragraph().add_run().add_float_picture(
            _IMAGE,
            width=Cm(3),
            left=Cm(2),
            wrap_type=WD_WRAP_TYPE.TOP_BOTTOM,
            behind_text=False,
        )

        stream = io.BytesIO()
        document.save(stream)
        stream.seek(0)

        (shape,) = docx.Document(stream).floating_shapes
        assert shape.wrap_type == WD_WRAP_TYPE.TOP_BOTTOM
        assert shape.left == Cm(2)
        assert shape.width == Cm(3)
