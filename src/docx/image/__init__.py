"""Provides objects that can characterize image streams.

That characterization is as to content type and size, as a required step in including
them in a document.
"""

from docx.image.bmp import Bmp
from docx.image.emf import Emf
from docx.image.gif import Gif
from docx.image.jpeg import Exif, Jfif
from docx.image.png import Png
from docx.image.svg import Svg
from docx.image.tiff import Tiff
from docx.image.webp import Webp
from docx.image.wmf import Wmf

SIGNATURES = (
    # class, offset, signature_bytes
    (Png, 0, b"\x89PNG\x0d\x0a\x1a\x0a"),
    (Jfif, 6, b"JFIF"),
    (Exif, 6, b"Exif"),
    (Gif, 0, b"GIF87a"),
    (Gif, 0, b"GIF89a"),
    (Tiff, 0, b"MM\x00*"),  # big-endian (Motorola) TIFF
    (Tiff, 0, b"II*\x00"),  # little-endian (Intel) TIFF
    (Bmp, 0, b"BM"),
    # -- a WebP file is a RIFF container, so it starts with "RIFF"; the form mark at
    # -- offset 8 is what distinguishes it from a WAV or an AVI --
    (Webp, 8, b"WEBP"),
    # -- `dSignature` in the EMF header. The first 40 bytes are records and extents, so
    # -- there is nothing distinctive to match earlier. --
    (Emf, 40, b" EMF"),
    # -- the Aldus Placeable Metafile key. A WMF without this prefix carries no display
    # -- size and is not recognized; see `docx.image.wmf`. --
    (Wmf, 0, b"\xd7\xcd\xc6\x9a"),
)

# -- formats with no magic number, identified by inspecting the leading bytes. Tried
# -- only after every signature above has failed to match. --
SNIFFERS = (
    # class, predicate over the leading bytes of the file
    (Svg, Svg.sniff),
)
