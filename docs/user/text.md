# Working with Text

To work effectively with text, it's important to first understand a little about block-level elements like paragraphs and inline-level objects like runs.

## Block-level vs. inline text objects

The paragraph is the primary block-level object in Word.

A block-level item flows the text it contains between its left and right edges, adding an additional line each time the text extends beyond its right boundary. For a paragraph, the boundaries are generally the page margins, but they can also be column boundaries if the page is laid out in columns, or cell boundaries if the paragraph occurs inside a table cell.

A table is also a block-level object.

An inline object is a portion of the content that occurs inside a block-level item. An example would be a word that appears in bold or a sentence in all-caps. The most common inline object is a *run*. All content within a block container is inside of an inline object. Typically, a paragraph contains one or more runs, each of which contain some part of the paragraph's text.

The attributes of a block-level item specify its placement on the page, such items as indentation and space before and after a paragraph. The attributes of an inline item generally specify the font in which the content appears, things like typeface, font size, bold, and italic.

## Paragraph properties

A paragraph has a variety of properties that specify its placement within its container (typically a page) and the way it divides its content into separate lines.

In general, it's best to define a *paragraph style* collecting these attributes into a meaningful group and apply the appropriate style to each paragraph, rather than repeatedly apply those properties directly to each paragraph. This is analogous to how Cascading Style Sheets (CSS) work with HTML. All the paragraph properties described here can be set using a style as well as applied directly to a paragraph.

The formatting properties of a paragraph are accessed using the [ParagraphFormat][docx.text.parfmt.ParagraphFormat] object available using the paragraph's [paragraph_format][docx.text.paragraph.Paragraph.paragraph_format] property.

### Horizontal alignment (justification)

Also known as *justification*, the horizontal alignment of a paragraph can be set to left, centered, right, or fully justified (aligned on both the left and right sides) using values from the enumeration `WdParagraphAlignment`:

```pycon
>>> from docx.enum.text import WD_ALIGN_PARAGRAPH
>>> document = Document()
>>> paragraph = document.add_paragraph()
>>> paragraph_format = paragraph.paragraph_format

>>> paragraph_format.alignment
None  # indicating alignment is inherited from the style hierarchy
>>> paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
>>> paragraph_format.alignment
CENTER (1)
```
### Indentation

Indentation is the horizontal space between a paragraph and edge of its container, typically the page margin. A paragraph can be indented separately on the left and right side. The first line can also have a different indentation than the rest of the paragraph. A first line indented further than the rest of the paragraph has *first line indent*. A first line indented less has a *hanging indent*.

Indentation is specified using a [Length][docx.shared.Length] value, such as [Inches][docx.shared.Inches], [Pt][docx.shared.Pt], or [Cm][docx.shared.Cm]. Negative values are valid and cause the paragraph to overlap the margin by the specified amount. A value of `None` indicates the indentation value is inherited from the style hierarchy. Assigning `None` to an indentation property removes any directly-applied indentation setting and restores inheritance from the style hierarchy:

```pycon
>>> from docx.shared import Inches
>>> paragraph = document.add_paragraph()
>>> paragraph_format = paragraph.paragraph_format

>>> paragraph_format.left_indent
None  # indicating indentation is inherited from the style hierarchy
>>> paragraph_format.left_indent = Inches(0.5)
>>> paragraph_format.left_indent
457200
>>> paragraph_format.left_indent.inches
0.5
```
Right-side indent works in a similar way:

```pycon
>>> from docx.shared import Pt
>>> paragraph_format.right_indent
None
>>> paragraph_format.right_indent = Pt(24)
>>> paragraph_format.right_indent
304800
>>> paragraph_format.right_indent.pt
24.0
```
First-line indent is specified using the [first_line_indent][docx.text.parfmt.ParagraphFormat.first_line_indent] property and is interpreted relative to the left indent. A negative value indicates a hanging indent:

```pycon
>>> paragraph_format.first_line_indent
None
>>> paragraph_format.first_line_indent = Inches(-0.25)
>>> paragraph_format.first_line_indent
-228600
>>> paragraph_format.first_line_indent.inches
-0.25
```
### Indentation in character units

