#
# Copyright (c), 2018-2021, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""
XPath 1.0 implementation - part 2 (operators and expressions)
"""
import math
import decimal
import operator
from copy import copy
from typing import Any, cast, List, NoReturn, Optional, Set, Type, Union

from elementpath._typing import Iterator, Sequence
from elementpath.exceptions import ElementPathKeyError, ElementPathTypeError
from elementpath.helpers import collapse_white_spaces, node_position
from elementpath.datatypes import AbstractDateTime, AnyURI, Duration, DayTimeDuration, \
    YearMonthDuration, NumericProxy, ArithmeticProxy, NumericType, ArithmeticType
from elementpath.xpath_context import ContextType, ItemType, XPathSchemaContext
from elementpath.namespaces import XMLNS_NAMESPACE, XSD_NAMESPACE
from elementpath.xpath_nodes import ParentNodeType, XPathNode, \
    ElementNode, AttributeNode, DocumentNode
from elementpath.xpath_tokens import XPathParserType, XPathToken, XPathTokenType

from .xpath1_parser import XPath1Parser

__all__ = ['XPath1Parser']

OPERATORS_MAP = {
    '=': operator.eq,
    '!=': operator.ne,
    '>': operator.gt,
    '>=': operator.ge,
    '<': operator.lt,
    '<=': operator.le,
}

register = XPath1Parser.register
nullary = XPath1Parser.nullary
infix = XPath1Parser.infix
method = XPath1Parser.method


@method(register('(name)', bp=10, label='literal'))
def nud_name_literal(self: XPathToken) -> XPathToken:
    if self.parser.next_token.symbol == '::':
        msg = "axis '%s::' not found" % self.value
        if self.parser.compatibility_mode:
            raise self.error('XPST0010', msg)
        raise self.error('XPST0003', msg)
    elif self.parser.next_token.symbol == '(':
        if self.parser.version >= '2.0':
            pass  # XP30+ has led() for '(' operator that can check this
        elif self.namespace == XSD_NAMESPACE:
            raise self.error('XPST0017', 'unknown constructor function {!r}'.format(self.value))
        elif self.namespace or self.value not in self.parser.RESERVED_FUNCTION_NAMES:
            raise self.error('XPST0017', 'unknown function {!r}'.format(self.value))
        else:
            msg = f"{self.value!r} is not allowed as function name"
            raise self.error('XPST0003', msg)

    return self


@method('(name)')
def evaluate_name_literal(self: XPathToken, context: ContextType = None) \
        -> List[ItemType]:
    return [x for x in self.select(context)]


@method('(name)')
def select_name_literal(self: XPathToken, context: ContextType = None) \
        -> Iterator[ItemType]:
    if context is None:
        raise self.missing_context()

    if isinstance(self.value, str):
        yield from context.iter_matching_nodes(self.value, self.parser.default_namespace)


###
# Prefixed reference (name or function)

class _PrefixedReferenceToken(XPathToken):

    symbol = lookup_name = ':'
    lbp = 95
    rbp = 95
    value: str

    def __init__(self, parser: XPathParserType, value: Optional[Any] = None) -> None:
        super().__init__(parser, value)

        # Change bind powers if it cannot be a namespace related token
        if self.is_spaced():
            self.lbp = self.rbp = 0
        elif self.parser.token.symbol not in ('*', '(name)', 'array'):
            self.lbp = self.rbp = 0

    def __str__(self) -> str:
        if len(self) < 2:
            return 'unparsed prefixed reference'
        elif self[1].label.endswith('function'):
            return f"{self.value!r} {self[1].label}"
        elif '*' in self.value:
            return f"{self.value!r} prefixed wildcard"
        else:
            return f"{self.value!r} prefixed name"

    @property
    def source(self: XPathToken) -> str:
        if self.occurrence:
            return ':'.join(tk.source for tk in self) + self.occurrence
        else:
            return ':'.join(tk.source for tk in self)

    @property
    def name(self) -> str:
        prefix = self[0].value
        assert isinstance(prefix, str)
        if prefix == '*':
            return '*:%s' % self[1].value
        else:
            return f'{{{self.get_namespace(prefix)}}}{self[1].value}'

    def led(self: XPathToken, left: XPathToken) -> XPathToken:
        version = self.parser.version
        if self.is_spaced():
            if version <= '3.0':
                raise self.wrong_syntax("a QName cannot contains spaces before or after ':'")
            return left

        if version == '1.0':
            left.expected('(name)')
        elif version <= '3.0':
            left.expected('(name)', '*')
        elif left.symbol not in ('(name)', '*'):
            return left

        if not self.parser.next_token.label.endswith('function'):
            self.parser.expected_next('(name)', '*')

        if left.symbol == '(name)':
            try:
                namespace = self.get_namespace(cast(str, left.value))
            except ElementPathKeyError:
                self.parser.advance()  # Assure there isn't a following incomplete comment
                self[:] = left, self.parser.token
                msg = "prefix {!r} is not declared".format(left.value)
                raise self.error('XPST0081', msg) from None
            else:
                self.parser.next_token.bind_namespace(namespace)
        elif self.parser.next_token.symbol != '(name)':
            raise self.wrong_syntax()

        self[:] = left, self.parser.expression(95)

        if self[1].label.endswith('function'):
            self.value = f'{self[0].value}:{self[1].symbol}'
        else:
            self.value = f'{self[0].value}:{self[1].value}'
        return self

    def evaluate(self: XPathToken, context: ContextType = None) \
            -> Union[ItemType, List[ItemType]]:
        if self[1].label.endswith('function'):
            return self[1].evaluate(context)
        return [x for x in self.select(context)]

    def select(self, context: ContextType = None) -> Iterator[ItemType]:
        if self[1].label.endswith('function'):
            value = self[1].evaluate(context)
            if isinstance(value, list):
                yield from value
            elif value is not None:
                yield value
            return

        if context is None:
            raise self.missing_context()

        yield from context.iter_matching_nodes(self.name)


XPath1Parser.symbol_table[':'] = _PrefixedReferenceToken


###
# Namespace URI as in ElementPath
@method('{', bp=95)
def nud_namespace_uri(self: XPathToken) -> XPathToken:
    if self.parser.strict and self.symbol == '{':
        raise self.wrong_syntax("not allowed symbol if parser has strict=True")

    self.parser.next_token.unexpected('{')
    if self.parser.next_token.symbol == '}':
        namespace = ''
    else:
        value = self.parser.next_token.value
        assert isinstance(value, str)
        namespace = value + self.parser.advance_until('}')
        namespace = collapse_white_spaces(namespace)

    try:
        AnyURI(namespace)
    except ValueError as err:
        msg = f"invalid URI in an EQName: {str(err)}"
        raise self.error('XQST0046', msg) from None

    if namespace == XMLNS_NAMESPACE:
        msg = f"cannot use the URI {XMLNS_NAMESPACE!r}!r in an EQName"
        raise self.error('XQST0070', msg)

    self.parser.advance()
    if not self.parser.next_token.label.endswith('function'):
        self.parser.expected_next('(name)', '*')
    self.parser.next_token.bind_namespace(namespace)

    cls: Type[XPathToken] = self.parser.symbol_table['(string)']
    self[:] = cls(self.parser, namespace), self.parser.expression(90)

    if not self[0].value:
        self.value = self[1].value
    else:
        self.value = f'{{{self[0].value}}}{self[1].value}'
    return self


@method('{')
def evaluate_namespace_uri(self: XPathToken, context: ContextType = None) \
        -> Union[ItemType, List[ItemType]]:
    if self[1].label.endswith('function'):
        return self[1].evaluate(context)
    return [x for x in self.select(context)]


@method('{')
def select_namespace_uri(self: XPathToken, context: ContextType = None) \
        -> Iterator[Union[ItemType, List[ItemType]]]:
    if self[1].label.endswith('function'):
        yield self[1].evaluate(context)
        return
    elif context is None:
        raise self.missing_context()

    if isinstance(self.value, str):
        yield from context.iter_matching_nodes(self.value)


###
# Variables
@method('$', bp=90)
def nud_variable_reference(self: XPathToken) -> XPathToken:
    self.parser.expected_next('(name)')
    self[:] = self.parser.expression(rbp=90),
    if not isinstance(self[0].value, str) or ':' in self[0].value:
        raise self[0].wrong_syntax("variable reference requires a simple reference name")
    return self


@method('$')
def evaluate_variable_reference(self: XPathToken, context: ContextType = None) \
        -> Union[ItemType, List[ItemType]]:
    if context is None:
        raise self.missing_context()

    try:
        value = context.variables[cast(str, self[0].value)]
    except KeyError as err:
        raise self.error('XPST0008', 'unknown variable %r' % str(err)) from None
    else:
        return value if value is not None else []


###
# Nullary operators (use only the context)
@method(nullary('*'))
def select_wildcard(self: XPathToken, context: ContextType = None) -> Iterator[ItemType]:
    if self:
        # Product operator
        item = self.evaluate(context)
        if not isinstance(item, list):
            if context is not None:
                context.item = item
            yield item
        elif context is not None:
            for context.item in item:
                yield context.item
        else:
            yield from item
        return
    elif context is None:
        raise self.missing_context()

    # Wildcard literal
    if self.parser.schema is None:
        for item in context.iter_children_or_self():
            if item is None:
                pass  # '*' wildcard doesn't match document nodes
            elif context.axis == 'attribute':
                if isinstance(item, AttributeNode):
                    yield item
            elif isinstance(item, ElementNode):
                yield item
    else:
        # XSD typed selection
        for item in context.iter_children_or_self():
            if context.is_principal_node_kind():
                if isinstance(item, (ElementNode, AttributeNode)):
                    yield item


@method(nullary('.'))
def select_self_shortcut(self: XPathToken, context: ContextType = None) -> Iterator[ItemType]:
    if context is None:
        raise self.missing_context()
    yield from context.iter_self()


@method(nullary('..'))
def select_parent_shortcut(self: XPathToken, context: ContextType = None) \
        -> Iterator[ParentNodeType]:
    if context is None:
        raise self.missing_context()
    yield from context.iter_parent()


###
# Logical Operators
@method(infix('or', bp=20))
def evaluate_or_operator(self: XPathToken, context: ContextType = None) -> bool:
    if isinstance(context, XPathSchemaContext):
        op1 = self.boolean_value(self[0].select(copy(context)))
        op2 = self.boolean_value(self[1].select(copy(context)))
        return op1 or op2

    return self.boolean_value(self[0].select(copy(context))) or \
        self.boolean_value(self[1].select(copy(context)))


@method(infix('and', bp=25))
def evaluate_and_operator(self: XPathToken, context: ContextType = None) -> bool:
    if isinstance(context, XPathSchemaContext):
        op1 = self.boolean_value(self[0].select(copy(context)))
        op2 = self.boolean_value(self[1].select(copy(context)))
        return op1 and op2

    return self.boolean_value(self[0].select(copy(context))) and \
        self.boolean_value(self[1].select(copy(context)))


###
# Comparison operators
@method('=', bp=30)
@method('!=', bp=30)
@method('<', bp=30)
@method('>', bp=30)
@method('<=', bp=30)
@method('>=', bp=30)
def led_comparison_operators(self: XPathToken, left: XPathToken) -> XPathToken:
    if left.symbol in OPERATORS_MAP:
        raise self.wrong_syntax()
    self[:] = left, self.parser.expression(rbp=30)
    return self


@method('=')
@method('!=')
@method('<')
@method('>')
@method('<=')
@method('>=')
def evaluate_comparison_operators(self: XPathToken, context: ContextType = None) -> bool:
    op = OPERATORS_MAP[self.symbol]
    try:
        return any(op(x1, x2) for x1, x2 in self.iter_comparison_data(context))
    except (TypeError, ValueError) as err:
        if isinstance(context, XPathSchemaContext):
            return False
        elif isinstance(err, ElementPathTypeError):
            raise
        elif isinstance(err, TypeError):
            raise self.error('XPTY0004', err) from None
        else:
            raise self.error('FORG0001', err) from None


###
# Numerical operators
@method(infix('+', bp=40))
def evaluate_plus_operator(self: XPathToken, context: ContextType = None) \
        -> Union[List[NoReturn], ArithmeticType]:
    if len(self) == 1:
        arg: NumericType = self.get_argument(context, cls=NumericProxy)
        return [] if arg is None else +arg
    else:
        op1: Optional[ArithmeticType]
        op2: ArithmeticType
        op1, op2 = self.get_operands(context, cls=ArithmeticProxy)
        if op1 is None:
            return []

        try:
            return op1 + op2  # type:ignore[operator]
        except (TypeError, OverflowError) as err:
            if isinstance(context, XPathSchemaContext):
                return []
            elif isinstance(err, TypeError):
                raise self.error('XPTY0004', err) from None
            elif isinstance(op1, AbstractDateTime):
                raise self.error('FODT0001', err) from None
            elif isinstance(op1, Duration):
                raise self.error('FODT0002', err) from None
            else:
                raise self.error('FOAR0002', err) from None


@method(infix('-', bp=40))
def evaluate_minus_operator(self: XPathToken, context: ContextType = None) \
        -> Union[List[NoReturn], ArithmeticType]:
    if len(self) == 1:
        arg: NumericType = self.get_argument(context, cls=NumericProxy)
        return [] if arg is None else -arg
    else:
        op1: Optional[ArithmeticType]
        op2: ArithmeticType
        op1, op2 = self.get_operands(context, cls=ArithmeticProxy)
        if op1 is None:
            return []

        try:
            return op1 - op2  # type:ignore[operator]
        except (TypeError, OverflowError) as err:
            if isinstance(context, XPathSchemaContext):
                return []
            elif isinstance(err, TypeError):
                raise self.error('XPTY0004', err) from None
            elif isinstance(op1, AbstractDateTime):
                raise self.error('FODT0001', err) from None
            elif isinstance(op1, Duration):
                raise self.error('FODT0002', err) from None
            else:
                raise self.error('FOAR0002', err) from None


@method('+')
@method('-')
def nud_plus_minus_operators(self: XPathToken) -> XPathToken:
    self[:] = self.parser.expression(rbp=70),
    return self


@method(infix('*', bp=45))
def evaluate_multiply_operator(self: XPathToken, context: ContextType = None) \
        -> Union[ArithmeticType, List[ItemType]]:
    op1: Optional[ArithmeticType]
    op2: ArithmeticType
    if self:
        op1, op2 = self.get_operands(context, cls=ArithmeticProxy)
        if op1 is None:
            return []
        try:
            if isinstance(op2, (YearMonthDuration, DayTimeDuration)):
                return op2 * op1
            return op1 * op2  # type:ignore[operator]
        except TypeError as err:
            if isinstance(context, XPathSchemaContext):
                return []

            if isinstance(op1, (float, decimal.Decimal)):
                if math.isnan(op1):
                    raise self.error('FOCA0005') from None
                elif math.isinf(op1):
                    raise self.error('FODT0002') from None

            if isinstance(op2, (float, decimal.Decimal)):
                if math.isnan(op2):
                    raise self.error('FOCA0005') from None
                elif math.isinf(op2):
                    raise self.error('FODT0002') from None

            raise self.error('XPTY0004', err) from None
        except ValueError as err:
            if isinstance(context, XPathSchemaContext):
                return []
            raise self.error('FOCA0005', err) from None
        except OverflowError as err:
            if isinstance(context, XPathSchemaContext):
                return []
            elif isinstance(op1, AbstractDateTime):
                raise self.error('FODT0001', err) from None
            elif isinstance(op1, Duration):
                raise self.error('FODT0002', err) from None
            else:
                raise self.error('FOAR0002', err) from None
    else:
        # This is not a multiplication operator but a wildcard select statement
        return [x for x in self.select(context)]


@method(infix('div', bp=45))
def evaluate_div_operator(self: XPathToken, context: ContextType = None) \
        -> Union[int, float, decimal.Decimal, List[Any]]:
    dividend: Optional[ArithmeticType]
    divisor: ArithmeticType
    dividend, divisor = self.get_operands(context, cls=ArithmeticProxy)
    if dividend is None:
        return []
    elif divisor != 0:
        try:
            if isinstance(dividend, int) and isinstance(divisor, int):
                return decimal.Decimal(dividend) / decimal.Decimal(divisor)
            return dividend / divisor  # type:ignore[operator]
        except TypeError as err:
            raise self.error('XPTY0004', err) from None
        except ValueError as err:
            raise self.error('FOCA0005', err) from None
        except OverflowError as err:
            raise self.error('FOAR0002', err) from None
        except (ZeroDivisionError, decimal.DivisionByZero):
            raise self.error('FOAR0001') from None

    elif isinstance(dividend, AbstractDateTime):
        raise self.error('FODT0001')
    elif isinstance(dividend, Duration):
        raise self.error('FODT0002')
    elif not self.parser.compatibility_mode and \
            isinstance(dividend, (int, decimal.Decimal)) and \
            isinstance(divisor, (int, decimal.Decimal)):
        raise self.error('FOAR0001')
    elif dividend == 0:
        return math.nan
    elif dividend > 0:
        return float('-inf') if str(divisor).startswith('-') else float('inf')
    else:
        return float('inf') if str(divisor).startswith('-') else float('-inf')


@method(infix('mod', bp=45))
def evaluate_mod_operator(self: XPathToken, context: ContextType = None) \
        -> Union[List[NoReturn], ArithmeticType]:
    op1: Optional[NumericType]
    op2: Optional[NumericType]
    op1, op2 = self.get_operands(context, cls=NumericProxy)
    if op1 is None:
        return []
    elif op2 is None:
        raise self.error('XPTY0004', '2nd operand is an empty sequence')
    elif op2 == 0 and isinstance(op2, float):
        return math.nan
    elif math.isinf(op2) and not math.isinf(op1) and op1 != 0:
        return op1 if self.parser.version != '1.0' else math.nan

    try:
        if isinstance(op1, int) and isinstance(op2, int):
            return op1 % op2 if op1 * op2 >= 0 else -(abs(op1) % op2)
        return op1 % op2  # type: ignore[operator]
    except TypeError as err:
        raise self.error('FORG0006', err) from None
    except (ZeroDivisionError, decimal.InvalidOperation):
        raise self.error('FOAR0001') from None


# Resolve the intrinsic ambiguity of some infix operators
@method('or')
@method('and')
@method('div')
@method('mod')
def nud_disambiguation_of_infix_operators(self: XPathToken) -> XPathTokenType:
    return self.as_name()


###
# Union expressions
@method('|', bp=50)
def led_union_operator(self: XPathToken, left: XPathToken) -> XPathToken:
    if left.symbol in ('|', 'union'):
        left.concatenated = True
    self[:] = left, self.parser.expression(rbp=50)
    return self


@method('|')
def select_union_operator(self: XPathToken, context: ContextType = None) \
        -> Iterator[XPathNode]:
    if context is None:
        raise self.missing_context()

    results = {item for k in range(2) for item in self[k].select(copy(context))}
    if any(not isinstance(x, XPathNode) for x in results):
        raise self.error('XPTY0004', 'only XPath nodes are allowed')
    elif self.concatenated:
        yield from cast(Set[XPathNode], results)
    else:
        yield from cast(List[XPathNode], sorted(results, key=node_position))


###
# Path expressions
@method('//', bp=75)
def nud_descendant_path(self: XPathToken) -> XPathToken:
    if self.parser.next_token.label not in self.parser.PATH_STEP_LABELS:
        self.parser.expected_next(*self.parser.PATH_STEP_SYMBOLS)

    self[:] = self.parser.expression(75),
    return self


@method('/', bp=75)
def nud_child_path(self: XPathToken) -> XPathToken:
    if self.parser.next_token.label not in self.parser.PATH_STEP_LABELS:
        try:
            self.parser.expected_next(*self.parser.PATH_STEP_SYMBOLS)
        except SyntaxError:
            return self

    self[:] = self.parser.expression(75),
    return self


@method('//')
@method('/')
def led_child_or_descendant_path(self: XPathToken, left: XPathToken) -> XPathToken:
    if left.symbol in ('/', '//', ':', '[', '$'):
        pass
    elif left.label not in self.parser.PATH_STEP_LABELS and \
            left.symbol not in self.parser.PATH_STEP_SYMBOLS:
        raise self.wrong_syntax()

    if self.parser.next_token.label not in self.parser.PATH_STEP_LABELS:
        self.parser.expected_next(*self.parser.PATH_STEP_SYMBOLS)

    self[:] = left, self.parser.expression(75)
    return self


@method('/')
def select_child_path(self: XPathToken, context: ContextType = None) \
        -> Iterator[ItemType]:
    """
    Child path expression. Selects child:: axis as default (when bind to '*' or '(name)').
    """
    if context is None:
        raise self.missing_context()
    elif not self:
        if isinstance(context.root, DocumentNode):
            yield context.root
    elif len(self) == 1:
        if isinstance(context.document, DocumentNode):
            context.item = context.document
        elif context.root is None or isinstance(context.root.parent, ElementNode):
            return  # No root or a rooted subtree -> document root produce []
        else:
            context.item = context.root  # A fragment or a schema node
        yield from self[0].select(context)
    else:
        items: Set[ItemType] = set()
        for _ in context.inner_focus_select(self[0]):
            if not isinstance(context.item, XPathNode):
                msg = f"Intermediate step contains an atomic value {context.item!r}"
                raise self.error('XPTY0019', msg)

            for result in self[1].select(context):
                if not isinstance(result, XPathNode):
                    yield result
                elif result in items:
                    pass
                elif isinstance(result, ElementNode):
                    if result.obj not in items:
                        items.add(result)
                        yield result
                else:
                    items.add(result)
                    yield result


@method('//')
def select_descendant_path(self: XPathToken, context: ContextType = None) \
        -> Iterator[ItemType]:
    """Operator '//' is a short equivalent to /descendant-or-self::node()/"""
    if context is None:
        raise self.missing_context()
    elif len(self) == 2:
        items: Set[ItemType] = set()
        for _ in context.inner_focus_select(self[0]):
            if not isinstance(context.item, XPathNode):
                raise self.error('XPTY0019')

            for _ in context.iter_descendants():
                for result in self[1].select(context):
                    if not isinstance(result, XPathNode):
                        yield result
                    elif result in items:
                        pass
                    elif isinstance(result, ElementNode):
                        if result.obj not in items:
                            items.add(result)
                            yield result
                    else:
                        items.add(result)
                        yield result

    else:
        if isinstance(context.document, DocumentNode):
            context.item = context.document
        elif context.root is None or isinstance(context.root.parent, ElementNode):
            return  # No root or a rooted subtree -> document root produce []
        else:
            context.item = context.root  # A fragment or a schema node

        items = set()
        for _ in context.iter_descendants():
            for result in self[0].select(context):
                if not isinstance(result, XPathNode):
                    items.add(result)
                elif result in items:
                    pass
                elif isinstance(result, ElementNode):
                    if result.obj not in items:
                        items.add(result)
                else:
                    items.add(result)

        yield from sorted(items, key=node_position)


###
# Predicate filters
@method('[', bp=80)
def led_predicate(self: XPathToken, left: XPathToken) -> XPathToken:
    self[:] = left, self.parser.expression()
    self.parser.advance(']')
    return self


@method('[')
def select_predicate(self: XPathToken, context: ContextType = None) -> Iterator[ItemType]:
    if context is None:
        raise self.missing_context()

    for _ in context.inner_focus_select(self[0], True):
        if (self[1].label in ('axis', 'kind test') or self[1].symbol == '..') \
                and not isinstance(context.item, XPathNode):
            raise self.error('XPTY0020')

        predicate: Sequence[NumericType]
        predicate = [x for x in cast(Iterator[NumericType], self[1].select(copy(context)))]

        if len(predicate) == 1 and isinstance(predicate[0], NumericProxy):
            if context.position == predicate[0]:
                yield context.item
        elif self.boolean_value(predicate):
            yield context.item


###
# Parenthesized expressions
@method('(', bp=100)
def nud_parenthesized_expr(self: XPathToken) -> XPathToken:
    self[:] = self.parser.expression(),
    self.parser.advance(')')
    return self


@method('(')
def evaluate_parenthesized_expr(self: XPathToken, context: ContextType = None) -> Any:
    return self[0].evaluate(context)


@method('(')
def select_parenthesized_expr(self: XPathToken, context: ContextType = None) -> Iterator[Any]:
    return self[0].select(context)

# XPath 1.0 definitions continue into module xpath1_functions
