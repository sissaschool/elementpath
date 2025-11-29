#
# Copyright (c), 2018-2025, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from collections.abc import Callable, Iterable, Iterator, Sequence
from itertools import zip_longest
from typing import Any, NoReturn, overload, TypeVar, Union

from elementpath.aliases import ValueType

__all__ = ['XSequence', 'empty_sequence', 'flattened_items',
           'sequence_concat', 'count', 'iterate_sequence']


T = TypeVar('T', bound=ValueType)
S = TypeVar('S')

SeqCompType = Union['XSequence[T]', list[T], tuple[T]]


class XSequence(Sequence[T]):
    """
    Class for representing XQuery/XPath sequences, as defined by XQuery and XPath Data Model 4.0.
    Used for internal processing, results are converted to a list.

    Ref: https://qt4cg.org/specifications/xpath-datamodel-40/Overview.html
    """
    __slots__ = ('_items',)

    def __init__(self, items: Iterable[T] = ()) -> None:
        self._items = tuple(flattened_items(items))

    def __str__(self) -> str:
        return f'({", ".join(map(repr, self._items))})'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({", ".join(map(repr, self._items))})'

    def __hash__(self) -> int:
        return hash(self._items)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, XSequence):
            return self._items == other._items
        elif isinstance(other, tuple):
            return self._items == other
        elif isinstance(other, list):
            return all(i1 == i2 for i1, i2 in zip_longest(self._items, other))
        return False if len(self) != 1 else not self[0] != other

    def __ne__(self, other: Any) -> bool:
        if isinstance(other, XSequence):
            return self._items != other._items
        elif isinstance(other, tuple):
            return self._items != other
        elif isinstance(other, list):
            return any(i1 != i2 for i1, i2 in zip_longest(self, other))
        return True if len(self) != 1 else not self[0] == other

    def __getitem__(self, item):
        return self._items[item]

    def __iter__(self) -> Iterator[T]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    @overload
    def __add__(self, other: 'XSequence[T]') -> 'XSequence[T]': ...

    @overload
    def __add__(self, other: tuple[T]) -> tuple[T]: ...

    @overload
    def __add__(self, other: list[T]) -> list[T]: ...

    @overload
    def __add__(self, other: 'XSequence[S]') -> 'XSequence[S | T]': ...

    @overload
    def __add__(self, other: tuple[S]) -> tuple[S | T]: ...

    @overload
    def __add__(self, other: list[S]) -> list[S | T]: ...

    def __add__(self, other: SeqCompType[S] | SeqCompType[T]) -> SeqCompType[S | T]:
        if isinstance(other, list):
            return list(self._items) + other
        elif isinstance(other, tuple):
            return self._items + other
        elif isinstance(other, XSequence):
            return self._items + other._items
        return NotImplemented

    def __radd__(self, other: tuple[S] | list[S]) -> tuple[T | S] | list[S | T]:
        if isinstance(other, list):
            return other + list(self._items)
        elif isinstance(other, tuple):
            return other + self._items
        return NotImplemented

    @property
    def sequence_type(self) -> str:
        if not self:
            return 'empty-sequence()'
        elif len(self) == 1:
            return 'item()'
        else:
            return 'item()*'


def flattened_items(items: Iterable[T]) -> Iterator[T]:
    for item in items:
        if isinstance(item, XSequence):
            yield from item
        else:
            yield item


_empty_sequence = XSequence()


###
# XDM 4.0 constructors and accessors.
def empty_sequence() -> XSequence[NoReturn]:
    return _empty_sequence


def sequence_concat(s1: XSequence[T] | XSequence[NoReturn],
                    s2: XSequence[T] | XSequence[NoReturn]) -> XSequence[T] | XSequence[NoReturn]:
    match len(s1) + len(s2):
        case 0:
            return _empty_sequence
        case 1:
            return s1 or s2
        case _:
            return XSequence(s1 + s2)


def count(seq: XSequence[Any]) -> int:
    return len(seq)


def iterate_sequence(seq: XSequence[T], action: Callable[[T, int], XSequence[T]]) -> XSequence[T]:
    items: list[T] = []
    for position, item in enumerate(seq, start=1):
        items.extend(action(item, position))
    return XSequence(items)
