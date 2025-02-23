#
# Copyright (c), 2024, SISSA (International School for Advanced Studies).
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
from functools import lru_cache
from typing import List, Optional, Type

from elementpath._typing import Callable, Iterator, MutableMapping
from elementpath.aliases import AnyNsmapType
from elementpath.datatypes import AtomicType
from elementpath.protocols import XsdTypeProtocol
from elementpath.exceptions import xpath_error
from elementpath.namespaces import XSD_NAMESPACE

import elementpath.datatypes as dt

DecoderType = Callable[[str, AnyNsmapType], AtomicType]

Builder = namedtuple('Builder', 'cls text nsmap', defaults=(None, None))


class _Notation(dt.Notation):
    """An instantiable xs:NOTATION."""


# noinspection PyArgumentList
ATOMIC_BUILDERS: MutableMapping[Optional[str], Builder] = {
    f'{{{XSD_NAMESPACE}}}untypedAtomic': Builder(dt.UntypedAtomic, '1'),
    f'{{{XSD_NAMESPACE}}}anyType': Builder(dt.UntypedAtomic, '1'),
    f'{{{XSD_NAMESPACE}}}anySimpleType': Builder(dt.UntypedAtomic, '1'),
    f'{{{XSD_NAMESPACE}}}anyAtomicType': Builder(dt.UntypedAtomic, '1'),
    f'{{{XSD_NAMESPACE}}}boolean': Builder(bool, 'true'),
    f'{{{XSD_NAMESPACE}}}decimal': Builder(Decimal, '1.0'),
    f'{{{XSD_NAMESPACE}}}double': Builder(float, '1.0'),
    f'{{{XSD_NAMESPACE}}}float': Builder(dt.Float10, '1.0'),
    f'{{{XSD_NAMESPACE}}}string': Builder(str, '  alpha\t'),
    f'{{{XSD_NAMESPACE}}}date': Builder(dt.Date, '2000-01-01'),
    f'{{{XSD_NAMESPACE}}}dateTime': Builder(dt.DateTime, '2000-01-01T12:00:00'),
    f'{{{XSD_NAMESPACE}}}gDay': Builder(dt.GregorianDay, '---31'),
    f'{{{XSD_NAMESPACE}}}gMonth': Builder(dt.GregorianMonth, '--12'),
    f'{{{XSD_NAMESPACE}}}gMonthDay': Builder(dt.GregorianMonthDay, '--12-01'),
    f'{{{XSD_NAMESPACE}}}gYear': Builder(dt.GregorianYear, '1999'),
    f'{{{XSD_NAMESPACE}}}gYearMonth': Builder(dt.GregorianYearMonth, '1999-09'),
    f'{{{XSD_NAMESPACE}}}time': Builder(dt.Time, '09:26:54'),
    f'{{{XSD_NAMESPACE}}}duration': Builder(dt.Duration, 'P1MT1S'),
    f'{{{XSD_NAMESPACE}}}dayTimeDuration': Builder(dt.DayTimeDuration, 'P1DT1S'),
    f'{{{XSD_NAMESPACE}}}yearMonthDuration': Builder(dt.YearMonthDuration, 'P1Y1M'),
    f'{{{XSD_NAMESPACE}}}QName': Builder(dt.QName, 'xs:element'),
    f'{{{XSD_NAMESPACE}}}NOTATION': Builder(_Notation, 'xs:element'),
    f'{{{XSD_NAMESPACE}}}anyURI': Builder(dt.AnyURI, 'https://example.com'),
    f'{{{XSD_NAMESPACE}}}normalizedString': Builder(dt.NormalizedString, ' alpha  '),
    f'{{{XSD_NAMESPACE}}}token': Builder(dt.XsdToken, 'a token'),
    f'{{{XSD_NAMESPACE}}}language': Builder(dt.Language, 'en-US'),
    f'{{{XSD_NAMESPACE}}}Name': Builder(dt.Name, '_a.name::'),
    f'{{{XSD_NAMESPACE}}}NCName': Builder(dt.NCName, 'nc-name'),
    f'{{{XSD_NAMESPACE}}}ID': Builder(dt.Id, 'id1'),
    f'{{{XSD_NAMESPACE}}}IDREF': Builder(dt.Idref, 'id_ref1'),
    f'{{{XSD_NAMESPACE}}}ENTITY': Builder(dt.Entity, 'entity1'),
    f'{{{XSD_NAMESPACE}}}NMTOKEN': Builder(dt.NMToken, 'a_token'),
    f'{{{XSD_NAMESPACE}}}base64Binary': Builder(dt.Base64Binary, 'YWxwaGE='),
    f'{{{XSD_NAMESPACE}}}hexBinary': Builder(dt.HexBinary, '31'),
    f'{{{XSD_NAMESPACE}}}dateTimeStamp':
        Builder(dt.DateTimeStamp.fromstring, '2000-01-01T12:00:00+01:00'),
    f'{{{XSD_NAMESPACE}}}integer': Builder(dt.Integer, '1'),
    f'{{{XSD_NAMESPACE}}}long': Builder(dt.Long, '1'),
    f'{{{XSD_NAMESPACE}}}int': Builder(dt.Int, '1'),
    f'{{{XSD_NAMESPACE}}}short': Builder(dt.Short, '1'),
    f'{{{XSD_NAMESPACE}}}byte': Builder(dt.Byte, '1'),
    f'{{{XSD_NAMESPACE}}}positiveInteger': Builder(dt.PositiveInteger, '1'),
    f'{{{XSD_NAMESPACE}}}negativeInteger': Builder(dt.NegativeInteger, '-1'),
    f'{{{XSD_NAMESPACE}}}nonPositiveInteger': Builder(dt.NonPositiveInteger, '0'),
    f'{{{XSD_NAMESPACE}}}nonNegativeInteger': Builder(dt.NonNegativeInteger, '0'),
    f'{{{XSD_NAMESPACE}}}unsignedLong': Builder(dt.UnsignedLong, '1'),
    f'{{{XSD_NAMESPACE}}}unsignedInt': Builder(dt.UnsignedInt, '1'),
    f'{{{XSD_NAMESPACE}}}unsignedShort': Builder(dt.UnsignedShort, '1'),
    f'{{{XSD_NAMESPACE}}}unsignedByte': Builder(dt.UnsignedByte, '1'),
}


