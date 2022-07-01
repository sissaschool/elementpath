#
# Copyright (c), 2018-2022, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""
Helper functions for XPath nodes and basic data types.
"""
from urllib.parse import urlparse
from typing import cast, Any, Dict, Iterator, List, Optional, Tuple, Union

from .datatypes import UntypedAtomic, get_atomic_value, AtomicValueType
from .namespaces import XML_NAMESPACE, XML_BASE, XSI_NIL, \
    XSD_ANY_TYPE, XSD_ANY_SIMPLE_TYPE, XSD_ANY_ATOMIC_TYPE, \
    XML_ID, XSD_IDREF, XSD_IDREFS
from .exceptions import ElementPathTypeError
from .protocols import ElementProtocol, LxmlElementProtocol, DocumentProtocol, \
    XsdElementProtocol, XsdAttributeProtocol, XsdTypeProtocol, XMLSchemaProtocol
from .helpers import match_wildcard
from .etree import etree_iter_strings, is_etree_document, is_etree_element

_XSD_SPECIAL_TYPES = {XSD_ANY_TYPE, XSD_ANY_SIMPLE_TYPE, XSD_ANY_ATOMIC_TYPE}

ChildNodeType = Union['TextNode', 'ElementNode', 'CommentNode', 'ProcessingInstructionNode']


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

    # Accessors, empty sequences are represented with None values.
    kind: str = ''
    attributes: Optional[List['AttributeNode']]
    children: Optional[List[ChildNodeType]]
    parent: Union['ElementNode', 'DocumentNode', None]

    __slots__ = 'parent', 'position'

    @property
    def base_uri(self) -> Optional[str]:
        return None

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

    # Other common attributes and methods
    value: Any
    position: int  # for document total order

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
    :param parent: the parent element.
    """
    attributes: None = None
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
    def name(self) -> Optional[str]:
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
    :param parent: the parent element.
    """
    attributes: None = None
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
    :param parent: the parent element.
    """
    attributes: None = None
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
    def base_uri(self) -> Optional[str]:
        if isinstance(self.parent, ElementNode):
            return self.parent.elem.get(XML_BASE)
        return None

    @property
    def string_value(self) -> str:
        return self.value

    @property
    def typed_value(self) -> UntypedAtomic:
        return UntypedAtomic(self.value)


class CommentNode(XPathNode):
    """
    A class for processing XPath comment nodes.
    """
    attributes: None = None
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
    def base_uri(self) -> Optional[str]:
        if self.parent is not None:
            return self.parent.base_uri
        return None

    @property
    def string_value(self) -> str:
        return self.elem.text or ''

    @property
    def typed_value(self) -> str:
        return self.elem.text or ''


class ProcessingInstructionNode(XPathNode):
    """
    A class for XPath processing instructions nodes.
    """
    attributes: None = None
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
    def base_uri(self) -> Optional[str]:
        if self.parent is not None:
            return self.parent.base_uri
        return None

    @property
    def name(self) -> str:
        try:
            # an lxml PI
            return cast(str, self.elem.target)  # type: ignore[attr-defined]
        except AttributeError:
            return cast(str, self.elem.text).split(' ', maxsplit=1)[0]

    @property
    def string_value(self) -> str:
        return self.elem.text or ''

    @property
    def typed_value(self) -> str:
        return self.elem.text or ''


