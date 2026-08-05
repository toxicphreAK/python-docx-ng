# Style usage and cleanup

A document created by this library defines 168 styles. A one-paragraph document
references ten of them. Most of `word/styles.xml` is Word's built-in gallery, carried
along because the template it came from carried it.

This page is about finding that out and doing something about it. The command-line
front end for everything here is [`python -m docx`](cli.md).

## Which styles are in use

```python
usage = document.styles.usage()

print(usage)
# 168 styles defined, 10 in use, 158 unused; 131 latent style exceptions
```

[`Styles.usage()`][docx.styles.styles.Styles.usage] returns a
[`StyleUsage`][docx.styles.usage.StyleUsage], a named tuple of style **ids**:

| Field | Meaning |
| --- | --- |
| `defined` | every style id in the styles part, in document order |
| `used` | the ids in the reachability closure of what the document applies |
| `unused` | `defined` minus `used`, in document order |
| `reference_counts` | how many times each id is *directly* applied; a style reachable only indirectly counts zero |
| `latent` | names declared in `w:latentStyles` that the document does not define |

Iterating a `StyleUsage` yields the ids in use.

The convenience accessors work in names, as the rest of the styles API does:

```python
for style in document.styles.unused:
    print(style.name)

document.styles["Heading 7"].in_use   # -> False
```

### "Used" is a closure, not a scan

A scan of `w:pStyle` in `word/document.xml` gets the wrong answer in four ways, and each
of them is a real document:

- **Every story part counts, not just the body.** Headers, footers, footnotes, endnotes
  and comments are separate parts with their own style references.
- **A style can be reachable without ever being applied** — as the `w:basedOn` of a used
  style, as its `w:next`, as its `w:link`, from a numbering level's `w:pStyle`, or from
  the `w:tblStylePr` conditional formatting inside a table style.
- **The `w:default="1"` styles apply to content that names no style at all.** They are
  used by definition and have zero direct references.
- **`Normal` is never dead.** Word repairs a document that lacks it, and the repair
  dialogue is worse than the bloat.

So "used" is computed as a reachability closure: seed from the direct applications, the
default styles and `Normal`, then follow the reference edges until the set stops growing.
A dangling edge — a `w:basedOn` naming a style that is not defined — is a dead end rather
than an error, because that is legal and common.

Two keyword arguments adjust the seed:

```python
# -- treat a style you are about to apply as used, along with its dependencies --
document.styles.usage(keep=("Quote",))

# -- the narrower question: what is reachable by reference alone? --
document.styles.usage(seed_defaults=False)
```

## Removing the unused ones

```python
removed = document.styles.remove_unused()
len(removed)   # -> 158
```

[`Styles.remove_unused()`][docx.styles.styles.Styles.remove_unused] returns the ids it
removed. It takes the same `keep`, and `keep_defaults` (`True` by default) protects the
`w:default="1"` styles.

!!! warning

    This is destructive and it is not undoable within the open document. A style you
    intend to apply later is unused *now*, so name it in `keep`:

    ```python
    document.styles.remove_unused(keep=("Quote", "Intense Quote"))
    ```

## Cleaning up the whole document

[`Document.cleanup()`][docx.document.Document.cleanup] runs three passes and returns a
[`CleanupResult`][docx.cleanup.CleanupResult]:

```python
result = document.cleanup()

print(result)
# removed 158 styles, 3 numbering definitions, 3 abstract numbering
# definitions, 0 media parts and 0 latent style exceptions

result.styles             # -> the style ids
result.num_ids            # -> the w:num numIds
result.abstract_num_ids   # -> the w:abstractNum abstractNumIds
result.media              # -> the partnames of the image parts
result.latent_styles      # -> how many w:lsdException overrides went
```

The three passes, each of which can be turned off:

**Styles** — the closure above.

**Numbering definitions** — a `w:num` no `w:numPr` points at is dead, and a
`w:abstractNum` no surviving `w:num` points at is dead too. Chains through
`w:numStyleLink` are followed, so a definition kept alive only indirectly survives.

**Orphan media** — an image part related from nothing, which is what
[`.delete()`][docx.text.paragraph.Paragraph.delete] on a paragraph holding a picture
leaves behind. Only the document part's own image relationships are considered: a header
image belongs to the header part and is not orphaned by anything happening in the body.

```python
document.cleanup(
    styles=True,
    numbering=True,
    media=True,
    latent_styles=False,   # -- off by default, see below --
    keep=("Quote",),
)
```

Styles are pruned before numbering, so a numbering definition kept alive only by a style
that is about to go is correctly seen as dead.

### Latent styles are separate on purpose

`latent_styles` is `False` by default. A `w:lsdException` is a *behaviour declaration*
for a style the document does not define — whether it shows in Word's style gallery, and
in what order. Removing one changes what a user sees in the UI rather than how the
document renders, which is a different kind of change from removing a style definition.

[`LatentStyles.trim()`][docx.styles.latent.LatentStyles.trim] does it on its own, and
returns how many went. It removes *every* override — the bundled template carries 137,
one per built-in Word might offer — while leaving the defaults on the `w:latentStyles`
element itself, which are what the overrides were overriding:

```python
document.styles.latent_styles.trim()   # -> 137
```

That count is not the same as `usage.latent`, which is the narrower set of latent names
the document does not also *define*. The two answer different questions and it is worth
not confusing them.

## What this is worth

For a document generated from the bundled template and then cleaned:

| | Uncompressed | On disk |
| --- | --- | --- |
| As generated | 376 KB | 20 KB |
| After `cleanup()` | 40 KB | 9 KB |

Almost all of it is `word/styles.xml`. Whether that matters depends on what you are
doing — it is nothing for one document and a great deal for a hundred thousand of them.

## Moving styles between documents

The other side of the same coin: rather than pruning what a template brought, bring only
what you want. See [Templates and embedded files](templates.md#importing-a-templates-styles).
