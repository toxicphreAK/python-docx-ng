.. :changelog:

Release History
---------------

Unreleased
++++++++++

New features
~~~~~~~~~~~~

- ``Document.add_table()``, ``BlockItemContainer.add_table()`` and ``_Cell.add_table()``
  accept keyword-only ``title`` and ``description``, matching ``Run.add_picture()``.
  Both default to ``None`` and write nothing when omitted.
- ``_Row.repeat_as_header`` ("Repeat Header Rows"), plus ``_Row.hidden``,
  ``.alignment``, ``.cell_spacing``, ``.width_before`` and ``.width_after`` — the rest
  of ``w:trPr``.
- ``Table.look``, the ``w:tblLook`` flags that decide which parts of a table style
  apply: ``first_row``, ``last_row``, ``first_column``, ``last_column``,
  ``horizontal_banding`` and ``vertical_banding``. The legacy ``@w:val`` bitmask is
  rewritten in step, as Word does.
- ``Table.width``, including percentage widths through the new ``docx.shared.Pct``
  value type, plus ``Table.indent`` and ``Table.cell_margins``.
- ``Styles.default_font`` and ``Styles.default_paragraph_format``, exposing
  ``w:docDefaults`` — the bottom of the formatting inheritance chain, and for many
  documents the only place the base font is set.
- ``ParagraphFormat.mark_font``, the run properties of the paragraph mark itself
  (``w:pPr/w:rPr``). This is the only place the formatting of an empty paragraph lives.
- Character-unit indents and line-unit spacing:
  ``ParagraphFormat.first_line_indent_chars``, ``.left_indent_chars``,
  ``.right_indent_chars``, ``.space_before_lines`` and ``.space_after_lines``. Values
  are in hundredths, matching the XML. The existing twips properties now also read the
  ``w:start``/``w:end`` spellings Word writes in recent files, and setting either unit
  clears its counterpart so the two cannot disagree.
- Right-to-left and vertical text: ``ParagraphFormat.bidi``, ``Section.bidi``, and
  ``text_direction`` on ``ParagraphFormat``, ``Section`` and ``_Cell``, with the new
  ``WD_TEXT_DIRECTION`` enumeration.
- ``ParagraphFormat.borders`` and ``Section.page_borders``, spelled the same as the
  table and cell borders API. A paragraph with only a bottom border is how Word draws a
  horizontal rule.
- Endnotes: ``Document.endnotes``, ``Endnotes.add_endnote()``, ``Endnote.text``,
  ``Endnote.endnote_id`` and ``Run.add_endnote_reference()``, mirroring the footnote
  API. ``word/endnotes.xml`` is created on demand, as the footnotes part is, and
  ``Document.replace_text(footnotes=True)`` now reaches endnotes as its docstring
  already said it would.
- ``Paragraph.math``, ``BlockItemContainer.math`` and ``Document.math``, exposing the
  OMML equations (``m:oMath``) that were previously unreachable. Each ``Math`` object
  offers ``.text``, ``.xml`` and ``.is_display``.

  **Equation text is deliberately not included in ``Paragraph.text``.** Including it
  would describe the document more truthfully, but ``replace_text()`` and the
  run-isolating machinery under it measure offsets against ``Paragraph.text`` and can
  only cut at run boundaries; text they cannot reach would silently mis-target every
  replacement after the first equation in a paragraph. A wrong edit is worse than a
  missing character.
- ``Document.theme``, exposing ``word/theme/theme1.xml`` — the major and minor
  typefaces and the twelve theme colours — and ``Font.theme_typeface``, which resolves
  a ``minorHAnsi``-style token to the font name it stands for. For a document whose
  fonts come only from its theme, this is the first way to find out what the text is
  actually rendered in. ``Document.theme`` is ``None`` for a document with no theme
  part; unlike the styles and settings parts, one is never created on demand.
