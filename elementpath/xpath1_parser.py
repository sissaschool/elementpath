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

from .exceptions import ElementPathSyntaxError, ElementPathTypeError, ElementPathValueError
from .todp_parser import Parser
from .xpath_base import (
    XML_ID_ATTRIBUTE, XPathToken, qname_to_prefixed, is_etree_element, is_xpath_node,
    is_element_node, is_document_node, is_comment_node, is_processing_instruction_node,
    is_attribute_node, is_text_node
)


class XPath1Parser(Parser):
    """
    XPath 1.0 expression parser class.

    :param namespaces: optional prefix to namespace map.
    """
    token_base_class = XPathToken
    symbol_table = {k: v for k, v in Parser.symbol_table.items()}
    SYMBOLS = {
        # Axes
        'descendant-or-self', 'following-sibling', 'preceding-sibling',
        'ancestor-or-self', 'descendant', 'attribute', 'following',
        'namespace', 'preceding', 'ancestor', 'parent', 'child', 'self',

        # Operators
        'and', 'mod', 'div', 'or', '..', '//', '!=', '<=', '>=', '(', ')', '[', ']',
        '.', '@', ',', '/', '|', '*', '-', '=', '+', '<', '>', '(:', ':)', '$', '::',

        # XPath Core function library
        'node', 'text', 'comment', 'processing-instruction',  # Node test functions
        'last', 'position', 'count', 'id', 'local-name',      # Node set functions
        'namespace-uri', 'name',
        'string', 'concat', 'starts-with', 'contains',        # String functions
        'substring-before', 'substring-after', 'substring',
        'string-length', 'normalize-space', 'translate',
        'boolean', 'not', 'true', 'false'                     # Boolean functions
    }

    def __init__(self, namespaces=None, *args, **kwargs):
        super(XPath1Parser, self).__init__()
        self.namespaces = namespaces if namespaces is not None else {}

    @property
    def version(self):
        return '1.0'

    @classmethod
    def axis(cls, symbol, bp=0):
        def nud_(self):
            self.parser.advance('::')
            self.parser.next_token.expected(
                '(name)', '*', 'text', 'node', 'document-node', 'comment', 'processing-instruction',
                'attribute', 'schema-attribute', 'element', 'schema-element'
            )
            self[0:] = self.parser.expression(rbp=bp),
            return self

        axis_pattern_template = '\\b%s(?=\s*\\:\\:)'
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
                    self.append(self.parser.expression(90))
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
                self[k:] = self.parser.expression(rbp=bp),
                k += 1
                if k < min_args:
                    self.parser.advance(',')
            while k < max_args:
                if self.parser.next_token.symbol == ',':
                    self.parser.advance(',')
                    self[k:] = self.parser.expression(90),
                elif k == 0 and self.parser.next_token.symbol != ')':
                    self[k:] = self.parser.expression(90),
                else:
                    break
                k += 1
            self.parser.advance(')')
            self.value = self.evaluate()  # Static context evaluation
            return self

        function_pattern_template = '\\b%s(?=\s*\\()'
        try:
            pattern = function_pattern_template % symbol.strip()
        except AttributeError:
            pattern = function_pattern_template % getattr(symbol, 'symbol')
        return cls.register(symbol, pattern=pattern, label='function', lbp=bp, rbp=bp, nud=nud_)

    def map_reference(self, ref):
        """
        Map a reference into a fully qualified name using the instance namespace map.

        :param ref: a local name, a prefixed name or a fully qualified name.
        :return: String with a FQN or a local name.
        """
        if ref and ref[0] == '{':
            return ref

        try:
            ns_prefix, local_name = ref.split(':')
        except ValueError:
            if ':' in ref:
                raise ElementPathValueError("wrong format for reference name %r" % ref)
            try:
                uri = self.namespaces['']
            except KeyError:
                return ref
            else:
                return u'{%s}%s' % (uri, ref) if uri else ref
        else:
            if not ns_prefix or not local_name:
                raise ElementPathValueError("wrong format for reference name %r" % ref)
            try:
                uri = self.namespaces[ns_prefix]
            except KeyError:
                raise ElementPathValueError("prefix %r not found in namespace map" % ns_prefix)
            else:
                return u'{%s}%s' % (uri, local_name) if uri else local_name


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
register(':)')
register(')')
register(']')
register('::')


