#
# Copyright (c), 2018-2021, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import re
import math
import decimal
import operator
from copy import copy
from typing import Dict, Tuple

from ..helpers import EQNAME_PATTERN, normalize_sequence_type
from ..exceptions import MissingContextError, ElementPathKeyError, \
    ElementPathValueError, xpath_error
from ..datatypes import AnyAtomicType, AbstractDateTime, Duration, DayTimeDuration, \
    YearMonthDuration, NumericProxy, ArithmeticProxy, UntypedAtomic, QName, \
    xsd10_atomic_types, xsd11_atomic_types, ATOMIC_VALUES
from ..xpath_context import XPathSchemaContext
from ..tdop import Parser
from ..namespaces import XML_NAMESPACE, XSD_NAMESPACE, XPATH_FUNCTIONS_NAMESPACE, \
    XPATH_MATH_FUNCTIONS_NAMESPACE, XSD_ANY_SIMPLE_TYPE, XSD_ANY_ATOMIC_TYPE, \
    XSD_UNTYPED_ATOMIC, get_namespace, get_expanded_name, split_expanded_name
from ..schema_proxy import AbstractSchemaProxy
from ..xpath_token import XPathToken, XPathAxis, XPathFunction
from ..xpath_nodes import XPathNode, TypedElement, AttributeNode, TypedAttribute, \
    is_xpath_node, match_element_node, is_schema_node, is_document_node, \
    match_attribute_node, is_element_node, node_kind


OPERATORS_MAP = {
    '=': operator.eq,
    '!=': operator.ne,
    '>': operator.gt,
    '>=': operator.ge,
    '<': operator.lt,
    '<=': operator.le,
}


