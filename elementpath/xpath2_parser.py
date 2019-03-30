# -*- coding: utf-8 -*-
#
# Copyright (c), 2018-2019, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""
XPath 2.0 implementation - part 1 (XPath2Parser class and operators)
"""
from __future__ import division
from itertools import product
from abc import ABCMeta
import operator

from .compat import MutableSequence, urlparse
from .exceptions import ElementPathError, ElementPathTypeError, ElementPathMissingContextError
from .namespaces import XSD_NAMESPACE, XPATH_FUNCTIONS_NAMESPACE, XPATH_2_DEFAULT_NAMESPACES, \
    XSD_NOTATION, XSD_ANY_ATOMIC_TYPE, get_namespace, qname_to_prefixed, prefixed_to_qname
from .datatypes import XSD_BUILTIN_TYPES
from .xpath_helpers import is_xpath_node, boolean_value
from .tdop_parser import create_tokenizer
from .xpath1_parser import XML_NCNAME_PATTERN, XPath1Parser
from .xpath_context import XPathSchemaContext
from .schema_proxy import AbstractSchemaProxy


class XPath2Parser(XPath1Parser):
    """
    XPath 2.0 expression parser class. This is the default parser used by XPath selectors.
    A parser instance represents also the XPath static context. With *variables* you can pass
    a dictionary with the static context's in-scope variables.
    Provide a *namespaces* dictionary argument for mapping namespace prefixes to URI inside
    expressions. If *strict* is set to `False` the parser enables also the parsing of QNames,
    like the ElementPath library. There are some additional XPath 2.0 related arguments.

    :param namespaces: a dictionary with mapping from namespace prefixes into URIs.
    :param variables: a dictionary with the static context's in-scope variables.
    :param strict: if strict mode is `False` the parser enables parsing of QNames, \
    like the ElementPath library. Default is `True`.
    :param default_namespace: the default namespace to apply to unprefixed names. \
    For default no namespace is applied (empty namespace '').
    :param function_namespace: the default namespace to apply to unprefixed function names. \
    For default the namespace "http://www.w3.org/2005/xpath-functions" is used.
    :param schema: the schema proxy class or instance to use for types, attributes and elements lookups. \
    If an `AbstractSchemaProxy` subclass is provided then a schema proxy instance is built without the \
    optional argument, that involves a mapping of only XSD builtin types. If it's not provided the \
    XPath 2.0 schema's related expressions cannot be used.
    :param base_uri: an absolute URI maybe provided, used when necessary in the resolution of relative URIs.
    :param compatibility_mode: if set to `True` the parser instance works with XPath 1.0 compatibility rules.
    """
    SYMBOLS = XPath1Parser.SYMBOLS | {
        'union', 'intersect', 'instance', 'castable', 'if', 'then', 'else', 'for', 'to',
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

        # Aggregate functions
        'avg', 'min', 'max',

        # String functions
        'codepoints-to-string', 'string-to-codepoints', 'compare', 'codepoint-equal',
        'string-join', 'normalize-unicode', 'upper-case', 'lower-case', 'encode-for-uri',
        'iri-to-uri', 'escape-html-uri', 'ends-with',

        # General functions for sequences
        'distinct-values', 'empty', 'exists', 'index-of', 'insert-before', 'remove',
        'reverse', 'subsequence', 'unordered',

        # Cardinality functions for sequences
        'zero-or-one', 'one-or-more', 'exactly-one',

        # Comparing function for sequences
        # TODO 'deep-equal',

        # Pattern matching functions
        'matches', 'replace', 'tokenize',

        # Functions on anyURI
        'resolve-uri',

        # Functions for extracting fragments from xs:duration
        'years-from-duration', 'months-from-duration', 'days-from-duration',
        'hours-from-duration', 'minutes-from-duration', 'seconds-from-duration',

        # Functions for extracting fragments from xs:dateTime
        'year-from-dateTime', 'month-from-dateTime', 'day-from-dateTime', 'hours-from-dateTime',
        'minutes-from-dateTime', 'seconds-from-dateTime', 'timezone-from-dateTime',

        # Functions for extracting fragments from xs:date
        'year-from-date', 'month-from-date', 'day-from-date', 'timezone-from-date',

        # Functions for extracting fragments from xs:time
        'hours-from-time', 'minutes-from-time', 'seconds-from-time', 'timezone-from-time',

        # Timezone adjustment functions
        'adjust-dateTime-to-timezone', 'adjust-date-to-timezone', 'adjust-time-to-timezone',

        # Functions Related to QNames (QName function is also a constructor)
        'QName', 'local-name-from-QName', 'prefix-from-QName', 'local-name-from-QName',
        'namespace-uri-from-QName', 'namespace-uri-for-prefix', 'in-scope-prefixes', 'resolve-QName',

        # Context functions (TODO: 'default-collation')
        'current-dateTime', 'current-date', 'current-time', 'implicit-timezone', 'static-base-uri',

        # Node set functions
        'root',

        # Error function
        'error',

        # XSD builtins constructors ('string', 'boolean' and 'QName' already registered as functions)
        'normalizedString', 'token', 'language', 'Name', 'NCName', 'ENTITY', 'ID', 'IDREF',
        'NMTOKEN', 'anyURI', 'decimal', 'int', 'integer', 'long', 'short', 'byte', 'double',
        'float', 'nonNegativeInteger', 'positiveInteger', 'nonPositiveInteger', 'negativeInteger',
        'unsignedLong', 'unsignedInt', 'unsignedShort', 'unsignedByte', 'dateTime', 'date', 'time',
        'gDay', 'gMonth', 'gYear', 'gMonthDay', 'gYearMonth', 'duration', 'dayTimeDuration',
        'yearMonthDuration', 'base64Binary', 'hexBinary'

        # TODO: Functions and Operators that Generate Sequences
        # 'id', 'idref', 'doc', 'doc-available', 'collection',
    }

    QUALIFIED_FUNCTIONS = {
        'attribute', 'comment', 'document-node', 'element', 'empty-sequence', 'if', 'item', 'node',
        'processing-instruction', 'schema-attribute', 'schema-element', 'text', 'typeswitch'
    }

    DEFAULT_NAMESPACES = XPATH_2_DEFAULT_NAMESPACES

    def __init__(self, namespaces=None, variables=None, strict=True, default_namespace=None,
                 function_namespace=None, schema=None, base_uri=None, compatibility_mode=False):
        super(XPath2Parser, self).__init__(namespaces, variables, strict)
        if default_namespace is not None:
            self.namespaces[''] = default_namespace

        if function_namespace is None:
            self.function_namespace = XPATH_FUNCTIONS_NAMESPACE
        else:
            self.function_namespace = function_namespace

        if schema is None:
            self.schema = None
        elif not isinstance(schema, AbstractSchemaProxy):
            raise ElementPathTypeError("schema argument must be a subclass or instance of AbstractSchemaProxy!")
        else:
            self.schema = schema
            self.symbol_table = self.symbol_table.copy()
            for xsd_type in self.schema.iter_atomic_types():
                self.schema_constructor(xsd_type.name)
            self.tokenizer = create_tokenizer(self.symbol_table, XML_NCNAME_PATTERN)

        self.base_uri = None if base_uri is None else urlparse(base_uri).geturl()
        self._compatibility_mode = compatibility_mode

    @property
    def version(self):
        return '2.0'

    @property
    def compatibility_mode(self):
        return self._compatibility_mode

    @compatibility_mode.setter
    def compatibility_mode(self, value):
        self._compatibility_mode = value

    @property
    def default_namespace(self):
        return self.namespaces.get('')

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

    @classmethod
    def constructor(cls, symbol, bp=0):
        """Creates a constructor token class."""
        def nud_(self):
            self.parser.advance('(')
            self[0:] = self.parser.expression(5),
            self.parser.advance(')')
            self.value = None
            return self

        def evaluate_(self, context=None):
            item = self.get_argument(context)
            if item is None:
                return []
            try:
                return self.cast(item)
            except ElementPathError as err:
                if err.token is None:
                    err.token = self
                raise
            except ValueError as err:
                raise self.error('FOCA0002', str(err))
            except TypeError as err:
                raise self.error('FORG0006', str(err))

        def cast(value):
            raise NotImplemented

        pattern = r'\b%s(?=\s*\(|\s*\(\:.*\:\)\()' % symbol
        token_class = cls.register(symbol, pattern=pattern, label='constructor', lbp=bp, rbp=bp,
                                   nud=nud_, evaluate=evaluate_, cast=staticmethod(cast))

        def bind(func):
            assert func.__name__ == 'cast', "The function name must be 'cast', not %r." % func.__name__
            setattr(token_class, func.__name__, staticmethod(func))
            return func
        return bind

    def schema_constructor(self, atomic_type, bp=90):
        """Registers a token class for a schema atomic type constructor function."""
        if atomic_type in {XSD_ANY_ATOMIC_TYPE, XSD_NOTATION}:
            raise self.error('XPST0080')

        def nud_(self_):
            self_.parser.advance('(')
            self_[0:] = self_.parser.expression(5),
            self_.parser.advance(')')

            try:
                self_.value = self_.evaluate()  # Static context evaluation
            except ElementPathMissingContextError:
                self_.value = None
            return self_

        def evaluate_(self_, context=None):
            item = self_.get_argument(context)
            if item is None:
                return []
            else:
                return self_.parser.schema.cast_as(self_[0].evaluate(context), atomic_type)

        symbol = qname_to_prefixed(atomic_type, self.namespaces)
        token_class_name = str("_%s_constructor_token" % symbol.replace(':', '_'))
        kwargs = {
            'symbol': symbol,
            'label': 'constructor',
            'pattern': r'\b%s(?=\s*\(|\s*\(\:.*\:\)\()' % symbol,
            'lbp': bp,
            'rbp': bp,
            'nud': nud_,
            'evaluate': evaluate_,
            '__module__': self.__module__,
            '__qualname__': token_class_name,
            '__return__': None
        }
        token_class = ABCMeta(token_class_name, (self.token_base_class,), kwargs)
        MutableSequence.register(token_class)
        self.symbol_table[symbol] = token_class
        return token_class

    def next_is_path_step_token(self):
        return self.next_token.label in ('axis', 'function') or self.next_token.symbol in {
            '(integer)', '(string)', '(float)',  '(decimal)', '(name)', '*', '@', '..', '.', '(', '{'
        }

    def next_is_sequence_type_token(self):
        return self.next_token.symbol in {
            '(name)', ':', 'empty-sequence', 'item', 'document-node', 'element', 'attribute',
            'text', 'comment', 'processing-instruction', 'schema-attribute', 'schema-element'
        }

    def is_instance(self, obj, type_qname):
        if self.schema is not None:
            return self.schema.is_instance(obj, type_qname)
        local_name = type_qname.split('}')[1]
        return XSD_BUILTIN_TYPES[local_name].validator(obj)

    def parse(self, source):
        root_token = super(XPath1Parser, self).parse(source)
        context = None if self.schema is None else self.schema.get_context()
        try:
            root_token.evaluate(context)  # Static context evaluation
        except ElementPathMissingContextError:
            pass
        return root_token


##
# XPath 2.0 definitions
register = XPath2Parser.register
unregister = XPath2Parser.unregister
literal = XPath2Parser.literal
prefix = XPath2Parser.prefix
infix = XPath2Parser.infix
infixr = XPath2Parser.infixr
method = XPath2Parser.method

##
# Remove symbols that have to be redefined for XPath 2.0.
unregister(',')
unregister('(')

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
    if boolean_value(self[0].evaluate(context), self):
        return self[1].evaluate(context)
    else:
        return self[2].evaluate(context)


@method('if')
def select(self, context=None):
    if boolean_value(list(self[0].select(context)), self):
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
        if boolean_value(list(self[-1].select(context.copy())), self):
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
    self.parser.advance('of' if self.symbol == 'instance' else 'as')
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
                if not self.parser.is_instance(item, qname):
                    return False
            except KeyError:
                self.missing_schema("atomic type %r not found in in-scope schema types" % self[1].source)
            else:
                if position and (occurs is None or occurs == '?'):
                    return False
        else:
            return position is not None or occurs in ('*', '?')


@method('treat')
def evaluate(self, context=None):
    occurs = self[2].symbol if len(self) > 2 else None
    position = None
    castable_expr = []
    if self[1].symbol == 'empty-sequence':
        for _ in self[0].select(context):
            self.wrong_sequence_type()
    elif self[1].label == 'function':
        for position, item in enumerate(self[0].select(context)):
            if self[1].evaluate(context) is None:
                if context is not None and not isinstance(context, XPathSchemaContext):
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
                if not self.parser.is_instance(item, qname):
                    self.wrong_sequence_type("item %r is not of type %r" % (item, self[1].source))
            except KeyError:
                self.missing_schema("atomic type %r not found in in-scope schema types" % self[1].source)
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
    atomic_type = prefixed_to_qname(self[1].source, namespaces=self.parser.namespaces)
    if atomic_type in (XSD_NOTATION, XSD_ANY_ATOMIC_TYPE):
        raise self.error('XPST0080')

    namespace = get_namespace(atomic_type)
    if namespace != XSD_NAMESPACE and self.parser.schema is None or \
            self.parser.schema.get_type(atomic_type) is None:
        self.missing_schema("type %r not found in schema" % atomic_type)

    result = [res for res in self[0].select(context)]
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
        if namespace != XSD_NAMESPACE:
            value = self.parser.schema.cast_as(result[0], atomic_type)
        else:
            local_name = atomic_type.split('}')[1]
            token_class = self.parser.symbol_table.get(local_name)
            if token_class is None or token_class.label != 'constructor':
                self.unknown_atomic_type("atomic type %r not found in the in-scope schema types" % self[1].source)

            if local_name in {'base64Binary', 'hexBinary'}:
                value = token_class.cast(result[0], self[0].label == 'literal')
            elif local_name in {'dateTime', 'date', 'gDay', 'gMonth', 'gMonthDay', 'gYear', 'gYearMonth', 'time'}:
                value = token_class.cast(result[0], tz=None if context is None else context.timezone)
            elif local_name == 'QName':
                value = token_class.cast(result[0], self.parser.namespaces)
            else:
                value = token_class.cast(result[0])

    except ElementPathError as err:
        if self.symbol != 'cast':
            return False
        elif err.token is None:
            err.token = self
        raise
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
# Value comparison operators (eq, ne, lt, le, gt, and ge)
#
# Ref: https://www.w3.org/TR/xpath20/#id-value-comparisons
#
@method(infix('eq', bp=30))
@method(infix('ne', bp=30))
@method(infix('lt', bp=30))
@method(infix('gt', bp=30))
@method(infix('le', bp=30))
@method(infix('ge', bp=30))
def evaluate(self, context=None):
    if context is None:
        op1, op2 = self[0].get_atomized_operand(), self[1].get_atomized_operand()
    else:
        op1, op2 = self[0].get_atomized_operand(context.copy()), self[1].get_atomized_operand(context.copy())

    if op1 is not None and op2 is not None:
        return getattr(operator, self.symbol)(op1, op2)


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


# XPath 2.0 definitions continue into module xpath2_functions
