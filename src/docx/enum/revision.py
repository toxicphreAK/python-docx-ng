"""Enumerations related to tracked changes in WordprocessingML files."""

from docx.enum.base import BaseXmlEnum


class WD_REVISION_TYPE(BaseXmlEnum):
    """Specifies what kind of change a tracked revision records.

    Example::

        from docx.enum.revision import WD_REVISION_TYPE

        for revision in document.revisions:
            if revision.type == WD_REVISION_TYPE.DELETION:
                revision.reject()

    MS API name: `WdRevisionType`

    https://learn.microsoft.com/en-us/office/vba/api/word.wdrevisiontype
    """

    INSERTION = (1, "ins", "Content was added.")
    """Content was added."""

    DELETION = (2, "del", "Content was removed.")
    """Content was removed."""

    MOVE_FROM = (
        5,
        "moveFrom",
        "Content was moved away from here. The deletion half of a move; the matching"
        " MOVE_TO holds the same content where it now is.",
    )
    """Content was moved away from here — the deletion half of a move."""

    MOVE_TO = (
        6,
        "moveTo",
        "Content was moved to here. The insertion half of a move.",
    )
    """Content was moved to here — the insertion half of a move."""

    FORMATTING = (
        3,
        None,
        "Formatting was changed. The revision records the properties as they were"
        " before, which is what rejecting it puts back. Covers `w:rPrChange`,"
        " `w:pPrChange` and the other `*Change` elements, which differ only in which"
        " properties they record.",
    )
    """Formatting was changed; the revision records the previous properties."""
