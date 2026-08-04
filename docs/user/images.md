# Images

## Inline pictures

An inline picture sits in the text flow like a very large character:

```python
from docx import Document
from docx.shared import Inches

document = Document()
document.add_picture("logo.png", width=Inches(1.25))
```

[`Document.add_picture()`][docx.document.Document.add_picture] puts the image in a
paragraph of its own. To place one within a paragraph you are building, use
[`Run.add_picture()`][docx.text.run.Run.add_picture]:

```python
paragraph = document.add_paragraph("As shown here: ")
paragraph.add_run().add_picture("figure.png", width=Inches(2))
```

Giving only `width` or only `height` scales the other to match, preserving the aspect
ratio. Giving neither uses the image's native size, from its own DPI.

## Floating pictures

A floating picture is anchored to something on the page and text wraps around it — a logo
in a corner, a figure beside a paragraph:

```python
from docx.enum.shape import WD_WRAP_TYPE
from docx.shared import Cm

run = document.add_paragraph("Text that flows around the figure. ").add_run()
shape = run.add_float_picture(
    "figure.png",
    width=Cm(4),
    left=Cm(1),
    top=Cm(0.5),
    wrap_type=WD_WRAP_TYPE.SQUARE,
)
```

`left` and `top` are offsets from whatever the image is positioned against, which
`relative_from_h` and `relative_from_v` choose — the column and the paragraph by default,
or the page, the margin, a specific margin, or the character position.

[`WD_WRAP_TYPE`][docx.enum.shape.WD_WRAP_TYPE] controls how text behaves around it:

| Value | Effect |
| --- | --- |
| `SQUARE` | text keeps clear of the image's bounding box |
| `TIGHT` | text follows the image's outline |
| `THROUGH` | text also fills enclosed transparent areas |
| `TOP_BOTTOM` | text breaks above and below, none beside |
| `NONE` | text ignores the image, which then overlaps or underlies it |

To put an image *behind* the text, both settings are needed — `behind_text` takes effect
only when nothing is keeping text out of the way in the first place:

```python
shape.wrap_type = WD_WRAP_TYPE.NONE
shape.behind_text = True
```

For the specific case of a background image on every page, see
[Watermarks](watermarks.md), which handles the header placement for you.

[`Document.floating_shapes`][docx.document.Document.floating_shapes] lists the ones
already in a document, and each shape exposes `width`, `height`, `left`, `top`,
`horizontal_align`, `vertical_align`, `z_order`, `allow_overlap` and
`set_wrap_distance()`.

## Alternative text

Screen readers announce the description; the title is presented separately and generally
not announced, so accessibility depends on the description:

```python
picture = document.add_picture("chart.png", description="Revenue by quarter, 2026")
picture.title = "Revenue chart"
```

Both are read/write on [`InlineShape`][docx.shape.InlineShape] and
[`FloatingShape`][docx.shape.FloatingShape], and both
[`add_picture()`][docx.text.run.Run.add_picture] and
[`add_float_picture()`][docx.text.run.Run.add_float_picture] accept them as arguments.
Assigning `None` removes them:

```python
for shape in document.inline_shapes:
    if not shape.description:
        print("missing alt text")
```

## Supported formats

PNG, JPEG, GIF, BMP, TIFF, WebP, SVG, EMF and WMF.

SVG needs care, because Word will not render one without a raster fallback — it stores
both and shows the fallback in any version that cannot draw the vector:

```python
document.add_picture("diagram.svg", svg_fallback="diagram.png")
```

Without `svg_fallback` the image is embedded but may not display.

The format is detected from the file's own header rather than its extension, so a
mislabelled file still works. An unrecognised one raises
[`UnrecognizedImageError`][docx.image.exceptions.UnrecognizedImageError].
