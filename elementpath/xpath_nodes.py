#
# Copyright (c), 2018-2021, SISSA (International School for Advanced Studies).
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
from collections import deque
from urllib.parse import urlparse
from typing import cast, Any, Dict, Iterator, List, Optional, Tuple, Union

from .datatypes import UntypedAtomic, get_atomic_value, AtomicValueType
from .namespaces import XML_NAMESPACE, XML_BASE, XSI_NIL, \
    XSD_ANY_TYPE, XSD_ANY_SIMPLE_TYPE, XSD_ANY_ATOMIC_TYPE
from .exceptions import ElementPathTypeError, ElementPathValueError
from .protocols import ElementProtocol, LxmlElementProtocol, DocumentProtocol, \
    XsdElementProtocol, XsdAttributeProtocol, XsdTypeProtocol, XMLSchemaProtocol
from .etree import ElementType, DocumentType, etree_iter_strings, \
    is_etree_document, is_etree_element

_XSD_SPECIAL_TYPES = {XSD_ANY_TYPE, XSD_ANY_SIMPLE_TYPE, XSD_ANY_ATOMIC_TYPE}


ParentNodeType = Union[ElementProtocol, DocumentProtocol]
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
    namespaces: Any = None
    attributes: Any = None
    base_uri: Any = None
    children: Any = None
    document_uri: Any = None
    is_id: bool
    is_idrefs: bool
    nilled: Any = None
    kind: str
    name: Any = None
    type_name: Optional[str]
    value: Any

    parent: Optional[ParentNodeType] = None
    size: int  # TODO ???
    position: int  # for document total order

    @property
    def string_value(self) -> str:
        raise NotImplementedError()

    @property
    def typed_value(self) -> Optional[AtomicValueType]:
        raise NotImplementedError()

    def match(self, name: str, use_default_namespace: bool = True) -> bool:
        """
        Returns `True` if the argument is matching the name of the node, `False` otherwise.
        Raises a ValueError if the argument is used, but it's in a wrong format.

        :param name: a fully qualified name, a local name or a wildcard. The accepted \
        wildcard formats are '*', '*:*', '*:local-name' and '{namespace}*'.
        :param use_default_namespace: use the default namespace for unprefixed names.
        """
        return False


class AttributeNode(XPathNode):
    """
    A class for processing XPath attribute nodes.

    :param name: the attribute name.
    :param value: a string value or an XSD attribute when XPath is applied on a schema.
    :param parent: the parent element.
    """
    name: str
    kind = 'attribute'
    xsd_type: Optional[XsdTypeProtocol]

    __slots__ = 'name', 'value', 'parent', 'position', 'xsd_type'

    def __init__(self,
                 name: str, value: Union[str, XsdAttributeProtocol],
                 parent: Optional[ElementType] = None,
                 position: int = 1,
                 xsd_type: Optional[XsdTypeProtocol] = None) -> None:
        self.name = name
        self.value: Union[str, XsdAttributeProtocol] = value
        self.parent = parent
        self.position = position
        self.xsd_type = xsd_type

    def as_item(self) -> Tuple[str, Union[str, XsdAttributeProtocol]]:
        return self.name, self.value

    def __repr__(self) -> str:
        return '%s(name=%r, value=%r)' % (self.__class__.__name__, self.name, self.value)

    @property
    def path(self) -> str:
        if self.parent is None:
            return f'@{self.name}'
        return f'{self.parent.path}/@{self.name}'

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

    def match(self, name: str, use_default_namespace: bool = True) -> bool:
        if name == '*' or name == '*:*':
            return True
        elif not name:
            return not self.name
        elif name[0] == '*':
            try:
                _, _name = name.split(':')
            except (ValueError, IndexError):
                raise ElementPathValueError("unexpected format %r for argument 'name'" % name)
            else:
                if self.name.startswith('{'):
                    return self.name.split('}')[1] == _name
                else:
                    return self.name == _name

        elif name[-1] == '*':
            if name[0] != '{' or '}' not in name:
                raise ElementPathValueError("unexpected format %r for argument 'name'" % name)
            elif self.name.startswith('{'):
                return self.name.split('}')[0][1:] == name.split('}')[0][1:]
            else:
                return False
        else:
            return self.name == name


