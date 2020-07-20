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
from decimal import Decimal
from urllib.parse import urlparse

from .exceptions import ElementPathError, ElementPathSyntaxError
from .namespaces import XQT_ERRORS_NAMESPACE
from .datatypes import DateTime10, DateTime, Date10, Date, Time, \
    XPathGregorianDay, XPathGregorianMonth, XPathGregorianMonthDay, \
    XPathGregorianYear, XPathGregorianYearMonth, UntypedAtomic, Duration, \
    YearMonthDuration, DayTimeDuration, Base64Binary, HexBinary, Double, AnyURI, \
    QName, WHITESPACES_PATTERN, NMTOKEN_PATTERN, NAME_PATTERN, NCNAME_PATTERN, \
    LANGUAGE_CODE_PATTERN, WRONG_ESCAPE_PATTERN, XSD_BUILTIN_TYPES
from .xpath_token import XPathToken
from .xpath_context import XPathContext
from .xpath2_functions import XPath2Parser


def collapse_white_spaces(s):
    return WHITESPACES_PATTERN.sub(' ', s).strip()


register = XPath2Parser.register
unregister = XPath2Parser.unregister
method = XPath2Parser.method
constructor = XPath2Parser.constructor


###
# Constructors for string-based XSD types
@constructor('normalizedString')
def cast(self, value):
    return str(value).replace('\t', ' ').replace('\n', ' ')


@constructor('token')
def cast(self, value):
    return collapse_white_spaces(value)


@constructor('language')
def cast(self, value):
    if value is True:
        return 'true'
    elif value is False:
        return 'false'

    match = LANGUAGE_CODE_PATTERN.match(collapse_white_spaces(value))
    if match is None:
        raise self.error('FORG0001', "%r is not a language code" % value)
    return match.group()


@constructor('NMTOKEN')
def cast(self, value):
    match = NMTOKEN_PATTERN.match(collapse_white_spaces(value))
    if match is None:
        raise self.error('FORG0001', "%r is not an xs:NMTOKEN value" % value)
    return match.group()


@constructor('Name')
def cast(self, value):
    match = NAME_PATTERN.match(collapse_white_spaces(value))
    if match is None:
        raise self.error('FORG0001', "%r is not an xs:Name value" % value)
    return match.group()


@constructor('NCName')
@constructor('ID')
@constructor('IDREF')
@constructor('ENTITY')
def cast(self, value):
    match = NCNAME_PATTERN.match(collapse_white_spaces(value))
    if match is None:
        raise self.error('FORG0001', "invalid value %r for constructor" % value)
    return match.group()


@constructor('anyURI')
def cast(self, value):
    if isinstance(value, UntypedAtomic):
        value = value.value

    uri = collapse_white_spaces(value)
    try:
        url_parts = urlparse(uri)
        _ = url_parts.port
    except ValueError as err:
        msg = "%r is not an xs:anyURI value (%s)"
        raise self.error('FORG0001', msg % (value, str(err)))

    if uri.count('#') > 1:
        msg = "%r is not an xs:anyURI value (too many # characters)"
        raise self.error('FORG0001', msg % value)
    elif WRONG_ESCAPE_PATTERN.search(uri):
        msg = "%r is not an xs:anyURI value (wrong escaping)"
        raise self.error('FORG0001', msg % value)
    return uri


###
# Constructors for numeric XSD types
@constructor('decimal')
def cast(self, value):
    return self.cast_to_number(value, Decimal)


@constructor('double')
def cast(self, value):
    return self.cast_to_number(value, float)


