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
import re
from .exceptions import ElementPathValueError


_RE_MATCH_NAMESPACE = re.compile(r'{([^}]*)}')

# Namespaces
XML_NAMESPACE = "http://www.w3.org/XML/1998/namespace"
XSD_NAMESPACE = "http://www.w3.org/2001/XMLSchema"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"
XPATH_FUNCTIONS_NAMESPACE = "http://www.w3.org/2005/xpath-functions"
XQT_ERRORS_NAMESPACE = "http://www.w3.org/2005/xqt-errors"

XPATH_1_DEFAULT_NAMESPACES = {'xml': XML_NAMESPACE}

XPATH_2_DEFAULT_NAMESPACES = {
    'xml': XML_NAMESPACE,
    'xs': XSD_NAMESPACE,
    'xlink': XLINK_NAMESPACE,
    'fn': XPATH_FUNCTIONS_NAMESPACE,
    'err': XQT_ERRORS_NAMESPACE
}

# XML namespace attributes
XML_BASE_QNAME = '{%s}base' % XML_NAMESPACE
XML_LANG_QNAME = '{%s}lang' % XML_NAMESPACE
XML_SPACE_QNAME = '{%s}space' % XML_NAMESPACE
XML_ID_QNAME = '{%s}id' % XML_NAMESPACE

# XML Schema Instance namespace attributes
XSI_TYPE_QNAME = '{%s}type' % XSI_NAMESPACE
XSI_NIL_QNAME = '{%s}nil' % XSI_NAMESPACE
XSI_SCHEMA_LOCATION_QNAME = '{%s}schemaLocation' % XSI_NAMESPACE
XSI_NONS_SCHEMA_LOCATION_QNAME = '{%s}schemaLocation' % XSI_NAMESPACE

# XSD tags and attributes
XSD_NOTATION = '{%s}NOTATION' % XSD_NAMESPACE
XSD_ANY_ATOMIC_TYPE = '{%s}anyAtomicType' % XSD_NAMESPACE
XSD_UNTYPED = '{%s}untyped' % XSD_NAMESPACE
XSD_UNTYPED_ATOMIC = '{%s}untypedAtomic' % XSD_NAMESPACE


def get_namespace(name):
    try:
        return _RE_MATCH_NAMESPACE.match(name).group(1)
    except (AttributeError, TypeError):
        return ''


def qname_to_prefixed(name, namespaces):
    """
    Get the prefixed form of a name, using a namespace map.

    :param name: A fully qualified name or a local name.
    :param namespaces: A dictionary with the map from prefixes to namespace URIs.
    :return: String with a prefixed or local name.
    """
    qname_uri = get_namespace(name)
    for prefix, uri in sorted(namespaces.items(), reverse=True):
        if uri != qname_uri:
            continue
        if prefix:
            return name.replace(u'{%s}' % uri, u'%s:' % prefix)
        else:
            return name.replace(u'{%s}' % uri, '')
    return name


def prefixed_to_qname(name, namespaces):
    """
    Get the fully qualified form of a name, using a namespace map.

    :param name: A local name or a prefixed name or a fully qualified name.
    :param namespaces: A dictionary with the map from prefixes to namespace URIs.
    :return: String with a fully qualified or local name.
    """
    if name and name[0] == '{':
        return name

    try:
        prefix, name = name.split(':')
    except ValueError:
        if ':' in name:
            raise ElementPathValueError("wrong format for reference name %r" % name)
        try:
            uri = namespaces['']
        except KeyError:
            return name
        else:
            return u'{%s}%s' % (uri, name) if uri else name
    else:
        if not prefix or not name:
            raise ElementPathValueError("wrong format for reference name %r" % name)
        try:
            uri = namespaces[prefix]
        except KeyError:
            raise ElementPathValueError("prefix %r not found in namespace map" % prefix)
        else:
            return u'{%s}%s' % (uri, name) if uri else name