Word can express an indent as a number of characters rather than an absolute distance,
which is what East Asian typesetting conventions expect and what Word's own dialogue
offers when the document language calls for it. Those values are a separate set of
properties, because they are a different unit and the two cannot both apply:

```pycon
>>> paragraph_format.first_line_indent_chars = 200   # -> two characters
>>> paragraph_format.left_indent_chars = 100         # -> one character
>>> paragraph_format.right_indent_chars
None
```

Values are in **hundredths of a character**, matching the XML — `200` is two characters.
Setting a character-unit property clears its twips counterpart and vice versa, so the two
can never disagree about the same edge.

The absolute properties also read the `w:start` and `w:end` spellings Word writes in
recent files, not only the older `w:left` and `w:right`, so a document produced by a
current version of Word reports the indents it actually has.

### Tab stops

A tab stop determines the rendering of a tab character in the text of a paragraph. In particular, it specifies the position where the text following the tab character will start, how it will be aligned to that position, and an optional leader character that will fill the horizontal space spanned by the tab.

The tab stops for a paragraph or style are contained in a [TabStops][docx.text.tabstops.TabStops] object accessed using the [tab_stops][docx.text.parfmt.ParagraphFormat.tab_stops] property on [ParagraphFormat][docx.text.parfmt.ParagraphFormat]:

```pycon
>>> tab_stops = paragraph_format.tab_stops
>>> tab_stops
<docx.text.tabstops.TabStops object at 0x106b802d8>
```
A new tab stop is added using the [add_tab_stop][docx.text.tabstops.TabStops.add_tab_stop] method:

```pycon
>>> tab_stop = tab_stops.add_tab_stop(Inches(1.5))
>>> tab_stop.position
1371600
>>> tab_stop.position.inches
1.5
```
Alignment defaults to left, but may be specified by providing a member of the [WdTabAlignment][docx.enum.text.WD_TAB_ALIGNMENT] enumeration. The leader character defaults to spaces, but may be specified by providing a member of the [WdTabLeader][docx.enum.text.WD_TAB_LEADER] enumeration:

```pycon
>>> from docx.enum.text import WD_TAB_ALIGNMENT, WD_TAB_LEADER
>>> tab_stop = tab_stops.add_tab_stop(Inches(1.5), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
>>> print(tab_stop.alignment)
RIGHT (2)
>>> print(tab_stop.leader)
DOTS (1)
```
Existing tab stops are accessed using sequence semantics on [TabStops][docx.text.tabstops.TabStops]:

```pycon
>>> tab_stops[0]
<docx.text.tabstops.TabStop object at 0x1105427e8>
```
More details are available in the [TabStops][docx.text.tabstops.TabStops] and [TabStop][docx.text.tabstops.TabStop] API documentation

### Paragraph spacing

The [space_before][docx.text.parfmt.ParagraphFormat.space_before] and [space_after][docx.text.parfmt.ParagraphFormat.space_after] properties control the spacing between subsequent paragraphs, controlling the spacing before and after a paragraph, respectively. Inter-paragraph spacing is *collapsed* during page layout, meaning the spacing between two paragraphs is the maximum of the *space_after* for the first paragraph and the *space_before* of the second paragraph. Paragraph spacing is specified as a [Length][docx.shared.Length] value, often using [Pt][docx.shared.Pt]:

```pycon
>>> paragraph_format.space_before, paragraph_format.space_after
(None, None)  # inherited by default

>>> paragraph_format.space_before = Pt(18)
>>> paragraph_format.space_before.pt
18.0

>>> paragraph_format.space_after = Pt(12)
>>> paragraph_format.space_after.pt
12.0
```
### Line spacing

Line spacing is the distance between subsequent baselines in the lines of a paragraph. Line spacing can be specified either as an absolute distance or relative to the line height (essentially the point size of the font used). A typical absolute measure would be 18 points. A typical relative measure would be double-spaced (2.0 line heights). The default line spacing is single-spaced (1.0 line heights).

