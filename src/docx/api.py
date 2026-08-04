"""Directly exposed API functions and classes, :func:`Document` for now.

Provides a syntactically more convenient API for interacting with the OpcPackage graph.
"""

from __future__ import annotations

import os
from typing import IO, TYPE_CHECKING, cast

from docx.opc.constants import CONTENT_TYPE as CT
from docx.package import Package

if TYPE_CHECKING:
    from docx.document import Document as DocumentObject
    from docx.parts.document import DocumentPart

# -- content types whose main part is a Word document body. Each of `.docm`, `.dotx`
# -- and `.dotm` uses a distinct content type from `.docx` but the same
# -- WordprocessingML markup; the macro storage the macro-enabled forms add lives in a
# -- separate part that round-trips untouched. --
_WORD_MAIN_CONTENT_TYPES = (
    CT.WML_DOCUMENT_MAIN,
    CT.WML_DOCUMENT_MACRO_ENABLED_MAIN,
    CT.WML_TEMPLATE_MAIN,
    CT.WML_TEMPLATE_MACRO_ENABLED_MAIN,
)


def Document(docx: str | os.PathLike[str] | IO[bytes] | None = None) -> DocumentObject:
    """Return a |Document| object loaded from `docx`, where `docx` can be either a path
    to a ``.docx`` file (a string or ``os.PathLike``) or a file-like object.

    Macro-enabled ``.docm`` files and Word templates — ``.dotx`` and ``.dotm`` — are
    also accepted. Their macro storage is preserved when the document is saved, but this
    library provides no API to read or modify it.

    A template opened this way is still a template when saved; pass
    ``as_template=False`` to :meth:`.Document.save` to write it out as an ordinary
    document instead.

    If `docx` is missing or ``None``, the built-in default document "template" is
    loaded.
    """
    docx = _default_docx_path() if docx is None else docx
    if isinstance(docx, os.PathLike):
        docx = os.fspath(docx)
    document_part = cast("DocumentPart", Package.open(docx).main_document_part)
    if document_part.content_type not in _WORD_MAIN_CONTENT_TYPES:
        tmpl = "file '%s' is not a Word file, content type is '%s'"
        raise ValueError(tmpl % (docx, document_part.content_type))
    return document_part.document


def _default_docx_path():
    """Return the path to the built-in default .docx package."""
    _thisdir = os.path.split(__file__)[0]
    return os.path.join(_thisdir, "templates", "default.docx")
