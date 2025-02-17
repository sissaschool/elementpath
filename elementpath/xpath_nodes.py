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
from elementpath.exceptions import ElementPathRuntimeError
from elementpath.aliases import NsmapType, SequenceType
from elementpath.datatypes import UntypedAtomic, AtomicType
from elementpath.namespaces import XML_NAMESPACE, XML_BASE, XSI_NIL, \
    XSD_ANY_TYPE, XSD_ANY_SIMPLE_TYPE, XSD_ANY_ATOMIC_TYPE, \
    XML_ID, XSD_IDREF, XSD_IDREFS, XSD_UNTYPED, XSD_UNTYPED_ATOMIC
from elementpath.protocols import ElementProtocol, XsdElementProtocol, \
    XsdAttributeProtocol, XsdTypeProtocol, DocumentType, ElementType, SchemaElemType, \
    CommentType, ProcessingInstructionType
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

_XSD_SPECIAL_TYPES = {XSD_ANY_TYPE, XSD_ANY_SIMPLE_TYPE, XSD_ANY_ATOMIC_TYPE}

TypedNodeType = Union['AttributeNode', 'ElementNode']
ParentNodeType = Union['DocumentNode', 'ElementNode']
ChildNodeType = Union['TextNode', 'ElementNode', 'CommentNode', 'ProcessingInstructionNode']
ElementMapType = Dict[ElementType, 'ElementNode']


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

    __slots__ = 'name', 'parent', 'position'

    ###
    # XDM accessors

    kind: str = ''
    children: Optional[List[ChildNodeType]]
    parent: Optional[ParentNodeType]
    name: Optional[str]

    @property
    def attributes(self) -> Optional[List['AttributeNode']]:
        return None

    @property
    def base_uri(self) -> Optional[str]:
        return self.parent.base_uri if self.parent is not None else None

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
    def is_list(self) -> Optional[bool]:
        return None

    @property
    def namespace_nodes(self) -> Optional[List['NamespaceNode']]:
        return None

    @property
    def nilled(self) -> Optional[bool]:
        return None

    @property
    def type_name(self) -> Optional[str]:
        return None

    @property
    def string_value(self) -> str:
        raise NotImplementedError()

    @property
    def iter_typed_values(self) -> Iterator[AtomicType]:
        raise NotImplementedError()

    @property
    def typed_value(self) -> SequenceType[AtomicType]:
        values = [v for v in self.iter_typed_values]
        if len(values) == 1:
            return values[0]
        else:
            return values

    ###
    # Other properties and methods

    @property
    def value(self) -> object:
        raise NotImplementedError()

    position: int  # for document total order
    xsd_type: Optional[XsdTypeProtocol]

    @property
    def root_node(self) -> 'XPathNode':
        return self if self.parent is None else self.parent.root_node

    @property
    def nsmap(self) -> NsmapType:
        return self.parent.nsmap if self.parent is not None else {}

    def is_schema_node(self) -> bool:
        return False

    def is_typed(self) -> bool:
        return False

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
    attributes: None
    children: None = None
    base_uri: None
    document_uri: None
    is_id: None
    is_idrefs: None
    namespace_nodes: None
    nilled: None
    parent: Optional['ElementNode']
    type_name: None

    kind = 'namespace'

    __slots__ = 'uri',

    def __init__(self,
                 prefix: Optional[str], uri: str,
                 parent: Optional['ElementNode'] = None,
                 position: int = 1) -> None:
        self.name = prefix
        self.uri = uri
        self.parent = parent
        self.position = position

    @property
    def prefix(self) -> Optional[str]:
        return self.name

    @property
    def value(self) -> str:
        return self.uri

    def as_item(self) -> Tuple[Optional[str], str]:
        return self.name, self.uri

    def __repr__(self) -> str:
        return '%s(prefix=%r, uri=%r)' % (self.__class__.__name__, self.name, self.uri)

    @property
    def string_value(self) -> str:
        return self.uri

    @property
    def iter_typed_values(self) -> Iterator[str]:
        yield self.uri


