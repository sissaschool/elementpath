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
Helper functions for XPath nodes and functions.
"""
from collections import namedtuple

from .compat import PY3
from .namespaces import XML_BASE_QNAME, XML_ID_QNAME, XSI_TYPE_QNAME, XSI_NIL_QNAME, \
    XSD_UNTYPED, XSD_UNTYPED_ATOMIC, prefixed_to_qname
from .exceptions import xpath_error
from .datatypes import UntypedAtomic

###
# Node types
AttributeNode = namedtuple('Attribute', 'name value')
"""A namedtuple-based type to represent XPath attributes."""

NamespaceNode = namedtuple('Namespace', 'prefix uri')
"""A namedtuple-based type to represent XPath namespaces."""


###
# Utility functions for ElementTree's Element instances
def is_etree_element(obj):
    return hasattr(obj, 'tag') and hasattr(obj, 'attrib') and hasattr(obj, 'text')


def elem_iter_strings(elem):
    for e in elem.iter():
        if e.text is not None:
            yield e.text
        if e.tail is not None and e is not elem:
            yield e.tail


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
    if tag is None:
        return is_etree_element(obj) and not callable(obj.tag)
    elif not is_etree_element(obj):
        return False
    elif tag[0] == '*':
        if not obj.tag:
            return False
        elif obj.tag[0] == '{':
            return obj.tag.split('}')[1] == tag.split(':')[1]
        else:
            return obj.tag == tag.split(':')[1]
    elif tag[-1] == '*':
        if not obj.tag:
            return False
        elif obj.tag[0] == '{':
            return obj.tag.split('}')[0][1:] == tag.split('}')[0][1:]
        else:
            return True
    else:
        return obj.tag == tag


def is_attribute_node(obj, name=None):
    if name is None:
        return isinstance(obj, AttributeNode)
    elif not isinstance(obj, AttributeNode):
        return False
    elif name[0] == '*':
        if obj[0][0] == '{':
            return obj[0].split('}')[1] == name.split(':')[1]
        else:
            return obj[0] == name.split(':')[1]
    elif name[-1] == '*':
        if obj[0][0] == '{':
            return obj[0].split('}')[0][1:] == name.split('}')[0][1:]
        else:
            return True
    else:
        return obj[0] == name


def is_comment_node(obj):
    return is_etree_element(obj) and callable(obj.tag) and obj.tag.__name__ == 'Comment'


def is_processing_instruction_node(obj):
    return is_etree_element(obj) and callable(obj.tag) and obj.tag.__name__ == 'ProcessingInstruction'


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
    return isinstance(obj, tuple) or is_etree_element(obj) or is_document_node(obj) or is_text_node(obj)


###
# Node accessors
def node_attributes(obj):
    if is_element_node(obj):
        return obj.attrib


def node_base_uri(obj):
    try:
        if is_element_node(obj):
            return obj.attrib[XML_BASE_QNAME]
        elif is_document_node(obj):
            return obj.getroot().attrib[XML_BASE_QNAME]
    except KeyError:
        pass


def node_document_uri(obj):
    # Try the xml:base of root node because an ElementTree doesn't save reference to source.
    for uri in node_base_uri(obj):
        return uri


def node_children(obj):
    if is_element_node(obj):
        for child in obj:
            return child
    elif is_document_node(obj):
        return obj.getroot()


def node_is_id(obj):
    if is_element_node(obj):
        return XML_ID_QNAME in obj.attrib
    elif is_attribute_node(obj):
        return obj[0] == XML_ID_QNAME


def node_is_idrefs(obj, namespaces):
    if is_element_node(obj):
        try:
            node_type = obj.attrib[XSI_TYPE_QNAME]
        except KeyError:
            pass
        else:
            return prefixed_to_qname(node_type, namespaces) in ("IDREF", "IDREFS")
    elif is_attribute_node(obj) and obj[0] == XSI_TYPE_QNAME:
        return prefixed_to_qname(obj[1], namespaces) in ("IDREF", "IDREFS")


def node_nilled(obj):
    if is_element_node(obj):
        return obj.get(XSI_NIL_QNAME) == 'true'


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
    elif is_attribute_node(obj):
        return obj[0]
    elif is_namespace_node(obj):
        return obj[0]


def node_string_value(obj):
    if is_element_node(obj):
        return u''.join(elem_iter_strings(obj))
    elif is_attribute_node(obj):
        return obj[1]
    elif is_text_node(obj):
        return obj
    elif is_document_node(obj):
        return u''.join(e.text for e in obj.getroot().iter() if e.text is not None)
    elif is_namespace_node(obj):
        return obj[1]
    elif is_comment_node(obj):
        return obj.text
    elif is_processing_instruction_node(obj):
        return obj.text


def node_type_name(obj, schema=None):
    if is_element_node(obj):
        if schema is None:
            return XSD_UNTYPED
    elif is_attribute_node(obj):
        if schema is None:
            return XSD_UNTYPED_ATOMIC  # TODO: from a PSVI ...
    elif is_text_node(obj):
        return XSD_UNTYPED_ATOMIC


###
# XPath base functions
def boolean_value(obj, token=None):
    """
    The effective boolean value, as computed by fn:boolean().
    """
    if isinstance(obj, list):
        if not obj:
            return False
        elif isinstance(obj[0], tuple) or is_element_node(obj[0]):
            return True
        elif len(obj) == 1:
            return bool(obj[0])
        else:
            raise xpath_error(
                code='FORG0006', token=token, prefix=getattr(token, 'error_prefix', 'err'),
                message="Effective boolean value is not defined for a sequence of two or "
                "more items not starting with an XPath node.",
            )
    elif isinstance(obj, tuple) or is_element_node(obj):
        raise xpath_error(
            code='FORG0006', token=token, prefix=getattr(token, 'error_prefix', 'err'),
            message="Effective boolean value is not defined for {}.".format(obj)
        )
    return bool(obj)


def string_value(obj):
    """
    The string value, as computed by fn:string().
    """
    if obj is None:
        return ''
    elif is_xpath_node(obj):
        return node_string_value(obj)
    else:
        return str(obj)


def data_value(obj):
    """
    The typed value, as computed by fn:data() on each item. Returns an instance of
    UntypedAtomic.
    """
    if obj is None:
        return
    elif not is_xpath_node(obj):
        return obj
    else:
        value = node_string_value(obj)
        if value is not None:
            return UntypedAtomic(value)


def number_value(obj):
    """
    The numeric value, as computed by fn:number() on each item. Returns a float value.
    """
    try:
        return float(node_string_value(obj) if is_xpath_node(obj) else obj)
    except (TypeError, ValueError):
        return float('nan')
