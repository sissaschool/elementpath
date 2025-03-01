#
# Copyright (c), 2018-2022, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import importlib
from collections import deque
from urllib.parse import urljoin
from typing import cast, Any, Dict, List, Optional, Tuple, TYPE_CHECKING, Union
from xml.etree import ElementTree

from elementpath._typing import Deque, Iterator
from elementpath.exceptions import ElementPathRuntimeError, \
    ElementPathValueError, ElementPathKeyError
from elementpath.aliases import NamespacesType, NsmapType, SequenceType
from elementpath.datatypes import UntypedAtomic, AtomicType, AnyURI, QName
from elementpath.namespaces import XML_NAMESPACE, XML_BASE, XSI_NIL, \
    XSD_ANY_TYPE, XSD_ANY_SIMPLE_TYPE, XSD_ANY_ATOMIC_TYPE, XSI_TYPE, \
    XML_ID, XSD_IDREF, XSD_IDREFS, XSD_UNTYPED, XSD_UNTYPED_ATOMIC, \
    XPATH_FUNCTIONS_NAMESPACE, get_expanded_name
from elementpath.protocols import ElementProtocol, XsdElementProtocol, \
    XsdAttributeProtocol, XsdTypeProtocol, DocumentType, ElementType, \
    SchemaElemType, CommentType, ProcessingInstructionType
from elementpath.helpers import match_wildcard, is_absolute_uri
from elementpath.decoder import get_atomic_sequence
from elementpath.etree import etree_iter_strings, is_etree_element_instance

if TYPE_CHECKING:
    from elementpath.schema_proxy import AbstractSchemaProxy

__all__ = ['TypedNodeType', 'ParentNodeType', 'ChildNodeType', 'ElementMapType',
           'XPathNode', 'NamespaceNode', 'AttributeNode', 'TextAttributeNode',
           'SchemaAttributeNode', 'TextNode', 'CommentNode', 'ProcessingInstructionNode',
           'ElementNode', 'EtreeElementNode', 'LazyElementNode', 'SchemaElementNode',
           'DocumentNode', 'EtreeDocumentNode', 'RootNodeType', 'RootArgType']

_EMPTY_NAME_PATH = f'*[Q{{{XPATH_FUNCTIONS_NAMESPACE}}}local-name()=""]'

_XSD_SPECIAL_TYPES = {XSD_ANY_TYPE, XSD_ANY_SIMPLE_TYPE, XSD_ANY_ATOMIC_TYPE}

TypedNodeType = Union['AttributeNode', 'ElementNode']
ParentNodeType = Union['DocumentNode', 'ElementNode']
ChildNodeType = Union['TextNode', 'ElementNode', 'CommentNode', 'ProcessingInstructionNode']
ElementMapType = Dict[ElementType, 'ElementNode']


# TODO for v5.0: use an internal shared object for storing same data once. This
#   will replace position argument and some attributes in element nodes. Position
#   argument will be kept only for namespace and attribute nodes.
class XPathNodeTree:
    """
    Status of the node tree structure, shared between nodes.
    """
    root: ParentNodeType
    elements: ElementMapType
    namespaces: NamespacesType
    schema: Optional['AbstractSchemaProxy']
    uri: Optional[str]
    total: int

    __slots__ = ('root', 'namespaces', 'uri', 'elements', 'schema', 'total')

    def __init__(self, root: ParentNodeType,
                 namespaces: Optional[NamespacesType] = None,
                 uri: Optional[str] = None) -> None:
        self.root = root
        self.namespaces = namespaces if namespaces is not None else {}
        self.uri = uri
        self.elements = {}
        self.schema = None
        self.total = 1


