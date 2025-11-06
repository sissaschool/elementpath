#
# Copyright (c), 2018-2025, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from collections.abc import Callable, Sequence  # noqa: F401
from typing import Any, TypeVar, NoReturn, overload

from elementpath.aliases import ItemType, SequenceType  # noqa: F401

__all__ = ['XPathSequence', 'EmptySequence', 'empty_sequence',
           'FullSequence', 'SingletonSequence']

T = TypeVar('T', bound=ItemType)
T1 = TypeVar('T1', bound=ItemType)
T2 = TypeVar('T2', bound=ItemType)


class XPathSequence(Sequence[T]):
    """
    A class for representing a sequence of XPath items. This is a generalization
    introduced with XPath 4.0 (draft).
    """
    items: list[T]

    @classmethod
    def from_items(cls, items: list[T]) -> 'SequenceType[T]':
        if not items:
            try:
                return empty_sequence
            except NameError:
                return object.__new__(EmptySequence)
        elif len(items) == 1:
            singleton = object.__new__(SingletonSequence)
            singleton.item = items[0]
            return singleton
        else:
            sequence = object.__new__(FullSequence)
            sequence.items = items
            return sequence

    def __str__(self) -> str:
        return f'({str(self.items)[1:-1]})'

    def __repr__(self) -> str:
        return self.__str__()

    ###
    # XDM 4.0 constructors and accessors.
    @classmethod
    def empty_sequence(cls) -> 'EmptySequence':
        return EmptySequence()

    @classmethod
    def sequence_concat(cls, s1: 'SequenceType[T]', s2: 'SequenceType[T2]') \
            -> 'SequenceType[T] | SequenceType[T2] | FullSequence[T | T2]':
        if isinstance(s2, EmptySequence):
            return s1
        elif isinstance(s1, EmptySequence):
            return s2
        else:
            return FullSequence(s1.items + s2.items)

    @classmethod
    def count(cls, seq: 'XPathSequence[T1]') -> int:
        return len(seq)

    @classmethod
    def iterate_sequence(cls, seq: 'SequenceType[T1]',
                         action: 'Callable[[T1, int], SequenceType[T2]]') \
            -> 'SequenceType[T1 | T2]':
        items: list[T2] = []
        for position, item in enumerate(seq.items, start=1):
            items.extend(action(item, position).items)

        if not items:
            return empty_sequence
        elif len(items) == 1:
            singleton = object.__new__(SingletonSequence)
            singleton.item = items[0]
            return singleton
        else:
            sequence = object.__new__(FullSequence)
            sequence.items = items
            return sequence

    def __add__(self, other: 'SequenceType[T1] | list[T1] | Any') \
            -> 'SequenceType[T | T1]':
        if isinstance(other, XPathSequence):
            return XPathSequence[T | T1].from_items(self.items + other.items)
        elif isinstance(other, list):
            return XPathSequence[T | T1].from_items(self.items + other)
        return NotImplemented

    def __radd__(self, other: list[T1] | Any) -> 'SequenceType[T | T1]':
        if isinstance(other, list):
            return XPathSequence[T | T1].from_items(other + self.items)
        return NotImplemented

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, XPathSequence):
            return self.items == other.items
        elif isinstance(other, list):
            return self.items == other
        return False

    def __ne__(self, other: Any) -> bool:
        if isinstance(other, XPathSequence):
            return self.items != other.items
        elif isinstance(other, list):
            return self.items != other
        return True


class EmptySequence(XPathSequence[NoReturn]):
    """An empty sequence, that is processes as a singleton with no values."""
    __slots__ = ()

    def __new__(cls) -> 'EmptySequence':
        try:
            return empty_sequence
        except NameError:
            return object.__new__(EmptySequence)

    @property
    def item(self) -> None:
        return None

    @property
    def items(self) -> list[NoReturn]:
        return []

    @items.setter
    def items(self, items: list[NoReturn] | Any) -> None:
        if not isinstance(items, list):
            raise TypeError(f'items must be an empty list not {type(items)}')
        if items:
            raise ValueError(f'cannot set {self!r} items with a not empty sequence')

    def __str__(self) -> str:
        return '()'

    def __len__(self) -> int:
        return 0

    @overload
    def __getitem__(self, index: int) -> NoReturn: ...

    @overload
    def __getitem__(self, index: slice) -> list[NoReturn]: ...

    def __getitem__(self, index: int | slice) -> NoReturn | list[NoReturn]:
        return [][index]

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, (EmptySequence, tuple, list)) and len(other) == 0

    def __ne__(self, other: Any) -> bool:
        return not isinstance(other, (EmptySequence, tuple, list)) or len(other) != 0


empty_sequence = EmptySequence()  # The empty sequence as a singleton


class SingletonSequence(XPathSequence[T]):
    """A singleton sequence."""
    __slots__ = ('item',)
    item: T

    def __init__(self, item: T) -> None:
        self.item = item

    def __len__(self) -> int:
        return 1

    @overload
    def __getitem__(self, index: int) -> T: ...

    @overload
    def __getitem__(self, index: slice) -> list[T] | list[NoReturn]: ...

    def __getitem__(self, index: int | slice) -> T | list[T] | list[NoReturn]:
        return self.item if index == 0 else [self.item][index]

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, SingletonSequence):
            return bool(self.item == other.item)
        elif isinstance(other, list):
            return len(other) == 1 and self.item == other[0]
        return bool(self.items[0] == other)

    def __ne__(self, other: object) -> bool:
        if isinstance(other, list):
            return len(other) != 1 or self.item != other[0]
        return self.item != other

    @property
    def items(self) -> list[T]:
        return [self.item]

    @items.setter
    def items(self, items: list[T] | Any) -> None:
        if not (isinstance(items, list)):
            raise TypeError(f'items must be a list, not {type(items)}')
        if len(items) != 1:
            raise ValueError(f'cannot set {self!r} items with a list with more than one item')
        self.item = items[0]


class FullSequence(XPathSequence[T]):
    """A sequence with two or more items."""
    items: list[T]

    __slots__ = ('items',)

    def __init__(self, items: list[T]) -> None:
        self.items = items

    def __len__(self) -> int:
        return len(self.items)

    @overload
    def __getitem__(self, index: int) -> T: ...

    @overload
    def __getitem__(self, index: slice) -> list[T] | list[NoReturn]: ...

    def __getitem__(self, index: int | slice) -> T | list[T] | list[NoReturn]:
        return self.items[index]
