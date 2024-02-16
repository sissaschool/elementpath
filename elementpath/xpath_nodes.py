#
# Copyright (c), 2018-2022, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from importlib import import_module
from urllib.parse import urljoin
from types import ModuleType
from typing import cast, Any, Dict, Iterator, List, MutableMapping, Optional, Tuple, Union

from .datatypes import UntypedAtomic, get_atomic_value, AtomicValueType
from .namespaces import XML_NAMESPACE, XML_BASE, XSI_NIL, \
    XSD_ANY_TYPE, XSD_ANY_SIMPLE_TYPE, XSD_ANY_ATOMIC_TYPE, \
    XML_ID, XSD_IDREF, XSD_IDREFS
from .protocols import ElementProtocol, DocumentProtocol, XsdElementProtocol, \
    XsdAttributeProtocol, XsdTypeProtocol, XsdSchemaProtocol
from .helpers import match_wildcard, is_absolute_uri
from .etree import etree_iter_strings, is_etree_element, is_etree_document

__all__ = ['is_xpath_node', 'SchemaElemType', 'ChildNodeType', 'ElementMapType',
           'XPathNode', 'AttributeNode', 'NamespaceNode', 'TextNode',
           'CommentNode', 'ProcessingInstructionNode', 'ElementNode',
           'LazyElementNode', 'SchemaElementNode', 'DocumentNode']

_XSD_SPECIAL_TYPES = {XSD_ANY_TYPE, XSD_ANY_SIMPLE_TYPE, XSD_ANY_ATOMIC_TYPE}

SchemaElemType = Union[XsdSchemaProtocol, XsdElementProtocol]
ChildNodeType = Union['TextNode', 'ElementNode', 'CommentNode', 'ProcessingInstructionNode']
ElementMapType = Dict[Union[ElementProtocol, SchemaElemType], 'ElementNode']


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
    """The base class of all XPath nodes. Used only for type checking."""

    # Accessors, empty sequences are represented with None values.
    kind: str = ''
    children: Optional[List[ChildNodeType]]
    parent: Union['ElementNode', 'DocumentNode', None]

    __slots__ = 'parent', 'position'

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
    def namespace_nodes(self) -> Optional[List['NamespaceNode']]:
        return None

    @property
    def nilled(self) -> Optional[bool]:
        return None

    @property
    def name(self) -> Optional[str]:
        return None

    @property
    def type_name(self) -> Optional[str]:
        return None

    @property
    def string_value(self) -> str:
        raise NotImplementedError()

    @property
    def typed_value(self) -> Optional[AtomicValueType]:
        raise NotImplementedError()

    # Other common attributes, properties and methods
    value: Any
    position: int  # for document total order

    @property
    def root_node(self, namespace: Optional[str] = None) -> 'XPathNode':
        return self if self.parent is None else self.parent.root_node

    def is_schema_node(self) -> Optional[bool]:
        return None

    def match_name(self, name: str, default_namespace: Optional[str] = None) -> bool:
        """
        Returns `True` if the argument is matching the name of the node, `False` otherwise.
        Raises a ValueError if the argument is used, but it's in a wrong format.

        :param name: a fully qualified name, a local name or a wildcard. The accepted \
        wildcard formats are '*', '*:*', '*:local-name' and '{namespace}*'.
        :param default_namespace: the default namespace for unprefixed names.
        """
        return False