###
# XQuery and XPath Data Model: https://www.w3.org/TR/xpath-datamodel/
#
# Note: in this implementation empty sequence return value is replaced by None.
#
# XPath has seven kinds of nodes:
#
#  element, attribute, text, namespace, processing-instruction, comment, document
###
class XPathNode:
    """
    The base class of all XPath nodes. In the base class and in other intermediate
    derivation string and typed values are not implemented. Use these classes only
    for type checking and for wrapping other types in a custom XPath node types.
    """
    __slots__ = ('name', 'obj', 'parent', 'position')

    ###
    # XDM accessors

    @property
    def attributes(self) -> Optional[List['AttributeNode']]:
        return None

    @property
    def base_uri(self) -> Optional[str]:
        return self.parent.base_uri if self.parent is not None else None

    children: Optional[List[ChildNodeType]]

    @property
    def document_uri(self) -> Optional[str]:
        return None

    @property
    def is_id(self) -> Optional[bool]:
        return None

    @property
    def is_idrefs(self) -> Optional[bool]:
        return None

    @property
    def namespace_nodes(self) -> Optional[List['NamespaceNode']]:
        return None

    @property
    def nilled(self) -> Optional[bool]:
        return None

    @property
    def node_kind(self) -> str:
        raise NotImplementedError()

    @property
    def node_name(self) -> Optional[QName]:
        name: Optional[str] = getattr(self, 'name', None)
        if name is None:
            return None
        elif not name.startswith('{'):
            return QName(None, name)

        try:
            namespace, local = name[1:].split('}')
        except ValueError:
            raise ElementPathValueError(f'invalid name format for {self!r}')
        else:
            if namespace == XML_NAMESPACE:
                return QName(namespace, f'xml:{local}')

        if isinstance(self, ElementNode):
            nsmap = self.nsmap
        elif isinstance(self.parent, ElementNode):
            nsmap = self.parent.nsmap
        else:
            nsmap = {}

        for prefix, ns in nsmap.items():
            if namespace == ns:
                if not prefix:
                    return QName(namespace, local)
                return QName(namespace, f"{prefix}:{local}")
        raise ElementPathKeyError(f'missing namespace prefix mapping in {self!r}')

    parent: Optional[ParentNodeType]

    @property
    def type_name(self) -> Optional[str]:
        return None

    @property
    def string_value(self) -> str:
        raise NotImplementedError()

    @property
    def typed_value(self) -> SequenceType[AtomicType]:
        raise NotImplementedError()

    @staticmethod
    def unparsed_entity_public_id(name: str) -> Optional[str]:
        return None

    @staticmethod
    def unparsed_entity_system_id(name: str) -> Optional[AnyURI]:
        return None

    ###
    # Other properties and methods

    name: Optional[str]  # node name
    obj: object          # the object wrapped in the node
    position: int        # position of the node, for document total order

    @property
    def value(self) -> object:
        """Access to wrapped object using the old API."""
        return self.obj

    @property
    def root_node(self) -> 'XPathNode':
        return self if self.parent is None else self.parent.root_node

    @property
    def path(self) -> str:
        """Returns the node path in XPath 3.0+ format."""
        return ''

    @property
    def extended_path(self) -> str:
        """Returns the node path in extended format."""
        return self.path.replace('Q{}', '').replace('Q{', '{')

    @property
    def qname_path(self) -> str:
        """Returns the node path with names in prefixed QName format."""
        path = self.path

        if isinstance(self, ElementNode):
            for prefix, namespace in self.nsmap.items():
                path = path.replace(f'Q{{{namespace}}}', f'{prefix}:')
        elif isinstance(self.parent, ElementNode):
            for prefix, namespace in self.parent.nsmap.items():
                path = path.replace(f'Q{{{namespace}}}', f'{prefix}:')

        path = path.replace('Q{}', '')
        if 'Q{' not in path:
            return path
        raise ElementPathKeyError(f'missing namespace prefix mapping in {path}')

    @property
    def iter_typed_values(self) -> Iterator[AtomicType]:
        raise NotImplementedError()

    @property
    def is_schema_node(self) -> Optional[bool]:
        return None

    @property
    def is_typed(self) -> Optional[bool]:
        return None

    @property
    def is_extended(self) -> Optional[bool]:
        return None

    @property
    def is_list(self) -> Optional[bool]:
        return None

    def apply_schema(self, schema: 'AbstractSchemaProxy') -> None:
        """Set XSD types for elements and attribute nodes from schema proxy instance."""
        if self.parent is not None:
            self.parent.apply_schema(schema)

    def match_name(self, name: str, default_namespace: Optional[str] = None) -> bool:
        """
        Returns `True` if the argument is matching the name of the node, `False` otherwise.
        Raises a ValueError if the argument is used, but it's in a wrong format.

        :param name: a fully qualified name, a local name or a wildcard. The accepted \
        wildcard formats are '*', '*:*', '*:local-name' and '{namespace}*'.
        :param default_namespace: the default namespace for matching element names. \
        The default is no-namespace.
        """
        return False

    def get_child_position(self, child: ChildNodeType) -> int:
        pos = 0
        if self.children:
            for c in self.children:
                if isinstance(child, ElementNode):
                    if c.name == child.name:
                        pos += 1
                elif isinstance(c, child.__class__):
                    pos += 1
                if c is child:
                    break
        return pos


###
# NAMESPACE NODES

class NamespaceNode(XPathNode):
    """
    A class for processing XPath namespace nodes.

    :param prefix: the namespace prefix.
    :param uri: the namespace URI.
    :param parent: the parent element node.
    :param position: the position of the node in the document.
    """
    obj: str
    parent: Optional['ElementNode']

    __slots__ = ()

    def __init__(self,
                 prefix: Optional[str], uri: str,
                 parent: Optional['ElementNode'] = None,
                 position: int = 1) -> None:
        self.name = prefix
        self.obj = uri
        self.parent = parent
        self.position = position

    def __repr__(self) -> str:
        return '%s(prefix=%r, uri=%r)' % (self.__class__.__name__, self.name, self.obj)

    @property
    def prefix(self) -> Optional[str]:
        return self.name

    @property
    def uri(self) -> str:
        return self.obj

    value = uri

    def as_item(self) -> Tuple[Optional[str], str]:
        return self.name, self.obj

    @property
    def name_path(self) -> str:
        return self.prefix or _EMPTY_NAME_PATH

    @property
    def path(self) -> str:
        if self.parent is None:
            return '/namespace::{name_path}'
        elif isinstance(self.parent, ElementNode):
            return f"{self.parent.path}/namespace::{self.name_path}"
        return f"/namespace::{self.name_path}"

    @property
    def node_kind(self) -> str:
        return 'namespace'

    @property
    def node_name(self) -> Optional[QName]:
        return None if not self.name else QName(None, self.name)

    @property
    def string_value(self) -> str:
        return self.obj

    @property
    def iter_typed_values(self) -> Iterator[str]:
        yield self.obj


###
# ATTRIBUTE NODES

class AttributeNode(XPathNode):
    """
    Base class for XPath attribute nodes, used only for type checking.
    """
    name: Optional[str]
    parent: Optional['ElementNode']
    schema: Optional['AbstractSchemaProxy']
    xsd_type: Optional[XsdTypeProtocol]

    __slots__ = ('xsd_type',)

    def __new__(cls, *args: Any, **kwargs: Any) -> 'AttributeNode':
        if cls is AttributeNode:
            return object.__new__(TextAttributeNode)
        return object.__new__(cls)

    @property
    def uri_qualified_name(self) -> Optional[str]:
        """The URI qualified name of the attribute."""
        if not self.name:
            return self.name
        elif self.name[0] == '{':
            return f'Q{self.name}'
        else:
            return self.name

    @property
    def name_path(self) -> str:
        return self.uri_qualified_name or _EMPTY_NAME_PATH

    @property
    def path(self) -> str:
        if self.parent is None:
            return f'/@{self.name_path}'
        elif isinstance(self.parent, ElementNode):
            return f"{self.parent.path}/@{self.name_path}"
        return f"/@{self.name_path}"

    @property
    def is_typed(self) -> bool:
        return self.xsd_type is not None

    @property
    def is_list(self) -> bool:
        return self.xsd_type is not None and self.xsd_type.is_list()

    def match_name(self, name: str, default_namespace: Optional[str] = None) -> bool:
        if self.name is None:
            return False
        return self.name == name or '*' in name and match_wildcard(self.name, name)

    @property
    def base_uri(self) -> Optional[str]:
        return self.parent.base_uri if self.parent is not None else None

    @property
    def is_id(self) -> bool:
        return self.name == XML_ID or self.xsd_type is not None and self.xsd_type.is_key()

    @property
    def is_idrefs(self) -> bool:
        if self.xsd_type is None:
            return False
        root_type = self.xsd_type.root_type
        return root_type.name == XSD_IDREF or root_type.name == XSD_IDREFS

    @property
    def node_kind(self) -> str:
        return 'attribute'

    @property
    def string_value(self) -> str:
        raise NotImplementedError()

    @property
    def type_name(self) -> Optional[str]:
        return XSD_UNTYPED_ATOMIC if self.xsd_type is None else self.xsd_type.name

    @property
    def typed_value(self) -> SequenceType[AtomicType]:
        values = [v for v in self.iter_typed_values]
        if len(values) == 1:
            return values[0]
        else:
            return values

    @property
    def iter_typed_values(self) -> Iterator[AtomicType]:
        raise NotImplementedError()


