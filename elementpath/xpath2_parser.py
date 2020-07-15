#
# Copyright (c), 2018-2020, SISSA (International School for Advanced Studies).
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
from itertools import product
from abc import ABCMeta
import decimal
import locale
import math
import operator
from collections.abc import MutableSequence
from copy import copy
from urllib.parse import urlparse

from .exceptions import ElementPathError, ElementPathKeyError, ElementPathTypeError, \
    MissingContextError, ElementPathValueError, xpath_error
from .namespaces import XSD_NAMESPACE, XML_NAMESPACE, XLINK_NAMESPACE, \
    XPATH_FUNCTIONS_NAMESPACE, XQT_ERRORS_NAMESPACE, XSD_NOTATION, \
    XSD_ANY_ATOMIC_TYPE, get_namespace, get_prefixed_qname, get_extended_qname, \
    XSD_UNTYPED_ATOMIC
from .datatypes import UntypedAtomic, XSD_BUILTIN_TYPES
from .xpath_nodes import is_xpath_node, is_attribute_node, is_element_node, \
    is_document_node, node_kind
from .xpath1_parser import XPath1Parser
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
    :param variables: a dictionary with the static context's in-scope variables. \
    It defines the associations between variables and static types. For backward \
    compatibility the variable types are detected if values are provided.
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

    def __init__(self, namespaces=None, variables=None, strict=True, compatibility_mode=False,
                 default_namespace=None, function_namespace=None, schema=None, base_uri=None,
                 default_collation=None,
                 document_types=None, collection_types=None, default_collection_type='node()*'):
        super(XPath2Parser, self).__init__(namespaces, strict)
        if default_namespace is not None:
            self.namespaces[''] = default_namespace

        if function_namespace is None:
            self.function_namespace = XPATH_FUNCTIONS_NAMESPACE
        else:
            self.function_namespace = function_namespace

        if schema is None:
            pass
        elif not isinstance(schema, AbstractSchemaProxy):
            msg = "argument 'schema' must be an instance of AbstractSchemaProxy"
            raise ElementPathTypeError(msg)
        else:
            schema.bind_parser(self)

        if not variables:
            self.variables = {}
        elif all(self.is_sequence_type(v) for v in variables.values()):
            self.variables = variables.copy()
        elif any(self.is_sequence_type(v) for v in variables.values()):
            raise ElementPathTypeError('ambiguous sequence types in variables')
        else:
            self.variables = {k: self.get_sequence_type(v) for k, v in variables.items()}

        self.base_uri = None if base_uri is None else urlparse(base_uri).geturl()
        self._compatibility_mode = compatibility_mode
        self._default_collation = default_collation

        if document_types:
            if any(not self.is_sequence_type(v) for v in document_types.values()):
                raise ElementPathTypeError('invalid document_types')
        self.document_types = document_types

        if collection_types:
            if any(not self.is_sequence_type(v) for v in collection_types.values()):
                raise ElementPathTypeError('invalid collection_types')
        self.collection_types = collection_types

        if not self.is_sequence_type(default_collection_type):
            raise ElementPathTypeError('invalid default_collection_type')
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
        return '.'.join(default_locale) if default_locale[1] else default_locale[0]

    @property
    def default_namespace(self):
        return self.namespaces.get('')

    @property
    def xsd_prefix(self):
        if self.namespaces.get('xs') == XSD_NAMESPACE:
            return 'xs'

        for pfx, uri in self.namespaces.items():
            if uri == XSD_NAMESPACE:
                return pfx

        raise xpath_error('XPST0081', 'Missing XSD namespace registration')

    def advance(self, *symbols):
        super(XPath2Parser, self).advance(*symbols)

        if self.next_token.symbol == '(:':
            # Parses and consumes an XPath 2.0 comment. A comment is
            # delimited by symbols '(:' and ':)' and can be nested.
            comment_level = 1
            while comment_level:
                self.advance_until('(:', ':)')
                if self.next_token.symbol == ':)':
                    comment_level -= 1
                elif self.next_token.symbol == '(:':
                    comment_level += 1
            self.advance(':)')

        return self.next_token

    @classmethod
    def constructor(cls, symbol, bp=0):
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
            except ElementPathError as err:
                if err.token is None:
                    err.token = self
                raise
            except ValueError as err:
                raise self.error('FORG0001', str(err)) from None
            except TypeError as err:
                raise self.error('FORG0001', str(err)) from None

        def cast_(value):
            raise NotImplementedError

        pattern = r'\b%s(?=\s*\(|\s*\(\:.*\:\)\()' % symbol
        token_class = cls.register(symbol, pattern=pattern, label='constructor', lbp=bp, rbp=bp,
                                   nud=nud_, evaluate=evaluate_, cast=cast_)

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
            item = self_.get_argument(context)
            if item is None:
                return []
            else:
                return self_.parser.schema.cast_as(self_[0].evaluate(context), atomic_type)

        symbol = get_prefixed_qname(atomic_type, self.namespaces)
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

    def is_schema_bound(self):
        return 'symbol_table' in self.__dict__

    def parse(self, source):
        root_token = super(XPath1Parser, self).parse(source)
        if root_token.label == 'sequence type':
            raise root_token.error('XPST0003', message="not allowed in XPath expression")

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

    ###
    # Type checking
    def is_instance(self, obj, type_qname):
        if type_qname == XSD_UNTYPED_ATOMIC:
            return isinstance(obj, UntypedAtomic)
        elif self.schema is not None:
            return self.schema.is_instance(obj, type_qname)

        if get_namespace(type_qname) == XSD_NAMESPACE:
            try:
                return XSD_BUILTIN_TYPES[type_qname.split('}')[1]].validator(obj)
            except ValueError:
                raise ElementPathValueError("%r is not extended QName" % type_qname)
            except KeyError:
                pass

        raise ElementPathKeyError("unknown type %r" % type_qname)

    def is_sequence_type(self, value):
        if not isinstance(value, str):
            return False

        text = value.strip()
        if not text:
            return False
        elif text == 'empty-sequence()':
            return True
        elif text[-1] in ('?', '+', '*'):
            text = text[:-1]

        if text in {'attribute()', 'element()', 'text()', 'document-node()',
                    'comment()', 'processing-instruction()', 'item()', 'node()'}:
            return True
        elif not XSD_BUILTIN_TYPES['QName'].validator(text):
            return False

        try:
            type_qname = get_extended_qname(text, self.namespaces)
            self.is_instance(None, type_qname)
        except (KeyError, ValueError):
            return False
        else:
            return True

    def get_sequence_type(self, value):
        if value is None or value == []:
            return 'empty-sequence()'
        elif isinstance(value, list):
            if value[0] is not None and not isinstance(value[0], list):
                sequence_type = self.get_sequence_type(value[0])
                if all(self.get_sequence_type(x) == sequence_type for x in value[1:]):
                    return '{}+'.format(sequence_type)
                else:
                    return 'node()+'
        else:
            value_kind = node_kind(value)
            if value_kind is not None:
                return '{}()'.format(value_kind)
            elif isinstance(value, UntypedAtomic):
                return '{}:{}'.format(self.xsd_prefix, 'untypedAtomic')

            if XSD_BUILTIN_TYPES['QName'].validator(value) and ':' in value:
                return '{}:QName'.format(self.xsd_prefix)

            for type_name in ['date', 'dateTime', 'gDay', 'gMonth', 'gMonthDay', 'gYear',
                              'gYearMonth', 'time', 'duration', 'dayTimeDuration',
                              'yearMonthDuration', 'dateTimeStamp', 'base64Binary',
                              'hexBinary', 'string', 'boolean', 'decimal', 'float']:
                if XSD_BUILTIN_TYPES[type_name].validator(value):
                    return '{}:{}'.format(self.xsd_prefix, type_name)

        raise ElementPathTypeError("Inconsistent sequence type for {!r}".format(value))

    def get_variable_value(self, varname):
        sequence_type = self.variables[varname]
        if sequence_type[-1] in {'?', '+', '*'}:
            sequence_type = sequence_type[:-1]

        if XSD_BUILTIN_TYPES['QName'].validator(sequence_type):
            type_qname = get_extended_qname(sequence_type, self.namespaces)
            if type_qname == XSD_UNTYPED_ATOMIC:
                return UntypedAtomic('1')
            elif self.schema is not None:
                xsd_type = self.schema.get_type(type_qname)
                if xsd_type is not None:
                    primitive_type = self.schema.get_primitive_type(xsd_type)
                    return XSD_BUILTIN_TYPES[primitive_type.local_name].value

            elif get_namespace(type_qname) == XSD_NAMESPACE:
                try:
                    return XSD_BUILTIN_TYPES[type_qname.split('}')[1]].value
                except KeyError:
                    pass

    def match_sequence_type(self, value, sequence_type, occurrence=None):
        if sequence_type[-1] in {'?', '+', '*'}:
            return self.match_sequence_type(value, sequence_type[:-1], sequence_type[-1])
        elif value is None or value == []:
            return sequence_type == 'empty-sequence()' or occurrence in {'?', '*'}
        elif sequence_type == 'empty-sequence()':
            return False
        elif isinstance(value, list):
            if len(value) == 1:
                return self.match_sequence_type(value[0], sequence_type)
            elif occurrence is None or occurrence == '?':
                return False
            else:
                return all(self.match_sequence_type(x, sequence_type) for x in value)
        else:
            value_kind = node_kind(value)
            if value_kind is not None:
                return sequence_type == 'node()' or \
                    '()' in sequence_type and sequence_type.startswith(value_kind)
            elif isinstance(value, UntypedAtomic):
                return '{}:{}'.format(self.xsd_prefix, 'untypedAtomic')

            try:
                type_qname = get_extended_qname(sequence_type, self.namespaces)
                return self.is_instance(value, type_qname)
            except (KeyError, ValueError):
                return False

    def check_variables(self, values):
        """Check variables values of the XPath dynamic context."""
        for varname, xsd_type in self.variables.items():
            if varname not in values:
                raise xpath_error('XPST0008', "Missing variable {!r}".format(varname))

        for varname, value in values.items():
            try:
                sequence_type = self.variables[varname]
            except KeyError:
                message = "Undeclared variable {!r}".format(varname)
                raise xpath_error('XPST0008', message) from None
            else:
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
literal = XPath2Parser.literal
prefix = XPath2Parser.prefix
infix = XPath2Parser.infix
infixr = XPath2Parser.infixr
method = XPath2Parser.method
function = XPath2Parser.function