class XPath1Parser(Parser):
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

    token_base_class = XPathToken
    literals_pattern = re.compile(
        r"""'(?:[^']|'')*'|"(?:[^"]|"")*"|(?:\d+|\.\d+)(?:\.\d*)?(?:[Ee][+-]?\d+)?"""
    )
    name_pattern = re.compile(r'[^\d\W][\w.\-\xb7\u0300-\u036F\u203F\u2040]*')

    SYMBOLS = Parser.SYMBOLS | {
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

    DEFAULT_NAMESPACES = {'xml': XML_NAMESPACE}
    """
    The default prefix-to-namespace associations of the XPath class. These namespaces
    are updated in the instance with the ones passed with the *namespaces* argument.
    """

    # Labels and symbols admitted after a path step
    PATH_STEP_LABELS: Tuple[str, ...] = ('axis', 'kind test')
    PATH_STEP_SYMBOLS = {
        '(integer)', '(string)', '(float)', '(decimal)', '(name)', '*', '@', '..', '.', '{'
    }

    # Class attributes for compatibility with XPath 2.0+
    schema = None           # XPath 1.0 doesn't have schema bindings
    variable_types = None   # XPath 1.0 doesn't have in-scope variable types
    xsd_version = '1.0'     # Use XSD 1.0 datatypes for default
    function_namespace = XPATH_FUNCTIONS_NAMESPACE
    function_signatures: Dict[Tuple[QName, int], str] = {}

    # https://www.w3.org/TR/xpath-3/#id-reserved-fn-names
    RESERVED_FUNCTION_NAMES = {
        'array', 'attribute', 'comment', 'document-node', 'element', 'empty-sequence',
        'function', 'if', 'item', 'map', 'namespace-node', 'node', 'processing-instruction',
        'schema-attribute', 'schema-element', 'switch', 'text', 'typeswitch',
    }

    def __init__(self, namespaces=None, strict=True, *args, **kwargs):
        super(XPath1Parser, self).__init__()
        self.namespaces = self.DEFAULT_NAMESPACES.copy()
        if namespaces is not None:
            self.namespaces.update(namespaces)
        self.strict = strict

    @property
    def compatibility_mode(self):
        """XPath 1.0 compatibility mode."""
        return True

    @property
    def default_namespace(self):
        """
        The default namespace. For XPath 1.0 this value is always `None` because the default
        namespace is ignored (see https://www.w3.org/TR/1999/REC-xpath-19991116/#node-tests).
        """
        return

    def xsd_qname(self, local_name):
        """Returns a prefixed QName string for XSD namespace."""
        if self.namespaces.get('xs') == XSD_NAMESPACE:
            return 'xs:%s' % local_name

        for pfx, uri in self.namespaces.items():
            if uri == XSD_NAMESPACE:
                return '%s:%s' % (pfx, local_name) if pfx else local_name

        raise xpath_error('XPST0081', 'Missing XSD namespace registration')

    @staticmethod
    def unescape(string_literal):
        if string_literal.startswith("'"):
            return string_literal[1:-1].replace("''", "'")
        else:
            return string_literal[1:-1].replace('""', '"')

    @classmethod
    def axis(cls, symbol, reverse_axis=False, bp=80):
        """Register a token for a symbol that represents an XPath *axis*."""
        return cls.register(symbol, label='axis', bases=(XPathAxis,),
                            reverse_axis=reverse_axis, lbp=bp, rbp=bp)

    @classmethod
    def function(cls, symbol, nargs=None, sequence_types=(), label='function', bp=90):
        """
        Registers a token class for a symbol that represents an XPath function.
        """
        if 'function' not in label:
            pass
        elif symbol in cls.RESERVED_FUNCTION_NAMES:
            raise ElementPathValueError(f'{symbol!r} is a reserved function name')
        elif sequence_types:
            # Register function signature(s)
            if label == 'math function':
                qname = QName(XPATH_MATH_FUNCTIONS_NAMESPACE, 'math:%s' % symbol)
            else:
                qname = QName(XPATH_FUNCTIONS_NAMESPACE, 'fn:%s' % symbol)

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

        return cls.register(symbol, nargs=nargs, sequence_types=sequence_types, label=label,
                            bases=(XPathFunction,), lbp=bp, rbp=bp)

    def parse(self, source):
        root_token = super(XPath1Parser, self).parse(source)
        try:
            root_token.evaluate()  # Static context evaluation
        except MissingContextError:
            pass
        return root_token

    def expected_name(self, *symbols, message=None):
        """
        Checks the next symbol with a list of symbols. Replaces the next token
        with a '(name)' token if check fails and the symbol can be also a name.
        Otherwise raises a syntax error.

        :param symbols: a sequence of symbols.
        :param message: optional error message.
        """
        if self.next_token.symbol in symbols:
            return
        elif self.next_token.label == 'operator' and \
                self.name_pattern.match(self.next_token.symbol) is not None:
            self.next_token = self.symbol_table['(name)'](self, self.next_token.symbol)
        else:
            raise self.next_token.wrong_syntax(message)

    ###
    # Type checking (used in XPath 2.0)
    def is_instance(self, obj, type_qname):
        """Checks an instance against an XSD type."""
        if get_namespace(type_qname) == XSD_NAMESPACE:
            if type_qname == XSD_UNTYPED_ATOMIC:
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

    def is_sequence_type(self, value):
        """Checks is a string is a sequence type specification."""
        try:
            value = normalize_sequence_type(value)
        except TypeError:
            return False

        if not value:
            return False
        elif value == 'empty-sequence()' or value == 'none':
            return True
        elif value[-1] in {'?', '+', '*'}:
            value = value[:-1]

        if value in {'untypedAtomic', 'attribute()', 'attribute(*)', 'element()',
                     'element(*)', 'text()', 'document-node()', 'comment()',
                     'processing-instruction()', 'item()', 'node()', 'numeric'}:
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
            if value == 'function(*)' and self.version >= '3.0':
                return True

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

    def get_atomic_value(self, type_or_name):
        """Gets an atomic value for an XSD type instance or name. Used for schema contexts."""
        if isinstance(type_or_name, str):
            expanded_name = get_expanded_name(type_or_name, self.namespaces)
            xsd_type = None
        else:
            xsd_type = type_or_name
            expanded_name = xsd_type.name

        if expanded_name:
            uri, local_name = split_expanded_name(expanded_name)
            if uri == XSD_NAMESPACE:
                try:
                    return ATOMIC_VALUES[local_name]
                except KeyError:
                    pass

        if xsd_type is None and self.schema is not None:
            xsd_type = self.schema.get_type(expanded_name)

        if xsd_type is None:
            return UntypedAtomic('1')
        elif xsd_type.is_simple() or xsd_type.has_simple_content():
            try:
                primitive_type = self.schema.get_primitive_type(xsd_type)
                return ATOMIC_VALUES[primitive_type.local_name]
            except (KeyError, AttributeError):
                return UntypedAtomic('1')
        else:
            # returns an xs:untypedAtomic value also for element-only types
            # (that should be None) because it is for static evaluation.
            return UntypedAtomic('1')

    def match_sequence_type(self, value, sequence_type, occurrence=None):
        """
        Checks a value instance against a sequence type.

        :param value: the instance to check.
        :param sequence_type: a string containing the sequence type spec.
        :param occurrence: an optional occurrence spec, can be '?', '+' or '*'.
        """
        if sequence_type[-1] in {'?', '+', '*'}:
            return self.match_sequence_type(value, sequence_type[:-1], sequence_type[-1])
        elif value is None or isinstance(value, list) and value == []:
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
        elif sequence_type == 'item()':
            return is_xpath_node(value) or isinstance(value, (AnyAtomicType, list))
        elif sequence_type == 'numeric':
            return isinstance(value, NumericProxy)

        value_kind = node_kind(value)
        if value_kind is not None:
            return sequence_type == 'node()' or sequence_type == '%s()' % value_kind

        try:
            type_qname = get_expanded_name(sequence_type, self.namespaces)
            return self.is_instance(value, type_qname)
        except (KeyError, ValueError):
            return False

    def check_variables(self, values):
        """Checks the sequence types of the XPath dynamic context's variables."""
        for varname, value in values.items():
            if not self.match_sequence_type(
                    value, 'item()', occurrence='*' if isinstance(value, list) else None):
                message = "Unmatched sequence type for variable {!r}".format(varname)
                raise xpath_error('XPDY0050', message)


##
# XPath1 definitions
register = XPath1Parser.register
literal = XPath1Parser.literal
nullary = XPath1Parser.nullary
prefix = XPath1Parser.prefix
infix = XPath1Parser.infix
postfix = XPath1Parser.postfix
method = XPath1Parser.method
function = XPath1Parser.function
axis = XPath1Parser.axis


###
# Simple symbols
register(',')
register(')', bp=100)
register(']')
register('::')
register('}')


###
# Literals
literal('(string)')
literal('(float)')
literal('(decimal)')
literal('(integer)')
literal('(invalid)')
literal('(unknown)')


@method(register('(name)', bp=10, label='literal'))
def nud_name_literal(self):
    if self.parser.next_token.symbol == '(':
        if self.parser.version >= '3.0':
            pass
        elif self.namespace == XSD_NAMESPACE:
            raise self.error('XPST0017', 'unknown constructor function {!r}'.format(self.value))
        elif self.value not in self.parser.RESERVED_FUNCTION_NAMES:
            raise self.error('XPST0017', 'unknown function {!r}'.format(self.value))
        elif self.value == 'typeswitch':
            msg = 'improper use of XQuery reserved name {!r}'
            raise self.error('XPST0003', msg.format(self.value))
        else:
            msg = 'improper use of XPath reserved name {!r}'
            raise self.error('XPST0017', msg.format(self.value))

    elif self.parser.next_token.symbol == '::':
        raise self.missing_axis("axis '%s::' not found" % self.value)
    return self


@method('(name)')
def evaluate_name_literal(self, context=None):
    return [x for x in self.select(context)]


@method('(name)')
def select_name_literal(self, context=None):
    if context is None:
        raise self.missing_context()

    name = self.value

    if isinstance(context, XPathSchemaContext):
        yield from self.select_xsd_nodes(context, name)
        return

    if name[0] == '{' or not self.parser.default_namespace:
        tag = name
    else:
        tag = '{%s}%s' % (self.parser.default_namespace, name)

    # With an ElementTree context checks if the token is bound to an XSD type. If not
    # try a match using the element path. If this match fails the xsd_type attribute
    # is set with the schema object to prevent other checks until the schema change.
    if self.xsd_types is self.parser.schema:

        # Untyped selection
        for item in context.iter_children_or_self():
            if match_attribute_node(item, name) or match_element_node(item, tag):
                yield item

    elif self.xsd_types is None or isinstance(self.xsd_types, AbstractSchemaProxy):

        # Try to match the type using the item's path
        for item in context.iter_children_or_self():
            if match_attribute_node(item, name) or match_element_node(item, tag):
                if isinstance(item, (TypedAttribute, TypedElement)):
                    yield item
                else:
                    path = context.get_path(item)

                    xsd_node = self.parser.schema.find(path, self.parser.namespaces)
                    if xsd_node is not None:
                        self.xsd_types = {tag: xsd_node.type}
                    else:
                        self.xsd_types = self.parser.schema

                    context.item = self.get_typed_node(item)
                    yield context.item
    else:
        # XSD typed selection
        for item in context.iter_children_or_self():
            if match_attribute_node(item, name) or match_element_node(item, tag):
                if isinstance(item, (TypedAttribute, TypedElement)):
                    yield item
                else:
                    context.item = self.get_typed_node(item)
                    yield context.item


###
# Namespace prefix reference
@method(':', bp=95)
def led_namespace_prefix(self, left):
    if self.parser.version == '1.0':
        left.expected('(name)')
    else:
        left.expected('(name)', '*')

    if not self.parser.next_token.label.endswith('function'):
        self.parser.expected_name('(name)', '*')
    if self.parser.is_spaced():
        raise self.wrong_syntax("a QName cannot contains spaces before or after ':'")

    if left.symbol == '(name)':
        try:
            namespace = self.get_namespace(left.value)
        except ElementPathKeyError:
            self.parser.advance()  # Assure there isn't a following incomplete comment
            self[:] = left, self.parser.token
            msg = "prefix {!r} is not declared".format(left.value)
            raise self.error('XPST0081', msg) from None
        else:
            self.parser.next_token.bind_namespace(namespace)
    elif self.parser.next_token.symbol != '(name)':
        raise self.wrong_syntax()

    self[:] = left, self.parser.expression(90)
    self.value = '{}:{}'.format(self[0].value, self[1].value)

    if self.parser.next_token.symbol == ':':
        raise self.wrong_syntax()

    return self


@method(':')
def evaluate_namespace_prefix(self, context=None):
    if self[1].label.endswith('function'):
        return self[1].evaluate(context)
    return [x for x in self.select(context)]


@method(':')
def select_namespace_prefix(self, context=None):
    if self[1].label.endswith('function'):
        value = self[1].evaluate(context)
        if isinstance(value, list):
            yield from value
        elif value is not None:
            yield value
        return

    if self[0].value == '*':
        name = '*:%s' % self[1].value
    else:
        name = '{%s}%s' % (self.get_namespace(self[0].value), self[1].value)

    if context is None:
        yield name
    elif isinstance(context, XPathSchemaContext):
        yield from self.select_xsd_nodes(context, name)

    elif self.xsd_types is self.parser.schema:
        for item in context.iter_children_or_self():
            if match_attribute_node(item, name) or match_element_node(item, name):
                yield item

    elif self.xsd_types is None or isinstance(self.xsd_types, AbstractSchemaProxy):
        for item in context.iter_children_or_self():
            if match_attribute_node(item, name) or match_element_node(item, name):
                if isinstance(item, (TypedAttribute, TypedElement)):
                    yield item
                else:
                    path = context.get_path(item)
                    xsd_node = self.parser.schema.find(path, self.parser.namespaces)
                    if xsd_node is not None:
                        self.add_xsd_type(xsd_node)
                    else:
                        self.xsd_types = self.parser.schema

                    context.item = self.get_typed_node(item)
                    yield context.item

    else:
        # XSD typed selection
        for item in context.iter_children_or_self():
            if match_attribute_node(item, name) or match_element_node(item, name):
                if isinstance(item, (TypedAttribute, TypedElement)):
                    yield item
                else:
                    context.item = self.get_typed_node(item)
                    yield context.item


###
# Namespace URI as in ElementPath
@method('{', bp=95)
def nud_namespace_uri(self):
    if self.parser.strict and self.symbol == '{':
        raise self.wrong_syntax("not allowed symbol if parser has strict=True")

    namespace = self.parser.next_token.value + self.parser.advance_until('}')
    self.parser.advance()
    if not self.parser.next_token.label.endswith('function'):
        self.parser.expected_name('(name)', '*')
    self.parser.next_token.bind_namespace(namespace)

    self[:] = self.parser.symbol_table['(string)'](self.parser, namespace), \
        self.parser.expression(90)

    if self[1].value is None:
        self.value = None
    else:
        self.value = '{%s}%s' % (self[0].value, self[1].value)
    return self


@method('{')
def evaluate_namespace_uri(self, context=None):
    if self[1].label.endswith('function'):
        return self[1].evaluate(context)
    return [x for x in self.select(context)]


@method('{')
def select_namespace_uri(self, context=None):
    if self[1].label.endswith('function'):
        yield self[1].evaluate(context)
        return
    elif context is None:
        raise self.missing_context()

    if isinstance(context, XPathSchemaContext):
        yield from self.select_xsd_nodes(context, self.value)

    elif self.xsd_types is None:
        for item in context.iter_children_or_self():
            if match_attribute_node(item, self.value):
                yield item
            elif match_element_node(item, self.value):
                yield item
    else:
        # XSD typed selection
        for item in context.iter_children_or_self():
            if match_attribute_node(item, self.value) or match_element_node(item, self.value):
                if isinstance(item, (TypedAttribute, TypedElement)):
                    yield item
                else:
                    context.item = self.get_typed_node(item)
                    yield context.item


###
# Variables
@method('$', bp=90)
def nud_variable_reference(self):
    self.parser.expected_name('(name)')
    self[:] = self.parser.expression(rbp=90),
    if ':' in self[0].value:
        raise self[0].wrong_syntax("variable reference requires a simple reference name")
    return self


@method('$')
def evaluate_variable_reference(self, context=None):
    if context is None:
        raise self.missing_context()

    try:
        return context.variables[self[0].value]
    except KeyError as err:
        raise self.missing_name('unknown variable %r' % str(err)) from None


###
# Nullary operators (use only the context)
@method(nullary('*'))
def select_wildcard(self, context=None):
    if self:
        # Product operator
        item = self.evaluate(context)
        if item is not None:
            if context is not None:
                context.item = item
            yield item
    elif context is None:
        raise self.missing_context()

    # Wildcard literal
    elif isinstance(context, XPathSchemaContext):
        for item in context.iter_children_or_self():
            if item is not None:
                self.add_xsd_type(item)
                yield item

    elif self.xsd_types is None:
        for item in context.iter_children_or_self():
            if item is None:
                pass  # '*' wildcard doesn't match document nodes
            elif context.axis == 'attribute':
                if isinstance(item, (AttributeNode, TypedAttribute)):
                    yield item
            elif is_element_node(item):
                yield item

    else:
        # XSD typed selection
        for item in context.iter_children_or_self():
            if context.item is not None and context.is_principal_node_kind():
                if isinstance(item, (TypedAttribute, TypedElement)):
                    yield item
                else:
                    context.item = self.get_typed_node(item)
                    yield context.item


@method(nullary('.'))
def select_self_shortcut(self, context=None):
    if context is None:
        raise self.missing_context()

    elif isinstance(context, XPathSchemaContext):
        for item in context.iter_self():
            if is_schema_node(item):
                self.add_xsd_type(item)
            elif item is context.root:
                # item is the schema
                for xsd_element in item:
                    self.add_xsd_type(xsd_element)
            yield item

    elif self.xsd_types is None:
        for item in context.iter_self():
            if item is not None:
                yield item
            elif is_document_node(context.root):
                yield context.root

    else:
        for item in context.iter_self():
            if item is not None:
                if isinstance(item, (TypedAttribute, TypedElement)):
                    yield item
                else:
                    context.item = self.get_typed_node(item)
                    yield context.item
            elif is_document_node(context.root):
                yield context.root


@method(nullary('..'))
def select_parent_shortcut(self, context=None):
    if context is None:
        raise self.missing_context()
    else:
        parent = context.get_parent(context.item)
        if is_element_node(parent):
            context.item = parent
            yield parent


###
# Logical Operators
@method(infix('or', bp=20))
def evaluate_or_operator(self, context=None):
    return self.boolean_value(self[0].evaluate(copy(context))) or \
        self.boolean_value(self[1].evaluate(copy(context)))


@method(infix('and', bp=25))
def evaluate_and_operator(self, context=None):
    return self.boolean_value(self[0].evaluate(copy(context))) and \
        self.boolean_value(self[1].evaluate(copy(context)))


###
# Comparison operators
@method('=', bp=30)
@method('!=', bp=30)
@method('<', bp=30)
@method('>', bp=30)
@method('<=', bp=30)
@method('>=', bp=30)
def led_comparison_operators(self, left):
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
def evaluate_comparison_operators(self, context=None):
    op = OPERATORS_MAP[self.symbol]
    try:
        return any(op(x1, x2) for x1, x2 in self.iter_comparison_data(context))
    except TypeError as err:
        raise self.error('XPTY0004', err) from None
    except ValueError as err:
        raise self.error('FORG0001', err) from None


###
# Numerical operators
@method(infix('+', bp=40))
def evaluate_plus_operator(self, context=None):
    if len(self) == 1:
        arg = self.get_argument(context, cls=NumericProxy)
        if arg is not None:
            return +arg
    else:
        op1, op2 = self.get_operands(context, cls=ArithmeticProxy)
        if op1 is not None:
            try:
                return op1 + op2
            except TypeError as err:
                raise self.error('XPTY0004', err) from None
            except OverflowError as err:
                if isinstance(op1, AbstractDateTime):
                    raise self.error('FODT0001', err) from None
                elif isinstance(op1, Duration):
                    raise self.error('FODT0002', err) from None
                else:
                    raise self.error('FOAR0002', err) from None


@method(infix('-', bp=40))
def evaluate_minus_operator(self, context=None):
    if len(self) == 1:
        arg = self.get_argument(context, cls=NumericProxy)
        if arg is not None:
            return -arg
    else:
        op1, op2 = self.get_operands(context, cls=ArithmeticProxy)
        if op1 is not None:
            try:
                return op1 - op2
            except TypeError as err:
                raise self.error('XPTY0004', err) from None
            except OverflowError as err:
                if isinstance(op1, AbstractDateTime):
                    raise self.error('FODT0001', err) from None
                elif isinstance(op1, Duration):
                    raise self.error('FODT0002', err) from None
                else:
                    raise self.error('FOAR0002', err) from None


@method('+')
@method('-')
def nud_plus_minus_operators(self):
    self[:] = self.parser.expression(rbp=70),
    return self


@method(infix('*', bp=45))
def evaluate_multiply_operator(self, context=None):
    if self:
        op1, op2 = self.get_operands(context, cls=ArithmeticProxy)
        if op1 is not None:
            try:
                if isinstance(op2, (YearMonthDuration, DayTimeDuration)):
                    return op2 * op1
                return op1 * op2
            except TypeError as err:
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
                raise self.error('FOCA0005', err) from None
            except OverflowError as err:
                if isinstance(op1, AbstractDateTime):
                    raise self.error('FODT0001', err) from None
                elif isinstance(op1, Duration):
                    raise self.error('FODT0002', err) from None
                else:
                    raise self.error('FOAR0002', err) from None
    else:
        # This is not a multiplication operator but a wildcard select statement
        return [x for x in self.select(context)]


@method(infix('div', bp=45))
def evaluate_div_operator(self, context=None):
    dividend, divisor = self.get_operands(context, cls=ArithmeticProxy)
    if dividend is None:
        return
    elif divisor != 0:
        try:
            if isinstance(dividend, int) and isinstance(divisor, int):
                return decimal.Decimal(dividend) / decimal.Decimal(divisor)
            return dividend / divisor
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
        return float('nan')
    elif dividend > 0:
        return float('-inf') if str(divisor).startswith('-') else float('inf')
    else:
        return float('inf') if str(divisor).startswith('-') else float('-inf')


@method(infix('mod', bp=45))
def evaluate_mod_operator(self, context=None):
    op1, op2 = self.get_operands(context, cls=NumericProxy)
    if op1 is not None:
        if op2 == 0 and isinstance(op2, float):
            return float('nan')
        elif math.isinf(op2) and not math.isinf(op1) and op1 != 0:
            return op1 if self.parser.version != '1.0' else float('nan')

        try:
            if isinstance(op1, int) and isinstance(op2, int):
                return op1 % op2 if op1 * op2 >= 0 else -(abs(op1) % op2)
            return op1 % op2
        except TypeError as err:
            raise self.error('FORG0006', err) from None
        except (ZeroDivisionError, decimal.InvalidOperation):
            raise self.error('FOAR0001') from None


# Resolve the intrinsic ambiguity of some infix operators
@method('or')
@method('and')
@method('div')
@method('mod')
def nud_logical_div_mod_operators(self):
    token = self.parser.symbol_table['(name)'](self.parser, self.symbol)
    return token.nud()


###
# Union expressions
@method('|', bp=50)
def led_union_operator(self, left):
    self.cut_and_sort = True
    if left.symbol in {'|', 'union'}:
        left.cut_and_sort = False
    self[:] = left, self.parser.expression(rbp=50)
    return self


@method('|')
def select_union_operator(self, context=None):
    if context is None:
        raise self.missing_context()

    results = {item for k in range(2) for item in self[k].select(copy(context))}
    if any(not is_xpath_node(x) for x in results):
        raise self.error('XPTY0004', 'only XPath nodes are allowed')
    elif not self.cut_and_sort:
        yield from results
    else:
        yield from context.iter_results(results)


###
# Path expressions
@method('//', bp=75)
def nud_descendant_path(self):
    if self.parser.next_token.label not in self.parser.PATH_STEP_LABELS:
        self.parser.expected_name(*self.parser.PATH_STEP_SYMBOLS)

    self[:] = self.parser.expression(75),
    return self


@method('/', bp=75)
def nud_child_path(self):
    if self.parser.next_token.label not in self.parser.PATH_STEP_LABELS:
        try:
            self.parser.expected_name(*self.parser.PATH_STEP_SYMBOLS)
        except SyntaxError:
            return self

    self[:] = self.parser.expression(75),
    return self


@method('//')
@method('/')
def led_child_or_descendant_path(self, left):
    if self.parser.next_token.label not in self.parser.PATH_STEP_LABELS:
        self.parser.expected_name(*self.parser.PATH_STEP_SYMBOLS)

    self[:] = left, self.parser.expression(75)
    return self


@method('/')
def select_child_path(self, context=None):
    """
    Child path expression. Selects child:: axis as default (when bind to '*' or '(name)').
    """
    if context is None:
        raise self.missing_context()
    elif not self:
        if is_document_node(context.root):
            yield context.root
    elif len(self) == 1:
        if is_document_node(context.root) or context.item is context.root:
            if not isinstance(context, XPathSchemaContext):
                context.item = None
            yield from self[0].select(context)
    else:
        items = set()
        for _ in context.inner_focus_select(self[0]):
            if not is_xpath_node(context.item):
                raise self.error('XPTY0019')

            for result in self[1].select(context):
                if not isinstance(result, (tuple, XPathNode)) and not hasattr(result, 'tag'):
                    yield result
                elif result in items:
                    pass
                elif isinstance(result, TypedElement):
                    if result.elem not in items:
                        items.add(result)
                        yield result
                elif isinstance(result, TypedAttribute):
                    if result.attribute not in items:
                        items.add(result)
                        yield result
                else:
                    items.add(result)
                    yield result
                    if isinstance(context, XPathSchemaContext):
                        self[1].add_xsd_type(result)


@method('//')
def select_descendant_path(self, context=None):
    # Note: // is short for /descendant-or-self::node()/, so the axis
    #   is left to None. Use descendant:: only if next-step uses child
    #   axis, to preserve document order.
    if context is None:
        raise self.missing_context()
    elif len(self) == 2:
        _axis = 'descendant' if self[1].child_axis else None

        for context.item in self[0].select(context):
            if not is_xpath_node(context.item):
                raise self.error('XPTY0019')

            for _ in context.iter_descendants(axis=_axis, inner_focus=True):
                yield from self[1].select(context)

    elif is_document_node(context.root) or context.item is context.root:
        context.item = None
        _axis = 'descendant' if self[0].child_axis else None

        for _ in context.iter_descendants(axis=_axis, inner_focus=True):
            yield from self[0].select(context)


###
# Predicate filters
@method('[', bp=80)
def led_predicate(self, left):
    self[:] = left, self.parser.expression()
    self.parser.advance(']')
    return self


@method('[')
def select_predicate(self, context=None):
    if context is None:
        raise self.missing_context()

    for _ in context.inner_focus_select(self[0]):
        if (self[1].label in ('axis', 'kind test') or self[1].symbol == '..') \
                and not is_xpath_node(context.item):
            raise self.error('XPTY0020')

        predicate = [x for x in self[1].select(copy(context))]
        if len(predicate) == 1 and isinstance(predicate[0], NumericProxy):
            if context.position == predicate[0]:
                yield context.item
        elif self.boolean_value(predicate):
            yield context.item


###
# Parenthesized expressions
@method('(', bp=100)
def nud_parenthesized_expr(self):
    self[:] = self.parser.expression(),
    self.parser.advance(')')
    return self


@method('(')
def evaluate_parenthesized_expr(self, context=None):
    return self[0].evaluate(context)


@method('(')
def select_parenthesized_expr(self, context=None):
    return self[0].select(context)