- ``InlineShape.image`` and ``FloatingShape.image``, the counterpart of
  ``Run.add_picture()``, plus ``.svg_image`` for the vector source of an SVG picture and
  ``Document.images`` for the package-level view. ``.image`` is ``None`` rather than an
  error for a chart, a SmartArt diagram or a linked picture.

2.0.0 (2026-08-05)
++++++++++++++++++

Restarted from upstream python-docx v1.2.0. The 0.9.x line had diverged from upstream
v0.8.11 in 2021; rather than merge four years of upstream change into that tree, this
release branches from upstream and re-applies the python-docx-ng features on top.

**This is a breaking release.** See
https://toxicphreak.github.io/python-docx-ng/user/migrating-from-0-9/ for a migration
path.

Breaking changes
~~~~~~~~~~~~~~~~

- Comments are now upstream's ``Document.comments``, ``Document.add_comment()`` and
  ``Run.mark_comment_range()``. ``Paragraph.add_comment()`` and the ``docx.text.comment``
  module are gone.
- Hyperlinks are now upstream's ``Hyperlink``, with ``.address``, ``.fragment``,
  ``.runs``, ``.text`` and ``.contains_page_break``. ``Paragraph.add_hyperlink()``
  remains but takes ``address`` and ``fragment`` and returns a ``Hyperlink``.
- ``Table._cells`` is a flat list rather than a row-major matrix, and ``_Row.cells``
  returns only the cells actually present. ``_Row.grid_cols_before`` and
  ``.grid_cols_after`` report the layout-grid positions a row leaves unpopulated.
  ``Table.row_cells()`` is deprecated in favour of ``table.rows[i].cells``.
- ``Font.highlight_color`` is strictly a ``WD_COLOR_INDEX`` member and no longer falls
  back to ``w:shd``; use the new ``Font.shading_fill`` for RGB shading.
- ``Section.paragraphs`` is removed; use ``Section.iter_inner_content()``.
- ``Table.section`` is removed. The 0.9.x implementation returned the wrong section in
  a multi-section document.
- ``ParagraphFormat.outline_level`` returns ``None`` when unset rather than ``9``;
  ``9`` now means Word's explicit "Body Text" level.
- The table and cell borders API is a mapping keyed by edge, with line styles as
  ``WD_LINE_STYLE`` members and sizes as ``Length`` values.
- Footnotes are ``Document.footnotes`` and ``Run.add_footnote_reference()`` rather than
  ``Paragraph.add_footnote()``.
- Python 3.8 is no longer supported. Supported versions are 3.9+.
- ``Paragraph.text`` now has defined semantics for a document carrying tracked changes:
  it is the text as the document *now* reads, with insertions included and deletions
  excluded. Previously both were dropped, so the result matched neither the original nor
  the final version of the document. ``Paragraph.original_text`` is the other reading.
  ``Paragraph.runs`` likewise now includes runs inside a ``w:ins``.
- ``Paragraph.text`` also now includes the cached result of a ``w:fldSimple`` — a page
  number or cross-reference displayed by such a field was previously missing from it.
- ``Paragraph.text`` and ``.runs`` now look through ``w:smartTag`` and ``w:customXml``.
  Word writes a ``w:smartTag`` around a recognised date, name or place, and its ``w:r``
  children are ordinary runs one level down — previously invisible, so the text was
  silently dropped and the run missing from ``.runs``. ``Paragraph.original_text``
  reads them too. A block-level ``w:customXml``, which wraps whole paragraphs and
  tables, is looked through as well — its content was previously absent from
  ``Document.paragraphs`` and ``.tables`` altogether. Text inside a text box
  (``w:txbxContent``) is still not included; that is a separate container rather than a
  transparent wrapper.
- Assigning ``Section.orientation`` now exchanges ``page_width`` and ``page_height`` as
  well, so the page is actually rotated. Previously it set ``w:pgSz/@w:orient`` alone,
  leaving a section declared landscape at portrait dimensions — which Word renders as
  portrait. **If your code applies the usual workaround**, swapping the dimensions by
  hand right after the assignment, remove it: the two swaps now cancel and the page
  comes out the size it started. Setting the orientation it already has does nothing,
  and margins are not moved.

