#
# Copyright (c), 2018-2025, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from collections.abc import Callable, Iterable
from typing import Any, NoReturn, overload, TypeVar, Union

from elementpath.aliases import ItemType

__all__ = ['xlist', 'XSequence', 'empty_sequence', 'sequence_concat', 'count', 'iterate_sequence']


T = TypeVar('T', bound=ItemType)
S = TypeVar('S')

SequenceArgItemType = Union[T, list[T], Iterable[T], tuple[T, ...]]


class xlist(list[T]):
    """An extended list type for processing XQuery/XPath sequences."""
    __slots__ = ()

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, list):
            return super().__eq__(other)
        return False if len(self) != 1 else not self[0] != other

    def __ne__(self, other: Any) -> bool:
        if isinstance(other, list):
            return super().__ne__(other)
        return True if len(self) != 1 else not self[0] == other


class XSequence(list[T]):
    """
    An extended list derived class for processing XQuery/XPath sequences.

    Ref: https://qt4cg.org/specifications/xpath-datamodel-40/Overview.html
    """
    __slots__ = ()

    def __init__(self, items: Iterable[T] = ()) -> None:
        super().__init__(items)
        if any(isinstance(x, list) for x in self):
            raise TypeError(f"{self!r} initialized with a nested sequence")

    def __str__(self) -> str:
        return f'({", ".join(map(repr, self))})'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}([{", ".join(map(repr, self))}])'

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, list):
            return super().__eq__(other)
        return False if len(self) != 1 else not self[0] != other

    def __ne__(self, other: Any) -> bool:
        if isinstance(other, list):
            return super().__ne__(other)
        return True if len(self) != 1 else not self[0] == other

    @overload
    def __add__(self, other: list[T] | list[NoReturn]) -> list[T]: ...

    @overload
    def __add__(self, other: list[S] | list[NoReturn]) -> list[S | T]: ...

    def __add__(self, other: list[S] | list[NoReturn]) -> list[S | T] | list[T]:
        if isinstance(other, list):
            return list(self) + other
        return NotImplemented

    def __radd__(self, other: list[S] | list[NoReturn]) -> list[S | T]:
        if isinstance(other, list):
            return other + list(self)
        return NotImplemented

    @property
    def sequence_type(self) -> str:
        if not self:
            return 'empty-sequence()'
        elif len(self) == 1:
            return 'item()'
        else:
            return 'item()*'


_empty_sequence: XSequence[NoReturn] = XSequence()  # Empty sequence as a singleton


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
