"""Unit-test suite for what the distribution declares.

An installed copy of this library should pull in an XML parser and nothing else. The
0.9.x line shipped `behave` — a test framework — as a *runtime* requirement, so every
install of it dragged in a BDD runner and its dependency tree. Nothing in the test suite
noticed, because the tests run in an environment where the development tooling is
present anyway.

These read the metadata of the installed distribution rather than `pyproject.toml`, so
they check what a user would actually receive.
"""

from __future__ import annotations

import re
from importlib.metadata import PackageNotFoundError, requires

import pytest

# -- everything this package is allowed to require at run time. Adding to this list is a
# -- deliberate act: each entry becomes a mandatory install for every downstream user. --
ALLOWED_RUNTIME_DEPENDENCIES = {"lxml", "typing_extensions"}

# -- development tooling that has previously escaped, or plausibly could. A test runner
# -- or docs generator in the runtime set is always a mistake. --
DEVELOPMENT_TOOLING = {
    "behave",
    "coverage",
    "mkdocs",
    "mkdocs-material",
    "mkdocstrings",
    "pyright",
    "pytest",
    "pytest-cov",
    "ruff",
    "tox",
    "twine",
    "types-lxml",
    "types-lxml-multi-subclass",
}


def _requirement_names() -> set[str]:
    """The distribution names this package requires unconditionally.

    Requirements guarded by an extra carry a `; extra == "..."` marker and are excluded —
    they are opt-in and are not imposed on an ordinary install.
    """
    try:
        declared = requires("python-docx-ng")
    except PackageNotFoundError:  # pragma: no cover -- not installed, nothing to check
        pytest.skip("python-docx-ng is not installed in this environment")
    if declared is None:  # pragma: no cover -- a distribution with no dependencies
        return set()
    names: set[str] = set()
    for requirement in declared:
        if "extra ==" in requirement:
            continue
        # -- name is everything up to the first version specifier, marker or bracket --
        name = re.split(r"[<>=!~;\[\s]", requirement, maxsplit=1)[0]
        if name:
            names.add(name)
    return names


class DescribeRuntimeDependencies:
    """Unit-test suite for the runtime requirements this package imposes."""

    def it_requires_nothing_beyond_the_allowed_set(self):
        unexpected = _requirement_names() - ALLOWED_RUNTIME_DEPENDENCIES

        assert not unexpected, (
            f"unexpected runtime requirement(s): {sorted(unexpected)}. Every entry here"
            " is a mandatory install for every downstream user — put development-only"
            " packages in [dependency-groups] instead, and update"
            " ALLOWED_RUNTIME_DEPENDENCIES only deliberately."
        )

    def and_it_never_requires_development_tooling(self):
        """The specific failure 0.9.x shipped: `behave` as a runtime requirement."""
        leaked = _requirement_names() & DEVELOPMENT_TOOLING

        assert not leaked, (
            f"development tooling declared as a runtime requirement: {sorted(leaked)}"
        )

    def but_it_does_require_an_xml_parser(self):
        """A guard against the allowlist being satisfied by requiring nothing at all."""
        assert "lxml" in _requirement_names()


class DescribeLxmlFloor:
    """Unit-test suite for the lower bound on lxml.

    The floor is a security boundary, not a compatibility one: CVE-2026-41066 is fixed
    in 6.1.0 and affects every earlier release. A well-meaning relaxation of the pin
    would silently re-admit a vulnerable parser.
    """

    def it_excludes_releases_affected_by_cve_2026_41066(self):
        declared = requires("python-docx-ng") or []
        lxml_requirements = [r for r in declared if r.startswith("lxml")]

        assert lxml_requirements, "lxml is not declared at all"
        assert any(
            ">=6.1" in requirement or ">=7" in requirement for requirement in lxml_requirements
        ), (
            f"lxml requirement {lxml_requirements} admits releases before 6.1.0, which are"
            " affected by CVE-2026-41066 (XXE to local files via the default configuration"
            " of iterparse() and ETCompatXMLParser())"
        )
