.. _WdLineStyle:

``WD_LINE_STYLE``
=================

Specifies the line style of a table or cell border.

Example::

    from docx.enum.table import WD_LINE_STYLE
    from docx.shared import Pt

    table = document.add_table(3, 3)
    table.borders["top"].line = WD_LINE_STYLE.SINGLE
    table.borders["top"].size = Pt(1)

Only the structural line styles are members here. The ``ST_Border`` schema type also
admits some 170 decorative "page border art" values such as ``"apples"`` and
``"zigZagStitch"``; those are meaningful only on a page border, and Word does not offer
or write them for a table or cell border.

----

NONE
    No border.

SINGLE
    A single solid line.

DOT
    A dotted line.

DASH_SMALL_GAP
    A dashed line with small gaps.

DASH_LARGE_GAP
    A dashed line with large gaps.

DASH_DOT
    A line of alternating dashes and dots.

DASH_DOT_DOT
    A line of dashes each followed by two dots.

DOUBLE
    Two parallel solid lines.

TRIPLE
    Three parallel solid lines.

THIN_THICK_SMALL_GAP
    A thin line and a thick line separated by a small gap.

THICK_THIN_SMALL_GAP
    A thick line and a thin line separated by a small gap.

THIN_THICK_THIN_SMALL_GAP
    A thin, a thick and a thin line separated by small gaps.

THIN_THICK_MED_GAP
    A thin line and a thick line separated by a medium gap.

THICK_THIN_MED_GAP
    A thick line and a thin line separated by a medium gap.

THIN_THICK_THIN_MED_GAP
    A thin, a thick and a thin line separated by medium gaps.

THIN_THICK_LARGE_GAP
    A thin line and a thick line separated by a large gap.

THICK_THIN_LARGE_GAP
    A thick line and a thin line separated by a large gap.

THIN_THICK_THIN_LARGE_GAP
    A thin, a thick and a thin line separated by large gaps.

SINGLE_WAVY
    A single wavy line.

DOUBLE_WAVY
    Two parallel wavy lines.

DASH_DOT_STROKED
    A line of slanting dashes and dots.

EMBOSS_3D
    A line that appears embossed.

ENGRAVE_3D
    A line that appears engraved.

OUTSET
    A line that makes the enclosed area appear raised.

INSET
    A line that makes the enclosed area appear sunken.

THICK
    A single thick solid line. This is an OpenXml value with no ``WdLineStyle``
    counterpart; Word renders it as a heavier ``SINGLE``.

NIL
    No border, and no space reserved for one. Distinct from ``NONE`` only in that
    ``NONE`` is the value Word writes when a border is explicitly turned off, whereas
    ``nil`` also appears as the default in a table style.
