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
XSD atomic datatypes subpackage. Includes a class for UntypedAtomic data and
classes for other XSD built-in types. This subpackage raises only built-in
exceptions in order to be reusable in other packages.
"""
from decimal import Decimal

from ..helpers import QNAME_PATTERN  # For backward compatibility

from .atomic_types import xsd10_atomic_types, xsd11_atomic_types, AnyAtomicType
from .untyped import UntypedAtomic
from .qname import Notation, QName
from .numeric import Float10, Float, Integer, Int, NegativeInteger, \
    PositiveInteger, NonNegativeInteger, NonPositiveInteger, Long, \
    Short, Byte, UnsignedByte, UnsignedInt, UnsignedLong, UnsignedShort
from .string import NormalizedString, XsdToken, Name, NCName, NMToken, Id, \
    Idref, Language, Entity
from .uri import AnyURI
from .binary import AbstractBinary, Base64Binary, HexBinary
from .datetime import AbstractDateTime, DateTime10, DateTime, DateTimeStamp, \
    Date10, Date, GregorianDay, GregorianMonth, GregorianYear, GregorianYear10, \
    GregorianMonthDay, GregorianYearMonth, GregorianYearMonth10, Time, Timezone, \
    Duration, DayTimeDuration, YearMonthDuration
from .proxies import BooleanProxy, DecimalProxy, DoubleProxy10, DoubleProxy, \
    StringProxy, NumericProxy, ArithmeticProxy

##
# Register not derived XSD primitive types as virtual subclasses of AnyAtomicType

AnyAtomicType.register(BooleanProxy)
AnyAtomicType.register(Base64Binary)
AnyAtomicType.register(DecimalProxy)
AnyAtomicType.register(StringProxy)
AnyAtomicType.register(Date10)
AnyAtomicType.register(DateTime10)
AnyAtomicType.register(DoubleProxy10)
AnyAtomicType.register(GregorianDay)
AnyAtomicType.register(GregorianMonth)
AnyAtomicType.register(GregorianMonthDay)
AnyAtomicType.register(GregorianYear10)
AnyAtomicType.register(GregorianYearMonth10)
AnyAtomicType.register(HexBinary)
AnyAtomicType.register(Notation)
AnyAtomicType.register(QName)
AnyAtomicType.register(Time)
AnyAtomicType.register(UntypedAtomic)
StringProxy.register(NormalizedString)

xsd11_atomic_types.update(
    (k, v) for k, v in xsd10_atomic_types.items() if k not in xsd11_atomic_types
)
XSD_BUILTIN_TYPES = xsd10_atomic_types

ATOMIC_VALUES = {
    'untypedAtomic': UntypedAtomic('1'),
    'anyType': UntypedAtomic('1'),
    'anySimpleType': UntypedAtomic('1'),
    'anyAtomicType': UntypedAtomic('1'),
    'boolean': True,
    'decimal': Decimal('1.0'),
    'double': 1.0,
    'float': Float10(1.0),
    'string': '  alpha\t',
    'date': Date.fromstring('2000-01-01'),
    'dateTime': DateTime.fromstring('2000-01-01T12:00:00'),
    'gDay': GregorianDay.fromstring('---31'),
    'gMonth': GregorianMonth.fromstring('--12'),
    'gMonthDay': GregorianMonthDay.fromstring('--12-01'),
    'gYear': GregorianYear.fromstring('1999'),
    'gYearMonth': GregorianYearMonth.fromstring('1999-09'),
    'time': Time.fromstring('09:26:54'),
    'duration': Duration.fromstring('P1MT1S'),
    'dayTimeDuration': DayTimeDuration.fromstring('P1DT1S'),
    'yearMonthDuration': YearMonthDuration.fromstring('P1Y1M'),
    'QName': QName("http://www.w3.org/2001/XMLSchema", 'xs:element'),
    'anyURI': AnyURI('https://example.com'),
    'normalizedString': NormalizedString(' alpha  '),
    'token': XsdToken('a token'),
    'language': Language('en-US'),
    'Name': Name('_a.name::'),
    'NCName': NCName('nc-name'),
    'ID': Id('id1'),
    'IDREF': Idref('id_ref1'),
    'ENTITY': Entity('entity1'),
    'NMTOKEN': NMToken('a_token'),
    'base64Binary': Base64Binary(b'YWxwaGE='),
    'hexBinary': HexBinary(b'31'),
    'dateTimeStamp': DateTimeStamp.fromstring('2000-01-01T12:00:00+01:00'),
    'integer': Integer(1),
    'long': Long(1),
    'int': Int(1),
    'short': Short(1),
    'byte': Byte(1),
    'positiveInteger': PositiveInteger(1),
    'negativeInteger': NegativeInteger(-1),
    'nonPositiveInteger': NonPositiveInteger(0),
    'nonNegativeInteger': NonNegativeInteger(0),
    'unsignedLong': UnsignedLong(1),
    'unsignedInt': UnsignedInt(1),
    'unsignedShort': UnsignedShort(1),
    'unsignedByte': UnsignedByte(1),
}

__all__ = ['xsd10_atomic_types', 'xsd11_atomic_types', 'ATOMIC_VALUES', 'XSD_BUILTIN_TYPES',
           'NumericProxy', 'ArithmeticProxy', 'QNAME_PATTERN', 'AnyAtomicType',
           'AbstractDateTime', 'DateTime10', 'DateTime', 'DateTimeStamp', 'Date10',
           'Date', 'Time', 'GregorianDay', 'GregorianMonth', 'GregorianMonthDay',
           'GregorianYear10', 'GregorianYear', 'GregorianYearMonth10', 'GregorianYearMonth',
           'Timezone', 'Duration', 'YearMonthDuration', 'DayTimeDuration', 'StringProxy',
           'NormalizedString', 'XsdToken', 'Language', 'Name', 'NCName', 'Id', 'Idref',
           'Entity', 'NMToken', 'Base64Binary', 'HexBinary', 'Float10', 'Float',
           'Integer', 'NonPositiveInteger', 'NegativeInteger', 'Long', 'Int', 'Short',
           'Byte', 'NonNegativeInteger', 'PositiveInteger', 'UnsignedLong', 'UnsignedInt',
           'UnsignedShort', 'UnsignedByte', 'AnyURI', 'Notation', 'QName', 'BooleanProxy',
           'DecimalProxy', 'DoubleProxy10', 'DoubleProxy', 'UntypedAtomic', 'AbstractBinary']
