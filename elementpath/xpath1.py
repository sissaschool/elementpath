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
from .todp_parser import Token, Parser
from .context import ElementPathContext


class XPathToken(Token):

    def eval(self, context=None):
        return self.value

    def select(self, context, results):
        """
        Select operator that generates results

        :param context: The XPath evaluation context.
        :param results: The XPath selector results. Must be an iterable producing \
        context nodes or other values (simple types or None).
        """
        self.wrong_symbol()

    @staticmethod
    def iselement(elem):
        return hasattr(elem, 'tag') and hasattr(elem, 'attrib') and hasattr(elem, 'text')

    def __str__(self):
        if self.symbol.endswith('::') and len(self.symbol) > 3:
            return '%s axis' % self.symbol[:-2]
        else:
            return super(XPathToken, self).__str__()


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

    @classmethod
    def selector(cls, symbol, bp=0):
        def select(self, context, results):
            for elem in results:
                if self.iselement(elem):
                    context.size = len(elem)
                    for context.position, context.node in enumerate(elem):
                        yield self.eval(context)
                elif elem is not None:
                    context.node, context.position, context.size = elem, 0, 0
                    yield self.eval(context)

        return cls.register(symbol, lbp=bp, rbp=bp, select=select)

    def parse(self, path):
        if not path:
            raise ElementPathSyntaxError("empty XPath expression.")
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
function = XPath1Parser.function


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


@method(literal('(ref)'))
def nud(self):
    if self.value[0] != '{' and ':' in self.value:
        self.value = self.parser.map_reference(self.value)
    return self


@method('(ref)')
def select(self, context):
    if self.iselement(context.node) and context.node.tag == self.value:
        yield context.node


###
# Forward Axes
@method('child::', bp=80)
def nud(self):
    self.parser.next_token.expected('(ref)', '*', 'text(', 'node(')
    self[0:] = self.parser.expression(80),
    return self


@method('child::')
def select(self, context):
    for _ in context.iterchildren():
        for result in self[0].select(context):
            yield result


def select2(self, context):
    if context.node is None:
        context.size, context.position, context.node = 1, 0, context.root
        for result in self[0].select(context):
            yield result
    else:
        elem = context.node
        context.size = len(elem)
        for context.position, context.node in enumerate(elem):
            for result in self[0].select(context):
                yield result


@method('descendant::', bp=80)
@method('descendant-or-self::', bp=80)
def select(self, context, results):
    for elem in results:
        if self.iselement(elem):
            if self.symbol == 'descendant-or-self::':
                yield elem
            for e in elem.iter():
                if e is not elem:
                    yield e


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



@method('@')
@method('attribute::')
def select(self, _context, results):
    """
    Attribute selector.
    """
    if self[0].symbol != '=':
        # @attribute
        key = self.value
        if key is None:
            for elem in results:
                if self.iselement(elem):
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


@method('_@')
@method('_attribute::')
def select(self, _context, results):
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


@method('self::', bp=80)
def select(self, context, results):
    for _ in results:
        yield self


@method('following-sibling::', bp=80)
def select(self, context, results):
    parent_map = context.parent_map
    for elem in results:
        if self.iselement(elem):
            try:
                parent = parent_map[elem]
            except KeyError:
                pass
            else:
                follows = False
                for child in parent:
                    if follows:
                        yield child
                    elif child is elem:
                        follows = True


@method('following::', bp=80)
def select(self, context, results):
    for elem in results:
        ancestors = set(context.get_ancestors(elem))
        follows = False
        for e in context.root.iter():
            if follows:
                if e not in ancestors:
                    yield e
            elif e is elem:
                follows = True


@method('namespace::', bp=80)
def select(self, context, results):
    for elem in results:
        if self.iselement(elem):
            element_class = elem.__class__
            for prefix, uri in self.parser.namespaces.items():
                yield element_class(tag=prefix, text=uri)



###
# Reverse Axes
@method('parent::', bp=80)
def select(self, context, results):
    parent_map = context.parent_map
    parents = {}  # Check if it is needed (maybe repetitions admitted?)
    for elem in results:
        try:
            p = parent_map[elem]
        except KeyError:
            pass
        else:
            if p not in parents:
                yield p
                parents[p] = None


@method('ancestor::', bp=80)
def select(self, context, results):
    for elem in results:
        for e in context.get_ancestors(elem):
            yield e


@method('ancestor-or-self::', bp=80)
def select(self, context, results):
    for elem in results:
        for e in context.get_ancestors(elem):
            yield e
        yield elem


@method('preceding-sibling::', bp=80)
def select(self, context, results):
    parent_map = context.parent_map
    for elem in results:
        if self.iselement(elem):
            try:
                parent = parent_map[elem]
            except KeyError:
                pass
            else:
                for child in parent:
                    if child is elem:
                        break
                    yield child


