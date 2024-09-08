#
# Copyright (c), 2021, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""
Imports for subscriptable types and common type hints aliases.
"""
import sys
from typing import Any, Optional, NoReturn, Tuple, Type, TypeVar, Union

if sys.version_info < (3, 9):
    from typing import Deque, Dict, List, Mapping, MutableMapping, MutableSequence, Sequence, Set
else:
    from collections import deque
    from collections.abc import Mapping, MutableMapping, MutableSequence, Sequence

    Deque = deque
    Dict = dict
    List = list
    Set = set

Never = NoReturn

NamespacesType = MutableMapping[str, str]
NsmapType = MutableMapping[Optional[str], str]  # compatible with the nsmap of lxml Element
AnyNsmapType = Union[NamespacesType, NsmapType, None]  # for composition and function arguments

NargsType = Optional[Union[int, Tuple[int, Optional[int]]]]
ClassCheckType = Union[Type[Any], Tuple[Type[Any], ...]]

T = TypeVar('T')
Emptiable = Union[T, List[Never]]
Listable = Union[T, List[T]]
InputData = Union[None, T, List[T], Tuple[T, ...]]

__all__ = ['Mapping', 'MutableMapping', 'MutableSequence', 'Sequence', 'Dict', 'List',
           'Set', 'Never', 'NamespacesType', 'NsmapType', 'AnyNsmapType', 'NargsType',
           'ClassCheckType', 'Emptiable', 'Listable', 'InputData', 'Deque']
