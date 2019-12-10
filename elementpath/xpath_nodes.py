# -*- coding: utf-8 -*-
#
# Copyright (c), 2018-2019, SISSA (International School for Advanced Studies).
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

from .compat import PY3, urlparse
from .namespaces import XML_BASE, XSI_NIL
from .exceptions import ElementPathValueError
from .datatypes import ncname_validator

###
# Node types
AttributeNode = namedtuple('Attribute', 'name value')
"""A namedtuple-based type to represent XPath attributes."""

NamespaceNode = namedtuple('Namespace', 'prefix uri')
"""A namedtuple-based type to represent XPath namespaces."""

TypedAttribute = namedtuple('TypedAttribute', 'attr value')
"""A wrapper for processing typed-value attributes."""

TypedElement = namedtuple('TypedElement', 'elem value')
"""A wrapper for processing typed-value elements."""


###
# Utility functions for ElementTree's Element instances
def is_etree_element(obj):
    return hasattr(obj, 'tag') and hasattr(obj, 'attrib') and hasattr(obj, 'text')


def elem_iter_strings(elem):
    if isinstance(elem, TypedElement):
        elem = elem.elem

    for e in elem.iter():
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
#    element, attribute, text, namespace, processing-instruction, comment, document
#
# Element-like objects are used for representing elements and comments, ElementTree-like objects
# for documents. Generic tuples are used for representing attributes and named-tuples for namespaces.
###
def is_element_node(obj, tag=None):
    """
    Returns `True` if the first argument is an element node matching the tag, `False` otherwise.
    Raises a ValueError if the argument tag has to be used but it's in a wrong format.

    :param obj: the node to be tested.
    :param tag: a fully qualified name, a local name or a wildcard. The accepted wildcard formats \
    are '*', '*:*', '*:local-name' and '{namespace}*'.
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


def is_attribute_node(obj, name=None):
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
        obj = obj.attr

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


def is_schema_node(obj):
    return hasattr(obj, 'name') and hasattr(obj, 'local_name') and hasattr(obj, 'type')


def is_comment_node(obj):
    return hasattr(obj, 'tag') and callable(obj.tag) and obj.tag.__name__ == 'Comment'


def is_processing_instruction_node(obj):
    return hasattr(obj, 'tag') and callable(obj.tag) and obj.tag.__name__ == 'ProcessingInstruction'


def is_document_node(obj):
    return all(hasattr(obj, name) for name in ('getroot', 'iter', 'iterfind', 'parse'))


def is_namespace_node(obj):
    return isinstance(obj, NamespaceNode)


if not PY3:
    def is_text_node(obj):
        return isinstance(obj, (str, unicode))
else:
    def is_text_node(obj):
        return isinstance(obj, str)


def is_xpath_node(obj):
    return isinstance(obj, tuple) or is_etree_element(obj) or is_schema_node(obj) or \
        is_document_node(obj) or is_text_node(obj)


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


def node_is_id(obj):
    if is_element_node(obj):
        return ncname_validator(obj.text)
    elif is_attribute_node(obj):
        return ncname_validator(obj[1])


def node_is_idrefs(obj):
    if is_element_node(obj):
        return obj.text is not None and all(ncname_validator(x) for x in obj.text.split())
    elif is_attribute_node(obj):
        return all(ncname_validator(x) for x in obj[1].split())


def node_nilled(obj):
    if is_element_node(obj):
        return obj.get(XSI_NIL) in ('true', '1')


def node_kind(obj):
    if is_element_node(obj):
        return 'element'
    elif is_attribute_node(obj):
        return 'attribute'
    elif is_text_node(obj):
        return 'text'
    elif is_document_node(obj):
        return 'document'
    elif is_namespace_node(obj):
        return 'namespace'
    elif is_comment_node(obj):
        return 'comment'
    elif is_processing_instruction_node(obj):
        return 'processing-instruction'


def node_name(obj):
    if is_element_node(obj):
        return obj.tag
    elif is_attribute_node(obj) or is_namespace_node(obj):
        return obj[0]