###
# ATTRIBUTE NODES

class AttributeNode(XPathNode):
    """
    Base class for XPath attribute nodes, used only for type checking.
    """
    attributes: None
    children: None = None
    base_uri: None
    document_uri: None
    namespace_nodes: None
    nilled: None
    parent: Optional['ElementNode']
    value: object

    kind = 'attribute'

    __slots__ = ()

    def __new__(cls, *args: Any, **kwargs: Any) -> 'AttributeNode':
        if cls is AttributeNode:
            return object.__new__(TextAttributeNode)
        return object.__new__(cls)

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
    def is_list(self) -> bool:
        return self.xsd_type is not None and self.xsd_type.is_list()

    @property
    def type_name(self) -> Optional[str]:
        return XSD_UNTYPED_ATOMIC if self.xsd_type is None else self.xsd_type.name

    @property
    def iter_typed_values(self) -> Iterator[AtomicType]:
        raise NotImplementedError()

    def as_item(self) -> Tuple[Optional[str], object]:
        return self.name, self.value

    def __repr__(self) -> str:
        return '%s(name=%r, value=%r)' % (self.__class__.__name__, self.name, self.value)

    @property
    def path(self) -> str:
        if self.parent is None:
            return f"@{self.name or '*'}"
        path = self.parent.path
        return f"/@{self.name or '*'}" if path == '/' else f"{path}/@{self.name or '*'}"

    def is_typed(self) -> bool:
        return self.xsd_type is not None

    def match_name(self, name: str, default_namespace: Optional[str] = None) -> bool:
        if self.name is None:
            return False
        return self.name == name or '*' in name and match_wildcard(self.name, name)


class TextAttributeNode(AttributeNode):
    """
    Class for processing XPath attribute nodes.

    :param name: the attribute name.
    :param value: the string value of the attribute.
    :param parent: the parent element node.
    :param position: the position of the node in the document.
    :param schema: an optional schema proxy instance for set the XSD type annotation.
    """
    name: str
    value: str

    __slots__ = ('value', 'schema', 'xsd_type')

    def __init__(self,
                 name: str,
                 value: str,
                 parent: Optional['ElementNode'] = None,
                 position: int = 1,
                 schema: Optional['AbstractSchemaProxy'] = None) -> None:

        self.name = name
        self.value = value
        self.parent = parent
        self.position = position
        self.schema = schema

        if schema is None:
            self.schema = None
            self.xsd_type = None
        else:
            self.set_schema(schema)

    def set_schema(self, schema: 'AbstractSchemaProxy') -> None:
        self.schema = schema
        if schema.attribute_type is not None:
            self.xsd_type = schema.attribute_type
        elif isinstance(self.parent, EtreeElementNode):
            if self.parent.xsd_element is not None and \
                    self.name in self.parent.xsd_element.attrib:
                self.xsd_type = self.parent.xsd_element.attrib[self.name].type
            else:
                xsd_attribute = schema.find(self.path)
                if xsd_attribute is not None and hasattr(xsd_attribute, 'type'):
                    self.xsd_type = xsd_attribute.type
                else:
                    self.xsd_type = None
        else:
            self.xsd_type = None

    @property
    def string_value(self) -> str:
        return self.value

    @property
    def iter_typed_values(self) -> Iterator[AtomicType]:
        if self.parent is not None:
            yield from get_atomic_sequence(self.xsd_type, self.value, self.parent.nsmap)
        else:
            yield from get_atomic_sequence(self.xsd_type, self.value)

    def as_item(self) -> Tuple[str, str]:
        return self.name, self.value

    def match_name(self, name: str, default_namespace: Optional[str] = None) -> bool:
        return self.name == name or '*' in name and match_wildcard(self.name, name)


