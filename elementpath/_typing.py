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
Version related imports for subscriptable types for type annotations.
"""
import sys
from typing import Any, cast, ClassVar, Generic, Hashable, ItemsView, Optional, \
    NoReturn, Protocol, Sized, SupportsFloat, TYPE_CHECKING, Tuple, Type, \
    TypeVar, Union

if sys.version_info < (3, 9):
    from typing import Callable, Counter, Deque, Dict, List, Iterable, Iterator, \
        Mapping, Match, MutableMapping, MutableSequence, Pattern, Sequence, Set
else:
    from collections import deque, Counter
    from collections.abc import Callable, Iterable, Iterator, Mapping, MutableMapping, \
        MutableSequence, Sequence
    from re import Match, Pattern

    Deque = deque
    Dict = dict
    List = list
    Set = set

Never = NoReturn

__all__ = ['Any', 'Callable', 'cast', 'ClassVar', 'Counter', 'Deque', 'Dict', 'Generic',
           'Hashable', 'Iterable', 'ItemsView', 'Iterator', 'List', 'Match',
           'Mapping', 'MutableMapping', 'MutableSequence', 'Never', 'Optional',
           'Pattern', 'Protocol', 'Sequence', 'Set', 'Sized', 'SupportsFloat',
           'Union', 'Tuple', 'Type', 'TYPE_CHECKING', 'TypeVar']
