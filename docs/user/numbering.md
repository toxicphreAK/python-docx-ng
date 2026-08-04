# Numbered and bulleted lists

A list number is nowhere in the document body. Word stores which list a paragraph belongs
to and computes "1.", "a)" or "iii." from `numbering.xml` at display time, which is why
reading a document gives you paragraph text with the numbers missing.

This library computes them the same way Word does.

## Reading the numbers

[`Document.list_numbers`][docx.document.Document.list_numbers] pairs every list paragraph
in the body with the number a reader sees:

```python
from docx import Document

document = Document("report.docx")

for paragraph, number in document.list_numbers:
    print(number, paragraph.text)
```

```text
1. First point
2. Second point
a) A sub-point
3. Third point
```

Paragraphs inside tables are included, because they count towards the same lists.

[`Paragraph.list_number`][docx.text.paragraph.Paragraph.list_number] gives the number for
a single paragraph, and `None` when it is not in a list:

```python
paragraph.list_number  # -> "2." or None
```

!!! warning

    A list number depends on every paragraph before it, so reading
    [`Paragraph.list_number`][docx.text.paragraph.Paragraph.list_number] in a loop is
    quadratic. Use [`Document.list_numbers`][docx.document.Document.list_numbers], which
    walks the document once.

## Which list a paragraph is in

[`Paragraph.numbering`][docx.text.paragraph.Paragraph.numbering] returns a
[`ParagraphNumbering`][docx.numbering.ParagraphNumbering], or `None` when the paragraph
is not in a list:

```python
item = document.add_paragraph("first item", style="List Number")
numbering = item.numbering

numbering.num_id           # -> the list this paragraph belongs to
numbering.level            # -> indent level, 0 for the outermost
numbering.from_style       # -> True when the style applies it, not the paragraph
numbering.level_definition # -> the NumberingLevel, for format and start value
```

The level definition is where the appearance lives:

```python
level = item.numbering.level_definition

level.number_format     # -> WD_NUMBER_FORMAT.DECIMAL
level.start             # -> 1
level.is_bullet         # -> False
level.format_number(3)  # -> "3."
```

[`format_number()`][docx.numbering.NumberingLevel.format_number] applies the level's own
template, so a level written as `%1)` in lower letters gives `"c)"` for the same input.
[`WD_NUMBER_FORMAT`][docx.enum.numbering.WD_NUMBER_FORMAT] lists the formats.

## Creating a list

The simplest lists are the built-in styles, which carry their own numbering:

```python
document.add_paragraph("first item", style="List Bullet")
document.add_paragraph("first item", style="List Number")
```

To put further paragraphs in the *same* list as an existing one, take its `num_id`:

```python
first = document.add_paragraph("one", style="List Number")
second = document.add_paragraph("two")
second.set_numbering(first.numbering.num_id)
```

[`set_numbering()`][docx.text.paragraph.Paragraph.set_numbering] also takes a level, so
nesting is a matter of saying which:

```python
sub = document.add_paragraph("one, continued")
sub.set_numbering(first.numbering.num_id, level=1)
```

Numbering applied directly like this overrides whatever the paragraph's style would
apply. [`remove_numbering()`][docx.text.paragraph.Paragraph.remove_numbering] takes it
off again.

## Restarting numbering

```python
item.restart_numbering()      # begins again at 1
item.restart_numbering(10)    # begins again at 10
```

This paragraph and every later one in the same list start a new sequence; paragraphs
before it keep the original one. That is what Word's own "Restart at 1" does.

It is worth knowing what happens underneath, because it explains the return value. OOXML
has no counter to reset. A second `w:num` is created against the same abstract
definition, carrying a `w:startOverride`, and the affected paragraphs are pointed at it —
so [`restart_numbering()`][docx.text.paragraph.Paragraph.restart_numbering] returns the
`num_id` of that new list:

```python
new_num_id = item.restart_numbering()
later = document.add_paragraph("still in the restarted list")
later.set_numbering(new_num_id)
```

It raises `ValueError` when the paragraph is not in a list.

## The numbering part

[`Document.numbering`][docx.document.Document.numbering] is the whole of
`numbering.xml`, for finding a list to join or inspecting one:

```python
definition = document.numbering.get(item.numbering.num_id)

definition.num_id
definition.abstract_num_id
definition.levels          # -> the NumberingLevel objects, one per level
definition.level(0)
```

[`Numbering.restart()`][docx.numbering.Numbering.restart] creates the overriding
definition directly, when you want the new list without repointing any paragraphs:

```python
restarted = document.numbering.restart(item.numbering.num_id, ilvl=0, start=1)
```
