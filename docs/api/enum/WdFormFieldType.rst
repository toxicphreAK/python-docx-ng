.. _WdFormFieldType:

``WD_FORM_FIELD_TYPE``
======================

Specifies the kind of a legacy form field.

The kind is determined by which child of ``w:ffData`` is present, not by an attribute
value, so these members have no XML value mapping.

Example::

    from docx.enum.text import WD_FORM_FIELD_TYPE

    for form_field in document.form_fields:
        if form_field.type == WD_FORM_FIELD_TYPE.CHECK_BOX:
            form_field.value = True

MS API name: ``WdFieldType`` (the form-field subset)

https://learn.microsoft.com/en-us/office/vba/api/word.wdfieldtype

----

TEXT
    A text input, which Word calls FORMTEXT.

CHECK_BOX
    A check box, which Word calls FORMCHECKBOX.

DROP_DOWN
    A drop-down list, which Word calls FORMDROPDOWN.
