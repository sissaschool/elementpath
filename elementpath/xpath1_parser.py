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
from __future__ import division
import math
import decimal

from .compat import PY3
from .exceptions import (
    ElementPathSyntaxError, ElementPathTypeError, ElementPathValueError, ElementPathMissingContextError
)
from .tdop_parser import Parser
from .namespaces import (
    XML_ID_QNAME, XML_LANG_QNAME, XPATH_1_DEFAULT_NAMESPACES, XPATH_FUNCTIONS_NAMESPACE, qname_to_prefixed
)
from .xpath_token import XPathToken
from .xpath_helpers import (
    NamespaceNode, is_etree_element, is_xpath_node, is_element_node, is_document_node,
    is_attribute_node, is_text_node, is_comment_node, is_processing_instruction_node,
    node_name, node_string_value, boolean_value, data_value, string_value
)

XML_NAME_CHARACTER = (u"A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF"
                      u"\u200C\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD")
XML_NCNAME_PATTERN = u"[{0}][\-.0-9\u00B7\u0300-\u036F\u203F-\u2040{0}]*".format(XML_NAME_CHARACTER)


class XPath1Parser(Parser):
    """
    XPath 1.0 expression parser class. The parser instance represents also the XPath static context.

    :param namespaces: A dictionary with mapping from namespace prefixes into URIs.
    :param variables: A dictionary with the static context's in-scope variables.
    :param strict: If strict mode is `False` the parser enables parsing of QNames, \
    like the ElementPath library. Default is `True`.
    """
    token_base_class = XPathToken
    symbol_table = {k: v for k, v in Parser.symbol_table.items()}
    compatibility_mode = True

    SYMBOLS = {
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

    DEFAULT_NAMESPACES = XPATH_1_DEFAULT_NAMESPACES

    def __init__(self, namespaces=None, variables=None, strict=True, *args, **kwargs):
        super(XPath1Parser, self).__init__()
        self.namespaces = self.DEFAULT_NAMESPACES.copy()
        if namespaces is not None:
            self.namespaces.update(namespaces)
        self.variables = dict(variables if variables is not None else [])
        self.strict = strict

    @property
    def version(self):
        return '1.0'

    @classmethod
    def end(cls):
        cls.register('(end)')
        cls.build_tokenizer(name_pattern=r'(?:\{[^}]+\})?' + XML_NCNAME_PATTERN)

    @classmethod
    def alias(cls, symbol, other):
        token_class = super(XPath1Parser, cls).alias(symbol, other)
        token_class.select = cls.symbol_table[other].select
        return token_class

    @classmethod
    def axis(cls, symbol, bp=0):
        def nud_(self): 
            self.parser.advance('::')
            self.parser.next_token.expected(
                '(name)', '*', 'text', 'node', 'document-node', 'comment', 'processing-instruction',
                'attribute', 'schema-attribute', 'element', 'schema-element'
            )
            self[:] = self.parser.expression(rbp=bp),
            return self

        axis_pattern_template = '\\b%s(?=\s*\\:\\:|\s*\\(\\:.*\\:\\)\s*\\:\\:)'
        try:
            pattern = axis_pattern_template % symbol.strip()
        except AttributeError:
            pattern = axis_pattern_template % getattr(symbol, 'symbol')
        return cls.register(symbol, pattern=pattern, label='axis', lbp=bp, rbp=bp, nud=nud_)

    @classmethod
    def function(cls, symbol, nargs=None, bp=0):
        def nud_(self):
            self.parser.advance('(')
            if nargs is None:
                del self[:]
                while True:
                    self.append(self.parser.expression(5))
                    if self.parser.next_token.symbol != ',':
                        break
                    self.parser.advance(',')
                self.parser.advance(')')
                self.value = self.evaluate()
                return self
            elif nargs == 0:
                self.parser.advance(')')
                self.value = self.evaluate()
                return self
            elif isinstance(nargs, (tuple, list)):
                min_args, max_args = nargs
            else:
                min_args = max_args = nargs

            k = 0
            while k < min_args:
                self[k:] = self.parser.expression(5),
                k += 1
                if k < min_args:
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
            self.parser.advance(')')

            try:
                self.value = self.evaluate()  # Static context evaluation
            except ElementPathMissingContextError:
                self.value = None

            return self

        function_pattern_template = '\\b%s(?=\s*\\(|\s*\\(\\:.*\\:\\)\\()'
        try:
            pattern = function_pattern_template % symbol.strip()
        except AttributeError:
            pattern = function_pattern_template % getattr(symbol, 'symbol')
        return cls.register(symbol, pattern=pattern, label='function', lbp=bp, rbp=bp, nud=nud_)

    def next_is_path_step_token(self):
        return self.next_token.label in 'axis' or self.next_token.symbol in {
            '(integer)', '(string)', '(float)',  '(decimal)', '(name)', 'node', 'text', '*',
            '@', '..', '.', '(', '/', '{'
        }


##
# XPath1 definitions
XPath1Parser.begin()

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
literal('(unexpected)')
literal('(string)')
literal('(float)')
literal('(decimal)')
literal('(integer)')
literal('(name)', bp=10)


@method('(name)')
def evaluate(self, context=None):
    if context is None:
        return None
    elif is_element_node(context.item, self.value) or is_attribute_node(context.item, self.value):
        return context.item


@method('(name)')
def select(self, context=None):
    if context is not None:
        value = self.value
        for item in context.iter_children_or_self():
            if is_attribute_node(item, value):
                yield item[1]
            elif is_element_node(item, value):
                yield item


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
        if next_token.symbol not in ('(name)', '*') and next_token.label != 'function':
            next_token.wrong_syntax()
        try:
            namespace = self.parser.namespaces[left.value]
        except KeyError:
            raise ElementPathValueError("prefix %r not found in namespace map" % left.value)
        if next_token.label != 'function' and namespace == XPATH_FUNCTIONS_NAMESPACE:
            next_token.wrong_syntax()
    elif left.symbol == '*' and next_token.symbol != '(name)':
        next_token.wrong_syntax()

    self[:] = left, self.parser.expression(90)
    return self


@method(':')
def evaluate(self, context=None):
    if self[0].value == '*':
        return
    try:
        namespace = self.parser.namespaces[self[0].value]
    except KeyError:
        raise ElementPathValueError("prefix %r not found in namespace map" % self[0].value)

    if namespace == XPATH_FUNCTIONS_NAMESPACE and self[1].label != 'function':
        self[1].wrong_value("must be a function")
    return self[1].evaluate(context)


@method(':')
def select(self, context=None):
    if self[1].label == 'function':
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
        except KeyError:
            raise ElementPathValueError("prefix %r not found in namespace map" % self[0].value)
        else:
            value = '{%s}%s' % (namespace, self[1].value)

    if context is not None:
        for item in context.iter_children_or_self():
            if is_attribute_node(item, value):
                yield item[1]
            elif is_element_node(item, value):
                yield item


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
        return None
    elif varname in context.variables:
        return context.variables[varname]
    else:
        self.wrong_name('unknown variable')


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
    elif context is not None:
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
        return
    elif context.item is not None:
        yield context.item
    elif is_document_node(context.root):
        yield context.root


@method(nullary('..'))
def select(self, context=None):
    if context is not None:
        try:
            parent = context.parent_map[context.item]
        except KeyError:
            pass
        else:
            if is_element_node(parent):
                context.item = parent
                yield parent


###
# Logical Operators
@method(infix('or', bp=20))
def evaluate(self, context=None):
    return bool(self[0].evaluate(context) or self[1].evaluate(context))


@method(infix('and', bp=25))
def evaluate(self, context=None):
    return bool(self[0].evaluate(context) and self[1].evaluate(context))


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
        try:
            return +self[0].evaluate(context)
        except TypeError:
            raise ElementPathTypeError("numeric values are required: %r." % self[:])
    else:
        try:
            return self[0].evaluate(context) + self[1].evaluate(context)
        except TypeError:
            raise ElementPathTypeError("a numeric value is required: %r." % self[0])


@method(infix('-', bp=40))
def evaluate(self, context=None):
    try:
        try:
            return self[0].evaluate(context) - self[1].evaluate(context)
        except TypeError:
            self.wrong_type("values must be numeric: %r" % [tk.evaluate(context) for tk in self])
    except IndexError:
        try:
            return -self[0].evaluate(context)
        except TypeError:
            self.wrong_type("value must be numeric: %r" % self[0].evaluate(context))


@method(infix('*', bp=45))
def evaluate(self, context=None):
    if self:
        return self[0].evaluate(context) * self[1].evaluate(context)


@method(infix('div', bp=45))
def evaluate(self, context=None):
    return self[0].evaluate(context) / self[1].evaluate(context)


@method(infix('mod', bp=45))
def evaluate(self, context=None):
    return self[0].evaluate(context) % self[1].evaluate(context)


###
# Union expressions
@method(infix('|', bp=50))
def select(self, context=None):
    if context is not None:
        results = {item for k in range(2) for item in self[k].select(context.copy())}
        for item in context.iter():
            if item in results:
                yield item


###
# Path expressions
@method('//', bp=80)
@method('/', bp=80)
def nud(self):
    next_token = self.parser.next_token
    if next_token.symbol == '(end)' and self.symbol == '/':
        return self
    elif not self.parser.next_is_path_step_token():
        next_token.wrong_syntax()
    self[:] = self.parser.expression(80),
    return self


@method('//', bp=80)
@method('/', bp=80)
def led(self, left):
    if not self.parser.next_is_path_step_token():
        self.parser.next_token.wrong_syntax()
    self[:] = left, self.parser.expression(80)
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
        items = set()
        left_results = list(self[0].select(context))
        context.size = len(left_results)
        for context.position, context.item in enumerate(left_results):
            if not is_element_node(context.item):
                self.wrong_type("left operand must returns element nodes: %r" % context.item)
            for result in self[1].select(context):
                if is_etree_element(result) or isinstance(result, tuple):
                    if result not in items:
                        yield result
                        items.add(result)
                else:
                    yield result


@method('/')
def evaluate(self, context=None):
    """
    General evaluation method for path operators, that may returns the a single value or None.
    """
    if context is not None:
        selector = iter(self.select(context))
        try:
            value = next(selector)
        except StopIteration:
            return
        else:
            try:
                next(selector)
            except StopIteration:
                return data_value(value)
            else:
                self.wrong_context_type("atomized operand is a sequence of length greater than one")


@method('//')
def select(self, context=None):
    if context is None:
        return
    elif len(self) == 1:
        for _ in context.iter_descendants(axis='descendant-or-self'):
            for result in self[0].select(context):
                yield result
    else:
        for elem in self[0].select(context):
            if not is_element_node(elem):
                self.wrong_type("left operand must returns element nodes: %r" % elem)
            for _ in context.iter_descendants(item=elem, axis='descendant-or-self'):
                for result in self[1].select(context):
                    yield result


###
# Predicate filters
@method('[', bp=75)
def led(self, left):
    self.parser.next_token.unexpected(']')
    self[:] = left, self.parser.expression()
    self.parser.advance(']')
    return self


@method('[')
def select(self, context=None):
    if context is not None:
        left_results = list(self[0].select(context))
        context.size = len(left_results)
        for context.position, context.item in enumerate(left_results):
            predicate = list(self[1].select(context.copy()))
            if len(predicate) == 1 and not isinstance(predicate[0], bool) and \
                    isinstance(predicate[0], (int, float)):
                if context.position == predicate[0] - 1:
                    yield context.item
            elif boolean_value(predicate):
                yield context.item


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
@method(axis('self', bp=80))
def select(self, context=None):
    if context is not None:
        for _ in context.iter_self():
            for result in self[0].select(context):
                yield result


@method(axis('child', bp=80))
def select(self, context=None):
    if context is not None:
        for _ in context.iter_children_or_self(child_axis=True):
            for result in self[0].select(context):
                yield result


@method(axis('descendant', bp=80))
def select(self, context=None):
    if context is not None:
        item = context.item
        for _ in context.iter_descendants(axis=self.symbol):
            if item is not context.item:
                for result in self[0].select(context):
                    yield result


@method(axis('descendant-or-self', bp=80))
def select(self, context=None):
    if context is not None:
        for _ in context.iter_descendants(axis=self.symbol):
            for result in self[0].select(context):
                yield result


@method(axis('following-sibling', bp=80))
def select(self, context=None):
    if context is not None:
        if is_element_node(context.item):
            item = context.item
            for elem in context.iter_parent(axis=self.symbol):
                follows = False
                for child in context.iter_children_or_self(elem, child_axis=True):
                    if follows:
                        for result in self[0].select(context):
                            yield result
                    elif item is child:
                        follows = True


@method(axis('following', bp=80))
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
@method(axis('attribute', bp=80))
def select(self, context=None):
    if context is not None:
        for _ in context.iter_attributes():
            for result in self[0].select(context):
                yield result


@method(axis('namespace', bp=80))
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
@method(axis('parent', bp=80))
def select(self, context=None):
    if context is not None:
        for _ in context.iter_parent(axis=self.symbol):
            for result in self[0].select(context):
                yield result


@method(axis('ancestor', bp=80))
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


@method(axis('ancestor-or-self', bp=80))
def select(self, context=None):
    if context is not None:
        item = context.item
        for elem in reversed(list(context.iter_ancestors(axis=self.symbol))):
            context.item = elem
            yield elem
        yield item


@method(axis('preceding-sibling', bp=80))
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


@method(axis('preceding', bp=80))
def select(self, context=None):
    if context is not None and is_element_node(context.item):
        elem = context.item
        ancestors = set(context.iter_ancestors(axis=self.symbol))
        for e in context.root.iter():
            if e is elem:
                break
            if e not in ancestors:
                context.item = e
                yield e


###
# Node types
@method(function('node', nargs=0, bp=90))
def select(self, context=None):
    if context is not None:
        for item in context.iter_children_or_self():
            if item is None:
                yield context.root
            elif is_xpath_node(item):
                yield item


@method(function('processing-instruction', nargs=(0, 1), bp=90))
def evaluate(self, context=None):
    if context and is_processing_instruction_node(context.item):
        return context.item


@method(function('comment', nargs=0, bp=90))
def evaluate(self, context=None):
    if context and is_comment_node(context.item):
        return context.item


@method(function('text', nargs=0, bp=90))
def select(self, context=None):
    if context is not None:
        for item in context.iter_children_or_self():
            if item is None:
                yield context.root
            elif is_text_node(item):
                yield item


###
# Node set functions
@method(function('last', nargs=0, bp=90))
def evaluate(self, context=None):
    return context.size if context is not None else 0


@method(function('position', nargs=0, bp=90))
def evaluate(self, context=None):
    return context.position + 1 if context is not None else 0


@method(function('count', nargs=1, bp=90))
def evaluate(self, context=None):
    results = self[0].evaluate(context)
    if isinstance(results, list):
        return len(results)
    elif results is not None:
        return 1
    else:
        return 0


@method(function('id', nargs=1, bp=90))
def select(self, context=None):
    if context is not None:
        value = self[0].evaluate(context)
        item = context.item
        if is_element_node(item):
            for elem in item.iter():
                if elem.get(XML_ID_QNAME) == value:
                    yield elem


@method(function('name', nargs=(0, 1), bp=90))
@method(function('local-name', nargs=(0, 1), bp=90))
@method(function('namespace-uri', nargs=(0, 1), bp=90))
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
@method(function('string', nargs=1, bp=90))
def evaluate(self, context=None):
    return string_value(self.get_argument(context))


@method(function('contains', nargs=2, bp=90))
def evaluate(self, context=None):
    try:
        return self[1].evaluate(context) in self[0].evaluate(context)
    except TypeError:
        self.wrong_type("the arguments must be strings")


@method(function('concat', bp=90))
def evaluate(self, context=None):
    try:
        return ''.join(tk.value for tk in self)
    except TypeError:
        self.wrong_type("the arguments must be strings")


@method(function('string-length', nargs=1, bp=90))
def evaluate(self, context=None):
    arg1 = self.get_argument(context, default_to_context=True)
    if arg1 is None:
        return 0
    try:
        return len(arg1)
    except TypeError:
        self.wrong_type("the argument must be a string")


@method(function('normalize-space', nargs=1, bp=90))
def evaluate(self, context=None):
    arg1 = self.get_argument(context, default_to_context=True)
    if arg1 is None:
        return ''
    try:
        return ' '.join(arg1.strip().split())
    except TypeError:
        self.wrong_type("the argument must be a string")


@method(function('starts-with', nargs=2, bp=90))
def evaluate(self, context=None):
    arg1 = self.get_argument(context)
    arg2 = self.get_argument(context, index=1)
    try:
        return arg1.startswith(arg2)
    except (AttributeError, TypeError):
        self.wrong_type("the arguments must be a string")


@method(function('translate', nargs=3, bp=90))
def evaluate(self, context=None):
    try:
        maketrans = str.maketrans
    except AttributeError:
        import string
        maketrans = getattr(string, 'maketrans')
    try:
        if not all(tk.symbol == '(string)' for tk in self):
            raise TypeError
        translation_map = maketrans(self[1].value, self[2].value)
        return self[0].value.translate(translation_map)
    except ValueError:
        self.wrong_value("the second and the third arguments must have equal length")
    except TypeError:
        self.wrong_type("the arguments must be strings")


@method(function('substring', nargs=(2, 3), bp=90))
def evaluate(self, context=None):
    start, stop = 0, None
    try:
        start = self[1].evaluate(context) - 1
    except TypeError:
        self.wrong_type("the second argument must be xs:numeric")
    if len(self) > 2:
        try:
            stop = start + self[2].evaluate(context)
        except TypeError:
            self.wrong_type("the third argument must be xs:numeric")

    item = self.get_argument(context)
    try:
        return '' if item is None else item[slice(start, stop)]
    except TypeError:
        self.wrong_type("the first argument must be a string")


@method(function('substring-before', nargs=2, bp=90))
@method(function('substring-after', nargs=2, bp=90))
def evaluate(self, context=None):
    arg1 = self.get_argument(context)
    arg2 = self.get_argument(context, index=1)
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
@method(function('boolean', nargs=1, bp=90))
def evaluate(self, context=None):
    return boolean_value(self[0].get_results(context))


@method(function('not', nargs=1, bp=90))
def evaluate(self, context=None):
    return not boolean_value(self[0].get_results(context))


@method(function('true', nargs=0, bp=90))
def evaluate(self, context=None):
    return True


@method(function('false', nargs=0, bp=90))
def evaluate(self, context=None):
    return False


@method(function('lang', nargs=1, bp=90))
def evaluate(self, context=None):
    if context is None:
        return
    elif not is_element_node(context.item):
        return False
    else:
        try:
            lang = context.item.attrib[XML_LANG_QNAME].strip()
        except KeyError:
            for elem in context.iter_ancestor():
                if XML_LANG_QNAME in elem.attrib:
                    lang = elem.attrib[XML_LANG_QNAME]
                    break
            else:
                return False

        if '-' in lang:
            lang, _ = lang.split('-')
        return lang.lower() == self[0].evaluate().lower()


###
# Number functions
@method(function('number', nargs=(0, 1), bp=90))
def evaluate(self, context=None):
    item = self.get_argument(context)
    try:
        return float(node_string_value(item) if is_xpath_node(item) else item)
    except (TypeError, ValueError):
        return float('nan')


@method(function('sum', nargs=(1, 2), bp=90))
def evaluate(self, context=None):
    if context is None:
        result = self[0].evaluate()
    else:
        result = list(self[0].select(context))

    if isinstance(result, list):
        try:
            return sum(result)
        except TypeError:
            return self[1].evaluate(context) if len(self) > 1 else 0
    elif context is not None:
        self.wrong_type("not a sequence: %r" % result)


@method(function('ceiling', nargs=1, bp=90))
def evaluate(self, context=None):
    item = self.get_argument(context)
    try:
        return math.ceil(item)
    except TypeError as err:
        if item is not None and not isinstance(item, list):
            self.wrong_type(str(err))


@method(function('floor', nargs=1, bp=90))
def evaluate(self, context=None):
    item = self.get_argument(context)
    try:
        return math.floor(item)
    except TypeError as err:
        if item is not None and not isinstance(item, list):
            self.wrong_type(str(err))


@method(function('round', nargs=1, bp=90))
def evaluate(self, context=None):
    item = self.get_argument(context)
    try:
        number = decimal.Decimal(item)
        if number > 0:
            return float(number.quantize(decimal.Decimal('1'), rounding='ROUND_HALF_UP'))
        elif PY3:
            return float(round(number))
        else:
            return float(number.quantize(decimal.Decimal('1'), rounding='ROUND_HALF_DOWN'))
    except TypeError as err:
        if item is not None and not isinstance(item, list):
            self.wrong_type(str(err))
    except decimal.DecimalException as err:
        if item is not None and not isinstance(item, list):
            self.wrong_value(str(err))


XPath1Parser.end()