Added
~~~~~

- Tracked changes — ``Document.revisions``, ``Paragraph.revisions``,
  ``Revision.accept()`` / ``.reject()``, ``Document.accept_all_revisions()`` /
  ``.reject_all_revisions()``, ``Paragraph.original_text`` and
  ``Settings.track_revisions``
- Fields — ``docx.fields``, ``Paragraph.add_field()``, ``Document.fields``,
  instruction builders for PAGE, NUMPAGES, TOC, REF, PAGEREF, SEQ, DATE, DOCPROPERTY
  and STYLEREF, and ``Settings.update_fields_on_open``
- List numbering — ``Paragraph.numbering``, ``Paragraph.list_number``,
  ``Document.list_numbers``, ``Paragraph.set_numbering()`` /
  ``.remove_numbering()`` / ``.restart_numbering()``, and ``Document.numbering``
- Cross-run search and replace — ``replace_text()`` on ``Paragraph``,
  ``BlockItemContainer`` and ``Document``, built on ``Paragraph.isolate_run()``
- Floating (anchored) images — ``Run.add_float_picture()``,
  ``Document.floating_shapes`` and the ``WD_WRAP_TYPE`` enum
- Watermarks — ``Document.add_text_watermark()`` / ``.add_image_watermark()`` /
  ``.remove_watermark()``, and the same three on ``Section``
- Copying a style between documents — ``Styles.copy_style_from()``, resolving the
  ``w:basedOn`` / ``w:next`` / ``w:link`` closure and carrying numbering across
- Footnotes — ``Document.footnotes``, ``Footnotes.add_footnote()``,
  ``Run.add_footnote_reference()``
- Legacy form fields — ``Document.form_fields``, ``Paragraph.form_fields``, and a
  ``FormField`` proxy that reads and writes field values
- AltChunk — ``Document.add_alt_chunk()`` and ``Document.alt_chunks``
- Table and cell borders — ``Table.borders`` and ``_Cell.borders``, with the
  ``WD_LINE_STYLE`` enum
- Custom document properties (``docProps/custom.xml``)
- Extended (application) document properties (``docProps/app.xml``)
- Bookmarks — ``Document.bookmarks`` — and ``Paragraph.add_hyperlink()``
- A deletion API — ``.delete()`` on paragraphs, runs, tables, rows and columns
- SVG, EMF, WMF and WebP image support
- ``.docm`` macro-enabled document support, and ``.dotx``/``.dotm`` template support
- Content controls — reading text wrapped in a ``w:sdt``
- East Asian and complex-script typefaces, ``w:szCs``, character scaling, theme fonts
- Paragraph and run shading — ``shading_fill``, plus ``shading_pattern`` and
  ``shading_color`` and the ``WD_SHADING_PATTERN`` enum — and paragraph outline level
- Multi-column section layout
- Alt text on pictures and inline shapes
- Table alternative text — ``Table.title`` and ``Table.description``
- ``_Row.dont_split``, and the merge extent and origin of a table cell
- Byte-reproducible output — the same document data serializes to identical bytes
- Custom namespace prefixes in ``xpath()`` calls
- ``Document()`` and ``Document.save()`` accept an ``os.PathLike`` — a ``pathlib.Path``
  no longer has to be wrapped in ``str()``. A path-like pointing at an extracted package
  directory is now detected as one, and a missing or corrupt path is reported by name.

Fixed
~~~~~

- ``w:shd`` is modelled correctly. The schema requires ``w:val`` and makes ``w:fill``
  optional; this library required ``w:fill`` and never wrote ``w:val``, so it emitted
  shading a validating consumer rejects and raised on the pattern shading Word writes
  for most of its presets. Shading now carries an explicit ``w:val``, and a ``w:shd``
  with a pattern but no fill reads as ``None`` rather than raising. A ``w:shd`` written by
  an earlier version, with no ``w:val``, still reads.
