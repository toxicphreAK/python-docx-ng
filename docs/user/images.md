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

## Photos from a phone: EXIF orientation

A camera does not rotate the pixels when you turn it sideways. It stores the sensor's
landscape frame and writes an EXIF `Orientation` tag saying which way up it goes. A
portrait photo off a phone is therefore a *landscape* JPEG with a tag on it, and inserting
it naively puts it in the document on its side — and, if you gave only a width, at the
wrong aspect ratio too, because the height was derived from the stored dimensions.

[`add_picture()`][docx.text.run.Run.add_picture] and
[`add_float_picture()`][docx.text.run.Run.add_float_picture] honour the tag:

```python
shape = document.add_picture("photo-from-phone.jpg", width=Inches(2))

shape.width    # -> Inches(2)
shape.height   # -> Inches(4), from the displayed 2:4 shape, not the stored 4:2
```

The rotation goes into the DrawingML — `a:xfrm/@rot`, in sixtieths of a degree — and never
into the pixels. The image part stays byte-identical to the file on disk, so the sha1
deduplication keeps working and the same photo inserted twice is still one part.

Pass `honor_exif_orientation=False` to insert the stored frame unrotated.

[`Image`][docx.image.image.Image] reports both sets of dimensions, and the distinction is
the whole point:

```python
from docx.image.image import Image

image = Image.from_file("photo-from-phone.jpg")

image.orientation         # -> 6, "rotate 90° clockwise to display"
image.is_rotated          # -> True, this orientation exchanges width and height

image.px_width            # -> 4032, the frame as stored
image.px_display_width    # -> 3024, the frame as a viewer shows it

image.width               # -> the stored width as a Length
image.display_width       # -> the displayed width as a Length
```

`px_width` and `px_height` keep meaning what they always meant — the stored dimensions —
so nothing that read them changed behaviour. The `display_*` accessors are the new ones.
[`scaled_dimensions()`][docx.image.image.Image.scaled_dimensions] scales from the display
aspect ratio by default and takes the same `honor_exif_orientation=False`.

An image whose format cannot carry the tag, or which does not set it, reports
`orientation == 1`, for which everything above is a no-op.

## Reading the images already in a document

The counterpart of `add_picture()`. Each shape hands back the image it displays:

```python
for shape in document.inline_shapes:
    image = shape.image
    if image is None:
        continue                          # -- a chart, a diagram, a linked picture
    print(image.filename, image.content_type, image.px_width, image.px_height)
    Path(image.filename).write_bytes(image.blob)
```

[`InlineShape.image`][docx.shape.InlineShape.image] and
[`FloatingShape.image`][docx.shape.FloatingShape.image] are `None` rather than an error
when there is no image to give — a chart, a SmartArt diagram, a picture linked to a file
on disk rather than embedded, or a relationship the document does not resolve.

For an SVG picture, `.image` is the raster fallback Word displays and
[`.svg_image`][docx.shape.InlineShape.svg_image] the vector source:

```python
shape.image.content_type      # -> "image/png", the fallback
shape.svg_image.content_type  # -> "image/svg+xml", the original
```

[`Document.images`][docx.document.Document.images] is the package-level view — the distinct
images the body embeds, deduplicated, with no shape needed to reach them:

```python
for image in document.images:
    print(image.filename, len(image.blob))
```