class ElementNode(XPathNode):
    """
    A class for processing XPath element nodes that uses lazy properties to
    diminish the average load for a tree processing.
    """
    attributes: Optional[List['AttributeNode']]
    children: List[ChildNodeType]
    document_uri: None

    kind = 'element'
    elem: Union[ElementProtocol, XsdElementProtocol, XMLSchemaProtocol]
    nsmap: Dict[Optional[str], str]
    _namespace_nodes: Optional[List['NamespaceNode']]

    __slots__ = 'nsmap', 'elem', 'xsd_type', \
                '_namespace_nodes', 'attributes', 'children'

    def __init__(self,
                 elem: Union[ElementProtocol, XsdElementProtocol, XMLSchemaProtocol],
                 parent: Optional[Union['ElementNode', 'DocumentNode']] = None,
                 position: int = 1,
                 nsmap: Optional[Dict[Any, str]] = None,
                 xsd_type: Optional[XsdTypeProtocol] = None) -> None:

        self.elem = elem
        self.parent = parent
        self.position = position
        self.nsmap = {} if nsmap is None else nsmap
        self.xsd_type = xsd_type
        self._namespace_nodes = None
        self.attributes = None
        self.children = []

    def __repr__(self) -> str:
        return '%s(elem=%r)' % (self.__class__.__name__, self.elem)

    def __getitem__(self, i: Union[int, slice]) -> Union[ChildNodeType, List[ChildNodeType]]:
        return self.children[i]

    def __len__(self) -> int:
        return len(self.children)

    def __iter__(self) -> Iterator[ChildNodeType]:
        yield from self.children

    @property
    def value(self) -> Union[ElementProtocol, XsdElementProtocol, XMLSchemaProtocol]:
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
        return self.elem.get(XML_BASE)

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
        if self.xsd_type is None:
            return UntypedAtomic(''.join(etree_iter_strings(self.elem)))
        elif self.xsd_type.name in _XSD_SPECIAL_TYPES:
            return UntypedAtomic(self.elem.text or '')
        elif self.xsd_type.has_mixed_content():
            return UntypedAtomic(self.elem.text or '')
        elif self.xsd_type.is_element_only():
            return None
        elif self.xsd_type.is_empty():
            return None
        elif self.elem.get(XSI_NIL) and getattr(self.xsd_type.parent, 'nillable', None):
            return None

        if self.elem.text is not None:
            value = self.xsd_type.decode(self.elem.text)
        elif self.elem.get(XSI_NIL) in ('1', 'true'):
            return ''
        else:
            value = self.xsd_type.decode(self.elem.text)

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

    def is_schema_element(self) -> bool:
        return hasattr(self.elem, 'name') and hasattr(self.elem, 'type')

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

    def iter(self) -> Iterator[XPathNode]:
        yield self

        iterators: List[Any] = []
        children: Iterator[Any] = iter(self.children)

        if self._namespace_nodes:
            yield from self._namespace_nodes
        if self.attributes:
            yield from self.attributes

        while True:
            for child in children:
                yield child

                if isinstance(child, ElementNode):
                    if child._namespace_nodes:
                        yield from child._namespace_nodes
                    if child.attributes:
                        yield from child.attributes

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


class SchemaNode(ElementNode):

    __slots__ = '__dict__',

    elem: Union[XsdElementProtocol, XMLSchemaProtocol]
    ref: Optional['SchemaNode'] = None

    def __iter__(self) -> Iterator[ChildNodeType]:
        if self.ref is None:
            yield from self.children
        else:
            yield from self.ref.children

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
        if self.attributes:
            yield from self.attributes

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
                    if child.attributes:
                        yield from child.attributes

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


