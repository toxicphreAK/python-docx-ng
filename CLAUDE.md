# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`python-docx-ng` is a downstream superset of [python-docx](https://github.com/python-openxml/python-docx). The distribution is `python-docx-ng` but the **importable package is `docx`** — all imports are `import docx` / `from docx.text.paragraph import Paragraph`, and the two distributions cannot be installed side by side.

The `main` branch is the 2.0.0 line, restarted from upstream **v1.2.0** in Aug 2026. The fork had previously diverged at upstream v0.8.11 (2021) and drifted; rather than merging four years of upstream change into that tree, `main` was branched from upstream and the python-docx-ng features are being re-applied on top one at a time. Upstream's docs and issue tracker still apply to the shared core.

- `main` — the 2.0.0 line. All work goes here.
- `master` — the 0.9.x record. Historical reference only; **never port work back onto it**.
- `upstream` remote — `python-openxml/python-docx`, HTTPS and read-only.

Remaining feature work is tracked as GitHub issues on the 2.0.0 milestone. Check there before starting: several 0.9.x features are deliberately *not yet* re-applied.

## Commands

Requires [uv](https://docs.astral.sh/uv/). Never use pip or poetry here.

```bash
uv sync                                  # create/update the environment
uv run pytest -q                         # unit tests
uv run pytest tests/text/test_font.py    # single module
uv run pytest -k it_knows_its_theme_typeface   # single test
uv run behave --format progress --tags=-wip    # acceptance tests
uv run ruff check .                      # lint (blocking in CI)
uv run pyright                           # type check (informational, see below)
uv build                                 # build sdist + wheel
make coverage                            # pytest with coverage
```

**Test on Python 3.9 before pushing anything with new annotations:**

```bash
uv run --python 3.9 pytest tests -q      # then: uv sync --python 3.12 to switch back
```

## Things that have already caused breakage

- **pytest collection is customized** in `pyproject.toml`: classes must be `Test*` or `Describe*`, and test functions must start with `it_`, `its_`, `they_`, `and_`, or `but_`. A conventional `def test_foo()` is **silently not collected**.
- **PEP 604 annotations need `from __future__ import annotations`.** Supported Python is 3.9+, where `int | None` in an annotation is evaluated at runtime and raises `TypeError` at import. Every module in the package has the import; keep it that way. This broke 23 test modules on 3.9 once while passing locally on 3.12.
- **New test classes go after the fixtures of the class above them.** Fixtures live at the bottom of each `Describe*` class; inserting a class in the middle of a file orphans them and every test in the class above errors with "fixture not found".
- **pyright is not a passing gate.** The code inherited from upstream v1.2.0 has ~8,900 strict-mode errors against the pinned `types-lxml` stubs. CI reports the count without failing. Annotate new code properly, but do not expect a clean run and do not "fix" inherited errors as a side quest.
- **Check `ref/xsd/` before assuming child order.** Some complex types are `xsd:all`, not `xsd:sequence` — `CT_Properties` (app.xml) is, which is why Word writes those children in an order that does not match the schema listing. Building `successors` bookkeeping for an `xsd:all` type is wasted work that implies a constraint that does not exist.

## Architecture

Three layers, bottom-up. Knowing which layer owns a behavior is most of knowing where a change belongs.

### 1. OPC package layer — `src/docx/opc/`

Generic Open Packaging Conventions implementation (zip container, parts, relationships), no Word-specific knowledge.

- `phys_pkg.py` — physical zip/directory read and write. Members are written with a **fixed zip-epoch timestamp**, part of byte-reproducible output.
- `pkgwriter.py` — sorts parts by partname before writing; `rel.py` emits relationships in numeric rId order. Together with the fixed timestamps this makes the same document data serialize to identical bytes. `tests/test_reproducible.py` pins this.
- `part.py` — `Part`, `XmlPart`, and `PartFactory`, mapping content type → part class.
- `coreprops.py` / `parts/coreprops.py` and `extendedprops.py` / `parts/extendedprops.py` — the `docProps/core.xml` and `docProps/app.xml` property objects. These two are the model to copy for any new document-properties work.

### 2. XML element layer — `src/docx/oxml/`

lxml custom element classes. `oxml/parser.py` configures the parser with an `ElementNamespaceClassLookup`, so parsing yields typed elements (`CT_P`, `CT_Tbl`, …) directly. The parser sets `huge_tree=True` to accept the oversized attribute values Word writes; **entity resolution must stay off** — that is the part of `huge_tree` carrying billion-laughs exposure, and a test pins it.

**Every new element class must be registered** with `register_element_cls("w:p", CT_P)` in `oxml/__init__.py`. A class file alone does nothing — the symptom of forgetting is an `AttributeError` on a plain `lxml.etree._Element` where you expected your class.

`oxml/xmlchemy.py` is the declarative DSL. `pPr = ZeroOrOne("w:pPr", successors=...)` generates `.pPr`, `.get_or_add_pPr()` and `._remove_pPr()` at class-creation time; `ZeroOrMore("w:r")` generates `.r_lst` and `.add_r()`. The `successors` tuple is what places a new child correctly — **Word rejects documents whose child order violates the schema**, so when adding an element to a sequence type, slice `_tag_seq` at the right index and add a test asserting placement against a neighbouring element.

Declared accessors need a matching `Callable[...]` annotation at the top of the class for pyright; follow the surrounding pattern.

`oxml/ns.py` holds `nsmap` and `qn()`. `BaseOxmlElement.xpath()` takes an optional `namespaces` mapping merged over the standard one, for vendor namespaces.

### 3. Proxy / public API layer

Thin objects over oxml elements, built on `ElementProxy` and `Parented` in `shared.py` (which also holds the `Length` units and `RGBColor`). They hold no state; the XML tree is the single source of truth.

`api.py` is the `Document()` entry point, accepting both `.docx` and macro-enabled `.docm`. Word-specific parts live in `parts/`, wired into `PartFactory` at the bottom of `src/docx/__init__.py` — a new part type means editing that mapping, or `part_class_selector` for reltype-based dispatch such as images.

### Shape of a typical feature

New `CT_*` class in `oxml/` → `register_element_cls` in `oxml/__init__.py` → accessor property on the oxml class → proxy property in the API layer → enum in `enum/` if it takes a fixed value set → unit tests including schema-order placement → optionally a `.feature` scenario.

## Testing conventions

- `tests/unitutil/cxml.py` implements **CXEL**, a compact XML language used throughout: `element("w:p/w:pPr/w:jc{w:val=center}")` builds a real oxml tree and `xml(...)` produces the expected serialization to assert against `element.xml`. Prefer it over hand-written XML. Parenthesised siblings express order: `"w:r/w:rPr/(w:w{w:val=150},w:sz{w:val=28})"`.
- `tests/unitutil/mock.py` wraps `mock` with `class_mock`, `instance_mock`, `method_mock`, `property_mock`.
- Newer tests use `@pytest.mark.parametrize`; older ones use `*_fixture` tuple fixtures. Follow the file you are in.
- `features/` holds 67 behave acceptance features with steps in `features/steps/`.
- When a change breaks an inherited test, **fix the test properly rather than weakening the assertion**. Several 0.9.x failures existed because assertions were left broken.

## Reference material

`ref/` holds the ISO/IEC 29500 specification PDFs and the `xsd/` and `rnc/` schemas. Use them to confirm element names, cardinality, value ranges and whether a type is `xsd:all` or `xsd:sequence` before writing oxml classes — this is faster and more reliable than inferring from existing documents, and the 0.9.x code contains several errors that came from not doing it.

## Code style

Upstream v1.2.0 style: `from __future__ import annotations`, type annotations throughout, PEP 257 docstrings using `|Paragraph|` substitution references and backtick-quoted parameter names. Line length 100, enforced by ruff. Match the surrounding file.

## Release

Version lives in `src/docx/__init__.py` (`__version__`, read dynamically by setuptools). Pushing a git tag triggers `.github/workflows/python-publish.yml`, which verifies the tag matches `docx.__version__`, runs the tests, builds with uv and publishes to PyPI.