##
# Remove symbols that have to be redefined for XPath 2.0.
unregister(',')
unregister('(')
unregister('$')

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

    varname = self[0].value
    try:
        return context.variable_values[varname]
    except KeyError:
        if isinstance(context, XPathSchemaContext):
            try:
                value = self.parser.get_variable_value(varname)
            except KeyError:
                pass
            else:
                if value is not None:
                    return value

    raise self.missing_name('unknown variable %r' % str(varname))


###
# Node sequence composition
XPath2Parser.duplicate('|', 'union')


@method(infix('intersect', bp=55))
def select(self, context=None):
    if context is None:
        raise self.missing_context()

    results = set(self[0].select(copy(context))) & set(self[1].select(copy(context)))
    yield from context.iter_results(results)


@method(infix('except', bp=55))
def select(self, context=None):
    if context is None:
        raise self.missing_context()

    results = set(self[0].select(copy(context))) - set(self[1].select(copy(context)))
    yield from context.iter_results(results)


###
# 'if' expression
@method('if', bp=20)
def nud(self):
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
        raise self.missing_context()

    some = self.symbol == 'some'
    varnames = [self[k][0].value for k in range(0, len(self) - 1, 2)]
    selectors = [self[k].select for k in range(1, len(self) - 1, 2)]

    for results in context.iter_product(selectors, varnames):
        context.variable_values.update(x for x in zip(varnames, results))
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
    if context is None:
        raise self.missing_context()

    context = copy(context)
    varnames = [self[k][0].value for k in range(0, len(self) - 1, 2)]
    selectors = tuple(self[k].select(copy(context)) for k in range(1, len(self) - 1, 2))
    for results in product(*selectors):
        context.variable_values.update(x for x in zip(varnames, results))
        yield from self[-1].select(copy(context))


