# pyright: reportImportCycles=false

"""Simple-type classes, corresponding to ST_* schema items.

These provide validation and format translation for values stored in XML element
attributes. Naming generally corresponds to the simple type in the associated XML
schema.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Tuple, cast

from docx.exceptions import InvalidXmlError
from docx.shared import Emu, Length, RGBColor, Twips


class BaseSimpleType:
    """Base class for simple-types."""

    @classmethod
    def from_xml(cls, xml_value: str) -> Any:
        return cls.convert_from_xml(xml_value)

    @classmethod
    def to_xml(cls, value: Any) -> str:
        cls.validate(value)
        str_value = cls.convert_to_xml(value)
        return str_value

    @classmethod
    def convert_from_xml(cls, str_value: str) -> Any:
        return int(str_value)

    @classmethod
    def convert_to_xml(cls, value: Any) -> str: ...

    @classmethod
    def validate(cls, value: Any) -> None: ...

    @classmethod
    def validate_int(cls, value: object):
        if not isinstance(value, int):
            raise TypeError("value must be <type 'int'>, got %s" % type(value))

    @classmethod
    def validate_int_in_range(cls, value: int, min_inclusive: int, max_inclusive: int) -> None:
        cls.validate_int(value)
        if value < min_inclusive or value > max_inclusive:
            raise ValueError(
                "value must be in range %d to %d inclusive, got %d"
                % (min_inclusive, max_inclusive, value)
            )

    @classmethod
    def validate_string(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise TypeError("value must be a string, got %s" % type(value))
        return value


class BaseIntType(BaseSimpleType):
    @classmethod
    def convert_from_xml(cls, str_value: str) -> int:
        return int(str_value)

    @classmethod
    def convert_to_xml(cls, value: int) -> str:
        return str(value)

    @classmethod
    def validate(cls, value: Any) -> None:
        cls.validate_int(value)


class BaseStringType(BaseSimpleType):
    @classmethod
    def convert_from_xml(cls, str_value: str) -> str:
        return str_value

    @classmethod
    def convert_to_xml(cls, value: str) -> str:
        return value

    @classmethod
    def validate(cls, value: str):
        cls.validate_string(value)


class BaseStringEnumerationType(BaseStringType):
    _members: Tuple[str, ...]

    @classmethod
    def validate(cls, value: Any) -> None:
        cls.validate_string(value)
        if value not in cls._members:
            raise ValueError("must be one of %s, got '%s'" % (cls._members, value))


class XsdAnyUri(BaseStringType):
    """There's a regex in the spec this is supposed to meet...

    but current assessment is that spending cycles on validating wouldn't be worth it
    for the number of programming errors it would catch.
    """


class XsdBoolean(BaseSimpleType):
    @classmethod
    def convert_from_xml(cls, str_value: str) -> bool:
        if str_value not in ("1", "0", "true", "false"):
            raise InvalidXmlError(
                "value must be one of '1', '0', 'true' or 'false', got '%s'" % str_value
            )
        return str_value in ("1", "true")

    @classmethod
    def convert_to_xml(cls, value: bool) -> str:
        return {True: "1", False: "0"}[value]

    @classmethod
    def validate(cls, value: Any) -> None:
        if value not in (True, False):
            raise TypeError(
                "only True or False (and possibly None) may be assigned, got '%s'" % value
            )


class XsdId(BaseStringType):
    """String that must begin with a letter or underscore and cannot contain any colons.

    Not fully validated because not used in external API.
    """

    pass


class XsdInt(BaseIntType):
    @classmethod
    def validate(cls, value: Any) -> None:
        cls.validate_int_in_range(value, -2147483648, 2147483647)


class XsdLong(BaseIntType):
    @classmethod
    def validate(cls, value: Any) -> None:
        cls.validate_int_in_range(value, -9223372036854775808, 9223372036854775807)


class XsdString(BaseStringType):
    pass


class XsdStringEnumeration(BaseStringEnumerationType):
    """Set of enumerated xsd:string values."""


class XsdToken(BaseStringType):
    """Xsd:string with whitespace collapsing, e.g. multiple spaces reduced to one,
    leading and trailing space stripped."""

    pass


class XsdUnsignedInt(BaseIntType):
    @classmethod
    def validate(cls, value: Any) -> None:
        cls.validate_int_in_range(value, 0, 4294967295)


class XsdUnsignedLong(BaseIntType):
    @classmethod
    def validate(cls, value: Any) -> None:
        cls.validate_int_in_range(value, 0, 18446744073709551615)


class ST_BrClear(XsdString):
    @classmethod
    def validate(cls, value: str) -> None:
        cls.validate_string(value)
        valid_values = ("none", "left", "right", "all")
        if value not in valid_values:
            raise ValueError("must be one of %s, got '%s'" % (valid_values, value))


class ST_BrType(XsdString):
    @classmethod
    def validate(cls, value: Any) -> None:
        cls.validate_string(value)
        valid_values = ("page", "column", "textWrapping")
        if value not in valid_values:
            raise ValueError("must be one of %s, got '%s'" % (valid_values, value))


class ST_Coordinate(BaseIntType):
    @classmethod
    def convert_from_xml(cls, str_value: str) -> Length:
        if "i" in str_value or "m" in str_value or "p" in str_value:
            return ST_UniversalMeasure.convert_from_xml(str_value)
        return Emu(int(str_value))

    @classmethod
    def validate(cls, value: Any) -> None:
        ST_CoordinateUnqualified.validate(value)


class ST_CoordinateUnqualified(XsdLong):
    @classmethod
    def validate(cls, value: Any) -> None:
        cls.validate_int_in_range(value, -27273042329600, 27273042316900)


class ST_DateTime(BaseSimpleType):
    @classmethod
    def convert_from_xml(cls, str_value: str) -> dt.datetime:
        """Convert an xsd:dateTime string to a datetime object."""

        def parse_xsd_datetime(dt_str: str) -> dt.datetime:
            # -- handle trailing 'Z' (Zulu/UTC), common in Word files --
            if dt_str.endswith("Z"):
                try:
                    # -- optional fractional seconds case --
                    return dt.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                        tzinfo=dt.timezone.utc
                    )
                except ValueError:
                    return dt.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ").replace(
                        tzinfo=dt.timezone.utc
                    )

            # -- handles explicit offsets like +00:00, -05:00, or naive datetimes --
            try:
                return dt.datetime.fromisoformat(dt_str)
            except ValueError:
                # -- fall-back to parsing as naive datetime (with or without fractional seconds) --
                try:
                    return dt.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%f")
                except ValueError:
                    return dt.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")

        try:
            # -- parse anything reasonable, but never raise, just use default epoch time --
            return parse_xsd_datetime(str_value)
        except Exception:
            return dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)

    @classmethod
    def convert_to_xml(cls, value: dt.datetime) -> str:
        # -- convert naive datetime to timezon-aware assuming local timezone --
        if value.tzinfo is None:
            value = value.astimezone()

        # -- convert to UTC if not already --
        value = value.astimezone(dt.timezone.utc)

        # -- format with 'Z' suffix for UTC --
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")

    @classmethod
    def validate(cls, value: Any) -> None:
        if not isinstance(value, dt.datetime):
            raise TypeError("only a datetime.datetime object may be assigned, got '%s'" % value)


class ST_DecimalNumber(XsdInt):
    pass


class ST_DrawingElementId(XsdUnsignedInt):
    pass


class ST_WrapDistance(XsdUnsignedInt):
    """Distance in EMU held clear of a floating shape when text wraps around it.

    The `distT`, `distB`, `distL` and `distR` attributes of `wp:anchor`. Exchanged as
    |Length| so it composes with `Pt()`, `Inches()` and the rest.
    """

    @classmethod
    def convert_from_xml(cls, str_value: str) -> Length:
        return Emu(int(str_value))


class ST_EighthPointMeasure(XsdUnsignedLong):
    """Measure in eighths of a point, e.g. `"4"` is half a point.

    Used for border widths (`w:sz` on `w:tblBorders/w:top` and friends). Values are
    exchanged as |Length| so they compose with `Pt()`, `Inches()` and the rest.
    """

    @classmethod
    def convert_from_xml(cls, str_value: str) -> Length:
        return Emu(int(round(float(str_value) / 8.0 * Length._EMUS_PER_PT)))

    @classmethod
    def convert_to_xml(cls, value: int | Length) -> str:
        return str(int(round(Emu(value).pt * 8)))


class ST_PointMeasure(XsdUnsignedLong):
    """Measure in whole points, e.g. `"4"` is four points.

    Used for the offset of a border from the text it surrounds (`w:space`). Values are
    exchanged as |Length|, as for :class:`ST_EighthPointMeasure`.
    """

    @classmethod
    def convert_from_xml(cls, str_value: str) -> Length:
        return Emu(int(round(float(str_value) * Length._EMUS_PER_PT)))

    @classmethod
    def convert_to_xml(cls, value: int | Length) -> str:
        return str(int(round(Emu(value).pt)))


class ST_FldCharType(XsdStringEnumeration):
    """Valid values for the `w:fldChar/@w:fldCharType` attribute."""

    BEGIN = "begin"
    SEPARATE = "separate"
    END = "end"

    _members = (BEGIN, SEPARATE, END)


class ST_FtnEdn(XsdStringEnumeration):
    """Valid values for the `w:footnote/@w:type` and `w:endnote/@w:type` attributes."""

    NORMAL = "normal"
    SEPARATOR = "separator"
    CONTINUATION_SEPARATOR = "continuationSeparator"
    CONTINUATION_NOTICE = "continuationNotice"

    _members = (NORMAL, SEPARATOR, CONTINUATION_SEPARATOR, CONTINUATION_NOTICE)


class ST_HexColor(BaseStringType):
    """`ST_HexColor`, a union of an RGB triple and the literal "auto".

    `ref/xsd/wml.xsd:159` defines it as `<xsd:union memberTypes="ST_HexColorAuto
    s:ST_HexColorRGB"/>`, so "auto" — meaning "let the consumer choose a colour that
    contrasts with the background" — is as valid as a hex triple. Both directions
    accept it; converting one way only would make a value readable and not writable.
    """

    @classmethod
    def convert_from_xml(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls, str_value: str
    ) -> RGBColor | str:
        if str_value == "auto":
            return ST_HexColorAuto.AUTO
        return RGBColor.from_string(str_value)

    @classmethod
    def convert_to_xml(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls, value: RGBColor | str
    ) -> str:
        """Keep alpha hex numerals all uppercase just for consistency."""
        if value == ST_HexColorAuto.AUTO:
            return ST_HexColorAuto.AUTO
        # expecting 3-tuple of ints in range 0-255
        return "%02X%02X%02X" % cast(RGBColor, value)

    @classmethod
    def validate(cls, value: Any) -> None:
        # must be an RGBColor object, or the string "auto" ---
        if isinstance(value, RGBColor) or value == ST_HexColorAuto.AUTO:
            return
        raise ValueError(
            'rgb color value must be an RGBColor object or "auto", got %s %s'
            % (type(value), value)
        )


class ST_HexColorAuto(XsdStringEnumeration):
    """Value for `w:color/[@val="auto"] attribute setting."""

    AUTO = "auto"

    _members = (AUTO,)


class ST_HpsMeasure(XsdUnsignedLong):
    """Half-point measure, e.g. 24.0 represents 12.0 points.

    The schema type is a union of an unsigned decimal count of half-points and a
    universal measure like `"12pt"`. A fractional count of half-points such as `"21.5"`
    is not strictly valid, but Word reads it and several other generators write it, so
    it is accepted here and rounded to the nearest EMU.
    """

    @classmethod
    def convert_from_xml(cls, str_value: str) -> Length:
        if "m" in str_value or "n" in str_value or "p" in str_value:
            return ST_UniversalMeasure.convert_from_xml(str_value)
        return Emu(round(float(str_value) / 2.0 * Length._EMUS_PER_PT))

    @classmethod
    def convert_to_xml(cls, value: int | Length) -> str:
        """Round to the nearest half-point rather than truncating.

        A half-point count is always written as an integer, since a fractional value is
        outside the schema type even though it is accepted on read.
        """
        emu = Emu(value)
        half_points = int(round(emu.pt * 2))
        return str(half_points)


class ST_Merge(XsdStringEnumeration):
    """Valid values for <w:xMerge val=""> attribute."""

    CONTINUE = "continue"
    RESTART = "restart"

    _members = (CONTINUE, RESTART)


class ST_OnOff(XsdBoolean):
    @classmethod
    def convert_from_xml(cls, str_value: str) -> bool:
        if str_value not in ("1", "0", "true", "false", "on", "off"):
            raise InvalidXmlError(
                "value must be one of '1', '0', 'true', 'false', 'on', or 'o"
                "ff', got '%s'" % str_value
            )
        return str_value in ("1", "true", "on")


class ST_PositiveCoordinate(XsdLong):
    @classmethod
    def convert_from_xml(cls, str_value: str) -> Length:
        return Emu(int(str_value))

    @classmethod
    def validate(cls, value: Any) -> None:
        cls.validate_int_in_range(value, 0, 27273042316900)


class ST_RelationshipId(XsdString):
    pass


class ST_SignedTwipsMeasure(XsdInt):
    @classmethod
    def convert_from_xml(cls, str_value: str) -> Length:
        if "i" in str_value or "m" in str_value or "p" in str_value:
            return ST_UniversalMeasure.convert_from_xml(str_value)
        return Twips(int(round(float(str_value))))

    @classmethod
    def convert_to_xml(cls, value: int | Length) -> str:
        emu = Emu(value)
        twips = emu.twips
        return str(twips)


class ST_PageBorderDisplay(XsdStringEnumeration):
    """Valid values for `w:pgBorders/@w:display`."""

    ALL_PAGES = "allPages"
    FIRST_PAGE = "firstPage"
    NOT_FIRST_PAGE = "notFirstPage"

    _members = (ALL_PAGES, FIRST_PAGE, NOT_FIRST_PAGE)


class ST_PageBorderOffset(XsdStringEnumeration):
    """Valid values for `w:pgBorders/@w:offsetFrom`."""

    PAGE = "page"
    TEXT = "text"

    _members = (PAGE, TEXT)


class ST_PageBorderZOrder(XsdStringEnumeration):
    """Valid values for `w:pgBorders/@w:zOrder`."""

    BACK = "back"
    FRONT = "front"

    _members = (BACK, FRONT)


class ST_MeasurementOrPercent(XsdInt):
    """The `w:w` attribute of `w:tblW`, `w:tcW`, `w:tblInd` and the rest of `CT_TblWidth`.

    What the number means depends on the sibling `w:type` attribute, which an attribute
    converter cannot see, so this type stays deliberately literal and hands back a plain
    `int`: twips for `w:type="dxa"`, fiftieths of a percent for `"pct"`. `CT_TblWidth`
    is where the two are told apart.

    The schema also admits `"50%"` and universal measures such as `"1.5in"`. Word writes
    neither, but documents from other producers do, so both are converted to the plain
    form on the way in.
    """

    @classmethod
    def convert_from_xml(cls, str_value: str) -> int:
        if str_value.endswith("%"):
            return int(round(float(str_value[:-1]) * 50))
        if "i" in str_value or "m" in str_value or "p" in str_value:
            return Emu(ST_UniversalMeasure.convert_from_xml(str_value)).twips
        return int(round(float(str_value)))


class ST_ShortHexNumber(BaseSimpleType):
    """A two-byte value written as four hexadecimal digits, e.g. `"04A0"`.

    Used for the legacy bitmask on `w:tblLook/@w:val`. Exchanged as an `int`.
    """

    @classmethod
    def convert_from_xml(cls, str_value: str) -> int:
        return int(str_value, 16)

    @classmethod
    def convert_to_xml(cls, value: int) -> str:
        return "%04X" % value

    @classmethod
    def validate(cls, value: Any) -> None:
        cls.validate_int_in_range(value, 0, 0xFFFF)


class ST_String(XsdString):
    pass


class ST_TextScalePercent(XsdInt):
    """Horizontal character scaling, as a whole percentage of normal width.

    ECMA-376 constrains `w:w/@w:val` to 1..600; Word rejects values outside that.
    """

    @classmethod
    def validate(cls, value: Any) -> None:
        cls.validate_int(value)
        if not 1 <= value <= 600:
            raise ValueError("value must be in range 1 to 600 (percent), got %d" % value)


class ST_TblLayoutType(XsdString):
    @classmethod
    def validate(cls, value: Any) -> None:
        cls.validate_string(value)
        valid_values = ("fixed", "autofit")
        if value not in valid_values:
            raise ValueError("must be one of %s, got '%s'" % (valid_values, value))


class ST_TblWidth(XsdString):
    @classmethod
    def validate(cls, value: Any) -> None:
        cls.validate_string(value)
        valid_values = ("auto", "dxa", "nil", "pct")
        if value not in valid_values:
            raise ValueError("must be one of %s, got '%s'" % (valid_values, value))


class ST_TwipsMeasure(XsdUnsignedLong):
    @classmethod
    def convert_from_xml(cls, str_value: str) -> Length:
        if "i" in str_value or "m" in str_value or "p" in str_value:
            return ST_UniversalMeasure.convert_from_xml(str_value)
        return Twips(int(str_value))

    @classmethod
    def convert_to_xml(cls, value: int | Length) -> str:
        emu = Emu(value)
        twips = emu.twips
        return str(twips)


class ST_UniversalMeasure(BaseSimpleType):
    @classmethod
    def convert_from_xml(cls, str_value: str) -> Emu:
        float_part, units_part = str_value[:-2], str_value[-2:]
        quantity = float(float_part)
        multiplier = {
            "mm": 36000,
            "cm": 360000,
            "in": 914400,
            "pt": 12700,
            "pc": 152400,
            "pi": 152400,
        }[units_part]
        return Emu(int(round(quantity * multiplier)))


class ST_VerticalAlignRun(XsdStringEnumeration):
    """Valid values for `w:vertAlign/@val`."""

    BASELINE = "baseline"
    SUPERSCRIPT = "superscript"
    SUBSCRIPT = "subscript"

    _members = (BASELINE, SUPERSCRIPT, SUBSCRIPT)
