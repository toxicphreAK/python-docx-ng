# python-docx-ng

*python-docx-ng* is a Python library for creating and updating Microsoft Word (.docx) files.
It was originally designed and developed by [scanny](https://github.com/scanny) as [python-docx](https://github.com/python-openxml/python-docx).
As he is not actively developing his repo and there are soo many useful pull requests, bringing together a more powerful tool.
This repo should merge a lot of those things and create a more powerful version, hopefully bearing the original structure of scanny in mind.

A new documentation section will be build up soon based on Markdown in the [docs](docs) section.
Examples can be found here: [examples](docs/examples)
Older information is available in the [python-docx Documentation](https://python-docx.readthedocs.org/en/latest/).

## Installation

```commandline
pip install python-docx-ng
```

> Hint: The library is called `docx` in python scripts, so use imports like `import docx`. 

## Features

+ [x] Word 16 (Office 2019) Template ([54a1269](https://github.com/toxicphreAK/python-docx-ng/commit/54a1269a3608239adfef079840f69389235c88b8))
+ [x] Faster & improved tables ([#1](https://github.com/toxicphreAK/python-docx-ng/pull/1))
+ [x] SVG support ([#4](https://github.com/toxicphreAK/python-docx-ng/pull/4))
+ [x] Font scaling ([#6](https://github.com/toxicphreAK/python-docx-ng/pull/6))
+ [x] Outline level ([#7](https://github.com/toxicphreAK/python-docx-ng/pull/7)) - shows outline in navigation (e.g. Word or PDF application - not affecting the document itself)
+ [x] RGB color font highlighting ([#14](https://github.com/toxicphreAK/python-docx-ng/pull/14))
+ [x] Hyperlink text ([#16](https://github.com/toxicphreAK/python-docx-ng/pull/16))
+ [x] `.docm` file support ([#19](https://github.com/toxicphreAK/python-docx-ng/pull/16)) - enables marco documents
+ [x] Form fields & AltChunk support ([#20](https://github.com/toxicphreAK/python-docx-ng/pull/20))
+ [x] Custom namespaces ([#21](https://github.com/toxicphreAK/python-docx-ng/pull/21))
+ [x] Performance improvements
  + Paragraph.text ([#3}(https://github.com/toxicphreAK/python-docx-ng/pull/3)
  + Cache for table cells ([#8](https://github.com/toxicphreAK/python-docx-ng/pull/8))
+ [x] Fixes
  + add_picture ([#10](https://github.com/toxicphreAK/python-docx-ng/pull/10)) - fix next_id to support multiple pictures
  + `Heading 1` key error due to style capitalization (e.g. in LibreOffice) ([#12](https://github.com/toxicphreAK/python-docx-ng/pull/12))
  + Fix XPath for sectPr in document ([#15](https://github.com/toxicphreAK/python-docx-ng/pull/15))
  + Reproducible documents ([#17](https://github.com/toxicphreAK/python-docx-ng/pull/17)) - same binary output with same data
  + AttValue too long in etree xml parser ([#24](https://github.com/toxicphreAK/python-docx-ng/pull/24))

## Roadmap

+ [ ] Document all functionallities building a new sample document with *all* (most) features included
+ [ ] Remove code references to original repo of python-docx
+ [ ] Setup new docs (markdown based)
+ [ ] Add missing tests