###
# Literals
literal('(string)')
literal('(float)')
literal('(decimal)')
literal('(integer)')


@method(literal('(name)', bp=10))
def nud(self):
    if self.value[0] != '{' and ':' in self.value:
        self.value = self.parser.map_reference(self.value)
    return self


@method('(name)')
def evaluate(self, context=None):
    if context is None:
        return None
    elif is_element_node(context.item, self.value) or is_attribute_node(context.item, self.value):
        return context.item


@method('(name)')
def select(self, context):
    value = self.value
    if context.active_iterator is None:
        for item in context.iter_children():
            if is_element_node(item, value) or is_attribute_node(item, value):
                yield item
    else:
        if is_element_node(context.item, value) or is_attribute_node(context.item, value):
            yield context.item


###
# Comments
@method(literal('(:'))
def nud(self):
    comment_level = 1
    value = []
    while comment_level:
        self.parser.advance()
        token = self.parser.token
        if token.symbol == ':)':
            comment_level -= 1
            if comment_level:
                value.append(token.value)
        elif token.symbol == '(:':
            comment_level += 1
            value.append(token.value)
        else:
            value.append(token.value)
    self.value = ' '.join(value)
    return self


###
# Variables
@method('$', bp=90)
def nud(self):
    self.parser.next_token.expected('(name)')
    self[0:] = self.parser.expression(rbp=90),
    return self


@method('$')
def evaluate(self, context=None):
    varname = self[0].value
    try:
        return context.variables[varname]
    except (KeyError, AttributeError):
        pass
    self.wrong_name('unknown variable')


###
# Nullary operators (use only the context)
@method(nullary('*'))
def select(self, context):
    if not self:
        # Wildcard literal
        if context.active_iterator is None:
            for child in context.iter_children():
                if is_element_node(child):
                    yield child
        elif context.principal_node_kind:
            if is_attribute_node(context.item):
                yield context.item[1]
            else:
                yield context.item
    else:
        # Product operator
        context.item = self[0].evaluate(context)
        yield context.item


@method(nullary('.'))
def select(self, context):
    if context.item is not None:
        yield context.item
    elif is_document_node(context.root):
        yield context.root


@method(nullary('..'))
def select(self, context):
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
    return self[0].evaluate(context) == self[1].evaluate(context)


@method(infix('!=', bp=30))
def evaluate(self, context=None):
    return self[0].evaluate(context) != self[1].evaluate(context)


@method(infix('<', bp=30))
def evaluate(self, context=None):
    return self[0].evaluate(context) < self[1].evaluate(context)


@method(infix('>', bp=30))
def evaluate(self, context=None):
    return self[0].evaluate(context) > self[1].evaluate(context)


@method(infix('<=', bp=30))
def evaluate(self, context=None):
    return self[0].evaluate(context) <= self[1].evaluate(context)


@method(infix('>=', bp=30))
def evaluate(self, context=None):
    return self[0].evaluate(context) >= self[1].evaluate(context)


###
# Numerical operators
prefix('+')
prefix('-', bp=90)


@method(infix('+', bp=40))
def evaluate(self, context=None):
    if len(self) > 1:
        try:
            return self[0].evaluate(context) + self[1].evaluate(context)
        except TypeError:
            raise ElementPathTypeError("a numeric value is required: %r." % self[0])
    else:
        try:
            return +self[0].evaluate(context)
        except TypeError:
            raise ElementPathTypeError("numeric values are required: %r." % self[:])


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
def select(self, context):
    results = {item for k in range(2) for item in self[k].select(context)}
    for item in context.iter():
        if item in results:
            yield item


###
# Path expressions
@method('//', bp=80)
@method('/', bp=80)
def nud(self):
    next_token = self.parser.next_token
    if not self.parser.source_first:
        self.wrong_symbol()
    elif next_token.symbol == '(end)' and self.symbol == '/':
        return self
    elif not self.parser.next_token.is_path_step_token():
        next_token.wrong_symbol()
    self[0:] = self.parser.expression(80),
    return self


