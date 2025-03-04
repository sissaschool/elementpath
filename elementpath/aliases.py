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
Common type hints aliases for elementpath.
"""
from typing import Any, Optional, NoReturn, TYPE_CHECKING, TypeVar, Union

from collections.abc import MutableMapping

##
# type aliases
NamespacesType = MutableMapping[str, str]
NsmapType = MutableMapping[Optional[str], str]  # compatible with the nsmap of lxml Element
AnyNsmapType = Union[NamespacesType, NsmapType, None]  # for composition and function arguments

NargsType = Optional[Union[int, tuple[int, Optional[int]]]]
ClassCheckType = Union[type[Any], tuple[type[Any], ...]]

T = TypeVar('T')
Emptiable = Union[T, list[NoReturn]]
SequenceType = Union[T, list[T]]
InputType = Union[None, T, list[T], tuple[T, ...]]

if TYPE_CHECKING:
    from elementpath.datatypes import AtomicType, ArithmeticType, NumericType
    from elementpath.xpath_nodes import ChildNodeType, ParentNodeType, RootArgType
    from elementpath.xpath_context import ContextType, FunctionArgType, ItemType, \
        ItemArgType, ValueType
    from elementpath.xpath_tokens import XPathParserType, XPathTokenType

__all__ = ['NamespacesType', 'NsmapType', 'AnyNsmapType', 'NargsType',
           'ClassCheckType', 'Emptiable', 'SequenceType', 'InputType',
           'AtomicType', 'ArithmeticType', 'NumericType', 'ChildNodeType',
           'ParentNodeType', 'RootArgType', 'ContextType', 'FunctionArgType',
           'ItemType', 'ItemArgType', 'ValueType', 'XPathParserType', 'XPathTokenType']