@constructor('float')
def cast(self, value):
    return self.cast_to_number(value, float)


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
    boundaries = {
        'integer': (None, None),
        'nonNegativeInteger': (0, None),
        'positiveInteger': (1, None),
        'nonPositiveInteger': (None, 1),
        'negativeInteger': (None, 0),
        'long': (-2**127, 2**127),
        'int': (-2**63, 2**63),
        'short': (-2**15, 2**15),
        'byte': (-2**7, 2**7),
        'unsignedLong': (0, 2**128),
        'unsignedInt': (0, 2**64),
        'unsignedShort': (0, 2**16),
        'unsignedByte': (0, 2**8),
    }
    lower_bound, higher_bound = boundaries[self.symbol]

    if isinstance(value, (str, bytes, UntypedAtomic)):
        try:
            result = int(self.cast_to_number(value, Decimal))
        except ValueError:
            raise self.error('FORG0001', 'could not convert %r to integer' % value) from None
        except OverflowError as err:
            raise self.error('FORG0001', str(err)) from None
    else:
        try:
            result = int(value)
        except ValueError as err:
            raise self.error('FOCA0002', str(err)) from None
        except OverflowError as err:
            raise self.error('FOCA0002', str(err)) from None

    if lower_bound is not None and result < lower_bound:
        raise self.error('FORG0001', "value %d is too low" % result)
    elif higher_bound is not None and result >= higher_bound:
        raise self.error('FORG0001', "value %d is too high" % result)
    return result


###
# Constructors for datetime XSD types
@constructor('date')
def cast(self, value):
    try:
        cls = Date if self.parser.schema.xsd_version == '1.1' else Date10
    except (AttributeError, NotImplementedError):
        cls = Date10

    if isinstance(value, cls):
        return value
    elif isinstance(value, UntypedAtomic):
        return cls.fromstring(value.value)
    elif isinstance(value, DateTime10):
        return cls(value.year, value.month, value.day, value.tzinfo)
    return cls.fromstring(value)


@constructor('gDay')
def cast(self, value):
    if isinstance(value, XPathGregorianDay):
        return value
    elif isinstance(value, UntypedAtomic):
        return XPathGregorianDay.fromstring(value.value)
    elif isinstance(value, (Date10, DateTime10)):
        return XPathGregorianDay(value.day, value.tzinfo)
    return XPathGregorianDay.fromstring(value)


@constructor('gMonth')
def cast(self, value):
    if isinstance(value, XPathGregorianMonth):
        return value
    elif isinstance(value, UntypedAtomic):
        return XPathGregorianMonth.fromstring(value.value)
    elif isinstance(value, (Date10, DateTime10)):
        return XPathGregorianMonth(value.month, value.tzinfo)
    return XPathGregorianMonth.fromstring(value)


@constructor('gMonthDay')
def cast(self, value):
    if isinstance(value, XPathGregorianMonthDay):
        return value
    elif isinstance(value, UntypedAtomic):
        return XPathGregorianMonthDay.fromstring(value.value)
    elif isinstance(value, (Date10, DateTime10)):
        return XPathGregorianMonthDay(value.month, value.day, value.tzinfo)
    return XPathGregorianMonthDay.fromstring(value)


@constructor('gYear')
def cast(self, value):
    if isinstance(value, XPathGregorianYear):
        return value
    elif isinstance(value, UntypedAtomic):
        return XPathGregorianYear.fromstring(value.value)
    elif isinstance(value, (Date10, DateTime10)):
        return XPathGregorianYear(value.year, value.tzinfo)
    return XPathGregorianYear.fromstring(value)


@constructor('gYearMonth')
def cast(self, value):
    if isinstance(value, XPathGregorianYearMonth):
        return value
    elif isinstance(value, UntypedAtomic):
        return XPathGregorianYearMonth.fromstring(value.value)
    elif isinstance(value, (Date10, DateTime10)):
        return XPathGregorianYearMonth(value.year, value.month, value.tzinfo)
    return XPathGregorianYearMonth.fromstring(value)


@constructor('time')
def cast(self, value):
    if isinstance(value, Time):
        return value
    elif isinstance(value, UntypedAtomic):
        return Time.fromstring(value.value)
    elif isinstance(value, DateTime10):
        return Time(value.hour, value.minute, value.second, value.microsecond, value.tzinfo)
    return Time.fromstring(value)


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


###
# Constructors for time durations XSD types
@constructor('duration')
def cast(self, value):
    if isinstance(value, Duration):
        return value
    elif isinstance(value, UntypedAtomic):
        return Duration.fromstring(value.value)
    return Duration.fromstring(value)


@constructor('yearMonthDuration')
def cast(self, value):
    if isinstance(value, YearMonthDuration):
        return value
    elif isinstance(value, UntypedAtomic):
        return YearMonthDuration.fromstring(value.value)
    elif isinstance(value, Duration):
        return YearMonthDuration(months=value.months)
    return YearMonthDuration.fromstring(value)


