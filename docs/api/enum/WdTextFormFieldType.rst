.. _WdTextFormFieldType:

``WD_TEXT_FORM_FIELD_TYPE``
===========================

Specifies what a text form field accepts.

Example::

    from docx.enum.text import WD_TEXT_FORM_FIELD_TYPE

    form_field.text_type = WD_TEXT_FORM_FIELD_TYPE.NUMBER_TEXT

MS API name: ``WdTextFormFieldType``

https://learn.microsoft.com/en-us/office/vba/api/word.wdtextformfieldtype

----

REGULAR_TEXT
    Any text.

NUMBER_TEXT
    A number.

DATE_TEXT
    A date.

CURRENT_DATE_TEXT
    The current date, filled in by Word.

CURRENT_TIME_TEXT
    The current time, filled in by Word.

CALCULATION_TEXT
    The result of an expression, computed by Word.
