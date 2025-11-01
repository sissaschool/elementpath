#
# Copyright (c), 2018-2025, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from collections.abc import MutableSequence
from types import MappingProxyType
from typing import Any

from .any_types import AtomicTypeMeta, AnySimpleType, AnyAtomicType
from .untyped import UntypedAtomic
from .string import NMToken, Idref, Entity

__all__ = ['builtin_list_types', 'ListType', 'NMTokens', 'Idrefs', 'Entities']


_builtin_list_types: dict[str, type] = {}
builtin_list_types = MappingProxyType(_builtin_list_types)
"""Registry of builtin list types by expanded name."""


class ListTypeMeta(AtomicTypeMeta):
    types_map = _builtin_list_types


class ListType(MutableSequence, AnySimpleType, metaclass=ListTypeMeta):
    value: list[AnyAtomicType]
    item_type: type[AnyAtomicType]

    __slots__ = ('value', 'item_type')

    def __init__(self, value: list[AnyAtomicType],
                 item_type: type[AnyAtomicType]) -> None:
        self.value = value
        self.item_type = item_type

    def __getitem__(self, index: int) -> AnyAtomicType:
        return self.value[index]

    def __setitem__(self, index: int, value: AnyAtomicType) -> None:
        self.value[index] = value

    def __delitem__(self, index: int) -> None:
        del self.value[index]

    def __len__(self) -> int:
        return len(self.value)

    def insert(self, index: int, value: AnyAtomicType) -> None:
        self.value.insert(index, value)

    @classmethod
    def validate(cls, obj: object) -> None:
        if isinstance(obj, cls):
            return
        elif not isinstance(obj, list) or \
                any(not isinstance(item, AnyAtomicType) for item in obj):
            raise cls._invalid_type(obj)
        else:
            for item in obj:
                cls.item_type.validate(item)

    @classmethod
    def decode(cls, value: Any) -> list['AnyAtomicType']:
        if isinstance(value, UntypedAtomic):
            values = value.value.split() or ['']
        elif isinstance(value, str):
            values = value.split() or ['']
        elif isinstance(value, list):
            values = value
        else:
            raise cls._invalid_type(value)

        try:
            return [cls.item_type(x) for x in values]
        except ValueError:
            raise cls._invalid_value(value)


###
# Builtin list types

class NMTokens(ListType):
    name = 'NMTOKENS'
    items: list[NMToken]
    item_type: type[NMToken] = NMToken


class Idrefs(ListType):
    name = 'IDREFS'
    items: list[Idref]
    item_type: type[Idref] = NMToken


class Entities(ListType):
    name = 'ENTITIES'
    items: list[Entity]
    item_type: type[Entity] = Entity
