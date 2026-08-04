"""Exceptions used with python-docx.

The base exception class is PythonDocxError.
"""


class PythonDocxError(Exception):
    """Generic error class."""


class InvalidSpanError(PythonDocxError):
    """Raised when an invalid merge region is specified in a request to merge table
    cells."""


class InvalidXmlError(PythonDocxError):
    """Raised when invalid XML is encountered, such as on attempt to access a missing
    required child element."""


class StrictOoxmlNotSupportedError(PythonDocxError):
    """Raised on opening an ISO/IEC 29500 Strict document.

    Word's "Strict Open XML Document" save format writes the same element names in the
    Strict namespaces (``http://purl.oclc.org/ooxml/...``) rather than the Transitional
    ones this library reads. The file is an ordinary-looking ``.docx``, so without this
    the failure is an :class:`AttributeError` naming an lxml internal, which says
    nothing about what is actually wrong or what to do about it.

    Strict is the default in some regulated and public-sector environments. Re-saving
    the file from Word as "Word Document (.docx)" produces the Transitional form.
    """
