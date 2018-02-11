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
from .exceptions import ElementPathSyntaxError, ElementPathValueError
from .todp_parser import Token, Parser


class XPathToken(Token):

    def iter_select(self, context):
        return self.sed(context, [context])

    def sed(self, context, results):
        """Select denotation"""
        raise ElementPathSyntaxError("Undefined operator for %r." % self.symbol)

    @staticmethod
    def iselement(elem):
        return hasattr(elem, 'tag') and hasattr(elem, 'attrib') and hasattr(elem, 'text')


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
        '-', '=', '+', '<', '>', '(:', ':)',

        # XPath Core function library
        'last(', 'position(', 'count(', 'id(', 'local-name(',   # Node set functions
        'namespace-uri(', 'name(',
        'string(', 'concat(', 'starts-with(', 'contains(',      # String functions
        'substring-before(', 'substring-after(', 'substring(',
        'string-length(', 'normalize-space(', 'translate(',
        'boolean(', 'not(', 'true(', 'false('                   # Boolean functions
    )
    RELATIVE_PATH_SYMBOLS = {s for s in SYMBOLS if s.endswith("::")} | {
        '(integer)', '(string)', '(decimal)', '(ref)', '*', '@', '..', '.', '(', '/'
    }

    def __init__(self, namespaces=None):
        super(XPath1Parser, self).__init__()
        self.namespaces = namespaces if namespaces is not None else {}

    @property
    def version(self):
        return '1.0'

    @classmethod
    def begin(cls):
        super(XPath1Parser, cls).begin()
        globals().update({'selector': cls.selector})

    @classmethod
    def selector(cls, symbol, bp=0):
        def sed_(self, _context, results):
            for elem in results:
                if elem is not None:
                    yield self.value
        return cls.register(symbol, lbp=bp, rbp=bp, sed=sed_)

    def parse(self, path):
        if not path:
            raise ElementPathSyntaxError("empty XPath expression.")
        elif path[-1] == '/':
            raise ElementPathSyntaxError("invalid path: %r" % path)
        if path[:1] == "/":
            path = "." + path
        return super(XPath1Parser, self).parse(path)

    def map_reference(self, ref):
        """
        Map a reference into a fully qualified name using the instance namespace map.

        :param ref: a local name, a prefixed name or a fully qualified name.
        :return: String with a FQN or a local name.
        """
        if ref and ref[0] == '{':
            return ref

        try:
            ns_prefix, name = ref.split(':')
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
            if not ns_prefix or not name:
                raise ElementPathValueError("wrong format for reference name %r" % ref)
            try:
                uri = self.namespaces[ns_prefix]
            except KeyError:
                raise ElementPathValueError("prefix %r not found in namespace map" % ns_prefix)
            else:
                return u'{%s}%s' % (uri, name) if uri else name


##
# XPath1 definitions
XPath1Parser.begin()

register = XPath1Parser.register
literal = XPath1Parser.literal
prefix = XPath1Parser.prefix
infix = XPath1Parser.infix
method = XPath1Parser.method
selector = XPath1Parser.selector


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
# Axes
@method('child::', bp=80)
def nud(self):
    if self.parser.next_token not in ('(ref)', '*', 'text(', 'node('):
        raise ElementPathSyntaxError("invalid child axis %r." % self.parser.next_token)
    self[0:] = self.parser.expression(80),
    return self

@method('child::')
def sed(self, context, results):
    for elem in results:
        if self.iselement(elem):
            for e in elem:
                yield e



selector(literal('(string)'))
selector(literal('(decimal)'))
selector(literal('(integer)'))


@method(literal('(ref)'))
def nud(self):
    if self.value[0] != '{' and ':' in self.value:
        self.value = self.parser.map_reference(self.value)
    return self


@method('(ref)')
@method('*')
def sed(self, _context, results):
    """Children selector."""
    for elem in results:
        if elem is not None:
            for e in elem:
                if self.value is None or e.tag == self.value:
                    yield e


@method('*')
def nud(self):
    if self.parser.next_token.symbol not in ('/', '[', '(end)', ')'):
        self.parser.next_token.unexpected()
    self.value = None
    return self