###
# Sequence type based
@method('instance', bp=60)
@method('treat', bp=61)
def led(self, left):
    self.parser.advance('of' if self.symbol == 'instance' else 'as')
    if self.parser.next_token.label not in ('kind test', 'sequence type'):
        self.parser.expected_name('(name)', ':')

    self[:] = left, self.parser.expression(rbp=self.rbp)
    next_symbol = self.parser.next_token.symbol
    if self[1].symbol != 'empty-sequence' and next_symbol in ('?', '*', '+'):
        self[2:] = self.parser.symbol_table[next_symbol](self.parser),  # Add nullary token
        self.parser.advance()
    elif next_symbol in {'('}:
        raise self.error('XPST0051')
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
            if self[1].evaluate(context) is None:
                return False
            elif position and (occurs is None or occurs == '?'):
                return False
        else:
            return position is not None or occurs in ('*', '?')
    else:
        qname = get_extended_qname(self[1].source, self.parser.namespaces)
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
            if self[1].evaluate(context) is None:
                if context is not None and not isinstance(context, XPathSchemaContext):
                    raise self.wrong_sequence_type()
            elif position and (occurs is None or occurs == '?'):
                raise self.wrong_sequence_type("more than one item in sequence")
            castable_expr.append(item)
        else:
            if position is None and occurs not in ('*', '?'):
                raise self.wrong_sequence_type("the sequence cannot be empty")
    else:
        try:
            qname = get_extended_qname(self[1].source, self.parser.namespaces)
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
    self[:] = left, self.parser.expression(rbp=self.rbp)
    if self.parser.next_token.symbol == '?':
        self[2:] = self.parser.symbol_table['?'](self.parser),  # Add nullary token
        self.parser.advance()
    return self


