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
import math

from ..namespaces import XPATH_MATH_FUNCTIONS_NAMESPACE
from ..xpath2 import XPath2Parser
from ..datatypes import NumericProxy


class XPath30Parser(XPath2Parser):
    """
    XPath 3.0 expression parser class.
    """
    version = '3.0'

    # add namespaces math

    SYMBOLS = XPath2Parser.SYMBOLS | {
        # Formatting functions
        # 'format-integer', 'format-dateTime', 'format-date', 'format-time',

        # Trigonometric and exponential functions
        'pi', 'exp', 'exp10', 'log', 'log10', 'pow', 'sqrt',
        'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'atan2',

        # String functions that use regular expressions
        # 'analyze-string',

        # Functions and operators on nodes
        # 'path', 'has-children', 'innermost', 'outermost',

        # Functions and operators on sequences
        # 'head', 'tail', 'generate-id', 'uri-collection',
        # 'unparsed-text', 'unparsed-text-lines', 'unparsed-text-available',
        # 'environment-variable', 'available-environment-variables',

        # Parsing and serializing
        # 'parse-xml', 'parse-xml-fragment', 'serialize',

        # Higher-order functions
        # 'function-lookup', 'function-name', 'function-arity',
        # 'for-each', 'filter', 'fold-left', 'fold-right', 'for-each-pair',
    }

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


###
# Mathematical functions
@method(function('pi', label='math function', nargs=0))
def evaluate(self, context):
    return math.pi


@method(function('exp', label='math function', nargs=1))
def evaluate(self, context):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        return math.exp(arg)


@method(function('exp10', label='math function', nargs=1))
def evaluate(self, context):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        return float(10 ** arg)


@method(function('log', label='math function', nargs=1))
def evaluate(self, context):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        return float('-inf') if not arg else float('nan') if arg <= -1 else math.log(arg)


@method(function('log10', label='math function', nargs=1))
def evaluate(self, context):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        return float('-inf') if not arg else float('nan') if arg <= -1 else math.log10(arg)


@method(function('pow', label='math function', nargs=2))
def evaluate(self, context):
    x = self.get_argument(context, cls=NumericProxy)
    y = self.get_argument(context, index=1, required=True, cls=NumericProxy)
    if x is not None:
        if not x and y < 0:
            return float('inf')

        try:
            return float(x ** y)
        except TypeError:
            return float('nan')


@method(function('sqrt', label='math function', nargs=1))
def evaluate(self, context):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        if arg < 0:
            return float('nan')
        return math.sqrt(arg)


@method(function('sin', label='math function', nargs=1))
def evaluate(self, context):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        if math.isinf(arg):
            return float('nan')
        return math.sin(arg)


@method(function('cos', label='math function', nargs=1))
def evaluate(self, context):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        if math.isinf(arg):
            return float('nan')
        return math.cos(arg)


@method(function('tan', label='math function', nargs=1))
def evaluate(self, context):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        if math.isinf(arg):
            return float('nan')
        return math.tan(arg)


@method(function('asin', label='math function', nargs=1))
def evaluate(self, context):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        if arg < -1 or arg > 1:
            return float('nan')
        return math.asin(arg)


@method(function('acos', label='math function', nargs=1))
def evaluate(self, context):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        if arg < -1 or arg > 1:
            return float('nan')
        return math.acos(arg)


@method(function('atan', label='math function', nargs=1))
def evaluate(self, context):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        return math.atan(arg)


@method(function('atan2', label='math function', nargs=2))
def evaluate(self, context):
    x = self.get_argument(context, cls=NumericProxy)
    y = self.get_argument(context, index=1, required=True, cls=NumericProxy)
    return math.atan2(x, y)


XPath30Parser.build()