Line spacing is controlled by the interaction of the [line_spacing][docx.text.parfmt.ParagraphFormat.line_spacing] and [line_spacing_rule][docx.text.parfmt.ParagraphFormat.line_spacing_rule] properties. [line_spacing][docx.text.parfmt.ParagraphFormat.line_spacing] is either a [Length][docx.shared.Length] value, a (small-ish) `float`, or None. A [Length][docx.shared.Length] value indicates an absolute distance. A `float` indicates a number of line heights. `None` indicates line spacing is inherited. [line_spacing_rule][docx.text.parfmt.ParagraphFormat.line_spacing_rule] is a member of the [WdLineSpacing][docx.enum.text.WD_LINE_SPACING] enumeration or `None`:

```pycon
>>> from docx.shared import Length
>>> paragraph_format.line_spacing
None
>>> paragraph_format.line_spacing_rule
None

>>> paragraph_format.line_spacing = Pt(18)
>>> isinstance(paragraph_format.line_spacing, Length)
True
>>> paragraph_format.line_spacing.pt
18.0
>>> paragraph_format.line_spacing_rule
EXACTLY (4)

>>> paragraph_format.line_spacing = 1.75
>>> paragraph_format.line_spacing
1.75
>>> paragraph_format.line_spacing_rule
MULTIPLE (5)
```
### Spacing in line units

As with indentation, Word can express paragraph spacing as a number of lines rather than
an absolute distance:

```pycon
>>> paragraph_format.space_before_lines = 100   # -> one line
>>> paragraph_format.space_after_lines = 50     # -> half a line
```

Values are in **hundredths of a line**. These are `w:spacing/@w:beforeLines` and
`@w:afterLines`, and Word applies them in preference to the absolute values when both are
present — so as with the character units, setting one clears the other.

### Paragraph borders

A paragraph's borders are spelled the same way as a table's or a cell's — a mapping keyed
by edge name:

```python
from docx.enum.table import WD_LINE_STYLE
from docx.shared import Pt, RGBColor

paragraph_format.borders["bottom"].line = WD_LINE_STYLE.SINGLE
paragraph_format.borders["bottom"].size = Pt(1)
paragraph_format.borders["bottom"].color = RGBColor(0x99, 0x99, 0x99)
```

A paragraph with only a bottom border is how Word draws a horizontal rule, which is the
common reason to want this.

The edges are `top`, `bottom`, `left`, `right`, plus two a table does not have:

- `between` — drawn between *consecutive* paragraphs that carry the same border setting,
  not around each one.
- `bar` — a vertical line at the outer edge, used to mark changed text.