class TextAttributeNode(AttributeNode):
    """
    Class for processing XPath attribute nodes.

    :param name: the attribute name.
    :param value: the string value of the attribute.
    :param parent: the parent element node.
    :param position: the position of the node in the document.
    """
    name: str
    obj: str
    parent: Optional['EtreeElementNode']

    __slots__ = ()

    def __init__(self,
                 name: str,
                 value: str,
                 parent: Optional['EtreeElementNode'] = None,
                 position: int = 1) -> None:

        self.name = name
        self.obj = value
        self.parent = parent
        self.position = position
        self.xsd_type = None

    def __repr__(self) -> str:
        return '%s(name=%r, value=%r)' % (self.__class__.__name__, self.name, self.obj)

    @property
    def value(self) -> str:
        return self.obj

    def as_item(self) -> Tuple[str, str]:
        return self.name, self.obj

    def match_name(self, name: str, default_namespace: Optional[str] = None) -> bool:
        return self.name == name or '*' in name and match_wildcard(self.name, name)

    @property
    def string_value(self) -> str:
        return self.obj

    @property
    def iter_typed_values(self) -> Iterator[AtomicType]:
        if self.parent is not None:
            yield from get_atomic_sequence(self.xsd_type, self.obj, self.parent.nsmap)
        else:
            yield from get_atomic_sequence(self.xsd_type, self.obj)

    def apply_schema(self, schema: 'AbstractSchemaProxy') -> None:
        if self.parent is not None:
            self.parent.apply_schema(schema)
        elif (xsd_attribute := schema.get_attribute(self.name)) is not None:
            self.xsd_type = xsd_attribute.type
        else:
            self.xsd_type = None


class SchemaAttributeNode(AttributeNode):
    """A class for processing XML Schema attribute nodes."""
    name: Optional[str]
    obj: XsdAttributeProtocol
    parent: Optional['ElementNode']

    __slots__ = ()

    def __init__(self,
                 attr: XsdAttributeProtocol,
                 parent: Optional['ElementNode'] = None,
                 position: int = 1):

        self.name = attr.name
        self.obj = attr
        self.parent = parent
        self.position = position
        self.xsd_type = attr.type

    def __repr__(self) -> str:
        return '%s(attr=%r)' % (self.__class__.__name__, self.obj)

    @property
    def xsd_attribute(self) -> XsdAttributeProtocol:
        return self.obj
    value = xsd_attribute

    def as_item(self) -> Tuple[Optional[str], object]:
        return self.name, self.obj

    @property
    def string_value(self) -> str:
        return str(get_atomic_sequence(self.xsd_type))

    @property
    def iter_typed_values(self) -> Iterator[AtomicType]:
        yield from get_atomic_sequence(self.xsd_type)

    def match_name(self, name: str, default_namespace: Optional[str] = None) -> bool:
        if not self.name:
            return self.obj.is_matching(name, default_namespace)
        elif '*' in name:
            return match_wildcard(self.name, name)
        else:
            return self.name == name

    @property
    def is_schema_node(self) -> bool:
        return True


###
# TEXT NODES

class TextNode(XPathNode):
    """
    A class for processing XPath text nodes. An Element's property
    (elem.text or elem.tail) with a `None` value is not a text node.

    :param content: a string value.
    :param parent: the parent element node.
    :param position: the position of the node in the document.
    """
    name: None
    obj: str
    parent: Optional['ElementNode']
    children: None = None

    __slots__ = ()

    def __init__(self,
                 content: str,
                 parent: Optional['ElementNode'] = None,
                 position: int = 1) -> None:
        self.name = None
        self.obj = content
        self.parent = parent
        self.position = position

    def __repr__(self) -> str:
        return '%s(%r)' % (self.__class__.__name__, self.obj)

    @property
    def content(self) -> str:
        return self.obj

    value = content

    @property
    def path(self) -> str:
        if self.parent is None:
            return '/text()[1]'

        pos = self.parent.get_child_position(self)
        if isinstance(self.parent, ElementNode):
            return f"{self.parent.path}/text()[{pos}]"
        return f"/text()[{pos}]"

    ###
    # Text node accessors

    @property
    def base_uri(self) -> Optional[str]:
        return self.parent.base_uri if self.parent is not None else None

    @property
    def node_kind(self) -> str:
        return 'text'

    @property
    def string_value(self) -> str:
        return self.obj

    @property
    def type_name(self) -> Optional[str]:
        return XSD_UNTYPED_ATOMIC

    @property
    def typed_value(self) -> SequenceType[AtomicType]:
        return UntypedAtomic(self.obj)

    @property
    def iter_typed_values(self) -> Iterator[UntypedAtomic]:
        yield UntypedAtomic(self.obj)


###
# COMMENT NODES

