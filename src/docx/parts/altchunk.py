"""|AltChunkPart| and closely related objects."""

from __future__ import annotations

import os
from typing import IO, TYPE_CHECKING

from docx.opc.constants import CONTENT_TYPE as CT
from docx.opc.packuri import PackURI
from docx.opc.part import Part

if TYPE_CHECKING:
    from docx.opc.package import OpcPackage

# -- Word chooses the importer for an alt-chunk from the content type of its part, not
# -- from the partname, so an unmapped format still works; the extension is chosen only
# -- so the package is readable by a human with an unzip tool. --
_EXT_FOR_CONTENT_TYPE = {
    CT.WML_DOCUMENT: "docx",
    CT.XML: "xml",
    "application/vnd.ms-word.document.macroEnabled.12": "docm",
    "application/rtf": "rtf",
    "application/xhtml+xml": "xhtml",
    "message/rfc822": "mht",
    "text/html": "html",
    "text/plain": "txt",
}


class AltChunkPart(Part):
    """An "alternative format import" part, the target of a `w:altChunk` reference.

    Holds an embedded document in some format other than WordprocessingML — HTML, RTF,
    plain text, MHTML, or another .docx — for Word to convert and splice in when it
    opens the file. The bytes are stored and written back unchanged; this library has no
    knowledge of the embedded format.
    """

    @classmethod
    def new(cls, package: OpcPackage, blob: bytes, content_type: str) -> AltChunkPart:
        """An |AltChunkPart| newly created from `blob` and added to `package`."""
        ext = _EXT_FOR_CONTENT_TYPE.get(content_type, "bin")
        return cls(cls._next_partname(package, ext), content_type, blob, package)

    @classmethod
    def new_from_stream(
        cls,
        package: OpcPackage,
        chunk: str | os.PathLike[str] | IO[bytes],
        content_type: str,
    ) -> AltChunkPart:
        """An |AltChunkPart| newly created from `chunk` and added to `package`.

        `chunk` is either a path to a file (a string or ``os.PathLike``) or a file-like
        object open for binary read.
        """
        if isinstance(chunk, (str, os.PathLike)):
            with open(os.fspath(chunk), "rb") as f:
                blob = f.read()
        else:
            blob = chunk.read()
        return cls.new(package, blob, content_type)

    @staticmethod
    def _next_partname(package: OpcPackage, ext: str) -> PackURI:
        """The next free `/word/afchunk{n}.{ext}` partname.

        Numbering is unique without regard to the extension, as it is for image parts,
        so two alt-chunks in different formats do not both come out as `afchunk1`.
        """
        used_numbers = {
            part.partname.idx
            for part in package.iter_parts()
            if part.partname.baseURI == "/word" and part.partname.filename.startswith("afchunk")
        }
        n = 1
        while n in used_numbers:
            n += 1
        return PackURI("/word/afchunk%d.%s" % (n, ext))