class AttributeNode(XPathNode):
    """
    A class for processing XPath attribute nodes.

    :param name: the attribute name.
    :param value: a string value or an XSD attribute when XPath is applied on a schema.
    :param parent: the parent element node.
    :param position: the position of the node in the document.
    :param xsd_type: an optional XSD type associated with the attribute node.
    """
    attributes: None
    children: None = None
    base_uri: None
    document_uri: None
    namespace_nodes: None
    nilled: None
    parent: Optional['ElementNode']

    kind = 'attribute'

    __slots__ = '_name', 'value', 'xsd_type'

    def __init__(self,
                 name: str, value: Union[str, XsdAttributeProtocol],
                 parent: Optional['ElementNode'] = None,
                 position: int = 1,
                 xsd_type: Optional[XsdTypeProtocol] = None) -> None:
        self._name = name
        self.value: Union[str, XsdAttributeProtocol] = value
        self.parent = parent
        self.position = position
        self.xsd_type = xsd_type

    @property
    def is_id(self) -> bool:
        return self._name == XML_ID or self.xsd_type is not None and self.xsd_type.is_key()

    @property
    def is_idrefs(self) -> bool:
        if self.xsd_type is None:
            return False
        root_type = self.xsd_type.root_type
        return root_type.name == XSD_IDREF or root_type.name == XSD_IDREFS

    @property
    def name(self) -> str:
        return self._name

    @property
    def type_name(self) -> Optional[str]:
        if self.xsd_type is None:
            return None
        return self.xsd_type.name

    @property
    def string_value(self) -> str:
        if isinstance(self.value, str):
            return self.value
        return str(get_atomic_value(self.value.type))

    @property
    def typed_value(self) -> AtomicValueType:
        if not isinstance(self.value, str):
            return get_atomic_value(self.value.type)
        elif self.xsd_type is None or self.xsd_type.name in _XSD_SPECIAL_TYPES:
            return UntypedAtomic(self.value)
        return cast(AtomicValueType, self.xsd_type.decode(self.value))

    def as_item(self) -> Tuple[str, Union[str, XsdAttributeProtocol]]:
        return self._name, self.value

    def __repr__(self) -> str:
        return '%s(name=%r, value=%r)' % (self.__class__.__name__, self._name, self.value)

    @property
    def path(self) -> str:
        if self.parent is None:
            return f'@{self._name}'
        return f'{self.parent.path}/@{self._name}'

    def is_schema_node(self) -> bool:
        return hasattr(self.value, 'name') and hasattr(self.value, 'type')

    def match_name(self, name: str, default_namespace: Optional[str] = None) -> bool:
        if '*' in name:
            return match_wildcard(self._name, name)
        else:
            return self._name == name


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

    __slots__ = 'prefix', 'uri'

    def __init__(self,
                 prefix: Optional[str], uri: str,
                 parent: Optional['ElementNode'] = None,
                 position: int = 1) -> None:
        self.prefix = prefix
        self.uri = uri
        self.parent = parent
        self.position = position

    @property
    def name(self) -> Optional[str]:
        return self.prefix

    @property
    def value(self) -> str:
        return self.uri

    def as_item(self) -> Tuple[Optional[str], str]:
        return self.prefix, self.uri

    def __repr__(self) -> str:
        return '%s(prefix=%r, uri=%r)' % (self.__class__.__name__, self.prefix, self.uri)

    @property
    def string_value(self) -> str:
        return self.uri

    @property
    def typed_value(self) -> str:
        return self.uri


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
    name: None
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
    def typed_value(self) -> UntypedAtomic:
        return UntypedAtomic(self.value)


class CommentNode(XPathNode):
    """
    A class for processing XPath comment nodes.

    :param elem: the wrapped Comment Element.
    :param parent: the parent element node.
    :param position: the position of the node in the document.
    """
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
                 elem: ElementProtocol,
                 parent: Union['ElementNode', 'DocumentNode', None] = None,
                 position: int = 1) -> None:
        self.elem = elem
        self.parent = parent
        self.position = position

    def __repr__(self) -> str:
        return '%s(elem=%r)' % (self.__class__.__name__, self.elem)

    @property
    def value(self) -> ElementProtocol:
        return self.elem

    @property
    def string_value(self) -> str:
        return self.elem.text or ''

    @property
    def typed_value(self) -> str:
        return self.elem.text or ''


class ProcessingInstructionNode(XPathNode):
    """
    A class for XPath processing instructions nodes.

    :param elem: the wrapped Processing Instruction Element.
    :param parent: the parent element node.
    :param position: the position of the node in the document.
    """
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
                 elem: ElementProtocol,
                 parent: Union['ElementNode', 'DocumentNode', None] = None,
                 position: int = 1) -> None:
        self.elem = elem
        self.parent = parent
        self.position = position

    def __repr__(self) -> str:
        return '%s(elem=%r)' % (self.__class__.__name__, self.elem)

    @property
    def value(self) -> ElementProtocol:
        return self.elem

    @property
    def name(self) -> str:
        try:
            # an lxml PI
            return cast(str, self.elem.target)  # type: ignore[attr-defined]
        except AttributeError:
            return cast(str, self.elem.text).split(' ', maxsplit=1)[0]

    @property
    def string_value(self) -> str:
        if hasattr(self.elem, 'target'):
            return self.elem.text or ''

        try:
            return cast(str, self.elem.text).split(' ', maxsplit=1)[1]
        except IndexError:
            return ''

    @property
    def typed_value(self) -> str:
        return self.string_value


