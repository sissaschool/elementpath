#
# Copyright (c), 2018-2020, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from abc import ABCMeta, abstractmethod
from types import MappingProxyType
from typing import Any, Optional
import re

XSD_NAMESPACE = "http://www.w3.org/2001/XMLSchema"

###
# Classes for XSD built-in atomic types. All defined classes use a
# metaclass that adds some common methods and registers each class
# into a dictionary. Some classes of XSD primitive types are defined
# as proxies of basic Python datatypes.

_xsd_atomic_types: dict[str, dict[Optional[str], 'AtomicTypeMeta']] = {
    '1.0': {},
    '1.1': {}
}
"""Registry of builtin XSD 1.0/1.1 atomic types."""

xsd_atomic_types = MappingProxyType({
    '1.0': MappingProxyType(_xsd_atomic_types['1.0']),
    '1.1': MappingProxyType(_xsd_atomic_types['1.1']),
})


class AtomicTypeMeta(ABCMeta):
    """
    Metaclass for creating XSD atomic types. The created classes
    are decorated with missing attributes and methods. When a name
    attribute is provided the class is registered into a global map
    of XSD atomic types and also the expanded name is added.
    """
    xsd_version: str

    def __new__(mcs, class_name: str, bases: tuple[type[Any], ...], dict_: dict[str, Any]) \
            -> 'AtomicTypeMeta':
        try:
            name = dict_['name']
        except KeyError:
            name = dict_['name'] = None  # do not inherit name

        if name is not None and not isinstance(name, str):
            raise TypeError("attribute 'name' must be a string or None")

        cls = super(AtomicTypeMeta, mcs).__new__(mcs, class_name, bases, dict_)

        # Register ony derived classes with a name
        if name:
            for xsd_version, atomic_types in _xsd_atomic_types.items():
                if cls.xsd_version <= xsd_version and (
                    name not in atomic_types or atomic_types[name].xsd_version < cls.xsd_version
                ):
                    atomic_types[name] = cls

        return cls


class AnyAtomicType(metaclass=AtomicTypeMeta):
    name: Optional[str] = 'anyAtomicType'
    xsd_version: str = '1.0'
    pattern: re.Pattern[str] = re.compile(r'^$')

    @classmethod
    def validate(cls, value: object) -> None:
        if isinstance(value, cls):
            return
        elif isinstance(value, str):
            if cls.pattern.match(value) is None:
                raise cls.invalid_value(value)
        else:
            raise cls.invalid_type(value)

    @classmethod
    def is_valid(cls, value: object) -> bool:
        try:
            cls.validate(value)
        except (TypeError, ValueError):
            return False
        else:
            return True

    @classmethod
    def invalid_type(cls, value: object) -> TypeError:
        if cls.name:
            return TypeError('invalid type {!r} for xs:{}'.format(type(value), cls.name))
        return TypeError('invalid type {!r} for {!r}'.format(type(value), cls))

    @classmethod
    def invalid_value(cls, value: object) -> ValueError:
        if cls.name:
            return ValueError('invalid value {!r} for xs:{}'.format(value, cls.name))
        return ValueError('invalid value {!r} for {!r}'.format(value, cls))

    @abstractmethod
    def __init__(self, value: Any) -> None:
        raise NotImplementedError()
