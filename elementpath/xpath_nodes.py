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
from urllib.parse import urlparse
from typing import cast, Any, Dict, Iterator, List, Optional, Tuple, Union

from .namespaces import XML_BASE, XSI_NIL
from .exceptions import ElementPathValueError
from .protocols import ElementProtocol, LxmlElementProtocol, DocumentProtocol, \
    XsdElementProtocol, XsdAttributeProtocol, XMLSchemaProtocol
from .etree import is_etree_element, etree_iter_strings


###
# Elements and document nodes are processed on duck typing
# bases and mypy checks them using structural subtyping.
# In ElementTree element nodes, comment nodes and PI nodes
# use the same class, so they are indistinguishable with a
# class check.
ElementNodeType = Union[ElementProtocol, XsdElementProtocol, XMLSchemaProtocol]
DocumentNodeType = DocumentProtocol


class ElementProxy:
    """
    A proxy for ElementTree elements.

    :param elem: the wrapped Element object.
    :param parent: the parent Element object.
    """
    def __init__(self, elem: ElementNodeType, parent: Optional[ElementNodeType] = None) -> None:
        self.elem = elem
        self.parent = parent

    def __repr__(self) -> str:
        if self.parent is None:
            return '%s(elem=%r)' % (self.__class__.__name__, self.elem)
        return '%s(elem=%r, parent=%r)' % (self.__class__.__name__, self.elem, self.parent)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, self.__class__) and self.elem is other.elem

    def __hash__(self) -> int:
        return hash(self.elem)

    @property
    def tag(self) -> str:
        return self.elem.tag

    @property
    def text(self) -> str:
        return self.elem.text

    @property
    def tail(self) -> str:
        return self.elem.tail

    @property
    def attrib(self) -> Dict[str, str]:
        return self.elem.attrib

    def get(self, key, default: Optional[str] = None) -> Optional[str]:
        return self.elem.get(key, default)


###
# Other node types, based on a class hierarchy. These nodes
# include also wrappers for element and attribute nodes that
# are associated with an XSD type.
class XPathNode:

    # Accessors, empty sequences are represented with None values.
    attributes: Any = None
    base_uri: Any = None
    children: Any = None
    document_uri: Any = None
    is_id: bool
    is_idrefs: bool
    namespace_nodes: Optional[List['NamespaceNode']]
    nilled: Optional[bool]
    kind: str
    name: Any = None
    parent: Optional[ElementNodeType] = None
    string_value: str
    type_name: Optional[str]
    typed_value: None

    value: Any = None


class AttributeNode(XPathNode):
    """
    A class for processing XPath attribute nodes.

    :param name: the attribute name.
    :param value: a string value or an XSD attribute when XPath is applied on a schema.
    :param parent: the parent element.
    """
    name: str
    kind = 'attribute'

    def __init__(self, name: str, value: Union[str, XsdAttributeProtocol],
                 parent: Optional[ElementNodeType] = None) -> None:
        self.name = name
        self.value: Union[str, XsdAttributeProtocol] = value
        self.parent = parent

    def as_item(self) -> Tuple[str, Union[str, XsdAttributeProtocol]]:
        return self.name, self.value

    def __repr__(self) -> str:
        if self.parent is not None:
            return '%s(name=%r, value=%r, parent=%r)' % (
                self.__class__.__name__, self.name, self.value, self.parent
            )
        return '%s(name=%r, value=%r)' % (self.__class__.__name__, self.name, self.value)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, self.__class__) and \
            self.name == other.name and \
            self.value == other.value and \
            self.parent is other.parent

    def __hash__(self) -> int:
        return hash((self.name, self.value, self.parent))


class TextNode(XPathNode):
    """
    A class for processing XPath text nodes. An Element's property
    (elem.text or elem.tail) with a `None` value is not a text node.

    :param value: a string value.
    :param parent: the parent element.
    :param tail: provide `True` if the text node is the parent Element's tail.
    """
    kind = 'text'

    text: None
    _tail = False

    def __init__(self, value: str, parent: Optional[ElementNodeType] = None,
                 tail: bool = False) -> None:
        self.value = value
        self.parent = parent
        if tail and parent is not None:
            self._tail = True

    def is_tail(self) -> bool:
        """Returns `True` if the node has a parent and represents the tail text."""
        return self._tail

    def __repr__(self) -> str:
        if self.parent is not None:
            return '%s(%r, parent=%r, tail=%r)' % (
                self.__class__.__name__, self.value, self.parent, self._tail
            )
        return '%s(%r)' % (self.__class__.__name__, self.value)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, self.__class__) and \
            self.value == other.value and \
            self.parent is other.parent and \
            self._tail is other._tail

    def __hash__(self) -> int:
        return hash((self.value, self.parent, self._tail))


