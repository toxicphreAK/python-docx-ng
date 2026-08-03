
.. _text_api:

Text-related objects
====================


|Paragraph| objects
-------------------

.. autoclass:: docx.text.paragraph.Paragraph()
   :members:


|ParagraphFormat| objects
-------------------------

.. autoclass:: docx.text.parfmt.ParagraphFormat()
   :members:


|Hyperlink| objects
-------------------

.. autoclass:: docx.text.hyperlink.Hyperlink()
   :members:


|Run| objects
-------------

.. autoclass:: docx.text.run.Run()
   :members:


|Font| objects
--------------

.. autoclass:: docx.text.run.Font()
   :members:


|RenderedPageBreak| objects
---------------------------

.. autoclass:: docx.text.pagebreak.RenderedPageBreak()
   :members:


|TabStop| objects
-----------------

.. autoclass:: docx.text.tabstops.TabStop()
   :members:


|TabStops| objects
------------------

.. autoclass:: docx.text.tabstops.TabStops()
   :members: clear_all

   .. automethod:: docx.text.tabstops.TabStops.add_tab_stop(position, alignment=WD_TAB_ALIGNMENT.LEFT, leader=WD_TAB_LEADER.SPACES)


|FormField| objects
-------------------

A *legacy form field* is what Word's Developer ribbon calls a "Legacy Form": a text
input, check box or drop-down, written as a complex field whose properties live in
``w:ffData``. These are distinct from content controls (``w:sdt``), which
:class:`.ContentControl` covers.

Reach them through :attr:`Document.form_fields` or :attr:`Paragraph.form_fields`::

    values = {f.name: f.value for f in document.form_fields}

.. autoclass:: docx.formfield.FormField()
   :members:
