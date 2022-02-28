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
from copy import deepcopy
from typing import Any, Dict, Optional

from ..namespaces import XPATH_MATH_FUNCTIONS_NAMESPACE
from ..xpath2 import XPath2Parser


DecimalFormatsType = Dict[Optional[str], Dict[str, str]]


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
        'function', 'let', ':=', 'namespace-node',

        # XSD list-types constructor functions
        'ENTITIES', 'IDREFS', 'NMTOKENS',
    }

    DEFAULT_NAMESPACES = {
        'math': XPATH_MATH_FUNCTIONS_NAMESPACE, **XPath2Parser.DEFAULT_NAMESPACES
    }
    PATH_STEP_SYMBOLS = {
        '(integer)', '(string)', '(float)', '(decimal)', '(name)',
        '*', '@', '..', '.', '(', '{', 'Q{', '$',
    }

    decimal_formats: DecimalFormatsType = {
        None: {
            'decimal-separator': '.',
            'grouping-separator': ',',
            'exponent-separator': 'e',
            'infinity': 'Infinity',
            'minus-sign': '-',
            'NaN': 'NaN',
            'percent': '%',
            'per-mille': '‰',
            'zero-digit': '0',
            'digit': '#',
            'pattern-separator': ';',
        }
    }

    # https://www.w3.org/TR/xpath-30/#id-reserved-fn-names
    RESERVED_FUNCTION_NAMES = {
        'attribute', 'comment', 'document-node', 'element', 'empty-sequence',
        'function', 'if', 'item', 'namespace-node', 'node', 'processing-instruction',
        'schema-attribute', 'schema-element', 'switch', 'text', 'typeswitch',
    }

    function_signatures = XPath2Parser.function_signatures.copy()

    def __init__(self, *args: Any, decimal_formats: Optional[DecimalFormatsType] = None,
                 **kwargs: Any) -> None:
        kwargs.pop('strict', None)
        super(XPath30Parser, self).__init__(*args, **kwargs)

        if decimal_formats is not None:
            self.decimal_formats = deepcopy(self.decimal_formats)

            for k, v in decimal_formats.items():
                if k is not None:
                    self.decimal_formats[k] = self.decimal_formats[None].copy()
                    self.decimal_formats[k].update(v)

            if None in decimal_formats:
                self.decimal_formats[None].update(decimal_formats[None])

# XPath 3.0 definitions continue into module xpath3_operators
