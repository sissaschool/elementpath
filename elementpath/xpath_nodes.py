#
# Copyright (c), 2018-2020, SISSA (International School for Advanced Studies).
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
from collections import namedtuple
from urllib.parse import urlparse

from .namespaces import XML_BASE, XSI_NIL
from .exceptions import ElementPathValueError

###
# Node types
AttributeNode = namedtuple('Attribute', 'name value')
"""
A namedtuple-based type for processing XPath attributes.

:param name: the attribute name.
:param value: the string value of the attribute, or an XSD attribute \
when XPath is applied on a schema.
"""

TextNode = namedtuple('Text', 'value')
"""
A namedtuple-based type for processing XPath text nodes. A text node is the elem.text
value if this is `None`, otherwise the element doesn't have a text node.

:param value: the string value.
"""

NamespaceNode = namedtuple('Namespace', 'prefix uri')
"""
A namedtuple-based type for processing XPath namespaces.

:param prefix: the namespace prefix.
:param uri: the namespace URI.
"""

TypedAttribute = namedtuple('TypedAttribute', 'attribute type value')
"""
A namedtuple-based type for processing typed-value attributes.

:param attribute: the origin AttributeNode tuple.
:param type: the reference XSD type.
:param value: the decoded value.
"""

TypedElement = namedtuple('TypedElement', 'elem type value')
"""
A namedtuple-based type for processing typed-value elements.

:param elem: the origin element. Can be an Element, or an XSD element \
when XPath is applied on a schema.
:param type: the reference XSD type.
:param value: the decoded value. Can be `None` for empty or element-only elements.
"""


###
# Utility functions for ElementTree's Element instances
def is_etree_element(obj):
    return hasattr(obj, 'tag') and hasattr(obj, 'attrib') and hasattr(obj, 'text')


def etree_iter_nodes(root, with_root=True, with_attributes=False):
    if isinstance(root, TypedElement):
        root = root.elem
    elif is_document_node(root) and with_root:
        yield root

    for e in root.iter():
        if callable(e.tag):
            continue  # is a comment or a process instruction
        if with_root or e is not root:
            yield e
        if e.text is not None:
            yield TextNode(e.text)
        if e.attrib and with_attributes:
            yield from map(lambda x: AttributeNode(*x), e.attrib.items())
        if e.tail is not None and e is not root:
            yield TextNode(e.tail)


def etree_iter_strings(elem):
    if isinstance(elem, TypedElement):
        if elem.type.is_element_only():
            # Element-only text content is normalized
            elem = elem.elem
            for e in elem.iter():
                if callable(e.tag):
                    continue
                if e.text is not None:
                    yield e.text.strip() if e is elem else e.text
                if e.tail is not None and e is not elem:
                    yield e.tail.strip() if e in elem else e.tail
            return

        elem = elem.elem

    for e in elem.iter():
        if callable(e.tag):
            continue
        if e.text is not None:
            yield e.text
        if e.tail is not None and e is not elem:
            yield e.tail


def etree_deep_equal(e1, e2):
    if e1.tag != e2.tag:
        return False
    elif (e1.text or '').strip() != (e2.text or '').strip():
        return False
    elif (e1.tail or '').strip() != (e2.tail or '').strip():
        return False
    elif e1.attrib != e2.attrib:
        return False
    elif len(e1) != len(e2):
        return False
    return all(etree_deep_equal(c1, c2) for c1, c2 in zip(e1, e2))


###
# XPath node test functions
#
# XPath has there are 7 kinds of nodes:
#
#  element, attribute, text, namespace, processing-instruction, comment, document
#
# Element-like objects are used for representing elements and comments,
# ElementTree-like objects for documents. Generic tuples are used for
# representing attributes and named-tuples for namespaces.
###
def match_element_node(obj, tag=None):
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
            return obj.tag.split('}')[1] == name if obj.tag[0] == '{' else obj.tag == name
    elif tag[-1] == '*':
        if tag[0] != '{' or '}' not in tag:
            raise ElementPathValueError("unexpected format %r for argument 'tag'" % tag)
        return obj.tag.split('}')[0][1:] == tag.split('}')[0][1:] if obj.tag[0] == '{' else False
    else:
        return obj.tag == tag