class ElementNode(XPathNode):
    """
    A class for processing XPath element nodes that uses lazy properties to
    diminish the average load for a tree processing.

    :param elem: the wrapped Element or XSD schema/element.
    :param parent: the parent document node or element node.
    :param position: the position of the node in the document.
    :param nsmap: an optional mapping from prefix to namespace URI.
    :param xsd_type: an optional XSD type associated with the element node.
    """
    children: List[ChildNodeType]
    document_uri: None

    kind = 'element'
    elem: Union[ElementProtocol, SchemaElemType]
    nsmap: MutableMapping[Optional[str], str]
    elements: Optional[ElementMapType]
    _namespace_nodes: Optional[List['NamespaceNode']]
    _attributes: Optional[List['AttributeNode']]

    uri: Optional[str] = None

    __slots__ = 'nsmap', 'elem', 'xsd_type', 'elements', \
                '_namespace_nodes', '_attributes', 'children', '__dict__'

    def __init__(self,
                 elem: Union[ElementProtocol, SchemaElemType],
                 parent: Optional[Union['ElementNode', 'DocumentNode']] = None,
                 position: int = 1,
                 nsmap: Optional[MutableMapping[Any, str]] = None,
                 xsd_type: Optional[XsdTypeProtocol] = None) -> None:

        self.elem = elem
        self.parent = parent
        self.position = position
        self.xsd_type = xsd_type
        self.elements = None
        self._namespace_nodes = None
        self._attributes = None
        self.children = []

        if nsmap is not None:
            self.nsmap = nsmap
        else:
            try:
                self.nsmap = cast(Dict[Any, str], getattr(elem, 'nsmap'))
            except AttributeError:
                self.nsmap = {}

    def __repr__(self) -> str:
        return '%s(elem=%r)' % (self.__class__.__name__, self.elem)

    def __getitem__(self, i: Union[int, slice]) -> Union[ChildNodeType, List[ChildNodeType]]:
        return self.children[i]

    def __len__(self) -> int:
        return len(self.children)

    def __iter__(self) -> Iterator[ChildNodeType]:
        yield from self.children

    @property
    def value(self) -> Union[ElementProtocol, SchemaElemType]:
        return self.elem

    @property
    def is_id(self) -> bool:
        return False

    @property
    def is_idrefs(self) -> bool:
        return False

    @property
    def name(self) -> str:
        return self.elem.tag

    @property
    def type_name(self) -> Optional[str]:
        if self.xsd_type is None:
            return None
        return self.xsd_type.name

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
    def typed_value(self) -> Optional[AtomicValueType]:
        if self.xsd_type is None or \
                self.xsd_type.name in _XSD_SPECIAL_TYPES or \
                self.xsd_type.has_mixed_content():
            return UntypedAtomic(''.join(etree_iter_strings(self.elem)))
        elif self.xsd_type.is_element_only() or self.xsd_type.is_empty():
            return None
        elif self.elem.get(XSI_NIL) and getattr(self.xsd_type.parent, 'nillable', None):
            return None

        if self.elem.text is not None:
            value = self.xsd_type.decode(self.elem.text)
        elif self.elem.get(XSI_NIL) in ('1', 'true'):
            return ''
        else:
            value = self.xsd_type.decode('')

        return cast(Optional[AtomicValueType], value)

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
        if self._attributes is None:
            position = self.position + len(self.nsmap) + int('xml' not in self.nsmap)
            self._attributes = [
                AttributeNode(name, value, self, pos)
                for pos, (name, value) in enumerate(self.elem.attrib.items(), position)
            ]
        return self._attributes

    @property
    def path(self) -> str:
        """Returns an absolute path for the node."""
        path = []
        item: Any = self
        while True:
            if isinstance(item, ElementNode):
                path.append(item.elem.tag)

            item = item.parent
            if item is None:
                return '/{}'.format('/'.join(reversed(path)))

    def is_schema_node(self) -> bool:
        return hasattr(self.elem, 'name') and hasattr(self.elem, 'type')

    is_schema_element = is_schema_node

    def match_name(self, name: str, default_namespace: Optional[str] = None) -> bool:
        if '*' in name:
            return match_wildcard(self.elem.tag, name)
        elif not name:
            return not self.elem.tag
        elif hasattr(self.elem, 'type'):
            return cast(XsdElementProtocol, self.elem).is_matching(name, default_namespace)
        elif name[0] == '{' or default_namespace is None:
            return self.elem.tag == name

        if None in self.nsmap:
            default_namespace = self.nsmap[None]  # lxml element in-scope namespaces

        if default_namespace:
            return self.elem.tag == '{%s}%s' % (default_namespace, name)
        return self.elem.tag == name

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

    def iter(self) -> Iterator[XPathNode]:
        # Iterate the tree not including the not built lazy components.
        yield self

        iterators: List[Any] = []
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

    def iter_document(self) -> Iterator[XPathNode]:
        # Iterate the tree but building lazy components.
        # Rarely used, don't need optimization.
        yield self
        yield from self.namespace_nodes
        yield from self.attributes

        for child in self:
            if isinstance(child, ElementNode):
                yield from child.iter()
            else:
                yield child

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

    def __init__(self, document: DocumentProtocol,
                 uri: Optional[str] = None,
                 position: int = 1) -> None:
        self.document = document
        self.uri = uri
        self.parent = None
        self.position = position
        self.elements = {}
        self.children = []

    def __repr__(self) -> str:
        return '%s(document=%r)' % (self.__class__.__name__, self.document)

    @property
    def base_uri(self) -> Optional[str]:
        return self.uri.strip() if self.uri is not None else None

    def getroot(self) -> ElementNode:
        for child in self.children:
            if isinstance(child, ElementNode):
                return child
        raise RuntimeError("Missing document root")

    def get_element_node(self, elem: ElementProtocol) -> Optional[ElementNode]:
        return self.elements.get(elem)

    def iter(self) -> Iterator[XPathNode]:
        yield self

        for e in self.children:
            if isinstance(e, ElementNode):
                yield from e.iter()
            else:
                yield e

    def iter_document(self) -> Iterator[XPathNode]:
        yield self

        for e in self.children:
            if isinstance(e, ElementNode):
                yield from e.iter_document()
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
    def value(self) -> DocumentProtocol:
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

    @property
    def typed_value(self) -> UntypedAtomic:
        return UntypedAtomic(self.string_value)

    @property
    def document_uri(self) -> Optional[str]:
        if self.uri is not None and is_absolute_uri(self.uri):
            return self.uri.strip()
        else:
            return None

    def is_extended(self) -> bool:
        """
        Returns `True` if the document node cannot be represented with an
        ElementTree structure, `False` otherwise.
        """
        root = self.document.getroot()
        if root is None or not is_etree_element(root):
            return True
        elif not self.children:
            raise RuntimeError("Missing document root")
        elif len(self.children) == 1:
            return not isinstance(self.children[0], ElementNode)
        elif not hasattr(root, 'itersiblings'):
            return True  # an extended xml.etree.ElementTree structure
        elif any(isinstance(x, TextNode) for x in root):
            return True
        else:
            return sum(isinstance(x, ElementNode) for x in root) != 1

    @classmethod
    def from_element_node(cls, root_node: ElementNode, replace: bool = True) -> 'DocumentNode':
        """
        Build a `DocumentNode` from a tree based on an ElementNode.

        :param root_node: the root element node.
        :param replace: if `True` the root element is replaced by a document node. \
        This is usually useful for extended data models (more element children, text nodes).
        """
        etree_module_name = root_node.elem.__class__.__module__
        etree: ModuleType = import_module(etree_module_name)

        assert root_node.elements is not None, "Not a root element node"
        assert all(not isinstance(x, SchemaElementNode) for x in root_node.elements)
        elements = cast(Dict[ElementProtocol, ElementNode], root_node.elements)

        if replace:
            document = etree.ElementTree()
            if sum(isinstance(x, ElementNode) for x in root_node.children) == 1:
                for child in root_node.children:
                    if isinstance(child, ElementNode):
                        document = etree.ElementTree(child.elem)
                        break

            document_node = cls(document, root_node.uri, root_node.position)
            for child in root_node.children:
                document_node.children.append(child)
                child.parent = document_node

            elements.pop(root_node, None)  # type: ignore[call-overload]
            document_node.elements = elements
            del root_node
            return document_node

        else:
            document = etree.ElementTree(root_node.elem)
            document_node = cls(document, root_node.uri, root_node.position - 1)
            document_node.children.append(root_node)
            root_node.parent = document_node
            document_node.elements = elements

        return document_node


