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
XPath 1.0 implementation - part 1 (parser class and symbols)
"""
import re
from abc import ABCMeta
from typing import cast, Any, ClassVar, Dict, FrozenSet, MutableMapping, \
    Optional, Tuple, Type, Set, Sequence

from ..helpers import OCCURRENCE_INDICATORS, EQNAME_PATTERN, normalize_sequence_type
from ..exceptions import MissingContextError, ElementPathKeyError, \
    ElementPathValueError, xpath_error
from ..datatypes import AnyAtomicType, NumericProxy, UntypedAtomic, QName, \
    xsd10_atomic_types, xsd11_atomic_types
from ..tdop import Token, Parser
from ..namespaces import NamespacesType, XML_NAMESPACE, XSD_NAMESPACE, XSD_ERROR, \
    XPATH_FUNCTIONS_NAMESPACE, XSD_ANY_SIMPLE_TYPE, XSD_ANY_ATOMIC_TYPE, \
    XSD_UNTYPED_ATOMIC, get_namespace, get_expanded_name
from ..schema_proxy import AbstractSchemaProxy
from ..xpath_token import NargsType, XPathToken, XPathAxis, XPathFunction, ProxyToken
from ..xpath_nodes import XPathNode, ElementNode, AttributeNode, DocumentNode

COMMON_SEQUENCE_TYPES = {
    'xs:untyped', 'untypedAtomic', 'attribute()', 'attribute(*)',
    'element()', 'element(*)', 'text()', 'document-node()', 'comment()',
    'processing-instruction()', 'item()', 'node()', 'numeric'
}


class XPath1Parser(Parser[XPathToken]):
    """
    XPath 1.0 expression parser class. Provide a *namespaces* dictionary argument for
    mapping namespace prefixes to URI inside expressions. If *strict* is set to `False`
    the parser enables also the parsing of QNames, like the ElementPath library.

    :param namespaces: a dictionary with mapping from namespace prefixes into URIs.
    :param strict: a strict mode is `False` the parser enables parsing of QNames \
    in extended format, like the Python's ElementPath library. Default is `True`.
    """
    version = '1.0'
    """The XPath version string."""

    token_base_class: Type[Token[Any]] = XPathToken
    literals_pattern = re.compile(
        r"""'(?:[^']|'')*'|"(?:[^"]|"")*"|(?:\d+|\.\d+)(?:\.\d*)?(?:[Ee][+-]?\d+)?"""
    )
    name_pattern = re.compile(r'[^\d\W][\w.\-\xb7\u0300-\u036F\u203F\u2040]*')

    SYMBOLS: ClassVar[FrozenSet[str]] = Parser.SYMBOLS | {
        # Axes
        'descendant-or-self', 'following-sibling', 'preceding-sibling',
        'ancestor-or-self', 'descendant', 'attribute', 'following',
        'namespace', 'preceding', 'ancestor', 'parent', 'child', 'self',

        # Operators
        'and', 'mod', 'div', 'or', '..', '//', '!=', '<=', '>=', '(', ')', '[', ']',
        ':', '.', '@', ',', '/', '|', '*', '-', '=', '+', '<', '>', '$', '::',

        # Node test functions
        'node', 'text', 'comment', 'processing-instruction',

        # Node set functions
        'last', 'position', 'count', 'id', 'name', 'local-name', 'namespace-uri',

        # String functions
        'string', 'concat', 'starts-with', 'contains',
        'substring-before', 'substring-after', 'substring',
        'string-length', 'normalize-space', 'translate',

        # Boolean functions
        'boolean', 'not', 'true', 'false', 'lang',

        # Number functions
        'number', 'sum', 'floor', 'ceiling', 'round',

        # Symbols for ElementPath extensions
        '{', '}'
    }

    RESERVED_FUNCTION_NAMES = {
        'comment', 'element', 'node', 'processing-instruction', 'text'
    }

    DEFAULT_NAMESPACES: ClassVar[Dict[str, str]] = {'xml': XML_NAMESPACE}
    """Namespaces known statically by default."""

    # Labels and symbols admitted after a path step
    PATH_STEP_LABELS: ClassVar[Tuple[str, ...]] = ('axis', 'kind test')
    PATH_STEP_SYMBOLS: ClassVar[Set[str]] = {
        '(integer)', '(string)', '(float)', '(decimal)', '(name)', '*', '@', '..', '.', '{'
    }

    # Class attributes for compatibility with XPath 2.0+
    schema: Optional[AbstractSchemaProxy] = None
    variable_types: Optional[Dict[str, str]] = None
    base_uri: Optional[str] = None
    function_namespace = XPATH_FUNCTIONS_NAMESPACE
    function_signatures: Dict[Tuple[QName, int], str] = {}

    compatibility_mode: bool = True
    """XPath 1.0 compatibility mode."""

    default_namespace: Optional[str] = None
    """
    The default namespace. For XPath 1.0 this value is always `None` because the default
    namespace is ignored (see https://www.w3.org/TR/1999/REC-xpath-19991116/#node-tests).
    """

    def __init__(self, namespaces: Optional[NamespacesType] = None, strict: bool = True,
                 *args: Any, **kwargs: Any) -> None:
        super(XPath1Parser, self).__init__()
        self.namespaces: Dict[str, str] = self.DEFAULT_NAMESPACES.copy()
        if namespaces is not None:
            self.namespaces.update(namespaces)
        self.strict: bool = strict

    @property
    def other_namespaces(self) -> Dict[str, str]:
        """The subset of namespaces not known by default."""
        return {k: v for k, v in self.namespaces.items() if k not in self.DEFAULT_NAMESPACES}

    @property
    def xsd_version(self) -> str:
        return '1.0'  # Use XSD 1.0 datatypes for default

    def xsd_qname(self, local_name: str) -> str:
        """Returns a prefixed QName string for XSD namespace."""
        if self.namespaces.get('xs') == XSD_NAMESPACE:
            return 'xs:%s' % local_name

        for pfx, uri in self.namespaces.items():
            if uri == XSD_NAMESPACE:
                return '%s:%s' % (pfx, local_name) if pfx else local_name

        raise xpath_error('XPST0081', 'Missing XSD namespace registration')

    @classmethod
    def create_restricted_parser(cls, name: str, symbols: Sequence[str]) \
            -> Type['XPath1Parser']:
        """Get a parser subclass with a restricted set of symbols.s"""
        _symbols = frozenset(symbols)
        symbol_table = {
            k: v for k, v in cls.symbol_table.items()
            if k in _symbols
        }
        return cast(Type['XPath1Parser'], ABCMeta(
            f"{name}{cls.__name__}", (cls,), {'symbol_table': symbol_table, 'SYMBOLS': _symbols}
        ))

    @staticmethod
    def unescape(string_literal: str) -> str:
        if string_literal.startswith("'"):
            return string_literal[1:-1].replace("''", "'")
        else:
            return string_literal[1:-1].replace('""', '"')

    @classmethod
    def proxy(cls, symbol: str, label: str = 'proxy', bp: int = 90) -> Type[ProxyToken]:
        """Register a proxy token for a symbol."""
        if symbol in cls.symbol_table and not issubclass(cls.symbol_table[symbol], ProxyToken):
            # Move the token class before register the proxy token
            token_cls = cls.symbol_table.pop(symbol)
            cls.symbol_table[f'{{{token_cls.namespace}}}{symbol}'] = token_cls

        proxy_class = cls.register(symbol, bases=(ProxyToken,), label=label, lbp=bp, rbp=bp)
        return cast(Type[ProxyToken], proxy_class)

    @classmethod
    def axis(cls, symbol: str, reverse_axis: bool = False, bp: int = 80) -> Type[XPathAxis]:
        """Register a token for a symbol that represents an XPath *axis*."""
        token_class = cls.register(symbol, label='axis', bases=(XPathAxis,),
                                   reverse_axis=reverse_axis, lbp=bp, rbp=bp)
        return cast(Type[XPathAxis], token_class)

    @classmethod
    def function(cls, symbol: str,
                 prefix: Optional[str] = None,
                 label: str = 'function',
                 nargs: NargsType = None,
                 sequence_types: Tuple[str, ...] = (),
                 bp: int = 90) -> Type[XPathFunction]:
        """
        Registers a token class for a symbol that represents an XPath function.
        """
        kwargs = {
            'bases': (XPathFunction,),
            'label': label,
            'nargs': nargs,
            'lbp': bp,
            'rbp': bp,
        }
        if 'function' not in label:
            # kind test or sequence type
            return cast(Type[XPathFunction], cls.register(symbol, **kwargs))
        elif symbol in cls.RESERVED_FUNCTION_NAMES:
            raise ElementPathValueError(f'{symbol!r} is a reserved function name')

        if prefix:
            namespace = cls.DEFAULT_NAMESPACES[prefix]
            qname = QName(namespace, '%s:%s' % (prefix, symbol))
            kwargs['lookup_name'] = qname.expanded_name
            kwargs['namespace'] = namespace
            cls.proxy(symbol, label='proxy function', bp=bp)
        else:
            qname = QName(XPATH_FUNCTIONS_NAMESPACE, 'fn:%s' % symbol)
            kwargs['namespace'] = XPATH_FUNCTIONS_NAMESPACE

        if sequence_types:
            # Register function signature(s)
            kwargs['sequence_types'] = sequence_types

            if nargs is None:
                pass  # pragma: no cover
            elif isinstance(nargs, int):
                assert len(sequence_types) == nargs + 1
                cls.function_signatures[(qname, nargs)] = 'function({}) as {}'.format(
                    ', '.join(sequence_types[:-1]), sequence_types[-1]
                )
            elif nargs[1] is None:
                assert len(sequence_types) == nargs[0] + 1
                cls.function_signatures[(qname, nargs[0])] = 'function({}, ...) as {}'.format(
                    ', '.join(sequence_types[:-1]), sequence_types[-1]
                )
            else:
                assert len(sequence_types) == nargs[1] + 1
                for arity in range(nargs[0], nargs[1] + 1):
                    cls.function_signatures[(qname, arity)] = 'function({}) as {}'.format(
                        ', '.join(sequence_types[:arity]), sequence_types[-1]
                    )

        return cast(Type[XPathFunction], cls.register(symbol, **kwargs))

    def parse(self, source: str) -> XPathToken:
        root_token = super(XPath1Parser, self).parse(source)
        try:
            root_token.evaluate()  # Static context evaluation
        except MissingContextError:
            pass
        return root_token

    def expected_name(self, *symbols: str, message: Optional[str] = None) -> None:
        """
        Checks the next symbol with a list of symbols. Replaces the next token
        with a '(name)' token if check fails and the symbol can be also a name.
        Otherwise raises a syntax error.

        :param symbols: a sequence of symbols.
        :param message: optional error message.
        """
        if self.next_token.symbol in symbols:
            return
        elif self.next_token.label in ('operator', 'symbol', 'let expression', 'proxy function') \
                and self.name_pattern.match(self.next_token.symbol) is not None:
            token_class = self.symbol_table['(name)']
            self.next_token = token_class(self, self.next_token.symbol)
        else:
            raise self.next_token.wrong_syntax(message)

    ###
    # Type checking (used in XPath 2.0)
    def is_instance(self, obj: Any, type_qname: str) -> bool:
        """Checks an instance against an XSD type."""
        if get_namespace(type_qname) == XSD_NAMESPACE:
            if type_qname == XSD_ERROR:
                return obj is None or obj == []
            elif type_qname == XSD_UNTYPED_ATOMIC:
                return isinstance(obj, UntypedAtomic)
            elif type_qname == XSD_ANY_ATOMIC_TYPE:
                return isinstance(obj, AnyAtomicType)
            elif type_qname == XSD_ANY_SIMPLE_TYPE:
                return isinstance(obj, AnyAtomicType) or \
                    isinstance(obj, list) and \
                    all(isinstance(x, AnyAtomicType) for x in obj)

            try:
                if self.xsd_version == '1.1':
                    return isinstance(obj, xsd11_atomic_types[type_qname])
                return isinstance(obj, xsd10_atomic_types[type_qname])
            except KeyError:
                pass

        if self.schema is not None:
            try:
                return self.schema.is_instance(obj, type_qname)
            except KeyError:
                pass

        raise ElementPathKeyError("unknown type %r" % type_qname)

    def is_sequence_type(self, value: str) -> bool:
        """Checks if a string is a sequence type specification."""
        try:
            value = normalize_sequence_type(value)
        except TypeError:
            return False

        if not value:
            return False
        elif value == 'empty-sequence()' or value == 'none':
            return True
        elif value in ('map(*)', 'array(*)') and self.version >= '3.1':
            return True
        elif value[-1] in OCCURRENCE_INDICATORS:
            value = value[:-1]

        if value in COMMON_SEQUENCE_TYPES:
            return True

        elif value.startswith('element(') and value.endswith(')'):
            if ',' not in value:
                return EQNAME_PATTERN.match(value[8:-1]) is not None

            try:
                arg1, arg2 = value[8:-1].split(', ')
            except ValueError:
                return False
            else:
                return (arg1 == '*' or EQNAME_PATTERN.match(arg1) is not None) \
                    and EQNAME_PATTERN.match(arg2) is not None

        elif value.startswith('document-node(') and value.endswith(')'):
            if not value.startswith('document-node(element('):
                return False
            return self.is_sequence_type(value[14:-1])

        elif value.startswith('function('):
            if self.version >= '3.0':
                if value == 'function(*)':
                    return True
                elif ' as ' in value:
                    pass
                elif not value.endswith(')'):
                    return False
                else:
                    return self.is_sequence_type(value[9:-1])

            try:
                value, return_type = value.rsplit(' as ', 1)
            except ValueError:
                return False
            else:
                if not self.is_sequence_type(return_type):
                    return False
                elif value == 'function()':
                    return True

                value = value[9:-1]
                if value.endswith(', ...'):
                    value = value[:-5]

                if 'function(' not in value:
                    return all(self.is_sequence_type(x) for x in value.split(', '))

                # Cover only if function() spec is the last argument
                k = value.index('function(')
                if not self.is_sequence_type(value[k:]):
                    return False
                return all(self.is_sequence_type(x) for x in value[:k].split(', ') if x)

        elif QName.pattern.match(value) is None:
            return False

        try:
            type_qname = get_expanded_name(value, self.namespaces)
            self.is_instance(None, type_qname)
        except (KeyError, ValueError):
            return False
        else:
            return True

    def match_sequence_type(self, value: Any,
                            sequence_type: str,
                            occurrence: Optional[str] = None) -> bool:
        """
        Checks a value instance against a sequence type.

        :param value: the instance to check.
        :param sequence_type: a string containing the sequence type spec.
        :param occurrence: an optional occurrence spec, can be '?', '+' or '*'.
        """
        if sequence_type[-1] in OCCURRENCE_INDICATORS:
            return self.match_sequence_type(value, sequence_type[:-1], sequence_type[-1])
        elif value is None or isinstance(value, list) and value == []:
            return sequence_type in ('empty-sequence()', 'none') or occurrence in ('?', '*')
        elif sequence_type in ('empty-sequence()', 'none'):
            return False
        elif isinstance(value, list):
            if len(value) == 1:
                return self.match_sequence_type(value[0], sequence_type)
            elif occurrence is None or occurrence == '?':
                return False
            else:
                return all(self.match_sequence_type(x, sequence_type) for x in value)
        elif sequence_type == 'item()':
            return isinstance(value, XPathNode) \
                   or isinstance(value, (AnyAtomicType, list, XPathFunction))
        elif sequence_type == 'numeric':
            return isinstance(value, NumericProxy)
        elif sequence_type.startswith('function('):
            if not isinstance(value, XPathFunction):
                return False
            return value.match_function_test(sequence_type)

        if isinstance(value, XPathNode):
            value_kind = value.kind
        else:
            try:
                type_expanded_name = get_expanded_name(sequence_type, self.namespaces)
                return self.is_instance(value, type_expanded_name)
            except (KeyError, ValueError):
                return False

        if sequence_type == 'node()':
            return True
        elif not sequence_type.startswith(value_kind) or not sequence_type.endswith(')'):
            return False
        elif sequence_type == f'{value_kind}()':
            return True
        elif value_kind == 'document':
            element_test = sequence_type[14:-1]
            if not element_test:
                return True
            element_node = cast(DocumentNode, value).getroot()
            return self.match_sequence_type(element_node, element_test)
        elif value_kind not in ('element', 'attribute'):
            return False

        _, params = sequence_type[:-1].split('(')
        if ',' not in sequence_type:
            name = params
        else:
            name, type_name = params.split(',')
            if type_name.endswith('?'):
                type_name = type_name[:-1]
            elif isinstance(value, ElementNode) and value.nilled:
                return False

            if type_name == 'xs:untyped':
                if isinstance(value, (ElementNode, AttributeNode)) \
                        and value.xsd_type is not None:
                    return False
            else:
                try:
                    type_expanded_name = get_expanded_name(type_name, self.namespaces)
                    if not self.is_instance(value, type_expanded_name):
                        return False
                except (KeyError, ValueError):
                    return False

        if name == '*':
            return True

        try:
            return bool(value.name == get_expanded_name(name, self.namespaces))
        except (KeyError, ValueError, AttributeError):
            return False

    def check_variables(self, values: MutableMapping[str, Any]) -> None:
        """Checks the sequence types of the XPath dynamic context's variables."""
        for varname, value in values.items():
            if not self.match_sequence_type(
                    value, 'item()', occurrence='*' if isinstance(value, list) else None):
                message = "Unmatched sequence type for variable {!r}".format(varname)
                raise xpath_error('XPDY0050', message)


###
# Special symbols
XPath1Parser.register('(start)')
XPath1Parser.register('(end)')
XPath1Parser.literal('(string)')
XPath1Parser.literal('(float)')
XPath1Parser.literal('(decimal)')
XPath1Parser.literal('(integer)')
XPath1Parser.literal('(invalid)')
XPath1Parser.register('(unknown)')

###
# Simple symbols
XPath1Parser.register(',')
XPath1Parser.register(')', bp=100)
XPath1Parser.register(']')
XPath1Parser.register('::')
XPath1Parser.register('}')

# XPath 1.0 definitions continue into module xpath1_operators
