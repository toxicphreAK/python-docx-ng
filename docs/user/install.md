# Installing

```console
pip install python-docx-ng
```

!!! warning "The import name is `docx`"

    The distribution is `python-docx-ng`, the importable package is `docx`:

    ```python
    import docx
    from docx import Document
    ```

    That is deliberate — it makes this a drop-in replacement for `python-docx`, so
    existing code and every upstream example keep working. It also means
    **`python-docx-ng` and `python-docx` cannot be installed side by side**: they claim
    the same import name, and whichever was installed last wins. Uninstall one before
    installing the other.

    ```console
    pip uninstall python-docx
    pip install python-docx-ng
    ```

## Requirements

| | |
| --- | --- |
| Python | 3.9 – 3.14 |
| [lxml](https://pypi.org/project/lxml/) | >= 6.1.0 |
| [typing_extensions](https://pypi.org/project/typing-extensions/) | >= 4.9.0 |

Both dependencies are installed for you. There are no others — no test framework, no
documentation tooling.

lxml is floored at 6.1.0 because that is the first release fixing CVE-2026-41066, an
XXE-to-local-files hole in the default configuration of `iterparse()` and
`ETCompatXMLParser()`; every 4.x and 5.x release is affected. This library uses neither
API and sets `resolve_entities=False` on its own parser, so it was never exposed itself,
but it will not pull a known-vulnerable XML parser into your dependency tree.

!!! note "If you are pinned below lxml 6"

    Another package in your environment may cap lxml below 6. In that case this release
    will not resolve, and there is no supported workaround — the floor is a security
    boundary rather than a compatibility one.

## Other installers

```console
uv add python-docx-ng
poetry add python-docx-ng
pipenv install python-docx-ng
```

## Upgrading from 0.9.x

2.0.0 rebases onto upstream python-docx v1.2.0 and **contains breaking changes**. Read
the [migration guide](migrating-from-0-9.md) before upgrading.

The 0.9.x releases are yanked on PyPI. They require `lxml<5`, which has no wheels for
Python 3.13 or later, and they declare a test framework as a runtime dependency. An
exact pin such as `python-docx-ng==0.9.7` still resolves, so existing locked builds are
unaffected, but nothing new will select one.

## Installing from source

```console
git clone https://github.com/toxicphreAK/python-docx-ng.git
cd python-docx-ng
uv sync
```

[uv](https://docs.astral.sh/uv/) is what this project uses; `uv sync` creates the
environment and installs the development dependencies. See
[CONTRIBUTING.md](https://github.com/toxicphreAK/python-docx-ng/blob/main/CONTRIBUTING.md)
for running the tests.