class SchemaAttributeNode(AttributeNode):
    """A class for processing XML Schema attribute nodes."""

    value: XsdAttributeProtocol

    __slots__ = ('value', 'xsd_type')

    def __init__(self,
                 name: Optional[str],
                 value: XsdAttributeProtocol,
                 parent: Optional['ElementNode'] = None,
                 position: int = 1):

        self.name = name
        self.value = value
        self.parent = parent
        self.position = position
        self.xsd_type = value.type

    @property
    def string_value(self) -> str:
        return str(get_atomic_sequence(self.xsd_type))

    @property
    def iter_typed_values(self) -> Iterator[AtomicType]:
        yield from get_atomic_sequence(self.xsd_type)

    def match_name(self, name: str, default_namespace: Optional[str] = None) -> bool:
        if not self.name:
            return self.value.is_matching(name, default_namespace)
        elif '*' in name:
            return match_wildcard(self.name, name)
        else:
            return self.name == name

    def is_schema_node(self) -> bool:
        return True


###
# TEXT NODES

class TextNode(XPathNode):
    """
    A class for processing XPath text nodes. An Element's property
    (elem.text or elem.tail) with a `None` value is not a text node.

    :param value: a string value.
    :param parent: the parent element node.
    :param position: the position of the node in the document.
    """
    attributes: None
    children: None = None
    document_uri: None
    is_id: None
    is_idrefs: None
    namespace_nodes: None
    nilled: None
    name: None = None
    parent: Optional['ElementNode']
    type_name: None

    kind = 'text'
    value: str

    __slots__ = 'value',

    def __init__(self,
                 value: str,
                 parent: Optional['ElementNode'] = None,
                 position: int = 1) -> None:
        self.value = value
        self.parent = parent
        self.position = position

    def __repr__(self) -> str:
        return '%s(value=%r)' % (self.__class__.__name__, self.value)

    @property
    def string_value(self) -> str:
        return self.value

    @property
    def iter_typed_values(self) -> Iterator[UntypedAtomic]:
        yield UntypedAtomic(self.value)


###
# COMMENT NODES

class CommentNode(XPathNode):
    """
    A class for processing XPath comment nodes.

    :param comment: the wrapped Comment Element or a string.
    :param parent: the parent element node.
    :param position: the position of the node in the document.
    """
    elem: CommentType
    attributes: None
    children:  None = None
    document_uri: None
    is_id: None
    is_idrefs: None
    namespace_nodes: None
    nilled: None
    name: None
    type_name: None

    kind = 'comment'

    __slots__ = 'elem',

    def __init__(self,
                 comment: Union[ElementType, str],
                 parent: Union[ParentNodeType, None] = None,
                 position: int = 1) -> None:

        if isinstance(comment, str):
            self.elem = ElementTree.Comment(comment)
        else:
            self.elem = comment
        self.name = None
        self.parent = parent
        self.position = position

    def __repr__(self) -> str:
        return '%s(comment=%r)' % (self.__class__.__name__, self.elem.text or '')

    @property
    def value(self) -> CommentType:
        return self.elem

    @property
    def string_value(self) -> str:
        return self.elem.text or ''

    @property
    def iter_typed_values(self) -> Iterator[str]:
        yield self.string_value


###
# PROCESSING INSTRUCTION NODES

