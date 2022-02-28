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
XPath 2.0 implementation - part 2 (operators, expressions and multi-role tokens)
"""
import math
import operator
from copy import copy
from decimal import Decimal, DivisionByZero

from ..exceptions import ElementPathError, ElementPathTypeError
from ..helpers import OCCURRENCE_INDICATORS, numeric_equal, numeric_not_equal
from ..namespaces import XSD_NAMESPACE, XSD_NOTATION, XSD_ANY_ATOMIC_TYPE, \
    XSI_NIL, get_namespace, get_expanded_name
from ..datatypes import UntypedAtomic, QName, AnyURI, Duration, Integer, DoubleProxy10
from ..xpath_nodes import TypedElement, is_xpath_node, \
    match_attribute_node, is_element_node, is_document_node
from ..xpath_context import XPathSchemaContext
from ..xpath_token import XPathFunction

from .xpath2_parser import XPath2Parser

COMPARISON_OPERATORS = {'eq', 'ne', 'lt', 'le', 'gt', 'ge'}

register = XPath2Parser.register
infix = XPath2Parser.infix
method = XPath2Parser.method
function = XPath2Parser.function


@method('as')
@method('of')
def nud_as_and_of_symbols(self):
    raise self.error('XPDY0002')  # Dynamic context required


###
# Variables
@method('$', bp=90)
def nud_variable_reference(self):
    self.parser.expected_name('(name)', 'Q{')
    self[:] = self.parser.expression(rbp=90),
    return self


@method('$')
def evaluate_variable_reference(self, context=None):
    if context is None:
        raise self.missing_context()

    try:
        get_expanded_name(self[0].value, self.parser.namespaces)
    except KeyError as err:
        raise self.error('XPST0081', "namespace prefix {} not found".format(err))

    varname = self[0].value
    try:
        return context.variables[varname]
    except KeyError:
        if isinstance(context, XPathSchemaContext):
            try:
                sequence_type = self.parser.variable_types[varname].strip()
            except KeyError:
                pass
            else:
                if sequence_type[-1] in OCCURRENCE_INDICATORS:
                    sequence_type = sequence_type[:-1]

                if QName.pattern.match(sequence_type) is not None:
                    return self.parser.get_atomic_value(sequence_type)
                return UntypedAtomic('')

    raise self.missing_name('unknown variable %r' % str(varname))


###
# Node sequence composition
XPath2Parser.duplicate('|', 'union')


@method(infix('intersect', bp=55))
@method(infix('except', bp=55))
def select_intersect_and_except_operators(self, context=None):
    if context is None:
        raise self.missing_context()

    s1, s2 = set(self[0].select(copy(context))), set(self[1].select(copy(context)))
    if any(not is_xpath_node(x) for x in s1) or any(not is_xpath_node(x) for x in s2):
        raise self.error('XPTY0004', 'only XPath nodes are allowed')

    if self.symbol == 'except':
        yield from context.iter_results(s1 - s2)
    else:
        yield from context.iter_results(s1 & s2)


###
# 'if' expression
@method('if', bp=20)
def nud_if_expression(self):
    if self.parser.next_token.symbol != '(':
        token = self.parser.symbol_table['(name)'](self.parser, self.symbol)
        return token.nud()

    self.parser.advance('(')
    self[:] = self.parser.expression(5),
    self.parser.advance(')')
    self.parser.advance('then')
    self[1:] = self.parser.expression(5),
    self.parser.advance('else')
    self[2:] = self.parser.expression(5),
    return self


@method('if')
def evaluate_if_expression(self, context=None):
    if self.boolean_value(self[0].evaluate(copy(context))):
        return self[1].evaluate(context)
    else:
        return self[2].evaluate(context)


@method('if')
def select_if_expression(self, context=None):
    if self.boolean_value([x for x in self[0].select(copy(context))]):
        yield from self[1].select(context)
    else:
        yield from self[2].select(context)


###
# Quantified expressions
@method('some', bp=20)
@method('every', bp=20)
def nud_quantified_expressions(self):
    del self[:]
    if self.parser.next_token.symbol != '$':
        token = self.parser.symbol_table['(name)'](self.parser, self.symbol)
        return token.nud()

    while True:
        self.parser.next_token.expected('$')
        variable = self.parser.expression(5)
        self.append(variable)
        self.parser.advance('in')
        expr = self.parser.expression(5)
        self.append(expr)
        for tk in filter(lambda x: x.symbol == '$', expr.iter()):
            if tk[0].value == variable[0].value:
                raise tk.error('XPST0008', 'loop variable in its range expression')

        if self.parser.next_token.symbol != ',':
            break
        self.parser.advance()

    self.parser.advance('satisfies')
    self.append(self.parser.expression(5))
    return self


@method('some')
@method('every')
def evaluate_quantified_expressions(self, context=None):
    if context is None:
        raise self.missing_context()

    context = copy(context)
    some = self.symbol == 'some'
    varnames = [self[k][0].value for k in range(0, len(self) - 1, 2)]
    selectors = [self[k].select for k in range(1, len(self) - 1, 2)]

    for results in copy(context).iter_product(selectors, varnames):
        context.variables.update(x for x in zip(varnames, results))
        if self.boolean_value([x for x in self[-1].select(copy(context))]):
            if some:
                return True
        elif not some:
            return False

    return not some


###
# 'for' expressions
@method('for', bp=20)
def nud_for_expression(self):
    del self[:]
    if self.parser.next_token.symbol != '$':
        token = self.parser.symbol_table['(name)'](self.parser, self.symbol)
        return token.nud()

    while True:
        self.parser.next_token.expected('$')
        variable = self.parser.expression(5)
        self.append(variable)
        self.parser.advance('in')
        expr = self.parser.expression(5)
        self.append(expr)
        for tk in filter(lambda x: x.symbol == '$', expr.iter()):
            if tk[0].value == variable[0].value:
                raise tk.error('XPST0008', 'loop variable in its range expression')

        if self.parser.next_token.symbol != ',':
            break
        self.parser.advance()

    self.parser.advance('return')
    self.append(self.parser.expression(5))
    return self


@method('for')
def select_for_expression(self, context=None):
    if context is None:
        raise self.missing_context()

    context = copy(context)
    varnames = [self[k][0].value for k in range(0, len(self) - 1, 2)]
    selectors = [self[k].select for k in range(1, len(self) - 1, 2)]

    for results in copy(context).iter_product(selectors, varnames):
        context.variables.update(x for x in zip(varnames, results))
        yield from self[-1].select(copy(context))


###
# Sequence type based
@method('instance', bp=60)
@method('treat', bp=61)
def led_sequence_type_based_expressions(self, left):
    self.parser.advance('of' if self.symbol == 'instance' else 'as')
    if self.parser.next_token.label not in ('kind test', 'sequence type', 'function test'):
        self.parser.expected_name('(name)', ':')

    try:
        self[:] = left, self.parser.expression(rbp=self.rbp)
    except ElementPathTypeError as err:
        message = getattr(err, 'message', str(err))
        raise self.error('XPST0003', message) from None

    next_symbol = self.parser.next_token.symbol
    if self[1].symbol != 'empty-sequence' and next_symbol in ('?', '*', '+'):
        self[2:] = self.parser.symbol_table[next_symbol](self.parser),  # Add nullary token
        self.parser.advance()
    return self


@method('instance')
def evaluate_instance_expression(self, context=None):
    if len(self) > 2:
        occurs = self[2].symbol
    else:
        occurs = self[1].occurrence
    position = None

    if self[1].symbol == 'empty-sequence':
        for _ in self[0].select(context):
            return False
        return True
    elif self[1].label in ('kind test', 'sequence type', 'function test'):
        if context is None:
            raise self.missing_context()

        for position, context.item in enumerate(self[0].select(context)):
            result = self[1].evaluate(context)
            if result is None or isinstance(result, list) and not result:
                return occurs in ('*', '?')
            elif position and (occurs is None or occurs == '?'):
                return False
        else:
            return position is not None or occurs in ('*', '?')
    else:
        try:
            qname = get_expanded_name(self[1].source, self.parser.namespaces)
        except KeyError as err:
            raise self.error('XPST0081', "namespace prefix {} not found".format(err))

        for position, item in enumerate(self[0].select(context)):
            try:
                if not self.parser.is_instance(item, qname):
                    return False
            except KeyError:
                msg = "atomic type %r not found in in-scope schema types"
                raise self.error('XPST0051', msg % self[1].source) from None
            else:
                if position and (occurs is None or occurs == '?'):
                    return False
        else:
            return position is not None or occurs in ('*', '?')


@method('treat')
def evaluate_treat_expression(self, context=None):
    if len(self) > 2:
        occurs = self[2].symbol
    else:
        occurs = self[1].occurrence

    position = None
    castable_expr = []
    if self[1].symbol == 'empty-sequence':
        for _ in self[0].select(context):
            raise self.wrong_sequence_type()
    elif self[1].label in ('kind test', 'sequence type', 'function test'):
        for position, item in enumerate(self[0].select(context)):
            result = self[1].evaluate(context)
            if isinstance(result, list) and not result:
                raise self.wrong_sequence_type()
            elif position and (occurs is None or occurs == '?'):
                raise self.wrong_sequence_type("more than one item in sequence")
            castable_expr.append(item)
        else:
            if position is None and occurs not in ('*', '?'):
                raise self.wrong_sequence_type("the sequence cannot be empty")
    else:
        try:
            qname = get_expanded_name(self[1].source, self.parser.namespaces)
        except KeyError as err:
            raise self.error('XPST0081', 'prefix {} not found'.format(str(err)))

        if not qname.startswith('{') and not QName.is_valid(qname):
            raise self.error('XPST0003')

        for position, item in enumerate(self[0].select(context)):
            try:
                if not self.parser.is_instance(item, qname):
                    msg = f"item {item!r} is not of type {self[1].source!r}"
                    raise self.error('XPDY0050', msg)
            except KeyError:
                msg = "atomic type %r not found in in-scope schema types"
                raise self.error('XPST0051', msg % self[1].source) from None
            else:
                if position and (occurs is None or occurs == '?'):
                    raise self.wrong_sequence_type("more than one item in sequence")
                castable_expr.append(item)
        else:
            if position is None and occurs not in ('*', '?'):
                raise self.wrong_sequence_type("the sequence cannot be empty")

    return castable_expr


###
# Simple type based
@method('castable', bp=62)
@method('cast', bp=63)
def led_cast_expressions(self, left):
    self.parser.advance('as')
    self.parser.expected_name('(name)', ':')
    self[:] = left, self.parser.expression(rbp=self.rbp)
    if self.parser.next_token.symbol == '?':
        self[2:] = self.parser.symbol_table['?'](self.parser),  # Add nullary token
        self.parser.advance()
    return self


@method('castable')
@method('cast')
def evaluate_cast_expressions(self, context=None):
    try:
        atomic_type = get_expanded_name(self[1].source, namespaces=self.parser.namespaces)
    except KeyError as err:
        raise self.error('XPST0081', 'prefix {} not found'.format(str(err)))

    if atomic_type in (XSD_NOTATION, XSD_ANY_ATOMIC_TYPE):
        raise self.error('XPST0080')

    namespace = get_namespace(atomic_type)
    if namespace != XSD_NAMESPACE and \
            (self.parser.schema is None or self.parser.schema.get_type(atomic_type) is None):
        msg = "atomic type %r not found in the in-scope schema types"
        raise self.unknown_atomic_type(msg % atomic_type)

    result = [res for res in self[0].select(context)]
    if len(result) > 1:
        if self.symbol != 'cast':
            return False
        raise self.wrong_context_type("more than one value in expression")
    elif not result:
        if len(self) == 3:
            return [] if self.symbol == 'cast' else True
        elif self.symbol != 'cast':
            return False
        else:
            raise self.wrong_context_type("an atomic value is required")

    arg = self.data_value(result[0])
    try:
        if namespace != XSD_NAMESPACE:
            value = self.parser.schema.cast_as(self.string_value(arg), atomic_type)
        else:
            local_name = atomic_type.split('}')[1]
            token_class = self.parser.symbol_table.get(local_name)
            if token_class is None or token_class.label != 'constructor function':
                msg = "atomic type %r not found in the in-scope schema types"
                raise self.unknown_atomic_type(msg % self[1].source)
            elif local_name == 'QName':
                if isinstance(arg, QName):
                    pass
                elif self.parser.version < '3.0' and self[0].symbol != '(string)':
                    raise self.error('XPTY0004', "Non literal string to QName cast")

            token = token_class(self.parser)
            value = token.cast(arg)

    except ElementPathError:
        if self.symbol != 'cast':
            return False
        raise
    except (TypeError, ValueError) as err:
        if self.symbol != 'cast':
            return False
        elif isinstance(arg, (UntypedAtomic, str)):
            raise self.error('FORG0001', err) from None
        raise self.error('XPTY0004', err) from None
    else:
        return value if self.symbol == 'cast' else True


###
# Comma operator - concatenate items or sequences
@method(infix(',', bp=5))
def evaluate_comma_operator(self, context=None):
    results = []
    for op in self:
        result = op.evaluate(context)
        if isinstance(result, list):
            results.extend(result)
        elif result is not None:
            results.append(result)
    return results


@method(',')
def select_comma_operator(self, context=None):
    for op in self:
        yield from op.select(context=copy(context))


###
# Parenthesized expression: XPath 2.0 admits the empty case ().
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
    return self[0].evaluate(context) if self else []


@method('(')
def select_parenthesized_expression(self, context=None):
    return self[0].select(context) if self else iter(())


###
# Value comparison operators (eq, ne, lt, le, gt, and ge)
#
# Ref: https://www.w3.org/TR/xpath20/#id-value-comparisons
#
@method('eq', bp=30)
@method('ne', bp=30)
@method('lt', bp=30)
@method('gt', bp=30)
@method('le', bp=30)
@method('ge', bp=30)
def led_value_comparison_operators(self, left):
    if left.symbol in COMPARISON_OPERATORS:
        raise self.wrong_syntax()
    self[:] = left, self.parser.expression(rbp=30)
    return self


@method('eq')
@method('ne')
@method('lt')
@method('gt')
@method('le')
@method('ge')
def evaluate_value_comparison_operators(self, context=None):
    operands = [self[0].get_atomized_operand(context=copy(context)),
                self[1].get_atomized_operand(context=copy(context))]

    if any(x is None for x in operands):
        return None
    elif any(isinstance(x, XPathFunction) for x in operands):
        raise self.error('FOTY0013', "cannot compare a function item")
    elif all(isinstance(x, DoubleProxy10) for x in operands):
        # Special case of two <class 'float'> values: use custom operators
        if self.symbol == 'eq':
            return numeric_equal(*operands)
        elif self.symbol == 'ne':
            return numeric_not_equal(*operands)
        elif numeric_equal(*operands):
            return self.symbol in ('le', 'ge')

    cls0, cls1 = type(operands[0]), type(operands[1])
    if cls0 is cls1 and cls0 is not Duration:
        pass
    elif all(isinstance(x, float) for x in operands):
        pass
    elif any(isinstance(x, bool) for x in operands):
        msg = "cannot apply {} between {!r} and {!r}".format(self, *operands)
        raise self.error('XPTY0004', msg)
    elif all(isinstance(x, (int, Decimal)) for x in operands):
        pass
    elif all(isinstance(x, (str, UntypedAtomic, AnyURI)) for x in operands):
        pass
    elif all(isinstance(x, (float, Decimal, int)) for x in operands):
        if isinstance(operands[0], float):
            operands[1] = float(operands[1])
        else:
            operands[0] = float(operands[0])
    elif all(isinstance(x, Duration) for x in operands) and self.symbol in ('eq', 'ne'):
        pass
    elif (issubclass(cls0, cls1) or issubclass(cls1, cls0)) and not issubclass(cls0, Duration):
        pass
    else:
        msg = "cannot apply {} between {!r} and {!r}".format(self, *operands)
        raise self.error('XPTY0004', msg)

    try:
        return getattr(operator, self.symbol)(*operands)
    except TypeError as err:
        raise self.error('XPTY0004', err) from None


###
# Node comparison
@method('is', bp=30)
def led_node_comparison(self, left):
    if left.symbol == 'is':
        raise self.wrong_syntax()
    self[:] = left, self.parser.expression(rbp=30)
    return self


@method('is')
@method(infix('<<', bp=30))
@method(infix('>>', bp=30))
def evaluate_node_comparison(self, context=None):
    symbol = self.symbol

    left = [x for x in self[0].select(context)]
    if not left:
        return
    elif len(left) > 1 or not is_xpath_node(left[0]):
        raise self[0].error('XPTY0004', "left operand of %r must be a single node" % symbol)

    right = [x for x in self[1].select(context)]
    if not right:
        return
    elif len(right) > 1 or not is_xpath_node(right[0]):
        raise self[0].error('XPTY0004', "right operand of %r must be a single node" % symbol)

    # For identity comparison use '==' operator instead of 'is'
    # because elem1 == elem2 if and only if elem1 is elem2.
    # For example two AttributeNode objects (a1, a2) represent
    # the same node if they have the same name, the same value
    # and the same parent.
    if symbol == 'is':
        return left[0] == right[0]
    else:
        if left[0] == right[0]:
            return False

        documents = [context.root]
        documents.extend(v for v in context.variables.values() if is_document_node(v))

        for root in documents:
            for item in root.iter():  # pragma: no cover
                if left[0] == item:
                    return True if symbol == '<<' else False
                elif right[0] == item:
                    return False if symbol == '<<' else True
        else:
            raise self.error('FOCA0002', "operands are not nodes of the XML tree!")


###
# Range expression
@method('to', bp=35)
def led_range_expression(self, left):
    if left.symbol == 'to':
        raise self.wrong_syntax()
    self[:] = left, self.parser.expression(rbp=35)
    return self


@method('to')
def evaluate_range_expression(self, context=None):
    start, stop = self.get_operands(context, cls=Integer)
    try:
        return [x for x in range(start, stop + 1)]
    except TypeError:
        return []


@method('to')
def select_range_expression(self, context=None):
    yield from self.evaluate(context)


###
# Numerical operators
@method(infix('idiv', bp=45))
def evaluate_idiv_operator(self, context=None):
    op1, op2 = self.get_operands(context)
    if op1 is None or op2 is None:
        raise self.error('XPST0005')

    try:
        if math.isinf(op1):
            raise self.error('FOAR0001' if op2 == 0 else 'FOAR0002')
        elif math.isnan(op1) or math.isnan(op2):
            raise self.error('FOAR0002')
    except TypeError as err:
        raise self.error('XPTY0004', err) from None

    try:
        result = op1 // op2
    except (ZeroDivisionError, DivisionByZero):
        raise self.error('FOAR0001') from None
    else:
        if result >= 0 or isinstance(op1, Decimal) or \
                isinstance(op2, Decimal) or abs(op1) == abs(op2):
            return int(result)
        else:
            return int(result) + 1


# Resolve the intrinsic ambiguity of some infix operators
@method('union')
@method('intersect')
@method('except')
@method('eq')
@method('ne')
@method('lt')
@method('gt')
@method('le')
@method('ge')
@method('is')
@method('to')
@method('idiv')
@method('instance')
@method('treat')
@method('castable')
@method('cast')
def nud_disambiguation_of_infix_operators(self):
    token = self.parser.symbol_table['(name)'](self.parser, self.symbol)
    return token.nud()


###
# Kind tests (sequence types that can appear also in XPath expressions)
@method(function('document-node', nargs=(0, 1), label='kind test'))
def select_document_node_kind_test(self, context=None):
    if context is None:
        raise self.missing_context()
    elif not self:
        if is_document_node(context.item):
            yield context.item
        elif is_document_node(context.root) and context.item is None:
            for item in context.iter_children_or_self():
                if item is None:
                    yield context.root
    else:
        elements = [e for e in self[0].select(copy(context)) if is_element_node(e)]
        if is_document_node(context.root) and context.item is None:
            if len(elements) == 1:
                yield context.root


@method('document-node')
def nud_document_node_kind_test(self):
    self.parser.advance('(')
    if self.parser.next_token.symbol in ('element', 'schema-element'):
        self[0:] = self.parser.expression(5),
        if self.parser.next_token.symbol == ',':
            raise self.wrong_nargs('Too many arguments: expected at most 1 argument')
    elif self.parser.next_token.symbol != ')':
        raise self.error('XPST0003', 'element or schema-element kind test expected')
    self.parser.advance(')')
    self.value = None
    return self


@method(function('element', nargs=(0, 2), label='kind test'))
def select_element_kind_test(self, context=None):
    if context is None:
        raise self.missing_context()
    elif not self:
        for item in context.iter_children_or_self():
            if is_element_node(item):
                yield item
    else:
        for item in self[0].select(context):
            if len(self) == 1:
                yield item
            elif isinstance(item, TypedElement):
                try:
                    type_annotation = get_expanded_name(self[1].source, self.parser.namespaces)
                except KeyError:
                    type_annotation = self[1].source

                if type_annotation == item.xsd_type.name:
                    yield item
                elif item.elem.get(XSI_NIL) and type_annotation[-1] in ('*', '?'):
                    yield item


@method('element')
def nud_element_kind_test(self):
    self.parser.advance('(')
    if self.parser.next_token.symbol != ')':
        self.parser.expected_name('(name)', ':', '*', message='a QName or a wildcard expected')
        self[0:] = self.parser.expression(5),
        if self.parser.next_token.symbol == ',':
            self.parser.advance(',')
            self.parser.expected_name('(name)', ':', message='a QName expected')
            self[1:] = self.parser.expression(5),
            if self.parser.next_token.symbol in ('*', '+', '?'):
                self[1].occurrence = self.parser.next_token.symbol
                self.parser.advance()

    self.parser.advance(')')
    self.value = None
    return self


@method(function('schema-attribute', nargs=1, label='kind test'))
def select_schema_attribute_kind_test(self, context=None):
    if context is None:
        raise self.missing_context()

    attribute_name = self[0].source
    for _ in context.iter_children_or_self():
        qname = get_expanded_name(attribute_name, self.parser.namespaces)
        if self.parser.schema.get_attribute(qname) is None:
            raise self.missing_name("attribute %r not found in schema" % attribute_name)

        if match_attribute_node(context.item, qname):
            yield context.item
            return

    if not isinstance(context, XPathSchemaContext):
        raise self.error('XPST0008', 'schema attribute %r not found' % attribute_name)


@method(function('schema-element', nargs=1, label='kind test'))
def select_schema_element_kind_test(self, context=None):
    if context is None:
        raise self.missing_context()

    element_name = self[0].source
    for _ in context.iter_children_or_self():
        qname = get_expanded_name(element_name, self.parser.namespaces)
        if self.parser.schema.get_element(qname) is None \
                and self.parser.schema.get_substitution_group(qname) is None:
            raise self.missing_name("element %r not found in schema" % element_name)

        if is_element_node(context.item) and context.item.tag == qname:
            yield context.item
            return

    if not isinstance(context, XPathSchemaContext):
        raise self.error('XPST0008', 'schema element %r not found' % element_name)


@method('schema-attribute')
@method('schema-element')
def nud_schema_node_kind_test(self):
    self.parser.advance('(')
    self.parser.expected_name('(name)', ':', message='a QName expected')
    self[0:] = self.parser.expression(5),
    self.parser.advance(')')
    self.value = None
    return self


###
# Multi role-tokens definition: in XPath 2.0 the 'attribute' keyword is used both for
# attribute:: axis and attribute() node type function.
#
# First the XPath1 token class has to be removed from the XPath2 symbol table. Then the
# symbol has to be registered usually with the same binding power (bp --> lbp, rbp), a
# multi-value label (using a tuple of values) and a custom pattern. Finally a custom nud
# or led method is required.
XPath2Parser.unregister('attribute')
XPath2Parser.register(
    'attribute', lbp=90, rbp=90, label=('kind test', 'axis'),
    pattern=r'\battribute(?=\s*\:\:|\s*\(\:.*\:\)\s*\:\:|\s*\(|\s*\(\:.*\:\)\()'
)


@method('attribute')
def nud_attribute_kind_test_or_axis(self):
    if self.parser.next_token.symbol == '::':
        self.label = 'axis'
        self.parser.advance('::')
        self.parser.expected_name(
            '(name)', '*', 'text', 'node', 'document-node', 'comment', 'processing-instruction',
            'attribute', 'schema-attribute', 'element', 'schema-element', 'namespace-node'
        )
        self[:] = self.parser.expression(rbp=90),
    else:
        self.label = 'kind test'
        self.parser.advance('(')
        if self.parser.next_token.symbol != ')':
            self.parser.next_token.expected('(name)', '*', ':')
            self[:] = self.parser.expression(5),

            if self.parser.next_token.symbol == ',':
                self.parser.advance(',')
                self.parser.next_token.expected('(name)', ':')
                self[1:] = self.parser.expression(5),

        self.parser.advance(')')

        if self.namespace:
            msg = f"{self.value!r} is not allowed as function name"
            raise self.error('XPST0003', msg)

    return self


@method('attribute')
def select_attribute_kind_test_or_axis(self, context=None):
    if context is None:
        raise self.missing_context()
    elif self.label == 'axis':
        for _ in context.iter_attributes():
            yield from self[0].select(context)
    elif not self:
        for attribute in context.iter_attributes():
            yield attribute.value
    else:
        name = self[0].value
        if self.parser.schema is not None and len(self) == 2:
            type_name = get_expanded_name(self[1].value, namespaces=self.parser.namespaces)
        else:
            type_name = None

        for attribute in context.iter_attributes():
            if match_attribute_node(attribute, name):
                if isinstance(context, XPathSchemaContext):
                    self.add_xsd_type(attribute)
                elif not type_name:
                    yield attribute.value
                else:
                    xsd_type = self.get_xsd_type(attribute)
                    if xsd_type is not None and xsd_type.name == type_name:
                        yield attribute.value


# XPath 2.0 definitions continue into module xpath2_functions
