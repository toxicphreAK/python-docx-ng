# Working with Styles

This page uses concepts developed in the prior page without introduction. If a term is unfamiliar, consult the prior page [understanding styles](styles-understanding.md) for a definition.

## Access a style

Styles are accessed using the [Document.styles][docx.document.Document.styles] attribute:

```pycon
>>> document = Document()
>>> styles = document.styles
>>> styles
<docx.styles.styles.Styles object at 0x10a7c4f50>
```
The [Styles][docx.styles.styles.Styles] object provides dictionary-style access to defined styles by name:

```pycon
>>> styles['Normal']
<docx.styles.style._ParagraphStyle object at <0x10a7c4f6b>
```
!!! note

    Built-in styles are stored in a WordprocessingML file using their English name, e.g. 'Heading 1', even though users working on a localized version of Word will see native language names in the UI, e.g. 'Kop 1'. Because `python-docx` operates on the WordprocessingML file, style lookups must use the English name. A document available on this external site allows you to create a mapping between local language names and English style names: <http://www.thedoctools.com/index.php?show=mt_create_style_name_list>
>
> User-defined styles, also known as *custom styles*, are not localized and are accessed with the name exactly as it appears in the Word UI.

The [Styles][docx.styles.styles.Styles] object is also iterable. By using the identification properties on [BaseStyle][docx.styles.style.BaseStyle], various subsets of the defined styles can be generated. For example, this code will produce a list of the defined paragraph styles:

```pycon
>>> from docx.enum.style import WD_STYLE_TYPE
>>> styles = document.styles
>>> paragraph_styles = [
...     s for s in styles if s.type == WD_STYLE_TYPE.PARAGRAPH
... ]
>>> for style in paragraph_styles:
...     print(style.name)
...
Normal
Body Text
List Bullet
```
## Apply a style

The [Paragraph][docx.text.paragraph.Paragraph], [Run][docx.text.run.Run], and [Table][docx.table.Table] objects each have a [style][docx.enum.style] attribute. Assigning a style object to this attribute applies that style:

```pycon
>>> document = Document()
>>> paragraph = document.add_paragraph()
>>> paragraph.style
<docx.styles.style._ParagraphStyle object at <0x11a7c4c50>
>>> paragraph.style.name
'Normal'
>>> paragraph.style = document.styles['Heading 1']
>>> paragraph.style.name
'Heading 1'
```
A style name can also be assigned directly, in which case `python-docx` will do the lookup for you:

```pycon
>>> paragraph.style = 'List Bullet'
>>> paragraph.style
<docx.styles.style._ParagraphStyle object at <0x10a7c4f84>
>>> paragraph.style.name
'List Bullet'
```
A style can also be applied at creation time using either the style object or its name:

```pycon
>>> paragraph = document.add_paragraph(style='Body Text')
>>> paragraph.style.name
'Body Text'
>>> body_text_style = document.styles['Body Text']
>>> paragraph = document.add_paragraph(style=body_text_style)
>>> paragraph.style.name
'Body Text'
```
## Add or delete a style

A new style can be added to the document by specifying a unique name and a style type:

```pycon
>>> from docx.enum.style import WD_STYLE_TYPE
>>> styles = document.styles
>>> style = styles.add_style('Citation', WD_STYLE_TYPE.PARAGRAPH)
>>> style.name
'Citation'
>>> style.type
PARAGRAPH (1)
```
Use the `base_style` property to specify a style the new style should inherit formatting settings from:

```pycon
>>> style.base_style
None
>>> style.base_style = styles['Normal']
>>> style.base_style
<docx.styles.style._ParagraphStyle object at 0x10a7a9550>
>>> style.base_style.name
'Normal'
```
A style can be removed from the document simply by calling its [delete][docx.styles.style.BaseStyle.delete] method:

```pycon
>>> styles = document.styles
>>> len(styles)
10
>>> styles['Citation'].delete()
>>> len(styles)
9
```
!!! note

    The `Style.delete` method removes the style's definition from the document. It does not affect content in the document to which that style is applied. Content having a style not defined in the document is rendered using the default style for that content object, e.g. 'Normal' in the case of a paragraph.

## Document defaults

Below every style in the inheritance chain sits `w:docDefaults`, the formatting that
applies to content no style has spoken for. For many documents in the wild it is the only
place the base font is set, so a style walk that stops at `Normal` reads the wrong answer:

```python
document.styles.default_font.name         # -> the document-wide default typeface
document.styles.default_font.size

document.styles.default_paragraph_format.space_after
document.styles.default_paragraph_format.line_spacing
```

[`Styles.default_font`][docx.styles.styles.Styles.default_font] is a
[`Font`][docx.text.font.Font] and
[`Styles.default_paragraph_format`][docx.styles.styles.Styles.default_paragraph_format] a
[`ParagraphFormat`][docx.text.parfmt.ParagraphFormat], so everything documented for those
works here. Both are writable, and setting a document default is the broadest change you
can make to a document's appearance in one statement:

```python
from docx.shared import Pt

document.styles.default_font.name = "Calibri"
document.styles.default_font.size = Pt(11)
```

The inheritance order, most specific first: direct formatting on a run, then its
character style, then the paragraph style, then `w:docDefaults`.

## Define character formatting

Character, paragraph, and table styles can all specify character formatting to be applied to content with that style. All the character formatting that can be applied directly to text can be specified in a style. Examples include font typeface and size, bold, italic, and underline.

Each of these three style types have a `font` attribute providing access to a [Font][docx.text.font.Font] object. A style's [Font][docx.text.font.Font] object provides properties for getting and setting the character formatting for that style.

Several examples are provided here. For a complete set of the available properties, see the [Font][docx.text.font.Font] API documentation.

The font for a style can be accessed like this:

```pycon
>>> from docx import Document
>>> document = Document()
>>> style = document.styles['Normal']
>>> font = style.font
```
Typeface and size are set like this:

```pycon
>>> from docx.shared import Pt
>>> font.name = 'Calibri'
>>> font.size = Pt(12)
```
Many font properties are *tri-state*, meaning they can take the values `True`, `False`, and `None`. `True` means the property is "on", `False` means it is "off". Conceptually, the `None` value means "inherit". Because a style exists in an inheritance hierarchy, it is important to have the ability to specify a property at the right place in the hierarchy, generally as far up the hierarchy as possible. For example, if all headings should be in the Arial typeface, it makes more sense to set that property on the *Heading 1* style and have *Heading 2* inherit from *Heading 1*.

Bold and italic are tri-state properties, as are all-caps, strikethrough, superscript, and many others. See the [Font][docx.text.font.Font] API documentation for a full list:

```pycon
>>> font.bold, font.italic
(None, None)
>>> font.italic = True
>>> font.italic
True
>>> font.italic = False
>>> font.italic
False
>>> font.italic = None
>>> font.italic
None
```
Underline is a bit of a special case. It is a hybrid of a tri-state property and an enumerated value property. `True` means single underline, by far the most common. `False` means no underline, but more often `None` is the right choice if no underlining is wanted since it is rare to inherit it from a base style. The other forms of underlining, such as double or dashed, are specified with a member of the [WdUnderline][docx.enum.text.WD_UNDERLINE] enumeration:

```pycon
>>> font.underline
None
>>> font.underline = True
>>> # or perhaps
>>> font.underline = WD_UNDERLINE.DOT_DASH
```
## Define paragraph formatting

Both a paragraph style and a table style allow paragraph formatting to be specified. These styles provide access to a [ParagraphFormat][docx.text.parfmt.ParagraphFormat] object via their `paragraph_format` property.

Paragraph formatting includes layout behaviors such as justification, indentation, space before and after, page break before, and widow/orphan control. For a complete list of the available properties, consult the API documentation page for the [ParagraphFormat][docx.text.parfmt.ParagraphFormat] object.

Here's an example of how you would create a paragraph style having hanging indentation of 1/4 inch, 12 points spacing above, and widow/orphan control:

```pycon
>>> from docx.enum.style import WD_STYLE_TYPE
>>> from docx.shared import Inches, Pt
>>> document = Document()
>>> style = document.styles.add_style('Indent', WD_STYLE_TYPE.PARAGRAPH)
>>> paragraph_format = style.paragraph_format
>>> paragraph_format.left_indent = Inches(0.25)
>>> paragraph_format.first_line_indent = Inches(-0.25)
>>> paragraph_format.space_before = Pt(12)
>>> paragraph_format.widow_control = True
```
## Use paragraph-specific style properties

A paragraph style has a `next_paragraph_style` property that specifies the style to be applied to new paragraphs inserted after a paragraph of that style. This is most useful when the style would normally appear only once in a sequence, such as a heading. In that case, the paragraph style can automatically be set back to a body style after completing the heading.

In the most common case (body paragraphs), subsequent paragraphs should receive the same style as the current paragraph. The default handles this case well by applying the same style if a next paragraph style is not specified.

Here's an example of how you would change the next paragraph style of the *Heading 1* style to *Body Text*:

```pycon
>>> from docx import Document
>>> document = Document()
>>> styles = document.styles

>>> styles['Heading 1'].next_paragraph_style = styles['Body Text']
```
The default behavior can be restored by assigning `None` or the style itself:

```pycon
>>> heading_1_style = styles['Heading 1']
>>> heading_1_style.next_paragraph_style.name
'Body Text'

>>> heading_1_style.next_paragraph_style = heading_1_style
>>> heading_1_style.next_paragraph_style.name
'Heading 1'

>>> heading_1_style.next_paragraph_style = None
>>> heading_1_style.next_paragraph_style.name
'Heading 1'
```
## Control how a style appears in the Word UI

The properties of a style fall into two categories, *behavioral properties* and *formatting properties*. Its behavioral properties control when and where the style appears in the Word UI. Its formatting properties determine the formatting of content to which the style is applied, such as the size of the font and its paragraph indentation.

There are five behavioral properties of a style:

- [hidden][docx.styles.style.BaseStyle.hidden]
- [unhide_when_used][docx.styles.style.BaseStyle.unhide_when_used]
- [priority][docx.styles.style.BaseStyle.priority]
- [quick_style][docx.styles.style.BaseStyle.quick_style]
- [locked][docx.styles.style.BaseStyle.locked]

See the [style behavior](styles-understanding.md#style-behavior) section in [understanding styles](styles-understanding.md) for a description of how these behavioral properties interact to determine when and where a style appears in the Word UI.

The [priority][docx.styles.latent._LatentStyle.priority] property takes an integer value. The other four style behavior properties are *tri-state*, meaning they can take the value `True` (on), `False` (off), or `None` (inherit).

### Display a style in the style gallery

The following code will cause the 'Body Text' paragraph style to appear first in the style gallery:

```pycon
>>> from docx import Document
>>> document = Document()
>>> style = document.styles['Body Text']

>>> style.hidden = False
>>> style.quick_style = True
>>> style.priorty = 1
```
### Remove a style from the style gallery

This code will remove the 'Normal' paragraph style from the style gallery, but allow it to remain in the recommended list:

```pycon
>>> style = document.styles['Normal']

>>> style.hidden = False
>>> style.quick_style = False
```
## Working with Latent Styles

See the [builtin styles](styles-understanding.md#built-in-styles) and [latent styles](styles-understanding.md#latent-styles) sections in [understanding styles](styles-understanding.md) for a description of how latent styles define the behavioral properties of built-in styles that are not yet defined in the *styles.xml* part of a .docx file.

### Access the latent styles in a document

The latent styles in a document are accessed from the styles object:

```pycon
>>> document = Document()
>>> latent_styles = document.styles.latent_styles
```
A [LatentStyles][docx.styles.latent.LatentStyles] object supports `len`, iteration, and dictionary-style access by style name:

```pycon
>>> len(latent_styles)
161

>>> latent_style_names = [ls.name for ls in latent_styles]
>>> latent_style_names
['Normal', 'Heading 1', 'Heading 2', ... 'TOC Heading']

>>> latent_quote = latent_styles['Quote']
>>> latent_quote
<docx.styles.latent.LatentStyle object at 0x10a7c4f50>
>>> latent_quote.priority
29
```
### Change latent style defaults

The [LatentStyles][docx.styles.latent.LatentStyles] object also provides access to the default behavioral properties for built-in styles in the current document. These defaults provide the value for any undefined attributes of the [_LatentStyle][docx.styles.latent._LatentStyle] definitions and to all behavioral properties of built-in styles having no explicit latent style definition. See the API documentation for the [LatentStyles][docx.styles.latent.LatentStyles] object for the complete set of available properties:

```pycon
>>> latent_styles.default_to_locked
False
>>> latent_styles.default_to_locked = True
>>> latent_styles.default_to_locked
True
```
### Add a latent style definition

A new latent style can be added using the [add_latent_style][docx.styles.latent.LatentStyles.add_latent_style] method on [LatentStyles][docx.styles.latent.LatentStyles]. This code adds a new latent style for the builtin style 'List Bullet', setting it to appear in the style gallery:

```pycon
>>> latent_style = latent_styles['List Bullet']
KeyError: no latent style with name 'List Bullet'
>>> latent_style = latent_styles.add_latent_style('List Bullet')
>>> latent_style.hidden = False
>>> latent_style.priority = 2
>>> latent_style.quick_style = True
```
### Delete a latent style definition

A latent style definition can be deleted by calling its `delete` method:

```pycon
>>> latent_styles['Light Grid']
<docx.styles.latent.LatentStyle object at 0x10a7c4f50>
>>> latent_styles['Light Grid'].delete()
>>> latent_styles['Light Grid']
KeyError: no latent style with name 'Light Grid'
```

## Which styles are in use

```python
document.styles.usage()          # -> a full StyleUsage report
document.styles.unused           # -> the styles nothing reaches
document.styles["Quote"].in_use  # -> True or False
```

"Used" is a reachability closure over every story part in the document, not a scan of the
body — a style that is only ever the `basedOn` of another one is used. See
[Style usage and cleanup](cleanup.md), which also covers
[`Styles.remove_unused()`][docx.styles.styles.Styles.remove_unused] and
[`Document.cleanup()`][docx.document.Document.cleanup].

## Moving styles between documents

[`Styles.copy_style_from()`][docx.styles.styles.Styles.copy_style_from] copies one style
with its dependency closure. Three operations build on it, for whole sets of styles at a
time:

```python
# -- pull a house template's styles into a generated document --
report = document.styles.import_from("house-style.dotx")

# -- push a document's styles out into a template of their own --
document.styles.extract("house.dotx", as_template=True)

# -- or just the styles.xml bytes --
xml = document.styles.extract_xml(["Heading 1", "Heading 2"])
```

See [Templates and embedded files](templates.md#importing-a-templates-styles) for what
each of them does with a name collision and what `report` contains.