class CommentNode(XPathNode):
    """
    A class for processing XPath comment nodes.

    :param content: the wrapped Comment Element or a string.
    :param parent: the parent node.
    :param position: the position of the node in the document.
    """
    name: None
    obj: CommentType

    __slots__ = ()

    def __init__(self,
                 content: Union[CommentType, str],
                 parent: Union[ParentNodeType, None] = None,
                 position: int = 1) -> None:

        self.name = None
        if isinstance(content, str):
            self.obj = ElementTree.Comment(content)
        else:
            self.obj = content
        self.parent = parent
        self.position = position

    def __repr__(self) -> str:
        return '%s(%r)' % (self.__class__.__name__, self.obj.text or '')

    @property
    def content(self) -> CommentType:
        return self.obj

    elem = value = content

    @property
    def path(self) -> str:
        if self.parent is None:
            return '/comment()[1]'

        pos = self.parent.get_child_position(self)
        if isinstance(self.parent, ElementNode):
            return f"{self.parent.path}/comment()[{pos}]"
        return f"/comment()[{pos}]"

    @property
    def base_uri(self) -> Optional[str]:
        return self.parent.base_uri if self.parent is not None else None

    @property
    def node_kind(self) -> str:
        return 'comment'

    @property
    def string_value(self) -> str:
        return self.obj.text or ''

    @property
    def typed_value(self) -> str:
        return self.string_value

    @property
    def iter_typed_values(self) -> Iterator[str]:
        yield self.string_value


###
# PROCESSING INSTRUCTION NODES

class ProcessingInstructionNode(XPathNode):
    """
    A class for XPath processing instructions nodes.

    :param target: the wrapped Processing Instruction object or a string.
    :param content: an optional string, used if *target* is a string.
    :param parent: the parent element node.
    :param position: the position of the node in the document.
    """
    name: str
    obj: ProcessingInstructionType

    __slots__ = ()

    def __init__(self,
                 target: Union[str, ProcessingInstructionType],
                 content: Optional[str] = None,
                 parent: Optional[ParentNodeType] = None,
                 position: int = 1) -> None:

        if isinstance(target, str):
            self.name = target
            self.obj = ElementTree.ProcessingInstruction(self.name, content)
        else:
            if hasattr(target, 'target'):
                self.name = cast(str, target.target)  # lxml PI
            else:
                self.name = (target.text or '').partition(' ')[0]
            self.obj = target
        self.parent = parent
        self.position = position

    def __repr__(self) -> str:
        return '%s(target=%r, content=%r)' % (self.__class__.__name__, self.name, self.content)

    @property
    def target(self) -> str:
        return self.name

    @property
    def content(self) -> str:
        if hasattr(self.obj, 'target'):
            return self.obj.text or ''
        else:
            return (self.obj.text or '').partition(' ')[-1]

    @property
    def elem(self) -> ProcessingInstructionType:
        return self.obj
    value = elem

    @property
    def path(self) -> str:
        if self.parent is None:
            return '/processing-instruction({self.name})[1]'

        pos = self.parent.get_child_position(self)
        if isinstance(self.parent, ElementNode):
            return f"{self.parent.path}/processing-instruction({self.name})[{pos}]"
        return f"/processing-instruction({self.name})[{pos}]"

    @property
    def base_uri(self) -> Optional[str]:
        return self.parent.base_uri if self.parent is not None else None

    @property
    def node_kind(self) -> str:
        return 'processing-instruction'

    @property
    def node_name(self) -> QName:
        return QName(None, self.name)

    @property
    def string_value(self) -> str:
        return self.content

    @property
    def typed_value(self) -> SequenceType[AtomicType]:
        return self.content

    @property
    def iter_typed_values(self) -> Iterator[str]:
        yield self.content

    text = string_value


###
# ELEMENT NODES