class ProcessingInstructionNode(XPathNode):
    """
    A class for XPath processing instructions nodes.

    :param pi: the wrapped Processing Instruction object.
    :param parent: the parent element node.
    :param position: the position of the node in the document.
    """
    elem: ProcessingInstructionType
    name: str
    attributes: None
    children:  None = None
    document_uri: None
    is_id: None
    is_idrefs: None
    namespace_nodes: None
    nilled: None
    type_name: None

    kind = 'processing-instruction'

    __slots__ = 'elem',

    def __init__(self,
                 pi: Union[ProcessingInstructionType, str],
                 parent: Optional[ParentNodeType] = None,
                 position: int = 1) -> None:

        if isinstance(pi, str):
            self.name, _, text = pi.rpartition(' ')
            self.elem = ElementTree.ProcessingInstruction(self.name, text)
        else:
            if hasattr(pi, 'target'):
                self.name = cast(str, pi.target)  # lxml PI
            else:
                self.name = (pi.text or '').partition(' ')[0]
            self.elem = pi
        self.parent = parent
        self.position = position

    def __repr__(self) -> str:
        return '%s(target=%r, text=%r)' % (self.__class__.__name__, self.name, self.text)

    @property
    def value(self) -> ProcessingInstructionType:
        return self.elem

    @property
    def target(self) -> str:
        return self.name

    @property
    def string_value(self) -> str:
        if hasattr(self.elem, 'target'):
            return self.elem.text or ''
        else:
            return (self.elem.text or '').partition(' ')[-1]

    @property
    def iter_typed_values(self) -> Iterator[str]:
        yield self.string_value

    text = string_value


###
# ELEMENT NODES

