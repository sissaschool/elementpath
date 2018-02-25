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
from .exceptions import ElementPathSyntaxError, ElementPathTypeError, ElementPathValueError
from .todp_parser import Parser
from .xpath_base import is_etree_element, XPathToken


class XPath1Parser(Parser):
    """
    XPath 1.0 expression parser class.

    :param namespaces: optional prefix to namespace map.
    """
    token_base_class = XPathToken
    symbol_table = {k: v for k, v in Parser.symbol_table.items()}
    SYMBOLS = (
        'processing-instruction(', 'descendant-or-self::', 'following-sibling::',
        'preceding-sibling::', 'ancestor-or-self::', 'descendant::', 'attribute::',
        'following::', 'namespace::', 'preceding::', 'ancestor::', 'comment(', 'parent::',
        'child::', 'self::', 'text(', 'node(', 'and', 'mod', 'div', 'or',
        '..', '//', '!=', '<=', '>=', '(', ')', '[', ']', '.', '@', ',', '/', '|', '*',
        '-', '=', '+', '<', '>', '(:', ':)', '$',

        # XPath Core function library
        'last(', 'position(', 'count(', 'id(', 'local-name(',   # Node set functions
        'namespace-uri(', 'name(',
        'string(', 'concat(', 'starts-with(', 'contains(',      # String functions
        'substring-before(', 'substring-after(', 'substring(',
        'string-length(', 'normalize-space(', 'translate(',
        'boolean(', 'not(', 'true(', 'false('                   # Boolean functions
    )
    RELATIVE_PATH_SYMBOLS = {s for s in SYMBOLS if s.endswith("::")} | {
        '(integer)', '(string)', '(decimal)', '(name)', '*', '@', '..', '.', '(', '/'
    }

    def __init__(self, namespaces=None, schema=None):
        super(XPath1Parser, self).__init__()
        self.namespaces = namespaces if namespaces is not None else {}
        self.schema = schema

    @property
    def version(self):
        return '1.0'

    @classmethod
    def axis(cls, symbol, bp=0):
        def nud(self):
            self.parser.next_token.expected(
                '(name)', '*', 'text(', 'node(', 'document-node(', 'comment(', 'processing-instruction(',
                'attribute', 'schema-attribute', 'element', 'schema-element'
            )
            self[0:] = self.parser.expression(rbp=bp),
            return self
        return cls.register(symbol, lbp=bp, rbp=bp, nud=nud)

    @classmethod
    def function(cls, symbol, nargs=None, bp=0):
        def nud(self):
            if nargs is None:
                del self[:]
                while True:
                    self.append(self.parser.expression(90))
                    if self.parser.next_token.symbol != ',':
                        break
                    self.parser.advance(',')
                self.parser.advance(')')
                self.value = self.eval()
                return self
            elif nargs == 0:
                self.parser.advance(')')
                self.value = self.eval()
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
                else:
                    break
            self.parser.advance(')')
            self.value = self.eval()
            return self

        return cls.register(symbol, lbp=bp, rbp=bp, nud=nud)

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
prefix = XPath1Parser.prefix
infix = XPath1Parser.infix
method = XPath1Parser.method
function = XPath1Parser.function
axis = XPath1Parser.axis


register(',')


# Comments
@method('(:')
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


register(':)')


###
# Literals
literal('(string)')
literal('(decimal)')
literal('(integer)')


@method(literal('(name)'))
def nud(self):
    if self.value[0] != '{' and ':' in self.value:
        self.value = self.parser.map_reference(self.value)
    return self


@method('(name)')
def select(self, context):
    if context.is_element_node() and context.node.tag == self.value:
        yield context.node
    elif context.node == self.value:
        yield context.node


@method(literal('.'))
def select(self, context):
    yield context.node if context.node is not None else context.root


@method(literal('..'))
def select(self, context):
    try:
        parent = context.parent_map[context.node]
    except KeyError:
        pass
    else:
        if is_etree_element(parent):
            yield parent


literal('*')


###
# Variables
@method('$', bp=90)
def nud(self):
    self.parser.next_token.expected('(name)')
    self[0:] = self.parser.expression(rbp=90),
    return self


@method('$')
def eval(self, context=None):
    varname = self[0].eval(context)
    try:
        return context.variables[varname]
    except (KeyError, AttributeError):
        pass
    self.wrong_name('unknown variable')