class ElementNode(XPathNode):
    """
    Base class for XPath element nodes, used only for type checking. Element nodes
    use lazy properties to diminish the average load for a tree processing.
    """
    name: Optional[str]
    obj: object
    nsmap: Union[NsmapType, NamespacesType]
    children: List[ChildNodeType]
    parent: Optional[ParentNodeType]
    xsd_type: Optional[XsdTypeProtocol]

    # Lazy protected attributes
    _uri: str
    _schema: 'AbstractSchemaProxy'
    _elements: ElementMapType
    _namespace_nodes: List[NamespaceNode]
    _attributes: List[AttributeNode]

    __slots__ = ('children', 'nsmap', 'xsd_type', '_uri', '_schema',
                 '_elements', '_namespace_nodes', '_attributes')

    def __new__(cls, *args: Any, **kwargs: Any) -> 'ElementNode':
        if cls is ElementNode:
            return object.__new__(EtreeElementNode)
        return object.__new__(cls)

    def __repr__(self) -> str:
        return '%s(elem=%r)' % (self.__class__.__name__, self.obj)

    def __getitem__(self, i: Union[int, slice]) -> Union[ChildNodeType, List[ChildNodeType]]:
        return self.children[i]

    def __len__(self) -> int:
        return len(self.children)

    def __iter__(self) -> Iterator[ChildNodeType]:
        yield from self.children

    @property
    def uri_qualified_name(self) -> Optional[str]:
        """The URI qualified name of the element."""
        if not self.name:
            return self.name
        elif self.name[0] == '{':
            return f'Q{self.name}'
        else:
            return f'Q{{}}{self.name}'

    @property
    def attributes(self) -> List[AttributeNode]:
        return []

    @property
    def base_uri(self) -> Optional[str]:
        base_uri = self._uri.strip() if hasattr(self, '_uri') else None
        if self.parent is None:
            return base_uri
        elif base_uri is None:
            return self.parent.base_uri
        else:
            return urljoin(self.parent.base_uri or '', base_uri)

    @property
    def is_id(self) -> bool:
        return self.name == XML_ID or self.xsd_type is not None and self.xsd_type.is_key()

    @property
    def is_idrefs(self) -> bool:
        if self.xsd_type is None:
            return False
        root_type = self.xsd_type.root_type
        return root_type.name == XSD_IDREF or root_type.name == XSD_IDREFS

    @property
    def namespace_nodes(self) -> List[NamespaceNode]:
        if not hasattr(self, '_namespace_nodes'):
            # Lazy generation of namespace nodes of the element
            position = self.position + 1
            self._namespace_nodes = [NamespaceNode('xml', XML_NAMESPACE, self, position)]
            position += 1
            if self.nsmap:
                for pfx, uri in self.nsmap.items():
                    if pfx != 'xml':
                        self._namespace_nodes.append(NamespaceNode(pfx, uri, self, position))
                        position += 1

        return self._namespace_nodes

    @property
    def nilled(self) -> bool:
        return False

    @property
    def node_kind(self) -> str:
        return 'element'

    @property
    def string_value(self) -> str:
        raise NotImplementedError()

    @property
    def type_name(self) -> Optional[str]:
        return XSD_UNTYPED if self.xsd_type is None else self.xsd_type.name

    @property
    def typed_value(self) -> SequenceType[AtomicType]:
        values = [v for v in self.iter_typed_values]
        if len(values) == 1:
            return values[0]
        else:
            return values

    @property
    def iter_typed_values(self) -> Iterator[AtomicType]:
        raise NotImplementedError()

    @property
    def is_list(self) -> bool:
        return self.xsd_type is not None and self.xsd_type.is_list()

    @property
    def uri(self) -> Optional[str]:
        return getattr(self, '_uri', None)

    @uri.setter
    def uri(self, uri: str) -> None:
        self._uri = uri

    @property
    def schema(self) -> Optional['AbstractSchemaProxy']:
        root_node = self
        while isinstance(root_node.parent, EtreeElementNode):
            root_node = root_node.parent
        return getattr(root_node, '_schema', None)

    @schema.setter
    def schema(self, schema: 'AbstractSchemaProxy') -> None:
        root_node = self
        while isinstance(root_node.parent, EtreeElementNode):
            root_node = root_node.parent
        root_node._schema = schema

    @property
    def elements(self) -> Optional[ElementMapType]:
        return getattr(self, '_elements', None)

    @elements.setter
    def elements(self, elements: ElementMapType) -> None:
        self._elements = elements

    @property
    def name_path(self) -> str:
        return self.uri_qualified_name or _EMPTY_NAME_PATH

    @property
    def path(self) -> str:
        if self.parent is None:
            return f'/{self.name_path}[1]'

        pos = self.parent.get_child_position(self)
        if isinstance(self.parent, ElementNode):
            return f"{self.parent.path}/{self.name_path}[{pos}]"
        return f"/{self.name_path}[{pos}]"

    @property
    def default_namespace(self) -> Optional[str]:
        if None in self.nsmap:
            return self.nsmap[None]  # type: ignore
        else:
            return self.nsmap.get('')

    @property
    def is_typed(self) -> bool:
        return self.xsd_type is not None

    def match_name(self, name: str, default_namespace: Optional[str] = None) -> bool:
        if self.name is None:
            return False
        elif '*' in name:
            return match_wildcard(self.name, name)
        elif not name:
            return not self.name
        elif name[0] == '{' or not default_namespace:
            return self.name == name
        else:
            return self.name == f'{{{default_namespace}}}{name}'

    def get_element_node(self, elem: Union[ElementProtocol, SchemaElemType]) \
            -> Optional['ElementNode']:
        if hasattr(self, '_elements'):
            return self._elements.get(elem)

        # Fallback if there is not the map of elements but do not expand lazy elements
        for node in self.iter():
            if isinstance(node, ElementNode) and elem is node.obj:
                return node
        else:
            return None

    def get_document_node(self, replace: bool = True, as_parent: bool = True) -> 'DocumentNode':
        """
        Returns a `DocumentNode` for the element node. If the element belongs to a tree that
        already has a document root, returns the document, otherwise creates a dummy document.

        :param replace: if `True` the root element of the tree is replaced by the \
        document node. This is usually useful for extended data models (more element \
        children, text nodes).
        :param as_parent: if `True` the root node/s of parent attribute is set with \
        the dummy document node, otherwise is set to `None`.
        """
        raise NotImplementedError()

    def iter(self) -> Iterator[XPathNode]:
        """Iterates the tree building lazy components."""
        yield self
        yield from self.namespace_nodes
        yield from self.attributes

        for child in self:
            if isinstance(child, ElementNode):
                yield from child.iter()
            else:
                yield child

    iter_document = iter  # For backward compatibility

    def iter_lazy(self) -> Iterator[XPathNode]:
        """Iterates the tree not including the not built lazy components."""
        yield self

        iterators: Deque[Any] = deque()  # slightly faster than list()
        children: Iterator[Any] = iter(self.children)

        if hasattr(self, '_namespace_nodes'):
            yield from self._namespace_nodes
        if hasattr(self, '_attributes'):
            yield from self._attributes

        while True:
            for child in children:
                yield child

                if isinstance(child, ElementNode):
                    if hasattr(child, '_namespace_nodes'):
                        yield from child._namespace_nodes
                    if hasattr(child, '_attributes'):
                        yield from child._attributes

                    if child.children:
                        iterators.append(children)
                        children = iter(child.children)
                        break
            else:
                try:
                    children = iterators.pop()
                except IndexError:
                    return

    def iter_descendants(self, with_self: bool = True) -> Iterator[ChildNodeType]:
        if with_self:
            yield self

        iterators: Deque[Any] = deque()
        children: Iterator[Any] = iter(self.children)

        while True:
            for child in children:
                yield child

                if isinstance(child, ElementNode) and child.children:
                    iterators.append(children)
                    children = iter(child.children)
                    break
            else:
                try:
                    children = iterators.pop()
                except IndexError:
                    return