@method('castable')
@method('cast')
def evaluate(self, context=None):
    try:
        atomic_type = get_extended_qname(self[1].source, namespaces=self.parser.namespaces)
    except KeyError as err:
        raise self.error('XPST0081', 'prefix {} not found'.format(str(err)))

    if atomic_type in (XSD_NOTATION, XSD_ANY_ATOMIC_TYPE):
        raise self.error('XPST0080')

    namespace = get_namespace(atomic_type)
    if namespace != XSD_NAMESPACE and \
            (self.parser.schema is None or self.parser.schema.get_type(atomic_type) is None):
        raise self.missing_schema("type %r not found in schema" % atomic_type)

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
            value = self.parser.schema.cast_as(arg, atomic_type)
        else:
            local_name = atomic_type.split('}')[1]
            token_class = self.parser.symbol_table.get(local_name)
            if token_class is None or token_class.label != 'constructor':
                msg = "atomic type %r not found in the in-scope schema types"
                self.unknown_atomic_type(msg % self[1].source)

            token = token_class(self.parser)
            if local_name in {'base64Binary', 'hexBinary'}:
                value = token.cast(arg, self[0].label == 'literal')
            elif local_name in {'dateTime', 'date', 'gDay', 'gMonth',
                                'gMonthDay', 'gYear', 'gYearMonth', 'time'}:
                value = token.cast(
                    arg, tz=None if context is None else context.timezone
                )
            else:
                value = token.cast(arg)
    except ElementPathError as err:
        if self.symbol != 'cast':
            return False
        elif err.token is None:
            err.token = self
        if isinstance(arg, UntypedAtomic):
            err.code = 'err:FORG0001'
        else:
            err.code = 'err:XPTY0004'
        raise
    except KeyError:
        msg = "atomic type %r not found in the in-scope schema types"
        self.unknown_atomic_type(msg % self[1].source)
    except TypeError as err:
        if self.symbol != 'cast':
            return False
        elif isinstance(arg, UntypedAtomic):
            raise self.error('FORG0001', str(err))
        elif self[0].symbol == ':' and self[0][1].symbol == 'string':
            raise self.error('FORG0001', str(err)) from None

        raise self.error('XPTY0004', str(err)) from None
    except ValueError as err:
        if self.symbol != 'cast':
            return False
        elif self[0].symbol == ':' and self[0][1].symbol == 'string':
            raise self.error('FORG0001', str(err)) from None

        raise self.error('XPTY0004', str(err)) from None
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
        yield from op.select(context=copy(context))


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
    op1 = self[0].get_atomized_operand(context=copy(context))
    op2 = self[1].get_atomized_operand(context=copy(context))

    if op1 is not None and op2 is not None:
        try:
            return getattr(operator, self.symbol)(op1, op2)
        except TypeError as err:
            if isinstance(context, XPathSchemaContext):
                raise self.wrong_context_type(str(err)) from None
            raise self.error('XPTY0004', str(err)) from None