###
# Forward Axes
@method(axis('self::', bp=80))
def select(self, context):
    for result in self[0].select(context):
        yield result


@method(axis('child::', bp=80))
def select(self, context):
    for child_context in context.iter_children():
        for result in self[0].select(child_context):
            yield result


@method(axis('descendant::', bp=80))
def select(self, context):
    for descendant_context in context.copy().iter_descendants():
        if descendant_context.node is not context.node:
            for result in self[0].select(descendant_context):
                yield result


@method(axis('descendant-or-self::', bp=80))
def select(self, context):
    for descendant_context in context.copy().iter_descendants():
        for result in self[0].select(descendant_context):
            yield result


@method(axis('following-sibling::', bp=80))
def select(self, context):
    if context.is_element_node():
        elem = context.node
        try:
            parent = context.parent_map[elem]
        except KeyError:
            return
        else:
            follows = False
            for sibling_context in context.copy(node=parent).iter_children():
                if follows:
                    for result in self[0].select(sibling_context):
                        yield result
                elif sibling_context.node is elem:
                    follows = True


@method(axis('following::', bp=80))
def select(self, context):
    descendants = {c.node for c in context.copy().iter_descendants()}
    follows = False
    for elem in context.root.iter():
        if follows:
            if elem not in descendants:
                for result in self[0].select(context.copy(elem)):
                    yield result
        elif context.node is elem:
            follows = True


@method(axis('namespace::', bp=80))
def select(self, context):
    if context.is_element_node():
        element_class = context.node.__class__
        for prefix, uri in self.parser.namespaces.items():
            yield element_class(tag=prefix, text=uri)


###
# Reverse Axes
@method(axis('parent::', bp=80))
def select(self, context):
    try:
        parent = context.parent_map[context.node]
    except KeyError:
        pass
    else:
        for result in self[0].select(context.copy(node=parent)):
            yield result


@method(axis('ancestor::', bp=80))
def select(self, context):
    results = [
        item for ancestor_context in context.copy().iter_ancestors()
        for item in self[0].select(ancestor_context)
    ]
    for result in reversed(results):
        yield result


@method(axis('ancestor-or-self::', bp=80))
def select(self, context):
    for elem in reversed([c.node for c in context.copy().iter_ancestors()]):
        yield elem
    yield context.node


@method(axis('preceding-sibling::', bp=80))
def select(self, context):
    if context.is_element_node():
        elem = context.node
        try:
            parent = context.parent_map[elem]
        except KeyError:
            pass
        else:
            for child in parent:
                if child is elem:
                    break
                yield child


@method(axis('preceding::', bp=80))
def select(self, context):
    if context.is_element_node():
        elem = context.node
        ancestors = {c.node for c in context.copy().iter_ancestors()}
        for e in context.root.iter():
            if e is elem:
                break
            if e not in ancestors:
                yield e


###
# Node types
function('processing-instruction(', nargs=0, bp=90)
function('comment(', nargs=0, bp=90)


@method(function('text(', nargs=0, bp=90))
def select(self, context):
    if context.is_element_node():
        if context.node.text is not None:
            yield context.node.text  # adding tails??


@method(function('node(', nargs=0, bp=90))
def select(self, context):
    yield context.node if context.node is not None else context.root


###
# Node set functions
@method(function('last(', nargs=0, bp=90))
def eval(self, context=None):
    return context.size


@method(function('position(', nargs=0, bp=90))
def eval(self, context=None):
    return context.position


@method(function('count(', nargs=1, bp=90))
def eval(self, context=None):
    return len(list(filter(self.node_filter, self[0].select(context))))


function('id(', nargs=1, bp=90)
function('local-name(', nargs=1, bp=90)
function('namespace-uri(', nargs=1, bp=90)
function('name(', nargs=1, bp=90)


###
# String functions
@method(function('string(', nargs=1, bp=90))
def eval(self, context=None):
    return str(self[0].eval(context))


@method(function('contains(', nargs=2, bp=90))
def eval(self, context=None):
    try:
        return self[1].eval(context) in self[0].eval(context)
    except TypeError:
        self.wrong_type("the arguments must be strings")


@method(function('concat(', bp=90))
def eval(self, context=None):
    try:
        return ''.join(tk.value for tk in self)
    except TypeError:
        self.wrong_type("the arguments must be strings")


