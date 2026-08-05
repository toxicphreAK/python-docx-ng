# pyright: reportPrivateUsage=false

"""Unit test suite for honouring the EXIF `Orientation` tag when inserting an image.

`exif-orientation-6.jpg` and `exif-orientation-1.jpg` are synthesised rather than
photographed: each is a minimal Exif JPEG — SOI, an APP1 segment holding a TIFF IFD with
`Orientation`, `XResolution`, `YResolution` and `ResolutionUnit`, an SOF0 declaring
400x200, and EOI. Stored 400x200 landscape, orientation 6 means "rotate 90 degrees
clockwise for display", so the display size is 200x400 portrait — the shape a photo off
a phone has.
"""

from __future__ import annotations

import pytest

import docx
from docx.image.image import Image
from docx.oxml.ns import qn
from docx.shared import Inches

from .unitutil.file import test_file

_ROTATED = test_file("exif-orientation-6.jpg")
_UPRIGHT = test_file("exif-orientation-1.jpg")


class DescribeImageOrientation:
    """Unit-test suite for the orientation properties on |Image|."""

    def it_reads_the_orientation_tag(self):
        assert Image.from_file(_ROTATED).orientation == 6

    def and_reports_1_when_the_image_declares_none(self):
        assert Image.from_file(_UPRIGHT).orientation == 1

    def and_reports_1_for_a_format_that_cannot_carry_the_tag(self):
        assert Image.from_file(test_file("monty-truth.png")).orientation == 1

    @pytest.mark.parametrize(
        ("orientation", "expected"),
        [
            (1, False),
            (2, False),
            (3, False),
            (4, False),
            (5, True),
            (6, True),
            (7, True),
            (8, True),
        ],
    )
    def it_knows_which_orientations_exchange_width_and_height(
        self, orientation: int, expected: bool
    ):
        image = Image.from_file(_UPRIGHT)
        image._image_header._orientation = orientation

        assert image.is_rotated is expected

    def it_reports_stored_dimensions_from_px_width_and_px_height(self):
        """These keep meaning what they always meant: what is in the file."""
        image = Image.from_file(_ROTATED)

        assert (image.px_width, image.px_height) == (400, 200)

    def and_display_dimensions_from_the_display_pair(self):
        image = Image.from_file(_ROTATED)

        assert (image.px_display_width, image.px_display_height) == (200, 400)
        assert image.display_width == Inches(200 / 72)
        assert image.display_height == Inches(400 / 72)

    def and_the_two_agree_for_an_upright_image(self):
        image = Image.from_file(_UPRIGHT)

        assert image.px_display_width == image.px_width
        assert image.display_height == image.height

    @pytest.mark.parametrize(
        ("orientation", "expected"),
        [
            (1, (0, False)),
            (2, (0, True)),
            (3, (180 * 60000, False)),
            (4, (180 * 60000, True)),
            (5, (270 * 60000, True)),
            (6, (90 * 60000, False)),
            (7, (90 * 60000, True)),
            (8, (270 * 60000, False)),
        ],
    )
    def it_maps_each_orientation_to_a_drawingml_transform(
        self, orientation: int, expected: tuple[int, bool]
    ):
        image = Image.from_file(_UPRIGHT)
        image._image_header._orientation = orientation

        assert image.drawingml_transform == expected


class DescribeOrientationAwareScaling:
    """The bug the issue is about: a width-only scale derived the wrong height."""

    def it_scales_from_the_display_aspect_ratio(self):
        image = Image.from_file(_ROTATED)

        cx, cy = image.scaled_dimensions(width=Inches(2))

        # -- displayed 200x400, so a 2in width is a 4in height --
        assert (cx, cy) == (Inches(2), Inches(4))

    def but_the_stored_ratio_is_used_when_asked(self):
        image = Image.from_file(_ROTATED)

        cx, cy = image.scaled_dimensions(width=Inches(2), honor_exif_orientation=False)

        # -- stored 400x200, so a 2in width is a 1in height --
        assert (cx, cy) == (Inches(2), Inches(1))

    def and_native_size_is_the_display_size(self):
        image = Image.from_file(_ROTATED)

        cx, cy = image.scaled_dimensions()

        assert (cx, cy) == (Inches(200 / 72), Inches(400 / 72))


class DescribeRotationInTheDrawingML:
    """The rotation goes in the markup, never into the pixels."""

    def it_writes_the_rotation_on_the_picture(self):
        document = docx.Document()

        shape = document.add_picture(_ROTATED)

        xfrm = shape._inline.graphic.graphicData.pic.spPr.xfrm
        assert xfrm.rot == 90 * 60000
        assert xfrm.flipH is None

    def and_writes_no_rotation_for_an_upright_image(self):
        document = docx.Document()

        shape = document.add_picture(_UPRIGHT)

        xfrm = shape._inline.graphic.graphicData.pic.spPr.xfrm
        assert xfrm.rot is None
        assert xfrm.flipH is None

    def it_makes_the_inline_extent_the_display_box(self):
        """Otherwise the picture is drawn rotated inside a wrongly-shaped frame."""
        document = docx.Document()

        shape = document.add_picture(_ROTATED, width=Inches(2))

        assert shape.width == Inches(2)
        assert shape.height == Inches(4)

    def and_the_shape_extent_stays_the_unrotated_box(self):
        """`a:ext` is what the shape occupies before rotation about its centre."""
        document = docx.Document()

        shape = document.add_picture(_ROTATED, width=Inches(2))

        spPr = shape._inline.graphic.graphicData.pic.spPr
        assert spPr.cx == Inches(4)
        assert spPr.cy == Inches(2)

    def it_leaves_the_image_bytes_untouched(self):
        """Rotating the pixels would break the sha1 part deduplication."""
        document = docx.Document()

        document.add_picture(_ROTATED)

        image = document.inline_shapes[0].image
        assert image is not None
        with open(_ROTATED, "rb") as f:
            assert image.blob == f.read()

    def and_the_same_image_twice_is_still_one_part(self):
        document = docx.Document()

        document.add_picture(_ROTATED)
        document.add_picture(_ROTATED)

        assert len(document.images) == 1

    def it_can_be_turned_off(self):
        document = docx.Document()

        shape = document.add_picture(_ROTATED, honor_exif_orientation=False)

        xfrm = shape._inline.graphic.graphicData.pic.spPr.xfrm
        assert xfrm.rot is None
        assert shape.width == Inches(400 / 72)

    def it_applies_to_a_floating_picture_too(self):
        document = docx.Document()
        run = document.add_paragraph().add_run()

        shape = run.add_float_picture(_ROTATED)

        xfrm = shape._anchor.graphic.graphicData.pic.spPr.xfrm
        assert xfrm.rot == 90 * 60000
        assert shape.width == Inches(200 / 72)

    def it_writes_a_flip_for_a_mirrored_orientation(self, monkeypatch: pytest.MonkeyPatch):
        from docx.parts.story import StoryPart

        original = StoryPart._image_rIds

        def patched(self, image_descriptor, svg_fallback):
            rId, image, svg_rId = original(self, image_descriptor, svg_fallback)
            image._image_header._orientation = 2
            return rId, image, svg_rId

        monkeypatch.setattr(StoryPart, "_image_rIds", patched)
        document = docx.Document()

        shape = document.add_picture(_UPRIGHT)

        xfrm = shape._inline.graphic.graphicData.pic.spPr.xfrm
        assert xfrm.flipH is True
        assert xfrm.get(qn("a:rot")) is None
