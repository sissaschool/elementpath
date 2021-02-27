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
XPath 2.0 implementation - part 1 (XPath2Parser class and operators)
"""
from abc import ABCMeta
import locale
import math
import operator
from collections.abc import MutableSequence
from copy import copy
from decimal import Decimal, DivisionByZero
from urllib.parse import urlparse

from ..exceptions import ElementPathError, ElementPathTypeError, \
    ElementPathValueError, MissingContextError, xpath_error
from ..namespaces import XSD_NAMESPACE, XML_NAMESPACE, XLINK_NAMESPACE, \
    XPATH_FUNCTIONS_NAMESPACE, XQT_ERRORS_NAMESPACE, XSD_NOTATION, \
    XSD_ANY_ATOMIC_TYPE, get_namespace, get_prefixed_name, get_expanded_name
from ..datatypes import UntypedAtomic, QName, AnyURI, Duration, Integer
from ..xpath_nodes import TypedElement, is_xpath_node, \
    match_attribute_node, is_element_node, is_document_node
from ..xpath_token import UNICODE_CODEPOINT_COLLATION, XPathFunction
from ..xpath1 import XPath1Parser
from ..xpath_context import XPathSchemaContext
from ..schema_proxy import AbstractSchemaProxy


class XPath2Parser(XPath1Parser):
    """
    XPath 2.0 expression parser class. This is the default parser used by XPath selectors.
    A parser instance represents also the XPath static context. With *variable_types* you
    can pass a dictionary with the types of the in-scope variables.
    Provide a *namespaces* dictionary argument for mapping namespace prefixes to URI inside
    expressions. If *strict* is set to `False` the parser enables also the parsing of QNames,
    like the ElementPath library. There are some additional XPath 2.0 related arguments.

    :param namespaces: a dictionary with mapping from namespace prefixes into URIs.
    :param variable_types: a dictionary with the static context's in-scope variable \
    types. It defines the associations between variables and static types.
    :param strict: if strict mode is `False` the parser enables parsing of QNames, \
    like the ElementPath library. Default is `True`.
    :param compatibility_mode: if set to `True` the parser instance works with \
    XPath 1.0 compatibility rules.
    :param default_namespace: the default namespace to apply to unprefixed names. \
    For default no namespace is applied (empty namespace '').
    :param function_namespace: the default namespace to apply to unprefixed function \
    names. For default the namespace "http://www.w3.org/2005/xpath-functions" is used.
    :param schema: the schema proxy class or instance to use for types, attributes and \
    elements lookups. If an `AbstractSchemaProxy` subclass is provided then a schema \
    proxy instance is built without the optional argument, that involves a mapping of \
    only XSD builtin types. If it's not provided the XPath 2.0 schema's related \
    expressions cannot be used.
    :param base_uri: an absolute URI maybe provided, used when necessary in the \
    resolution of relative URIs.
    :param default_collation: the default string collation to use. If not set the \
    environment's default locale setting is used.
    :param document_types: statically known documents, that is a dictionary from \
    absolute URIs onto types. Used for type check when calling the *fn:doc* function \
    with a sequence of URIs. The default type of a document is 'document-node()'.
    :param collection_types: statically known collections, that is a dictionary from \
    absolute URIs onto types. Used for type check when calling the *fn:collection* \
    function with a sequence of URIs. The default type of a collection is 'node()*'.
    :param default_collection_type: this is the type of the sequence of nodes that \
    would result from calling the *fn:collection* function with no arguments. \
    Default is 'node()*'.
    """
    version = '2.0'

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
        'document-node', 'schema-attribute', 'element', 'schema-element',
        'attribute', 'empty-sequence',

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
        'deep-equal',

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
        'namespace-uri-from-QName', 'namespace-uri-for-prefix', 'in-scope-prefixes',
        'resolve-QName',

        # Static context functions
        'default-collation', 'static-base-uri',

        # Dynamic context functions
        'current-dateTime', 'current-date', 'current-time', 'implicit-timezone',

        # Node set functions
        'root',

        # Error function and trace function
        'error', 'trace',

        # XSD builtins constructors ('string', 'boolean' and 'QName' are
        # already registered as functions)
        'normalizedString', 'token', 'language', 'Name', 'NCName', 'ENTITY', 'ID',
        'IDREF', 'NMTOKEN', 'anyURI', 'NOTATION', 'decimal', 'int', 'integer', 'long',
        'short', 'byte', 'double', 'float', 'nonNegativeInteger', 'positiveInteger',
        'nonPositiveInteger', 'negativeInteger', 'unsignedLong', 'unsignedInt',
        'unsignedShort', 'unsignedByte', 'dateTime', 'date', 'time', 'gDay', 'gMonth',
        'gYear', 'gMonthDay', 'gYearMonth', 'duration', 'dayTimeDuration',
        'yearMonthDuration', 'dateTimeStamp', 'base64Binary', 'hexBinary', 'untypedAtomic',

        # Functions and Operators that Generate Sequences ('id' changes but
        # is already registered)
        'element-with-id', 'idref', 'doc', 'doc-available', 'collection',
    }

    DEFAULT_NAMESPACES = {
        'xml': XML_NAMESPACE,
        'xs': XSD_NAMESPACE,
        'xlink': XLINK_NAMESPACE,
        'fn': XPATH_FUNCTIONS_NAMESPACE,
        'err': XQT_ERRORS_NAMESPACE
    }

    PATH_STEP_LABELS = ('axis', 'function', 'kind test')
    PATH_STEP_SYMBOLS = {
        '(integer)', '(string)', '(float)', '(decimal)', '(name)', '*', '@', '..', '.', '(', '{'
    }

    function_signatures = XPath1Parser.function_signatures.copy()

    def __init__(self, namespaces=None, variable_types=None, strict=True, compatibility_mode=False,
                 default_collation=None, default_namespace=None, function_namespace=None,
                 xsd_version=None, schema=None, base_uri=None, document_types=None,
                 collection_types=None, default_collection_type='node()*'):
        super(XPath2Parser, self).__init__(namespaces, strict)
        self._compatibility_mode = compatibility_mode
        self._default_collation = default_collation
        self._xsd_version = xsd_version or '1.0'

        if default_namespace is not None:
            self.namespaces[''] = default_namespace

        if function_namespace is not None:
            self.function_namespace = function_namespace

        if schema is None:
            pass
        elif not isinstance(schema, AbstractSchemaProxy):
            msg = "argument 'schema' must be an instance of AbstractSchemaProxy"
            raise ElementPathTypeError(msg)
        else:
            schema.bind_parser(self)

        if not variable_types:
            self.variable_types = {}
        elif all(self.is_sequence_type(v) for v in variable_types.values()):
            self.variable_types = variable_types.copy()
        else:
            raise ElementPathValueError('invalid sequence type for in-scope variable types')

        self.base_uri = None if base_uri is None else urlparse(base_uri).geturl()

        if document_types:
            if any(not self.is_sequence_type(v) for v in document_types.values()):
                raise ElementPathValueError('invalid sequence type in document_types argument')
        self.document_types = document_types

        if collection_types:
            if any(not self.is_sequence_type(v) for v in collection_types.values()):
                raise ElementPathValueError('invalid sequence type in collection_types argument')
        self.collection_types = collection_types

        if not self.is_sequence_type(default_collection_type):
            raise ElementPathValueError('invalid sequence type for '
                                        'default_collection_type argument')
        self.default_collection_type = default_collection_type

    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop('symbol_table', None)
        state.pop('tokenizer', None)
        return state

    @property
    def compatibility_mode(self):
        return self._compatibility_mode

    @compatibility_mode.setter
    def compatibility_mode(self, value):
        self._compatibility_mode = value

    @property
    def default_collation(self):
        if self._default_collation is not None:
            return self._default_collation

        default_locale = locale.getdefaultlocale()
        collation = '.'.join(default_locale) if default_locale[1] else default_locale[0]
        return collation if collation != 'en_US.UTF-8' else UNICODE_CODEPOINT_COLLATION

    @property
    def default_namespace(self):
        return self.namespaces.get('')

    @property
    def xsd_version(self):
        try:
            return self.schema.xsd_version
        except (AttributeError, NotImplementedError):
            return self._xsd_version

    def advance(self, *symbols):
        super(XPath2Parser, self).advance(*symbols)

        if self.next_token.symbol == '(:':
            try:
                self.token.unexpected(':')
            except AttributeError:
                pass

            # Parses and consumes an XPath 2.0 comment. A comment is
            # delimited by symbols '(:' and ':)' and can be nested.
            comment_level = 1
            while comment_level:
                self.advance_until('(:', ':)')
                if self.next_token.symbol == ':)':
                    comment_level -= 1
                else:
                    comment_level += 1
            self.advance(':)')
            self.next_token.unexpected(':')

        return self.next_token

    @classmethod
    def signature(cls, value, *symbols, prefix=None):
        arity = 0 if value.startswith('function()') else value.count(',') + 1
        if not prefix:
            for symbol in symbols:
                qname = QName(XPATH_FUNCTIONS_NAMESPACE, 'fn:%s' % symbol)
                cls.function_signatures[(qname, arity)] = value
        else:
            namespace = cls.DEFAULT_NAMESPACES[prefix]
            for symbol in symbols:
                qname = QName(namespace, '%s:%s' % (prefix, symbol))
                cls.function_signatures[(qname, arity)] = value

    @classmethod
    def constructor(cls, symbol, bp=0, label='constructor function'):
        """Creates a constructor token class."""
        def nud_(self):
            try:
                self.parser.advance('(')
                self[0:] = self.parser.expression(5),
                if self.parser.next_token.symbol == ',':
                    raise self.wrong_nargs('Too many arguments: expected at most 1 argument')
                self.parser.advance(')')
                self.value = None
            except SyntaxError:
                raise self.error('XPST0017') from None
            return self

        def evaluate_(self, context=None):
            arg = self.data_value(self.get_argument(context))
            if arg is None:
                return []

            try:
                if isinstance(arg, UntypedAtomic):
                    return self.cast(arg.value)
                return self.cast(arg)
            except ElementPathError:
                raise
            except (TypeError, ValueError) as err:
                raise self.error('FORG0001', err) from None

        def cast_(value):
            raise NotImplementedError

        token_class = cls.register(symbol, nargs=1, label=label, bases=(XPathFunction,),
                                   lbp=bp, rbp=bp, nud=nud_, evaluate=evaluate_, cast=cast_)

        def bind(func):
            assert func.__name__ == 'cast', \
                "The function name must be 'cast', not %r." % func.__name__
            setattr(token_class, func.__name__, func)
            return func
        return bind

    def schema_constructor(self, atomic_type, bp=90):
        """Registers a token class for a schema atomic type constructor function."""
        if atomic_type in {XSD_ANY_ATOMIC_TYPE, XSD_NOTATION}:
            raise xpath_error('XPST0080')

        def nud_(self_):
            self_.parser.advance('(')
            self_[0:] = self_.parser.expression(5),
            self_.parser.advance(')')

            try:
                self_.value = self_.evaluate()  # Static context evaluation
            except MissingContextError:
                self_.value = None
            return self_

        def evaluate_(self_, context=None):
            arg = self_.get_argument(context)
            if arg is None:
                return []

            value = self_.string_value(arg)
            try:
                return self_.parser.schema.cast_as(value, atomic_type)
            except (TypeError, ValueError) as err:
                raise self_.error('FORG0001', err)

        symbol = get_prefixed_name(atomic_type, self.namespaces)
        token_class_name = "_%sConstructorFunction" % symbol.replace(':', '_')
        kwargs = {
            'symbol': symbol,
            'nargs': 1,
            'label': 'constructor function',
            'pattern': r'\b%s(?=\s*\(|\s*\(\:.*\:\)\()' % symbol,
            'lbp': bp,
            'rbp': bp,
            'nud': nud_,
            'evaluate': evaluate_,
            '__module__': self.__module__,
            '__qualname__': token_class_name,
            '__return__': None
        }
        token_class = ABCMeta(token_class_name, (XPathFunction,), kwargs)
        MutableSequence.register(token_class)
        self.symbol_table[symbol] = token_class
        return token_class

    def is_schema_bound(self):
        return 'symbol_table' in self.__dict__

    def parse(self, source):
        root_token = super(XPath1Parser, self).parse(source)
        if root_token.label == 'sequence type':
            raise root_token.error('XPST0003', "not allowed in XPath expression")

        if self.schema is None:
            try:
                root_token.evaluate()  # Static context evaluation
            except MissingContextError:
                pass
        else:
            # Static context evaluation with a dynamic schema context
            context = self.schema.get_context()
            for _ in root_token.select(context):
                pass

        return root_token

    def check_variables(self, values):
        for varname, xsd_type in self.variable_types.items():
            if varname not in values:
                raise xpath_error('XPST0008', "missing variable {!r}".format(varname))

        for varname, value in values.items():
            try:
                sequence_type = self.variable_types[varname]
            except KeyError:
                sequence_type = 'item()*' if isinstance(value, list) else 'item()'

            if sequence_type[-1] in ('?', '+', '*'):
                if self.match_sequence_type(value, sequence_type[:-1], sequence_type[-1]):
                    continue
            else:
                if self.match_sequence_type(value, sequence_type):
                    continue

            message = "Unmatched sequence type for variable {!r}".format(varname)
            raise xpath_error('XPDY0050', message)


##
# XPath 2.0 definitions
register = XPath2Parser.register
unregister = XPath2Parser.unregister
infix = XPath2Parser.infix
method = XPath2Parser.method
function = XPath2Parser.function

##
# Remove symbols that have to be redefined for XPath 2.0.
unregister(',')
unregister('(')
unregister('$')
unregister('contains')
unregister('lang')
unregister('id')
unregister('substring-before')
unregister('substring-after')
unregister('starts-with')

###
# Symbols
register('then')
register('else')
register('in')
register('return')
register('satisfies')
register('?')
register('(:')
register(':)')


@method('as')
@method('of')
def nud(self):
    raise self.error('XPDY0002')  # Dynamic context required


###
# Variables
@method('$', bp=90)
def nud(self):
    self.parser.expected_name('(name)')
    self[:] = self.parser.expression(rbp=90),
    return self


@method('$')
def evaluate(self, context=None):
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
                if sequence_type[-1] in {'?', '+', '*'}:
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
def select(self, context=None):
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
def nud(self):
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
def evaluate(self, context=None):
    if self.boolean_value(self[0].evaluate(copy(context))):
        return self[1].evaluate(context)
    else:
        return self[2].evaluate(context)


@method('if')
def select(self, context=None):
    if self.boolean_value([x for x in self[0].select(copy(context))]):
        yield from self[1].select(context)
    else:
        yield from self[2].select(context)


###
# Quantified expressions
@method('some', bp=20)
@method('every', bp=20)
def nud(self):
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
def evaluate(self, context=None):
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
def nud(self):
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
def select(self, context=None):
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
def led(self, left):
    self.parser.advance('of' if self.symbol == 'instance' else 'as')
    if self.parser.next_token.label not in ('kind test', 'sequence type'):
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
def evaluate(self, context=None):
    occurs = self[2].symbol if len(self) > 2 else None
    position = None

    if self[1].symbol == 'empty-sequence':
        for _ in self[0].select(context):
            return False
        return True
    elif self[1].label in ('kind test', 'sequence type'):
        if context is None:
            raise self.missing_context()

        for position, context.item in enumerate(self[0].select(context)):
            result = self[1].evaluate(context)
            if isinstance(result, list) and not result:
                return False
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
def evaluate(self, context=None):
    occurs = self[2].symbol if len(self) > 2 else None
    position = None
    castable_expr = []
    if self[1].symbol == 'empty-sequence':
        for _ in self[0].select(context):
            raise self.wrong_sequence_type()
    elif self[1].label in ('kind test', 'sequence type'):
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

        for position, item in enumerate(self[0].select(context)):
            try:
                if not self.parser.is_instance(item, qname):
                    msg = "item %r is not of type %r"
                    raise self.wrong_sequence_type(msg % (item, self[1].source))
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
def led(self, left):
    self.parser.advance('as')
    self.parser.expected_name('(name)', ':')
    self[:] = left, self.parser.expression(rbp=self.rbp)
    if self.parser.next_token.symbol == '?':
        self[2:] = self.parser.symbol_table['?'](self.parser),  # Add nullary token
        self.parser.advance()
    return self


@method('castable')
@method('cast')
def evaluate(self, context=None):
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
def evaluate(self, context=None):
    results = []
    for op in self:
        result = op.evaluate(context)
        if isinstance(result, list):
            results.extend(result)
        elif result is not None:
            results.append(result)
    return results


@method(',')
def select(self, context=None):
    for op in self:
        yield from op.select(context=copy(context))


###
# Parenthesized expressions: XPath 2.0 admits the empty case ().
@method('(', bp=100)
def nud(self):
    if self.parser.next_token.symbol != ')':
        self[:] = self.parser.expression(),
    self.parser.advance(')')
    return self


@method('(')
def evaluate(self, context=None):
    return self[0].evaluate(context) if self else []


@method('(')
def select(self, context=None):
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
def led(self, left):
    if left.symbol in {'eq', 'ne', 'lt', 'le', 'gt', 'ge'}:
        raise self.wrong_syntax()
    self[:] = left, self.parser.expression(rbp=30)
    return self


@method('eq')
@method('ne')
@method('lt')
@method('gt')
@method('le')
@method('ge')
def evaluate(self, context=None):
    operands = [self[0].get_atomized_operand(context=copy(context)),
                self[1].get_atomized_operand(context=copy(context))]

    if any(x is None for x in operands):
        return

    cls0, cls1 = type(operands[0]), type(operands[1])
    if cls0 is cls1 and cls0 is not Duration:
        pass
    elif all(isinstance(x, float) for x in operands):
        pass
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
def led(self, left):
    if left.symbol == 'is':
        raise self.wrong_syntax()
    self[:] = left, self.parser.expression(rbp=30)
    return self


@method('is')
@method(infix('<<', bp=30))
@method(infix('>>', bp=30))
def evaluate(self, context=None):
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

    if symbol == 'is':
        return left[0] is right[0]
    else:
        if left[0] is right[0]:
            return False
        for item in context.root.iter():  # pragma: no cover
            if left[0] is item:
                return True if symbol == '<<' else False
            elif right[0] is item:
                return False if symbol == '<<' else True
        else:
            raise self.error('FOCA0002', "operands are not nodes of the XML tree!")


###
# Range expression
@method('to', bp=35)
def led(self, left):
    if left.symbol == 'to':
        raise self.wrong_syntax()
    self[:] = left, self.parser.expression(rbp=35)
    return self


@method('to')
def evaluate(self, context=None):
    start, stop = self.get_operands(context, cls=Integer)
    try:
        return [x for x in range(start, stop + 1)]
    except TypeError:
        return []


@method('to')
def select(self, context=None):
    yield from self.evaluate(context)


###
# Numerical operators
@method(infix('idiv', bp=45))
def evaluate(self, context=None):
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
def nud(self):
    token = self.parser.symbol_table['(name)'](self.parser, self.symbol)
    return token.nud()


###
# Kind tests (sequence types that can appear also in XPath expressions)
@method(function('document-node', nargs=(0, 1), label='kind test'))
def select(self, context=None):
    if context is None:
        raise self.missing_context()
    elif not self:
        if is_document_node(context.root) and context.item is None:
            for item in context.iter_children_or_self():
                if item is None:
                    yield context.root
    else:
        elements = [e for e in self[0].select(copy(context)) if is_element_node(e)]
        if is_document_node(context.root) and context.item is None:
            if len(elements) == 1:
                yield context.root


@method('document-node')
def nud(self):
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
def select(self, context=None):
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
                for type_annotation in self[1].select():
                    if type_annotation == item.xsd_type.name:
                        yield item


@method('element')
def nud(self):
    self.parser.advance('(')
    if self.parser.next_token.symbol != ')':
        self.parser.expected_name('(name)', ':', '*', message='a QName or a wildcard expected')
        self[0:] = self.parser.expression(5),
        if self.parser.next_token.symbol == ',':
            self.parser.advance(',')
            self.parser.expected_name('(name)', ':', message='a QName expected')
            self[1:] = self.parser.expression(5),
    self.parser.advance(')')
    self.value = None
    return self


@method(function('schema-attribute', nargs=1, label='kind test'))
def select(self, context=None):
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
def select(self, context=None):
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
def nud(self):
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
unregister('attribute')
register('attribute', lbp=90, rbp=90, label=('kind test', 'axis'),
         pattern=r'\battribute(?=\s*\:\:|\s*\(\:.*\:\)\s*\:\:|\s*\(|\s*\(\:.*\:\)\()')


@method('attribute')
def nud(self):
    if self.parser.next_token.symbol == '::':
        self.parser.advance('::')
        self.parser.expected_name(
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
        self.label = 'kind test'
    return self


@method('attribute')
def select(self, context=None):
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
