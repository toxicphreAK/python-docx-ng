# python-docx-ng

*python-docx-ng* is a Python library for creating and updating Microsoft Word (.docx) files.
It was originally designed and developed by [scanny](https://github.com/scanny) as [python-docx](https://github.com/python-openxml/python-docx).
As he is not actively developing his repo and there are soo many useful pull requests, bringing together a more powerful tool.
This repo should merge a lot of those things and create a more powerful version, hopefully bearing the original structure of scanny in mind.

More information is available in the [python-docx-ng Documentation](https://python-docx.readthedocs.org/en/latest/).

## Features

+ [x] Word 16 (Office 2019) Template
+ [x] Faster & improved tables (#1)
+ [x] SVG support (#4)
+ [x] Font scaling (#6)
+ [x] Outline level (#7) - shows outline in navigation (e.g. Word or PDF application - not affecting the document itself)
+ [x] RGB color font highlighting (#14)
+ [x] Hyperlink text (#16)
+ [x] `.docm` file support (#19) - enables marco documents
+ [x] Form fields & AltChunk support (#20)
+ [x] Custom namespaces (#21)
+ [x] Performance improvements
  + Paragraph.text (#3)
  + Cache for table cells (#8)
+ [x] Fixes
  + add_picture (#10) - fix next_id to support multiple pictures
  + `Heading 1` key error due to style capitalization (e.g. in LibreOffice) (#12)
  + Fix XPath for sectPr in document (#15)
  + Reproducible documents (#17) - same binary output with same data

## Roadmap

+ [ ] Document all functionallities building a new sample document with *all* (most) features included
+ [ ] Setup new docs
+ [ ] Add missing tests
