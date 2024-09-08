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
from typing import Union

from .atomic_types import xsd10_atomic_types, xsd11_atomic_types, \
    AtomicTypeMeta, AnyAtomicType
from .untyped import UntypedAtomic
from .qname import AbstractQName, QName, Notation
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
    Duration, DayTimeDuration, YearMonthDuration, OrderedDateTime
from .proxies import BooleanProxy, DecimalProxy, DoubleProxy10, DoubleProxy, \
    StringProxy, NumericProxy, ArithmeticProxy


xsd11_atomic_types.update(
    (k, v) for k, v in xsd10_atomic_types.items() if k not in xsd11_atomic_types
)

###
# Aliases for type annotations
AtomicType = Union[str, int, float, Decimal, bool, AnyAtomicType]
NumericType = Union[int, float, Decimal]
ArithmeticType = Union[NumericType, AbstractDateTime, Duration, UntypedAtomic]
DatetimeValueType = AbstractDateTime  # keep until v5.0 for backward compatibility

__all__ = ['xsd10_atomic_types', 'xsd11_atomic_types',
           'AtomicTypeMeta', 'AnyAtomicType', 'NumericProxy', 'ArithmeticProxy',
           'AbstractDateTime', 'DateTime10', 'DateTime', 'DateTimeStamp', 'Date10',
           'Date', 'Time', 'GregorianDay', 'GregorianMonth', 'GregorianMonthDay',
           'GregorianYear10', 'GregorianYear', 'GregorianYearMonth10', 'GregorianYearMonth',
           'Timezone', 'Duration', 'YearMonthDuration', 'DayTimeDuration', 'StringProxy',
           'NormalizedString', 'XsdToken', 'Language', 'Name', 'NCName', 'Id', 'Idref',
           'Entity', 'NMToken', 'Base64Binary', 'HexBinary', 'Float10', 'Float',
           'Integer', 'NonPositiveInteger', 'NegativeInteger', 'Long', 'Int', 'Short',
           'Byte', 'NonNegativeInteger', 'PositiveInteger', 'UnsignedLong', 'UnsignedInt',
           'UnsignedShort', 'UnsignedByte', 'AnyURI', 'Notation', 'QName', 'BooleanProxy',
           'DecimalProxy', 'DoubleProxy10', 'DoubleProxy', 'UntypedAtomic', 'AbstractBinary',
           'AtomicType', 'DatetimeValueType', 'OrderedDateTime', 'AbstractQName',
           'NumericType', 'ArithmeticType']