@method('//', bp=80)
@method('/', bp=80)
def led(self, left):
    if not self.parser.next_token.is_path_step_token():
        self.parser.next_token.wrong_symbol()
    self[0:1] = left, self.parser.expression(80)
    return self


@method('/')
def select(self, context):
    """
    Child path expression. Selects child:: axis as default (when bind to '*' or '(name)').
    """
    if not self:
        if is_document_node(context.root):
            yield context.root
    elif len(self) == 1:
        context.item = None
        for result in self[0].select(context):
            yield result
    else:
        items = set()
        for elem in self[0].select(context):
            if not is_element_node(elem):
                self.wrong_type("left operand must returns element nodes: %r" % elem)
            for result in self[1].select(context.copy(item=elem)):
                if is_etree_element(result) or isinstance(result, tuple):
                    if result not in items:
                        yield result
                        items.add(result)
                else:
                    yield result


@method('//')
def select(self, context):
    if len(self) == 1:
        for _ in context.iter_descendants():
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
# Parenthesized expressions
@method('(', bp=90)
def nud(self):
    self.parser.next_token.unexpected(')')
    self[0:] = self.parser.expression(),
    self.parser.advance(')')
    return self[0]


###
# Predicate filters
@method('[', bp=90)
def led(self, left):
    self.parser.next_token.unexpected(']')
    self[0:1] = left, self.parser.expression()
    self.parser.advance(']')
    return self


@method('[')
def select(self, context):
    for result in self[0].select(context):
        predicate = list(self[1].select(context.copy()))
        if len(predicate) == 1 and not isinstance(predicate[0], bool) and \
                isinstance(predicate[0], (int, float)):
            if context.position == predicate[0] - 1:
                context.item = result
                yield result
        elif self.boolean(predicate):
            context.item = result
            yield result


###
# Forward Axes
@method(axis('self', bp=80))
def select(self, context):
    for _ in context.iter_self():
        for result in self[0].select(context):
            yield result


@method(axis('child', bp=80))
def select(self, context):
    for _ in context.iter_children():
        for result in self[0].select(context):
            yield result


@method(axis('descendant', bp=80))
def select(self, context):
    item = context.item
    for _ in context.iter_descendants():
        if item is not context.item:
            for result in self[0].select(context):
                yield result


@method(axis('descendant-or-self', bp=80))
def select(self, context):
    for _ in context.iter_descendants():
        for result in self[0].select(context):
            yield result


@method(axis('following-sibling', bp=80))
def select(self, context):
    if is_element_node(context.item):
        item = context.item
        for _ in context.iter_parent():
            follows = False
            for child in context.iter_children():
                if follows:
                    for result in self[0].select(context):
                        yield result
                elif item is child:
                    follows = True


@method(axis('following', bp=80))
def select(self, context):
    descendants = set(context.iter_descendants())
    item = context.item
    follows = False
    for elem in context.iter_descendants(item=context.root):
        if follows:
            if elem not in descendants:
                for result in self[0].select(context):
                    yield result
        elif item is elem:
            follows = True


@method('@', bp=80)
def nud(self):
    self[0:] = self.parser.expression(rbp=80),
    if self[0].symbol not in ('*', '(name)'):
        raise ElementPathSyntaxError("invalid attribute specification for XPath.")
    return self


@method('@')
@method(axis('attribute', bp=80))
def select(self, context):
    for _ in context.iter_attributes():
        for result in self[0].select(context):
            yield result


@method(axis('namespace', bp=80))
def select(self, context):
    if is_element_node(context.item):
        element_class = context.item.__class__
        for prefix_, uri in self.parser.namespaces.items():
            context.item = element_class(tag=prefix_, text=uri)
            yield context.item


###
# Reverse Axes
@method(axis('parent', bp=80))
def select(self, context):
    for _ in context.iter_parent():
        for result in self[0].select(context):
            yield result


@method(axis('ancestor', bp=80))
def select(self, context):
    results = [item for _ in context.iter_ancestors() for item in self[0].select(context)]
    for result in reversed(results):
        context.item = result
        yield result


