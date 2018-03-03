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
from .xpath_base import is_document_node, is_attribute_node, is_xpath_node
from .xpath1_parser import XPath1Parser


class XPath2Parser(XPath1Parser):
    """
    XPath 2.0 expression parser class.
    """
    symbol_table = {k: v for k, v in XPath1Parser.symbol_table.items()}
    SYMBOLS = XPath1Parser.SYMBOLS | {
        'union', 'intersect', 'instance of', 'castable as', 'if', 'then', 'else', 'for',
        'some', 'every', 'in', 'satisfies', 'validate', 'type', 'item', 'satisfies', 'context',
        'cast as', 'treat as', 'return', 'except', '?', 'untyped',

        # Value comparison operators
        'eq', 'ne', 'lt', 'le', 'gt', 'ge',
        
        # Node comparison operators
        'is', '<<', '>>',

        # Mathematical operators
        'idiv',

        # # Node test functions
        'document-node',
    }

    QUALIFIED_FUNCTIONS = {
        'attribute', 'comment', 'document-node', 'element', 'empty-sequence', 'if', 'item', 'node',
        'processing-instruction', 'schema-attribute', 'schema-element', 'text', 'typeswitch'
    }

    def __init__(self, namespaces=None, schema=None, compatibility_mode=False):
        super(XPath2Parser, self).__init__()
        self.namespaces = namespaces if namespaces is not None else {}
        self.schema = schema
        self.compatibility_mode = compatibility_mode

    @property
    def version(self):
        return '2.0'


##
# XPath1 definitions
XPath2Parser.begin()

register = XPath2Parser.register
alias = XPath2Parser.alias
literal = XPath2Parser.literal
prefix = XPath2Parser.prefix
infix = XPath2Parser.infix
infixr = XPath2Parser.infixr
method = XPath2Parser.method
function = XPath2Parser.function
axis = XPath2Parser.axis


###
# Node sequence composition
alias('union', '|')


@method(infix('intersect', bp=55))
def select(self, context):
    results = set(self[0].select(context)) & set(self[1].select(context))
    for item in context.iter():
        if item in results:
            yield item


@method(infix('except', bp=55))
def select(self, context):
    results = set(self[0].select(context)) & set(self[1].select(context))
    for item in context.iter():
        if item in results:
            yield item


###
# 'for' expression
@method('for', bp=20)
def nud(self):
    del self[:]
    while True:
        self.parser.next_token.expected('$')
        self.append(self.parser.expression())
        self.parser.advance('in')
        self.append(self.parser.expression())
        if self.parser.next_token.symbol != ',':
            break
    self.parser.advance('return')
    self.append(self.parser.expression())
    return self


register('in')
register('return')


###
# 'if' expression
register('then')
register('else')


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
    if self.boolean(self[0].evaluate(context)):
        return self[1].evaluate(context)
    else:
        return self[2].evaluate(context)


@method('if')
def select(self, context):
    if self.boolean(list(self[0].select(context))):
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
        self.append(self.parser.expression())
        self.parser.advance('in')
        self.append(self.parser.expression())
        if self.parser.next_token.symbol != ',':
            break
    self.parser.advance('satisfies')
    self.append(self.parser.expression())
    return self


register('satisfies')


@method(function('item', nargs=0, bp=90))
def evaluate(self, context=None):
    if context is None:
        return
    elif context.item is None:
        return context.root
    else:
        return context.item


register('instance of')
register('castable as')
register('validate')
register('type')
register('context')
register('cast as')
register('treat as')
register('as')
register('of')
register('?')
register('untyped')


###
# Comma operator - concatenate items or sequences
@method(infix(',', bp=5))
def evaluate(self, context=None):
    results = []
    for op in self:
        result = op.evaluate(context)
        if isinstance(result, list):
            results.extend(result)
        else:
            results.append(result)
    return results


@method(',')
def select(self, context):
    for op in self:
        for result in op.select(context):
            yield result


@method('(')
def nud(self):
    self[0:] = self.parser.expression(),
    self.parser.advance(')')
    return self[0]


###
# Value comparison operators
@method(infix('eq', bp=30))
def evaluate(self, context=None):
    return self[0   ].evaluate(context) == self[1].evaluate(context)


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
    left = list(self[0].list(context))
    if len(left) > 1 or left and not is_xpath_node(left):
        self[0].wrong_type("left operand of %r must be a single node" % symbol)
    right = list(self[1].select(context))
    if len(right) > 1 or right and not is_xpath_node(right):
        self[0].wrong_type("right operand of %r must be a single node" % symbol)

    if len(left) != len(right):
        self[0].wrong_type("operands of %r must be both single nodes or empty sequences")
    elif len(left) == 0:
        return
    elif symbol == 'is':
        return left is right
    else:
        if left is right:
            return False
        for item in context.iter():
            if left is item:
                return True if symbol == '<<' else False
            elif right is item:
                return False if symbol == '<<' else True
        else:
            self.wrong_value("operands are not nodes of the XML tree!")


###
# Numerical operators
@method(infix('idiv', bp=45))
def evaluate(self, context=None):
    return self[0].evaluate(context) // self[1].evaluate(context)


###
# Node types
@method(function('document-node', nargs=(0, 1), bp=90))
def select(self, context):
    if context.item is None and is_document_node(context.root):
        if not self:
            yield context.root
        else:
            for elem in self[0].select(context):
                context.item = elem
                yield elem


XPath2Parser.end()