class ElementNode(XPathNode):
    """
    Base class for XPath element nodes, used only for type checking. Element nodes
    use lazy properties to diminish the average load for a tree processing.
    """
    kind = 'element'
    elem: object
    nsmap: NsmapType
    children: List[ChildNodeType]

    elements: Optional[ElementMapType] = None
    _namespace_nodes: Optional[List['NamespaceNode']] = None
    _attributes: Optional[List['AttributeNode']] = None

    document_uri: None
    uri: Optional[str] = None

    __slots__ = ('elem', 'xsd_type', 'children', '__dict__')

    def __new__(cls, *args: Any, **kwargs: Any) -> 'ElementNode':
        if cls is ElementNode:
            return object.__new__(EtreeElementNode)
        return object.__new__(cls)

    def __repr__(self) -> str:
        return '%s(elem=%r)' % (self.__class__.__name__, self.elem)

    def __getitem__(self, i: Union[int, slice]) -> Union[ChildNodeType, List[ChildNodeType]]:
        return self.children[i]

    def __len__(self) -> int:
        return len(self.children)

    def __iter__(self) -> Iterator[ChildNodeType]:
        yield from self.children

    @property
    def value(self) -> object:
        return self.elem

    @property
    def is_id(self) -> bool:
        return False

    @property
    def is_idrefs(self) -> bool:
        return False

    @property
    def is_list(self) -> bool:
        return self.xsd_type is not None and self.xsd_type.is_list()

    @property
    def base_uri(self) -> Optional[str]:
        base_uri = self.uri and self.uri.strip()
        if self.parent is None:
            return base_uri
        elif base_uri is None:
            return self.parent.base_uri
        else:
            return urljoin(self.parent.base_uri or '', base_uri)

    @property
    def nilled(self) -> bool:
        return False

    @property
    def type_name(self) -> Optional[str]:
        return XSD_UNTYPED if self.xsd_type is None else self.xsd_type.name

    @property
    def namespace_nodes(self) -> List['NamespaceNode']:
        if self._namespace_nodes is None:
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
    def attributes(self) -> List['AttributeNode']:
        return []

    @property
    def path(self) -> str:
        """Returns an absolute path for the node."""
        if not isinstance(self.parent, ElementNode):
            return f'/{self.name}'
        return f'{self.parent.path}/{self.name}'

    @property
    def default_namespace(self) -> Optional[str]:
        if None in self.nsmap:
            return self.nsmap[None]
        else:
            return self.nsmap.get('')

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
        if self.elements is not None:
            return self.elements.get(elem)

        # Fallback if there is not the map of elements but do not expand lazy elements
        for node in self.iter():
            if isinstance(node, ElementNode) and elem is node.elem:
                return node
        else:
            return None

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

        if root_node.elem.__class__.__module__ not in ('lxml.etree', 'lxml.html'):
            etree = ElementTree
        else:
            etree = importlib.import_module('lxml.etree')

        if replace:
            document = etree.ElementTree()
            if sum(isinstance(x, ElementNode) for x in root_node.children) == 1:
                for child in root_node.children:
                    if isinstance(child, ElementNode):
                        document = etree.ElementTree(cast(ElementTree.Element, child.elem))
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
            document = etree.ElementTree(cast(ElementTree.Element, root_node.elem))
            document_node = DocumentNode(document, root_node.uri, root_node.position - 1)
            document_node.children.append(root_node)
            if as_parent:
                root_node.parent = document_node
            if root_node.elements is not None:
                document_node.elements = root_node.elements

        return document_node

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

        if self._namespace_nodes:
            yield from self._namespace_nodes
        if self._attributes:
            yield from self._attributes

        while True:
            for child in children:
                yield child

                if isinstance(child, ElementNode):
                    if child._namespace_nodes:
                        yield from child._namespace_nodes
                    if child._attributes:
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
    :param schema: an optional schema proxy instance for set the XSD type annotation.

    """
    elem: ElementType
    schema: Optional['AbstractSchemaProxy']
    xsd_type: Optional[XsdTypeProtocol]
    xsd_element: Optional[XsdElementProtocol]

    __slots__ = ('nsmap', 'schema', 'xsd_element')

    def __init__(self,
                 elem: ElementType,
                 parent: Optional[ParentNodeType] = None,
                 position: int = 1,
                 nsmap: Optional[NsmapType] = None,
                 schema: Optional['AbstractSchemaProxy'] = None):

        self.name = elem.tag
        self.elem = elem
        self.parent = parent
        self.position = position
        self.children = []

        if nsmap is not None:
            self.nsmap = nsmap
        else:
            try:
                self.nsmap = cast(Dict[Any, str], getattr(elem, 'nsmap'))
            except AttributeError:
                self.nsmap = {}

        if schema is None:
            self.schema = None
            self.xsd_type = None
            self.xsd_element = None
        else:
            self.set_schema(schema)

    def set_schema(self, schema: 'AbstractSchemaProxy') -> None:
        self.schema = schema
        if schema.element_type is not None:
            self.xsd_type = schema.element_type
            self.xsd_element = None
            return

        xsd_element = schema.find(self.path)
        if xsd_element is not None and hasattr(xsd_element, 'type'):
            self.xsd_element = cast(Optional[XsdElementProtocol], xsd_element)
            self.xsd_type = xsd_element.type
        else:
            self.xsd_element = None
            self.xsd_type = None

    @property
    def value(self) -> ElementType:
        return self.elem

    @property
    def attributes(self) -> List['AttributeNode']:
        if self._attributes is None:
            position = self.position + len(self.nsmap) + int('xml' not in self.nsmap) + 1
            self._attributes = [
                TextAttributeNode(name, value, self, pos, self.schema)
                for pos, (name, value) in enumerate(self.elem.attrib.items(), position)
            ]
        return self._attributes

    @property
    def base_uri(self) -> Optional[str]:
        base_uri = self.elem.get(XML_BASE)
        if isinstance(base_uri, str):
            base_uri = base_uri.strip()
        elif base_uri is not None:
            base_uri = ''
        elif self.uri is not None:
            base_uri = self.uri.strip()

        if self.parent is None:
            return base_uri
        elif base_uri is None:
            return self.parent.base_uri
        else:
            return urljoin(self.parent.base_uri or '', base_uri)

    @property
    def nilled(self) -> bool:
        return self.elem.get(XSI_NIL) in ('true', '1')

    @property
    def string_value(self) -> str:
        if self.xsd_type is not None and self.xsd_type.is_element_only():
            # Element-only text content is normalized
            return ''.join(etree_iter_strings(self.elem, normalize=True))
        return ''.join(etree_iter_strings(self.elem))

    @property
    def iter_typed_values(self) -> Iterator[AtomicType]:
        if self.xsd_type is None or \
                self.xsd_type.name in _XSD_SPECIAL_TYPES or \
                self.xsd_type.has_mixed_content():
            yield UntypedAtomic(''.join(etree_iter_strings(self.elem)))
        elif self.xsd_type.is_element_only():
            if self.schema and self.schema.is_assertion_base(self):
                self.xsd_type = self.schema.get_type(XSD_ANY_TYPE)
                yield UntypedAtomic(''.join(etree_iter_strings(self.elem)))
        elif self.xsd_type.is_element_only():
            return
        elif self.elem.get(XSI_NIL) and getattr(self.xsd_type.parent, 'nillable', None):
            return
        elif self.elem.text is not None:
            yield from get_atomic_sequence(self.xsd_type, self.elem.text, self.nsmap)
        elif self.elem.get(XSI_NIL) in ('1', 'true'):
            yield ''
        else:
            yield from get_atomic_sequence(self.xsd_type, '')

    @property
    def path(self) -> str:
        """Returns an absolute path for the node."""
        if not isinstance(self.parent, ElementNode):
            return f'/{self.elem.tag}'
        return f'{self.parent.path}/{self.elem.tag}'

    def is_typed(self) -> bool:
        return self.xsd_type is not None

    def match_name(self, name: str, default_namespace: Optional[str] = None) -> bool:
        if '*' in name:
            return match_wildcard(self.elem.tag, name)
        elif not name:
            return not self.elem.tag
        elif hasattr(self.elem, 'type'):
            return cast(XsdElementProtocol, self.elem).is_matching(name, default_namespace)
        elif name[0] == '{' or not default_namespace:
            return self.elem.tag == name
        else:
            return self.elem.tag == f'{{{default_namespace}}}{name}'

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

        if root_node.elem.__class__.__module__ not in ('lxml.etree', 'lxml.html'):
            etree = ElementTree
        else:
            etree = importlib.import_module('lxml.etree')

        if replace:
            document = etree.ElementTree()
            if sum(isinstance(x, ElementNode) for x in root_node.children) == 1:
                for child in root_node.children:
                    if isinstance(child, ElementNode):
                        document = etree.ElementTree(cast(ElementTree.Element, child.elem))
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
            document = etree.ElementTree(cast(ElementTree.Element, root_node.elem))
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

    def __iter__(self) -> Iterator[ChildNodeType]:
        if not self.children:
            if self.elem.text is not None:
                self.children.append(TextNode(self.elem.text, self))
            if len(self.elem):
                for elem in self.elem:
                    if not callable(elem.tag):
                        nsmap = cast(Dict[Any, str], getattr(elem, 'nsmap', self.nsmap))
                        self.children.append(LazyElementNode(elem, self, nsmap=nsmap))
                    elif elem.tag.__name__ == 'Comment':  # type: ignore[attr-defined]
                        self.children.append(CommentNode(elem, self))
                    else:
                        self.children.append(ProcessingInstructionNode(elem, self))

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
    elem: SchemaElemType

    __slots__ = 'nsmap',

    def __init__(self,
                 elem: SchemaElemType,
                 parent: Optional[ParentNodeType] = None,
                 position: int = 1,
                 nsmap: Optional[NsmapType] = None):

        self.name = elem.tag
        self.elem = elem
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
    def value(self) -> ElementType:
        return self.elem

    def match_name(self, name: str, default_namespace: Optional[str] = None) -> bool:
        if '*' in name:
            return match_wildcard(self.elem.tag, name)
        elif not name:
            return not self.elem.tag
        elif hasattr(self.elem, 'type'):
            return self.elem.is_matching(name, default_namespace)
        else:
            return self.elem.tag == name  # a schema

    @property
    def attributes(self) -> List['AttributeNode']:
        if self._attributes is None:
            position = self.position + len(self.nsmap) + int('xml' not in self.nsmap)
            self._attributes = [
                SchemaAttributeNode(name, attr, self, pos)
                for pos, (name, attr) in enumerate(self.elem.attrib.items(), position)
            ]
        return self._attributes

    @property
    def base_uri(self) -> Optional[str]:
        base_uri = self.uri.strip() if self.uri is not None else None
        if self.parent is None:
            return base_uri
        elif base_uri is None:
            return self.parent.base_uri
        else:
            return urljoin(self.parent.base_uri or '', base_uri)

    @property
    def type_name(self) -> Optional[str]:
        if (xsd_type := getattr(self.value, 'type', None)) is not None:
            return cast(Optional[str], xsd_type.name)
        return None

    @property
    def string_value(self) -> str:
        if not hasattr(self.elem, 'type'):
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

        if self._namespace_nodes:
            yield from self._namespace_nodes
        if self._attributes:
            yield from self._attributes

        elements = {self}
        while True:
            for child in children:
                if child in elements:
                    continue
                yield child
                elements.add(child)

                if isinstance(child, ElementNode):
                    if child._namespace_nodes:
                        yield from child._namespace_nodes
                    if child._attributes:
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

    @property
    def path(self) -> str:
        path: List[str] = []
        item: Any = self
        while True:
            if item.parent is None:
                return '/{}'.format('/'.join(reversed(path)))
            path.append(item.elem.tag)
            item = item.parent

    def is_schema_node(self) -> bool:
        return True


###
# DOCUMENT NODES

class DocumentNode(XPathNode):
    """
    A class for XPath document nodes.

    :param document: the wrapped ElementTree instance.
    :param position: the position of the node in the document, usually 1, \
    or 0 for lxml standalone root elements with siblings.
    """
    attributes: None = None
    children: List[ChildNodeType]
    is_id: None
    is_idrefs: None
    namespace_nodes: None
    nilled: None
    name: None
    parent: None
    type_name: None

    kind = 'document'
    elements: Dict[ElementProtocol, ElementNode]

    __slots__ = 'document', 'uri', 'elements', 'children'

    def __new__(cls, *args: Any, **kwargs: Any) -> 'DocumentNode':
        if cls is DocumentNode:
            return object.__new__(EtreeDocumentNode)
        return object.__new__(cls)

    def __init__(self, document: object,
                 uri: Optional[str] = None,
                 position: int = 1) -> None:

        self.document = document
        self.uri = uri
        self.name = None
        self.parent = None
        self.position = position
        self.elements = {}
        self.children = []

    def __repr__(self) -> str:
        return '%s(document=%r)' % (self.__class__.__name__, self.document)

    @property
    def base_uri(self) -> Optional[str]:
        return self.uri.strip() if self.uri is not None else None

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

    def __getitem__(self, i: Union[int, slice]) -> Union[ChildNodeType, List[ChildNodeType]]:
        return self.children[i]

    def __len__(self) -> int:
        return len(self.children)

    def __iter__(self) -> Iterator[ChildNodeType]:
        yield from self.children

    @property
    def value(self) -> object:
        return self.document

    @property
    def iter_typed_values(self) -> Iterator[UntypedAtomic]:
        yield UntypedAtomic(self.string_value)

    @property
    def document_uri(self) -> Optional[str]:
        if self.uri is not None and is_absolute_uri(self.uri):
            return self.uri.strip()
        else:
            return None

    def is_typed(self) -> bool:
        for child in self.children:
            if isinstance(child, ElementNode):
                return child.xsd_type is not None
        else:
            return False

    def is_extended(self) -> bool:
        """
        Returns `True` if the document node can't be represented with an
        ElementTree structure, `False` otherwise.
        """
        if not self.children:
            raise ElementPathRuntimeError("Missing document root")
        return len(self.children) > 1 or not isinstance(self.children[0], ElementNode)


class EtreeDocumentNode(DocumentNode):
    """
    A class for ElementTree document nodes.
    """
    document: DocumentType

    @property
    def value(self) -> DocumentType:
        return self.document

    @property
    def string_value(self) -> str:
        if not self.children:
            # Fallback for not built documents
            root = self.document.getroot()
            if root is None:
                return ''
            return ''.join(etree_iter_strings(root))
        return ''.join(child.string_value for child in self.children)

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
