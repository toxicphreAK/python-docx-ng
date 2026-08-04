# Watermarks

A watermark is the faint "DRAFT" or "CONFIDENTIAL" behind the content, or a logo sitting
under it. Word implements one as a shape anchored in the *header*, which is what makes it
appear on every page.

## Adding a text watermark

```python
from docx import Document

document = Document()
document.add_text_watermark("DRAFT")
```

That is the whole of the common case. The defaults reproduce Word's own
"Semitransparent" watermark: light grey Calibri, rotated 315°, sized to the page.

Every section is covered, and within each section the default, first-page and even-page
headers alike — so the watermark does not vanish on a page that uses a different header.
A header shared between sections is written to once.

Appearance is controlled by keyword:

```python
document.add_text_watermark(
    "CONFIDENTIAL",
    font="Arial",
    color="FF0000",
    angle=0,
    opacity=0.4,
    bold=True,
)
```

- `color` is an RGB hex string, without a leading `#`
- `angle` is degrees; `315` is Word's diagonal, `0` is horizontal
- `opacity` sets true VML transparency, which is subtler than picking a pale colour
- `font_size`, `width` and `height` take a [`Length`][docx.shared.Length]; leaving
  `font_size` unset scales the text to the box

## An image watermark

```python
document.add_image_watermark("logo.png", scale=0.75)
```

`washout` is on by default and applies Word's brightness-and-contrast correction — that
is what makes a logo read as a background rather than sitting opaquely over the text.
Turn it off for an image that is already faint:

```python
document.add_image_watermark("logo.png", washout=False)
```

## One section only

The same three methods exist on [`Section`][docx.section.Section], which is how a
watermark is applied to part of a document rather than all of it:

```python
document.sections[0].add_text_watermark("DRAFT")
```

## Reading and removing

[`Document.watermarks`][docx.document.Document.watermarks] returns what is there:

```python
for watermark in document.watermarks:
    print(watermark.text, watermark.is_image)
```

[`Watermark.text`][docx.watermark.Watermark.text] is `None` for an image watermark.

Remove them all, or one at a time:

```python
document.remove_watermark()          # -> how many were removed

for watermark in list(document.watermarks):
    watermark.remove()
```

[`remove_watermark()`][docx.document.Document.remove_watermark] exists on
[`Section`][docx.section.Section] too, for removing a single section's watermark.
