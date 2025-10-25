#
# Copyright (c), 2018-2025, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from abc import ABCMeta, abstractmethod
from types import MappingProxyType
from typing import Any, Optional, TypeVar

from elementpath.helpers import Property, LazyPattern
from elementpath.namespaces import XSD_NAMESPACE

###
# Classes for XSD built-in atomic types. All defined classes use a
# metaclass that adds some common methods and registers each class
# into a dictionary. Some classes of XSD primitive types are defined
# as proxies of basic Python datatypes.

_builtin_xsd_types: dict[str, 'BuiltinTypeMeta'] = {}
builtin_xsd_types = MappingProxyType(_builtin_xsd_types)
"""Registry of builtin XSD types by expanded name."""

_builtin_sequence_types: dict[str, 'BuiltinTypeMeta'] = {}
atomic_sequence_types = MappingProxyType(_builtin_sequence_types)
"""Registry of builtin XSD types by sequence type."""

AT = TypeVar('AT')


class BuiltinTypeMeta(ABCMeta):
    """
    Metaclass for creating builtin XSD types. The created classes
    are decorated with missing attributes and methods. When a name
    attribute is provided the class is registered into a global map
    of XSD atomic types and also the expanded name is added.
    """
    def __new__(mcs, class_name: str, bases: tuple[type[Any], ...], dict_: dict[str, Any]) \
            -> 'BuiltinTypeMeta':
        try:
            name = dict_['name']
        except KeyError:
            name = dict_['name'] = None  # do not inherit name

        if name is not None and not isinstance(name, (str, Property)):
            raise TypeError("attribute 'name' must be a string or None")

        if '__slots__' not in dict_:
            dict_['__slots__'] = ()
        cls = super(BuiltinTypeMeta, mcs).__new__(mcs, class_name, bases, dict_)

        # Register all the derived classes with a valid name if not already registered
        if name:
            namespace: str | None = dict_.pop('namespace', XSD_NAMESPACE)
            prefix: str | None =  dict_.pop('prefix', 'xs')

            extended_name = f'{{{namespace}}}{name}' if namespace else name
            prefixed_name = f'{prefix}:{name}' if prefix else name

            if extended_name not in _builtin_xsd_types:
                _builtin_xsd_types[extended_name] = cls
            if prefixed_name not in _builtin_sequence_types:
                _builtin_sequence_types[prefixed_name] = cls

        return cls


class AnyType(metaclass=BuiltinTypeMeta):
    xsd_version: str = '1.0'
    name: str
    namespace: str | None = None
    prefix: str | None = None

    __slots__ = ()

    @abstractmethod
    def __init__(self, obj: Any) -> None:
        raise NotImplementedError()

    @classmethod
    def make(cls, obj: Any,
             version: str = '2.0',
             xsd_version: str = '1.1') -> 'AnyType':
        """
        Versioned factory method to create an atomic type.

        :param obj: the value to be converted to an atomic type.
        :param version: the version of the XPath processor that create the atomic type.
        :param xsd_version: the version of the XSD processor that create the atomic type.
        """
        return cls(obj)

    @classmethod
    def validate(cls, obj: object) -> None:
        if not isinstance(obj, object):
            raise cls.invalid_type(obj)  # noqa

    @classmethod
    def is_valid(cls, obj: object) -> bool:
        try:
            cls.validate(obj)
        except (TypeError, ValueError):
            return False
        else:
            return True

    @classmethod
    def invalid_type(cls, obj: object) -> TypeError:
        if cls.name:
            return TypeError('invalid type {!r} for xs:{}'.format(type(obj), cls.name))
        return TypeError('invalid type {!r} for {!r}'.format(type(obj), cls))

    @classmethod
    def invalid_value(cls, obj: object) -> ValueError:
        if cls.name:
            return ValueError('invalid value {!r} for xs:{}'.format(obj, cls.name))
        return ValueError('invalid value {!r} for {!r}'.format(obj, cls))


class AnySimpleType(AnyType):
    """Un"""
    __slots__ = ()


class AnyAtomicType(AnySimpleType):
    name = 'anyAtomicType'
    pattern = LazyPattern(r'^$')

    __slots__ = ()

    @abstractmethod
    def __init__(self, value: Any) -> None:
        raise NotImplementedError()

    @classmethod
    def validate(cls, value: object) -> None:
        if isinstance(value, cls):
            return
        elif isinstance(value, str):
            if cls.pattern.match(value) is None:
                raise cls.invalid_value(value)
        else:
            raise cls.invalid_type(value)
