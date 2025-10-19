#
# Copyright (c), 2018-2025, SISSA (International School for Advanced Studies).
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
from decimal import Decimal as _Decimal
from typing import Union as _Union

from .atomic_types import builtin_atomic_types, atomic_sequence_types, \
    AtomicTypeMeta, AnyAtomicType
from .numeric import Float, Float10, Integer, Int, Long, \
    NegativeInteger, PositiveInteger, NonNegativeInteger, \
    NonPositiveInteger, Short, Byte, UnsignedByte, UnsignedInt, \
    UnsignedLong, UnsignedShort
from .untyped import UntypedAtomic
from .qname import AbstractQName, QName, Notation
from .string import NormalizedString, XsdToken, Name, NCName, \
    NMToken, Id, Idref, Language, Entity
from .uri import AnyURI
from .binary import AbstractBinary, Base64Binary, HexBinary
from .datetime import AbstractDateTime, DateTime10, DateTime, DateTimeStamp, \
    Date10, Date, GregorianDay, GregorianMonth, GregorianYear, GregorianYear10, \
    GregorianMonthDay, GregorianYearMonth, GregorianYearMonth10, Time, Timezone, \
    Duration, DayTimeDuration, YearMonthDuration
from .proxies import BooleanProxy, DecimalProxy, DoubleProxy, DoubleProxy10, StringProxy, \
    NumericProxy, ArithmeticProxy

###
# Aliases for type annotations
AtomicType = _Union[str, int, float, _Decimal, bool, AnyAtomicType]
NumericType = _Union[int, float, _Decimal]
ArithmeticType = _Union[NumericType, AbstractDateTime, Duration, UntypedAtomic]

###
# Alias kept for backward compatibility, will be removed in v6.0.
OrderedDateTime = AbstractDateTime
