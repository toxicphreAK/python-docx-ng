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

+ [x] Extended Properties support [python-docx #1206](https://github.com/python-openxml/python-docx/pull/1206)
+ [x] Word 16 (Office 2019) Template ([54a1269](https://github.com/toxicphreAK/python-docx-ng/commit/54a1269a3608239adfef079840f69389235c88b8))
+ [x] Faster & improved tables ([#1](https://github.com/toxicphreAK/python-docx-ng/pull/1))
+ [x] SVG support ([#4](https://github.com/toxicphreAK/python-docx-ng/pull/4))
+ [x] EMF support ([85a30f1](https://github.com/toxicphreAK/python-docx-ng/commit/85a30f16a1f49767e331525346d8220926ecde39))
+ [x] WMF support ([9288ec9](https://github.com/toxicphreAK/python-docx-ng/commit/9288ec96db4faed53e46221e61100106e82934d8))
+ [x] Font scaling ([#6](https://github.com/toxicphreAK/python-docx-ng/pull/6))
+ [x] Outline level ([#7](https://github.com/toxicphreAK/python-docx-ng/pull/7)) - shows outline in navigation (e.g. Word or PDF application - not affecting the document itself)
+ [x] RGB color font highlighting ([#14](https://github.com/toxicphreAK/python-docx-ng/pull/14))
+ [x] Hyperlink text ([#16](https://github.com/toxicphreAK/python-docx-ng/pull/16))
+ [x] `.docm` file support ([#19](https://github.com/toxicphreAK/python-docx-ng/pull/16)) - enables marco documents
+ [x] Form fields & AltChunk support ([#20](https://github.com/toxicphreAK/python-docx-ng/pull/20))
+ [x] Custom namespaces ([#21](https://github.com/toxicphreAK/python-docx-ng/pull/21))
+ [x] Comment support ([85a30f1](https://github.com/toxicphreAK/python-docx-ng/commit/85a30f16a1f49767e331525346d8220926ecde39))
+ [x] Footnote support ([85a30f1](https://github.com/toxicphreAK/python-docx-ng/commit/85a30f16a1f49767e331525346d8220926ecde39))
+ [x] Shading support ([9288ec9](https://github.com/toxicphreAK/python-docx-ng/commit/9288ec96db4faed53e46221e61100106e82934d8))
+ [x] Performance improvements
  + Paragraph.text ([#3}(https://github.com/toxicphreAK/python-docx-ng/pull/3)
  + Cache for table cells ([#8](https://github.com/toxicphreAK/python-docx-ng/pull/8))
+ [x] Fixes
  + Fix table issue [python-docx#1196](https://github.com/python-openxml/python-docx/pull/1196) - as table columns were not assigned correctly, see [python-docx#1193](https://github.com/python-openxml/python-docx/issues/1193)
  + Fix table merging recusion [https://github.com/python-openxml/python-docx/issues/1208](https://github.com/python-openxml/python-docx/issues/1208) - replace recursion with for loop
  + add_picture ([#10](https://github.com/toxicphreAK/python-docx-ng/pull/10)) - fix next_id to support multiple pictures
  + `Heading 1` key error due to style capitalization (e.g. in LibreOffice) ([#12](https://github.com/toxicphreAK/python-docx-ng/pull/12))
  + Fix XPath for sectPr in document ([#15](https://github.com/toxicphreAK/python-docx-ng/pull/15))
  + Reproducible documents ([#17](https://github.com/toxicphreAK/python-docx-ng/pull/17)) - same binary output with same data
  + AttValue too long in etree xml parser ([#24](https://github.com/toxicphreAK/python-docx-ng/pull/24))

## Roadmap

+ [ ] Document all functionallities building a new sample document with *all* (most) features included
  + [ ] Go through *all* Issues of python-docx repo
    + Open & To Be Implemented:
      + [ ] media file path issue - https://github.com/python-openxml/python-docx/pull/1205
      + [ ] automatically update table of contents - https://github.com/python-openxml/python-docx/issues/1207
      + [ ] specify table location (not at end of document) - https://github.com/python-openxml/python-docx/issues/1204
      + [ ] read information from activex elements - https://github.com/python-openxml/python-docx/issues/1197
      + [ ] begin new list numbering - https://github.com/python-openxml/python-docx/issues/1194
  + [ ] Search on stackoverflow and document solutions
+ [ ] Remove code references to original repo of python-docx
+ [ ] Setup new docs (markdown based)
+ [ ] Add missing tests
