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
from typing import Any, Optional, Tuple, Type, Union

if sys.version_info < (3, 9):
    from typing import Dict, List, MutableMapping, MutableSequence, Set
else:
    from collections.abc import MutableMapping, MutableSequence

    Dict = dict
    List = list
    Set = set

NamespacesType = MutableMapping[str, str]
NsmapType = MutableMapping[Optional[str], str]  # compatible with the nsmap of lxml Element
AnyNsmapType = Union[NamespacesType, NsmapType, None]  # for composition and function arguments

NargsType = Optional[Union[int, Tuple[int, Optional[int]]]]
ClassCheckType = Union[Type[Any], Tuple[Type[Any], ...]]

__all__ = ['MutableMapping', 'MutableSequence', 'Dict', 'List', 'Set', 'NamespacesType',
           'NsmapType', 'AnyNsmapType', 'NargsType', 'ClassCheckType']
