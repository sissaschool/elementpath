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
from .namespaces import XPATH_FUNCTIONS_NAMESPACE, XSD_NOTATION, XSD_ANY_ATOMIC_TYPE
from .xpath_nodes import (
    is_document_node, is_xpath_node, node_name, node_value, node_nilled, node_base_uri, node_document_uri
)
from .xpath1_parser import XPath1Parser


class XPath2Parser(XPath1Parser):
    """
    XPath 2.0 expression parser class.
    """
    symbol_table = {k: v for k, v in XPath1Parser.symbol_table.items()}
    SYMBOLS = XPath1Parser.SYMBOLS | {
        'union', 'intersect', 'instance', 'castable', 'if', 'then', 'else', 'for',
        'some', 'every', 'in', 'satisfies', 'type', 'item', 'satisfies', 'context',
        'cast', 'treat', 'return', 'except', '?', 'untyped', 'as', 'of',

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
    }

    QUALIFIED_FUNCTIONS = {
        'attribute', 'comment', 'document-node', 'element', 'empty-sequence', 'if', 'item', 'node',
        'processing-instruction', 'schema-attribute', 'schema-element', 'text', 'typeswitch'
    }

    def __init__(self, namespaces=None, variables=None, default_namespace='', function_namespace=None,
                 schema=None, compatibility_mode=False):
        super(XPath2Parser, self).__init__(namespaces, variables)
        self.default_namespace = default_namespace
        if function_namespace is None:
            self.function_namespace = XPATH_FUNCTIONS_NAMESPACE
        else:
            self.function_namespace = function_namespace
        self.schema = schema
        self.compatibility_mode = compatibility_mode

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
def select(self, context):
    results = set(self[0].select(context)) & set(self[1].select(context))
    for item in context.iter():
        if item in results:
            yield item


@method(infix('except', bp=55))
def select(self, context):
    results = set(self[0].select(context)) - set(self[1].select(context))
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


register('type')
register('context')

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
# Range expression
@method(infix('to', bp=35))
def evaluate(self, context=None):
    try:
        start = self[0].evaluate(context) + 1
        stop = self[1].evaluate(context) + 1
    except TypeError as err:
        if context is not None:
            self.wrong_type(str(err))
        return
    else:
        return range(start, stop)


@method('to')
def select(self, context):
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
def select(self, context):
    if context.item is None and is_document_node(context.root):
        if not self:
            yield context.root
        else:
            for elem in self[0].select(context):
                context.item = elem
                yield elem


#@method(function('attribute', nargs=(0, 2), bp=90))
#def select(self, context):
#    pass


@method(function('schema-attribute', nargs=1, bp=90))
def select(self, context):
    pass



@method(function('element', nargs=(0, 2), bp=90))
def select(self, context):
    pass


@method(function('schema-element', nargs=1, bp=90))
def select(self, context):
    pass


###
# Accessor functions
@method(function('node-name', nargs=1, bp=90))
def evaluate(self, context=None):
    if context is not None:
        for item in self[0].select(context):
            return node_name(item)


@method(function('nilled', nargs=1, bp=90))
def evaluate(self, context=None):
    if context is not None:
        for item in self[0].select(context):
            return node_nilled(item)


@method(function('data', nargs=1, bp=90))
def select(self, context):
    for item in self[0].select(context):
        if not is_xpath_node(item):
            yield item
        else:
            value = node_value(item)
            if value is None:
                self.wrong_type("argument node does not have a typed value [err:FOTY0012]")
            else:
                yield value


@method(function('base-uri', nargs=(0, 1), bp=90))
def evaluate(self, context=None):
    if self:
        if context is None:
            return node_base_uri(self[0].evaluate())
        for item in self[0].select(context):
            return node_base_uri(item)
    elif context is None:
        self.missing_context()
    else:
        for item in self[0].select(context):
            value = node_base_uri(item)
            if value is None:
                self.wrong_context_type('context item is not a node')
            return value


@method(function('document-uri', nargs=1, bp=90))
def evaluate(self, context=None):
    if context is None:
        return
    for item in self[0].select(context):
        return node_document_uri(item)


###
# Number functions
register('round-half-to-even')


@method(function('abs', nargs=1, bp=90))
def evaluate(self, context=None):
    item = self.get_argument(context)
    try:
        return abs(node_value(item) if is_xpath_node(item) else item)
    except TypeError:
        return float('nan')


XPath2Parser.end()
