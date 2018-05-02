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

from .compat import PY3, unicode_chr, urllib_quote
from .exceptions import ElementPathTypeError
from .namespaces import (
    XPATH_FUNCTIONS_NAMESPACE, XPATH_2_DEFAULT_NAMESPACES, XSD_NOTATION, XSD_ANY_ATOMIC_TYPE,
    qname_to_prefixed, prefixed_to_qname
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
    For default the namespace "http://www.w3.org/2005/xpath-functions" is used.
    :param schema: The schema proxy instance to use for types, attributes and elements lookups. \
    If it's not provided the XPath 2.0 schema's related expressions cannot be used.
    :param build_constructors: If set to `True` the parser instance adds constructor functions
    for the in-schema XSD atomic types.
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

        # Node type functions
        'document-node', 'schema-attribute', 'element', 'schema-element', 'attribute', 'empty-sequence',

        # Accessor functions
        'node-name', 'nilled', 'data', 'base-uri', 'document-uri',

        # Number functions
        'abs', 'round-half-to-even',

        # String functions
        'codepoints-to-string', 'string-to-codepoints', 'compare', 'codepoint-equal',
        'string-join', 'normalize-unicode', 'upper-case', 'lower-case', 'encode-for-uri',
        'iri-to-uri', 'escape-html-uri', 'starts-with', 'ends-with',

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

    def __init__(self, namespaces=None, variables=None, strict=True, default_namespace='',
                 function_namespace=None, schema=None, build_constructors=False, compatibility_mode=False):
        super(XPath2Parser, self).__init__(namespaces, variables, strict)
        if '' not in self.namespaces and default_namespace:
            self.namespaces[''] = default_namespace

        if function_namespace is None:
            self.function_namespace = XPATH_FUNCTIONS_NAMESPACE
        else:
            self.function_namespace = function_namespace

        self.schema = schema
        if schema is not None:
            if not isinstance(schema, AbstractSchemaProxy):
                raise ElementPathTypeError("schema argument must be a subclass of AbstractSchemaProxy!")
            elif build_constructors:
                for xsd_type in schema.iter_atomic_types():
                    if xsd_type.name not in (XSD_ANY_ATOMIC_TYPE, XSD_NOTATION):
                        symbol = qname_to_prefixed(xsd_type.name, self.namespaces)
                        if symbol not in self.symbol_table:
                            self.atomic_type(symbol, xsd_type.name)
                        self.end()

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
                self.next_token.comment = self.comment().strip()
            elif token.comment is None:
                token.comment = self.comment().strip()
            else:
                token.comment = '%s %s' % (token.comment, self.comment().strip())
            super(XPath2Parser, self).advance()
        return self.next_token

    def comment(self):
        """
        Parses and consumes a XPath 2.0 comment. Comments are delimited by symbols
        '(:' and ':)' and can be nested. A comment is attached to the previous token
        or the next token when the previous is None.
        """
        if self.next_token.symbol != '(:':
            return

        comment_level = 1
        comment = []
        while comment_level:
            comment.append(self.raw_advance('(:', ':)'))
            next_token = self.next_token
            if next_token.symbol == ':)':
                comment_level -= 1
                if comment_level:
                    comment.append(str(next_token.value))
            elif next_token.symbol == '(:':
                comment_level += 1
                comment.append(str(next_token.value))
        return ''.join(comment)

    def atomic_type(self, symbol, type_qname):
        """
        Create a XSD type constructor function for parser instance.
        """
        def evaluate_(self_, context=None):
            return self_.parser.schema.cast_as(self_[0].evaluate(context), type_qname)

        token_class = self.function(symbol, nargs=1, bp=90)
        token_class.evaluate = evaluate_

    def next_is_path_step_token(self):
        return self.next_token.label in ('axis', 'function') or self.next_token.symbol in {
            '(integer)', '(string)', '(float)',  '(decimal)', '(name)', '*', '@', '..', '.', '(', '/', '{'
        }

    def next_is_sequence_type_token(self):
        return self.next_token.symbol in {
            '(name)', ':', 'empty-sequence', 'item', 'document-node', 'element', 'attribute',
            'text', 'comment', 'processing-instruction', 'schema-attribute', 'schema-element'
        }


##
# XPath 2.0 definitions
XPath2Parser.begin()

register = XPath2Parser.register
unregister = XPath2Parser.unregister
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
@method(infix('union', bp=50))
def select(self, context=None):
    if context is not None:
        results = {item for k in range(2) for item in self[k].select(context.copy())}
        for item in context.iter():
            if item in results:
                yield item


@method(infix('intersect', bp=55))
def select(self, context=None):
    if context is not None:
        results = set(self[0].select(context.copy())) & set(self[1].select(context.copy()))
        for item in context.iter():
            if item in results:
                yield item


@method(infix('except', bp=55))
def select(self, context=None):
    if context is not None:
        results = set(self[0].select(context.copy())) - set(self[1].select(context.copy()))
        for item in context.iter():
            if item in results:
                yield item


###
# 'if' expression
@method('if', bp=20)
def nud(self):
    self.parser.advance('(')
    self[:] = self.parser.expression(),
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
    if context is None:
        return

    some = self.symbol == 'some'
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
def select(self, context=None):
    if context is not None:
        selectors = tuple(self[k].select(context.copy()) for k in range(1, len(self) - 1, 2))
        for results in product(*selectors):
            for i in range(len(results)):
                context.variables[self[i * 2][0].value] = results[i]
            for result in self[-1].select(context.copy()):
                yield result


###
# Sequence type based
@method('instance', bp=60)
@method('treat', bp=61)
def led(self, left):
    self.parser.advance('of' if self.symbol is 'instance' else 'as')
    if not self.parser.next_is_sequence_type_token():
        self.parser.next_token.wrong_syntax()
    self[:] = left, self.parser.expression(rbp=self.rbp)
    next_symbol = self.parser.next_token.symbol
    if self[1].symbol != 'empty-sequence' and next_symbol in ('?', '*', '+'):
        self[2:] = self.parser.symbol_table[next_symbol](self.parser),  # Add nullary token
        self.parser.advance()
    return self


@method('instance')
def evaluate(self, context=None):
    if self.parser.schema is None:
        self.missing_schema()
    occurs = self[2].symbol if len(self) > 2 else None
    position = None
    if self[1].symbol == 'empty-sequence':
        for _ in self[0].select(context):
            return False
        return True
    elif self[1].label == 'function':
        for position, item in enumerate(self[0].select(context)):
            if self[1].evaluate(context) is None:
                return False
            elif position and (occurs is None or occurs == '?'):
                return False
        else:
            return position is not None or occurs in ('*', '?')
    else:
        qname = prefixed_to_qname(self[1].source, self.parser.namespaces)
        for position, item in enumerate(self[0].select(context)):
            try:
                if not self.parser.schema.is_instance(item, qname):
                    return False
            except KeyError:
                self.missing_name("type %r not found in schema" % self[1].source)
            else:
                if position and (occurs is None or occurs == '?'):
                    return False
        else:
            return position is not None or occurs in ('*', '?')


@method('treat')
def evaluate(self, context=None):
    if self.parser.schema is None:
        self.missing_schema()
    occurs = self[2].symbol if len(self) > 2 else None
    position = None
    castable_expr = []
    if self[1].symbol == 'empty-sequence':
        for _ in self[0].select(context):
            self.wrong_sequence_type()
    elif self[1].label == 'function':
        for position, item in enumerate(self[0].select(context)):
            if self[1].evaluate(context) is None:
                self.wrong_sequence_type()
            elif position and (occurs is None or occurs == '?'):
                self.wrong_sequence_type("more than one item in sequence")
            castable_expr.append(item)
        else:
            if position is None and occurs not in ('*', '?'):
                self.wrong_sequence_type("the sequence cannot be empty")
    else:
        qname = prefixed_to_qname(self[1].source, self.parser.namespaces)
        for position, item in enumerate(self[0].select(context)):
            try:
                if not self.parser.schema.is_instance(item, qname):
                    self.wrong_sequence_type("item %r is not of type %r" % (item, self[1].source))
            except KeyError:
                self.missing_name("type %r not found in schema" % self[1].source)
            else:
                if position and (occurs is None or occurs == '?'):
                    self.wrong_sequence_type("more than one item in sequence")
                castable_expr.append(item)
        else:
            if position is None and occurs not in ('*', '?'):
                self.wrong_sequence_type("the sequence cannot be empty")

    return castable_expr


###
# Simple type based
@method('castable', bp=62)
@method('cast', bp=63)
def led(self, left):
    self.parser.advance('as')
    self[:] = left, self.parser.expression(rbp=self.rbp)
    if self.parser.next_token.symbol == '?':
        self[2:] = self.parser.symbol_table['?'](self.parser),  # Add nullary token
        self.parser.advance()
    return self


@method('castable')
@method('cast')
def evaluate(self, context=None):
    if self.parser.schema is None:
        self.missing_schema()
    atomic_type = prefixed_to_qname(self[1].source, namespaces=self.parser.namespaces)
    if atomic_type in (XSD_NOTATION, XSD_ANY_ATOMIC_TYPE):
        self.wrong_type("target type cannot be xs:NOTATION or xs:anyAtomicType [err:XPST0080]")

    result = [data_value(res) for res in self[0].select(context)]
    if len(result) > 1:
        if self.symbol != 'cast':
            return False
        self.wrong_context_type("more than one value in expression")
    elif not result:
        if len(self) == 3:
            return [] if self.symbol == 'cast' else True
        elif self.symbol != 'cast':
            return False
        else:
            self.wrong_value("atomic value is required")

    try:
        value = self.parser.schema.cast_as(result[0], atomic_type)
    except KeyError:
        self.unknown_atomic_type("atomic type %r not found in the in-scope schema types" % self[1].source)
    except TypeError as err:
        if self.symbol != 'cast':
            return False
        self.wrong_type(str(err))
    except ValueError as err:
        if self.symbol != 'cast':
            return False
        self.wrong_value(str(err))
    else:
        return value if self.symbol == 'cast' else True


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
        for result in op.select(context.copy() if context else None):
            yield result


###
# Parenthesized expressions: XPath 2.0 admits the empty case ().
@method('(')
def nud(self):
    if self.parser.next_token.symbol != ')':
        self[:] = self.parser.expression(),
    self.parser.advance(')')
    return self


@method('(')
def evaluate(self, context=None):
    if not self:
        return []
    else:
        return self[0].evaluate(context)


@method('(')
def select(self, context=None):
    if self:
        return self[0].select(context)
    else:
        return iter(())


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
        for item in context.root.iter():
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
    if context is not None:
        if context.item is None and is_document_node(context.root):
            if not self:
                return context.root
            elif is_element_node(context.root.getroot(), self[0].evaluate(context)):
                return context.root


@method(function('element', nargs=(0, 2), bp=90))
def evaluate(self, context=None):
    if context is not None:
        if not self:
            if is_element_node(context.item):
                return context.item
        elif is_element_node(context.item, self[1].evaluate(context)):
            return context.item


@method(function('schema-attribute', nargs=1, bp=90))
def evaluate(self, context=None):
    attribute_name = self[0].source
    qname = prefixed_to_qname(attribute_name, self.parser.namespaces)
    if self.parser.schema.get_attribute(qname) is None:
        self.missing_name("attribute %r not found in schema" % attribute_name)

    if context is not None:
        if is_attribute_node(context.item, qname):
            return context.item


@method(function('schema-element', nargs=1, bp=90))
def evaluate(self, context=None):
    element_name = self[0].source
    qname = prefixed_to_qname(element_name, self.parser.namespaces)
    if self.parser.schema.get_element(qname) is None \
            and self.parser.schema.get_substitution_group(qname) is None:
        self.missing_name("element %r not found in schema" % element_name)

    if context is not None:
        if is_element_node(context.item) and context.item.tag == qname:
            return context.item


@method(function('empty-sequence', nargs=0, bp=90))
def evaluate(self, context=None):
    if context is not None:
        return isinstance(context.item, list) and not context.item


@method('document-node')
@method('element')
@method('schema-attribute')
@method('schema-element')
@method('empty-sequence')
def select(self, context=None):
    if context is not None:
        for _ in context.iter_children_or_self():
            item = self.evaluate(context)
            if item is not None:
                yield item


###
# Context item
@method(function('item', nargs=0, bp=90))
def evaluate(self, context=None):
    if context is None:
        return
    elif context.item is None:
        return context.root
    else:
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
        precision = 0 if len(self) < 2 else self[1].evaluate(context)
        if PY3 or precision < 0:
            value = round(decimal.Decimal(item), precision)
        else:
            number = decimal.Decimal(item)
            exp = decimal.Decimal('1' if not precision else '.%s1' % ('0' * (precision - 1)))
            value = float(number.quantize(exp, rounding='ROUND_HALF_EVEN'))
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
def select(self, context=None):
    nan = False
    results = []
    for item in self[0].select(context):
        value = data_value(item)
        if context is not None:
            context.item = value
        if not nan and isinstance(value, float) and math.isnan(value):
            yield value
            nan = True
        elif value not in results:
            yield value
            results.append(value)


@method(function('insert-before', nargs=3, bp=90))
def select(self, context=None):
    insert_at_pos = max(0, self[1].value - 1)
    inserted = False
    for pos, result in enumerate(self[0].select(context)):
        if not inserted and pos == insert_at_pos:
            for item in self[2].select(context):
                yield item
            inserted = True
        yield result

    if not inserted:
        for item in self[2].select(context):
            yield item


@method(function('index-of', nargs=(1, 3), bp=90))
def select(self, context=None):
    value = self[1].evaluate(context)
    for pos, result in enumerate(self[0].select(context)):
        if result == value:
            yield pos + 1


@method(function('remove', nargs=2, bp=90))
def select(self, context=None):
    target = self[1].evaluate(context) - 1
    for pos, result in enumerate(self[0].select(context)):
        if pos != target:
            yield result


@method(function('reverse', nargs=1, bp=90))
def select(self, context=None):
    for result in reversed(list(self[0].select(context))):
        yield result


@method(function('subsequence', nargs=(2, 3), bp=90))
def select(self, context=None):
    starting_loc = self[1].evaluate(context) - 1
    length = self[2].evaluate(context) if len(self) >= 3 else 0
    for pos, result in enumerate(self[0].select(context)):
        if starting_loc <= pos and (not length or pos < starting_loc + length):
            yield result


@method(function('unordered', nargs=1, bp=90))
def select(self, context=None):
    for result in sorted(list(self[0].select(context)), key=lambda x: string_value(x)):
        yield result


###
# Cardinality functions for sequences
@method(function('zero-or-one', nargs=1, bp=90))
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


@method(function('one-or-more', nargs=1, bp=90))
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


@method(function('exactly-one', nargs=1, bp=90))
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
# String functions
@method(function('codepoints-to-string', nargs=1, bp=90))
def evaluate(self, context=None):
    return ''.join(unicode_chr(cp) for cp in self[0].select(context))


@method(function('string-to-codepoints', nargs=1, bp=90))
def select(self, context=None):
    for char in self[0].evaluate(context):
        yield ord(char)


@method(function('compare', nargs=(2, 3), bp=90))
def evaluate(self, context=None):
    raise NotImplementedError()


@method(function('codepoint-equal', nargs=2, bp=90))
def evaluate(self, context=None):
    raise NotImplementedError()


@method(function('string-join', nargs=2, bp=90))
def evaluate(self, context=None):
    try:
        return self[1].evaluate(context).join(s for s in self[0].select(context))
    except AttributeError as err:
        self.wrong_type("the separator must be a string: %s" % err)
    except TypeError as err:
        self.wrong_type("the values must be strings: %s" % err)


@method(function('normalize-unicode', nargs=(1, 2), bp=90))
def evaluate(self, context=None):
    raise NotImplementedError()


@method(function('upper-case', nargs=1, bp=90))
def evaluate(self, context=None):
    arg = self.get_argument(context)
    try:
        return '' if arg is None else arg.upper()
    except AttributeError:
        self.wrong_type("the argument must be a string: %r" % arg)


@method(function('lower-case', nargs=1, bp=90))
def evaluate(self, context=None):
    arg = self.get_argument(context)
    try:
        return '' if arg is None else arg.lower()
    except AttributeError:
        self.wrong_type("the argument must be a string: %r" % arg)


@method(function('encode-for-uri', nargs=1, bp=90))
def evaluate(self, context=None):
    uri_part = self.get_argument(context)
    try:
        return '' if uri_part is None else urllib_quote(uri_part, safe='~')
    except TypeError:
        self.wrong_type("the argument must be a string: %r" % uri_part)


@method(function('iri-to-uri', nargs=1, bp=90))
def evaluate(self, context=None):
    iri = self.get_argument(context)
    try:
        return '' if iri is None else urllib_quote(iri, safe='-_.!~*\'()#;/?:@&=+$,[]%')
    except TypeError:
        self.wrong_type("the argument must be a string: %r" % iri)


@method(function('escape-html-uri', nargs=1, bp=90))
def evaluate(self, context=None):
    uri = self.get_argument(context)
    try:
        return '' if uri is None else urllib_quote(uri, safe=''.join(chr(cp) for cp in range(32, 127)))
    except TypeError:
        self.wrong_type("the argument must be a string: %r" % uri)


@method(function('starts-with', nargs=(2, 3), bp=90))
def evaluate(self, context=None):
    arg1 = self.get_argument(context)
    arg2 = self.get_argument(context, index=1)
    try:
        return arg1.startswith(arg2)
    except TypeError:
        self.wrong_type("the arguments must be a string")


@method(function('ends-with', nargs=(2, 3), bp=90))
def evaluate(self, context=None):
    arg1 = self.get_argument(context)
    arg2 = self.get_argument(context, index=1)
    try:
        return arg1.endswith(arg2)
    except TypeError:
        self.wrong_type("the arguments must be a string")


###
# Example of token redefinition and how-to create a multi-role token.
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
        self[:] = self.parser.expression(rbp=90),
        self.label = 'axis'
    else:
        self.parser.advance('(')
        if self.parser.next_token.symbol != ')':
            self[:] = self.parser.expression(5),
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
        attribute_name = self[0].evaluate(context) if self else None
        for item in context.iter_attributes():
            if is_attribute_node(item, attribute_name):
                yield context.item[1]


@method('attribute')
def evaluate(self, context=None):
    if context is not None:
        if is_attribute_node(context.item, self[0].evaluate(context) if self else None):
            return context.item[1]


XPath2Parser.end()