###
# Node comparison
@method(infix('is', bp=30))
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
        for item in context.root.iter():
            if left[0] is item:
                return True if symbol == '<<' else False
            elif right[0] is item:
                return False if symbol == '<<' else True
        else:
            raise self.wrong_value("operands are not nodes of the XML tree!")


@method('is')
def nud(self):
    if self.parser.next_token.symbol == '(':
        raise self.error('XPST0017', '{} cannot have arguments'.format(self))
    raise self.wrong_syntax()


###
# Range expression
@method(infix('to', bp=35))
def evaluate(self, context=None):
    start, stop = self.get_operands(context, cls=int)
    try:
        return [x for x in range(start, stop + 1)]
    except TypeError as err:
        if context is None or start is None or stop is None:
            return []
        raise self.wrong_type(str(err)) from None


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
    elif isinstance(op1, UntypedAtomic):
        op1 = type(op2)(op1)
    elif isinstance(op2, UntypedAtomic):
        op2 = type(op1)(op2)

    try:
        if math.isinf(op1):
            raise self.error('FOAR0001' if op2 == 0 else 'FOAR0002')
        elif math.isnan(op1) or math.isnan(op2):
            raise self.error('FOAR0002')
    except TypeError as err:
        raise self.error('XPTY0004', str(err)) from None
    except ValueError as err:
        raise self.error('FORG0001', str(err)) from None

    try:
        return op1 // op2
    except (ZeroDivisionError, decimal.DivisionByZero):
        raise self.error('FOAR0001') from None


###
# Kind tests (sequence types that can appear also in XPath expressions)
@method(function('document-node', nargs=(0, 1), label='kind test'))
def select(self, context=None):
    if context is None:
        raise self.missing_context()
    elif not is_document_node(context.root) or context.item is not None:
        return
    elif not self:
        for item in context.iter_children_or_self():
            if item is None:
                yield context.root
    else:
        context.item = context.root.getroot()
        elements = [e for e in self[0].select(context) if is_element_node(e)]
        if len(elements) == 1:
            yield context.root
        context.item = None


@method('document-node')
def nud(self):
    self.parser.advance('(')
    if self.parser.next_token.symbol == 'element':
        self[0:] = self.parser.expression(5),
        if self.parser.next_token.symbol == ',':
            raise self.wrong_nargs('Too many arguments: expected at most 1 argument')
    elif self.parser.next_token.symbol != ')':
        raise self.wrong_syntax('element() kind test expected', code='XPST0081')
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
            elif self.xsd_types:
                type_annotation = self[1].evaluate(context)
                if self.xsd_types.is_matching(type_annotation, self.parser.default_namespace):
                    yield context.item


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

    for _ in context.iter_children_or_self():
        attribute_name = self[0].source
        qname = get_extended_qname(attribute_name, self.parser.namespaces)
        if self.parser.schema.get_attribute(qname) is None:
            raise self.missing_name("attribute %r not found in schema" % attribute_name)

        if is_attribute_node(context.item, qname):
            yield context.item


@method(function('schema-element', nargs=1, label='kind test'))
def select(self, context=None):
    if context is None:
        raise self.missing_context()

    for _ in context.iter_children_or_self():
        element_name = self[0].source
        qname = get_extended_qname(element_name, self.parser.namespaces)
        if self.parser.schema.get_element(qname) is None \
                and self.parser.schema.get_substitution_group(qname) is None:
            raise self.missing_name("element %r not found in schema" % element_name)

        if is_element_node(context.item) and context.item.tag == qname:
            yield context.item


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
        for item in context.iter_attributes():
            if is_attribute_node(item):
                yield context.item[1]
    else:
        name = self[0].value
        if self.parser.schema is not None and len(self) == 2:
            type_name = get_extended_qname(self[1].value, namespaces=self.parser.namespaces)
        else:
            type_name = None

        for item in context.iter_attributes():
            if is_attribute_node(item, name):
                if isinstance(context, XPathSchemaContext):
                    self.add_xsd_type(item[0], item[1].type)
                elif not type_name:
                    yield context.item[1]
                else:
                    xsd_type = self.get_xsd_type(item)
                    if xsd_type is not None and xsd_type.name == type_name:
                        yield context.item[1]

# XPath 2.0 definitions continue into module xpath2_functions
