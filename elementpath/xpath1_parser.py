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
from __future__ import division
import math
import decimal

from .compat import PY3, string_base_type
from .exceptions import ElementPathSyntaxError, ElementPathNameError, MissingContextError
from .datatypes import UntypedAtomic, DayTimeDuration, YearMonthDuration, \
    NumericTypeProxy, ArithmeticTypeProxy
from .xpath_context import XPathSchemaContext
from .tdop_parser import Parser, MultiLabel
from .namespaces import XML_ID, XML_LANG, XPATH_FUNCTIONS_NAMESPACE, \
    XSD_NAMESPACE, XML_NAMESPACE, qname_to_prefixed
from .schema_proxy import AbstractSchemaProxy
from .xpath_token import XPathToken
from .xpath_nodes import AttributeNode, NamespaceNode, TypedAttribute, TypedElement,\
    is_etree_element, is_xpath_node, is_element_node, is_document_node, is_attribute_node, \
    is_text_node, is_comment_node, is_processing_instruction_node, node_name


XML_NAME_CHARACTER = (u"A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF"
                      u"\u200C\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD")
XML_NCNAME_PATTERN = u"[{0}][-.0-9\u00B7\u0300-\u036F\u203F-\u2040{0}]*".format(XML_NAME_CHARACTER)


