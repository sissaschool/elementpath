#
# Copyright (c), 2018-2025, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from collections.abc import Callable, Sequence, Iterable  # noqa: F401
from typing import Any, overload, TypeVar, NoReturn, Iterator, Union

from elementpath.aliases import ItemType, SequenceType, SequenceArgType  # noqa: F401

__all__ = ['XPathSequence', 'SingletonSequence', 'EmptySequence',
           'empty_sequence', 'to_sequence', 'iter_sequence']

T = TypeVar('T', bound=ItemType)
T1 = TypeVar('T1', bound=ItemType)
T2 = TypeVar('T2', bound=ItemType)


class XPathSequence(Sequence[T]):
    """
    A class for representing a sequence of XPath items, as defined by XQuery and
    XPath Data Model 4.0. This is derived from <class 'list'> for interoperability,
    but it's intended to be immutable and for internal processing.

    Ref: https://qt4cg.org/specifications/xpath-datamodel-40/Overview.html
    """
    _items: tuple[T, ...] | tuple[T] | tuple[()]
    __slots__ = ('_items',)

    def __new__(cls, items: tuple[T, ...] | tuple[T] | tuple[()]) -> 'XPathSequence[T]':
        obj = super().__new__(cls)
        obj._items = items
        return obj

    def __str__(self) -> str:
        return f'({", ".join(map(repr, self))})'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({", ".join(map(repr, self))})'

    @overload
    def __getitem__(self, index: int, /) -> T: ...

    @overload
    def __getitem__(self, index: slice,/ ) -> tuple[T, ...] | tuple[T] | tuple[()]: ...

    def __getitem__(self, index: int | slice) -> T | tuple[T, ...] | tuple[T] | tuple[()]:
        return self._items[index]

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[T]:
        return iter(self._items)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, XPathSequence):
            return self._items == other._items
        elif isinstance(other, tuple):
            return self._items == other
        elif isinstance(other, list):
            return self._items == tuple(other)
        return False if len(self._items) != 1 else not self._items != other

    def __ne__(self, other: Any) -> bool:
        if isinstance(other, XPathSequence):
            return self._items != other._items
        elif isinstance(other, tuple):
            return self._items != other
        elif isinstance(other, list):
            return self._items != tuple(other)
        return True if len(self._items) != 1 else not self._items == other

    def __add__(self, other: 'SequenceType[T] | list[T] | tuple[T, ...]') -> 'SequenceType[T]':
        if isinstance(other, XPathSequence):
            return to_sequence(self._items + other[:])
        elif isinstance(other, (tuple, list)):
            return to_sequence(self._items + tuple(other))
        return NotImplemented

    def __radd__(self, other: list[T] | tuple[T, ...]) -> 'SequenceType[T]':
        if isinstance(other, (tuple, list)):
            return to_sequence(self._items + tuple(other))
        return NotImplemented

    ###
    # XDM 4.0 constructors and accessors.
    @staticmethod
    def empty_sequence() -> 'EmptySequence':
        return EmptySequence()

    @staticmethod
    def sequence_concat(s1: 'XPathSequence[T]', s2: 'XPathSequence[T]') -> 'SequenceType[T]':
        items: tuple[T, ...] | tuple[T] | tuple[()] = s1._items + s2._items
        if not items:
            return EmptySequence()
        elif len(items) == 1:
            return SingletonSequence(items)
        else:
            return XPathSequence(items)

    @classmethod
    def count(cls, seq: 'XPathSequence[T1]') -> int:
        return len(seq._items)

    @staticmethod
    def iterate_sequence(seq: 'SequenceType[T]',
                         action: 'Callable[[T, int], SequenceType[T]]') \
            -> 'SequenceType[T]':
        items: list[T] = []
        for position, item in enumerate(seq, start=1):
            items.extend(action(item, position))

        if not items:
            return EmptySequence()
        elif len(items) == 1:
            return SingletonSequence((items[0],))
        else:
            return XPathSequence(tuple(items))


class SingletonSequence(XPathSequence[T]):
    """A sequence with only one item as defined by XDM 4.0."""
    _items: tuple[T]
    __slots__ = ()

    def __new__(cls, items: tuple[T]) -> 'SingletonSequence[T]':
        if len(items) != 1:
            raise ValueError(f"{type(items)!r} accepts exactly one item")
        obj = object.__new__(cls)
        obj._items = items
        return obj

    def __len__(self) -> int:
        return 1

    def __iter__(self) -> Iterator[T]:
        yield self._items[0]

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, SingletonSequence):
            return self._items == other._items
        elif isinstance(other, tuple):
            return self._items == other
        elif isinstance(other, list):
            return len(other) == 1 and self._items[0] == other[0]
        return not self._items[0] != other

    def __ne__(self, other: Any) -> bool:
        if isinstance(other, SingletonSequence):
            return self._items != other._items
        elif isinstance(other, tuple):
            return self._items != other
        elif isinstance(other, list):
            return len(other) != 1 or self._items[0] != other[0]
        return not self._items[0] == other


class EmptySequence(XPathSequence[NoReturn]):
    """An empty sequence, that is processes as a singleton with no values."""
    _items: tuple[()]
    __slots__ = ()

    def __new__(cls) -> 'EmptySequence':
        try:
            return empty_sequence
        except NameError:
            obj = object.__new__(cls)
            obj._items = ()
            return obj

    def __len__(self) -> int:
        return 0

    def __eq__(self, other: Any) -> bool:
        return not other and isinstance(other, (EmptySequence, list, tuple, None.__class__))

    def __ne__(self, other: Any) -> bool:
        return other or not isinstance(other, (EmptySequence, list, tuple, None.__class__))


empty_sequence = EmptySequence()  # The empty sequence as a singleton


def to_sequence(items: SequenceArgType[T] = ()) -> 'SequenceType[T]':
    """
    Main constructor that returns an instance of the appropriate subclass, \
    depending on the number of items.
    """
    items = tuple(items)
    if any(isinstance(x, XPathSequence) for x in items):
        raise ValueError(f"a sequence instance cannot contain other sequences")

    if not items:
        try:
            return empty_sequence
        except NameError:
            return EmptySequence()
    elif len(items) == 1:
        return SingletonSequence(items)
    else:
        return XPathSequence(items)


def iter_sequence(obj: Any) -> Iterator[Any]:
    if obj is None:
        return
    elif isinstance(obj, list):
        for item in obj:
            yield from iter_sequence(item)
    else:
        yield obj
