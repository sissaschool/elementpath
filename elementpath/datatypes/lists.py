#
# Copyright (c), 2018-2025, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from abc import abstractmethod
from typing import Any

from .any_types import AnySimpleType, AnyAtomicType
from .untyped import UntypedAtomic
from .string import NMToken, Idref, Entity

__all__ = ['AbstractListType', 'NMTokens', 'Idrefs', 'Entities']


class AbstractListType(AnySimpleType):
    obj: list[AnyAtomicType]
    item_type: type['AnyAtomicType']

    __slots__ = ('item_type',)

    @abstractmethod
    def __init__(self, obj: Any) -> None:
        raise NotImplementedError()

    @classmethod
    def validate(cls, obj: object) -> None:
        if isinstance(obj, cls):
            return
        elif not isinstance(obj, list) or \
                any(not isinstance(item, AnyAtomicType) for item in obj):
            raise cls.invalid_type(obj)
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
            raise cls.invalid_type(value)

        try:
            return [cls.item_type(x) for x in values]
        except ValueError:
            raise cls.invalid_value(value)


###
# Builtin list types

class NMTokens(AbstractListType):
    name = 'NMTOKENS'
    items: list[NMToken]
    item_type: type[NMToken] = NMToken


class Idrefs(AbstractListType):
    name = 'IDREFS'
    items: list[Idref]
    item_type: type[Idref] = NMToken


class Entities(AbstractListType):
    name = 'ENTITIES'
    items: list[Entity]
    item_type: type[Entity] = Entity