class EtreeElementNode(ElementNode):
    """
    XPath element nodes for wrapping ElementTree elements.

    :param elem: the wrapped Element or XSD schema/element.
    :param parent: the parent document node or element node.
    :param position: the position of the node in the document.
    :param nsmap: an optional mapping from prefix to namespace URI.
    """
    name: str
    obj: ElementType
    xsd_element: Optional[XsdElementProtocol]

    __slots__ = ()

    def __init__(self,
                 elem: ElementType,
                 parent: Optional[ParentNodeType] = None,
                 position: int = 1,
                 nsmap: Union[NsmapType, NamespacesType, None] = None):

        self.name = elem.tag
        self.obj = elem
        self.parent = parent
        self.position = position
        self.children = []
        self.xsd_type = None

        if nsmap is not None:
            self.nsmap = nsmap
        else:
            try:
                self.nsmap = cast(Dict[Any, str], getattr(elem, 'nsmap'))
            except AttributeError:
                self.nsmap = {}

    @property
    def content(self) -> ElementType:
        return self.obj

    elem = value = content

    @property
    def attributes(self) -> List[AttributeNode]:
        if not hasattr(self, '_attributes'):
            position = self.position + len(self.nsmap) + int('xml' not in self.nsmap) + 1
            self._attributes = [
                TextAttributeNode(name, value, self, pos)
                for pos, (name, value) in enumerate(self.obj.attrib.items(), position)
            ]
        return self._attributes

    @property
    def base_uri(self) -> Optional[str]:
        base_uri = self.obj.get(XML_BASE)
        if isinstance(base_uri, str):
            base_uri = base_uri.strip()
        elif base_uri is not None:
            base_uri = ''
        elif hasattr(self, '_uri'):
            base_uri = self._uri.strip()

        if self.parent is None:
            return base_uri
        elif base_uri is None:
            return self.parent.base_uri
        else:
            return urljoin(self.parent.base_uri or '', base_uri)

    @property
    def nilled(self) -> bool:
        return self.obj.get(XSI_NIL) in ('true', '1')

    @property
    def string_value(self) -> str:
        if self.xsd_type is not None and self.xsd_type.is_element_only():
            # Element-only text content is normalized
            return ''.join(etree_iter_strings(self.obj, normalize=True))
        return ''.join(etree_iter_strings(self.obj))

    @property
    def typed_value(self) -> SequenceType[AtomicType]:
        values = [v for v in self.iter_typed_values]
        if len(values) == 1:
            return values[0]
        else:
            return values

    @property
    def iter_typed_values(self) -> Iterator[AtomicType]:
        if self.xsd_type is None or \
                self.xsd_type.name in _XSD_SPECIAL_TYPES or \
                self.xsd_type.has_mixed_content():
            yield UntypedAtomic(''.join(etree_iter_strings(self.obj)))
        elif self.xsd_type.is_element_only():
            return
        elif self.obj.get(XSI_NIL) and getattr(self.xsd_type.parent, 'nillable', None):
            return
        elif self.obj.text is not None:
            yield from get_atomic_sequence(self.xsd_type, self.obj.text, self.nsmap)
        elif self.obj.get(XSI_NIL) in ('1', 'true'):
            yield ''
        else:
            yield from get_atomic_sequence(self.xsd_type, '')

    def apply_schema(self, schema: 'AbstractSchemaProxy') -> None:
        if self.schema is schema and not schema.is_assertion_based():
            return
        self.schema = schema

        if not schema.is_fully_valid():
            element_type = schema.get_type(XSD_ANY_TYPE)
            attribute_type = schema.get_type(XSD_ANY_SIMPLE_TYPE)
            for elem in self.iter_descendants(with_self=True):
                if isinstance(elem, EtreeElementNode):
                    elem.xsd_type = element_type
                    for attr in elem.attributes:
                        attr.xsd_type = attribute_type
            return

        if (xsd_element := schema.base_element) is not None:
            paths = ['./']
            children: Iterator[Any] = iter(self)
            if schema.is_assertion_based():
                self.xsd_type = schema.get_type(XSD_ANY_TYPE)
            else:
                self.xsd_type = xsd_element.type

            for attr in self.attributes:
                if attr.name in xsd_element.attrib:
                    attr.xsd_type = xsd_element.attrib[attr.name].type
                else:
                    xsd_attribute = schema.cached_find(f'./@{attr.name}')
                    if xsd_attribute is not None and hasattr(xsd_attribute, 'type'):
                        attr.xsd_type = xsd_attribute.type
                    else:
                        attr.xsd_type = None
        else:
            root_node: ParentNodeType = self
            while isinstance(root_node.parent, EtreeElementNode):
                root_node = root_node.parent

            paths = ['/']
            children = iter((root_node,))

        iterators: List[Any] = []
        while True:
            for elem in children:
                if not isinstance(elem, EtreeElementNode):
                    continue

                child_path = f'{paths[-1]}{elem.name}/'
                if isinstance(xsi_type := elem.obj.attrib.get(XSI_TYPE), str):
                    xsd_element = None
                    try:
                        type_name = get_expanded_name(xsi_type, elem.nsmap)
                    except KeyError:
                        elem.clear_types()
                        continue
                    else:
                        elem.xsd_type = schema.get_type(type_name)
                else:
                    result = schema.cached_find(f'{paths[-1]}{elem.name}')
                    if result is not None and hasattr(result, 'type'):
                        elem.xsd_type = cast(XsdElementProtocol, result).type
                    else:
                        elem.clear_types()
                        continue

                for attr in elem.attributes:
                    if xsd_element is not None and attr.name in xsd_element.attrib:
                        attr.xsd_type = xsd_element.attrib[attr.name].type
                    else:
                        xsd_attribute = schema.cached_find(f'{child_path}@{attr.name}')
                        if xsd_attribute is not None and hasattr(xsd_attribute, 'type'):
                            attr.xsd_type = xsd_attribute.type
                        else:
                            attr.xsd_type = None

                if len(elem.obj):
                    paths.append(child_path)
                    iterators.append(children)
                    children = iter(elem)
                    break
            else:
                try:
                    children = iterators.pop()
                    paths.pop()
                except IndexError:
                    return

    def clear_types(self) -> None:
        """Clear XSD types for element node subtree."""
        for elem in self.iter_descendants(with_self=True):
            if isinstance(elem, EtreeElementNode):
                elem.xsd_type = None
                for attr in elem.attributes:
                    attr.xsd_type = None

    @property
    def is_typed(self) -> bool:
        return self.xsd_type is not None

    def match_name(self, name: str, default_namespace: Optional[str] = None) -> bool:
        if '*' in name:
            return match_wildcard(self.obj.tag, name)
        elif not name:
            return not self.obj.tag
        elif hasattr(self.obj, 'type'):
            return cast(XsdElementProtocol, self.obj).is_matching(name, default_namespace)
        elif name[0] == '{' or not default_namespace:
            return self.obj.tag == name
        else:
            return self.obj.tag == f'{{{default_namespace}}}{name}'

    def get_document_node(self, replace: bool = True, as_parent: bool = True) -> 'DocumentNode':
        """
        Returns a `DocumentNode` for the element node. If the element belongs to a tree that
        already has a document root, returns the document, otherwise creates a dummy document
        if the element node wraps an Element of an ElementTree structure or return `None`.

        :param replace: if `True` the root element of the tree is replaced by the \
        document node. This is usually useful for extended data models (more element \
        children, text nodes).
        :param as_parent: if `True` the root node/s of parent attribute is set with \
        the dummy document node, otherwise is set to `None`.
        """
        root_node: ParentNodeType = self
        while root_node.parent is not None:
            root_node = root_node.parent

        if isinstance(root_node, DocumentNode):
            return root_node

        if root_node.obj.__class__.__module__ not in ('lxml.etree', 'lxml.html'):
            etree = ElementTree
        else:
            etree = importlib.import_module('lxml.etree')

        if replace:
            document = etree.ElementTree()
            if sum(isinstance(x, ElementNode) for x in root_node.children) == 1:
                for child in root_node.children:
                    if isinstance(child, ElementNode):
                        document = etree.ElementTree(cast(ElementTree.Element, child.obj))
                        break

            document_node = DocumentNode(document, root_node.uri, root_node.position)
            for child in root_node.children:
                document_node.children.append(child)
                child.parent = document_node if as_parent else None

            if root_node.elements is not None:
                root_node.elements.pop(root_node, None)  # type: ignore[call-overload]
                document_node.elements = root_node.elements
            del root_node

        else:
            document = etree.ElementTree(cast(ElementTree.Element, root_node.obj))
            document_node = DocumentNode(document, root_node.uri, root_node.position - 1)
            document_node.children.append(root_node)
            if as_parent:
                root_node.parent = document_node
            if root_node.elements is not None:
                document_node.elements = root_node.elements

        return document_node


