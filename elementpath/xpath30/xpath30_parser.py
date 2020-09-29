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

Refs:
  - https://www.w3.org/TR/2014/REC-xpath-30-20140408/
  - https://www.w3.org/TR/xpath-functions-30/
"""
import math
import xml.etree.ElementTree as ElementTree

from ..namespaces import XPATH_FUNCTIONS_NAMESPACE, XPATH_MATH_FUNCTIONS_NAMESPACE, \
    XSLT_XQUERY_SERIALIZATION_NAMESPACE
from ..xpath_nodes import etree_iterpath, is_xpath_node, is_document_node, \
    is_etree_element, TypedElement, TypedAttribute, AttributeNode, TextNode
from ..xpath_context import XPathSchemaContext
from ..xpath2 import XPath2Parser
from ..datatypes import NumericProxy


class XPath30Parser(XPath2Parser):
    """
    XPath 3.0 expression parser class.
    """
    version = '3.0'

    SYMBOLS = XPath2Parser.SYMBOLS | {
        'Q{',  # see BracedURILiteral rule

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
        'parse-xml', 'parse-xml-fragment', 'serialize',

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

XPath30Parser.duplicate('{', 'Q{')


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
    elif isinstance(item, TypedElement):
        elem = item.elem
    elif is_etree_element(item):
        elem = item
    else:
        elem = self._elem

    try:
        root = context.root.getroot()
    except AttributeError:
        root = context.root
        path = 'Q{%s}root()' % XPATH_FUNCTIONS_NAMESPACE
    else:
        path = '/%s' % root.tag

    for e, path in etree_iterpath(root, path):
        if e is elem:
            return path


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


# Parsing and serializing
@method(function('parse-xml', nargs=1))
@method(function('parse-xml-fragment', nargs=1))
def evaluate(self, context=None):
    # TODO: resolve relative entity references with static base URI
    arg = self.get_argument(context, cls=str)
    if arg is None:
        return

    etree = ElementTree if context is None else context.etree
    if self.symbol == 'parse-xml-fragment':
        # Wrap argument in a fake document because an
        # XML document can have only one root element
        arg = '<document>{}</document>'.format(arg)

    try:
        root = etree.XML(arg)
    except etree.ParseError:
        raise self.error('FODC0006')
    else:
        return etree.ElementTree(root)


@method(function('serialize', nargs=(1, 2)))
def evaluate(self, context=None):
    # TODO full implementation of serialization with
    #  https://www.w3.org/TR/xpath-functions-30/#xslt-xquery-serialization-30

    params = self.get_argument(context, index=1) if len(self) == 2 else None
    if params is None:
        tmpl = '<output:serialization-parameters xmlns:output="{}"/>'
        params = ElementTree.XML(tmpl.format(XSLT_XQUERY_SERIALIZATION_NAMESPACE))

    chunks = []
    etree = ElementTree if context is None else context.etree

    child = params.find(
        'output:serialization-parameters/omit-xml-declaration',
        namespaces={'output': XSLT_XQUERY_SERIALIZATION_NAMESPACE},
    )
    xml_declaration = child is not None and child.get('value') in ('yes',)

    for item in self[0].select(context):
        if is_etree_element(item):
            chunks.append(etree.tostring(
                item, encoding='utf-8', xml_declaration=xml_declaration
            ))

    return b'\n'.join(chunks)


XPath30Parser.build()
