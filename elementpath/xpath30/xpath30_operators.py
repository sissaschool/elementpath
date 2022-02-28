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

from ..namespaces import XPATH_FUNCTIONS_NAMESPACE, XSD_NAMESPACE
from ..xpath_nodes import TypedElement, TypedAttribute, XPathNode
from ..xpath_token import XPathToken, ValueToken, XPathFunction
from ..xpath_context import XPathSchemaContext
from ..datatypes import QName

from .xpath30_parser import XPath30Parser


register = XPath30Parser.register
infix = XPath30Parser.infix
method = XPath30Parser.method

register(':=')

###
# Placeholder symbol (used also for optional occurrence)

XPath30Parser.unregister('?')
register('?', bases=(ValueToken,))


@method('?')
def nud_placeholder_symbol(self):
    # self.value = self
    return self


@method('?')
def evaluate_placeholder_symbol(self, context=None):
    return self


###
# Braced/expanded QName(s)

XPath30Parser.duplicate('{', 'Q{', pattern=r'Q\{')
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
    if left.symbol == '(name)':
        if left.value in self.parser.RESERVED_FUNCTION_NAMES:
            msg = f"{left.value!r} is not allowed as function name"
            raise left.error('XPST0003', msg)
        else:
            raise left.error('XPST0017', 'unknown function {!r}'.format(left.value))

    elif left.symbol == ':' and left[1].symbol == '(name)':
        if left[1].namespace == XSD_NAMESPACE:
            msg = 'unknown constructor function {!r}'.format(left[1].value)
            raise left[1].error('XPST0017', msg)
        raise left.error('XPST0017', 'unknown function {!r}'.format(left.value))

    if self.parser.next_token.symbol != ')':
        self[:] = left, self.parser.expression()
    else:
        self[:] = left,
    self.parser.advance(')')
    return self


@method('(')
def evaluate_parenthesized_expression(self, context=None):
    if not self:
        return []

    value = self[0].evaluate(context)
    if isinstance(value, list) and len(value) == 1:
        value = value[0]

    if len(self) > 1:
        if isinstance(value, XPathFunction):
            return value(context, self[1])
        elif self[0].symbol == '(':
            if not isinstance(value, list):
                return value
            elif any(not isinstance(x, XPathFunction) for x in value):
                return value

        if isinstance(value, XPathToken) and value.symbol == '?':
            return value

        raise self.error('XPTY0004', f'an XPath function expected, not {type(value)!r}')

    if not isinstance(value, XPathFunction) or self[0].span[0] > self.span[0]:
        return value
    else:
        return value(context)


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
    for k in range(0, len(self) - 1, 2):
        varname = self[k][0].value
        value = self[k+1].evaluate(context)
        context.variables[varname] = value

    yield from self[-1].select(context)


@method('#', bp=90)
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
    elif self[0].value in self.parser.RESERVED_FUNCTION_NAMES:
        msg = f"{self[0].value!r} is not allowed as function name"
        raise self.error('XPST0003', msg)
    else:
        qname = QName(XPATH_FUNCTIONS_NAMESPACE, self[0].value)

    arity = self[1].value
    namespace = qname.namespace
    local_name = qname.local_name

    # Generic rule for XSD constructor functions
    if namespace == XSD_NAMESPACE and arity != 1:
        raise self.error('XPST0017', f"unknown function {qname.qname}#{arity}")

    # Special checks for multirole tokens
    if namespace == XPATH_FUNCTIONS_NAMESPACE and \
            local_name in ('QName', 'dateTime') and arity == 1:
        raise self.error('XPST0017', f"unknown function {qname.qname}#{arity}")

    try:
        token_class = self.parser.symbol_table[local_name]
    except KeyError:
        msg = f"unknown function {qname.qname}#{arity}"
        raise self.error('XPST0017', msg) from None
    else:
        if token_class.symbol == 'function' or not token_class.label.endswith('function'):
            raise self.error('XPST0003')

    try:
        func = token_class(self.parser, nargs=arity)
    except TypeError:
        msg = f"unknown function {qname.qname}#{arity}"
        raise self.error('XPST0017', msg) from None
    else:
        if func.namespace is None:
            func.namespace = namespace
        elif func.namespace != namespace:
            raise self.error('XPST0017', f"unknown function {qname.qname}#{arity}")
        return func

# XPath 3.0 definitions continue into module xpath3_functions
