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
from typing import TYPE_CHECKING, cast, Any, Dict, Iterator, List, Optional, Tuple, Union

from .datatypes import UntypedAtomic, get_atomic_value, AtomicValueType
from .namespaces import XML_NAMESPACE, XML_BASE, XSI_NIL, \
    XSD_ANY_TYPE, XSD_ANY_SIMPLE_TYPE, XSD_ANY_ATOMIC_TYPE
from .exceptions import ElementPathValueError
from .protocols import ElementProtocol, LxmlElementProtocol, DocumentProtocol, \
    XsdElementProtocol, XsdAttributeProtocol, XsdTypeProtocol
from .etree import ElementType, DocumentType, etree_iter_strings

if TYPE_CHECKING:
    from .xpath_context import XPathContext

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
    parent: Optional[ParentNodeType] = None
    type_name: Optional[str]
    value: Any = None

    context: 'XPathContext'
    position: int  # position in context, for document total order.

    __slots__ = 'context', 'position'

    def __init__(self, context: 'XPathContext') -> None:
        self.context = context
        context.total_nodes += 1
        self.position = context.total_nodes

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

    __slots__ = 'name', 'value', 'parent', 'xsd_type'

    def __init__(self, context: 'XPathContext',
                 name: str, value: Union[str, XsdAttributeProtocol],
                 parent: Optional[ElementType] = None,
                 xsd_type: Optional[XsdTypeProtocol] = None) -> None:
        super().__init__(context)
        self.name = name
        self.value: Union[str, XsdAttributeProtocol] = value
        self.parent = parent
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

    __slots__ = 'prefix', 'uri', 'parent'

    def __init__(self, context: 'XPathContext',
                 prefix: str, uri: str,
                 parent: Optional[ElementType] = None) -> None:
        super().__init__(context)
        self.prefix = prefix
        self.uri = uri
        self.parent = parent

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

    __slots__ = 'value', 'parent'

    def __init__(self, context: 'XPathContext',
                 value: str,
                 parent: Optional[ElementType] = None) -> None:
        super().__init__(context)
        self.value = value
        self.parent = parent

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

    __slots__ = 'elem', 'parent'

    def __init__(self, context: 'XPathContext',
                 elem: ElementProtocol,
                 parent: Optional[ParentNodeType] = None) -> None:
        super().__init__(context)
        self.elem = elem
        self.parent = parent

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

    __slots__ = 'elem', 'parent'

    def __init__(self, context: 'XPathContext',
                 elem: ElementProtocol,
                 parent: Optional[ParentNodeType] = None) -> None:
        super().__init__(context)
        self.elem = elem
        self.parent = parent

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
    nsmap: Dict[Optional[str], str]
    namespaces: List['NamespaceNode']
    attrib: List['AttributeNode']
    children: List[ChildNodeType]

    __slots__ = 'nsmap', 'namespaces', 'elem', 'parent', 'xsd_type', 'attributes', 'children'

    def __init__(self, context: 'XPathContext',
                 elem: ElementProtocol,
                 parent: Optional[ElementType] = None,
                 xsd_type: Optional[XsdTypeProtocol] = None) -> None:

        if hasattr(elem, 'nsmap'):
            self.nsmap = cast(LxmlElementProtocol, elem).nsmap
        else:
            self.nsmap = context.namespaces

        if 'xml' in self.nsmap:
            self.namespaces = [
                NamespaceNode(context, pfx, uri, self) for pfx, uri in self.nsmap.items()
            ]
        else:
            self.namespaces = [NamespaceNode(context, 'xml', XML_NAMESPACE, self)]
            self.namespaces.extend(
                NamespaceNode(context, pfx, uri, self) for pfx, uri in self.nsmap.items()
            )

        super().__init__(context)
        self.elem = elem
        self.parent = parent
        self.xsd_type = xsd_type

        self.attributes = [AttributeNode(context, name, value, self)
                           for name, value in elem.attrib.items()]

        if elem.text is not None:
            self.children = [TextNode(context, elem.text, self)]
        else:
            self.children = []

    def __repr__(self) -> str:
        return '%s(elem=%r)' % (self.__class__.__name__, self.elem)

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

        yield from self.namespaces
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
                    yield from child.namespaces
                    yield from child.attributes

                    iterators.append(children)
                    children = iter(child.children)

    def iter2(self, with_self=True):
        if with_self:
            yield self

        yield from self.namespaces
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

    __slots__ = 'document', 'children'

    def __init__(self, context: 'XPathContext', document: DocumentType) -> None:
        super().__init__(context)
        self.document = document
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
    def value(self) -> DocumentType:
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
    if isinstance(obj, XPathNode):
        obj = obj.value
    return hasattr(obj, 'xsd_version') and hasattr(obj, 'maps')


def is_schema_node(obj: Any) -> bool:
    if isinstance(obj, XPathNode):
        obj = obj.value
    return hasattr(obj, 'local_name') and hasattr(obj, 'type') and hasattr(obj, 'name')