@method(infix('*', bp=45))
def led(self, left):
    self[0:1] = left, self.parser.expression(45)
    self.value = left.value + self[1].value
    return self


@method('@')
@method('attribute::')
def nud(self):
    self[0:] = self.parser.expression(),
    if self[0].symbol not in ('*', '(ref)'):
        raise ElementPathSyntaxError("invalid attribute specification for XPath.")
    if self.parser.next_token.symbol == '=':
        self.parser.advance('=')
        self[0][0:] = self.parser.advance('(string)'),
    return self


@selector('@')
@selector('attribute::')
def sed(self, _context, results):
    """
    Attribute selector.
    """
    if self[0].symbol != '=':
        # @attribute
        key = self.value
        if key is None:
            for elem in results:
                if elem is not None:
                    for attr in elem.attrib.values():
                        yield attr
        elif '{' == key[0]:
            for elem in results:
                if elem is not None and key in elem.attrib:
                    yield elem.attrib[key]
        else:
            for elem in results:
                if elem is None:
                    continue
                elif key in elem.attrib:
                    yield elem.attrib[key]
    else:
        # @attribute='value'
        key = self.value
        value = self[0].value
        if key is not None:
            for elem in results:
                if elem is not None:
                    yield elem.get(key) == value
        else:
            for elem in results:
                if elem is not None:
                    for attr in elem.attrib.values():
                        yield attr == value


# [tag='value']
@selector('unknown')
def sed(self, _context, results):
    for elem in results:
        if elem is not None:
            for e in elem.findall(self.symbol):
                if "".join(e.itertext()) == self.value:
                    yield elem
                    break


@method(infix('or', bp=20))
@method(infix('|', bp=50))
@method(infix('union', bp=50))
def sed(self, context, results):
    left_results = list(self[0].sed(context, results))
    right_results = list(self[1].sed(context, results))
    for elem in left_results:
        yield elem
    for elem in right_results:
        yield elem


@method(infix('and', bp=25))
def sed(self, context, results):
    right_results = set(self[1].sed(context, results))
    for elem in self[0].sed(context, results):
        if elem in right_results:
            yield elem


# prefix('=', bp=30)
# prefix('<', bp=30)
# prefix('>', bp=30)
# prefix('!=', bp=30)
# prefix('<=', bp=30)
# prefix('>=', bp=30)

infix('=', bp=30)
infix('<', bp=30)
infix('>', bp=30)
infix('!=', bp=30)
infix('<=', bp=30)
infix('>=', bp=30)


@method('+')
def nud(self):
    self[0:] = self.parser.expression(75),
    if not isinstance(self[0].value, int):
        raise ElementPathSyntaxError("an integer value is required: %r." % self[0])
    self.value = self[0].value
    return self


@method(infix('+', bp=40))
def led(self, left):
    self[0:1] = left, self.parser.expression(40)
    self.value = self[0].value + self[1].value
    return self


@method('-')
def nud(self):
    self[0:] = self.parser.expression(75),
    if not isinstance(self[0].value, int):
        raise ElementPathSyntaxError("an integer value is required: %r." % self[0])
    self.value = - self[0].value
    return self


@method(infix('-', bp=40))
def led(self, left):
    self[0:1] = left, self.parser.expression(40)
    self.value = self[0].value - self[1].value
    return self


infix('div', bp=45)
infix('mod', bp=45)



@method('self::', bp=60)
def sed(self, _context, results):
    """Self selector."""
    for elem in results:
        yield elem


@method(literal('.', bp=60))
def sed(self, _context, results):
    """Self node selector."""
    for elem in results:
        if self.iselement(elem):
            yield elem


# @register_nud('parent::node()', bp=60)
@method(prefix('..', bp=60))
def sed(_self, context, results):
    """Parent selector."""
    parent_map = context.parent_map
    results_parents = []
    for elem in results:
        try:
            parent = parent_map[elem]
        except KeyError:
            pass
        else:
            if parent not in results_parents:
                results_parents.append(parent)
                yield parent


# @register_nud('ancestor::', bp=60)
# def parent_token_nud(self):
#    self.sed = self.parent_selector()
#    return self


