# -*- coding: utf-8 -*-
#
# Copyright (c), 2018, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import decimal
import math
from itertools import product

from .exceptions import ElementPathTypeError
from .namespaces import (
    XPATH_FUNCTIONS_NAMESPACE, XPATH_2_DEFAULT_NAMESPACES, XSD_NOTATION, XSD_ANY_ATOMIC_TYPE, prefixed_to_qname
)
from .xpath_helpers import (
    is_document_node, is_xpath_node, is_element_node, is_attribute_node, node_name,
    node_string_value, node_nilled, node_base_uri, node_document_uri, boolean_value,
    data_value, string_value
)
from .xpath1_parser import XPath1Parser
from .schema_proxy import AbstractSchemaProxy


class XPath2Parser(XPath1Parser):
    """
    XPath 2.0 expression parser class. The parser instance represents also the XPath static context.

    :param namespaces: A dictionary with mapping from namespace prefixes into URIs.
    :param variables: A dictionary with the static context's in-scope variables.
    :param default_namespace: The default namespace to apply to unprefixed names. \
    For default no namespace is applied (empty namespace '').
    :param function_namespace: The default namespace to apply to unprefixed function names. \
    For default no namespace is applied (empty namespace '').
    :param schema: The schema proxy instance to use for types, attributes and elements lookups. \
    If it's not provided the XPath 2.0 schema's related expressions cannot be used.
    :param compatibility_mode: If set to `True` the parser instance works with XPath 1.0 compatibility rules.
    """
    symbol_table = {k: v for k, v in XPath1Parser.symbol_table.items()}
    SYMBOLS = XPath1Parser.SYMBOLS | {
        'union', 'intersect', 'instance', 'castable', 'if', 'then', 'else', 'for',
        'some', 'every', 'in', 'satisfies', 'item', 'satisfies', 'cast', 'treat',
        'return', 'except', '?', 'as', 'of',

        # Comments
        '(:', ':)',

        # Value comparison operators
        'eq', 'ne', 'lt', 'le', 'gt', 'ge',
        
        # Node comparison operators
        'is', '<<', '>>',

        # Mathematical operators
        'idiv',

        # Node test functions
        'document-node', 'schema-attribute', 'element', 'schema-element',  # 'attribute',

        # Accessor functions
        'node-name', 'nilled', 'data', 'base-uri', 'document-uri',

        # Number functions
        'abs', 'round-half-to-even',

        # General functions for sequences
        'distinct-values', 'empty', 'exists', 'index-of', 'insert-before', 'remove',
        'reverse', 'subsequence', 'unordered',

        # Cardinality functions for sequences
        'zero-or-one', 'one-or-more', 'exactly-one',
    }

    QUALIFIED_FUNCTIONS = {
        'attribute', 'comment', 'document-node', 'element', 'empty-sequence', 'if', 'item', 'node',
        'processing-instruction', 'schema-attribute', 'schema-element', 'text', 'typeswitch'
    }

    DEFAULT_NAMESPACES = XPATH_2_DEFAULT_NAMESPACES

    def __init__(self, namespaces=None, variables=None, default_namespace='', function_namespace=None,
                 schema=None, compatibility_mode=False):
        super(XPath2Parser, self).__init__(namespaces, variables)
        self.default_namespace = default_namespace

        if function_namespace is None:
            self.function_namespace = XPATH_FUNCTIONS_NAMESPACE
        else:
            self.function_namespace = function_namespace

        if schema is not None and not isinstance(schema, AbstractSchemaProxy):
            raise ElementPathTypeError("schema argument must be a subclass of AbstractSchemaProxy!")
        self.schema = schema
        if compatibility_mode is False:
            self.compatibility_mode = False

    @property
    def version(self):
        return '2.0'

    def advance(self, *symbols):
        super(XPath2Parser, self).advance(*symbols)
        if self.next_token.symbol == '(:':
            token = self.token
            if token is None:
                self.next_token.comment = self.comment()
            elif token.comment is None:
                token.comment = self.comment()
            else:
                token.comment = '%s %s' % (token.comment, self.comment())

        return self.next_token

    def comment(self):
        """
        Parses and consumes a XPath 2.0 comment. Comments are delimited by symbols
        '(:' and ':)' and can be nested. A comment is attached to the previous token
        or the next token when the previous is None.
        """
        if self.next_token.symbol != '(:':
            return

        super(XPath2Parser, self).advance()
        comment_level = 1
        comment = []
        while comment_level:
            super(XPath2Parser, self).advance()
            token = self.token
            if token.symbol == ':)':
                comment_level -= 1
                if comment_level:
                    comment.append(str(token.value))
            elif token.symbol == '(:':
                comment_level += 1
                comment.append(str(token.value))
            else:
                comment.append(str(token.value))
        return ' '.join(comment)