###
# Specialized element nodes

class LazyElementNode(ElementNode):
    """
    A fully lazy element node, slower but better if the node does not
    to be used in a document context. The node extends descendants but
    does not record positions and a map of elements.
    """
    __slots__ = ()

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
    __slots__ = ()

    ref: Optional['SchemaElementNode'] = None
    elem: SchemaElemType

    def __iter__(self) -> Iterator[ChildNodeType]:
        if self.ref is None:
            yield from self.children
        else:
            yield from self.ref.children

    @property
    def attributes(self) -> List['AttributeNode']:
        if self._attributes is None:
            position = self.position + len(self.nsmap) + int('xml' not in self.nsmap)
            self._attributes = [
                AttributeNode(name, attr, self, pos, attr.type)
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
    def string_value(self) -> str:
        if not hasattr(self.elem, 'type'):
            return ''
        schema_node = cast(XsdElementProtocol, self.elem)
        return str(get_atomic_value(schema_node.type))

    @property
    def typed_value(self) -> Optional[AtomicValueType]:
        if not hasattr(self.elem, 'type'):
            return UntypedAtomic('')
        schema_node = cast(XsdElementProtocol, self.elem)
        return get_atomic_value(schema_node.type)

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


def is_xpath_node(obj: Any) -> bool:
    return isinstance(obj, XPathNode) or is_etree_element(obj) or is_etree_document(obj)