class NamespaceNode(XPathNode):
    """
    A class for processing XPath namespace nodes.

    :param prefix: the namespace prefix.
    :param uri: the namespace URI.
    :param parent: the parent element.
    """
    kind = 'namespace'

    def __init__(self, prefix: str, uri: str, parent: Optional[ElementNodeType] = None) -> None:
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
        if self.parent is not None:
            return '%s(prefix=%r, uri=%r, parent=%r)' % (
                self.__class__.__name__, self.prefix, self.uri, self.parent
            )
        return '%s(prefix=%r, uri=%r)' % (self.__class__.__name__, self.prefix, self.uri)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, self.__class__) and \
            self.prefix == other.prefix and \
            self.uri == other.uri and \
            self.parent is other.parent

    def __hash__(self) -> int:
        return hash((self.prefix, self.uri, self.parent))


class DocumentNode(XPathNode):
    """
    A class for XPath document nodes.
    """
    kind = 'document'

    def __init__(self, document: DocumentNodeType) -> None:
        self.document = document

    @property
    def value(self) -> str:
        return self.document

    def getroot(self):
        return ElementNode(self.document.getroot())

    def parse(self, source: Any, *args: Any, **kwargs: Any):
        return DocumentNode(self.document.parse(source, *args, **kwargs))

    def iter(self, tag: Optional[str] = None) -> Iterator[ElementProtocol]:
        return self.document.iter(tag)


class ElementNode(ElementProxy, XPathNode):
    """
    A class for processing XPath element nodes.
    """
    kind = 'element'

    @property
    def value(self) -> str:
        return self.elem

    @property
    def name(self) -> str:
        return self.elem.tag

    @property
    def attributes(self):
        return self.elem.attrib

    @property
    def base_uri(self) -> Optional[str]:
        return self.elem.get(XML_BASE)  # FIXME

    @property
    def children(self):
        return self.elem[:]

    @property
    def nilled(self) -> bool:
        return self.elem.get(XSI_NIL) in ('true', '1')

    @property
    def string_value(self):
        return ''.join(etree_iter_strings(self.elem))


class CommentNode(ElementProxy, XPathNode):
    """
    A class for processing XPath comment nodes.
    """
    kind = 'comment'

    @property
    def value(self) -> str:
        return self.elem

    @property
    def base_uri(self) -> Optional[str]:
        if self.parent is None:
            return None
        return self.parent.get(XML_BASE)  # FIXME

    @property
    def string_value(self) -> str:
        return self.elem.text

    @property
    def typed_value(self) -> str:
        return self.elem.text


class ProcessingInstructionNode(ElementProxy, XPathNode):
    """
    A class for XPath processing instructions nodes.
    """
    kind = 'processing-instruction'

    @property
    def name(self):
        try:
            return cast(str, self.elem.target)  # lxml PI
        except AttributeError:
            return cast(str, self.elem.text.split(' ', maxsplit=1)[0])

    @property
    def value(self) -> str:
        return self.elem

    @property
    def string_value(self) -> str:
        return self.elem.text

    @property
    def typed_value(self) -> str:
        return self.elem.text


class TypedElement(XPathNode):
    """
    A class for processing typed element nodes.

    :param elem: the linked element. Can be an Element, or an XSD element \
    when XPath is applied on a schema.
    :param xsd_type: the reference XSD type.
    :param value: the decoded value. Can be `None` for empty or element-only elements."
    """
    kind = 'element'

    def __init__(self, elem: ElementProtocol, xsd_type: Any, value: Any) -> None:
        self.elem = elem
        self.xsd_type = xsd_type
        self.value = value

    @property
    def name(self) -> str:
        return self.elem.tag

    @property
    def tag(self) -> str:
        return self.elem.tag

    def __repr__(self) -> str:
        return '%s(tag=%r)' % (self.__class__.__name__, self.elem.tag)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, self.__class__) and \
            self.elem is other.elem and \
            self.value == other.value

    def __hash__(self) -> int:
        return hash((self.elem, self.value))


