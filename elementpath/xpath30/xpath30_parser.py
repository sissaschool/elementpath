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
XPath 3.0 implementation - part 1 (parser class)

Refs:
  - https://www.w3.org/TR/2014/REC-xpath-30-20140408/
  - https://www.w3.org/TR/xpath-functions-30/
"""
from typing import Any, Dict, Optional

from ..namespaces import XPATH_MATH_FUNCTIONS_NAMESPACE
from ..xpath2 import XPath2Parser


class XPath30Parser(XPath2Parser):
    """
    XPath 3.0 expression parser class. Accepts all XPath 2.0 options as keyword
    arguments, but the *strict* option is ignored because XPath 3.0+ has braced
    URI literals and the expanded name syntax is not compatible.

    :param args: the same positional arguments of class :class:`XPath2Parser`.
    :param decimal_formats: a mapping with statically known decimal formats.
    :param kwargs: the same keyword arguments of class :class:`XPath2Parser`.
    """
    version = '3.0'

    SYMBOLS = XPath2Parser.SYMBOLS | {
        'Q{',  # see BracedURILiteral rule
        '||',  # concat operator
        '!',   # Simple map operator

        # Math functions (trigonometric and exponential)
        'pi', 'exp', 'exp10', 'log', 'log10', 'pow', 'sqrt',
        'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'atan2',

        # Formatting functions
        'format-integer', 'format-number', 'format-dateTime',
        'format-date', 'format-time',

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
        'function-lookup', 'function-name', 'function-arity', '#', '?',
        'for-each', 'filter', 'fold-left', 'fold-right', 'for-each-pair',

        # Expressions and node type functions
        'function', 'let', ':=',  # 'namespace-node', 'switch',
    }

    DEFAULT_NAMESPACES = {
        'math': XPATH_MATH_FUNCTIONS_NAMESPACE, **XPath2Parser.DEFAULT_NAMESPACES
    }

    function_signatures = XPath2Parser.function_signatures.copy()

    def __init__(self, *args: Any, decimal_formats: Optional[Dict[str, Any]] = None,
                 **kwargs: Any) -> None:
        kwargs.pop('strict', None)
        super(XPath30Parser, self).__init__(*args, **kwargs)
        self.decimal_formats = decimal_formats if decimal_formats is not None else {}


# XPath 3.0 definitions continue into module xpath3_operators
