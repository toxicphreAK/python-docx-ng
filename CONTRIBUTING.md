# Contributing to python-docx-ng

Thanks for wanting to help. This project is a downstream superset of
[python-docx](https://github.com/python-openxml/python-docx), so contributions here fall
into two kinds, and the first thing to work out is which kind yours is.

## Upstream or here?

**A bug in behaviour shared with python-docx belongs upstream.** The shared core is
python-docx v1.2.0 and we track it directly. Fixing it here means carrying a patch
forever and diverging a little further; fixing it upstream fixes it for everyone,
including us at the next catch-up. File it at
[python-openxml/python-docx](https://github.com/python-openxml/python-docx/issues), and
open an issue here too if you want it tracked.

**Anything upstream has declined, or has not adopted, belongs here.** That is the whole
reason this fork exists — tracked changes, fields, watermarks, floating images and the
rest. See the [2.0.0 milestone](https://github.com/toxicphreAK/python-docx-ng/milestone/1)
for what is planned and what is deliberately not started yet.

If you are unsure, open an issue and ask before writing code.

## Branches

- **`main`** is the 2.0.0 line and the only branch that takes work. It was restarted
  from upstream v1.2.0 in August 2026; the fork's own features are being re-applied on
  top one at a time.
- **`master`** is the 0.9.x record, kept for historical reference. Never target it, and
  never port work back onto it.
- The **`upstream`** remote is read-only.

Branch from `main`, and rebase rather than merge when `main` moves under you.

## Getting set up

The project uses [uv](https://docs.astral.sh/uv/). Do not use pip or poetry here — the
lockfile is the source of truth and the other tools will not respect it.

```bash
git clone https://github.com/toxicphreAK/python-docx-ng.git
cd python-docx-ng
uv sync
```

## The loop

```bash
uv run pytest -q                                  # unit tests
uv run pytest tests/text/test_font.py             # one module
uv run pytest -k it_knows_its_theme_typeface      # one test
uv run behave --format progress --tags=-wip       # acceptance tests
uv run ruff check .                               # lint — blocking in CI
uv run ruff format .                              # formatting
uv run pyright                                    # type check — informational, see below
make docs                                         # build the documentation into site/
make opendocs                                     # serve it with live reload
```

Before opening a pull request, run the unit tests, the acceptance tests and `ruff check`.

**Also run the tests on Python 3.9** if your change adds or edits type annotations:

```bash
uv run --python 3.9 pytest tests -q
uv sync --python 3.12          # switch back afterwards
```

That is also how the version matrix is covered locally — `uv run --python 3.11 pytest -q`
and so on. There is no tox configuration; CI runs the same command across 3.9 to 3.13.

## Things that will bite you

These have each broken the build at least once. They are not hypothetical.

**pytest collection is customised.** In `pyproject.toml`, test classes must be named
`Test*` or `Describe*`, and test functions must start with `it_`, `its_`, `they_`, `and_`
or `but_`. A conventional `def test_foo()` is **silently not collected** — it does not
error, it just never runs. If your new test seems to pass suspiciously fast, check that
it ran at all.

**PEP 604 annotations need `from __future__ import annotations`.** Supported Python is
3.9+, where `int | None` in an annotation is evaluated at runtime and raises `TypeError`
at import. Every module in the package has the import; keep it that way. This once broke
23 test modules on 3.9 while passing locally on 3.12.

**New test classes go after the fixtures of the class above them.** Fixtures live at the
bottom of each `Describe*` class. Inserting a class into the middle of a file orphans
them, and every test in the class above then errors with "fixture not found".

**pyright is not a passing gate.** The code inherited from upstream has roughly 8,900
strict-mode errors against the pinned `types-lxml` stubs. CI reports the count without
failing on it. Annotate new code properly, but do not expect a clean run, and do not
"fix" inherited errors as a side quest — it makes the diff unreviewable.

**Check `ref/xsd/` before assuming child order.** Word rejects documents whose child
order violates the schema. Some complex types are `xsd:all` rather than `xsd:sequence`
(`CT_Properties` in app.xml is one), where building `successors` bookkeeping is wasted
work implying a constraint that does not exist.

**Do not weaken a failing assertion.** When a change breaks an inherited test, fix the
test properly. Several 0.9.x failures existed only because assertions had been loosened
until they passed.

## How the code is laid out

Three layers, bottom-up. Knowing which layer owns a behaviour is most of knowing where a
change belongs.

1. **`src/docx/opc/`** — generic Open Packaging Conventions: the zip container, parts and
   relationships. No Word-specific knowledge. Output is byte-reproducible (fixed zip
   timestamps, sorted parts, ordered relationship ids); `tests/test_reproducible.py` pins
   that, so be careful about anything that changes write order.
2. **`src/docx/oxml/`** — lxml custom element classes. `oxml/xmlchemy.py` is the
   declarative DSL: `ZeroOrOne("w:pPr", successors=...)` generates `.pPr`,
   `.get_or_add_pPr()` and `._remove_pPr()`.
3. **Proxy / public API** — thin objects over oxml elements, holding no state. The XML
   tree is the single source of truth.

**Every new element class must be registered** with `register_element_cls("w:p", CT_P)`
in `oxml/__init__.py`. A class file alone does nothing; the symptom of forgetting is an
`AttributeError` on a plain `lxml.etree._Element` where you expected your class.

A typical feature is therefore: new `CT_*` class in `oxml/` → `register_element_cls` →
accessor on the oxml class → proxy property in the API layer → enum in `enum/` if it
takes a fixed value set → unit tests including schema-order placement → optionally a
`.feature` scenario.

## Testing conventions

- `tests/unitutil/cxml.py` implements **CXEL**, a compact XML language used throughout:
  `element("w:p/w:pPr/w:jc{w:val=center}")` builds a real oxml tree, and `xml(...)`
  produces the expected serialisation to assert against `element.xml`. Prefer it to
  hand-written XML. Parenthesised siblings express order:
  `"w:r/w:rPr/(w:w{w:val=150},w:sz{w:val=28})"`.
- `tests/unitutil/mock.py` wraps `mock` with `class_mock`, `instance_mock`, `method_mock`
  and `property_mock`.
- Newer tests use `@pytest.mark.parametrize`; older ones use `*_fixture` tuple fixtures.
  Follow the file you are in rather than converting it.
- `features/` holds the behave acceptance features, with steps in `features/steps/`.

When you add an element to a schema sequence, add a test asserting its placement against
a neighbouring element. That is the test that catches the "Word will not open this file"
class of bug.

## Reference material

`ref/` holds the ISO/IEC 29500 specification PDFs and the `xsd/` and `rnc/` schemas. Use
them to confirm element names, cardinality, value ranges, and whether a type is
`xsd:all` or `xsd:sequence`, before writing oxml classes. This is faster and more
reliable than inferring from example documents, and several errors in the old 0.9.x code
came from not doing it.

## Code style

Upstream v1.2.0 style: `from __future__ import annotations`, type annotations throughout,
PEP 257 docstrings using `|Paragraph|` substitution references and backtick-quoted
parameter names. Line length 100, enforced by ruff. Match the surrounding file.

## Pull requests

- One logical change per pull request. A 3000-line PR mixing a feature with a reformat
  will not get reviewed.
- Write a commit message that says what changed and why. Conventional-commit prefixes
  (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`) are used here.
- Include tests. A feature without tests will be asked for tests.
- Note in the PR whether the change affects the shared core, since that decides whether
  it should also go upstream.
- If the change alters public behaviour, update `HISTORY.rst` and, for a breaking change,
  the migration guide in `docs/`.

## Reporting bugs

Include the python-docx-ng version, the Python version, and a minimal script that
reproduces the problem. If a particular `.docx` triggers it, attach the smallest file
that still does — most bugs in this library are bugs about one specific piece of XML, and
that piece is much easier to find in a two-paragraph document than in a 90-page report.

## Licence

By contributing you agree that your contribution is licensed under the MIT Licence, the
same terms as the rest of the project.