Each edge exposes `line`, `size`, `color` and `space`, and setting `line` to
`WD_LINE_STYLE.NONE` removes the border. For borders around a whole page, see
[Page borders](sections.md#page-borders).

### The paragraph mark

A paragraph ends with a mark — the ¶ Word shows with formatting marks turned on — and that
mark has run properties of its own, stored in `w:pPr/w:rPr`. They are what an *empty*
paragraph is formatted with, because there is no run in it to carry formatting:

```python
paragraph = document.add_paragraph()          # -- empty
paragraph.paragraph_format.mark_font.size = Pt(4)
```

That is the way to make a blank spacer paragraph small, and it is the only place the
formatting of an empty paragraph lives.
[`mark_font`][docx.text.parfmt.ParagraphFormat.mark_font] is a full
[`Font`][docx.text.font.Font], so everything in
[Apply character formatting](#apply-character-formatting) applies to it. It also affects
the mark of a *non*-empty paragraph, which is what decides how tall the last line is.

### Pagination properties

Four paragraph properties, [keep_together][docx.text.parfmt.ParagraphFormat.keep_together], [keep_with_next][docx.text.parfmt.ParagraphFormat.keep_with_next], [page_break_before][docx.text.parfmt.ParagraphFormat.page_break_before], and [widow_control][docx.text.parfmt.ParagraphFormat.widow_control] control aspects of how the paragraph behaves near page boundaries.

[keep_together][docx.text.parfmt.ParagraphFormat.keep_together] causes the entire paragraph to appear on the same page, issuing a page break before the paragraph if it would otherwise be broken across two pages.

[keep_with_next][docx.text.parfmt.ParagraphFormat.keep_with_next] keeps a paragraph on the same page as the subsequent paragraph. This can be used, for example, to keep a section heading on the same page as the first paragraph of the section.

[page_break_before][docx.text.parfmt.ParagraphFormat.page_break_before] causes a paragraph to be placed at the top of a new page. This could be used on a chapter heading to ensure chapters start on a new page.

[widow_control][docx.text.parfmt.ParagraphFormat.widow_control] breaks a page to avoid placing the first or last line of the paragraph on a separate page from the rest of the paragraph.

All four of these properties are *tri-state*, meaning they can take the value `True`, `False`, or `None`. `None` indicates the property value is inherited from the style hierarchy. `True` means "on" and `False` means "off":

```pycon
>>> paragraph_format.keep_together
None  # all four inherit by default
>>> paragraph_format.keep_with_next = True
>>> paragraph_format.keep_with_next
True
>>> paragraph_format.page_break_before = False
>>> paragraph_format.page_break_before
False
```
## Apply character formatting

Character formatting is applied at the Run level. Examples include font typeface and size, bold, italic, and underline.

A [Run][docx.text.run.Run] object has a read-only [font][docx.text.run.Run.font] property providing access to a [Font][docx.text.font.Font] object. A run's [Font][docx.text.font.Font] object provides properties for getting and setting the character formatting for that run.

Several examples are provided here. For a complete set of the available properties, see the [Font][docx.text.font.Font] API documentation.

The font for a run can be accessed like this:

```pycon
>>> from docx import Document
>>> document = Document()
>>> run = document.add_paragraph().add_run()
>>> font = run.font
```
Typeface and size are set like this:

```pycon
>>> from docx.shared import Pt
>>> font.name = 'Calibri'
>>> font.size = Pt(12)
```
Many font properties are *tri-state*, meaning they can take the values `True`, `False`, and `None`. `True` means the property is "on", `False` means it is "off". Conceptually, the `None` value means "inherit". A run exists in the style inheritance hierarchy and by default inherits its character formatting from that hierarchy. Any character formatting directly applied using the [Font][docx.text.font.Font] object overrides the inherited values.

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
Underline is a bit of a special case. It is a hybrid of a tri-state property and an enumerated value property. `True` means single underline, by far the most common. `False` means no underline, but more often `None` is the right choice if no underlining is wanted. The other forms of underlining, such as double or dashed, are specified with a member of the [WdUnderline][docx.enum.text.WD_UNDERLINE] enumeration:

```pycon
>>> font.underline
None
>>> font.underline = True
>>> # or perhaps
>>> font.underline = WD_UNDERLINE.DOT_DASH
```
### Font color

Each [Font][docx.text.font.Font] object has a [ColorFormat][docx.dml.color.ColorFormat] object that provides access to its color, accessed via its read-only [color][docx.text.font.Font.color] property.

Apply a specific RGB color to a font:

```pycon
>>> from docx.shared import RGBColor
>>> font.color.rgb = RGBColor(0x42, 0x24, 0xE9)
```
A font can also be set to a theme color by assigning a member of the [MsoThemeColorIndex][docx.enum.dml.MSO_THEME_COLOR_INDEX] enumeration:

```pycon
>>> from docx.enum.dml import MSO_THEME_COLOR
>>> font.color.theme_color = MSO_THEME_COLOR.ACCENT_1
```
A font's color can be restored to its default (inherited) value by assigning `None` to either the [rgb][docx.dml.color.ColorFormat.rgb] or [theme_color][docx.dml.color.ColorFormat.theme_color] attribute of [ColorFormat][docx.dml.color.ColorFormat]:

```pycon
>>> font.color.rgb = None
```
Determining the color of a font begins with determining its color type:

```pycon
>>> font.color.type
RGB (1)
```
The value of the [type][docx.dml.color.ColorFormat.type] property can be a member of the [MsoColorType][docx.enum.dml.MSO_COLOR_TYPE] enumeration or None. *MSO_COLOR_TYPE.RGB* indicates it is an RGB color. *MSO_COLOR_TYPE.THEME* indicates a theme color. *MSO_COLOR_TYPE.AUTO* indicates its value is determined automatically by the application, usually set to black. (This value is relatively rare.) `None` indicates no color is applied and the color is inherited from the style hierarchy; this is the most common case.

When the color type is *MSO_COLOR_TYPE.RGB*, the [rgb][docx.dml.color.ColorFormat.rgb] property will be an [RGBColor][docx.shared.RGBColor] value indicating the RGB color:

```pycon
>>> font.color.rgb
RGBColor(0x42, 0x24, 0xe9)
```
When the color type is *MSO_COLOR_TYPE.THEME*, the [theme_color][docx.dml.color.ColorFormat.theme_color] property will be a member of [MsoThemeColorIndex][docx.enum.dml.MSO_THEME_COLOR_INDEX] indicating the theme color:

```pycon
>>> font.color.theme_color
ACCENT_1 (5)
```

## East Asian and complex-script typefaces

Word stores up to four typefaces for a run, one per script, and applies whichever matches
the characters being rendered. [`Font.name`][docx.text.font.Font.name] is the Latin one;
the others have their own properties:

```python
font = paragraph.add_run("mixed script text").font

font.name = "Calibri"       # Latin
font.east_asian_name = "MS Mincho"
font.complex_script_name = "Arial"
font.high_ansi_name = "Calibri"
```

Complex scripts also carry their own size, which is why a run can render at one size in
Latin and another in Arabic or Hebrew:

```python
from docx.shared import Pt

font.size = Pt(11)
font.cs_size = Pt(13)
```

## Character scaling

Horizontal scaling stretches or condenses the glyphs, as a whole percentage of normal
width:

```python
font.scaling = 150   # half again as wide
font.scaling = 80    # condensed
font.scaling = None  # inherit from the style hierarchy
```

## Shading

Shading fills the background behind text. It exists on a run and on a paragraph, and
takes an RGB hex string:

```python
font.shading_fill = "FFFF00"
paragraph.paragraph_format.shading_fill = "EEEEEE"
```

Word draws a *pattern* in a foreground colour over that fill. The usual case is no
pattern at all, `WD_SHADING_PATTERN.CLEAR`, which is what the two assignments above
produce and what leaves the fill as a plain background. The percentage patterns are how
Word produces a tint of one colour over another:

```python
from docx.enum.text import WD_SHADING_PATTERN

font.shading_fill = "FFFFFF"                        # -- background --
font.shading_color = "FF0000"                       # -- pattern foreground --
font.shading_pattern = WD_SHADING_PATTERN.PCT_25    # -- 25% red over white --
```

Setting `shading_pattern` to `None` removes the shading entirely, as does setting
`shading_fill` to `None`.

!!! note

    A shading pattern is valid with no fill — `<w:shd w:val="pct25" w:color="FF0000"/>`
    is what Word writes for several of its Shading presets. Reading `shading_fill` on
    such a run returns `None` rather than raising.

!!! note

    In 0.9.x, [`Font.highlight_color`][docx.text.font.Font.highlight_color] fell back to
    reading `w:shd`. It no longer does: it is strictly a
    [`WD_COLOR_INDEX`][docx.enum.text.WD_COLOR_INDEX] member — Word's highlighter pen,
    which has a fixed palette — and `shading_fill` is the arbitrary-colour fill.

## Theme fonts

A run's typeface can be set to a *theme token* rather than a font name — `minorHAnsi` for
body text, `majorHAnsi` for headings — in which case the concrete font comes from the
document's theme. [`Font.name`][docx.text.font.Font.name] reports `None` for such a run,
because there is no font name in the run to report:

```python
run.font.theme = "minorHAnsi"

run.font.name             # -> None
run.font.theme            # -> "minorHAnsi"
run.font.theme_typeface   # -> "Cambria"
```

[`Font.theme_typeface`][docx.text.font.Font.theme_typeface] resolves the token through
the theme part, and for a document whose fonts come only from its theme this is the only
way to find out what the text is actually rendered in. It is `None` when the run carries
no token, when the theme leaves that slot empty, or when the `Font` was built over a bare
element with no part behind it.

The theme itself is [`Document.theme`][docx.document.Document.theme]:

```python
theme = document.theme

theme.name                       # -> "Office Theme"
theme.minor_font.latin           # -> "Cambria"
theme.major_font.latin           # -> "Calibri"
theme.minor_font.east_asian      # -> None, the default theme leaves it empty
theme.minor_font.complex_script  # -> None

theme.typeface("minorHAnsi")     # -> "Cambria"
```

The twelve theme colours are there too, keyed by the slot names as they appear in the XML
— `dk1`, `lt1`, `dk2`, `lt2`, `accent1` through `accent6`, `hlink` and `folHlink`:

```python
theme.color("accent1")   # -> RGBColor(0x4F, 0x81, 0xBD)
theme.colors             # -> the twelve, as a dict, in schema order
```

A slot name that does not exist raises `ValueError`; a slot the theme omits gives `None`.
A system colour such as `dk1` reports the value the producing application last resolved it
to, which is the only concrete value available off that operating system.

!!! note

    [`Document.theme`][docx.document.Document.theme] is `None` for a document with no
    theme part, and — unlike the styles and settings parts — one is never created on
    demand. A theme is a design the document was authored against; an empty one
    synthesised on the spot would answer the typeface question with a fiction.

## Right-to-left and vertical text

Two separate things, often confused:

**Base direction** is whether a paragraph reads right-to-left. It decides where the first
character goes, which way punctuation faces, and which edge `start` and `end` mean:

```python
paragraph.paragraph_format.bidi = True
```

**Flow direction** is which way the lines themselves run, and it rotates the text:

```python
from docx.enum.text import WD_TEXT_DIRECTION

paragraph.paragraph_format.text_direction = WD_TEXT_DIRECTION.TB_RL
```

| [`WD_TEXT_DIRECTION`][docx.enum.text.WD_TEXT_DIRECTION] | Flow |
| --- | --- |
| `LR_TB` | left to right, then top to bottom — the default |
| `TB_RL` | top to bottom, then right to left — rotates the text 90° clockwise |
| `BT_LR` | bottom to top, then left to right — rotates it 90° anticlockwise |
| `LR_TB_V` | left to right, then top to bottom, rotating each East Asian character |
| `TB_RL_V` | top to bottom, then right to left, with each character upright |
| `TB_LR_V` | top to bottom, then left to right, Mongolian vertical layout |

Both exist at three levels, and the more specific wins:

```python
document.sections[0].bidi = True                            # -- the section default
document.sections[0].text_direction = WD_TEXT_DIRECTION.TB_RL
paragraph.paragraph_format.text_direction = ...             # -- one paragraph
table.cell(0, 0).text_direction = ...                       # -- one cell
```

All of them are `None` when the value is inherited.

## Equations

An equation is OMML — `m:oMath` — a markup language of its own that shares nothing with
WordprocessingML but the file it lives in. Reading is supported; there is no builder.

```python
for equation in document.math:
    print(equation.text, equation.is_display)
```

[`Document.math`][docx.document.Document.math],
[`BlockItemContainer.math`][docx.blkcntnr.BlockItemContainer.math] and
[`Paragraph.math`][docx.text.paragraph.Paragraph.math] each return the
[`Math`][docx.math.Math] objects in document order:

- `.text` — the characters of the equation, in reading order, with the structure flattened
  away. A fraction reads as its numerator then its denominator; there is no LaTeX here.
- `.xml` — the OMML itself, which is what to use if you need the structure.
- `.is_display` — `True` for a display equation in a `m:oMathPara` of its own, `False` for
  one inline in a sentence.

!!! note

    **Equation text is deliberately not part of
    [`Paragraph.text`][docx.text.paragraph.Paragraph.text].**

    Including it would describe the document more truthfully. But
    [`replace_text()`][docx.document.Document.replace_text] and the run-isolating
    machinery under it measure offsets against `Paragraph.text` and can only cut at run
    boundaries. Text they cannot reach would silently mis-target every replacement after
    the first equation in a paragraph, and a wrong edit is worse than a missing character.

    Read `paragraph.math` when you want the equations, and `paragraph.text` when you want
    what is safely editable.