class NamespaceNode(XPathNode):
    """
    A class for processing XPath namespace nodes.

    :param prefix: the namespace prefix.
    :param uri: the namespace URI.
    :param parent: the parent element.
    """
    kind = 'namespace'

    __slots__ = 'prefix', 'uri', 'parent', 'position'

    def __init__(self,
                 prefix: str, uri: str,
                 parent: Optional[ElementType] = None,
                 position: int = 1) -> None:
        self.prefix = prefix
        self.uri = uri
        self.parent = parent
        self.position = position

    @property
    def name(self) -> str:
        return self.prefix

    @property
    def value(self) -> str:
        return self.uri

    def as_item(self) -> Tuple[str, str]:
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
    kind = 'text'
    value: str

    __slots__ = 'value', 'parent', 'position'

    def __init__(self,
                 value: str,
                 parent: Optional[ElementType] = None,
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
    """
    kind = 'comment'

    __slots__ = 'elem', 'parent', 'position'

    def __init__(self,
                 elem: ElementProtocol,
                 parent: Optional[ParentNodeType] = None,
                 position: int = 1) -> None:
        self.elem = elem
        self.parent = parent
        self.position = position

    def __repr__(self) -> str:
        return '%s(elem=%r)' % (self.__class__.__name__, self.elem)

    @property
    def value(self) -> ParentNodeType:
        return self.elem

    @property
    def base_uri(self) -> Optional[str]:
        if isinstance(self.parent, ElementNode):
            return self.parent.elem.get(XML_BASE)
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
    kind = 'processing-instruction'
    elem: ElementProtocol

    __slots__ = 'elem', 'parent', 'position'

    def __init__(self,
                 elem: ElementProtocol,
                 parent: Optional[ParentNodeType] = None,
                 position: int = 1) -> None:
        self.elem = elem
        self.parent = parent
        self.position = position

    def __repr__(self) -> str:
        return '%s(elem=%r)' % (self.__class__.__name__, self.elem)

    @property
    def name(self) -> str:
        try:
            # an lxml PI
            return cast(str, self.elem.target)  # type: ignore[attr-defined]
        except AttributeError:
            return cast(str, self.elem.text).split(' ', maxsplit=1)[0]

    @property
    def value(self) -> ElementProtocol:
        return self.elem

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
    kind = 'element'
    xsd_type: Optional[XsdTypeProtocol]

    tail: Optional['TextNode'] = None
    nsmap: Optional[Dict[Optional[str], str]]
    _namespaces: Optional[List['NamespaceNode']]
    attributes: List['AttributeNode']
    children: List[ChildNodeType]

    __slots__ = 'nsmap', 'elem', 'parent', 'position', 'xsd_type', \
                '_namespaces', 'attributes', 'children'

    def __init__(self,
                 elem: ElementProtocol,
                 parent: Optional[ElementType] = None,
                 position: int = 1,
                 nsmap: Optional[Any] = None,
                 xsd_type: Optional[XsdTypeProtocol] = None) -> None:

        self.elem = elem
        self.parent = parent
        self.position = position
        self.nsmap = {} if nsmap is None else nsmap
        self.xsd_type = xsd_type
        self._namespaces = None
        self.attributes = None
        self.children = []

    def __repr__(self) -> str:
        return '%s(elem=%r)' % (self.__class__.__name__, self.elem)

    def is_schema_element(self):
        return hasattr(self.elem, 'name') and hasattr(self.elem, 'type')

    @property
    def namespaces(self) -> List['NamespaceNode']:
        if self._namespaces is None:
            # Lazy generation of namespace nodes of the element
            position = self.position + 1
            self._namespaces = [NamespaceNode('xml', XML_NAMESPACE, self, position)]
            position += 1
            if self.nsmap:
                for pfx, uri in self.nsmap.items():
                    if pfx != 'xml':
                        self._namespaces.append(NamespaceNode(pfx, uri, self, position))
                        position += 1

        return self._namespaces

    @property
    def path(self) -> str:
        """Returns an absolute path for the node."""
        path = []
        item = self
        while True:
            try:
                path.append(item.elem.tag)
            except AttributeError:
                pass  # is a document node

            item = item.parent
            if item is None:
                return '/{}'.format('/'.join(reversed(path)))

    def match(self, name: str, use_default_namespace: bool = True) -> bool:
        if name == '*' or name == '*:*':
            return True
        elif not name:
            return not self.name
        elif name[0] == '*':
            try:
                _, _name = name.split(':')
            except (ValueError, IndexError):
                raise ElementPathValueError("unexpected format %r for argument 'name'" % name)
            else:
                if self.name.startswith('{'):
                    return self.name.split('}')[1] == _name
                else:
                    return self.name == _name

        elif name[-1] == '*':
            if name[0] != '{' or '}' not in name:
                raise ElementPathValueError("unexpected format %r for argument 'name'" % name)
            elif self.name.startswith('{'):
                return self.name.split('}')[0][1:] == name.split('}')[0][1:]
            else:
                return False
        elif name[0] == '{' or not use_default_namespace:
            return self.name == name
        else:
            if None in self.nsmap:
                default_namespace = self.nsmap[None]
            else:
                default_namespace = self.nsmap.get('')
            if not default_namespace:
                return self.name == name
            return self.name == '{%s}%s' % (default_namespace, name)

    def iter(self, with_self=True):
        if with_self:
            yield self

        iterators: List[Any] = deque()
        children: Iterator[Any] = iter(self.children)

        if self._namespaces:
            yield from self._namespaces
        if self.attributes:
            yield from self.attributes

        while True:
            try:
                child = next(children)
            except StopIteration:
                try:
                    children = iterators.pop()
                except IndexError:
                    return
            else:
                yield child
                if isinstance(child, ElementNode):

                    if child.namespaces:
                        yield from child.namespaces
                    if child.attributes:
                        yield from child.attributes

                    iterators.append(children)
                    children = iter(child.children)

    def iter2(self, with_self=True):
        if with_self:
            yield self

        if self._namespaces:
            yield from self._namespaces
        if self.attributes:
            yield from self.attributes

        for child in self.children:
            yield child
            if isinstance(child, ElementNode):
                yield from child.iter2()

    def iter_descendants(self, with_self=True):
        if with_self:
            yield self

        iterators: List[Any] = []
        children: Iterator[Any] = iter(self.children)

        while True:
            try:
                child = next(children)
            except StopIteration:
                try:
                    children = iterators.pop()
                except IndexError:
                    return
            else:
                if isinstance(child, TextNode) or callable(child.elem.tag):
                    yield child
                else:
                    yield child
                    iterators.append(children)
                    children = iter(child.children)

    def __getitem__(self, i: Union[int, slice]) -> Any:
        return self.children[i]

    def __len__(self) -> int:
        return len(self.children)

    def __iter__(self):
        yield from self.children

    @property
    def value(self) -> ElementType:
        return self.elem

    @property
    def name(self) -> str:
        return self.elem.tag

    @property
    def base_uri(self) -> Optional[str]:
        return self.elem.get(XML_BASE)

    @property
    def nilled(self) -> bool:
        return self.elem.get(XSI_NIL) in ('true', '1')

    @property
    def string_value(self) -> str:
        if is_schema_node(self.elem):
            schema_node = cast(XsdElementProtocol, self.elem)
            return str(get_atomic_value(schema_node.type))
        elif self.xsd_type is not None and self.xsd_type.is_element_only():
            # Element-only text content is normalized
            return ''.join(etree_iter_strings(self.elem, normalize=True))
        return ''.join(etree_iter_strings(self.elem))

    @property
    def typed_value(self) -> Optional[AtomicValueType]:
        if is_schema_node(self.elem):
            schema_node = cast(XsdElementProtocol, self.elem)
            return get_atomic_value(schema_node.type)
        elif self.xsd_type is None:
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


class DocumentNode(XPathNode):
    """
    A class for XPath document nodes.
    """
    kind = 'document'
    children: List[Union[CommentNode, ProcessingInstructionNode, ElementNode]]

    __slots__ = 'document', 'children', 'position'

    def __init__(self, document: DocumentProtocol, position: int = 1) -> None:
        self.document = document
        self.position = position
        self.children = []

    def getroot(self):
        for child in self.children:
            if isinstance(child, ElementNode):
                return child
        raise RuntimeError("Missing document root")

    def iter(self, with_self=True):
        if with_self:
            yield self

        for e in self.children:
            if callable(e.elem.tag):
                yield e
            else:
                yield from e.iter()

    def iter_descendants(self, with_self=True):
        if with_self:
            yield self

        for e in self.children:
            if callable(e.elem.tag):
                yield e
            else:
                yield from e.iter_descendants()

    def __getitem__(self, i: Union[int, slice]) -> Any:
        return self.children[i]

    def __len__(self) -> int:
        return len(self.children)

    def __iter__(self):
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


def is_schema(obj: Any) -> bool:
    return hasattr(obj, 'xsd_version') and hasattr(obj, 'maps') and not hasattr(obj, 'type')


def is_schema_node(obj: Any) -> bool:
    return hasattr(obj, 'local_name') and hasattr(obj, 'type') and hasattr(obj, 'name')


#
# Node trees builders
def get_node_tree(root: Union[DocumentNode, ElementNode, DocumentProtocol,
                              ElementProtocol, XsdElementProtocol, XMLSchemaProtocol],
                  namespaces: Optional[Dict[str, str]] = None) \
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
            return build_lxml_node_tree(root)
        return build_node_tree(root, namespaces)
    elif hasattr(root, 'xsd_version') and hasattr(root, 'maps'):
        # schema or schema node
        return build_schema_node_tree(root)
    elif is_etree_element(root) and not callable(root.tag):
        if hasattr(root, 'nsmap'):
            return build_lxml_node_tree(cast(LxmlElementProtocol, root))
        return build_node_tree(root, namespaces)
    else:
        msg = "invalid root {!r}, an Element or an ElementTree or a schema node required"
        raise ElementPathTypeError(msg.format(root))


def build_node_tree(root: Union[DocumentProtocol, ElementProtocol],
                    namespaces: Optional[Dict[str, str]] = None) \
        -> Union[DocumentNode, ElementNode]:

    def build_element_node():
        nonlocal position
        nonlocal child

        child = ElementNode(elem, parent, position, namespaces)
        position += 1

        # Do not generate namespace nodes, only reserve positions.
        if 'xml' in namespaces:
            position += len(namespaces)
        else:
            position += len(namespaces) + 1

        if elem.attrib:
            child.attributes = []
            for name, value in elem.attrib.items():
                child.attributes.append(AttributeNode(name, value, child, position))
                position += 1

        if elem.text is not None:
            child.children.append(TextNode(elem.text, child, position))
            position += 1

        return child

    position = 1
    if namespaces is None:
        namespaces = {}
    elif isinstance(namespaces, list):
        namespaces = dict(namespaces)

    if hasattr(root, 'parse'):
        document = cast(DocumentProtocol, root)
        root_node = parent = DocumentNode(document, position)
        position += 1

        elem = cast(ElementType, root.getroot())
        child = build_element_node()
        parent.children.append(child)
        parent = child
        children: Iterator[Any] = iter(elem)
    else:
        elem = cast(ElementProtocol, root)
        parent = None
        root_node = parent = build_element_node()
        children: Iterator[Any] = iter(root)

    iterators: List[Any] = []
    ancestors: List[Any] = []

    while True:
        try:
            elem = next(children)
        except StopIteration:
            try:
                children, parent = iterators.pop(), ancestors.pop()
            except IndexError:
                return root_node
        else:
            if not callable(elem.tag):
                child = build_element_node()
            elif elem.tag.__name__ == 'Comment':
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


def build_lxml_node_tree(root: Union[DocumentProtocol, LxmlElementProtocol]) \
        -> Union[DocumentNode, ElementNode]:

    def build_lxml_element_node():
        nonlocal position
        nonlocal child

        child = ElementNode(elem, parent, position, elem.nsmap)
        position += 1

        # Do not generate namespace nodes, only reserve positions.
        if 'xml' in elem.nsmap:
            position += len(elem.nsmap)
        else:
            position += len(elem.nsmap) + 1

        if elem.attrib:
            child.attributes = []
            for name, value in elem.attrib.items():
                child.attributes.append(AttributeNode(name, value, child, position))
                position += 1

        if elem.text is not None:
            child.children.append(TextNode(elem.text, child, position))
            position += 1

        return child

    position = 1
    if hasattr(root, 'parse'):
        document = cast(DocumentType, root)
        root_node = parent = DocumentNode(document, position)
        position += 1
        elem = cast(LxmlElementProtocol, root.getroot())
    else:
        # create a new ElementTree for the root element at position==0
        document = cast(LxmlElementProtocol, root).getroottree()
        root_node = parent = DocumentNode(document, 0)
        elem = document.getroot()  # the root argument may not be the actual root

    # Add root siblings (comments and processing instructions)
    for e in reversed([x for x in elem.itersiblings(preceding=True)]):
        if e.tag.__name__ == 'Comment':
            parent.children.append(CommentNode(e, parent, position))
        else:
            parent.children.append(ProcessingInstructionNode(e, parent, position))
        position += 1

    child = build_lxml_element_node()
    parent.children.append(child)

    for e in elem.itersiblings():
        if e.tag.__name__ == 'Comment':
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

    children: Iterator[Any] = iter(elem)
    while True:
        try:
            elem = next(children)
        except StopIteration:
            try:
                children, parent = iterators.pop(), ancestors.pop()
            except IndexError:
                if isinstance(root_node, ElementNode) and root_node.elem is not root:
                    for node in root_node.iter_descendants():
                        if isinstance(node, ElementNode) and node.elem is root:
                            return node
                return root_node

        else:
            if not callable(elem.tag):
                child = build_lxml_element_node()
            elif elem.tag.__name__ == 'Comment':
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


def build_schema_node_tree(schema: XMLSchemaProtocol) -> ElementNode:

    def build_schema_element_node(xsd_type=None):
        nonlocal position
        nonlocal child

        child = ElementNode(elem, parent, position, schema.namespaces, xsd_type)
        position += 1

        if elem.attributes:
            child.attributes = []
            for name, attr in elem.attributes.items():
                child.attributes.append(
                    AttributeNode(name, attr, child, position, attr.type)
                )
                position += 1

        return child

    position = 1
    children: Iterator[Any] = iter(schema)
    elem = schema
    parent = None
    root_node = parent = build_schema_element_node()

    elements = {schema}
    iterators: List[Any] = []
    ancestors: List[Any] = []

    while True:
        try:
            elem = next(children)
        except StopIteration:
            try:
                children, parent = iterators.pop(), ancestors.pop()
            except IndexError:
                return root_node
        else:
            if elem.parent is not None and elem in elements:
                continue

            elements.add(elem)
            child = build_schema_element_node(xsd_type=elem.type)
            parent.children.append(child)

            if elem.ref is None:
                ancestors.append(parent)
                parent = child
                iterators.append(children)
                children = iter(elem)
            elif elem.ref not in elements:
                elements.add(elem.ref)
                ancestors.append(parent)
                parent = child
                iterators.append(children)
                children = iter(elem.ref)