###
# Specialized element nodes

class LazyElementNode(EtreeElementNode):
    """
    A fully lazy element node, slower but better if the node has not
    to be used in a document context. The node extends descendants but
    does not record positions and a map of elements.
    """
    __slots__ = ()

    def __iter__(self) -> Iterator[ChildNodeType]:
        if not self.children:
            if self.obj.text is not None:
                self.children.append(TextNode(self.obj.text, self))
            if len(self.obj):
                for elem in self.obj:
                    if not callable(elem.tag):
                        nsmap = cast(Dict[Any, str], getattr(elem, 'nsmap', self.nsmap))
                        self.children.append(LazyElementNode(elem, self, nsmap=nsmap))
                    elif elem.tag.__name__ == 'Comment':  # type: ignore[attr-defined]
                        self.children.append(CommentNode(elem, self))
                    else:
                        self.children.append(ProcessingInstructionNode(elem, parent=self))

                    if elem.tail is not None:
                        self.children.append(TextNode(elem.tail, self))

        yield from self.children

    def iter_descendants(self, with_self: bool = True) -> Iterator[ChildNodeType]:
        if with_self:
            yield self

        for child in self:
            if isinstance(child, ElementNode):
                yield from child.iter_descendants()
            else:
                yield child


class SchemaElementNode(ElementNode):
    """
    An element node class for wrapping the XSD schema and its elements.
    The resulting structure can be a tree or a set of disjoint trees.
    With more roots only one of them is the schema node.
    """
    ref: Optional['SchemaElementNode'] = None
    obj: SchemaElemType

    __slots__ = ('__dict__',)

    def __init__(self,
                 elem: SchemaElemType,
                 parent: Optional[ParentNodeType] = None,
                 position: int = 1,
                 nsmap: Optional[NsmapType] = None):

        self.name = elem.tag
        self.obj = elem
        self.parent = parent
        self.position = position
        self.nsmap = nsmap if nsmap is not None else {}
        self.children = []
        self.xsd_type = getattr(elem, 'type', None)

    def __iter__(self) -> Iterator[ChildNodeType]:
        if self.ref is None:
            yield from self.children
        else:
            yield from self.ref.children

    @property
    def xsd_element(self) -> Optional[XsdElementProtocol]:
        if hasattr(self.obj, 'type'):
            return cast(XsdElementProtocol, self.obj)
        else:
            return None

    @property
    def content(self) -> SchemaElemType:
        return self.obj

    elem = value = content

    @property
    def path(self) -> str:
        if not hasattr(self, 'type'):
            return '/'
        return super().path

    @property
    def is_schema_node(self) -> bool:
        return True

    def match_name(self, name: str, default_namespace: Optional[str] = None) -> bool:
        if '*' in name:
            return match_wildcard(self.obj.tag, name)
        elif not name:
            return not self.obj.tag
        elif hasattr(self.obj, 'type'):
            return self.obj.is_matching(name, default_namespace)
        else:
            return self.obj.tag == name  # a schema

    @property
    def attributes(self) -> List[AttributeNode]:
        if not hasattr(self, '_attributes'):
            position = self.position + len(self.nsmap) + int('xml' not in self.nsmap)
            self._attributes = [
                SchemaAttributeNode(attr, self, pos)
                for pos, (_, attr) in enumerate(self.obj.attrib.items(), position)
            ]
        return self._attributes

    @property
    def base_uri(self) -> Optional[str]:
        base_uri = self._uri.strip() if hasattr(self, '_uri') else None
        if self.parent is None:
            return base_uri
        elif base_uri is None:
            return self.parent.base_uri
        else:
            return urljoin(self.parent.base_uri or '', base_uri)

    @property
    def type_name(self) -> Optional[str]:
        if (xsd_type := getattr(self.obj, 'type', None)) is not None:
            return cast(Optional[str], xsd_type.name)
        return None

    @property
    def string_value(self) -> str:
        if not hasattr(self.obj, 'type'):
            return ''
        for item in get_atomic_sequence(self.xsd_type):
            return str(item)
        return ''

    @property
    def iter_typed_values(self) -> Iterator[AtomicType]:
        yield from get_atomic_sequence(self.xsd_type)

    def iter(self) -> Iterator[XPathNode]:
        yield self

        iterators: List[Any] = []
        children: Iterator[Any] = iter(self.children)

        if hasattr(self, '_namespace_nodes'):
            yield from self._namespace_nodes
        if hasattr(self, '_attributes'):
            yield from self._attributes

        elements = {self}
        while True:
            for child in children:
                if child in elements:
                    continue
                yield child
                elements.add(child)

                if isinstance(child, ElementNode):
                    if hasattr(child, '_namespace_nodes'):
                        yield from child._namespace_nodes
                    if hasattr(child, '_attributes'):
                        yield from child._attributes

                    if child.children:
                        iterators.append(children)
                        children = iter(child.children)
                        break
            else:
                try:
                    children = iterators.pop()
                except IndexError:
                    return

    def iter_descendants(self, with_self: bool = True) -> Iterator[ChildNodeType]:
        if with_self:
            yield self

        iterators: List[Any] = []
        children: Iterator[Any] = iter(self.children)

        elements = {self}
        while True:
            for child in children:
                if child.ref is not None:
                    child = child.ref

                if child in elements:
                    continue
                yield child
                elements.add(child)

                if child.children:
                    iterators.append(children)
                    children = iter(child.children)
                    break
            else:
                try:
                    children = iterators.pop()
                except IndexError:
                    return