class TypedAttribute(XPathNode):
    """
    A class for processing typed attribute nodes.

    :param attribute: the origin AttributeNode instance.
    :param xsd_type: the reference XSD type.
    :param value: the types value.
    """
    kind = 'attribute'

    def __init__(self, attribute: AttributeNode, xsd_type: Any, value: Any) -> None:
        self.attribute = attribute
        self.xsd_type = xsd_type
        self.value = value
        self.parent = attribute.parent

    @property
    def name(self) -> str:
        return self.attribute.name

    def as_item(self) -> Tuple[str, Any]:
        return self.attribute.name, self.value

    def __repr__(self) -> str:
        return '%s(name=%r)' % (self.__class__.__name__, self.attribute.name)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, self.__class__) and \
            self.attribute == other.attribute and \
            self.value == other.value

    def __hash__(self) -> int:
        return hash((self.attribute, self.value))


XPathNodeType = Union[ElementNodeType, DocumentNodeType, XPathNode]


###
# XPath node test functions
#
# XPath has there are seven kinds of nodes:
#
#  element, attribute, text, namespace, processing-instruction, comment, document
#
# Element-like objects are used for representing elements and comments,
# ElementTree-like objects for documents. XPathNode subclasses are used
# for representing other node types and typed elements/attributes.
###
def match_element_node(obj: Any, tag: Optional[str] = None) -> Any:
    """
    Returns `True` if the first argument is an element node matching the tag, `False` otherwise.
    Raises a ValueError if the argument tag has to be used but it's in a wrong format.

    :param obj: the node to be tested.
    :param tag: a fully qualified name, a local name or a wildcard. The accepted
    wildcard formats are '*', '*:*', '*:local-name' and '{namespace}*'.
    """
    if isinstance(obj, TypedElement):
        obj = obj.elem
    elif not is_etree_element(obj) or callable(obj.tag):
        return False

    if not tag:
        return True
    elif not obj.tag:
        return obj.tag == tag
    elif tag == '*' or tag == '*:*':
        return obj.tag != ''
    elif tag[0] == '*':
        try:
            _, name = tag.split(':')
        except (ValueError, IndexError):
            raise ElementPathValueError("unexpected format %r for argument 'tag'" % tag)
        else:
            if obj.tag[0] == '{':
                return obj.tag.split('}')[1] == name
            else:
                return obj.tag == name

    elif tag[-1] == '*':
        if tag[0] != '{' or '}' not in tag:
            raise ElementPathValueError("unexpected format %r for argument 'tag'" % tag)
        elif obj.tag[0] == '{':
            return obj.tag.split('}')[0][1:] == tag.split('}')[0][1:]
        else:
            return False
    else:
        return obj.tag == tag


def match_attribute_node(obj: Any, name: Optional[str] = None) -> bool:
    """
    Returns `True` if the first argument is an attribute node matching the name, `False` otherwise.
    Raises a ValueError if the argument name has to be used, but it's in a wrong format.

    :param obj: the node to be tested.
    :param name: a fully qualified name, a local name or a wildcard. The accepted wildcard formats \
    are '*', '*:*', '*:local-name' and '{namespace}*'.
    """
    if name is None or name == '*' or name == '*:*':
        return isinstance(obj, (AttributeNode, TypedAttribute))
    elif not isinstance(obj, (AttributeNode, TypedAttribute)):
        return False
    elif isinstance(obj, TypedAttribute):
        obj = obj.attribute

    if not name:
        return not obj.name
    elif name[0] == '*':
        try:
            _, _name = name.split(':')
        except (ValueError, IndexError):
            raise ElementPathValueError("unexpected format %r for argument 'name'" % name)
        else:
            if obj.name.startswith('{'):
                return obj.name.split('}')[1] == _name
            else:
                return obj.name == _name

    elif name[-1] == '*':
        if name[0] != '{' or '}' not in name:
            raise ElementPathValueError("unexpected format %r for argument 'name'" % name)
        elif obj.name.startswith('{'):
            return obj.name.split('}')[0][1:] == name.split('}')[0][1:]
        else:
            return False
    else:
        return obj.name == name


