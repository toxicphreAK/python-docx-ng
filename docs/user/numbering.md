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

## Defining a list from scratch

Everything above joins or restarts a list the numbering part already defines. When the
format you want is not in the template — Roman numerals at the top level, a bullet
character of your own, a particular indent step — define one:

```python
definition = document.numbering.add_numbered_definition()
document.add_paragraph("one").set_numbering(definition.num_id)
```

[`add_numbered_definition()`][docx.numbering.Numbering.add_numbered_definition] and
[`add_bulleted_definition()`][docx.numbering.Numbering.add_bulleted_definition] are the
two common cases. Both take a `depth` (nine levels by default, which is what Word writes)
and an `indent_step`:

```python
from docx.enum.numbering import WD_NUMBER_FORMAT
from docx.shared import Inches

legal = document.numbering.add_numbered_definition(
    depth=3,
    formats=[
        WD_NUMBER_FORMAT.UPPER_ROMAN,
        WD_NUMBER_FORMAT.UPPER_LETTER,
        WD_NUMBER_FORMAT.DECIMAL,
    ],
    indent_step=Inches(0.3),
)

bullets = document.numbering.add_bulleted_definition(bullets=["—", "·"])
```

[`add_definition()`][docx.numbering.Numbering.add_definition] is the general form, taking
a level specification directly. Both shorthands are built on it:

```python
definition = document.numbering.add_definition([
    {"number_format": WD_NUMBER_FORMAT.DECIMAL, "level_text": "%1.", "start": 1},
    {"number_format": WD_NUMBER_FORMAT.LOWER_LETTER, "level_text": "%2)"},
])
```

In a `level_text`, `%1` interpolates the counter of level 0, `%2` that of level 1, and so
on — `"%1.%2."` is what produces "2.3.". A definition has at most nine levels; more raises
`ValueError`.

Each returns a [`NumberingDefinition`][docx.numbering.NumberingDefinition], whose `num_id`
is what [`set_numbering()`][docx.text.paragraph.Paragraph.set_numbering] takes.

!!! note

    `w:nsid` and `w:tmpl` are deliberately not written. They are the identifiers Word uses
    to recognise a definition as one of its own and to match it against a gallery entry;
    inventing values would make Word treat unrelated lists as the same list, and they are
    optional.

## Changing a level

[`NumberingLevel.set()`][docx.numbering.NumberingLevel.set] changes an existing level in
place, and returns the level so calls chain:

```python
definition.level(0).set(
    number_format=WD_NUMBER_FORMAT.UPPER_ROMAN,
    level_text="%1.",
    suffix="tab",
    alignment="left",
    indent=Inches(0.5),
    hanging_indent=Inches(0.25),
    start=1,
)
```

`suffix` is what follows the number — `"tab"`, `"space"` or `"nothing"` — and
`restart_after_level` is what makes a sub-list start over when the level above it advances.
Every argument is keyword-only and optional; the ones you leave out are left alone.