@lru_cache(maxsize=None)
def get_builders(xsd_type: XsdTypeProtocol) -> List[Builder]:
    """
    Returns a list of atomic builtin XSD types that are in the base type of
    the XSD type argument.
    """
    def iter_builders(root_type: XsdTypeProtocol, depth: int) -> Iterator[Builder]:
        if depth > 15:
            return
        if root_type.name in ATOMIC_BUILDERS:
            yield ATOMIC_BUILDERS[root_type.name]
        elif hasattr(root_type, 'member_types'):
            for member_type in root_type.member_types:
                yield from iter_builders(member_type, depth + 1)

    if xsd_type.name in ATOMIC_BUILDERS:
        return [ATOMIC_BUILDERS[xsd_type.name]]
    elif xsd_type.is_simple() or (simple_type := xsd_type.simple_type) is None:
        return [builder for builder in iter_builders(xsd_type.root_type, 1)]
    elif simple_type.name in ATOMIC_BUILDERS:
        return [ATOMIC_BUILDERS[simple_type.name]]
    return [builder for builder in iter_builders(simple_type.root_type, 1)]


def get_atomic_sequence(xsd_type: Optional[XsdTypeProtocol],
                        text: object = None,
                        namespaces: AnyNsmapType = None) -> Iterator[dt.AtomicType]:
    """Returns a decoder function for atomic values of an XSD type instance."""
    def decode(value: str) -> dt.AtomicType:
        if issubclass(cls, (dt.AbstractDateTime, dt.Duration)):
            return cls.fromstring(value)
        elif not issubclass(cls, dt.AbstractQName):
            return cls(value)
        else:
            nonlocal namespaces
            if namespaces is None:
                namespaces = {'xs': XSD_NAMESPACE}
            if ':' not in value:
                return cls(namespaces.get(''), value)
            else:
                return cls(namespaces[value.split(':')[0]], value)

    if xsd_type is None:
        yield dt.UntypedAtomic(text if isinstance(text, str) else '')
        return

    for k, builder in enumerate(get_builders(xsd_type), start=1):
        cls: Type[dt.AtomicType] = builder.cls

        _text = text if isinstance(text, str) else builder.text
        if len(builder) < k and not xsd_type.is_valid(text, namespaces=namespaces):
            continue

        try:
            if xsd_type.is_list():
                for item in _text.split():
                    yield decode(item)
            else:
                yield decode(_text)

        except ValueError as err:
            raise xpath_error('FORG0001', err, namespaces=namespaces)
        except ArithmeticError as err:
            if issubclass(cls, dt.AbstractDateTime):
                raise xpath_error('FODT0001', err, namespaces=namespaces)
            elif issubclass(cls, dt.Duration):
                raise xpath_error('FODT0002', err, namespaces=namespaces)
            else:
                raise xpath_error('FOCA0002', err, namespaces=namespaces)
        else:
            return
    else:
        if hasattr(xsd_type, 'decode'):
            yield xsd_type.decode(text if isinstance(text, str) else '')
        else:
            yield dt.UntypedAtomic(text if isinstance(text, str) else '')


__all__ = ['ATOMIC_BUILDERS', 'get_atomic_sequence']
