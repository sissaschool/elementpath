#
# Copyright (c), 2018-2020, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""
XPath 2.0 implementation - part 3 (XSD constructors and multi-role tokens)
"""
from ..exceptions import ElementPathError, ElementPathSyntaxError
from ..namespaces import XSD_NAMESPACE
from ..datatypes import xsd10_atomic_types, xsd11_atomic_types, GregorianDay, \
    GregorianMonth, GregorianMonthDay, GregorianYear10, GregorianYear, \
    GregorianYearMonth10, GregorianYearMonth, Duration, DayTimeDuration, \
    YearMonthDuration, Date10, Date, DateTime10, DateTime, DateTimeStamp, \
    Time, UntypedAtomic, QName, HexBinary, Base64Binary, BooleanProxy, ATOMIC_VALUES
from ..xpath_token import XPathToken
from ..xpath_context import XPathSchemaContext
from .xpath2_functions import XPath2Parser


register = XPath2Parser.register
unregister = XPath2Parser.unregister
method = XPath2Parser.method
constructor = XPath2Parser.constructor


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
def cast(self, value):
    try:
        return xsd10_atomic_types[self.symbol](value)
    except ValueError as err:
        raise self.error('FORG0001', str(err))


###
# Constructors for numeric XSD types
@constructor('decimal')
@constructor('double')
@constructor('float')
def cast(self, value):
    try:
        if self.parser.xsd_version == '1.0':
            return xsd10_atomic_types[self.symbol](value)
        return xsd11_atomic_types[self.symbol](value)
    except ValueError as err:
        if isinstance(value, (str, UntypedAtomic)):
            raise self.error('FORG0001', str(err))
        raise self.error('FOCA0002', str(err))


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
def cast(self, value):
    try:
        return xsd10_atomic_types[self.symbol](value)
    except ValueError:
        msg = 'could not convert {!r} to xs:{}'.format(value, self.symbol)
        if isinstance(value, (str, bytes, UntypedAtomic, bool)):
            raise self.error('FORG0001', msg) from None
        raise self.error('FOCA0002', msg) from None
    except OverflowError as err:
        if isinstance(value, (str, bytes, UntypedAtomic)):
            raise self.error('FORG0001', str(err)) from None
        raise self.error('FOCA0002', str(err)) from None


###
# Constructors for datetime XSD types
@constructor('date')
def cast(self, value):
    cls = Date if self.parser.xsd_version == '1.1' else Date10
    if isinstance(value, cls):
        return value

    try:
        if isinstance(value, UntypedAtomic):
            return cls.fromstring(value.value)
        elif isinstance(value, DateTime10):
            return cls(value.year, value.month, value.day, value.tzinfo)
        return cls.fromstring(value)
    except OverflowError as err:
        raise self.error('FODT0001', str(err)) from None
    except ValueError as err:
        raise self.error('FORG0001', str(err))


@constructor('gDay')
def cast(self, value):
    if isinstance(value, GregorianDay):
        return value

    try:
        if isinstance(value, UntypedAtomic):
            return GregorianDay.fromstring(value.value)
        elif isinstance(value, (Date10, DateTime10)):
            return GregorianDay(value.day, value.tzinfo)
        return GregorianDay.fromstring(value)
    except ValueError as err:
        raise self.error('FORG0001', str(err))


@constructor('gMonth')
def cast(self, value):
    if isinstance(value, GregorianMonth):
        return value

    try:
        if isinstance(value, UntypedAtomic):
            return GregorianMonth.fromstring(value.value)
        elif isinstance(value, (Date10, DateTime10)):
            return GregorianMonth(value.month, value.tzinfo)
        return GregorianMonth.fromstring(value)
    except ValueError as err:
        raise self.error('FORG0001', str(err))


@constructor('gMonthDay')
def cast(self, value):
    if isinstance(value, GregorianMonthDay):
        return value

    try:
        if isinstance(value, UntypedAtomic):
            return GregorianMonthDay.fromstring(value.value)
        elif isinstance(value, (Date10, DateTime10)):
            return GregorianMonthDay(value.month, value.day, value.tzinfo)
        return GregorianMonthDay.fromstring(value)
    except ValueError as err:
        raise self.error('FORG0001', str(err))


@constructor('gYear')
def cast(self, value):
    cls = GregorianYear if self.parser.xsd_version == '1.1' else GregorianYear10
    if isinstance(value, cls):
        return value

    try:
        if isinstance(value, UntypedAtomic):
            return cls.fromstring(value.value)
        elif isinstance(value, (Date10, DateTime10)):
            return cls(value.year, value.tzinfo)
        return cls.fromstring(value)
    except OverflowError as err:
        raise self.error('FODT0001', str(err)) from None
    except ValueError as err:
        raise self.error('FORG0001', str(err))


@constructor('gYearMonth')
def cast(self, value):
    cls = GregorianYearMonth \
        if self.parser.xsd_version == '1.1' else GregorianYearMonth10
    if isinstance(value, cls):
        return value

    try:
        if isinstance(value, UntypedAtomic):
            return cls.fromstring(value.value)
        elif isinstance(value, (Date10, DateTime10)):
            return cls(value.year, value.month, value.tzinfo)
        return cls.fromstring(value)
    except OverflowError as err:
        raise self.error('FODT0001', str(err)) from None
    except ValueError as err:
        raise self.error('FORG0001', str(err))


@constructor('time')
def cast(self, value):
    if isinstance(value, Time):
        return value

    try:
        if isinstance(value, UntypedAtomic):
            return Time.fromstring(value.value)
        elif isinstance(value, DateTime10):
            return Time(value.hour, value.minute, value.second,
                        value.microsecond, value.tzinfo)
        return Time.fromstring(value)
    except ValueError as err:
        raise self.error('FORG0001', str(err))


@method('date')
@method('gDay')
@method('gMonth')
@method('gMonthDay')
@method('gYear')
@method('gYearMonth')
@method('time')
def evaluate(self, context=None):
    arg = self.data_value(self.get_argument(context))
    if arg is None:
        return []

    try:
        return self.cast(arg)
    except ValueError as err:
        raise self.error('FORG0001', str(err)) from None
    except TypeError as err:
        raise self.error('FORG0006', str(err)) from None
    except OverflowError as err:
        raise self.error('FODT0001', str(err)) from None


###
# Constructors for time durations XSD types
@constructor('duration')
def cast(self, value):
    if isinstance(value, Duration):
        return value

    try:
        if isinstance(value, UntypedAtomic):
            return Duration.fromstring(value.value)
        return Duration.fromstring(value)
    except OverflowError as err:
        raise self.error('FODT0002', str(err)) from None
    except ValueError as err:
        raise self.error('FORG0001', str(err))


@constructor('yearMonthDuration')
def cast(self, value):
    if isinstance(value, YearMonthDuration):
        return value
    elif isinstance(value, Duration):
        return YearMonthDuration(months=value.months)

    try:
        if isinstance(value, UntypedAtomic):
            return YearMonthDuration.fromstring(value.value)
        return YearMonthDuration.fromstring(value)
    except OverflowError as err:
        raise self.error('FODT0002', str(err)) from None
    except ValueError as err:
        raise self.error('FORG0001', str(err))


@constructor('dayTimeDuration')
def cast(self, value):
    if isinstance(value, DayTimeDuration):
        return value
    elif isinstance(value, Duration):
        return DayTimeDuration(seconds=value.seconds)

    try:
        if isinstance(value, UntypedAtomic):
            return DayTimeDuration.fromstring(value.value)
        return DayTimeDuration.fromstring(value)
    except OverflowError as err:
        raise self.error('FODT0002', str(err)) from None
    except ValueError as err:
        raise self.error('FORG0001', str(err))


@constructor('dateTimeStamp')
def cast(self, value):
    if isinstance(value, DateTimeStamp):
        return value
    elif isinstance(value, DateTime10):
        value = str(value)

    try:
        return DateTimeStamp.fromstring(value)
    except ValueError as err:
        raise self.error('FORG0001', str(err))


@method('dateTimeStamp')
def evaluate(self, context=None):
    arg = self.data_value(self.get_argument(context))
    if arg is None:
        return []

    try:
        if isinstance(arg, UntypedAtomic):
            return self.cast(arg.value)
        return self.cast(str(arg))
    except ValueError as err:
        raise self.error('FOCA0002', str(err)) from None
    except TypeError as err:
        raise self.error('FORG0006', str(err)) from None


###
# Constructors for binary XSD types
@constructor('base64Binary')
def cast(self, value):
    try:
        return Base64Binary(value)
    except ValueError as err:
        raise self.error('FORG0001', str(err)) from None
    except TypeError as err:
        if isinstance(value, str):
            raise self.error('FORG0006', str(err)) from None
        raise self.error('XPTY0004', str(err)) from None


@constructor('hexBinary')
def cast(self, value):
    try:
        return HexBinary(value)
    except ValueError as err:
        raise self.error('FORG0001', str(err)) from None
    except TypeError as err:
        if isinstance(value, str):
            raise self.error('FORG0006', str(err)) from None
        raise self.error('XPTY0004', str(err)) from None


@method('base64Binary')
@method('hexBinary')
def evaluate(self, context=None):
    arg = self.data_value(self.get_argument(context))
    if arg is None:
        return []

    try:
        return self.cast(arg)
    except ElementPathError as err:
        err.token = self
        raise
    except UnicodeEncodeError as err:
        raise self.error('FORG0001', str(err)) from None


@constructor('NOTATION')
def cast(self, value):
    return value


@method('NOTATION')
def nud(self):
    self.parser.advance('(')
    if self.parser.next_token.symbol == ')':
        raise self.error('XPST0017', 'expected exactly one argument')
    self[0:] = self.parser.expression(5),
    if self.parser.next_token.symbol != ')':
        raise self.error('XPST0017', 'expected exactly one argument')
    self.parser.advance()
    self.value = None
    raise self.error('XPST0017', "no constructor function exists for xs:NOTATION")


###
# Multi role-tokens constructors (function or constructor)
#

# Case 1: In XPath 2.0 the 'boolean' keyword is used both for boolean() function and
# for boolean() constructor.
unregister('boolean')


@constructor('boolean', bp=90, label=('function', 'constructor'))
def cast(self, value):
    try:
        return BooleanProxy(value)
    except ValueError as err:
        raise self.error('FORG0001', str(err)) from None
    except TypeError as err:
        if isinstance(value, str):
            raise self.error('FORG0006', str(err)) from None
        raise self.error('XPTY0004', str(err)) from None


@method('boolean')
def nud(self):
    self.parser.advance('(')
    if self.parser.next_token.symbol == ')':
        raise self.wrong_nargs('Too few arguments: expected at least 1 argument')
    self[0:] = self.parser.expression(5),
    if self.parser.next_token.symbol == ',':
        raise self.wrong_nargs('Too many arguments: expected at most 1 argument')
    self.parser.advance(')')
    self.value = None
    return self


@method('boolean')
def evaluate(self, context=None):
    if self.label == 'function':
        return self.boolean_value([x for x in self[0].select(context)])

    # xs:boolean constructor
    arg = self.data_value(self.get_argument(context))
    if arg is None:
        return []

    try:
        return self.cast(arg)
    except ElementPathError as err:
        err.token = self
        raise


###
# Case 2: In XPath 2.0 the 'string' keyword is used both for fn:string() and xs:string().
unregister('string')
register('string', lbp=90, rbp=90, label=('function', 'constructor'),  # pragma: no cover
         pattern=r'\bstring(?=\s*\(|\s*\(\:.*\:\)\()', cast=XPathToken.string_value)


@method('string')
def nud(self):
    try:
        self.parser.advance('(')
        if self.label != 'function' or self.parser.next_token.symbol != ')':
            self[0:] = self.parser.expression(5),
        self.parser.advance(')')
    except ElementPathSyntaxError as err:
        err.code = self.error_code('XPST0017')
        raise

    self.value = None
    return self


@method('string')
def evaluate(self, context=None):
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
@constructor('QName', bp=90, label=('function', 'constructor'))
def cast(self, value):
    if isinstance(value, QName):
        return value
    elif isinstance(value, UntypedAtomic):
        return self.cast_to_qname(value.value)
    elif isinstance(value, str):
        return self.cast_to_qname(value)
    else:
        raise self.error('XPTY0004', 'the argument has an invalid type %r' % type(value))


@constructor('dateTime', bp=90, label=('function', 'constructor'))
def cast(self, value):
    cls = DateTime if self.parser.xsd_version == '1.1' else DateTime10
    if isinstance(value, cls):
        return value

    try:
        if isinstance(value, UntypedAtomic):
            return cls.fromstring(value.value)
        elif isinstance(value, Date10):
            return cls(value.year, value.month, value.day, tzinfo=value.tzinfo)
        return cls.fromstring(value)
    except OverflowError as err:
        raise self.error('FODT0001', str(err)) from None
    except ValueError as err:
        raise self.error('FORG0001', str(err)) from None


@method('QName')
@method('dateTime')
def nud(self):
    try:
        self.parser.advance('(')
        self[0:] = self.parser.expression(5),
        if self.parser.next_token.symbol == ',':
            if self.label != 'function':
                raise self.error('XPST0017', 'unexpected 2nd argument')
            self.label = 'function'
            self.parser.advance(',')
            self[1:] = self.parser.expression(5),
        elif self.label != 'constructor' or self.namespace != XSD_NAMESPACE:
            raise self.error('XPST0017', '2nd argument missing')
        else:
            self.label = 'constructor'
        self.parser.advance(')')
    except SyntaxError:
        raise self.error('XPST0017') from None
    self.value = None
    return self


@method('QName')
def evaluate(self, context=None):
    if self.label == 'constructor':
        arg = self.data_value(self.get_argument(context))
        return [] if arg is None else self.cast(arg)
    else:
        uri = self.get_argument(context)
        qname = self.get_argument(context, index=1)
        try:
            return QName(uri, qname)
        except TypeError as err:
            raise self.error('XPTY0004', str(err))
        except ValueError as err:
            if isinstance(context, XPathSchemaContext):
                return ATOMIC_VALUES['QName']
            raise self.error('FOCA0002', str(err))


@method('dateTime')
def evaluate(self, context=None):
    if self.label == 'constructor':
        arg = self.data_value(self.get_argument(context))
        if arg is None:
            return []

        try:
            return self.cast(arg)
        except ValueError as err:
            raise self.error('FORG0001', str(err)) from None
        except TypeError as err:
            raise self.error('FORG0006', str(err)) from None
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
def cast(self, value):
    return UntypedAtomic(value)


@method('untypedAtomic')
def evaluate(self, context=None):
    arg = self.data_value(self.get_argument(context))
    if arg is None:
        return []
    elif isinstance(arg, UntypedAtomic):
        return arg
    else:
        return self.cast(arg)


XPath2Parser.build()  # XPath 2.0 definition complete, can build the parser class.