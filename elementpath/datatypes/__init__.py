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
from collections import namedtuple
from decimal import Decimal
from typing import Optional, Tuple, Type, Union

from elementpath.aliases import MutableMapping, NsmapType
from elementpath.protocols import XsdTypeProtocol
from elementpath.namespaces import XSD_NAMESPACE, XSD_NOTATION

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
DatetimeValueType = AbstractDateTime  # keep until v5.0 for backward compatibility
AtomicValueType = Union[str, int, float, Decimal, bool, AnyAtomicType]
NumericType = Union[int, float, Decimal]
NumericOpsType = Tuple[Optional[NumericType], Optional[NumericType]]
ArithmeticType = Union[NumericType, AbstractDateTime, Duration, UntypedAtomic]
ArithmeticOpsType = Tuple[Optional[ArithmeticType], Optional[ArithmeticType]]

Builder = namedtuple('Builder', ['cls', 'value'])

ATOMIC_TYPES: MutableMapping[Optional[str], Builder] = {
    f'{{{XSD_NAMESPACE}}}untypedAtomic': Builder(UntypedAtomic, '1'),
    f'{{{XSD_NAMESPACE}}}anyType': Builder(UntypedAtomic, '1'),
    f'{{{XSD_NAMESPACE}}}anySimpleType': Builder(UntypedAtomic, '1'),
    f'{{{XSD_NAMESPACE}}}anyAtomicType': Builder(UntypedAtomic, '1'),
    f'{{{XSD_NAMESPACE}}}boolean': Builder(bool, True),
    f'{{{XSD_NAMESPACE}}}decimal': Builder(Decimal, '1.0'),
    f'{{{XSD_NAMESPACE}}}double': Builder(float, 1.0),
    f'{{{XSD_NAMESPACE}}}float': Builder(Float10, 1.0),
    f'{{{XSD_NAMESPACE}}}string': Builder(str, '  alpha\t'),
    f'{{{XSD_NAMESPACE}}}date': Builder(Date, '2000-01-01'),
    f'{{{XSD_NAMESPACE}}}dateTime': Builder(DateTime, '2000-01-01T12:00:00'),
    f'{{{XSD_NAMESPACE}}}gDay': Builder(GregorianDay, '---31'),
    f'{{{XSD_NAMESPACE}}}gMonth': Builder(GregorianMonth, '--12'),
    f'{{{XSD_NAMESPACE}}}gMonthDay': Builder(GregorianMonthDay, '--12-01'),
    f'{{{XSD_NAMESPACE}}}gYear': Builder(GregorianYear, '1999'),
    f'{{{XSD_NAMESPACE}}}gYearMonth': Builder(GregorianYearMonth, '1999-09'),
    f'{{{XSD_NAMESPACE}}}time': Builder(Time, '09:26:54'),
    f'{{{XSD_NAMESPACE}}}duration': Builder(Duration, 'P1MT1S'),
    f'{{{XSD_NAMESPACE}}}dayTimeDuration': Builder(DayTimeDuration, 'P1DT1S'),
    f'{{{XSD_NAMESPACE}}}yearMonthDuration': Builder(YearMonthDuration, 'P1Y1M'),
    f'{{{XSD_NAMESPACE}}}QName':
        Builder(QName, ("http://www.w3.org/2001/XMLSchema", 'xs:element')),
    f'{{{XSD_NAMESPACE}}}anyURI': Builder(AnyURI, 'https://example.com'),
    f'{{{XSD_NAMESPACE}}}normalizedString': Builder(NormalizedString, ' alpha  '),
    f'{{{XSD_NAMESPACE}}}token': Builder(XsdToken, 'a token'),
    f'{{{XSD_NAMESPACE}}}language': Builder(Language, 'en-US'),
    f'{{{XSD_NAMESPACE}}}Name': Builder(Name, '_a.name::'),
    f'{{{XSD_NAMESPACE}}}NCName': Builder(NCName, 'nc-name'),
    f'{{{XSD_NAMESPACE}}}ID': Builder(Id, 'id1'),
    f'{{{XSD_NAMESPACE}}}IDREF': Builder(Idref, 'id_ref1'),
    f'{{{XSD_NAMESPACE}}}ENTITY': Builder(Entity, 'entity1'),
    f'{{{XSD_NAMESPACE}}}NMTOKEN': Builder(NMToken, 'a_token'),
    f'{{{XSD_NAMESPACE}}}base64Binary': Builder(Base64Binary, b'YWxwaGE='),
    f'{{{XSD_NAMESPACE}}}hexBinary': Builder(HexBinary, b'31'),
    f'{{{XSD_NAMESPACE}}}dateTimeStamp':
        Builder(DateTimeStamp.fromstring, '2000-01-01T12:00:00+01:00'),
    f'{{{XSD_NAMESPACE}}}integer': Builder(Integer, 1),
    f'{{{XSD_NAMESPACE}}}long': Builder(Long, 1),
    f'{{{XSD_NAMESPACE}}}int': Builder(Int, 1),
    f'{{{XSD_NAMESPACE}}}short': Builder(Short, 1),
    f'{{{XSD_NAMESPACE}}}byte': Builder(Byte, 1),
    f'{{{XSD_NAMESPACE}}}positiveInteger': Builder(PositiveInteger, 1),
    f'{{{XSD_NAMESPACE}}}negativeInteger': Builder(NegativeInteger, -1),
    f'{{{XSD_NAMESPACE}}}nonPositiveInteger': Builder(NonPositiveInteger, 0),
    f'{{{XSD_NAMESPACE}}}nonNegativeInteger': Builder(NonNegativeInteger, 0),
    f'{{{XSD_NAMESPACE}}}unsignedLong': Builder(UnsignedLong, 1),
    f'{{{XSD_NAMESPACE}}}unsignedInt': Builder(UnsignedInt, 1),
    f'{{{XSD_NAMESPACE}}}unsignedShort': Builder(UnsignedShort, 1),
    f'{{{XSD_NAMESPACE}}}unsignedByte': Builder(UnsignedByte, 1),
}


