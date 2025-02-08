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
from typing import Any, List, Optional, NoReturn, Tuple, Type, TYPE_CHECKING, TypeVar, Union

from elementpath._typing import MutableMapping

##
# Type aliases
NamespacesType = MutableMapping[str, str]
NsmapType = MutableMapping[Optional[str], str]  # compatible with the nsmap of lxml Element
AnyNsmapType = Union[NamespacesType, NsmapType, None]  # for composition and function arguments

NargsType = Optional[Union[int, Tuple[int, Optional[int]]]]
ClassCheckType = Union[Type[Any], Tuple[Type[Any], ...]]

T = TypeVar('T')
Emptiable = Union[T, List[NoReturn]]
SequenceType = Union[T, List[T]]
InputType = Union[None, T, List[T], Tuple[T, ...]]

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