##
# XPath 2.0 definitions
XPath2Parser.begin()

register = XPath2Parser.register
unregister = XPath2Parser.unregister
alias = XPath2Parser.alias
literal = XPath2Parser.literal
prefix = XPath2Parser.prefix
infix = XPath2Parser.infix
infixr = XPath2Parser.infixr
method = XPath2Parser.method
function = XPath2Parser.function
axis = XPath2Parser.axis

##
# Remove symbols that have to be redefined for XPath 2.0.
unregister(',')

###
# Symbols
register('then')
register('else')
register('in')
register('return')
register('satisfies')
register('as')
register('of')
register('?')
register('(:')
register(':)')


###
# Node sequence composition
alias('union', '|')


@method(infix('intersect', bp=55))
def select(self, context=None):
    results = set(self[0].select(context)) & set(self[1].select(context))
    for item in context.iter():
        if item in results:
            yield item


@method(infix('except', bp=55))
def select(self, context=None):
    results = set(self[0].select(context)) - set(self[1].select(context))
    for item in context.iter():
        if item in results:
            yield item


###
# 'if' expression
@method('if', bp=20)
def nud(self):
    self.parser.advance('(')
    self[0:] = self.parser.expression(),
    self.parser.advance(')')
    self.parser.advance('then')
    self[1:] = self.parser.expression(),
    self.parser.advance('else')
    self[2:] = self.parser.expression(),
    return self


@method('if')
def evaluate(self, context=None):
    if boolean_value(self[0].evaluate(context)):
        return self[1].evaluate(context)
    else:
        return self[2].evaluate(context)


@method('if')
def select(self, context=None):
    if boolean_value(list(self[0].select(context))):
        for result in self[1].select(context):
            yield result
    else:
        for result in self[2].select(context):
            yield result


###
# Quantified expressions
@method('some', bp=20)
@method('every', bp=20)
def nud(self):
    del self[:]
    while True:
        self.parser.next_token.expected('$')
        self.append(self.parser.expression(5))
        self.parser.advance('in')
        self.append(self.parser.expression(5))
        if self.parser.next_token.symbol == ',':
            self.parser.advance()
        else:
            break

    self.parser.advance('satisfies')
    self.append(self.parser.expression(5))
    return self


@method('some')
@method('every')
def evaluate(self, context=None):
    some = self.symbol == 'some'
    if context is not None:
        selectors = tuple(self[k].select(context.copy()) for k in range(1, len(self) - 1, 2))
        for results in product(*selectors):
            for i in range(len(results)):
                context.variables[self[i * 2][0].value] = results[i]
            if boolean_value(list(self[-1].select(context.copy()))):
                if some:
                    return True
            elif not some:
                return False
        return not some


###
# 'for' expressions
@method('for', bp=20)
def nud(self):
    del self[:]
    while True:
        self.parser.next_token.expected('$')
        self.append(self.parser.expression(5))
        self.parser.advance('in')
        self.append(self.parser.expression(5))
        if self.parser.next_token.symbol == ',':
            self.parser.advance()
        else:
            break

    self.parser.advance('return')
    self.append(self.parser.expression(5))
    return self


@method('for')
def evaluate(self, context=None):
    if context is not None:
        return list(self.select(context.copy()))


@method('for')
def select(self, context=None):
    if context is not None:
        selectors = tuple(self[k].select(context.copy()) for k in range(1, len(self) - 1, 2))
        for results in product(*selectors):
            for i in range(len(results)):
                context.variables[self[i * 2][0].value] = results[i]
            for result in self[-1].select(context.copy()):
                yield result


@method(function('item', nargs=0, bp=90))
def evaluate(self, context=None):
    if context is None:
        return
    elif context.item is None:
        return context.root
    else:
        return context.item


###
# Sequence type based
@method('instance', bp=60)
@method('treat', bp=61)
def led(self, left):
    self.parser.advance('of' if self.symbol is 'instance' else 'as')
    self[0:1] = left, self.parser.expression(rbp=self.rbp)
    next_symbol = self.parser.next_token.symbol
    if self[1].symbol != 'empty-sequence' and next_symbol in ('?', '*', '+'):
        self[3:] = next_symbol,
        self.advance()
    return self