###
# DOCUMENT NODES

class DocumentNode(XPathNode):
    """
    Base class for all XPath document nodes.
    """
    name: None
    obj: object
    parent: None
    uri: Optional[str]
    children: List[ChildNodeType]
    elements: Dict[ElementProtocol, ElementNode]

    __slots__ = ('children', 'uri', 'elements')

    def __new__(cls, *args: Any, **kwargs: Any) -> 'DocumentNode':
        if cls is DocumentNode:
            return object.__new__(EtreeDocumentNode)
        return object.__new__(cls)

    def __repr__(self) -> str:
        return '%s(document=%r)' % (self.__class__.__name__, self.document)

    def __getitem__(self, i: Union[int, slice]) -> Union[ChildNodeType, List[ChildNodeType]]:
        return self.children[i]

    def __len__(self) -> int:
        return len(self.children)

    def __iter__(self) -> Iterator[ChildNodeType]:
        yield from self.children

    @property
    def document(self) -> object:
        return self.obj
    value = document

    @property
    def path(self) -> str:
        return '/'

    def getroot(self) -> ElementNode:
        for child in self.children:
            if isinstance(child, ElementNode):
                return child
        raise ElementPathRuntimeError("Missing document root")

    def get_element_node(self, elem: ElementProtocol) -> Optional[ElementNode]:
        return self.elements.get(elem)

    def iter(self) -> Iterator[XPathNode]:
        yield self

        for e in self.children:
            if isinstance(e, ElementNode):
                yield from e.iter()
            else:
                yield e

    iter_document = iter

    def iter_lazy(self) -> Iterator[XPathNode]:
        yield self

        for e in self.children:
            if isinstance(e, ElementNode):
                yield from e.iter_lazy()
            else:
                yield e

    def iter_descendants(self, with_self: bool = True) \
            -> Iterator[Union['DocumentNode', ChildNodeType]]:
        if with_self:
            yield self

        for e in self.children:
            if isinstance(e, ElementNode):
                yield from e.iter_descendants()
            else:
                yield e

    @property
    def is_typed(self) -> bool:
        for child in self.children:
            if isinstance(child, ElementNode):
                return child.is_typed
        else:
            return False

    def apply_schema(self, schema: 'AbstractSchemaProxy') -> None:
        for child in self.children:
            if isinstance(child, EtreeElementNode):
                child.apply_schema(schema)

    def clear_types(self) -> None:
        for child in self.children:
            if isinstance(child, EtreeElementNode):
                child.clear_types()

    @property
    def is_extended(self) -> bool:
        """
        Returns `True` if the document node can't be represented with an
        ElementTree structure, `False` otherwise.
        """
        if not self.children:
            raise ElementPathRuntimeError("Missing document root")
        return len(self.children) > 1 or not isinstance(self.children[0], ElementNode)

    @property
    def base_uri(self) -> Optional[str]:
        return self.uri.strip() if self.uri is not None else None

    @property
    def document_uri(self) -> Optional[str]:
        if self.uri is not None and is_absolute_uri(self.uri):
            return self.uri.strip()
        else:
            return None

    @property
    def node_kind(self) -> str:
        return 'document'

    @property
    def string_value(self) -> str:
        raise NotImplementedError()

    @property
    def typed_value(self) -> AtomicType:
        return UntypedAtomic(self.string_value)

    @property
    def iter_typed_values(self) -> Iterator[UntypedAtomic]:
        yield UntypedAtomic(self.string_value)


class EtreeDocumentNode(DocumentNode):
    """
    A class for ElementTree document nodes.

    :param document: the wrapped ElementTree instance.
    :param uri: the document URI.
    :param position: the position of the node in the document, usually 1, \
    or 0 for lxml standalone root elements with siblings.
    """
    obj: DocumentType

    __slots__ = ()

    def __init__(self, document: DocumentType,
                 uri: Optional[str] = None,
                 position: int = 1) -> None:

        self.obj = document
        self.uri = uri
        self.name = None
        self.parent = None
        self.position = position
        self.elements = {}
        self.children = []

    @property
    def document(self) -> DocumentType:
        return self.obj

    @property
    def string_value(self) -> str:
        if not self.children:
            # Fallback for not built documents
            root = self.document.getroot()
            if root is None:
                return ''
            return ''.join(etree_iter_strings(root))
        return ''.join(child.string_value for child in self.children)

    @property
    def is_extended(self) -> bool:
        """
        Returns `True` if the document node can't be represented with an
        ElementTree structure, `False` otherwise.
        """
        root = self.document.getroot()
        if root is None or not is_etree_element_instance(root):
            return True
        elif not self.children:
            raise ElementPathRuntimeError("Missing document root")
        elif len(self.children) == 1:
            return not isinstance(self.children[0], ElementNode)
        elif not hasattr(root, 'itersiblings'):
            return True  # an extended xml.etree.ElementTree structure
        elif any(isinstance(x, TextNode) for x in root):
            return True
        else:
            return sum(isinstance(x, ElementNode) for x in root) != 1


###
# Type annotation aliases
XPathNodeType = Union[DocumentNode, NamespaceNode, AttributeNode, TextNode,
                      ElementNode, CommentNode, ProcessingInstructionNode]
RootNodeType = Union[DocumentNode, ElementNode]
RootArgType = Union[DocumentType, ElementType, SchemaElemType, RootNodeType]
