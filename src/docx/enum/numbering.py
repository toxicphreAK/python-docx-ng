"""Enumerations related to list numbering in WordprocessingML files."""

from docx.enum.base import BaseXmlEnum


class WD_NUMBER_FORMAT(BaseXmlEnum):
    """Specifies how a numbering level renders its counter.

    Corresponds to `ST_NumberFormat` in ISO/IEC 29500 §17.18.59. The specification
    defines a long tail of locale-specific formats; the ones this library can actually
    render a number for are marked below. For the rest, and for any value not listed
    here at all, :attr:`.NumberingLevel.format_number` falls back to decimal — a wrong
    number is less useful than an obviously plain one, but the alternative of raising
    would make a document using Japanese counting unreadable rather than imperfect.

    MS API name: `WdListNumberStyle` (the closest equivalent; the mapping is not exact)
    """

    DECIMAL = (0, "decimal", "Arabic numerals: 1, 2, 3. Rendered.")
    """Arabic numerals: 1, 2, 3."""

    UPPER_ROMAN = (1, "upperRoman", "Upper-case Roman numerals: I, II, III. Rendered.")
    """Upper-case Roman numerals: I, II, III."""

    LOWER_ROMAN = (2, "lowerRoman", "Lower-case Roman numerals: i, ii, iii. Rendered.")
    """Lower-case Roman numerals: i, ii, iii."""

    UPPER_LETTER = (
        3,
        "upperLetter",
        "Upper-case letters: A, B, C, continuing AA, BB, CC after Z. Rendered.",
    )
    """Upper-case letters: A, B, C, continuing AA, BB, CC after Z."""

    LOWER_LETTER = (
        4,
        "lowerLetter",
        "Lower-case letters: a, b, c, continuing aa, bb, cc after z. Rendered.",
    )
    """Lower-case letters: a, b, c, continuing aa, bb, cc after z."""

    ORDINAL = (5, "ordinal", "Ordinal numerals: 1st, 2nd, 3rd. Rendered.")
    """Ordinal numerals: 1st, 2nd, 3rd."""

    CARDINAL_TEXT = (6, "cardinalText", "Cardinal text: One, Two, Three. Not rendered.")
    """Cardinal text: One, Two, Three."""

    ORDINAL_TEXT = (7, "ordinalText", "Ordinal text: First, Second, Third. Not rendered.")
    """Ordinal text: First, Second, Third."""

    HEX = (8, "hex", "Hexadecimal numerals: 8, 9, A, B. Rendered.")
    """Hexadecimal numerals: 8, 9, A, B."""

    CHICAGO = (
        9,
        "chicago",
        "The Chicago Manual of Style sequence of footnote marks: *, †, ‡, §. Rendered.",
    )
    """The Chicago Manual of Style footnote marks."""

    DECIMAL_ZERO = (
        10,
        "decimalZero",
        "Arabic numerals with a leading zero below ten: 01, 02, 03. Rendered.",
    )
    """Arabic numerals with a leading zero below ten: 01, 02, 03."""

    BULLET = (
        11,
        "bullet",
        "A bullet rather than a number. The character shown is the literal level text,"
        " so the counter is not rendered at all.",
    )
    """A bullet rather than a number; the level text is shown literally."""

    NONE = (12, "none", "No numbering is shown for this level.")
    """No numbering is shown for this level."""

    RUSSIAN_LOWER = (13, "russianLower", "Lower-case Cyrillic letters. Not rendered.")
    """Lower-case Cyrillic letters."""

    RUSSIAN_UPPER = (14, "russianUpper", "Upper-case Cyrillic letters. Not rendered.")
    """Upper-case Cyrillic letters."""

    IDEOGRAPH_DIGITAL = (15, "ideographDigital", "Chinese numerals. Not rendered.")
    """Chinese numerals."""

    JAPANESE_COUNTING = (16, "japaneseCounting", "Japanese counting. Not rendered.")
    """Japanese counting."""

    AIUEO = (17, "aiueo", "Japanese aiueo ordering. Not rendered.")
    """Japanese aiueo ordering."""

    IROHA = (18, "iroha", "Japanese iroha ordering. Not rendered.")
    """Japanese iroha ordering."""

    DECIMAL_FULL_WIDTH = (19, "decimalFullWidth", "Full-width Arabic numerals. Not rendered.")
    """Full-width Arabic numerals."""

    DECIMAL_HALF_WIDTH = (20, "decimalHalfWidth", "Half-width Arabic numerals. Rendered.")
    """Half-width Arabic numerals."""

    GANADA = (21, "ganada", "Korean ganada ordering. Not rendered.")
    """Korean ganada ordering."""

    CHOSUNG = (22, "chosung", "Korean chosung ordering. Not rendered.")
    """Korean chosung ordering."""
