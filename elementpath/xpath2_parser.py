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
from .xpath_base import is_document_node, is_attribute_node
from .xpath1_parser import XPath1Parser


class XPath2Parser(XPath1Parser):
    """
    XPath 2.0 expression parser class.
    """
    symbol_table = {k: v for k, v in XPath1Parser.symbol_table.items()}
    SYMBOLS = XPath1Parser.SYMBOLS + (
        'union', 'intersect', 'instance of', 'castable as', 'if', 'then', 'else', 'for',
        'some', 'every', 'in', 'satisfies', 'validate', 'type', 'item', 'satisfies', 'context',
        'cast as', 'treat as', 'as', 'of', 'return', 'except', 'is', 'isnot', '<<', '>>', '?',
        'untyped',

        # Mathematical operators
        'idiv',

        # XPath 2.0 added functions
        'document-node',                                   # Node test functions
    )
    RELATIVE_PATH_SYMBOLS = XPath1Parser.RELATIVE_PATH_SYMBOLS | {s for s in SYMBOLS if s.endswith("::")}

    RESERVED_FUNCTIONS = {
        'attribute(', 'comment(', 'document-node(', 'element(', 'empty-sequence(', 'if', 'item', 'node(',
        'processing-instruction(', 'schema-attribute(', 'schema-element(', 'text(', 'typeswitch'
    }

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


alias('union', '|')

register('intersect')
register('instance of')
register('castable as')


###
# 'for' expression
@method('for', bp=15)
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


@method('if', bp=15)
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


register('some')
register('every')
register('satisfies')
register('validate')
register('type')
register('item')
register('satisfies')
register('context')
register('cast as')
register('treat as')
register('as')
register('of')
register('except')
register('is')
register('isnot')
register('<<')
register('>>')
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