@method(function('string-length(', nargs=1, bp=90))
def eval(self, context=None):
    try:
        return len(self[0].eval(context))
    except TypeError:
        self.wrong_type("the argument must be a string")


@method(function('normalize-space(', nargs=1, bp=90))
def eval(self, context=None):
    try:
        return ' '.join(self[0].eval(context).strip().split())
    except TypeError:
        self.wrong_type("the argument must be a string")


@method(function('starts-with(', nargs=2, bp=90))
def eval(self, context=None):
    try:
        return self[0].eval(context).startswith(self[1].value)
    except TypeError:
        self.wrong_type("the arguments must be a string")


@method(function('translate(', nargs=3, bp=90))
def eval(self, context=None):
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


@method(function('substring(', nargs=(2, 3), bp=90))
def eval(self, context=None):
    start, stop = 0, None
    try:
        start = self[1].eval(context) - 1
    except TypeError:
        self.wrong_type("the second argument must be xs:numeric")
    if len(self) > 2:
        try:
            stop = start + self[2].eval(context)
        except TypeError:
            self.wrong_type("the third argument must be xs:numeric")

    try:
        return self[0].eval(context)[slice(start, stop)]
    except TypeError:
        self.wrong_type("the first argument must be a string")


@method(function('substring-before(', nargs=2, bp=90))
@method(function('substring-after(', nargs=2, bp=90))
def eval(self, context=None):
    index = 0
    try:
        index = self[0].eval(context).find(self[1].eval(context))
    except AttributeError:
        self.wrong_type("the first argument must be a string")
    except TypeError:
        self.wrong_type("the second argument must be a string")

    if self.symbol == 'substring-before(':
        return self[0].eval(context)[:index]
    else:
        return self[0].eval(context)[index + len(self[1].value):]


###
# Boolean functions
@method(function('boolean(', nargs=1, bp=90))
def eval(self, context=None):
    return self.boolean(self[0].eval(context))


@method(function('not(', nargs=1, bp=90))
def eval(self, context=None):
    return not self.boolean(self[0].eval(context))


@method(function('true(', nargs=0, bp=90))
def eval(self, context=None):
    return True


@method(function('false(', nargs=0, bp=90))
def eval(self, context=None):
    return False


@method(infix('*', bp=45))
def eval(self, context=None):
    return self[0].eval(context) * self[1].eval(context)


@method('*', bp=45)
def select(self, context):
    if not self:
        # Wildcard literal
        if context.is_attribute_node():
            yield context.node[1]
        elif context.node is not None:
            yield context.node
    else:
        # Product operator
        yield self[0].eval(context)


@method('@', bp=80)
@method('attribute::', bp=80)
def nud(self):
    self[0:] = self.parser.expression(rbp=80),
    if self[0].symbol not in ('*', '(name)'):
        raise ElementPathSyntaxError("invalid attribute specification for XPath.")
    return self


@method('@')
@method(axis('attribute::'))
def select(self, context):
    if context.is_element_node():
        elem = context.node
        for context.node in elem.attrib.items():
            for result in self[0].select(context):
                yield result
        context.node = elem


###
# Logical Operators
@method(infix('or', bp=20))
def eval(self, context=None):
    return bool(self[0].eval(context) or self[1].eval(context))


@method(infix('and', bp=25))
def eval(self, context=None):
    return bool(self[0].eval(context) and self[1].eval(context))


@method(infix('=', bp=30))
def eval(self, context=None):
    return self[0].eval(context) == self[1].eval(context)


@method(infix('!=', bp=30))
def eval(self, context=None):
    return self[0].eval(context) != self[1].eval(context)


@method(infix('<', bp=30))
def eval(self, context=None):
    return self[0].eval(context) < self[1].eval(context)


@method(infix('>', bp=30))
def eval(self, context=None):
    return self[0].eval(context) > self[1].eval(context)


@method(infix('<=', bp=30))
def eval(self, context=None):
    return self[0].eval(context) <= self[1].eval(context)


@method(infix('>=', bp=30))
def eval(self, context=None):
    return self[0].eval(context) >= self[1].eval(context)