- ``ST_HexColor`` accepts ``"auto"`` on assignment as well as on read. The schema type
  is a union of an RGB triple and that literal, but only the read direction handled it,
  so ``font.shading_fill = "auto"`` raised ``ValueError`` on a value the getter
  documents and returns. ``w:color/@w:val`` is assignable as ``"auto"`` for the same
  reason.
- Style lookup matches case-insensitively when an exact match fails. A built-in style
  has two spellings — the UI name ("Heading 1") and the internal name Word stores
  ("heading 1") — and documents from other generators routinely store the UI casing,
  which made the style present but unreachable: ``add_heading()`` and every
  ``style=`` assignment raised ``KeyError`` on a document that opened fine.
  ``name in styles`` now resolves exactly as ``styles[name]`` does. Style *definitions*
  are unchanged on save; only lookup is tolerant.
- An ISO/IEC 29500 Strict document now raises ``StrictOoxmlNotSupportedError``, naming
  the format and how to convert it, rather than ``AttributeError: 'lxml.etree._Element'
  object has no attribute 'body'``. Strict is an option in Word's Save As dialogue and
  the default in some regulated environments; reading it is still not supported.
- Style and latent-style lookup now accepts names and style IDs containing quotes and
  other XPath metacharacters.
- Documents with oversized attribute values, which the default ``lxml`` parser rejects,
  now parse. Entity resolution stays off.
- Corrupt packages and dangling relationships no longer raise on load
- Tables with no ``w:tblGrid`` are readable, and cell access is linear rather than
  quadratic
- ``w:highlight w:val="none"`` and fractional half-point font sizes are accepted

Packaging
~~~~~~~~~

- The license is declared as an SPDX expression (PEP 639) rather than the deprecated
  table form, and ``LICENSE`` is declared through ``license-files``
- ``Typing :: Typed`` is declared; the package has shipped ``py.typed`` since 1.2.0
- Python 3.14 is supported and tested. The matrix is 3.9 through 3.14.
- The ``lxml`` floor is ``6.1.0``, raised from ``4.5.2``. 6.1.0 is the first release
  fixing CVE-2026-41066, an XXE-to-local-files hole in the default configuration of
  ``iterparse()`` and ``ETCompatXMLParser()``; every 4.x and 5.x release is affected.
  This package uses neither API and sets ``resolve_entities=False`` on its own parser,
  so it was never exposed itself — but it has no business pulling a known-vulnerable XML
  parser into a dependency tree. lxml 6.1.x ships wheels for CPython 3.9 through 3.14
  and requires Python 3.8+, so no supported interpreter is lost, and generated documents
  are byte-identical to those produced against 4.9.4 and 5.4.0.
  **If you are pinned below lxml 6 for another reason, this release will not resolve
  for you.**
- The unpacked ``default-docx-template/`` is no longer installed. It is the editable
  source of ``default.docx``, is read by nothing at run time, and stays in the sdist
- The ``requirements*.txt`` files are removed. ``[dependency-groups]`` in
  ``pyproject.toml`` is the single list of development dependencies, and ``tox`` reads it

Contributors
~~~~~~~~~~~~

Thank you to the people who sent patches for this release:

- `@lyydsheep <https://github.com/lyydsheep>`_ — ``os.PathLike`` support throughout
  document open and save (#130)
- `@builtbyhuy <https://github.com/builtbyhuy>`_ — XPath variable binding, so style
  names containing quotes are reachable (#131)
- `@BortnikMaxim <https://github.com/BortnikMaxim>`_ — table alternative text,
  ``Table.title`` and ``Table.description`` (#132)


1.2.0 (2025-06-16)
++++++++++++++++++

- Add support for comments
- Drop support for Python 3.8, add testing for Python 3.13


1.1.2 (2024-05-01)
++++++++++++++++++

- Fix #1383 Revert lxml<=4.9.2 pin that breaks Python 3.12 install
- Fix #1385 Support use of Part._rels by python-docx-template
- Add support and testing for Python 3.12


1.1.1 (2024-04-29)
++++++++++++++++++

- Fix #531, #1146 Index error on table with misaligned borders
- Fix #1335 Tolerate invalid float value in bottom-margin
- Fix #1337 Do not require typing-extensions at runtime


1.1.0 (2023-11-03)
++++++++++++++++++

- Add BlockItemContainer.iter_inner_content()


1.0.1 (2023-10-12)
++++++++++++++++++

- Fix #1256: parse_xml() and OxmlElement moved.
- Add Hyperlink.fragment and .url


1.0.0 (2023-10-01)
+++++++++++++++++++

- Remove Python 2 support. Supported versions are 3.7+
- Fix #85:   Paragraph.text includes hyperlink text
- Add #1113: Hyperlink.address
- Add Hyperlink.contains_page_break
- Add Hyperlink.runs
- Add Hyperlink.text
- Add Paragraph.contains_page_break
- Add Paragraph.hyperlinks
- Add Paragraph.iter_inner_content()
- Add Paragraph.rendered_page_breaks
- Add RenderedPageBreak.following_paragraph_fragment
- Add RenderedPageBreak.preceding_paragraph_fragment
- Add Run.contains_page_break
- Add Run.iter_inner_content()
- Add Section.iter_inner_content()


0.8.11 (2021-05-15)
+++++++++++++++++++

- Small build changes and Python 3.8 version changes like collections.abc location.


0.8.10 (2019-01-08)
+++++++++++++++++++

- Revert use of expanded package directory for default.docx to work around setup.py
  problem with filenames containing square brackets.


0.8.9 (2019-01-08)
++++++++++++++++++

- Fix gap in MANIFEST.in that excluded default document template directory


0.8.8 (2019-01-07)
++++++++++++++++++

- Add support for headers and footers


0.8.7 (2018-08-18)
++++++++++++++++++

- Add _Row.height_rule
- Add _Row.height
- Add _Cell.vertical_alignment
- Fix #455: increment next_id, don't fill gaps
- Add #375: import docx failure on --OO optimization
- Add #254: remove default zoom percentage
- Add #266: miscellaneous documentation fixes
- Add #175: refine MANIFEST.ini
- Add #168: Unicode error on core-props in Python 2


0.8.6 (2016-06-22)
++++++++++++++++++

- Add #257: add Font.highlight_color
- Add #261: add ParagraphFormat.tab_stops
- Add #303: disallow XML entity expansion


0.8.5 (2015-02-21)
++++++++++++++++++

- Fix #149: KeyError on Document.add_table()
- Fix #78: feature: add_table() sets cell widths
- Add #106: feature: Table.direction (i.e. right-to-left)
- Add #102: feature: add CT_Row.trPr


0.8.4 (2015-02-20)
++++++++++++++++++

- Fix #151: tests won't run on PyPI distribution
- Fix #124: default to inches on no TIFF resolution unit


0.8.3 (2015-02-19)
++++++++++++++++++

- Add #121, #135, #139: feature: Font.color


0.8.2 (2015-02-16)
++++++++++++++++++

- Fix #94: picture prints at wrong size when scaled
- Extract `docx.document.Document` object from `DocumentPart`

  Refactor `docx.Document` from an object into a factory function for new
  `docx.document.Document object`. Extract methods from prior `docx.Document`
  and `docx.parts.document.DocumentPart` to form the new API class and retire
  `docx.Document` class.

- Migrate `Document.numbering_part` to `DocumentPart.numbering_part`. The
  `numbering_part` property is not part of the published API and is an
  interim internal feature to be replaced in a future release, perhaps with
  something like `Document.numbering_definitions`. In the meantime, it can
  now be accessed using ``Document.part.numbering_part``.


0.8.1 (2015-02-10)
++++++++++++++++++

- Fix #140: Warning triggered on Document.add_heading/table()


0.8.0 (2015-02-08)
++++++++++++++++++

- Add styles. Provides general capability to access and manipulate paragraph,
  character, and table styles.

- Add ParagraphFormat object, accessible on Paragraph.paragraph_format, and
  providing the following paragraph formatting properties:

  + paragraph alignment (justfification)
  + space before and after paragraph
  + line spacing
  + indentation
  + keep together, keep with next, page break before, and widow control

- Add Font object, accessible on Run.font, providing character-level
  formatting including:

  + typeface (e.g. 'Arial')
  + point size
  + underline
  + italic
  + bold
  + superscript and subscript

The following issues were retired:

- Add feature #56: superscript/subscript
- Add feature #67: lookup style by UI name
- Add feature #98: Paragraph indentation
- Add feature #120: Document.styles

**Backward incompatibilities**

Paragraph.style now returns a Style object. Previously it returned the style
name as a string. The name can now be retrieved using the Style.name
property, for example, `paragraph.style.name`.


0.7.6 (2014-12-14)
++++++++++++++++++

- Add feature #69: Table.alignment
- Add feature #29: Document.core_properties


0.7.5 (2014-11-29)
++++++++++++++++++

- Add feature #65: _Cell.merge()


0.7.4 (2014-07-18)
++++++++++++++++++

- Add feature #45: _Cell.add_table()
- Add feature #76: _Cell.add_paragraph()
- Add _Cell.tables property (read-only)


0.7.3 (2014-07-14)
++++++++++++++++++

- Add Table.autofit
- Add feature #46: _Cell.width


0.7.2 (2014-07-13)
++++++++++++++++++

- Fix: Word does not interpret <w:cr/> as line feed


0.7.1 (2014-07-11)
++++++++++++++++++

- Add feature #14: Run.add_picture()


0.7.0 (2014-06-27)
++++++++++++++++++

- Add feature #68: Paragraph.insert_paragraph_before()
- Add feature #51: Paragraph.alignment (read/write)
- Add feature #61: Paragraph.text setter
- Add feature #58: Run.add_tab()
- Add feature #70: Run.clear()
- Add feature #60: Run.text setter
- Add feature #39: Run.text and Paragraph.text interpret '\n' and '\t' chars


0.6.0 (2014-06-22)
++++++++++++++++++

- Add feature #15: section page size
- Add feature #66: add section
- Add page margins and page orientation properties on Section
- Major refactoring of oxml layer


0.5.3 (2014-05-10)
++++++++++++++++++

- Add feature #19: Run.underline property


0.5.2 (2014-05-06)
++++++++++++++++++

- Add feature #17: character style


0.5.1 (2014-04-02)
++++++++++++++++++

- Fix issue #23, `Document.add_picture()` raises ValueError when document
  contains VML drawing.


0.5.0 (2014-03-02)
++++++++++++++++++

- Add 20 tri-state properties on Run, including all-caps, double-strike,
  hidden, shadow, small-caps, and 15 others.


0.4.0 (2014-03-01)
++++++++++++++++++

- Advance from alpha to beta status.
- Add pure-python image header parsing; drop Pillow dependency


0.3.0a5 (2014-01-10)
++++++++++++++++++++++

- Hotfix: issue #4, Document.add_picture() fails on second and subsequent
  images.


0.3.0a4 (2014-01-07)
++++++++++++++++++++++

- Complete Python 3 support, tested on Python 3.3


0.3.0a3 (2014-01-06)
++++++++++++++++++++++

- Fix setup.py error on some Windows installs


0.3.0a1 (2014-01-05)
++++++++++++++++++++++

- Full object-oriented rewrite
- Feature-parity with prior version
- text: add paragraph, run, text, bold, italic
- table: add table, add row, add column
- styles: specify style for paragraph, table
- picture: add inline picture, auto-scaling
- breaks: add page break
- tests: full pytest and behave-based 2-layer test suite


0.3.0dev1 (2013-12-14)
++++++++++++++++++++++

- Round-trip .docx file, preserving all parts and relationships
- Load default "template" .docx on open with no filename
- Open from stream and save to stream (file-like object)
- Add paragraph at and of document