@method('/')
def nud(self):
    self.parser.token.unexpected()


@method('/', bp=80)
def led(self, left):
    self[0:1] = left, self.parser.expression(100)
    if self[1].symbol not in self.parser.RELATIVE_PATH_SYMBOLS:
        raise ElementPathSyntaxError("invalid child %r." % self[1])
    return self


@method('/')
def sed(self, context, results):
    results = self[0].sed(context, results)
    return self[1].sed(context, results)



@method('//', bp=80)
def led(self, left):
    self[0:1] = left, self.parser.expression(100)
    if self[1].symbol not in self.parser.RELATIVE_PATH_SYMBOLS:
        raise ElementPathSyntaxError("invalid descendant %r." % self[1])
    if self[0].symbol in ('*', '(ref)'):
        delattr(self[0], 'sed')
        self.value = self[0].value
    else:
        self.value = None
    return self


@method('//')
def sed(self, context, results):
    """Descendants selector."""
    results = self[0].sed(context, results)
    for elem in results:
        if elem is not None:
            for e in elem.iter(self[1].value):
                if e is not elem:
                    yield e


@method('(', bp=90)
def nud(self):
    self.parser.next_token.unexpected(')')
    self[0:] = self.parser.expression(),
    self.parser.advance(')')
    return self[0]


@method(')')
def nud(self):
    self.parser.token.unexpected()


@method(')')
def led(self):
    self.parser.token.unexpected()


@method('[', bp=90)
def nud(self):
    self.parser.token.unexpected()


@method('[', bp=90)
def led(self, left):
    self.parser.next_token.unexpected(']')
    self[0:1] = left, self.parser.expression()
    self.parser.advance(']')
    return self


@method('[')
def sed(self, context, results):
    """Predicate selector."""
    results = self[0].sed(context, results)
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
                predicate_results = list(self[1].sed(context, [elem]))
                if predicate_results and any(predicate_results):
                    yield elem


register(']')
# @register_nud(']')
# @register_led(']')
# def predicate_close_token(self, *_args, **_kwargs):
#    self.parser.token.unexpected(']')


@method('last(')
def nud(self):
    self.parser.advance(')')
    if self.parser.next_token.symbol == '-':
        self.parser.advance('-')
        self[0:] = self.parser.advance('(integer)'),
        self.value = -1 - self[0].value
    else:
        self.value = -1
    return self


@method('position(')
def nud(self):
    self.parser.advance(')')
    self.parser.advance('=')
    self[0:] = self.parser.expression(90),
    if not isinstance(self[0].value, int):
        raise ElementPathSyntaxError("an integer expression is required: %r." % self[0].value)
    self.value = self[0].value
    return self


@method('boolean(')
def nud(self):
    """
    Syntax: boolean(expression) --> boolean
    """
    self.parser.next_token.unexpected(')')
    self[0:] = self.parser.expression(),
    self.parser.advance(')')
    print("Value:", self[0].value, self[0].sed)
    self.sed = self.function_selector()
    self.value = bool(self[0].value)
    return self


@method('text(')
def nud(self):
    self.parser.advance(')')
    return self


@method('text(')
def sed(self, context, results):
    for elem in results:
        if self.iselement(elem):
            if elem.text is not None:
                yield elem.text
            if elem.tail is not None:
                yield elem.tail


@method('node(')
def nud(self):
    self.parser.advance(')')
    return self


@method('node(')
def sed(self, context, results):
    for elem in results:
        if self.iselement(elem):
            yield elem


@method('not(')
def nud(self):
    """
    Syntax: not(expression) --> boolean
    """
    self.parser.next_token.unexpected(')')
    self[0:] = self.parser.expression(),
    self.parser.advance(')')
    self.value = not bool(self[0].value)
    return self


@method('true(')
def nud(self):
    """
    Syntax: true() --> boolean (true)
    """
    self.parser.advance(')')
    self.value = True
    return self


@method('false(')
def nud(self):
    """
    Syntax: false() --> boolean (false)
    """
    self.parser.advance(')')
    self.value = False
    return self


XPath1Parser.end()
