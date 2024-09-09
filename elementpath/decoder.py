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
from typing import Any, Optional, Type, TYPE_CHECKING

from elementpath._typing import MutableMapping
from elementpath.aliases import AnyNsmapType
from elementpath.protocols import XsdTypeProtocol
from elementpath.exceptions import xpath_error
from elementpath.namespaces import XSD_NAMESPACE, XSD_NOTATION, XSD_UNTYPED_ATOMIC

import elementpath.datatypes as dt

if TYPE_CHECKING:
    from elementpath.xpath_tokens import XPathToken

Builder = namedtuple('Builder', ['cls', 'value'])

ATOMIC_BUILDERS: MutableMapping[Optional[str], Builder] = {
    f'{{{XSD_NAMESPACE}}}untypedAtomic': Builder(dt.UntypedAtomic, '1'),
    f'{{{XSD_NAMESPACE}}}anyType': Builder(dt.UntypedAtomic, '1'),
    f'{{{XSD_NAMESPACE}}}anySimpleType': Builder(dt.UntypedAtomic, '1'),
    f'{{{XSD_NAMESPACE}}}anyAtomicType': Builder(dt.UntypedAtomic, '1'),
    f'{{{XSD_NAMESPACE}}}boolean': Builder(bool, True),
    f'{{{XSD_NAMESPACE}}}decimal': Builder(Decimal, '1.0'),
    f'{{{XSD_NAMESPACE}}}double': Builder(float, 1.0),
    f'{{{XSD_NAMESPACE}}}float': Builder(dt.Float10, 1.0),
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
    f'{{{XSD_NAMESPACE}}}QName':
        Builder(dt.QName, ("http://www.w3.org/2001/XMLSchema", 'xs:element')),
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
    f'{{{XSD_NAMESPACE}}}base64Binary': Builder(dt.Base64Binary, b'YWxwaGE='),
    f'{{{XSD_NAMESPACE}}}hexBinary': Builder(dt.HexBinary, b'31'),
    f'{{{XSD_NAMESPACE}}}dateTimeStamp':
        Builder(dt.DateTimeStamp.fromstring, '2000-01-01T12:00:00+01:00'),
    f'{{{XSD_NAMESPACE}}}integer': Builder(dt.Integer, 1),
    f'{{{XSD_NAMESPACE}}}long': Builder(dt.Long, 1),
    f'{{{XSD_NAMESPACE}}}int': Builder(dt.Int, 1),
    f'{{{XSD_NAMESPACE}}}short': Builder(dt.Short, 1),
    f'{{{XSD_NAMESPACE}}}byte': Builder(dt.Byte, 1),
    f'{{{XSD_NAMESPACE}}}positiveInteger': Builder(dt.PositiveInteger, 1),
    f'{{{XSD_NAMESPACE}}}negativeInteger': Builder(dt.NegativeInteger, -1),
    f'{{{XSD_NAMESPACE}}}nonPositiveInteger': Builder(dt.NonPositiveInteger, 0),
    f'{{{XSD_NAMESPACE}}}nonNegativeInteger': Builder(dt.NonNegativeInteger, 0),
    f'{{{XSD_NAMESPACE}}}unsignedLong': Builder(dt.UnsignedLong, 1),
    f'{{{XSD_NAMESPACE}}}unsignedInt': Builder(dt.UnsignedInt, 1),
    f'{{{XSD_NAMESPACE}}}unsignedShort': Builder(dt.UnsignedShort, 1),
    f'{{{XSD_NAMESPACE}}}unsignedByte': Builder(dt.UnsignedByte, 1),
}


def get_builder(xsd_type: Optional[XsdTypeProtocol],
                text: Optional[str],
                namespaces: AnyNsmapType = None) -> Builder:
    """
    Returns the atomic builtin XSD type that is suitable for decoding a text value.
    """
    if xsd_type is None:
        return ATOMIC_BUILDERS[XSD_UNTYPED_ATOMIC]
    elif xsd_type.name in ATOMIC_BUILDERS:
        return ATOMIC_BUILDERS[xsd_type.name]

    if namespaces is None:
        namespaces = {}

    root_type = xsd_type.root_type
    derivation_depth = 1

    while root_type.name not in ATOMIC_BUILDERS or root_type.is_union():
        derivation_depth += 1
        if derivation_depth > 15:  # too many derivations: it could be a dummy XSD type
            return ATOMIC_BUILDERS[XSD_UNTYPED_ATOMIC]

        union_type = root_type
        if hasattr(union_type, 'member_types'):
            for xsd_type in union_type.member_types:
                assert xsd_type is not None
                if xsd_type.root_type.is_valid(text, namespaces=namespaces):
                    root_type = xsd_type.root_type
                    break
            else:
                if text is None:
                    return ATOMIC_BUILDERS[XSD_UNTYPED_ATOMIC]

    if root_type.is_notation():
        if root_type.name is None or root_type.name == XSD_NOTATION:
            name = '_Notation'
        elif '}' in root_type.name:
            name = f"{root_type.name.split('}')[-1].title()}_Notation"
        else:
            name = f"{root_type.name.split(':')[-1].title()}_Notation"

        return Builder(type(name, (dt.Notation,), {}), ATOMIC_BUILDERS[root_type.name])

    return ATOMIC_BUILDERS[root_type.name]


def get_atomic_value(xsd_type: Optional[XsdTypeProtocol] = None,
                     text: Optional[str] = None,
                     namespaces: AnyNsmapType = None,
                     token: Optional['XPathToken'] = None) -> dt.AtomicType:
    """Gets an atomic value for an XSD type instance and a source text/value."""

    def decode_value(v: Any) -> dt.AtomicType:
        if isinstance(v, str) and issubclass(cls, (dt.QName, dt.Notation)) and namespaces:
            if ':' not in v:
                v = namespaces.get(''), v
            else:
                v = namespaces[v.split(':')[0]], v

        try:
            if isinstance(v, tuple):
                return cls(*v)
            elif issubclass(cls, (dt.AbstractDateTime, dt.Duration)):
                return cls.fromstring(v)
            return cls(v)
        except ValueError as err:
            raise xpath_error('FORG0001', err, token, namespaces)
        except ArithmeticError as err:
            if issubclass(cls, dt.AbstractDateTime):
                raise xpath_error('FODT0001', err, token, namespaces)
            elif issubclass(cls, dt.Duration):
                raise xpath_error('FODT0002', err, token, namespaces)
            else:
                raise xpath_error('FOCA0002', err, token, namespaces)

    if xsd_type is None:
        return dt.UntypedAtomic(text or '')

    if namespaces is None:
        namespaces = {}

    builder = get_builder(xsd_type, text, namespaces)
    cls: Type[dt.AtomicType] = builder.cls

    if text is None:
        return decode_value(builder.value)

    xsd_type.validate(text, namespaces=namespaces)
    return decode_value(text)


__all__ = ['get_atomic_value']
