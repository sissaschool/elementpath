#
# Copyright (c), 2018-2021, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
# type: ignore
"""
XPath 3.1 implementation - part 2 (operators and constructors)
"""
from ..xpath_token import ValueToken, ProxyToken, XPathFunction, XPathMap, XPathArray
from .xpath31_parser import XPath31Parser

register = XPath31Parser.register
method = XPath31Parser.method

register('map', bp=90, label='map', bases=(XPathMap,))
register('array', bp=90, label='array', bases=(XPathArray,))


###
# Square array constructor (pushed lazy)
@method('[')
def nud_array_constructor(self):
    if self.parser.version < '3.1':
        raise self.wrong_syntax()

    # Constructs an XPathArray token and returns it instead of the predicate
    token = XPathArray(self.parser)
    if token.parser.next_token.symbol not in (']', '(end)'):
        while True:
            token.append(self.parser.expression(5))
            if token.parser.next_token.symbol != ',':
                break
            token.parser.advance()

    token.parser.advance(']')
    return token


XPath31Parser.unregister('?')

# The ambivalence of ? symbol, used for a literal, a unary and
# a postfix operator, force to use unbalanced binding powers.
register('?', bases=(ValueToken,), lbp=6, rbp=80)


@method('?', )
def nud_unary_lookup_operator(self):
    if self.parser.next_token.symbol in ('(name)', '(integer)', '(', '*'):
        self[:] = self.parser.expression(85),
    return self  # a placeholder token


@method('?')
def led_lookup_operator(self, left):
    if self.parser.next_token.symbol in ('(name)', '(integer)', '(', '*'):
        self[:] = left, self.parser.expression(80)
        return self
    raise self.wrong_syntax()


@method('?')
def evaluate_lookup_operator(self, context=None):
    if not self:
        return self.value  # a placeholder token
    return [x for x in self.select(context)]


@method('?')
def select_lookup_operator(self, context=None):
    if not self:
        if isinstance(self.value, list):
            yield from self.value
        elif self.value is not None:
            yield self.value
        return

    if len(self) == 1:
        # unary lookup operator (used in predicates)
        if context is None:
            raise self.missing_context()
        items = (context.item,)
    else:
        items = self[0].select(context)

    for item in items:
        symbol = self[-1].symbol
        if isinstance(item, XPathMap):
            if symbol == '*':
                yield from item.values(context)
            elif symbol == '(name)':
                yield item(context, self[-1].value)
            elif symbol == '(integer)':
                yield item(context, self[-1].value)
            elif symbol == '(':
                for value in self[-1].select(context):
                    yield item(context, self.data_value(value))

        elif isinstance(item, XPathArray):
            if symbol == '*':
                yield from item.items(context)
            elif symbol == '(name)':
                raise self.error('XPTY0004')
            elif symbol == '(integer)':
                yield item(context, self[-1].value)
            elif symbol == '(':
                for value in self[-1].select(context):
                    yield item(context, self.data_value(value))

        else:
            raise self.error('XPTY0004')


@method('=>', bp=67)
def led_arrow_operator(self, left):
    next_token = self.parser.next_token
    if next_token.symbol == '$':
        self[:] = left, self.parser.expression(80)
    elif isinstance(next_token, ProxyToken):
        self.parser.parse_arguments = False
        self[:] = left, next_token.nud()
        self.parser.parse_arguments = True
        self.parser.advance()
    elif isinstance(next_token, XPathFunction):
        self[:] = left, next_token
        self.parser.advance()  # Skip static evaluation of function arguments
    elif next_token.symbol == '(name)':
        self.parser.parse_arguments = False
        self[:] = left, self.parser.expression(80)
        self.parser.parse_arguments = True
    else:
        raise next_token.wrong_syntax()

    right = self.parser.expression(67)
    self.append(right)
    return self


@method('=>')
def evaluate_arrow_operator(self, context=None):
    if isinstance(self[1], XPathFunction):
        func = self[1]
    elif self[1].symbol == ':' and isinstance(self[1][1], XPathFunction):
        func = self[1][1]
    else:
        func = self[1].evaluate(context)

    arguments = []
    if self[2]:
        if len(self[2]) == 1:
            arguments.append(self[2][0])
        else:
            tk = self[2][1]
            while True:
                if tk.symbol == ',':
                    arguments.append(tk[1].evaluate(context))
                    tk = tk[0]
                else:
                    arguments.append(tk.evaluate(context))
                    break

    arguments.append(self[0].evaluate(context))
    arguments.reverse()
    return func(context, *arguments)
