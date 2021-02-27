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
XPath 3.1 implementation
"""
from ..namespaces import XPATH_MAP_FUNCTIONS_NAMESPACE, \
    XPATH_ARRAY_FUNCTIONS_NAMESPACE  # , XSLT_XQUERY_SERIALIZATION_NAMESPACE
from ..xpath30 import XPath30Parser


class XPath31Parser(XPath30Parser):
    """
    XPath 3.1 expression parser class.
    """
    version = '3.1'

    SYMBOLS = XPath30Parser.SYMBOLS | set()
    """
    {
        'format-number', 'random-number-generator', 'collation-key',
        'contains-token', 'parse-ietf-date',

        # Higher-order functions
        'sort', 'apply', 'load-xquery-module', 'transform',

        # Maps and Arrays
        'merge', 'size', 'keys', 'contains', 'get', 'find', 'put', 'entry',
        'remove', 'append', 'subarray', 'remove', 'join', 'flatten',

        # Functions on JSON Data
        'parse-json', 'json-doc', 'json-to-xml', 'xml-to-json',
    }
    """

    DEFAULT_NAMESPACES = {
        'map': XPATH_MAP_FUNCTIONS_NAMESPACE,
        'array': XPATH_ARRAY_FUNCTIONS_NAMESPACE,
        **XPath30Parser.DEFAULT_NAMESPACES
    }


##
# XPath 3.0 definitions
register = XPath31Parser.register
unregister = XPath31Parser.unregister
literal = XPath31Parser.literal
prefix = XPath31Parser.prefix
infix = XPath31Parser.infix
infixr = XPath31Parser.infixr
method = XPath31Parser.method
function = XPath31Parser.function

XPath31Parser.build()