def get_atomic_value(xsd_type: Optional[XsdTypeProtocol] = None,
                     text: Optional[str] = None,
                     namespaces: Optional[NsmapType] = None) -> AtomicValueType:
    """Gets an atomic value for an XSD type instance and a source text/value."""
    ns: Optional[str]

    if xsd_type is None:
        return UntypedAtomic(text or '')

    try:
        builder = ATOMIC_TYPES[xsd_type.name]
    except KeyError:
        try:
            builder = ATOMIC_TYPES[xsd_type.root_type.name]
        except KeyError:
            return UntypedAtomic(text or '')

    cls: Type[AtomicValueType]
    if xsd_type.is_notation():
        if xsd_type.name is None or xsd_type.name == XSD_NOTATION:
            name = '_Notation'
        elif '}' in xsd_type.name:
            name = f"{xsd_type.name.split('}')[-1].title()}_Notation"
        else:
            name = f"{xsd_type.name.split(':')[-1].title()}_Notation"

        cls = type(name, (Notation,), {})
    else:
        cls = builder.cls

    if text is None:
        value = builder.value
    else:
        if namespaces is None:
            namespaces = {}
        xsd_type.validate(text, namespaces=namespaces)

        if not issubclass(cls, (QName, Notation)):
            value = text
        elif ':' not in text:
            value = namespaces.get(''), text
        else:
            value = namespaces[text.split(':')[0]], text

    if isinstance(value, tuple):
        return cls(*value)
    elif issubclass(cls, (AbstractDateTime, Duration)):
        return cls.fromstring(value)
    return cls(value)


__all__ = ['xsd10_atomic_types', 'xsd11_atomic_types', 'get_atomic_value',
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
           'AtomicValueType', 'DatetimeValueType', 'OrderedDateTime', 'AbstractQName',
           'NumericType', 'NumericOpsType', 'ArithmeticType', 'ArithmeticOpsType']