@method('preceding::', bp=80)
def select(self, context, results):
    for elem in results:
        ancestors = set(context.get_ancestors(elem))
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
def select(self, context=None):
    if self.iselement(context.node):
        if context.node.text is not None:
            yield context.node.text  # adding tails??


@method(function('node(', nargs=0, bp=90))
def select(self, context=None):
    if self.iselement(context.node):
        yield context.node


###
# Node set functions
@method(function('last(', nargs=0, bp=90))
def eval(self, context=None):
    return context.size


@method(function('position(', nargs=0, bp=90))
def eval(self, context=None):
    return context.position


function('count(', nargs=1, bp=90)
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
    return bool(self[0].eval(context))


@method(function('not(', nargs=1, bp=90))
def eval(self, context=None):
    return not bool(self[0].eval(context))


@method(function('true(', nargs=0, bp=90))
def eval(self, context=None):
    return True


@method(function('false(', nargs=0, bp=90))
def eval(self, context=None):
    return False


@method('*')
def select(self, context):
    """Select all element children."""
    if self.iselement(context.node):
        yield context.node


@method('*')
def nud(self):
    self.parser.next_token.expected('/', '[', '(end)', ')')
    return self


@method(infix('*', bp=45))
def eval(self, context=None):
    return self[0].eval(context) * self[1].eval(context)


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


@method('@')
@method('attribute::')
def select(self, _context, results):
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
@method('unknown')
def select(self, _context, results):
    for elem in results:
        if elem is not None:
            for e in elem.findall(self.symbol):
                if "".join(e.itertext()) == self.value:
                    yield elem
                    break


@method(infix('or', bp=20))
@method(infix('|', bp=50))
@method(infix('union', bp=50))
def select(self, _context, results):
    left_results = list(self[0].select(_context, results))
    right_results = list(self[1].select(_context, results))
    for elem in left_results:
        yield elem
    for elem in right_results:
        yield elem


@method(infix('and', bp=25))
def select(self, _context, results):
    right_results = set(self[1].select(_context, results))
    for elem in self[0].select(_context, results):
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


@method(infix('<=', bp=30))
def eval(self, context=None):
    return self[0].eval(context) <= self[1].eval(context)


infix('>=', bp=30)

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
            return +self[0].value()
        except TypeError:
            raise ElementPathTypeError("numeric values are required: %r." % self[:])


prefix('-')
@method(infix('-', bp=40))
def eval(self, context=None):
    if len(self) > 1:
        try:
            return self[0].eval(context) - self[1].eval(context)
        except TypeError:
            raise ElementPathTypeError("a numeric value is required: %r." % self[0])
    else:
        try:
            return -self[0].value()
        except TypeError:
            raise ElementPathTypeError("numeric values are required: %r." % self[:])


@method(infix('-', bp=40))
def eval(self, context=None):
    try:
        return self[0].eval(context) - self[1].eval(context)
    except IndexError:
        return - self[0].eval(context)


infix('div', bp=45)
infix('mod', bp=45)


@method('self::', bp=60)
def select(self, _context, results):
    """Self selector."""
    for elem in results:
        yield elem


@method(literal('.', bp=60))
def select(self, _context, results):
    """Self node selector."""
    for elem in results:
        if self.iselement(elem):
            yield elem


@method(prefix('..', bp=60))
def select(_self, _context, results):
    """Parent selector."""
    parent_map = _context.parent_map
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
#    self.select = self.parent_selector()
#    return self

@method('/', bp=80)
def led(self, left):
    self[0:1] = left, self.parser.expression(100)
    if self[1].symbol not in self.parser.RELATIVE_PATH_SYMBOLS:
        raise ElementPathSyntaxError("invalid child %r." % self[1])
    return self


@method('/')
def select(self, context, results):
    results = self[0].select(context, results)
    return self[1].select(context, results)


@method('//', bp=80)
def led(self, left):
    self[0:1] = left, self.parser.expression(100)
    if self[1].symbol not in self.parser.RELATIVE_PATH_SYMBOLS:
        raise ElementPathSyntaxError("invalid descendant %r." % self[1])
    if self[0].symbol in ('*', '(ref)'):
        delattr(self[0], 'select')
        self.value = self[0].value
    else:
        self.value = None
    return self


@method('//')
def select(self, _context, results):
    """Descendants selector."""
    results = self[0].select(_context, results)
    for elem in results:
        if self.iselement(elem):
            for e in elem.iter(self[1].value):
                if e is not elem:
                    yield e

@method('//')
def select(self, context):
    """Descendants selector."""
    for results in self[0].select(context):
        for elem in results:
            if self.iselement(elem):
                for e in elem.iter(self[1].value):
                    if e is not elem:
                        yield e


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