class XPath1Parser(Parser):
    """
    XPath 1.0 expression parser class. A parser instance represents also the XPath static context.
    With *variables* you can pass a dictionary with the static context's in-scope variables.
    Provide a *namespaces* dictionary argument for mapping namespace prefixes to URI inside
    expressions. If *strict* is set to `False` the parser enables also the parsing of QNames,
    like the ElementPath library.

    :param namespaces: A dictionary with mapping from namespace prefixes into URIs.
    :param variables: A dictionary with the static context's in-scope variables.
    :param strict: If strict mode is `False` the parser enables parsing of QNames \
    in extended format, like the Python's ElementPath library. Default is `True`.
    """
    token_base_class = XPathToken

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
    The default prefix-to-namespace associations of the XPath class. Those namespaces are updated
    in the instance with the ones passed with the *namespaces* argument.
    """

    # Labels and symbols admitted after a path step
    PATH_STEP_LABELS = ('axis', 'kind test')
    PATH_STEP_SYMBOLS = {
        '(integer)', '(string)', '(float)', '(decimal)', '(name)', '*', '@', '..', '.', '(', '{'
    }

    schema = None  # To simplify the schema bind checks in compatibility with XPath2Parser

    def __init__(self, namespaces=None, variables=None, strict=True, *args, **kwargs):
        super(XPath1Parser, self).__init__()
        self.namespaces = self.DEFAULT_NAMESPACES.copy()
        if namespaces is not None:
            self.namespaces.update(namespaces)
        self.variables = dict(variables if variables is not None else [])
        self.strict = strict

    @staticmethod
    def create_tokenizer(symbol_table, name_pattern=XML_NCNAME_PATTERN):
        return Parser.create_tokenizer(symbol_table, name_pattern)

    @property
    def version(self):
        """The XPath version string."""
        return '1.0'

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

    @classmethod
    def axis(cls, symbol, bp=80):
        """Register a token for a symbol that represents an XPath *axis*."""
        def nud_(self):
            self.parser.advance('::')
            self.parser.next_token.expected(
                '(name)', '*', 'text', 'node', 'document-node', 'comment', 'processing-instruction',
                'attribute', 'schema-attribute', 'element', 'schema-element'
            )
            self[:] = self.parser.expression(rbp=bp),
            return self

        axis_pattern_template = r'\b%s(?=\s*\:\:|\s*\(\:.*\:\)\s*\:\:)'
        try:
            pattern = axis_pattern_template % symbol.strip()
        except AttributeError:
            pattern = axis_pattern_template % getattr(symbol, 'symbol')
        return cls.register(symbol, pattern=pattern, label='axis', lbp=bp, rbp=bp, nud=nud_)

    @classmethod
    def function(cls, symbol, nargs=None, label='function', bp=90):
        """
        Registers a token class for a symbol that represents an XPath *callable* object.
        For default a callable labeled as *function* is registered but a different label
        can be provided.
        """
        def nud_(self):
            self.value = None
            self.parser.advance('(')
            if nargs is None:
                del self[:]
                while True:
                    self.append(self.parser.expression(5))
                    if self.parser.next_token.symbol != ',':
                        break
                    self.parser.advance(',')
                self.parser.advance(')')
                return self
            elif nargs == 0:
                self.parser.advance(')')
                return self
            elif isinstance(nargs, (tuple, list)):
                min_args, max_args = nargs
            else:
                min_args = max_args = nargs

            k = 0
            while k < min_args:
                if self.parser.next_token.symbol == ')':
                    msg = 'Too few arguments: expected at least %s arguments' % min_args
                    self.wrong_nargs(msg if min_args > 1 else msg[:-1])

                self[k:] = self.parser.expression(5),
                k += 1
                if k < min_args:
                    if self.parser.next_token.symbol == ')':
                        msg = 'Too few arguments: expected at least %s arguments' % min_args
                        self.wrong_nargs(msg if min_args > 1 else msg[:-1])
                    self.parser.advance(',')

            while k < max_args:
                if self.parser.next_token.symbol == ',':
                    self.parser.advance(',')
                    self[k:] = self.parser.expression(5),
                elif k == 0 and self.parser.next_token.symbol != ')':
                    self[k:] = self.parser.expression(5),
                else:
                    break
                k += 1

            if self.parser.next_token.symbol == ',':
                msg = 'Too many arguments: expected at most %s arguments' % max_args
                self.wrong_nargs(msg if max_args > 1 else msg[:-1])

            self.parser.advance(')')
            return self

        pattern = r'\b%s(?=\s*\(|\s*\(\:.*\:\)\()' % symbol
        return cls.register(symbol, pattern=pattern, label=label, lbp=bp, rbp=bp, nud=nud_)

    def parse(self, source):
        root_token = super(XPath1Parser, self).parse(source)
        try:
            root_token.evaluate()  # Static context evaluation
        except MissingContextError:
            pass
        return root_token


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
register(')')
register(']')
register('::')
register('}')


###
# Literals
literal('(string)')
literal('(float)')
literal('(decimal)')
literal('(integer)')


@method(literal('(name)', bp=10))
def evaluate(self, context=None):
    return [x for x in self.select(context)]


@method('(name)')
def select(self, context=None):
    if context is None:
        return

    name = self.value
    if isinstance(context, XPathSchemaContext):
        # Bind with the XSD type from a schema
        if name[0] != '{' and self.parser.default_namespace:
            name = '{%s}%s' % (self.parser.default_namespace, name)

        for schema_item in context.iter_children_or_self():
            if self.match_xsd_type(schema_item, name) is not None:
                yield self.get_typed_node(context, schema_item)
        return

    if name[0] != '{' and self.parser.default_namespace:
        tag = '{%s}%s' % (self.parser.default_namespace, name)
    else:
        tag = name

    # Checks if the token is bound to an XSD type. If not try a match using
    # the element path. If this match fails the xsd_type attribute is set
    # with the schema object to prevent other checks until the schema change.
    if self.xsd_type is self.parser.schema:

        # Untyped selection
        for item in context.iter_children_or_self():
            if is_attribute_node(item, name):
                yield item
            elif is_element_node(item, tag):
                yield item

    elif self.xsd_type is None or isinstance(self.xsd_type, AbstractSchemaProxy):

        # Try to match the type using the path
        for item in context.iter_children_or_self():
            if is_attribute_node(item, name) or is_element_node(item, tag):
                path = context.get_path(item)

                xsd_component = self.parser.schema.find(path, self.parser.namespaces)
                if xsd_component is not None:
                    self.xsd_type = xsd_component.type
                else:
                    self.xsd_type = self.parser.schema

                yield self.get_typed_node(context, item)
    else:
        # XSD typed selection
        for item in context.iter_children_or_self():
            if is_attribute_node(item, name) or is_element_node(item, tag):
                yield self.get_typed_node(context, item)


###
# Namespace prefix reference
@method(':', bp=95)
def led(self, left):
    if self.parser.version == '1.0':
        left.expected('(name)')
    else:
        left.expected('(name)', '*')

    next_token = self.parser.next_token
    if left.symbol == '(name)':
        try:
            namespace = self.parser.namespaces[left.value]
        except KeyError as err:
            raise self.error('FONS0004', 'No namespace found for prefix %s' % str(err))

        if next_token.symbol not in ('(name)', '*') and next_token.label not in ('function', 'constructor'):
            next_token.wrong_syntax()
        elif namespace == XPATH_FUNCTIONS_NAMESPACE:
            if next_token.label != 'function':
                next_token.wrong_syntax("An XPath function is expected.")
            elif isinstance(next_token.label, MultiLabel):
                next_token.label = 'function'
        elif namespace == XSD_NAMESPACE:
            if next_token.symbol not in ('(name)', '*') and next_token.label != 'constructor':
                next_token.wrong_syntax("An XSD element or a constructor function is expected.")
            elif isinstance(next_token.label, MultiLabel):
                next_token.label = 'constructor'

    elif left.symbol == '*' and next_token.symbol != '(name)':
        next_token.wrong_syntax()

    if self.parser.is_spaced():
        self.wrong_syntax("a QName cannot contains spaces before or after ':'")
    self[:] = left, self.parser.expression(90)
    return self


@method(':')
def evaluate(self, context=None):
    if self[0].value == '*':
        return
    try:
        namespace = self.parser.namespaces[self[0].value]
    except KeyError as err:
        raise self.error('FONS0004', 'No namespace found for prefix %s' % str(err))

    if namespace == XPATH_FUNCTIONS_NAMESPACE and self[1].label != 'function':
        self[1].wrong_value("Must be a function")
    elif namespace == XSD_NAMESPACE and self[1].symbol not in ('(name)', '*') and self[1].label != 'constructor':
        self[1].wrong_value("An XSD element or a constructor function is expected.")
    return self[1].evaluate(context)


@method(':')
def select(self, context=None):
    if self[1].label in ('function', 'constructor'):
        value = self[1].evaluate(context)
        if isinstance(value, list):
            for result in value:
                yield result
        else:
            yield value
        return
    elif self[0].value == '*':
        value = '*:%s' % self[1].value
    else:
        try:
            namespace = self.parser.namespaces[self[0].value]
        except KeyError as err:
            raise self.error('FONS0004', 'No namespace found for prefix %s' % str(err))
        else:
            value = '{%s}%s' % (namespace, self[1].value)

    if context is None:
        return
    elif isinstance(context, XPathSchemaContext):
        for schema_item in context.iter_children_or_self():
            if self.match_xsd_type(schema_item, value) is not None:
                yield self.get_typed_node(context, schema_item)

    elif self.xsd_type is self.parser.schema:
        for item in context.iter_children_or_self():
            if is_attribute_node(item, value):
                yield item
            elif is_element_node(item, value):
                yield item

    elif self.xsd_type is None or isinstance(self.xsd_type, AbstractSchemaProxy):
        for item in context.iter_children_or_self():
            if is_attribute_node(item, value) or is_element_node(item, value):
                path = context.get_path(item)
                xsd_component = self.parser.schema.find(path, self.parser.namespaces)
                if xsd_component is not None:
                    self.xsd_type = xsd_component.type
                else:
                    self.xsd_type = self.parser.schema
                yield self.get_typed_node(context, item)

    else:
        # XSD typed selection
        for item in context.iter_children_or_self():
            if is_attribute_node(item, value) or is_element_node(item, value):
                yield self.get_typed_node(context, item)


###
# Namespace URI as in ElementPath
@method('{', bp=95)
def nud(self):
    if self.parser.strict:
        self.unexpected()
    namespace = self.parser.next_token.value + self.parser.raw_advance('}')
    self.parser.advance()

    next_token = self.parser.next_token
    if next_token.symbol not in ('(name)', '*') and next_token.label != 'function':
        next_token.wrong_syntax()
    elif self.parser.next_token.label != 'function' and namespace == XPATH_FUNCTIONS_NAMESPACE:
        self.parser.next_token.wrong_syntax()
    self[:] = self.parser.symbol_table['(string)'](self.parser, namespace), self.parser.expression(90)
    return self


@method('{')
def evaluate(self, context=None):
    if self[1].label == 'function':
        return self[1].evaluate(context)
    else:
        return '{%s}%s' % (self[0].value, self[1].value)


@method('{')
def select(self, context=None):
    if self[1].label == 'function':
        value = self[1].evaluate(context)
        if isinstance(value, list):
            for result in value:
                yield result
        else:
            yield value
    elif context is not None:
        value = '{%s}%s' % (self[0].value, self[1].value)
        for item in context.iter_children_or_self():
            if is_attribute_node(item, value):
                yield item[1]
            elif is_element_node(item, value):
                yield item


###
# Variables
@method('$', bp=90)
def nud(self):
    self.parser.next_token.expected('(name)')
    self[:] = self.parser.expression(rbp=90),
    if self[0].value.startswith('{'):
        self[0].wrong_value("Variable reference requires a simple reference name")
    return self


@method('$')
def evaluate(self, context=None):
    varname = self[0].value
    if varname in self.parser.variables:
        return self.parser.variables[varname]
    elif context is None:
        return
    elif varname in context.variables:
        return context.variables[varname]
    elif isinstance(context, XPathSchemaContext):
        return
    else:
        raise ElementPathNameError('unknown variable', token=self)


###
# Nullary operators (use only the context)
@method(nullary('*'))
def select(self, context=None):
    if self:
        # Product operator
        item = self.evaluate(context)
        if context is not None:
            context.item = item
        yield item
    elif context is None:
        self.missing_context()
    else:
        # Wildcard literal
        for item in context.iter_children_or_self():
            if context.is_principal_node_kind():
                if is_attribute_node(item):
                    yield item[1]
                else:
                    yield item


@method(nullary('.'))
def select(self, context=None):
    if context is None:
        self.missing_context()
    elif context.item is not None:
        yield context.item
    elif is_document_node(context.root):
        yield context.root


@method(nullary('..'))
def select(self, context=None):
    if context is None:
        self.missing_context()
    else:
        parent = context.get_parent(context.item)
        if is_element_node(parent):
            context.item = parent
            yield parent


###
# Logical Operators
@method(infix('or', bp=20))
def evaluate(self, context=None):
    if context is None:
        return self.boolean_value(self[0].evaluate()) or self.boolean_value(self[1].evaluate())
    return self.boolean_value(self[0].evaluate(context.copy())) or \
        self.boolean_value(self[1].evaluate(context.copy()))


@method(infix('and', bp=25))
def evaluate(self, context=None):
    if context is None:
        return self.boolean_value(self[0].evaluate()) and self.boolean_value(self[1].evaluate())
    return self.boolean_value(self[0].evaluate(context.copy())) and \
        self.boolean_value(self[1].evaluate(context.copy()))


@method(infix('=', bp=30))
def evaluate(self, context=None):
    return any(op1 == op2 for op1, op2 in self.get_comparison_data(context))


@method(infix('!=', bp=30))
def evaluate(self, context=None):
    return any(op1 != op2 for op1, op2 in self.get_comparison_data(context))


@method(infix('<', bp=30))
def evaluate(self, context=None):
    return any(op1 < op2 for op1, op2 in self.get_comparison_data(context))


@method(infix('>', bp=30))
def evaluate(self, context=None):
    return any(op1 > op2 for op1, op2 in self.get_comparison_data(context))


@method(infix('<=', bp=30))
def evaluate(self, context=None):
    return any(op1 <= op2 for op1, op2 in self.get_comparison_data(context))


@method(infix('>=', bp=30))
def evaluate(self, context=None):
    return any(op1 >= op2 for op1, op2 in self.get_comparison_data(context))


###
# Numerical operators
prefix('+')
prefix('-', bp=90)


@method(infix('+', bp=40))
def evaluate(self, context=None):
    if not self:
        return
    elif len(self) == 1:
        arg = self.get_argument(context, cls=NumericTypeProxy)
        if arg is not None:
            try:
                return +arg
            except TypeError:
                raise self.wrong_type("numeric value is required: %r" % arg)
    else:
        op1, op2 = self.get_operands(context, cls=ArithmeticTypeProxy)
        if op1 is not None:
            try:
                return op1 + op2
            except TypeError as err:
                raise self.wrong_type(str(err))


@method(infix('-', bp=40))
def evaluate(self, context=None):
    if len(self) == 1:
        arg = self.get_argument(context, cls=NumericTypeProxy)
        if arg is not None:
            try:
                return -arg
            except TypeError:
                raise self.wrong_type("numeric value is required: %r" % arg)
    else:
        op1, op2 = self.get_operands(context, cls=ArithmeticTypeProxy)
        if op1 is not None:
            try:
                return op1 - op2
            except TypeError as err:
                raise self.wrong_type(str(err))


@method(infix('*', bp=45))
def evaluate(self, context=None):
    if self:
        op1, op2 = self.get_operands(context, cls=ArithmeticTypeProxy)
        if op1 is not None:
            try:
                return op1 * op2
            except TypeError as err:
                raise self.wrong_type(str(err))


@method(infix('div', bp=45))
def evaluate(self, context=None):
    dividend, divisor = self.get_operands(context, cls=ArithmeticTypeProxy)
    if dividend is None:
        return
    elif divisor != 0:
        try:
            return dividend / divisor
        except TypeError as err:
            raise self.wrong_type(str(err))
    elif dividend == 0:
        return float('nan')
    elif dividend > 0:
        return float('inf')
    else:
        return float('-inf')


@method(infix('mod', bp=45))
def evaluate(self, context=None):
    op1, op2 = self.get_operands(context, cls=NumericTypeProxy)
    if op1 is not None:
        try:
            return op1 % op2
        except TypeError as err:
            raise self.wrong_type(str(err))


###
# Union expressions
@method('|', bp=50)
def led(self, left):
    self.cut_and_sort = True
    if left.symbol in {'|', 'union'}:
        left.cut_and_sort = False
    self[:] = left, self.parser.expression(rbp=50)
    return self


@method('|')
def select(self, context=None):
    if context is None:
        return
    elif not self.cut_and_sort:
        for k in range(2):
            for item in self[k].select(context.copy()):
                yield item
    else:
        results = {item for k in range(2) for item in self[k].select(context.copy())}
        for item in context.iter_results(results):
            yield item


###
# Path expressions
@method('//', bp=75)
@method('/', bp=75)
def nud(self):
    next_token = self.parser.next_token
    if next_token.symbol == '(end)' and self.symbol == '/':
        return self
    elif next_token.symbol in self.parser.PATH_STEP_SYMBOLS:
        pass
    elif next_token.label not in self.parser.PATH_STEP_LABELS:
        next_token.wrong_syntax()

    self[:] = self.parser.expression(75),
    return self


@method('//')
@method('/')
def led(self, left):
    next_token = self.parser.next_token
    if next_token.symbol in self.parser.PATH_STEP_SYMBOLS:
        pass
    elif next_token.label not in self.parser.PATH_STEP_LABELS:
        next_token.wrong_syntax()

    self[:] = left, self.parser.expression(75)
    return self


@method('/')
def select(self, context=None):
    """
    Child path expression. Selects child:: axis as default (when bind to '*' or '(name)').
    """
    if context is None:
        return
    elif not self:
        if is_document_node(context.root):
            yield context.root
    elif len(self) == 1:
        context.item = None
        for result in self[0].select(context):
            yield result
    else:
        items = []
        left_results = [x for x in self[0].select(context)]
        context.size = len(left_results)
        for context.position, context.item in enumerate(left_results):
            if not is_xpath_node(context.item):
                self.wrong_type("left operand must returns XPath nodes: {}".format(context.item))
            for result in self[1].select(context):
                if not is_etree_element(result) and not isinstance(result, tuple):
                    yield result
                elif result in items:
                    pass
                elif isinstance(result, (TypedAttribute, TypedElement)):
                    if result[0] not in items:
                        items.append(result)
                        yield result
                elif isinstance(result, AttributeNode):
                    items.append(result)
                    yield result
                else:
                    items.append(result)
                    yield result


@method('//')
def select(self, context=None):
    if context is None:
        return
    elif len(self) == 1:
        context.item = None
        for _ in context.iter_descendants(axis='descendant-or-self'):
            for result in self[0].select(context):
                yield result
    else:
        for elem in self[0].select(context):
            if not is_element_node(elem):
                self.wrong_type("left operand must returns element nodes: %r" % elem)
            for _ in context.iter_descendants(item=elem):
                for result in self[1].select(context):
                    yield result


###
# Predicate filters
@method('[', bp=80)
def led(self, left):
    self.parser.next_token.unexpected(']')
    self[:] = left, self.parser.expression()
    self.parser.advance(']')
    return self


@method('[')
def select(self, context=None):
    if context is not None:
        for position, item in enumerate(self[0].select(context), start=1):
            predicate = [x for x in self[1].select(context.copy())]
            if len(predicate) == 1 and isinstance(predicate[0], NumericTypeProxy):
                if position == predicate[0]:
                    yield item
            elif self.boolean_value(predicate):
                yield item


###
# Parenthesized expressions
@method('(', bp=100)
def nud(self):
    self.parser.next_token.unexpected(')')
    self[:] = self.parser.expression(),
    self.parser.advance(')')
    return self  # Skip self!! (remove a redundant level from selection/evaluation)


@method('(')
def evaluate(self, context=None):
    return self[0].evaluate(context)


@method('(')
def select(self, context=None):
    return self[0].select(context)


###
# Forward Axes
@method(axis('self'))
def select(self, context=None):
    if context is not None:
        for _ in context.iter_self():
            for result in self[0].select(context):
                yield result


@method(axis('child'))
def select(self, context=None):
    if context is not None:
        for _ in context.iter_children_or_self(child_axis=True):
            for result in self[0].select(context):
                yield result


@method(axis('descendant'))
def select(self, context=None):
    if context is not None:
        item = context.item
        for _ in context.iter_descendants(axis=self.symbol):
            if item is not context.item:
                for result in self[0].select(context):
                    yield result


@method(axis('descendant-or-self'))
def select(self, context=None):
    if context is not None:
        for _ in context.iter_descendants(axis=self.symbol):
            for result in self[0].select(context):
                yield result


@method(axis('following-sibling'))
def select(self, context=None):
    if context is not None:
        if isinstance(context.item, TypedElement):
            item = context.item[0]
        elif is_etree_element(context.item):
            item = context.item
        else:
            return

        for parent in context.iter_parent(axis=self.symbol):
            if isinstance(context, XPathSchemaContext):
                for _ in context.iter_children_or_self(parent, child_axis=True):
                    for result in self[0].select(context):
                        yield result

            else:
                follows = False
                for child in context.iter_children_or_self(parent, child_axis=True):
                    if follows:
                        for result in self[0].select(context):
                            yield result
                    elif item is child:
                        follows = True


@method(axis('following'))
def select(self, context=None):
    if context is not None:
        descendants = set(context.iter_descendants(axis=self.symbol))
        item = context.item
        follows = False
        for elem in context.iter_descendants(item=context.root, axis=self.symbol):
            if follows:
                if elem not in descendants:
                    for result in self[0].select(context):
                        yield result
            elif item is elem:
                follows = True


@method('@', bp=80)
def nud(self):
    self[:] = self.parser.expression(rbp=80),
    if self[0].symbol not in ('*', '(name)', ':'):
        raise ElementPathSyntaxError("invalid attribute specification for XPath.")
    return self


@method('@')
@method(axis('attribute'))
def select(self, context=None):
    if context is None:
        self.missing_context()

    for _ in context.iter_attributes():
        for result in self[0].select(context):
            yield result


@method(axis('namespace'))
def select(self, context=None):
    if context is not None and is_element_node(context.item):
        elem = context.item
        namespaces = self.parser.namespaces

        for prefix_, uri in namespaces.items():
            context.item = NamespaceNode(prefix_, uri)
            yield context.item

        if hasattr(elem, 'nsmap'):
            # Maybe an lxml's Element: don't use parser namespaces for axis.
            for prefix_, uri in elem.nsmap.items():
                if prefix_ not in namespaces:
                    context.item = NamespaceNode(prefix_, uri)
                    yield context.item


###
# Reverse Axes
@method(axis('parent'))
def select(self, context=None):
    if context is not None:
        for _ in context.iter_parent(axis=self.symbol):
            for result in self[0].select(context):
                yield result


@method(axis('ancestor'))
def select(self, context=None):
    if context is not None:
        results = [
            item
            for _ in context.iter_ancestors(axis=self.symbol)
            for item in self[0].select(context)
        ]
        for result in reversed(results):
            context.item = result
            yield result


@method(axis('ancestor-or-self'))
def select(self, context=None):
    if context is not None:
        item = context.item
        for elem in reversed([x for x in context.iter_ancestors(axis=self.symbol)]):
            context.item = elem
            yield elem
        yield item


@method(axis('preceding-sibling'))
def select(self, context=None):
    if context is not None and is_element_node(context.item):
        item = context.item
        for parent in context.iter_parent(axis=self.symbol):
            for child in parent:
                if child is item:
                    break
                else:
                    context.item = child
                    for result in self[0].select(context):
                        yield result


@method(axis('preceding'))
def select(self, context=None):
    if context is not None and is_element_node(context.item):
        for _ in context.iter_preceding():
            for result in self[0].select(context):
                yield result


###
# Kind tests (for matching of node types in XPath 1.0 or sequence types in XPath 2.0)
@method(function('node', nargs=0, label='kind test'))
def select(self, context=None):
    if context is not None:
        for item in context.iter_children_or_self():
            if item is None:
                yield context.root
            elif is_xpath_node(item):
                yield item


@method(function('processing-instruction', nargs=(0, 1), label='kind test'))
def evaluate(self, context=None):
    if context and is_processing_instruction_node(context.item):
        return context.item


@method(function('comment', nargs=0, label='kind test'))
def evaluate(self, context=None):
    if context and is_comment_node(context.item):
        return context.item


@method(function('text', nargs=0, label='kind test'))
def select(self, context=None):
    if context is not None:
        for item in context.iter_children_or_self():
            if is_text_node(item):
                yield item


###
# Node set functions
@method(function('last', nargs=0))
def evaluate(self, context=None):
    return context.size if context is not None else 0


@method(function('position', nargs=0))
def evaluate(self, context=None):
    return context.position + 1 if context is not None else 0


@method(function('count', nargs=1))
def evaluate(self, context=None):
    return len([x for x in self[0].select(context)])


@method(function('id', nargs=1))
def select(self, context=None):
    if context is not None:
        value = self[0].evaluate(context)
        item = context.item
        if is_element_node(item):
            for elem in item.iter():
                if elem.get(XML_ID) == value:
                    yield elem


@method(function('name', nargs=(0, 1)))
@method(function('local-name', nargs=(0, 1)))
@method(function('namespace-uri', nargs=(0, 1)))
def evaluate(self, context=None):
    name = node_name(self.get_argument(context, default_to_context=True))
    if name is None:
        return ''

    symbol = self.symbol
    if symbol == 'name':
        return qname_to_prefixed(name, self.parser.namespaces)
    elif not name or name[0] != '{':
        return name if symbol == 'local-name' else ''
    elif symbol == 'local-name':
        return name.split('}')[1]
    elif symbol == 'namespace-uri':
        return name.split('}')[0][1:]


###
# String functions
@method(function('string', nargs=1))
def evaluate(self, context=None):
    return self.string_value(self.get_argument(context))


@method(function('contains', nargs=2))
def evaluate(self, context=None):
    arg1 = self.get_argument(context, default='', cls=string_base_type)
    arg2 = self.get_argument(context, index=1, default='', cls=string_base_type)
    return arg2 in arg1


@method(function('concat'))
def evaluate(self, context=None):
    return ''.join(self.string_value(self.get_argument(context, index=k))
                   for k in range(len(self)))


@method(function('string-length', nargs=(0, 1)))
def evaluate(self, context=None):
    return len(self.get_argument(context, default_to_context=True, default='', cls=string_base_type))


@method(function('normalize-space', nargs=(0, 1)))
def evaluate(self, context=None):
    if self.parser.version == '1.0':
        arg = self.string_value(self.get_argument(context, default_to_context=True, default=''))
    else:
        arg = self.get_argument(context, default_to_context=True, default='', cls=string_base_type)
    return ' '.join(arg.strip().split())


@method(function('starts-with', nargs=2))
def evaluate(self, context=None):
    arg1 = self.get_argument(context, default='', cls=string_base_type)
    arg2 = self.get_argument(context, index=1, default='', cls=string_base_type)
    return arg1.startswith(arg2)


@method(function('translate', nargs=3))
def evaluate(self, context=None):
    arg = self.get_argument(context, default='', cls=string_base_type)
    map_string = self.get_argument(context, index=1, default='', cls=string_base_type)
    trans_string = self.get_argument(context, index=2, default='', cls=string_base_type)

    if not PY3:
        import string
        maketrans = getattr(string, 'maketrans')
        arg = arg.encode('utf-8')
        map_string = map_string.encode('utf-8')
        trans_string = trans_string.encode('utf-8')
    else:
        maketrans = str.maketrans

    if len(map_string) == len(trans_string):
        return arg.translate(maketrans(map_string, trans_string))
    elif len(map_string) > len(trans_string):
        k = len(trans_string)
        if PY3:
            return arg.translate(maketrans(map_string[:k], trans_string, map_string[k:]))
        for c in map_string[k:]:
            arg = arg.replace(c, '')
        return arg.translate(maketrans(map_string[:k], trans_string))
    else:
        self.wrong_value("the third argument must have a length less or equal than the second")


@method(function('substring', nargs=(2, 3)))
def evaluate(self, context=None):
    item = self.get_argument(context, default='', cls=string_base_type)
    start = self.get_argument(context, index=1)
    try:
        if math.isnan(start) or math.isinf(start):
            return ''
    except TypeError:
        self.wrong_type("the second argument must be xs:numeric")
    else:
        start = int(round(start)) - 1

    if len(self) == 2:
        return '' if item is None else item[max(start, 0):]
    else:
        length = self.get_argument(context, index=2)
        try:
            if math.isnan(length) or length <= 0:
                return ''
        except TypeError:
            self.wrong_type("the third argument must be xs:numeric")

        if item is None:
            return ''
        elif math.isinf(length):
            return item[max(start, 0):]
        else:
            stop = start + int(round(length))
            return '' if item is None else item[slice(max(start, 0), max(stop, 0))]


@method(function('substring-before', nargs=2))
@method(function('substring-after', nargs=2))
def evaluate(self, context=None):
    arg1 = self.get_argument(context, default='', cls=string_base_type)
    arg2 = self.get_argument(context, index=1, default='', cls=string_base_type)
    if arg1 is None:
        return ''

    index = 0
    try:
        index = arg1.find(arg2)
    except AttributeError:
        self.wrong_type("the first argument must be a string")
    except TypeError:
        self.wrong_type("the second argument must be a string")

    if self.symbol == 'substring-before':
        return arg1[:index]
    else:
        return arg1[index + len(arg2):]


###
# Boolean functions
@method(function('boolean', nargs=1))
def evaluate(self, context=None):
    return self.boolean_value(self[0].get_results(context))


@method(function('not', nargs=1))
def evaluate(self, context=None):
    return not self.boolean_value(self[0].get_results(context))


@method(function('true', nargs=0))
def evaluate(self, context=None):
    return True


@method(function('false', nargs=0))
def evaluate(self, context=None):
    return False


@method(function('lang', nargs=1))
def evaluate(self, context=None):
    if context is None:
        return
    elif not is_element_node(context.item):
        return False
    else:
        try:
            lang = context.item.attrib[XML_LANG].strip()
        except KeyError:
            for elem in context.iter_ancestor():
                if XML_LANG in elem.attrib:
                    lang = elem.attrib[XML_LANG]
                    break
            else:
                return False

        if '-' in lang:
            lang, _ = lang.split('-')
        return lang.lower() == self[0].evaluate().lower()


###
# Number functions
@method(function('number', nargs=(0, 1)))
def evaluate(self, context=None):
    arg = self.get_argument(context, default_to_context=True)
    try:
        return float(self.string_value(arg) if is_xpath_node(arg) else arg)
    except (TypeError, ValueError):
        return float('nan')


@method(function('sum', nargs=(1, 2)))
def evaluate(self, context=None):
    values = [self.number_value(x) if isinstance(x, UntypedAtomic) else x
              for x in self[0].select(context)]
    if not values:
        zero = 0 if len(self) == 1 else self.get_argument(context, index=1)
        return [] if zero is None else zero
    elif any(isinstance(x, float) and math.isnan(x) for x in values):
        return float('nan')

    if any(isinstance(x, DayTimeDuration) for x in values) or \
            all(isinstance(x, YearMonthDuration) for x in values):
        return sum(values)

    try:
        return sum(self.number_value(x) for x in values)
    except TypeError:
        if self.parser.version == '1.0':
            return float('nan')
        raise self.error('FORG0006')


@method(function('ceiling', nargs=1))
@method(function('floor', nargs=1))
def evaluate(self, context=None):
    arg = self.get_argument(context)
    if arg is None:
        return float('nan') if self.parser.version == '1.0' else []
    elif is_xpath_node(arg) or self.parser.compatibility_mode:
        arg = self.number_value(arg)

    if isinstance(arg, float) and (math.isnan(arg) or math.isinf(arg)):
        return arg

    try:
        return math.floor(arg) if self.symbol == 'floor' else math.ceil(arg)
    except TypeError as err:
        self.wrong_type(str(err))


@method(function('round', nargs=1))
def evaluate(self, context=None):
    arg = self.get_argument(context)
    if arg is None:
        return float('nan') if self.parser.version == '1.0' else []
    elif is_xpath_node(arg) or self.parser.compatibility_mode:
        arg = self.number_value(arg)

    if isinstance(arg, float) and (math.isnan(arg) or math.isinf(arg)):
        return arg

    try:
        number = decimal.Decimal(arg)
        if number > 0:
            return float(number.quantize(decimal.Decimal('1'), rounding='ROUND_HALF_UP'))
        elif PY3:
            return float(round(number))
        else:
            return float(number.quantize(decimal.Decimal('1'), rounding='ROUND_HALF_DOWN'))
    except TypeError as err:
        self.wrong_type(str(err))
    except decimal.DecimalException as err:
        self.wrong_value(str(err))


register('(end)')
XPath1Parser.build()
