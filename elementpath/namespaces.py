#
# Copyright (c), 2018-2020, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import re
from typing import Dict, Tuple

# Regex patterns related to names and namespaces
NAMESPACE_URI_PATTERN = re.compile(r'{([^}]+)}')
EXPANDED_NAME_PATTERN = re.compile(
    r'^(?:{(?P<namespace>[^}]+)})?'
    r'(?P<local>[^\d\W][\w\-.\u00B7\u0300-\u036F\u0387\u06DD\u06DE\u203F\u2040]*)$',
)

# Namespaces
XML_NAMESPACE = "http://www.w3.org/XML/1998/namespace"
XSD_NAMESPACE = "http://www.w3.org/2001/XMLSchema"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"

# XPath/XQuery namespaces
XPATH_FUNCTIONS_NAMESPACE = "http://www.w3.org/2005/xpath-functions"
XQT_ERRORS_NAMESPACE = "http://www.w3.org/2005/xqt-errors"
XPATH_MATH_FUNCTIONS_NAMESPACE = "http://www.w3.org/2005/xpath-functions/math"
XPATH_MAP_FUNCTIONS_NAMESPACE = "http://www.w3.org/2005/xpath-functions/map"
XPATH_ARRAY_FUNCTIONS_NAMESPACE = "http://www.w3.org/2005/xpath-functions/array"
XSLT_XQUERY_SERIALIZATION_NAMESPACE = "http://www.w3.org/2010/xslt-xquery-serialization"

# XML namespace attributes
XML_BASE = '{%s}base' % XML_NAMESPACE
XML_LANG = '{%s}lang' % XML_NAMESPACE
XML_SPACE = '{%s}space' % XML_NAMESPACE
XML_ID = '{%s}id' % XML_NAMESPACE

# XML Schema Instance namespace attributes
XSI_TYPE = '{%s}type' % XSI_NAMESPACE
XSI_NIL = '{%s}nil' % XSI_NAMESPACE
XSI_SCHEMA_LOCATION = '{%s}schemaLocation' % XSI_NAMESPACE
XSI_NONS_SCHEMA_LOCATION = '{%s}schemaLocation' % XSI_NAMESPACE

# XML Schema types
XSD_ANY_TYPE = '{%s}anyType' % XSD_NAMESPACE
XSD_ANY_SIMPLE_TYPE = '{%s}anySimpleType' % XSD_NAMESPACE
XSD_ANY_ATOMIC_TYPE = '{%s}anyAtomicType' % XSD_NAMESPACE
XSD_NOTATION = '{%s}NOTATION' % XSD_NAMESPACE
XSD_ID = '{%s}ID' % XSD_NAMESPACE
XSD_IDREF = '{%s}IDREF' % XSD_NAMESPACE
XSD_IDREFS = '{%s}IDREFS' % XSD_NAMESPACE

# XPath type labels defined in XSD namespace that are not XSD builtin types
XSD_UNTYPED = '{%s}untyped' % XSD_NAMESPACE
XSD_UNTYPED_ATOMIC = '{%s}untypedAtomic' % XSD_NAMESPACE


def get_namespace(name: str) -> str:
    try:
        return NAMESPACE_URI_PATTERN.match(name).group(1)  # type: ignore[union-attr]
    except AttributeError:
        return ''


def split_expanded_name(name: str) -> Tuple[str, str]:
    match = EXPANDED_NAME_PATTERN.match(name)
    if match is None:
        raise ValueError("{!r} is not an expanded QName".format(name))
    namespace, local_name = match.groups()
    return namespace or '', local_name


def get_prefixed_name(qname: str, namespaces: Dict[str, str]) -> str:
    """
    Get the prefixed form of a QName, using a namespace map.

    :param qname: an extended QName or a local name or a prefixed QName.
    :param namespaces: a dictionary with a map from prefixes to namespace URIs.
    """
    try:
        if qname[0] == '{':
            ns_uri, local_name = qname[1:].split('}')
        elif qname[1] == '{' and qname[0] == 'Q':
            ns_uri, local_name = qname[2:].split('}')
        else:
            return qname
    except IndexError:
        return qname
    except (ValueError, TypeError):
        raise ValueError("{!r} is not a QName".format(qname))

    for prefix, uri in sorted(namespaces.items(), reverse=True):
        if uri == ns_uri:
            return '%s:%s' % (prefix, local_name) if prefix else local_name
    else:
        return qname


def get_expanded_name(qname: str, namespaces: Dict[str, str]) -> str:
    """
    Get the expanded form of a QName, using a namespace map.
    Local names are mapped to the default namespace.

    :param qname: a prefixed QName or a local name or an extended QName.
    :param namespaces: a dictionary with a map from prefixes to namespace URIs.
    :return: the expanded format of a QName or a local name.
    """
    try:
        if qname[0] == '{' or qname[1] == '{' and qname[0] == 'Q':
            return qname
    except IndexError:
        return qname

    try:
        prefix, local_name = qname.split(':')
    except ValueError:
        if ':' in qname:
            raise ValueError("wrong format for prefixed QName %r" % qname)
        try:
            uri = namespaces['']
        except KeyError:
            return qname
        else:
            return '{%s}%s' % (uri, qname) if uri else qname
    else:
        if not prefix or not local_name:
            raise ValueError("wrong format for reference name %r" % qname)
        uri = namespaces[prefix]
        return '{%s}%s' % (uri, local_name) if uri else local_name
