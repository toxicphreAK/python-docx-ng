"""Generate an API reference page for every module in the package.

Run by ``mkdocs-gen-files`` during the build, so the reference never falls behind the
code: a new module appears in the documentation as soon as it exists. The pages are
virtual — nothing is written into ``docs/``.

Every module is included, including the ``oxml`` and ``opc`` layers, so that a docstring
cross-reference to an internal class still resolves to a page. The navigation nests them
under their package, which keeps them out of the way of the public API.
"""

from __future__ import annotations

from pathlib import Path

import mkdocs_gen_files

SOURCE_ROOT = Path(__file__).parent.parent / "src"

nav = mkdocs_gen_files.Nav()

for path in sorted(SOURCE_ROOT.rglob("*.py")):
    module_path = path.relative_to(SOURCE_ROOT).with_suffix("")
    doc_path = path.relative_to(SOURCE_ROOT).with_suffix(".md")
    parts = tuple(module_path.parts)

    if parts[-1] == "__init__":
        parts = parts[:-1]
        doc_path = doc_path.with_name("index.md")
    elif parts[-1] == "__main__":
        continue

    nav[parts] = doc_path.as_posix()

    with mkdocs_gen_files.open(Path("api", doc_path), "w") as page:
        print(f"::: {'.'.join(parts)}", file=page)

    mkdocs_gen_files.set_edit_path(Path("api", doc_path), Path("../src", path.name))

with mkdocs_gen_files.open("api/SUMMARY.md", "w") as summary:
    summary.writelines(nav.build_literate_nav())
