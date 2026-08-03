.. _footnotes_api:

Footnote-related objects
========================

A footnote is a note at the foot of the page the text referencing it falls on. The
footnotes of a document live in their own part; a footnote appears in the rendered
document only where a run references it::

    footnote = document.footnotes.add_footnote("See Smith (2019), p. 42.")
    paragraph.add_run().add_footnote_reference(footnote)

Word keeps two more footnotes in the same part, at ids -1 and 0, holding the rule it
draws above the footnote area and its continuation on the next page. Those are
structural and never appear in the |Footnotes| collection.

.. currentmodule:: docx.footnotes


|Footnotes| objects
-------------------

.. autoclass:: Footnotes()
   :members:
   :inherited-members:
   :exclude-members:
       part


|Footnote| objects
------------------

.. autoclass:: Footnote()
   :members:
   :inherited-members:
   :exclude-members:
       part