@method('instance')
def evaluate(self, context=None):
    if self.parser.schema is None:
        self.missing_schema()
    treat_expr = self[0].evaluate(context)
    if self[1].symbol == 'empty-sequence':
        return treat_expr == []
    type_qname = self[1].evaluate(context)
    occurs = self[2] if len(self) > 2 else None
    return self.parser.schema.is_instance(treat_expr, type_qname, occurs)


###
# Simple type based
@method('castable', bp=62)
@method('cast', bp=63)
def led(self, left):
    self.parser.advance('of')
    self[0:1] = left, self.parser.expression(rbp=self.rbp)
    if self.parser.next_token.symbol == '?':
        self[3:] = '?',
        self.advance()
    return self


@method('castable', bp=62)
@method('cast', bp=63)
def evaluate(self, context=None):
    if self.parser.schema is None:
        self.missing_schema()
    unary_expr = self.atomize(self[0].evaluate(context))
    if unary_expr in (XSD_NOTATION, XSD_ANY_ATOMIC_TYPE):
        self.wrong_type("target type cannot be xs:NOTATION or xs:anyAtomicType [err:XPST0080]")
    type_qname = self[1].evaluate(context)
    required = len(self) <= 2
    return self.parser.schema.cast_as(unary_expr, type_qname, required)


###
# Comma operator - concatenate items or sequences
@method(infix(',', bp=5))
def evaluate(self, context=None):
    results = []
    for op in self:
        result = op.evaluate(context)
        if isinstance(result, list):
            results.extend(result)
        elif results is not None:
            results.append(result)
    return results


@method(',')
def select(self, context=None):
    for op in self:
        for result in op.select(context):
            yield result


###
# Parenthesized expressions: XPath 2.0 admits empty case ()
@method('(')
def nud(self):
    if self.parser.next_token.symbol == ')':
        self.parser.advance(')')
        return self
    else:
        self[0:] = self.parser.expression(),
        self.parser.advance(')')
        return self[0]  # Skip self!! (remove a redundant level from selection/evaluation)


@method('(')
def evaluate(self, context=None):
    return []


@method('(')
def select(self, context=None):
    for _ in []:
        yield


###
# Value comparison operators
@method(infix('eq', bp=30))
def evaluate(self, context=None):
    return self[0].evaluate(context) == self[1].evaluate(context)


@method(infix('ne', bp=30))
def evaluate(self, context=None):
    return self[0].evaluate(context) != self[1].evaluate(context)


@method(infix('lt', bp=30))
def evaluate(self, context=None):
    return self[0].evaluate(context) < self[1].evaluate(context)


@method(infix('gt', bp=30))
def evaluate(self, context=None):
    return self[0].evaluate(context) > self[1].evaluate(context)


@method(infix('le', bp=30))
def evaluate(self, context=None):
    return self[0].evaluate(context) <= self[1].evaluate(context)


@method(infix('ge', bp=30))
def evaluate(self, context=None):
    return self[0].evaluate(context) >= self[1].evaluate(context)


###
# Node comparison
@method(infix('is', bp=30))
@method(infix('<<', bp=30))
@method(infix('>>', bp=30))
def evaluate(self, context=None):
    symbol = self.symbol

    left = list(self[0].select(context))
    if not left:
        return
    elif len(left) > 1 or not is_xpath_node(left[0]):
        self[0].wrong_type("left operand of %r must be a single node" % symbol)

    right = list(self[1].select(context))
    if not right:
        return
    elif len(right) > 1 or not is_xpath_node(right[0]):
        self[0].wrong_type("right operand of %r must be a single node" % symbol)

    if symbol == 'is':
        return left[0] is right[0]
    else:
        if left[0] is right[0]:
            return False
        for item in context.iter():
            if left[0] is item:
                return True if symbol == '<<' else False
            elif right[0] is item:
                return False if symbol == '<<' else True
        else:
            self.wrong_value("operands are not nodes of the XML tree!")


###
# Range expression
@method(infix('to', bp=35))
def evaluate(self, context=None):
    try:
        start = self[0].evaluate(context)
        stop = self[1].evaluate(context) + 1
    except TypeError as err:
        if context is not None:
            self.wrong_type(str(err))
        return
    else:
        return list(range(start, stop))


@method('to')
def select(self, context=None):
    for k in self.evaluate(context):
        yield k


###
# Numerical operators
@method(infix('idiv', bp=45))
def evaluate(self, context=None):
    return self[0].evaluate(context) // self[1].evaluate(context)