prefix('+')
@method(infix('+', bp=40))
def eval(self, context=None):
    if len(self) > 1:
        try:
            return self[0].eval(context) + self[1].eval(context)
        except TypeError:
            raise ElementPathTypeError("a numeric value is required: %r." % self[0])
    else:
        try:
            return +self[0].eval(context)
        except TypeError:
            raise ElementPathTypeError("numeric values are required: %r." % self[:])


prefix('-')
@method(infix('-', bp=40))
def eval(self, context=None):
    try:
        try:
            return self[0].eval(context) - self[1].eval(context)
        except TypeError:
            self.wrong_type("values must be numeric: %r" % [tk.eval(context) for tk in self])
    except IndexError:
        try:
            return -self[0].eval(context)
        except TypeError:
            self.wrong_type("value must be numeric: %r" % self[0].eval(context))


@method(infix('div', bp=45))
def eval(self, context=None):
    return self[0].eval(context) / self[1].eval(context)


infix('mod', bp=45)


@method(infix('|', bp=50))
def select(self, context):
    results = {self.filter_node(elem) for k in range(2) for elem in self[k].select(context)}
    for elem in self.root.iter():
        if elem in results:
            yield elem


@method('//', bp=80)
@method('/', bp=80)
def nud(self):
    if not self.parser.source_first:
        self.wrong_symbol()
    elif self.parser.next_token.symbol == '(end)' and self.symbol == '/':
        return self
    elif self.parser.next_token.symbol not in self.parser.RELATIVE_PATH_SYMBOLS:
        self.parser.next_token.wrong_symbol()
    self[0:] = self.parser.expression(80),
    return self


@method('//', bp=80)
@method('/', bp=80)
def led(self, left):
    if self.parser.next_token.symbol not in self.parser.RELATIVE_PATH_SYMBOLS:
        self.parser.next_token.wrong_symbol()
    self[0:1] = left, self.parser.expression(100)
    return self


@method('/')
def select(self, context):
    """
    Child path expression. Selects child:: axis as default (when bind to '*' or '(name)').
    """
    if not self:
        yield context.root
    elif len(self) == 1:
        if self[0].symbol in ('*', '(name)'):
            for child_context in context.copy().iter_children():
                for result in self[0].select(child_context):
                    yield result
        else:
            for result in self[0].select(context):
                yield result
    else:
        nodes = set()
        for elem in self[0].select(context.copy()):
            if not is_etree_element(elem):
                self.wrong_type("left operand must returns nodes: %r" % elem)
            if self[1].symbol in ('*', '(name)'):
                for child_context in context.copy(node=elem).iter_children():
                    for result in self[1].select(child_context):
                        if is_etree_element(result) or isinstance(result, tuple):
                            if result not in nodes:
                                yield result
                                nodes.add(result)
                        else:
                            yield result
            else:
                for result in self[1].select(context.copy(node=elem)):
                    if is_etree_element(result) or isinstance(result, tuple):
                        if result not in nodes:
                            yield result
                            nodes.add(result)
                    else:
                        yield result


@method('//')
def select(self, context):
    if len(self) == 1:
        for descendant_context in context.copy().iter_descendants():
            for result in self[0].select(descendant_context):
                yield result
    else:
        for elem in self[0].select(context):
            if not is_etree_element(elem):
                self.wrong_type("left operand must returns nodes: %r" % elem)
            for descendant_context in context.copy(node=elem).iter_descendants():
                for result in self[1].select(descendant_context):
                    yield result


@method('(', bp=90)
def nud(self):
    self.parser.next_token.unexpected(')')
    self[0:] = self.parser.expression(),
    self.parser.advance(')')
    return self[0]


register(')')


###
# Predicate selection
@method('[', bp=90)
def led(self, left):
    self.parser.next_token.unexpected(']')
    self[0:1] = left, self.parser.expression()
    self.parser.advance(']')
    return self


@method('[')
def select(self, context, results):
    """Predicate selector."""
    results = self[0].select(context, results)
    if isinstance(self[1].value, int):
        # subscript predicate
        value = self[1].value
        if value > 0:
            index = value - 1
        elif value == 0 or self[1].symbol not in ('last(', 'position('):
            index = None
        else:
            index = value

        if index is not None:
            try:
                yield [elem for elem in results][index]
            except IndexError:
                return
    else:
        for elem in results:
            if elem is not None:
                predicate_results = list(self[1].select(context, [elem]))
                if predicate_results and any(predicate_results):
                    yield elem


register(']')


XPath1Parser.end()
