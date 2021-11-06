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
XPath 2.0 implementation - part 1 (parser class and symbols)
"""
from abc import ABCMeta
import locale
from collections.abc import MutableSequence
from urllib.parse import urlparse
from typing import cast, Any, Callable, ClassVar, Dict, FrozenSet, List, \
    MutableMapping, Optional, Tuple, Type, Union

from ..helpers import normalize_sequence_type
from ..exceptions import ElementPathError, ElementPathTypeError, \
    ElementPathValueError, MissingContextError, xpath_error
from ..namespaces import NamespacesType, XSD_NAMESPACE, XML_NAMESPACE, \
    XLINK_NAMESPACE, XPATH_FUNCTIONS_NAMESPACE, XQT_ERRORS_NAMESPACE, \
    XSD_NOTATION, XSD_ANY_ATOMIC_TYPE, get_prefixed_name
from ..datatypes import UntypedAtomic, AtomicValueType, QName
from ..xpath_token import UNICODE_CODEPOINT_COLLATION, XPathToken, \
    XPathFunction, XPathConstructor
from ..xpath_context import XPathContext
from ..schema_proxy import AbstractSchemaProxy
from ..xpath1 import XPath1Parser


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

    SYMBOLS: ClassVar[FrozenSet[str]] = XPath1Parser.SYMBOLS | {
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

    DEFAULT_NAMESPACES: ClassVar[Dict[str, str]] = {
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

    function_signatures: Dict[Tuple[QName, int], str] = XPath1Parser.function_signatures.copy()
    namespaces: Dict[str, str]
    token: XPathToken
    next_token: XPathToken

    def __init__(self, namespaces: Optional[NamespacesType] = None,
                 variable_types: Optional[Dict[str, str]] = None,
                 strict: bool = True,
                 compatibility_mode: bool = False,
                 default_collation: Optional[str] = None,
                 default_namespace: Optional[str] = None,
                 function_namespace: Optional[str] = None,
                 xsd_version: Optional[str] = None,
                 schema: Optional[AbstractSchemaProxy] = None,
                 base_uri: Optional[str] = None,
                 document_types: Optional[Dict[str, str]] = None,
                 collection_types: Optional[Dict[str, str]] = None,
                 default_collection_type: str = 'node()*') -> None:

        super(XPath2Parser, self).__init__(namespaces, strict)
        self._compatibility_mode = compatibility_mode
        self._default_collation = default_collation
        self._xsd_version = xsd_version if xsd_version is not None else '1.0'

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
            self.variable_types = {
                k: normalize_sequence_type(v) for k, v in variable_types.items()
            }
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

    def __getstate__(self) -> Dict[str, Any]:
        state = self.__dict__.copy()
        state.pop('symbol_table', None)
        state.pop('tokenizer', None)
        return state

    @property
    def compatibility_mode(self) -> bool:
        return self._compatibility_mode

    @compatibility_mode.setter
    def compatibility_mode(self, value: bool) -> None:
        self._compatibility_mode = value

    @property
    def default_collation(self) -> str:
        if self._default_collation is not None:
            return self._default_collation

        language_code, encoding = locale.getdefaultlocale()

        if language_code is None:
            return UNICODE_CODEPOINT_COLLATION
        elif encoding is None or not encoding:
            return language_code
        else:
            collation = f'{language_code}.{encoding}'
            if collation != 'en_US.UTF-8':
                return collation
            else:
                return UNICODE_CODEPOINT_COLLATION

    @property
    def default_namespace(self) -> Optional[str]:
        return self.namespaces.get('')

    @property
    def xsd_version(self) -> str:
        if self.schema is None:
            return self._xsd_version

        try:
            return self.schema.xsd_version
        except (AttributeError, NotImplementedError):
            return self._xsd_version

    def advance(self, *symbols: str) -> XPathToken:
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
    def constructor(cls, symbol: str, bp: int = 0, nargs: int = 1,
                    sequence_types: Union[Tuple[()], Tuple[str, ...], List[str]] = (),
                    label: Union[str, Tuple[str, ...]] = 'constructor function') \
            -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Creates a constructor token class."""
        def nud_(self: XPathConstructor) -> XPathConstructor:
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

        def evaluate_(self: XPathConstructor, context: Optional[XPathContext] = None) \
                -> Union[List[None], AtomicValueType]:
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

        if not sequence_types:
            assert nargs == 1
            sequence_types = ('xs:anyAtomicType?', 'xs:%s?' % symbol)

        token_class = cls.register(symbol, nargs=nargs, sequence_types=sequence_types,
                                   label=label, bases=(XPathConstructor,), lbp=bp, rbp=bp,
                                   nud=nud_, evaluate=evaluate_)

        def bind(func: Callable[..., Any]) -> Callable[..., Any]:
            method_name = func.__name__.partition('_')[0]
            if method_name != 'cast':
                raise ValueError("The function name must be 'cast' or starts with 'cast_'")
            setattr(token_class, method_name, func)
            return func
        return bind

    def schema_constructor(self, atomic_type_name: str, bp: int = 90) \
            -> Type[XPathFunction]:
        """Registers a token class for a schema atomic type constructor function."""
        if atomic_type_name in {XSD_ANY_ATOMIC_TYPE, XSD_NOTATION}:
            raise xpath_error('XPST0080')

        def nud_(self_: XPathFunction) -> XPathFunction:
            self_.parser.advance('(')
            self_[0:] = self_.parser.expression(5),
            self_.parser.advance(')')

            try:
                self_.value = self_.evaluate()  # Static context evaluation
            except MissingContextError:
                self_.value = None
            return self_

        def evaluate_(self_: XPathFunction, context: Optional[XPathContext] = None) \
                -> Union[List[None], AtomicValueType]:
            arg = self_.get_argument(context)
            if arg is None or self_.parser.schema is None:
                return []

            value = self_.string_value(arg)
            try:
                return self_.parser.schema.cast_as(value, atomic_type_name)
            except (TypeError, ValueError) as err:
                raise self_.error('FORG0001', err)

        symbol = get_prefixed_name(atomic_type_name, self.namespaces)
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
        token_class = cast(
            Type[XPathFunction], ABCMeta(token_class_name, (XPathFunction,), kwargs)
        )
        MutableSequence.register(token_class)
        self.symbol_table[symbol] = token_class
        return token_class

    def is_schema_bound(self) -> bool:
        return 'symbol_table' in self.__dict__

    def parse(self, source: str) -> XPathToken:
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

    def check_variables(self, values: MutableMapping[str, Any]) -> None:
        if self.variable_types is None:
            return

        for varname, xsd_type in self.variable_types.items():
            if varname not in values:
                raise xpath_error('XPST0008', "missing variable {!r}".format(varname))

        for varname, value in values.items():
            try:
                sequence_type = self.variable_types[varname]
            except KeyError:
                sequence_type = 'item()*' if isinstance(value, list) else 'item()'

            if not self.match_sequence_type(value, sequence_type):
                message = "Unmatched sequence type for variable {!r}".format(varname)
                raise xpath_error('XPDY0050', message)


##
# Remove symbols that have to be redefined for XPath 2.0.
XPath2Parser.unregister(',')
XPath2Parser.unregister('(')
XPath2Parser.unregister('$')
XPath2Parser.unregister('contains')
XPath2Parser.unregister('lang')
XPath2Parser.unregister('id')
XPath2Parser.unregister('substring-before')
XPath2Parser.unregister('substring-after')
XPath2Parser.unregister('starts-with')

###
# Symbols
XPath2Parser.register('then')
XPath2Parser.register('else')
XPath2Parser.register('in')
XPath2Parser.register('return')
XPath2Parser.register('satisfies')
XPath2Parser.register('?')
XPath2Parser.register('(:')
XPath2Parser.register(':)')

# XPath 2.0 definitions continue into module xpath2_operators