class DocumentNode(XPathNode):
    """
    A class for XPath document nodes.
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

    __slots__ = 'document', 'children'

    def __init__(self, document: DocumentProtocol, position: int = 1) -> None:
        self.document = document
        self.parent = None
        self.position = position
        self.children = []

    @property
    def base_uri(self) -> Optional[str]:
        if not self.children:
            return None
        return self.getroot().base_uri

    def getroot(self) -> ElementNode:
        for child in self.children:
            if isinstance(child, ElementNode):
                return child
        raise RuntimeError("Missing document root")

    def iter(self) -> Iterator[XPathNode]:
        yield self

        for e in self.children:
            if isinstance(e, ElementNode):
                yield from e.iter()
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
        return ''.join(etree_iter_strings(self.document.getroot()))

    @property
    def typed_value(self) -> UntypedAtomic:
        return UntypedAtomic(''.join(etree_iter_strings(self.document.getroot())))

    @property
    def document_uri(self) -> Optional[str]:
        try:
            uri = cast(str, self.document.getroot().attrib[XML_BASE])
            parts = urlparse(uri)
        except (KeyError, ValueError):
            pass
        else:
            if parts.scheme and parts.netloc or parts.path.startswith('/'):
                return uri
        return None


#
# Helper functions and type aliases

def is_schema(obj: Any) -> bool:
    return hasattr(obj, 'xsd_version') and hasattr(obj, 'maps') and not hasattr(obj, 'type')


def is_schema_node(obj: Any) -> bool:
    return hasattr(obj, 'local_name') and hasattr(obj, 'type') and hasattr(obj, 'name')


def is_xpath_node(obj: Any) -> bool:
    return isinstance(obj, XPathNode) or is_etree_element(obj) or is_etree_document(obj)


RootArgType = Union[DocumentProtocol, DocumentNode, ElementProtocol,
                    XsdElementProtocol, XMLSchemaProtocol, ElementNode]


#
# Node trees builders
def get_node_tree(root: RootArgType, namespaces: Optional[Dict[str, str]] = None) \
        -> Union[DocumentNode, ElementNode]:
    """
    Returns a tree of XPath nodes that wrap the provided root tree.

    :param root: an Element or an ElementTree or a schema or a schema element.
    :param namespaces: an optional mapping from prefixes to namespace URIs, \
    Ignored if root is a lxml etree or a schema structure.
    """
    if isinstance(root, (DocumentNode, ElementNode)):
        return root
    elif is_etree_document(root):
        if hasattr(root, 'xpath'):
            return build_lxml_node_tree(cast(DocumentProtocol, root))
        return build_node_tree(
            cast(DocumentProtocol, root), namespaces
        )
    elif hasattr(root, 'xsd_version') and hasattr(root, 'maps'):
        # schema or schema node
        return build_schema_node_tree(
            cast(Union[XsdElementProtocol, XMLSchemaProtocol], root)
        )
    elif is_etree_element(root) and not callable(root.tag):  # type: ignore[union-attr]
        if hasattr(root, 'nsmap') and hasattr(root, 'xpath'):
            return build_lxml_node_tree(cast(LxmlElementProtocol, root))
        return build_node_tree(
            cast(ElementProtocol, root), namespaces
        )
    else:
        msg = "invalid root {!r}, an Element or an ElementTree or a schema node required"
        raise ElementPathTypeError(msg.format(root))


def build_node_tree(root: Union[DocumentProtocol, ElementProtocol],
                    namespaces: Optional[Dict[str, str]] = None) \
        -> Union[DocumentNode, ElementNode]:
    root_node: Union[DocumentNode, ElementNode]
    parent: Any
    child: ChildNodeType
    children: Iterator[Any]

    position = 1

    def build_element_node() -> ElementNode:
        nonlocal position

        node = ElementNode(elem, parent, position, nsmap)
        position += 1

        # Do not generate namespace nodes, only reserve positions.
        position += len(nsmap) if 'xml' in nsmap else len(nsmap) + 1

        if elem.attrib:
            node.attributes = [
                AttributeNode(name, value, node, pos)
                for pos, (name, value) in enumerate(elem.attrib.items(), position)
            ]
            position += len(node.attributes)

        if elem.text is not None:
            node.children.append(TextNode(elem.text, node, position))
            position += 1

        return node

    # Common nsmap
    nsmap = {} if namespaces is None else dict(namespaces)

    if hasattr(root, 'parse'):
        document = cast(DocumentProtocol, root)
        root_node = parent = DocumentNode(document, position)
        position += 1

        elem = document.getroot()
        child = build_element_node()
        parent.children.append(child)
        parent = child
    else:
        elem = cast(ElementProtocol, root)
        parent = None
        root_node = parent = build_element_node()

    children = iter(elem)
    iterators: List[Any] = []
    ancestors: List[Any] = []

    while True:
        for elem in children:
            if not callable(elem.tag):
                child = build_element_node()
            elif elem.tag.__name__ == 'Comment':  # type: ignore[attr-defined]
                child = CommentNode(elem, parent, position)
                position += 1
            else:
                child = ProcessingInstructionNode(elem, parent, position)

            parent.children.append(child)
            if elem.tail is not None:
                parent.children.append(TextNode(elem.tail, parent, position))
                position += 1

            if len(elem):
                ancestors.append(parent)
                parent = child
                iterators.append(children)
                children = iter(elem)
                break
        else:
            try:
                children, parent = iterators.pop(), ancestors.pop()
            except IndexError:
                return root_node


def build_lxml_node_tree(root: Union[DocumentProtocol, LxmlElementProtocol]) \
        -> Union[DocumentNode, ElementNode]:
    root_node: Union[DocumentNode, ElementNode]
    parent: Any
    child: ChildNodeType
    children: Iterator[Any]

    position = 1

    def build_lxml_element_node() -> ElementNode:
        nonlocal position

        node = ElementNode(elem, parent, position, elem.nsmap)
        position += 1

        # Do not generate namespace nodes, only reserve positions.
        position += len(elem.nsmap) if 'xml' in elem.nsmap else len(elem.nsmap) + 1

        if elem.attrib:
            node.attributes = [
                AttributeNode(name, value, node, pos)
                for pos, (name, value) in enumerate(elem.attrib.items(), position)
            ]
            position += len(node.attributes)

        if elem.text is not None:
            node.children.append(TextNode(elem.text, node, position))
            position += 1

        return node

    if hasattr(root, 'parse'):
        document = cast(DocumentProtocol, root)
        root_node = parent = DocumentNode(document, position)
        position += 1
    else:
        # create a new ElementTree for the root element at position==0
        document = cast(LxmlElementProtocol, root).getroottree()
        root_node = parent = DocumentNode(document, 0)

    elem = cast(LxmlElementProtocol, document.getroot())

    # Add root siblings (comments and processing instructions)
    for e in reversed([x for x in elem.itersiblings(preceding=True)]):
        if e.tag.__name__ == 'Comment':  # type: ignore[attr-defined]
            parent.children.append(CommentNode(e, parent, position))
        else:
            parent.children.append(ProcessingInstructionNode(e, parent, position))
        position += 1

    child = build_lxml_element_node()
    parent.children.append(child)

    for e in elem.itersiblings():
        if e.tag.__name__ == 'Comment':  # type: ignore[attr-defined]
            parent.children.append(CommentNode(e, parent, position))
        else:
            parent.children.append(ProcessingInstructionNode(e, parent, position))
        position += 1

    if not root_node.position and len(parent.children) == 1:
        # Remove non-root document if root element has no siblings
        root_node = child
        root_node.parent = None

    parent = child
    iterators: List[Any] = []
    ancestors: List[Any] = []

    children = iter(elem)
    while True:
        for elem in children:
            if not callable(elem.tag):
                child = build_lxml_element_node()
            elif elem.tag.__name__ == 'Comment':  # type: ignore[attr-defined]
                child = CommentNode(elem, parent, position)
                position += 1
            else:
                child = ProcessingInstructionNode(elem, parent, position)

            parent.children.append(child)
            if elem.tail is not None:
                parent.children.append(TextNode(elem.tail, parent, position))
                position += 1

            if len(elem):
                ancestors.append(parent)
                parent = child
                iterators.append(children)
                children = iter(elem)
                break
        else:
            try:
                children, parent = iterators.pop(), ancestors.pop()
            except IndexError:
                if isinstance(root_node, ElementNode) and root_node.elem is not root:
                    for _node in root_node.iter_descendants():
                        if isinstance(_node, ElementNode) and _node.elem is root:
                            return _node
                return root_node


def build_schema_node_tree(root: Union[XsdElementProtocol, XMLSchemaProtocol],
                           global_elements: Optional[List[ChildNodeType]] = None) -> SchemaNode:
    parent: Any
    elem: Any
    child: SchemaNode
    children: Iterator[Any]

    position = 1

    def build_schema_element_node() -> SchemaNode:
        nonlocal position

        node = SchemaNode(elem, parent, position, elem.namespaces)
        position += 1

        if elem.attrib:
            node.attributes = [
                AttributeNode(name, attr, elem, pos, attr.type)
                for pos, (name, attr) in enumerate(elem.attrib.items(), position)
            ]
            position += len(node.attributes)

        return node

    children = iter(root)
    elem = root
    parent = None
    root_node = parent = build_schema_element_node()

    if global_elements is not None:
        global_elements.append(root_node)
    elif is_schema(root):
        global_elements = root_node.children
    else:
        # Track global elements even if the initial root is not a schema to avoid circularity
        global_elements = []

    local_nodes = {root: root_node}  # Irrelevant even if it's the schema
    ref_nodes: List[SchemaNode] = []
    iterators: List[Any] = []
    ancestors: List[Any] = []

    while True:
        for elem in children:
            child = build_schema_element_node()
            child.xsd_type = elem.type
            parent.children.append(child)

            if elem in local_nodes:
                if elem.ref is None:
                    child.children = local_nodes[elem].children
                else:
                    ref_nodes.append(child)
            else:
                local_nodes[elem] = child
                if elem.ref is None:
                    ancestors.append(parent)
                    parent = child
                    iterators.append(children)
                    children = iter(elem)
                    break
                else:
                    ref_nodes.append(child)
        else:
            try:
                children, parent = iterators.pop(), ancestors.pop()
            except IndexError:
                # connect references to proper nodes
                for element_node in ref_nodes:
                    ref = cast(XsdElementProtocol, element_node.elem).ref
                    assert ref is not None

                    other: Any
                    for other in global_elements:
                        if other.elem is ref:
                            element_node.ref = other
                            break
                    else:
                        # Extend node tree with other globals
                        element_node.ref = build_schema_node_tree(ref, global_elements)

                return root_node
