#
# Copyright (c), 2018-2020, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
# type: ignore
"""
XPath 3.0 implementation - part 2 (symbols, operators and expressions)
"""
from copy import copy

from ..namespaces import XPATH_FUNCTIONS_NAMESPACE
from ..xpath_nodes import TypedElement, TypedAttribute, XPathNode
from ..xpath_token import ValueToken, XPathFunction
from ..xpath_context import XPathSchemaContext
from ..datatypes import QName

from .xpath30_parser import XPath30Parser


register = XPath30Parser.register
infix = XPath30Parser.infix
method = XPath30Parser.method

register(':=')

XPath30Parser.unregister('?')
register('?', bases=(ValueToken,))


@method('?')
def nud_optional_symbol(self):
    return self


###
# Braced/expanded QName(s)
XPath30Parser.duplicate('{', 'Q{')
XPath30Parser.unregister('{')
XPath30Parser.unregister('}')
register('{')
register('}', bp=100)


XPath30Parser.unregister('(')


@method(register('(', lbp=80, rpb=80, label='expression'))
def nud_parenthesized_expression(self):
    if self.parser.next_token.symbol != ')':
        self[:] = self.parser.expression(),
    self.parser.advance(')')
    return self


@method('(')
def led_parenthesized_expression(self, left):
    if left.symbol == '(name)' or left.symbol == ':' and left[1].symbol == '(name)':
        raise self.error('XPST0017', 'unknown function {!r}'.format(left.value))
    if self.parser.next_token.symbol != ')':
        self[:] = left, self.parser.expression()
    else:
        self[:] = left,
    self.parser.advance(')')
    return self


@method('(')
def evaluate_parenthesized_expression(self, context=None):
    if len(self) < 2:
        return self[0].evaluate(context) if self else []

    result = self[0].evaluate(context)
    if isinstance(result, list) and len(result) == 1:
        result = result[0]

    if not isinstance(result, XPathFunction):
        raise self.error('XPST0017', 'an XPath function expected, not {!r}'.format(type(result)))
    return result(context, self[1])


@method('(')
def select_parenthesized_expression(self, context=None):
    if len(self) < 2:
        yield from self[0].select(context) if self else iter(())
    else:

        value = self[0].evaluate(context)
        if not isinstance(value, XPathFunction):
            raise self.error('XPST0017', 'an XPath function expected, not {!r}'.format(type(value)))
        result = value(context, self[1])
        if isinstance(result, list):
            yield from result
        else:
            yield result


@method(infix('||', bp=32))
def evaluate_union_operator(self, context=None):
    return self.string_value(self.get_argument(context)) + \
        self.string_value(self.get_argument(context, index=1))


@method(infix('!', bp=72))
def select_simple_map_operator(self, context=None):
    if context is None:
        raise self.missing_context()

    for context.item in context.inner_focus_select(self[0]):
        for result in self[1].select(copy(context)):
            if not isinstance(result, (tuple, XPathNode)) and not hasattr(result, 'tag'):
                yield result
            elif isinstance(result, TypedElement):
                yield result
            elif isinstance(result, TypedAttribute):
                yield result
            else:
                yield result
                if isinstance(context, XPathSchemaContext):
                    self[1].add_xsd_type(result)


###
# 'let' expressions

@method(register('let', lbp=20, rbp=20, label='let expression'))
def nud_let_expression(self):
    del self[:]
    if self.parser.next_token.symbol != '$':
        token = self.parser.symbol_table['(name)'](self.parser, self.symbol)
        return token.nud()

    while True:
        self.parser.next_token.expected('$')
        variable = self.parser.expression(5)
        self.append(variable)
        self.parser.advance(':=')
        expr = self.parser.expression(5)
        self.append(expr)
        if self.parser.next_token.symbol != ',':
            break
        self.parser.advance()

    self.parser.advance('return')
    self.append(self.parser.expression(5))
    return self


@method('let')
def select_let_expression(self, context=None):
    if context is None:
        raise self.missing_context()

    context = copy(context)
    varnames = [self[k][0].value for k in range(0, len(self) - 1, 2)]
    values = [self[k].evaluate(copy(context)) for k in range(1, len(self) - 1, 2)]

    context.variables.update(x for x in zip(varnames, values))
    yield from self[-1].select(context)


@method('#', bp=50)
def led_function_reference(self, left):
    left.expected(':', '(name)', 'Q{')
    self[:] = left, self.parser.expression(rbp=90)
    self[1].expected('(integer)')
    return self


@method('#')
def evaluate_function_reference(self, context=None):
    if self[0].symbol == ':':
        qname = QName(self[0][1].namespace, self[0].value)
    elif self[0].symbol == 'Q{':
        qname = QName(self[0][0].value, self[0][1].value)
    else:
        qname = QName(XPATH_FUNCTIONS_NAMESPACE, self[0].value)
    arity = self[1].value

    # TODO: complete function signatures
    # if (qname, arity) not in self.parser.function_signatures:
    #    raise self.error('XPST0017')

    try:
        return self.parser.symbol_table[qname.local_name](self.parser, nargs=arity)
    except (KeyError, TypeError):
        raise self.error('XPST0017', "unknown function {}".format(qname.local_name))


# XPath 3.0 definitions continue into module xpath3_functions