###
# Node types
@method(function('document-node', nargs=(0, 1), bp=90))
def evaluate(self, context=None):
    if context is None:
        return
    elif context.item is None and is_document_node(context.root):
        if not self:
            return context.root
        elif is_element_node(context.root.getroot(), self[0].evaluate(context)):
            return context.root


@method(function('element', nargs=(0, 2), bp=90))
def evaluate(self, context=None):
    if context is None:
        return
    elif not self:
        if is_element_node(context.item):
            return context.item
    else:
        if is_element_node(context.item, self[1].evaluate(context)):
            return context.item


@method(function('schema-attribute', nargs=1, bp=90))
def evaluate(self, context=None):
    if self[0].symbol == ':':
        attribute_name = '%s:%s' % (self[0][0].value, self[0][1].value)
    else:
        attribute_name = self[0].value

    qname = prefixed_to_qname(attribute_name, self.parser.namespaces)
    if self.parser.schema.get_attribute(qname) is None:
        self.missing_name("attribute %r not found in schema" % attribute_name)

    if context is not None:
        if is_attribute_node(context.item) and context.item[0] == qname:
            return context.item


@method(function('schema-element', nargs=1, bp=90))
def evaluate(self, context=None):
    if self[0].symbol == ':':
        element_name = '%s:%s' % (self[0][0].value, self[0][1].value)
    else:
        element_name = self[0].value

    qname = prefixed_to_qname(element_name, self.parser.namespaces)
    if self.parser.schema.get_element(qname) is None \
            and self.parser.schema.get_substitution_group(qname) is None:
        self.missing_name("element %r not found in schema" % element_name)

    if context is not None:
        if is_element_node(context.item) and context.item.tag == qname:
            return context.item


###
# Accessor functions
@method(function('node-name', nargs=1, bp=90))
def evaluate(self, context=None):
    return node_name(self.get_argument(context))


@method(function('nilled', nargs=1, bp=90))
def evaluate(self, context=None):
    return node_nilled(self.get_argument(context))


@method(function('data', nargs=1, bp=90))
def select(self, context=None):
    for item in self[0].select(context):
        value = data_value(item)
        if value is None:
            self.wrong_type("argument node does not have a typed value [err:FOTY0012]")
        else:
            yield value


@method(function('base-uri', nargs=(0, 1), bp=90))
def evaluate(self, context=None):
    item = self.get_argument(context)
    if item is None:
        self.missing_context("context item is undefined")
    elif not is_xpath_node(item):
        self.wrong_context_type("context item is not a node")
    else:
        return node_base_uri


@method(function('document-uri', nargs=1, bp=90))
def evaluate(self, context=None):
    return node_document_uri(self.get_argument(context))


###
# Number functions
@method(function('round-half-to-even', nargs=(1, 2), bp=90))
def evaluate(self, context=None):
    item = self.get_argument(context)
    try:
        value = round(decimal.Decimal(item), 0 if len(self) < 2 else self[1].evaluate(context))
    except TypeError as err:
        if item is not None and not isinstance(item, list):
            self.wrong_type(str(err))
    except decimal.DecimalException as err:
        if item is not None and not isinstance(item, list):
            self.wrong_value(str(err))
    else:
        return float(value)


@method(function('abs', nargs=1, bp=90))
def evaluate(self, context=None):
    item = self.get_argument(context)
    try:
        return abs(node_string_value(item) if is_xpath_node(item) else item)
    except TypeError:
        return float('nan')


###
# General functions for sequences
@method(function('empty', nargs=1, bp=90))
@method(function('exists', nargs=1, bp=90))
def evaluate(self, context=None):
    return next(iter(self.select(context)))


@method('empty')
def select(self, context=None):
    try:
        next(iter(self[0].select(context)))
    except StopIteration:
        yield True
    else:
        yield False


@method('exists')
def select(self, context=None):
    try:
        next(iter(self[0].select(context)))
    except StopIteration:
        yield False
    else:
        yield True


@method(function('distinct-values', nargs=(1, 2), bp=90))
@method(function('insert-before', nargs=3, bp=90))
@method(function('index-of', nargs=(1, 3), bp=90))
@method(function('remove', nargs=2, bp=90))
@method(function('reverse', nargs=1, bp=90))
@method(function('subsequence', nargs=(2, 3), bp=90))
@method(function('unordered', nargs=1, bp=90))
def evaluate(self, context=None):
    return list(self.select(context))


@method('distinct-values')
def select(self, context=None):
    nan = False
    results = []
    for item in self[0].select(context):
        if not nan and isinstance(item, float) and math.isnan(item):
            yield item
            nan = True
        elif all(item != res for res in results):
            yield item
            results.append(item)


