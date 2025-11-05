#
# Copyright (c), 2025-2025, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""Type annotation aliases for elementpath."""
from collections.abc import MutableMapping
from decimal import Decimal
from typing import Any, Optional, NoReturn, TYPE_CHECKING, TypeVar, Union

if TYPE_CHECKING:
    from .protocols import ElementProtocol, DocumentProtocol  # noqa: F401
    from .protocols import XsdElementProtocol, XsdAttributeProtocol  # noqa: F401
    from .protocols import DocumentType, ElementType, SchemaElemType  # noqa: F401
    from .datatypes import AnyAtomicType, AbstractDateTime  # noqa: F401
    from .datatypes import Duration, UntypedAtomic  # noqa: F401
    from .xpath_nodes import XPathNode, ElementNode, AttributeNode  # noqa: F401
    from .xpath_nodes import TextNode, DocumentNode, NamespaceNode  # noqa: F401
    from .xpath_nodes import CommentNode, ProcessingInstructionNode  # noqa: F401
    from .xpath_tokens import XPathToken, XPathAxis, XPathFunction  # noqa: F401
    from .xpath_tokens import XPathConstructor, XPathMap, XPathArray  # noqa: F401
    from .xpath_context import XPathContext, XPathSchemaContext  # noqa: F401
    from .xpath1 import XPath1Parser  # noqa: F401
    from .xpath2 import XPath2Parser  # noqa: F401
    from .xpath30 import XPath30Parser  # noqa: F401
    from .xpath31 import XPath31Parser  # noqa: F401

###
# Namespace maps
NamespacesType = MutableMapping[str, str]
NsmapType = MutableMapping[Optional[str], str]  # compatible with the nsmap of lxml Element
AnyNsmapType = Union[NamespacesType, NsmapType, None]  # for composition and function arguments

###
# Datatypes
AtomicType = Union[str, int, float, Decimal, bool, 'AnyAtomicType']
NumericType = Union[int, float, Decimal]
ArithmeticType = Union[NumericType, 'AbstractDateTime', 'Duration', 'UntypedAtomic']

###
# Sequence and item/value types
_T = TypeVar('_T')

Emptiable = Union[_T, list[NoReturn], tuple[()]]
SequenceType = Union[_T, list[_T], tuple[_T, ...]]
UnionType = Union[_T, list[_T], tuple[_T, ...]]
InputType = Union[None, _T, list[_T], tuple[_T, ...]]

ItemType = Union['XPathNode', AtomicType, 'XPathFunction']
ValueType = Union[ItemType, tuple[ItemType, ...], list[ItemType]]
ResultType = Union[
    AtomicType, 'ElementProtocol', 'XsdAttributeProtocol', tuple[Optional[str], str],
    'DocumentProtocol', 'DocumentNode', 'XPathFunction', object
]
MapDictType = dict[Optional[AtomicType], ValueType]
SequenceTypesType = Union[str, list[str], tuple[str, ...]]

# Parsers and tokens
XPathParserType = Union['XPath1Parser', 'XPath2Parser', 'XPath30Parser', 'XPath31Parser']
XPathTokenType = Union['XPathToken', 'XPathAxis', 'XPathFunction', 'XPathConstructor']
XPath2ParserType = Union['XPath2Parser', 'XPath30Parser', 'XPath31Parser']
ParserClassType = Union[
    type['XPath1Parser'], type['XPath2Parser'], type['XPath30Parser'], type['XPath31Parser']
]
NargsType = Optional[Union[int, tuple[int, Optional[int]]]]
ClassCheckType = Union[type[Any], tuple[type[Any], ...]]


# XPath nodes
TypedNodeType = Union['AttributeNode', 'ElementNode']
TaggedNodeType = Union['ElementNode', 'CommentNode', 'ProcessingInstructionNode']
ElementMapType = dict[object, TaggedNodeType]
FindAttrType = Optional['XsdAttributeProtocol']
FindElemType = Optional['XsdElementProtocol']
XPathNodeType = Union['DocumentNode', 'NamespaceNode', 'AttributeNode', 'TextNode',
                      'ElementNode', 'CommentNode', 'ProcessingInstructionNode']
RootNodeType = Union['DocumentNode', 'ElementNode']

ParentNodeType = Union['DocumentNode', 'ElementNode']
ChildNodeType = Union['TextNode', TaggedNodeType]

# Context arguments
ContextType = Union['XPathContext', 'XPathSchemaContext', None]
RootArgType = Union['DocumentType', 'ElementType', 'SchemaElemType', RootNodeType]
ItemArgType = Union[ItemType, 'ElementProtocol', 'DocumentProtocol']
FunctionArgType = Union[InputType[ItemArgType], ValueType]
NodeArgType = Union['XPathNode', 'ElementProtocol', 'DocumentProtocol']
CollectionArgType = Optional[InputType[NodeArgType]]
