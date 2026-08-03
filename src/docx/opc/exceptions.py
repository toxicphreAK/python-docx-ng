"""Exceptions specific to python-opc.

The base exception class is OpcError.
"""


class OpcError(Exception):
    """Base error class for python-opc."""


class PackageNotFoundError(OpcError):
    """Raised when a package cannot be found at the specified path.

    Also raised when the file is present but is not a readable OPC package, for example
    a truncated download or a file that is not a zip archive at all.
    """


class DanglingRelationshipWarning(UserWarning):
    """Issued when a relationship targets a part that is not present in the package.

    The relationship is dropped on load, which is what Word does with one. Filter this
    category to silence the warning, or turn it into an error with
    :func:`warnings.simplefilter`.
    """


class EncryptedPackageError(PackageNotFoundError):
    """Raised when the file is a password-protected (encrypted) Office document.

    An encrypted document is an OLE compound file wrapping the encrypted package, not a
    zip archive, so it cannot be read without the password. Subclasses
    |PackageNotFoundError| so that callers already handling an unreadable file keep
    working; catch this class specifically to tell the user their file is encrypted.
    """