def is_element_node(obj: Any) -> bool:
    return isinstance(obj, TypedElement) or \
        hasattr(obj, 'tag') and not callable(obj.tag) and \
        hasattr(obj, 'attrib') and hasattr(obj, 'text')


def is_schema_node(obj: Any) -> bool:
    return hasattr(obj, 'local_name') and hasattr(obj, 'type') and hasattr(obj, 'name')


def is_comment_node(obj: Any) -> bool:
    return hasattr(obj, 'tag') and callable(obj.tag) and obj.tag.__name__ == 'Comment'


def is_processing_instruction_node(obj: Any) -> bool:
    return hasattr(obj, 'tag') and callable(obj.tag) and obj.tag.__name__ == 'ProcessingInstruction'


def is_document_node(obj: Any) -> bool:
    return hasattr(obj, 'getroot') and hasattr(obj, 'parse') and hasattr(obj, 'iter')


def is_lxml_document_node(obj: Any) -> bool:
    return is_document_node(obj) and hasattr(obj, 'xpath') and hasattr(obj, 'xslt')


def is_xpath_node(obj: Any) -> bool:
    return isinstance(obj, XPathNode) or \
        hasattr(obj, 'tag') and hasattr(obj, 'attrib') and hasattr(obj, 'text') or \
        hasattr(obj, 'local_name') and hasattr(obj, 'type') and hasattr(obj, 'name') or \
        hasattr(obj, 'getroot') and hasattr(obj, 'parse') and hasattr(obj, 'iter')


###
# Node accessors: https://www.w3.org/TR/xpath-datamodel-30/#accessors-list
#
# Note: in this implementation empty sequence return value is replaced by None.
#
def node_attributes(obj: Any) -> Optional[Dict[str, Any]]:
    return obj.attrib if is_element_node(obj) else None


def node_base_uri(obj: Any) -> Optional[str]:
    try:
        if is_element_node(obj):
            return cast(str, obj.attrib[XML_BASE])
        elif is_document_node(obj):
            return cast(str, obj.getroot().attrib[XML_BASE])
        return None
    except KeyError:
        return None


def node_document_uri(obj: Any) -> Optional[str]:
    if is_document_node(obj):
        try:
            uri = cast(str, obj.getroot().attrib[XML_BASE])
            parts = urlparse(uri)
        except (KeyError, ValueError):
            pass
        else:
            if parts.scheme and parts.netloc or parts.path.startswith('/'):
                return uri
    return None


def node_children(obj: Any) -> Optional[Iterator[ElementNodeType]]:
    if is_element_node(obj):
        return (child for child in obj)
    elif is_document_node(obj):
        return (child for child in [obj.getroot()])
    else:
        return None


def node_nilled(obj: Any) -> Optional[bool]:
    if is_element_node(obj):
        if isinstance(obj, TypedElement):
            return obj.elem.get(XSI_NIL) in ('true', '1')
        return obj.get(XSI_NIL) in ('true', '1')
    return None


def node_kind(obj: Any) -> Optional[str]:
    if isinstance(obj, XPathNode):
        return obj.kind
    elif is_element_node(obj):
        return 'element'
    elif is_document_node(obj):
        return 'document'
    elif is_comment_node(obj):
        return 'comment'
    elif is_processing_instruction_node(obj):
        return 'processing-instruction'
    else:
        return None


def node_name(obj: Any) -> Optional[str]:
    if isinstance(obj, XPathNode):
        return cast(Optional[str], obj.name)
    elif not hasattr(obj, 'tag') or not hasattr(obj, 'text'):
        return None
    elif not callable(obj.tag):
        return cast(str, obj.tag)
    elif obj.tag.__name__ != 'ProcessingInstruction':
        return None
    else:
        # Return pi target. ElementTree doesn't have a specific attribute
        # for target but put it before the text, separated by a space.
        try:
            return cast(str, obj.target)
        except AttributeError:
            return cast(str, obj.text.split(' ', maxsplit=1)[0])
