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
from ..xpath_nodes import is_xpath_node, is_document_node, is_etree_element, TypedElement
from ..xpath_context import XPathContext, XPathSchemaContext
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
        'path', 'has-children', 'innermost', 'outermost',

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


###
# Functions and operators on nodes
@method(function('path', nargs=(0, 1)))
def evaluate(self, context=None):
    if context is None:
        raise self.missing_context()
    elif isinstance(context, XPathSchemaContext):
        return
    elif not self:
        if context.item is None:
            return '/'
        item = context.item
    else:
        item = self.get_argument(context)
        if item is None:
            return

    if is_document_node(item):
        return '/'


@method(function('has-children', nargs=(0, 1)))
def evaluate(self, context=None):
    if context is None:
        raise self.missing_context()
    elif not self:
        if context.item is None:
            return is_document_node(context.root)

        item = context.item
        if not is_xpath_node(item):
            raise self.error('XPTY0004', 'context item must be a node')
    else:
        item = self.get_argument(context)
        if item is None:
            return False
        elif not is_xpath_node(item):
            raise self.error('XPTY0004', 'argument must be a node')

    return is_document_node(item) or \
        is_etree_element(item) and len(item) > 0 or \
        isinstance(item, TypedElement) and len(item.elem) > 0


@method(function('innermost', nargs=1))
def select(self, context=None):
    if context is None:
        raise self.missing_context()

    context = context.copy()
    nodes = [e for e in self[0].select(context)]
    if any(not is_xpath_node(x) for x in nodes):
        raise self.error('XPTY0004', 'argument must contain only nodes')

    ancestors = {x for context.item in nodes for x in context.iter_ancestors(axis='ancestor')}
    yield from context.iter_results([x for x in nodes if x not in ancestors])


@method(function('outermost', nargs=1))
def select(self, context=None):
    if context is None:
        raise self.missing_context()

    context = context.copy()
    nodes = {e for e in self[0].select(context)}
    if any(not is_xpath_node(x) for x in nodes):
        raise self.error('XPTY0004', 'argument must contain only nodes')

    yield from context.iter_results([
        context.item for context.item in nodes
        if all(x not in nodes for x in context.iter_ancestors(axis='ancestor'))
    ])


XPath30Parser.build()