@constructor('dayTimeDuration')
def cast(self, value):
    if isinstance(value, DayTimeDuration):
        return value
    elif isinstance(value, UntypedAtomic):
        return DayTimeDuration.fromstring(value.value)
    elif isinstance(value, Duration):
        return DayTimeDuration(seconds=value.seconds)
    return DayTimeDuration.fromstring(value)


@constructor('dateTimeStamp')
def cast(self, value):
    if not XSD_BUILTIN_TYPES['dateTimeStamp'].validator(value):
        raise ValueError("{} is not castable to an xs:dateTimeStamp".format(value))
    return value


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
        raise self.error('FORG0006', str(err)) from None


@constructor('hexBinary')
def cast(self, value):
    try:
        return HexBinary(value)
    except ValueError as err:
        raise self.error('FORG0001', str(err)) from None
    except TypeError as err:
        raise self.error('FORG0006', str(err)) from None


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
    self[0:] = self.parser.expression(5),
    if self.parser.next_token.symbol == ',':
        raise self.error('XPST0017', 'too many arguments: expected at most 1 argument')
    self.parser.advance(')')
    self.value = None
    raise self.error('XPST0017', "no constructor function exists for xs:NOTATION")


###
# Multi role-tokens constructors (function or constructor)
#

# Case 1: In XPath 2.0 the 'boolean' keyword is used both for boolean() function and
# for boolean() constructor.
unregister('boolean')


@constructor('boolean', bp=90, label=('function', 'constructor'))
def cast(self, value, context=None):
    assert context is None or isinstance(context, XPathContext)
    if isinstance(value, bool):
        return value
    elif isinstance(value, (int, float, Decimal)):
        return bool(value)
    elif isinstance(value, UntypedAtomic):
        value = value.value
    elif not isinstance(value, str):
        raise self.error('FORG0006', 'the argument has an invalid type %r' % type(value))

    if value.strip() not in {'true', 'false', '1', '0'}:
        raise self.error('FORG0001', "%r: not a boolean value" % value)
    return 't' in value or '1' in value


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
        if isinstance(arg, UntypedAtomic):
            return self.cast(arg.value, context)
        return self.cast(arg, context)
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
        err.code = self.parser.get_qname(XQT_ERRORS_NAMESPACE, 'XPST0017')
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
    if isinstance(value, UntypedAtomic):
        value = value.value
    elif not isinstance(value, str):
        raise self.error('XPTY0004', 'the argument has an invalid type %r' % type(value))

    try:
        if ':' not in value:
            return QName(self.parser.namespaces.get('', ''), value)
        pfx, _ = value.strip().split(':')
        return QName(self.parser.namespaces[pfx], value)
    except ValueError:
        raise self.error('FORG0001', 'invalid value {!r} for argument'.format(value.strip()))
    except KeyError as err:
        raise self.error('FONS0004', 'no namespace found for prefix {}'.format(err))


@constructor('dateTime', bp=90, label=('function', 'constructor'))
def cast(self, value):
    try:
        cls = DateTime if self.parser.schema.xsd_version == '1.1' else DateTime10
    except (AttributeError, NotImplementedError):
        cls = DateTime10

    if isinstance(value, cls):
        return value
    elif isinstance(value, UntypedAtomic):
        return cls.fromstring(value.value)
    elif isinstance(value, Date10):
        return cls(value.year, value.month, value.day, tzinfo=value.tzinfo)
    return cls.fromstring(value)


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
        elif self.label != 'constructor':
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
            return
        elif dt.tzinfo == tm.tzinfo or tm.tzinfo is None:
            tzinfo = dt.tzinfo
        elif dt.tzinfo is None:
            tzinfo = tm.tzinfo
        else:
            raise self.error('FORG0008')

        try:
            if self.parser.schema.xsd_version == '1.1':
                return DateTime(dt.year, dt.month, dt.day, tm.hour, tm.minute,
                                tm.second, tm.microsecond, tzinfo)
        except (AttributeError, NotImplementedError):
            pass

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