def match_attribute_node(obj, name=None):
    """
    Returns `True` if the first argument is an attribute node matching the name, `False` otherwise.
    Raises a ValueError if the argument name has to be used but it's in a wrong format.

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

    if name[0] == '*':
        try:
            _, _name = name.split(':')
        except (ValueError, IndexError):
            raise ElementPathValueError("unexpected format %r for argument 'name'" % name)
        else:
            return obj[0].split('}')[1] == _name if obj[0][0] == '{' else obj[0] == _name
    elif name[-1] == '*':
        if name[0] != '{' or '}' not in name:
            raise ElementPathValueError("unexpected format %r for argument 'name'" % name)
        return obj[0].split('}')[0][1:] == name.split('}')[0][1:] if obj[0][0] == '{' else False
    else:
        return obj[0] == name


def is_element_node(obj):
    if isinstance(obj, TypedElement):
        return True
    return hasattr(obj, 'tag') and not callable(obj.tag) and \
        hasattr(obj, 'attrib') and hasattr(obj, 'text')


def is_schema_node(obj):
    return hasattr(obj, 'local_name') and hasattr(obj, 'type') and hasattr(obj, 'name')


def is_comment_node(obj):
    return hasattr(obj, 'tag') and callable(obj.tag) and obj.tag.__name__ == 'Comment'


def is_processing_instruction_node(obj):
    return hasattr(obj, 'tag') and callable(obj.tag) and obj.tag.__name__ == 'ProcessingInstruction'


def is_document_node(obj):
    return hasattr(obj, 'getroot') and hasattr(obj, 'parse') and hasattr(obj, 'iter')


def is_xpath_node(obj):
    return isinstance(obj, tuple) or \
        hasattr(obj, 'tag') and hasattr(obj, 'attrib') and hasattr(obj, 'text') or \
        hasattr(obj, 'local_name') and hasattr(obj, 'type') and hasattr(obj, 'name') or \
        hasattr(obj, 'getroot') and hasattr(obj, 'parse') and hasattr(obj, 'iter')


###
# Node accessors: in this implementation node accessors return None instead of empty sequence.
# Ref: https://www.w3.org/TR/xpath-datamodel-31/#dm-document-uri
def node_attributes(obj):
    if is_element_node(obj):
        return obj.attrib


def node_base_uri(obj):
    try:
        if is_element_node(obj):
            return obj.attrib[XML_BASE]
        elif is_document_node(obj):
            return obj.getroot().attrib[XML_BASE]
    except KeyError:
        pass


def node_document_uri(obj):
    if is_document_node(obj):
        try:
            uri = obj.getroot().attrib[XML_BASE]
            parts = urlparse(uri)
        except (KeyError, ValueError):
            pass
        else:
            if parts.scheme and parts.netloc or parts.path.startswith('/'):
                return uri


def node_children(obj):
    if is_element_node(obj):
        return (child for child in obj)
    elif is_document_node(obj):
        return (child for child in [obj.getroot()])


def node_nilled(obj):
    if is_element_node(obj):
        return obj.get(XSI_NIL) in ('true', '1')


def node_kind(obj):
    if isinstance(obj, tuple):
        if isinstance(obj, (AttributeNode, TypedAttribute)):
            return 'attribute'
        elif isinstance(obj, TextNode):
            return 'text'
        elif isinstance(obj, NamespaceNode):
            return 'namespace'
    elif is_element_node(obj):
        return 'element'
    elif is_document_node(obj):
        return 'document-node'
    elif is_comment_node(obj):
        return 'comment'
    elif is_processing_instruction_node(obj):
        return 'processing-instruction'


def node_name(obj):
    if isinstance(obj, tuple):
        if isinstance(obj, (AttributeNode, NamespaceNode)):
            return obj[0]
        elif isinstance(obj, TypedAttribute):
            return obj[0][0]
        elif isinstance(obj, TypedElement):
            return obj[0].tag

    elif hasattr(obj, 'tag') and not callable(obj.tag) \
            and hasattr(obj, 'attrib') and hasattr(obj, 'text'):
        return obj.tag
