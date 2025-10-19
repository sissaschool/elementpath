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

_builtin_atomic_types: dict[str, 'AtomicTypeMeta'] = {}
builtin_atomic_types = MappingProxyType(_builtin_atomic_types)
"""Registry of builtin atomic types."""

_atomic_sequence_types: dict[str, 'AtomicTypeMeta'] = {}
atomic_sequence_types = MappingProxyType(_atomic_sequence_types)
"""Registry of atomic sequence types."""


AT = TypeVar('AT')


class AtomicTypeMeta(ABCMeta):
    """
    Metaclass for creating XSD atomic types. The created classes
    are decorated with missing attributes and methods. When a name
    attribute is provided the class is registered into a global map
    of XSD atomic types and also the expanded name is added.
    """
    def __new__(mcs, class_name: str, bases: tuple[type[Any], ...], dict_: dict[str, Any]) \
            -> 'AtomicTypeMeta':
        try:
            name = dict_['name']
        except KeyError:
            name = dict_['name'] = None  # do not inherit name

        if name is not None and not isinstance(name, (str, Property)):
            raise TypeError("attribute 'name' must be a string or None")

        cls = super(AtomicTypeMeta, mcs).__new__(mcs, class_name, bases, dict_)

        # Register all the derived classes with a valid name if not already registered
        if name:
            if isinstance(name, Property):
                name = name.value

            namespace: str | None = dict_.pop('namespace', XSD_NAMESPACE)
            prefix: str | None =  dict_.pop('prefix', 'xs')

            extended_name = f'{{{namespace}}}{name}' if namespace else name
            prefixed_name = f'{prefix}:{name}' if prefix else name

            if extended_name not in _builtin_atomic_types:
                _builtin_atomic_types[extended_name] = cls
            if prefixed_name not in _atomic_sequence_types:
                _atomic_sequence_types[prefixed_name] = cls

        return cls

    def __repr__(self) -> str:
        if self.__qualname__.startswith('elementpath.datatypes._'):
            return f"<class 'elementpath.datatypes.{self.__name__}'>"
        return super().__repr__()


class AnyAtomicType(metaclass=AtomicTypeMeta):

    name: Optional[str] = Property[str]('anyAtomicType')

    xsd_version: str = '1.0'
    pattern = LazyPattern(r'^$')

    __slots__ = ()

    @classmethod
    def make(cls, value: Any,
             version: str = '2.0',
             xsd_version: str = '1.1') -> 'AnyAtomicType':
        """
        Versioned factory method to create an atomic type.

        :param value: the value to be converted to an atomic type.
        :param version: the version of the XPath processor that create the atomic type.
        :param xsd_version: the version of the XSD processor that create the atomic type.
        """
        return cls(value)

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

    # noinspection PyAbstractClass
    @abstractmethod
    def __init__(self, value: Any) -> None:
        raise NotImplementedError()
