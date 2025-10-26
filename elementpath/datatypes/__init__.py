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
from .any_types import builtin_xsd_types, builtin_sequence_types, \
    BuiltinTypeMeta, AnyAtomicType
from .sequences import XPathSequence, EmptySequence
from .numeric import Float, Float10, Integer, Int, Long, \
    NegativeInteger, PositiveInteger, NonNegativeInteger, \
    NonPositiveInteger, Short, Byte, UnsignedByte, UnsignedInt, \
    UnsignedLong, UnsignedShort
from .untyped import UntypedAtomic
from .qname import AbstractQName, QName, Notation
from .string import NormalizedString, XsdToken, Name, NCName, \
    NMToken, Id, Idref, Language, Entity
from .lists import AbstractListType, NMTokens, Idrefs, Entities
from .uri import AnyURI
from .binary import AbstractBinary, Base64Binary, HexBinary
from .datetime import AbstractDateTime, DateTime10, DateTime, DateTimeStamp, \
    Date10, Date, GregorianDay, GregorianMonth, GregorianYear, GregorianYear10, \
    GregorianMonthDay, GregorianYearMonth, GregorianYearMonth10, Time, Timezone, \
    Duration, DayTimeDuration, YearMonthDuration
from .proxies import ErrorProxy, BooleanProxy, DecimalProxy, DoubleProxy, \
    DoubleProxy10, StringProxy, NumericProxy, ArithmeticProxy

###
# Alias kept for backward compatibility, will be removed in v6.0.
OrderedDateTime = AbstractDateTime
AtomicTypeMeta = BuiltinTypeMeta

__all__ = ['AbstractBinary', 'AbstractDateTime', 'AbstractListType', 'AbstractQName',
           'AnyAtomicType', 'AnyURI', 'ArithmeticProxy', 'AtomicTypeMeta', 'Base64Binary',
           'BooleanProxy', 'BuiltinTypeMeta', 'Byte', 'Date', 'Date10', 'DateTime',
           'DateTime10', 'DateTimeStamp', 'DayTimeDuration', 'DecimalProxy', 'DoubleProxy',
           'DoubleProxy10', 'Duration', 'EmptySequence', 'Entities', 'Entity', 'ErrorProxy',
           'Float', 'Float10', 'GregorianDay', 'GregorianMonth', 'GregorianMonthDay',
           'GregorianYear', 'GregorianYear10', 'GregorianYearMonth', 'GregorianYearMonth10',
           'HexBinary', 'Id', 'Idref', 'Idrefs', 'Int', 'Integer', 'Language', 'Long',
           'NCName', 'NMToken', 'NMTokens', 'Name', 'NegativeInteger', 'NonNegativeInteger',
           'NonPositiveInteger', 'NormalizedString', 'Notation', 'NumericProxy',
           'OrderedDateTime', 'PositiveInteger', 'QName', 'Short', 'StringProxy', 'Time',
           'Timezone', 'UnsignedByte', 'UnsignedInt', 'UnsignedLong', 'UnsignedShort',
           'UntypedAtomic', 'XPathSequence', 'XsdToken', 'YearMonthDuration',
           'builtin_sequence_types', 'builtin_xsd_types']