@method(axis('ancestor-or-self', bp=80))
def select(self, context):
    item = context.item
    for elem in reversed(list(context.iter_ancestors())):
        context.item = elem
        yield elem
    yield item


@method(axis('preceding-sibling', bp=80))
def select(self, context):
    if is_element_node(context.item):
        item = context.item
        for parent in context.iter_parent():
            for child in parent:
                if child is item:
                    break
                else:
                    context.item = child
                    for result in self[0].select(context):
                        yield result


@method(axis('preceding', bp=80))
def select(self, context):
    if is_element_node(context.item):
        elem = context.item
        ancestors = set(context.iter_ancestors())
        for e in context.root.iter():
            if e is elem:
                break
            if e not in ancestors:
                context.item = e
                yield e


###
# Node types
@method(function('node', nargs=0, bp=90))
def select(self, context):
    item = context.item
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
def evaluate(self, context=None):
    if context and is_text_node(context.item):
        return context.item


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


@method('count')
def select(self, context):
    yield len(list(self[0].select(context)))


@method(function('id', nargs=1, bp=90))
def select(self, context):
    value = self[0].evaluate(context)
    item = context.item
    if is_element_node(item):
        for elem in item.iter():
            if elem.get(XML_ID_ATTRIBUTE) == value:
                yield elem
    elif is_comment_node(item) or is_processing_instruction_node(item):
        for s in item.text.split():
            if s == value:
                yield item
                break
    elif isinstance(item, tuple):
        for s in item[1].split():
            if s == value:
                yield item
                break
    else:
        for s in str(item).split():
            if s == value:
                yield item
                break


@method(function('name', nargs=(0, 1), bp=90))
@method(function('local-name', nargs=(0, 1), bp=90))
@method(function('namespace-uri', nargs=(0, 1), bp=90))
def evaluate(self, context=None):
    if context is None:
        return
    elif not self:
        name = self.name(context.item)
    else:
        try:
            selector = iter(self[0].select(context))
            item = next(selector)
        except StopIteration:
            name = ''
        else:
            name = self.name(item)
            if self.parser.version > '1.0':
                try:
                    next(selector)
                except StopIteration:
                    pass
                else:
                    self.wrong_value("a sequence of more than one item is not allowed as argument")

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
    return str(self[0].evaluate(context))


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
    try:
        return len(self[0].evaluate(context))
    except TypeError:
        self.wrong_type("the argument must be a string")


@method(function('normalize-space', nargs=1, bp=90))
def evaluate(self, context=None):
    try:
        return ' '.join(self[0].evaluate(context).strip().split())
    except TypeError:
        self.wrong_type("the argument must be a string")


@method(function('starts-with', nargs=2, bp=90))
def evaluate(self, context=None):
    try:
        return self[0].evaluate(context).startswith(self[1].value)
    except TypeError:
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

    try:
        return self[0].evaluate(context)[slice(start, stop)]
    except TypeError:
        self.wrong_type("the first argument must be a string")


@method(function('substring-before', nargs=2, bp=90))
@method(function('substring-after', nargs=2, bp=90))
def evaluate(self, context=None):
    index = 0
    try:
        index = self[0].evaluate(context).find(self[1].evaluate(context))
    except AttributeError:
        self.wrong_type("the first argument must be a string")
    except TypeError:
        self.wrong_type("the second argument must be a string")

    if self.symbol == 'substring-before':
        return self[0].evaluate(context)[:index]
    else:
        return self[0].evaluate(context)[index + len(self[1].value):]


###
# Boolean functions
@method(function('boolean', nargs=1, bp=90))
def evaluate(self, context=None):
    return self.boolean(self[0].evaluate(context))


@method(function('not', nargs=1, bp=90))
def evaluate(self, context=None):
    return not self.boolean(self[0].evaluate(context))


@method(function('true', nargs=0, bp=90))
def evaluate(self, context=None):
    return True


@method(function('false', nargs=0, bp=90))
def evaluate(self, context=None):
    return False


XPath1Parser.end()
