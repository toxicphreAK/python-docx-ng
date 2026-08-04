# Working with Sections

Word supports the notion of a *section*, a division of a document having the same page layout settings, such as margins and page orientation. This is how, for example, a document can contain some pages in portrait layout and others in landscape. Each section also defines the headers and footers that apply to the pages of that section.

Most Word documents have only the single section that comes by default and further, most of those have no reason to change the default margins or other page layout. But when you *do* need to change the page layout, you'll need to understand sections to get it done.

## Accessing sections

Access to document sections is provided by the `sections` property on the [Document][docx.api.Document] object:

```pycon
>>> document = Document()
>>> sections = document.sections
>>> sections
<docx.parts.document.Sections object at 0x1deadbeef>
>>> len(sections)
3
>>> section = sections[0]
>>> section
<docx.section.Section object at 0x1deadbeef>
>>> for section in sections:
...     print(section.start_type)
...
NEW_PAGE (2)
EVEN_PAGE (3)
ODD_PAGE (4)
```
It's theoretically possible for a document not to have any explicit sections, although I've yet to see this occur in the wild. If you're accessing an unpredictable population of .docx files you may want to provide for that possibility using a `len()` check or `try` block to avoid an uncaught `IndexError` exception stopping your program.

## Adding a new section

The [Document.add_section][docx.document.Document.add_section] method allows a new section to be started at the end of the document. Paragraphs and tables added after calling this method will appear in the new section:

```pycon
>>> current_section = document.sections[-1]  # last section in document
>>> current_section.start_type
NEW_PAGE (2)
>>> new_section = document.add_section(WD_SECTION.ODD_PAGE)
>>> new_section.start_type
ODD_PAGE (4)
```
## Section properties

The [Section][docx.section.Section] object has eleven properties that allow page layout settings to be discovered and specified.

### Section start type

[Section.start_type][docx.section.Section.start_type] describes the type of break that precedes the section:

```pycon
>>> section.start_type
NEW_PAGE (2)
>>> section.start_type = WD_SECTION.ODD_PAGE
>>> section.start_type
ODD_PAGE (4)
```
Values of `start_type` are members of the [WdSectionStart][docx.enum.section.WD_SECTION_START] enumeration.

### Page dimensions and orientation

Three properties on [Section][docx.section.Section] describe page dimensions and orientation. Together these can be used, for example, to change the orientation of a section from portrait to landscape:

```pycon
>>> section.orientation, section.page_width, section.page_height
(PORTRAIT (0), 7772400, 10058400)  # (Inches(8.5), Inches(11))
>>> new_width, new_height = section.page_height, section.page_width
>>> section.orientation = WD_ORIENT.LANDSCAPE
>>> section.page_width = new_width
>>> section.page_height = new_height
>>> section.orientation, section.page_width, section.page_height
(LANDSCAPE (1), 10058400, 7772400)
```
### Page margins

Seven properties on [Section][docx.section.Section] together specify the various edge spacings that determine where text appears on the page:

```pycon
>>> from docx.shared import Inches
>>> section.left_margin, section.right_margin
(1143000, 1143000)  # (Inches(1.25), Inches(1.25))
>>> section.top_margin, section.bottom_margin
(914400, 914400)  # (Inches(1), Inches(1))
>>> section.gutter
0
>>> section.header_distance, section.footer_distance
(457200, 457200)  # (Inches(0.5), Inches(0.5))
>>> section.left_margin = Inches(1.5)
>>> section.right_margin = Inches(1)
>>> section.left_margin, section.right_margin
(1371600, 914400)
```

## Multiple text columns

A section can lay its text out in columns, as a newsletter does:

```python
from docx.shared import Cm

section = document.sections[0]
section.column_count = 2
section.column_spacing = Cm(1)
```

`column_count` is the number of columns, and `column_spacing` the gap between them as a
[`Length`][docx.shared.Length]; `column_spacing` reads as `None` when the document does
not specify one, in which case Word applies its own default.

Because this is a section property, changing the number of columns partway through a
document means starting a new section at that point:

```python
from docx.enum.section import WD_SECTION

two_up = document.add_section(WD_SECTION.CONTINUOUS)
two_up.column_count = 2
```
