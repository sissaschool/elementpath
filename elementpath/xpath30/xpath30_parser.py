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
XPath 3.0 implementation
"""
from ..namespaces import XPATH_MATH_FUNCTIONS_NAMESPACE
from ..xpath2_parser import XPath2Parser


class XPath30Parser(XPath2Parser):
    """
    XPath 3.0 expression parser class.
    """
    version = '3.0'

    # add namespaces math

    SYMBOLS = XPath2Parser.SYMBOLS | set()
    """
    {
        # Formatting functions
        'format-integer', 'format-dateTime', 'format-date', 'format-time',

        # Trigonometric and exponential functions
        'pi', 'exp', 'exp10', 'log', 'log10', 'pow', 'sqrt',
        'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'atan2',

        # String functions that use regular expressions
        'analyze-string',

        # Functions and operators on nodes
        'path', 'has-children', 'innermost', 'outermost',

        # Functions and operators on sequences
        'head', 'tail', 'generate-id', 'uri-collection',
        'unparsed-text', 'unparsed-text-lines', 'unparsed-text-available',
        'environment-variable', 'available-environment-variables',

        # Parsing and serializing
        'parse-xml', 'parse-xml-fragment', 'serialize',

        # Higher-order functions
        'function-lookup', 'function-name', 'function-arity',
        'for-each', 'filter', 'fold-left', 'fold-right', 'for-each-pair',
    }"""

    DEFAULT_NAMESPACES = {
        'math': XPATH_MATH_FUNCTIONS_NAMESPACE, **XPath2Parser.DEFAULT_NAMESPACES
    }


##
# XPath 3.0 definitions
register = XPath30Parser.register
unregister = XPath30Parser.unregister
literal = XPath30Parser.literal
prefix = XPath30Parser.prefix
infix = XPath30Parser.infix
infixr = XPath30Parser.infixr
method = XPath30Parser.method
function = XPath30Parser.function

XPath30Parser.build()