@method('insert-before')
def select(self, context=None):
    insert_at_pos = max(0, self[1].value - 1)
    inserted = False
    for pos, result in enumerate(self[0].select(context.copy() if context else None)):
        if not inserted and pos == insert_at_pos:
            for item in self[2].select(context.copy() if context else None):
                yield item
            inserted = True
        yield result

    if not inserted:
        for item in self[2].select(context.copy() if context else None):
            yield item


@method('index-of')
def select(self, context=None):
    value = self[1].evaluate(context)
    for pos, result in enumerate(self[0].select(context)):
        if result == value:
            yield pos + 1


@method('remove')
def select(self, context=None):
    target = self[1].evaluate(context) - 1
    for pos, result in enumerate(self[0].select(context)):
        if pos != target:
            yield result


@method('reverse')
def select(self, context=None):
    for result in reversed(list(self[0].select(context))):
        yield result


@method('subsequence')
def select(self, context=None):
    starting_loc = self[1].evaluate(context) - 1
    length = self[2].evaluate(context) if len(self) >= 3 else 0
    for pos, result in enumerate(self[0].select(context)):
        if starting_loc <= pos and (not length or pos < starting_loc + length):
            yield result


@method('unordered')
def select(self, context=None):
    for result in sorted(list(self[0].select(context)), key=lambda x: string_value(x)):
        yield result


###
# Cardinality functions for sequences
@method(function('zero-or-one', nargs=1, bp=90))
@method(function('one-or-more', nargs=1, bp=90))
@method(function('exactly-one', nargs=1, bp=90))
def evaluate(self, context=None):
    return list(self.select(context))


@method('zero-or-one')
def select(self, context=None):
    results = iter(self[0].select(context))
    try:
        item = next(results)
    except StopIteration:
        return

    try:
        next(results)
    except StopIteration:
        yield item
    else:
        self.wrong_value("called with a sequence containing more than one item [err:FORG0003]")


@method('one-or-more')
def select(self, context=None):
    results = iter(self[0].select(context))
    try:
        item = next(results)
    except StopIteration:
        self.wrong_value("called with a sequence containing no items [err:FORG0004]")
    else:
        yield item
        while True:
            try:
                yield next(results)
            except StopIteration:
                break


@method('exactly-one')
def select(self, context=None):
    results = iter(self[0].select(context))
    try:
        item = next(results)
    except StopIteration:
        self.wrong_value("called with a sequence containing zero items [err:FORG0005]")
    else:
        try:
            next(results)
        except StopIteration:
            yield item
        else:
            self.wrong_value("called with a sequence containing more than one item [err:FORG0005]")


###
# Example of token redefinition and howto create a multi-role token.
#
# In XPath 2.0 the 'attribute' keyword is used not only for the attribute:: axis but also for
# attribute() node type function.
###
class MultiValue(object):

    def __init__(self, *values):
        self.values = values

    def __eq__(self, other):
        return any(other == v for v in self.values)

    def __ne__(self, other):
        return all(other != v for v in self.values)


unregister('attribute')
register('attribute', lbp=90, rbp=90, label=MultiValue('function', 'axis'),
         pattern='\\battribute(?=\s*\\:\\:|\s*\\(\\:.*\\:\\)\s*\\:\\:|\s*\\(|\s*\\(\\:.*\\:\\)\\()')


@method('attribute')
def nud(self):
    if self.parser.next_token.symbol == '::':
        self.parser.advance('::')
        self.parser.next_token.expected(
            '(name)', '*', 'text', 'node', 'document-node', 'comment', 'processing-instruction',
            'attribute', 'schema-attribute', 'element', 'schema-element'
        )
        self[0:] = self.parser.expression(rbp=90),
        self.label = 'axis'
    else:
        self.parser.advance('(')
        if self.parser.next_token.symbol != ')':
            self[0:] = self.parser.expression(5),
            if self.parser.next_token.symbol == ',':
                self.parser.advance(',')
                self[1:] = self.parser.expression(5),
        self.parser.advance(')')
        self.label = 'function'
    return self


@method('attribute')
def select(self, context=None):
    if context is None:
        return
    elif self.label == 'axis':
        for _ in context.iter_attributes():
            for result in self[0].select(context):
                yield result
    else:
        yield self.evaluate(context)


@method('attribute')
def evaluate(self, context=None):
    if context is None:
        return
    elif not self:
        if is_attribute_node(context.item):
            return context.item
    else:
        if is_attribute_node(context.item, self[1].evaluate(context)):
            return context.item


XPath2Parser.end()
