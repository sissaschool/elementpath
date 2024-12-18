#
# Copyright (c), 2018-2021, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""
XPath 2.0 implementation - part 4 (XSD constructors)
"""
import decimal
from typing import cast, Optional, Union

from elementpath.aliases import Emptiable
from elementpath.exceptions import ElementPathError, ElementPathSyntaxError
from elementpath.namespaces import XSD_NAMESPACE
from elementpath.datatypes import xsd10_atomic_types, xsd11_atomic_types, \
    GregorianDay, GregorianMonth, GregorianMonthDay, GregorianYear10, \
    GregorianYear, GregorianYearMonth10, GregorianYearMonth, Duration, \
    DayTimeDuration, YearMonthDuration, Date10, Date, DateTime10, DateTime, \
    DateTimeStamp, Time, UntypedAtomic, QName, HexBinary, Base64Binary, \
    BooleanProxy, AnyURI, AtomicType, NumericType, Notation
from elementpath.xpath_context import ContextType, XPathSchemaContext
from elementpath.xpath_tokens import XPathConstructor

from ._xpath2_functions import XPath2Parser

register = XPath2Parser.register
unregister = XPath2Parser.unregister
method = XPath2Parser.method
constructor = XPath2Parser.constructor

# Type annotations aliases
OtherDateTimeTypes = Union[
    Date10, GregorianDay, GregorianMonth, GregorianMonthDay, GregorianYear10,
    GregorianYear, GregorianYearMonth10, GregorianYearMonth, Time
]


###
# Constructors for string-based XSD types
@constructor('normalizedString')
@constructor('token')
@constructor('language')
@constructor('NMTOKEN')
@constructor('Name')
@constructor('NCName')
@constructor('ID')
@constructor('IDREF')
@constructor('ENTITY')
@constructor('anyURI')
def cast_string_based_types(self: XPathConstructor, value: AtomicType) \
        -> Union[str, AnyURI]:
    try:
        result = xsd10_atomic_types[self.symbol](value)
    except ValueError as err:
        raise self.error('FORG0001', err)
    else:
        assert isinstance(result, (str, AnyURI))
        return result


###
# Constructors for numeric XSD types
@constructor('decimal')
@constructor('double')
@constructor('float')
def cast_numeric_types(self: XPathConstructor, value: AtomicType) -> NumericType:
    try:
        if self.parser.xsd_version == '1.0':
            result = xsd10_atomic_types[self.symbol](value)
        else:
            result = xsd11_atomic_types[self.symbol](value)
    except ValueError as err:
        if isinstance(value, (str, UntypedAtomic)):
            raise self.error('FORG0001', err)
        raise self.error('FOCA0002', err)
    except ArithmeticError as err:
        raise self.error('FOCA0002', err) from None
    else:
        assert isinstance(result, (int, float, decimal.Decimal))
        return result


@constructor('integer')
@constructor('nonNegativeInteger')
@constructor('positiveInteger')
@constructor('nonPositiveInteger')
@constructor('negativeInteger')
@constructor('long')
@constructor('int')
@constructor('short')
@constructor('byte')
@constructor('unsignedLong')
@constructor('unsignedInt')
@constructor('unsignedShort')
@constructor('unsignedByte')
def cast_integer_types(self: XPathConstructor, value: AtomicType) -> int:
    try:
        result = xsd10_atomic_types[self.symbol](value)
    except ValueError:
        msg = 'could not convert {!r} to xs:{}'.format(value, self.symbol)
        if isinstance(value, (str, bytes, int, UntypedAtomic)):
            raise self.error('FORG0001', msg) from None
        raise self.error('FOCA0002', msg) from None
    except ArithmeticError as err:
        raise self.error('FOCA0002', err) from None
    else:
        assert isinstance(result, int)
        return result


###
# Constructors for datetime XSD types
@constructor('date')
def cast_date_type(self: XPathConstructor, value: AtomicType) -> Date10:
    cls = Date if self.parser.xsd_version == '1.1' else Date10
    if isinstance(value, cls):
        return value

    try:
        if isinstance(value, UntypedAtomic):
            result = cls.fromstring(value.value)
        elif isinstance(value, DateTime10):
            result = cls(value.year, value.month, value.day, value.tzinfo)
        else:
            result = cls.fromstring(value)  # type: ignore[arg-type]
    except OverflowError as err:
        raise self.error('FODT0001', err) from None
    except ValueError as err:
        raise self.error('FORG0001', err)
    else:
        assert isinstance(result, Date10)
        return result


@constructor('gDay')
def cast_gregorian_day_type(self: XPathConstructor, value: AtomicType) -> GregorianDay:
    if isinstance(value, GregorianDay):
        return value

    try:
        if isinstance(value, UntypedAtomic):
            result = GregorianDay.fromstring(value.value)
        elif isinstance(value, (Date10, DateTime10)):
            result = GregorianDay(value.day, value.tzinfo)
        else:
            result = GregorianDay.fromstring(value)  # type: ignore[arg-type]
    except ValueError as err:
        raise self.error('FORG0001', err)
    else:
        assert isinstance(result, GregorianDay)
        return result


@constructor('gMonth')
def cast_gregorian_month_type(self: XPathConstructor, value: AtomicType) -> GregorianMonth:
    if isinstance(value, GregorianMonth):
        return value

    try:
        if isinstance(value, UntypedAtomic):
            return GregorianMonth.fromstring(value.value)
        elif isinstance(value, (Date10, DateTime10)):
            return GregorianMonth(value.month, value.tzinfo)
        return GregorianMonth.fromstring(value)  # type: ignore[arg-type]
    except ValueError as err:
        raise self.error('FORG0001', err)


@constructor('gMonthDay')
def cast_gregorian_month_day_type(self: XPathConstructor, value: AtomicType) \
        -> GregorianMonthDay:
    if isinstance(value, GregorianMonthDay):
        return value

    try:
        if isinstance(value, UntypedAtomic):
            return GregorianMonthDay.fromstring(value.value)
        elif isinstance(value, (Date10, DateTime10)):
            return GregorianMonthDay(value.month, value.day, value.tzinfo)
        return GregorianMonthDay.fromstring(value)  # type: ignore[arg-type]
    except ValueError as err:
        raise self.error('FORG0001', err)


@constructor('gYear')
def cast_gregorian_year_type(self: XPathConstructor, value: AtomicType) \
        -> Union[GregorianYear10, GregorianYear]:
    cls = GregorianYear if self.parser.xsd_version == '1.1' else GregorianYear10
    if isinstance(value, cls):
        return value

    try:
        if isinstance(value, UntypedAtomic):
            return cls.fromstring(value.value)
        elif isinstance(value, (Date10, DateTime10)):
            return cls(value.year, value.tzinfo)
        return cls.fromstring(value)  # type: ignore[arg-type]
    except OverflowError as err:
        raise self.error('FODT0001', err) from None
    except ValueError as err:
        raise self.error('FORG0001', err)


@constructor('gYearMonth')
def cast_gregorian_year_month_type(self: XPathConstructor, value: AtomicType) \
        -> Union[GregorianYearMonth10, GregorianYearMonth]:
    cls = GregorianYearMonth \
        if self.parser.xsd_version == '1.1' else GregorianYearMonth10
    if isinstance(value, cls):
        return value

    try:
        if isinstance(value, UntypedAtomic):
            return cls.fromstring(value.value)
        elif isinstance(value, (Date10, DateTime10)):
            return cls(value.year, value.month, value.tzinfo)
        return cls.fromstring(value)  # type: ignore[arg-type]
    except OverflowError as err:
        raise self.error('FODT0001', err) from None
    except ValueError as err:
        raise self.error('FORG0001', err)


@constructor('time')
def cast_time_type(self: XPathConstructor, value: AtomicType) -> Time:
    if isinstance(value, Time):
        return value

    try:
        if isinstance(value, UntypedAtomic):
            return Time.fromstring(value.value)
        elif isinstance(value, DateTime10):
            return Time(value.hour, value.minute, value.second,
                        value.microsecond, value.tzinfo)
        return Time.fromstring(value)  # type: ignore[arg-type]
    except ValueError as err:
        raise self.error('FORG0001', err)


@method('date')
@method('gDay')
@method('gMonth')
@method('gMonthDay')
@method('gYear')
@method('gYearMonth')
@method('time')
def evaluate_other_datetime_types(self: XPathConstructor, context: ContextType = None) \
        -> Emptiable[OtherDateTimeTypes]:
    if self.context is not None:
        context = self.context

    arg = self.data_value(self.get_argument(context))
    if arg is None:
        return []

    try:
        return cast(OtherDateTimeTypes, self.cast(arg))
    except (TypeError, OverflowError) as err:
        if isinstance(context, XPathSchemaContext):
            return []
        elif isinstance(err, TypeError):
            raise self.error('FORG0006', err) from None
        else:
            raise self.error('FODT0001', err) from None


###
# Constructors for time durations XSD types
@constructor('duration')
def cast_duration_type(self: XPathConstructor, value: AtomicType) -> Duration:
    if isinstance(value, Duration):
        return value

    try:
        if isinstance(value, UntypedAtomic):
            return Duration.fromstring(value.value)
        return Duration.fromstring(value)  # type: ignore[arg-type]
    except OverflowError as err:
        raise self.error('FODT0002', err) from None
    except ValueError as err:
        raise self.error('FORG0001', err)


@constructor('yearMonthDuration')
def cast_year_month_duration_type(self: XPathConstructor, value: AtomicType) \
        -> YearMonthDuration:
    if isinstance(value, YearMonthDuration):
        return value
    elif isinstance(value, Duration):
        return YearMonthDuration(months=value.months)

    try:
        if isinstance(value, UntypedAtomic):
            return YearMonthDuration.fromstring(value.value)
        return YearMonthDuration.fromstring(value)  # type: ignore[arg-type]
    except OverflowError as err:
        raise self.error('FODT0002', err) from None
    except ValueError as err:
        raise self.error('FORG0001', err)


@constructor('dayTimeDuration')
def cast_day_time_duration_type(self: XPathConstructor, value: AtomicType) \
        -> DayTimeDuration:
    if isinstance(value, DayTimeDuration):
        return value
    elif isinstance(value, Duration):
        return DayTimeDuration(seconds=value.seconds)

    try:
        if isinstance(value, UntypedAtomic):
            return DayTimeDuration.fromstring(value.value)
        return DayTimeDuration.fromstring(value)  # type: ignore[arg-type]
    except OverflowError as err:
        raise self.error('FODT0002', err) from None
    except ValueError as err:
        raise self.error('FORG0001', err) from None


@constructor('dateTimeStamp')
def cast_datetime_stamp_type(self: XPathConstructor, value: AtomicType) \
        -> DateTimeStamp:
    if isinstance(value, DateTimeStamp):
        return value
    elif isinstance(value, DateTime10):
        value = str(value)

    try:
        if isinstance(value, UntypedAtomic):
            return DateTimeStamp.fromstring(value.value)
        elif isinstance(value, Date):
            return DateTimeStamp(value.year, value.month, value.day, tzinfo=value.tzinfo)
        return DateTimeStamp.fromstring(value)  # type: ignore[arg-type]
    except ValueError as err:
        raise self.error('FORG0001', err) from None


@method('dateTimeStamp')
def evaluate_datetime_stamp_type(self: XPathConstructor, context: ContextType = None) \
        -> Emptiable[DateTimeStamp]:
    if self.context is not None:
        context = self.context

    arg = self.data_value(self.get_argument(context))
    if arg is None:
        return []

    if isinstance(arg, UntypedAtomic):
        result = self.cast(arg.value)
    elif isinstance(arg, Date):
        result = self.cast(arg)
    else:
        result = self.cast(str(arg))
    assert isinstance(result, DateTimeStamp)
    return result


@method('dateTimeStamp')
def nud_datetime_stamp_type(self: XPathConstructor) -> XPathConstructor:
    if self.parser.xsd_version == '1.0':
        raise self.wrong_syntax("xs:dateTimeStamp is not recognized unless XSD 1.1 is enabled")
    if not self.parser.parse_arguments:
        return self

    try:
        self.parser.advance('(')
        self[0:] = self.parser.expression(5),
        if self.parser.next_token.symbol == ',':
            msg = 'Too many arguments: expected at most 1 argument'
            raise self.error('XPST0017', msg)
        self.parser.advance(')')
    except SyntaxError as err:
        raise self.error('XPST0017', str(err)) from None
    return self


###
# Constructors for binary XSD types
@constructor('base64Binary')
def cast_base64_binary_type(self: XPathConstructor, value: AtomicType) -> Base64Binary:
    try:
        return Base64Binary(value, ordered=self.parser.version >= '3.1')  # type: ignore[arg-type]
    except ValueError as err:
        raise self.error('FORG0001', err) from None
    except TypeError as err:
        raise self.error('XPTY0004', err) from None


@constructor('hexBinary')
def cast_hex_binary_type(self: XPathConstructor, value: AtomicType) -> HexBinary:
    try:
        return HexBinary(value, ordered=self.parser.version >= '3.1')  # type: ignore[arg-type]
    except ValueError as err:
        raise self.error('FORG0001', err) from None
    except TypeError as err:
        raise self.error('XPTY0004', err) from None


@method('base64Binary')
@method('hexBinary')
def evaluate_binary_types(self: XPathConstructor, context: ContextType = None) \
        -> Emptiable[Union[HexBinary, Base64Binary]]:
    arg = self.data_value(self.get_argument(self.context or context))
    if arg is None:
        return []

    try:
        return cast(Union[HexBinary, Base64Binary], self.cast(arg))
    except ElementPathError as err:
        if isinstance(context, XPathSchemaContext):
            return []
        err.token = self
        raise


@constructor('NOTATION')
def cast_notation_type(self: XPathConstructor, value: AtomicType) -> Notation:
    raise NotImplementedError("No value is castable to xs:NOTATION")


@method('NOTATION')
def nud_notation_type(self: XPathConstructor) -> None:
    if not self.parser.parse_arguments:
        return

    self.parser.advance('(')
    if self.parser.next_token.symbol == ')':
        raise self.error('XPST0017', 'expected exactly one argument')
    self[0:] = self.parser.expression(5),
    if self.parser.next_token.symbol != ')':
        raise self.error('XPST0017', 'expected exactly one argument')
    self.parser.advance()
    raise self.error('XPST0017', "no constructor function exists for xs:NOTATION")


###
# Multirole tokens (function or constructor function)
#

# Case 1: In XPath 2.0 the 'boolean' keyword is used both for boolean() function and
# for boolean() constructor function.
unregister('boolean')


@constructor('boolean', label=('function', 'constructor function'),
             sequence_types=('item()*', 'xs:boolean'))
def cast_boolean_type(self: XPathConstructor, value: AtomicType) -> bool:
    try:
        return cast(bool, BooleanProxy(value))
    except ValueError as err:
        raise self.error('FORG0001', err) from None
    except TypeError as err:
        raise self.error('XPTY0004', err) from None


@method('boolean')
def nud_boolean_type_and_function(self: XPathConstructor) -> XPathConstructor:
    if not self.parser.parse_arguments:
        return self

    self.parser.advance('(')
    if self.parser.next_token.symbol == ')':
        msg = 'Too few arguments: expected at least 1 argument'
        raise self.error('XPST0017', msg)
    self[0:] = self.parser.expression(5),
    if self.parser.next_token.symbol == ',':
        msg = 'Too many arguments: expected at most 1 argument'
        raise self.error('XPST0017', msg)
    self.parser.advance(')')
    return self


@method('boolean')
def evaluate_boolean_type_and_function(self: XPathConstructor, context: ContextType = None) \
        -> Emptiable[bool]:
    if self.context is not None:
        context = self.context

    if self.label == 'function':
        return self.boolean_value(self[0].select(context))

    # xs:boolean constructor
    arg = self.data_value(self.get_argument(context))
    if arg is None:
        return []

    try:
        return cast(bool, self.cast(arg))
    except ElementPathError as err:
        if isinstance(context, XPathSchemaContext):
            return []
        err.token = self
        raise


###
# Case 2: In XPath 2.0 the 'string' keyword is used both for fn:string() and xs:string().
unregister('string')


@constructor('string', label=('function', 'constructor function'),
             nargs=(0, 1), sequence_types=('item()?', 'xs:string'))
def cast_string_type(self: XPathConstructor, value: AtomicType) -> str:
    return self.string_value(value)


@method('string')
def nud_string_type_and_function(self: XPathConstructor) -> XPathConstructor:
    if not self.parser.parse_arguments:
        return self

    try:
        self.parser.advance('(')
        if self.label != 'function' or self.parser.next_token.symbol != ')':
            self[0:] = self.parser.expression(5),
        self.parser.advance(')')
    except ElementPathSyntaxError as err:
        raise self.error('XPST0017', err)
    else:
        return self


@method('string')
def evaluate_string_type_and_function(self: XPathConstructor, context: ContextType = None) \
        -> Emptiable[str]:
    if self.context is not None:
        context = self.context

    if self.label == 'function':
        if not self:
            if context is None:
                raise self.missing_context()
            return self.string_value(context.item)
        return self.string_value(self.get_argument(context))
    else:
        item = self.get_argument(context)
        return [] if item is None else self.string_value(item)


# Case 3 and 4: In XPath 2.0 the XSD 'QName' and 'dateTime' types have special
# constructor functions so the 'QName' keyword is used both for fn:QName() and
# xs:QName(), the same for 'dateTime' keyword.
#
# In those cases the label at parse time is set by the nud method, in dependence
# of the number of args.
#
@constructor('QName', bp=90, label=('function', 'constructor function'),
             nargs=(1, 2), sequence_types=('xs:string?', 'xs:string', 'xs:QName'))
def cast_qname_type(self: XPathConstructor, value: AtomicType) -> QName:
    if isinstance(value, QName):
        return value
    elif isinstance(value, UntypedAtomic) and self.parser.version >= '3.0':
        return self.cast_to_qname(value.value)
    elif isinstance(value, str):
        return self.cast_to_qname(value)
    else:
        raise self.error('XPTY0004', 'the argument has an invalid type %r' % type(value))


@constructor('dateTime', bp=90, label=('function', 'constructor function'),
             nargs=(1, 2), sequence_types=('xs:date?', 'xs:time?', 'xs:dateTime?'))
def cast_datetime_type(self: XPathConstructor, value: AtomicType) \
        -> Optional[DateTime10]:
    cls = DateTime if self.parser.xsd_version == '1.1' else DateTime10
    if isinstance(value, cls):
        return value

    try:
        if isinstance(value, UntypedAtomic):
            result = cls.fromstring(value.value)
        elif isinstance(value, Date10):
            result = cls(value.year, value.month, value.day, tzinfo=value.tzinfo)
        else:
            result = cls.fromstring(value)  # type: ignore[arg-type]
    except OverflowError as err:
        raise self.error('FODT0001', err) from None
    except ValueError as err:
        raise self.error('FORG0001', err) from None
    else:
        return result


@method('QName')
@method('dateTime')
def nud_qname_and_datetime(self: XPathConstructor) -> XPathConstructor:
    if not self.parser.parse_arguments:
        return self

    try:
        self.parser.advance('(')
        self[0:] = self.parser.expression(5),
        if self.parser.next_token.symbol == ',':
            if self.label != 'function':
                raise self.error('XPST0017', 'unexpected 2nd argument')
            self.label = 'function'
            self.parser.advance(',')
            self[1:] = self.parser.expression(5),
        elif self.label != 'constructor function' or self.namespace != XSD_NAMESPACE:
            raise self.error('XPST0017', '2nd argument missing')
        else:
            self.label = 'constructor function'
            self.nargs = 1
        self.parser.advance(')')
    except SyntaxError:
        raise self.error('XPST0017') from None
    else:
        return self


@method('QName')
def evaluate_qname_type_and_function(self: XPathConstructor, context: ContextType = None) \
        -> Emptiable[QName]:
    if self.context is not None:
        context = self.context

    if self.label == 'constructor function':
        arg = self.data_value(self.get_argument(context))
        if arg is None:
            return []
        value = self.cast(arg)
        assert isinstance(value, QName)
        return value
    else:
        uri = self.get_argument(context)
        qname = self.get_argument(context, index=1)
        try:
            return QName(uri, qname)
        except (TypeError, ValueError) as err:
            if isinstance(context, XPathSchemaContext):
                return []
            elif isinstance(err, TypeError):
                raise self.error('XPTY0004', err)
            else:
                raise self.error('FOCA0002', err)


@method('dateTime')
def evaluate_datetime_type_and_function(self: XPathConstructor, context: ContextType = None) \
        -> Emptiable[DateTime10]:
    if self.context is not None:
        context = self.context

    if self.label == 'constructor function':
        arg = self.data_value(self.get_argument(context))
        if arg is None:
            return []

        try:
            result = self.cast(arg)
        except (ValueError, TypeError) as err:
            if isinstance(context, XPathSchemaContext):
                return []
            elif isinstance(err, ValueError):
                raise self.error('FORG0001', err) from None
            else:
                raise self.error('FORG0006', err) from None
        else:
            assert isinstance(result, DateTime10)
            return result
    else:
        dt = self.get_argument(context, cls=Date10)
        tm = self.get_argument(context, 1, cls=Time)
        if dt is None or tm is None:
            return []
        elif dt.tzinfo == tm.tzinfo or tm.tzinfo is None:
            tzinfo = dt.tzinfo
        elif dt.tzinfo is None:
            tzinfo = tm.tzinfo
        else:
            raise self.error('FORG0008')

        if self.parser.xsd_version == '1.1':
            return DateTime(dt.year, dt.month, dt.day, tm.hour, tm.minute,
                            tm.second, tm.microsecond, tzinfo)
        return DateTime10(dt.year, dt.month, dt.day, tm.hour, tm.minute,
                          tm.second, tm.microsecond, tzinfo)


@constructor('untypedAtomic')
def cast_untyped_atomic(self: XPathConstructor, value: AtomicType) -> UntypedAtomic:
    return UntypedAtomic(value)


@method('untypedAtomic')
def evaluate_untyped_atomic(self: XPathConstructor, context: ContextType = None) \
        -> Emptiable[UntypedAtomic]:
    arg = self.data_value(self.get_argument(self.context or context))
    if arg is None:
        return []
    elif isinstance(arg, UntypedAtomic):
        return arg
    else:
        arg = self.cast(arg)
        assert isinstance(arg, UntypedAtomic)
        return arg
