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
XPath 3.0 implementation

Refs:
  - https://www.w3.org/TR/2014/REC-xpath-30-20140408/
  - https://www.w3.org/TR/xpath-functions-30/
"""
import os
import re
import codecs
import math
import xml.etree.ElementTree as ElementTree
from copy import copy
from urllib.parse import urlsplit

from ..namespaces import XPATH_FUNCTIONS_NAMESPACE, XPATH_MATH_FUNCTIONS_NAMESPACE, \
    XSLT_XQUERY_SERIALIZATION_NAMESPACE
from ..xpath_nodes import etree_iterpath, is_xpath_node, \
    is_document_node, is_etree_element, TypedElement
from ..xpath_token import ValueToken, XPathFunction
from ..xpath_context import XPathSchemaContext
from ..xpath2 import XPath2Parser
from ..datatypes import NumericProxy, QName
from ..regex import translate_pattern, RegexError


class XPath30Parser(XPath2Parser):
    """
    XPath 3.0 expression parser class. Accepts all XPath 2.0 options as keyword
    arguments, but the *strict* option is ignored because XPath 3.0+ has braced
    URI literals and the expanded name syntax is not compatible.

    :param args: the same positional arguments of class :class:`XPath2Parser`.
    :param decimal_formats: a mapping with statically known decimal formats.
    :param kwargs: the same keyword arguments of class :class:`XPath2Parser`.
    """
    version = '3.0'

    SYMBOLS = XPath2Parser.SYMBOLS | {
        'Q{',  # see BracedURILiteral rule
        '||',  # concat operator

        # Math functions (trigonometric and exponential)
        'pi', 'exp', 'exp10', 'log', 'log10', 'pow', 'sqrt',
        'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'atan2',

        # Formatting functions
        'format-integer', 'format-number', 'format-dateTime',
        'format-date', 'format-time',

        # String functions that use regular expressions
        'analyze-string',

        # Functions and operators on nodes
        'path', 'has-children', 'innermost', 'outermost',

        # Functions and operators on sequences
        'head', 'tail', 'generate-id', 'uri-collection',
        'unparsed-text', 'unparsed-text-lines', 'unparsed-text-available',
        'environment-variable', 'available-environment-variables',

        # Parsing and serializing
        'parse-xml', 'parse-xml-fragment', 'serialize',

        # Higher-order functions
        'function-lookup', 'function-name', 'function-arity', '#', '?',
        'for-each', 'filter', 'fold-left', 'fold-right', 'for-each-pair',

        # Expressions and node type functions
        'function', 'let', ':=',  # 'namespace-node', 'switch',
    }

    DEFAULT_NAMESPACES = {
        'math': XPATH_MATH_FUNCTIONS_NAMESPACE, **XPath2Parser.DEFAULT_NAMESPACES
    }

    function_signatures = XPath2Parser.function_signatures.copy()

    def __init__(self, *args, decimal_formats=None, **kwargs):
        kwargs.pop('strict', None)
        super(XPath30Parser, self).__init__(*args, **kwargs)
        self.decimal_formats = decimal_formats if decimal_formats is not None else {}


##
# XPath 3.0 definitions
register = XPath30Parser.register
literal = XPath30Parser.literal
infix = XPath30Parser.infix
method = XPath30Parser.method
function = XPath30Parser.function
signature = XPath30Parser.signature

register(':=')


XPath30Parser.unregister('?')
register('?', bases=(ValueToken,))


@method('?')
def nud(self):
    return self


###
# Braced/expanded QName(s)
XPath30Parser.duplicate('{', 'Q{')
XPath30Parser.unregister('{')
XPath30Parser.unregister('}')
register('{')
register('}', bp=100)


XPath30Parser.unregister('(')


@method(register('(', lbp=80, rpb=80, label='expression'))
def nud(self):
    if self.parser.next_token.symbol != ')':
        self[:] = self.parser.expression(),
    self.parser.advance(')')
    return self


@method('(')
def led(self, left):
    if left.symbol == '(name)' or left.symbol == ':' and left[1].symbol == '(name)':
        raise self.error('XPST0017', 'unknown function {!r}'.format(left.value))
    if self.parser.next_token.symbol != ')':
        self[:] = left, self.parser.expression()
    else:
        self[:] = left,
    self.parser.advance(')')
    return self


@method('(')
def evaluate(self, context=None):
    if len(self) < 2:
        return self[0].evaluate(context) if self else []

    result = self[0].evaluate(context)
    if isinstance(result, list) and len(result) == 1:
        result = result[0]

    if not isinstance(result, XPathFunction):
        raise self.error('XPST0017', 'an XPath function expected, not {!r}'.format(type(result)))
    return result(context, self[1])


@method('(')
def select(self, context=None):
    if len(self) < 2:
        yield from self[0].select(context) if self else iter(())
    else:

        value = self[0].evaluate(context)
        if not isinstance(value, XPathFunction):
            raise self.error('XPST0017', 'an XPath function expected, not {!r}'.format(type(value)))
        result = value(context, self[1])
        if isinstance(result, list):
            yield from result
        else:
            yield result


@method(infix('||', bp=32))
def evaluate(self, context=None):
    return self.string_value(self.get_argument(context)) + \
        self.string_value(self.get_argument(context, index=1))


###
# 'let' expressions

@method(register('let', lbp=20, rbp=20, label='let expression'))
def nud(self):
    del self[:]
    if self.parser.next_token.symbol != '$':
        token = self.parser.symbol_table['(name)'](self.parser, self.symbol)
        return token.nud()

    while True:
        self.parser.next_token.expected('$')
        variable = self.parser.expression(5)
        self.append(variable)
        self.parser.advance(':=')
        expr = self.parser.expression(5)
        self.append(expr)
        if self.parser.next_token.symbol != ',':
            break
        self.parser.advance()

    self.parser.advance('return')
    self.append(self.parser.expression(5))
    return self


@method('let')
def select(self, context=None):
    if context is None:
        raise self.missing_context()

    context = copy(context)
    varnames = [self[k][0].value for k in range(0, len(self) - 1, 2)]
    values = [self[k].evaluate(copy(context)) for k in range(1, len(self) - 1, 2)]

    context.variables.update(x for x in zip(varnames, values))
    yield from self[-1].select(context)


###
# 'inline function' expression
@method(register('function', bp=90, label='inline function', bases=(XPathFunction,)))
def nud(self):
    if self.parser.next_token.symbol != '(':
        token = self.parser.symbol_table['(name)'](self.parser, self.symbol)
        return token.nud()

    self.parser.advance('(')
    self.params = {}
    while self.parser.next_token.symbol != ')':
        self.parser.next_token.expected('$')
        param = self.parser.expression(5)
        self.append(param)
        if self.parser.next_token.symbol == 'as':
            self.parser.advance('as')
            sequence_type = self.parser.expression(5)
            self.append(sequence_type)

        self.parser.next_token.expected(')', ',')
        if self.parser.next_token.symbol == ',':
            self.parser.advance()
            self.parser.next_token.unexpected(')')

    self.parser.advance(')')

    if self.parser.next_token.symbol == 'as':
        self.parser.advance('as')
        if self.parser.next_token.label not in ('kind test', 'sequence type'):
            self.parser.expected_name('(name)', ':')
        sequence_type = self.parser.expression(rbp=90)

        next_symbol = self.parser.next_token.symbol
        if sequence_type.symbol != 'empty-sequence' and next_symbol in ('?', '*', '+'):
            self.parser.symbol_table[next_symbol](self.parser),  # Add nullary token
            self.parser.advance()

    self.parser.advance('{')
    self.expr = self.parser.expression()
    self.parser.advance('}')
    return self


@method('function')
def evaluate(self, context=None):
    if context is None:
        raise self.missing_context()
    return self.expr.evaluate(context)


###
# Mathematical functions
@method(function('pi', label='math function', nargs=0))
def evaluate(self, context):
    return math.pi


@method(function('exp', label='math function', nargs=1))
def evaluate(self, context):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        return math.exp(arg)


@method(function('exp10', label='math function', nargs=1))
def evaluate(self, context):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        return float(10 ** arg)


@method(function('log', label='math function', nargs=1))
def evaluate(self, context):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        return float('-inf') if not arg else float('nan') if arg <= -1 else math.log(arg)


@method(function('log10', label='math function', nargs=1))
def evaluate(self, context):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        return float('-inf') if not arg else float('nan') if arg <= -1 else math.log10(arg)


@method(function('pow', label='math function', nargs=2))
def evaluate(self, context):
    x = self.get_argument(context, cls=NumericProxy)
    y = self.get_argument(context, index=1, required=True, cls=NumericProxy)
    if x is not None:
        if not x and y < 0:
            return float('inf')

        try:
            return float(x ** y)
        except TypeError:
            return float('nan')


@method(function('sqrt', label='math function', nargs=1))
def evaluate(self, context):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        if arg < 0:
            return float('nan')
        return math.sqrt(arg)


@method(function('sin', label='math function', nargs=1))
def evaluate(self, context):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        if math.isinf(arg):
            return float('nan')
        return math.sin(arg)


@method(function('cos', label='math function', nargs=1))
def evaluate(self, context):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        if math.isinf(arg):
            return float('nan')
        return math.cos(arg)


@method(function('tan', label='math function', nargs=1))
def evaluate(self, context):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        if math.isinf(arg):
            return float('nan')
        return math.tan(arg)


@method(function('asin', label='math function', nargs=1))
def evaluate(self, context):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        if arg < -1 or arg > 1:
            return float('nan')
        return math.asin(arg)


@method(function('acos', label='math function', nargs=1))
def evaluate(self, context):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        if arg < -1 or arg > 1:
            return float('nan')
        return math.acos(arg)


@method(function('atan', label='math function', nargs=1))
def evaluate(self, context):
    arg = self.get_argument(context, cls=NumericProxy)
    if arg is not None:
        return math.atan(arg)


@method(function('atan2', label='math function', nargs=2))
def evaluate(self, context):
    x = self.get_argument(context, cls=NumericProxy)
    y = self.get_argument(context, index=1, required=True, cls=NumericProxy)
    return math.atan2(x, y)


###
# TODO: Formatting functions
@method(function('format-integer', nargs=(2, 3)))
def evaluate(self, context):
    value = self.get_argument(context, cls=NumericProxy)
    if value is None:
        return ''


@method(function('format-number', nargs=(2, 3)))
def evaluate(self, context):
    value = self.get_argument(context, cls=NumericProxy)
    if value is None:
        return ''


@method(function('format-dateTime', nargs=(2, 3)))
def evaluate(self, context):
    value = self.get_argument(context, cls=NumericProxy)
    if value is None:
        return ''


@method(function('format-date', nargs=(2, 5)))
def evaluate(self, context):
    value = self.get_argument(context, cls=NumericProxy)
    if value is None:
        return None


@method(function('format-time', nargs=(2, 3)))
def evaluate(self, context):
    value = self.get_argument(context, cls=NumericProxy)
    if value is None:
        return ''


###
# String functions that use regular expressions
@method(function('analyze-string', nargs=(2, 3)))
def evaluate(self, context=None):
    input_string = self.get_argument(context, default='', cls=str)
    pattern = self.get_argument(context, 1, required=True, cls=str)
    flags = 0
    if len(self) > 2:
        for c in self.get_argument(context, 2, required=True, cls=str):
            if c in 'smix':
                flags |= getattr(re, c.upper())
            else:
                raise self.error('FORX0001', "Invalid regular expression flag %r" % c)

    try:
        python_pattern = translate_pattern(pattern, flags, self.parser.xsd_version)
        compiled_pattern = re.compile(python_pattern, flags=flags)
    except (re.error, RegexError) as err:
        msg = "Invalid regular expression: {}"
        raise self.error('FORX0002', msg.format(str(err))) from None
    except OverflowError as err:
        raise self.error('FORX0002', err) from None

    etree = ElementTree if context is None else context.etree
    lines = ['<analyze-string-result xmlns="{}">'.format(XPATH_FUNCTIONS_NAMESPACE)]
    k = 0

    while k < len(input_string):
        match = compiled_pattern.search(input_string, k)
        if match is None:
            lines.append('  <non-match>{}</non-match>'.format(input_string[k:]))
            break
        elif not match.groups():
            start, stop = match.span()
            if start > k:
                lines.append('  <non-match>{}</non-match>'.format(input_string[k:start]))
            lines.append('  <match>{}</match>'.format(input_string[start:stop]))
            k = stop
        else:
            start, stop = match.span()
            if start > k:
                lines.append('  <non-match>{}</non-match>'.format(input_string[k:start]))
                k = start

            group_string = []
            group_tmpl = '<group nr="{}">{}</group>'
            for idx in range(1, len(match.groups()) + 1):
                start, stop = match.span(idx)
                if start > k:
                    group_string.append(input_string[k:start])
                group_string.append(group_tmpl.format(idx, input_string[start:stop]))
                k = stop
            lines.append('  <match>{}</match>'.format(''.join(group_string)))

    lines.append('</analyze-string-result>')
    return etree.XML('\n'.join(lines))


###
# Functions and operators on nodes
@method(function('path', nargs=(0, 1)))
def evaluate(self, context=None):
    if context is None:
        raise self.missing_context()
    elif isinstance(context, XPathSchemaContext):
        return
    elif not self:
        if context.item is None:
            return '/'
        item = context.item
    else:
        item = self.get_argument(context)
        if item is None:
            return

    if is_document_node(item):
        return '/'
    elif isinstance(item, TypedElement):
        elem = item.elem
    elif is_etree_element(item):
        elem = item
    else:
        elem = self._elem

    try:
        root = context.root.getroot()
    except AttributeError:
        root = context.root
        path = 'Q{%s}root()' % XPATH_FUNCTIONS_NAMESPACE
    else:
        path = '/%s' % root.tag

    for e, path in etree_iterpath(root, path):
        if e is elem:
            return path


@method(function('has-children', nargs=(0, 1)))
def evaluate(self, context=None):
    if context is None:
        raise self.missing_context()
    elif not self:
        if context.item is None:
            return is_document_node(context.root)

        item = context.item
        if not is_xpath_node(item):
            raise self.error('XPTY0004', 'context item must be a node')
    else:
        item = self.get_argument(context)
        if item is None:
            return False
        elif not is_xpath_node(item):
            raise self.error('XPTY0004', 'argument must be a node')

    return is_document_node(item) or \
        is_etree_element(item) and len(item) > 0 or \
        isinstance(item, TypedElement) and len(item.elem) > 0


@method(function('innermost', nargs=1))
def select(self, context=None):
    if context is None:
        raise self.missing_context()

    context = context.copy()
    nodes = [e for e in self[0].select(context)]
    if any(not is_xpath_node(x) for x in nodes):
        raise self.error('XPTY0004', 'argument must contain only nodes')

    ancestors = {x for context.item in nodes for x in context.iter_ancestors(axis='ancestor')}
    yield from context.iter_results([x for x in nodes if x not in ancestors])


@method(function('outermost', nargs=1))
def select(self, context=None):
    if context is None:
        raise self.missing_context()

    context = context.copy()
    nodes = {e for e in self[0].select(context)}
    if any(not is_xpath_node(x) for x in nodes):
        raise self.error('XPTY0004', 'argument must contain only nodes')

    yield from context.iter_results([
        context.item for context.item in nodes
        if all(x not in nodes for x in context.iter_ancestors(axis='ancestor'))
    ])


##
# Functions and operators on sequences

@method(function('head', nargs=1))
def evaluate(self, context=None):
    for item in self[0].select(context):
        return item


@method(function('tail', nargs=1))
def select(self, context=None):
    for k, item in enumerate(self[0].select(context)):
        if k:
            yield item


@method(function('generate-id', nargs=(0, 1)))
def evaluate(self, context=None):
    arg = self.get_argument(context, default_to_context=True)
    if arg is None:
        return ''
    elif not is_xpath_node(arg):
        if self:
            raise self.error('XPTY0004', "argument is not a node")
        raise self.error('XPTY0004', "context item is not a node")
    else:
        return 'ID-{}'.format(id(arg))


@method(function('uri-collection', nargs=(0, 1)))
def evaluate(self, context=None):
    uri = self.get_argument(context)
    if context is None:
        raise self.missing_context()
    elif isinstance(context, XPathSchemaContext):
        return
    elif not self or uri is None:
        if context.default_resource_collection is None:
            raise self.error('FODC0002', 'no default resource collection has been defined')
        resource_collection = context.default_resource_collection
    else:
        uri = self.get_absolute_uri(uri)
        try:
            resource_collection = context.resource_collections[uri]
        except (KeyError, TypeError):
            url_parts = urlsplit(uri)
            if url_parts.scheme in ('', 'file') and \
                    not url_parts.path.startswith(':') and url_parts.path.endswith('/'):
                raise self.error('FODC0003', 'collection URI is a directory')
            raise self.error('FODC0002', '{!r} collection not found'.format(uri)) from None

    if not self.parser.match_sequence_type(resource_collection, 'xs:anyURI*'):
        raise self.wrong_sequence_type("Type does not match sequence type xs:anyURI*")

    return resource_collection


@method(function('unparsed-text', nargs=(1, 2)))
@method(function('unparsed-text-lines', nargs=(1, 2)))
@method(function('unparsed-text-available', nargs=(1, 2)))
def evaluate(self, context=None):
    from urllib.request import urlopen  # optional because it consumes ~4.3 MiB

    href = self.get_argument(context, cls=str)
    if href is None:
        return
    elif urlsplit(href).fragment:
        raise self.error('FOUT1170')

    if len(self) > 1:
        encoding = self.get_argument(context, index=1, required=True, cls=str)
    else:
        encoding = 'UTF-8'

    uri = self.get_absolute_uri(href)
    try:
        codecs.lookup(encoding)
    except LookupError:
        raise self.error('FOUT1190') from None

    with urlopen(uri) as rp:
        obj = rp.read()

    return codecs.decode(obj, encoding)


@method(function('environment-variable', nargs=1))
def evaluate(self, context=None):
    name = self.get_argument(context, required=True, cls=str)
    if context is None:
        raise self.missing_context()
    elif not context.allow_environment:
        return
    else:
        return os.environ.get(name)


@method(function('available-environment-variables', nargs=0))
def evaluate(self, context=None):
    if context is None:
        raise self.missing_context()
    elif not context.allow_environment:
        return
    else:
        return list(os.environ)


###
# Parsing and serializing
@method(function('parse-xml', nargs=1))
@method(function('parse-xml-fragment', nargs=1))
def evaluate(self, context=None):
    # TODO: resolve relative entity references with static base URI
    arg = self.get_argument(context, cls=str)
    if arg is None:
        return

    etree = ElementTree if context is None else context.etree
    if self.symbol == 'parse-xml-fragment':
        # Wrap argument in a fake document because an
        # XML document can have only one root element
        arg = '<document>{}</document>'.format(arg)

    try:
        root = etree.XML(arg)
    except etree.ParseError:
        raise self.error('FODC0006')
    else:
        return etree.ElementTree(root)


@method(function('serialize', nargs=(1, 2)))
def evaluate(self, context=None):
    # TODO full implementation of serialization with
    #  https://www.w3.org/TR/xpath-functions-30/#xslt-xquery-serialization-30

    params = self.get_argument(context, index=1) if len(self) == 2 else None
    if params is None:
        tmpl = '<output:serialization-parameters xmlns:output="{}"/>'
        params = ElementTree.XML(tmpl.format(XSLT_XQUERY_SERIALIZATION_NAMESPACE))

    chunks = []
    etree = ElementTree if context is None else context.etree
    kwargs = {}

    child = params.find(
        'output:serialization-parameters/omit-xml-declaration',
        namespaces={'output': XSLT_XQUERY_SERIALIZATION_NAMESPACE},
    )
    if child is not None and child.get('value') in ('yes',):
        kwargs['xml_declaration'] = True

    for item in self[0].select(context):
        if is_etree_element(item):
            try:
                serialized_item = etree.tostring(item, encoding='utf-8', **kwargs)
            except TypeError:
                serialized_item = etree.tostring(item, encoding='utf-8')

            chunks.append(serialized_item)

    return b'\n'.join(chunks)


###
# Higher-order functions

@method(function('function-lookup', nargs=2))
def evaluate(self, context=None):
    qname = self.get_argument(context, cls=QName)
    arity = self.get_argument(context, index=1, cls=int)

    # TODO: complete function signatures
    # if (qname, arity) not in self.parser.function_signatures:
    #    raise self.error('XPST0017')

    try:
        return self.parser.symbol_table[qname.local_name](self.parser, nargs=arity)
    except (KeyError, TypeError):
        raise self.error('XPST0017', "unknown function {}".format(qname.local_name))


@method(function('function-name', nargs=1))
def evaluate(self, context=None):
    if isinstance(self[0], XPathFunction):
        func = self[0]
    else:
        func = self.get_argument(context, cls=XPathFunction)

    return [] if func.name is None else func.name


@method(function('function-arity', nargs=1))
def evaluate(self, context=None):
    if isinstance(self[0], XPathFunction):
        return self[0].arity

    func = self.get_argument(context, cls=XPathFunction)
    return func.arity


@method('#', bp=50)
def led(self, left):
    left.expected(':', '(name)')
    self[:] = left, self.parser.expression(rbp=50)
    self[1].expected('(integer)')
    return self


@method('#')
def evaluate(self, context=None):
    if self[0].symbol == ':':
        qname = QName(self[0][1].namespace, self[0].value)
    else:
        qname = QName(XPATH_FUNCTIONS_NAMESPACE, self[0].value)
    arity = self[1].value

    # TODO: complete function signatures
    # if (qname, arity) not in self.parser.function_signatures:
    #    raise self.error('XPST0017')

    try:
        return self.parser.symbol_table[qname.local_name](self.parser, nargs=arity)
    except (KeyError, TypeError):
        raise self.error('XPST0017', "unknown function {}".format(qname.local_name))


@method(function('for-each', nargs=2))
def select(self, context=None):
    func = self[1][1] if self[1].symbol == ':' else self[1]
    if not isinstance(func, XPathFunction):
        func = self.get_argument(context, index=1, cls=XPathFunction)

    for item in self[0].select(copy(context)):
        result = func(context, argument_list=[item])
        if isinstance(result, list):
            yield from result
        else:
            yield result


@method(function('filter', nargs=2))
def select(self, context=None):
    func = self[1][1] if self[1].symbol == ':' else self[1]
    if not isinstance(func, XPathFunction):
        func = self.get_argument(context, index=1, cls=XPathFunction)

    for item in self[0].select(copy(context)):
        if self.boolean_value(func(context, argument_list=[item])):
            yield item


@method(function('fold-left', nargs=3))
def select(self, context=None):
    func = self[2][1] if self[2].symbol == ':' else self[2]
    if not isinstance(func, XPathFunction):
        func = self.get_argument(context, index=2, cls=XPathFunction)
    zero = self.get_argument(context, index=1)

    result = zero
    for item in self[0].select(copy(context)):
        result = func(context, argument_list=[result, item])

    if isinstance(result, list):
        yield from result
    else:
        yield result


@method(function('fold-right', nargs=3))
def select(self, context=None):
    func = self[2][1] if self[2].symbol == ':' else self[2]
    if not isinstance(func, XPathFunction):
        func = self.get_argument(context, index=2, cls=XPathFunction)
    zero = self.get_argument(context, index=1)

    result = zero
    sequence = [x for x in self[0].select(copy(context))]

    for item in reversed(sequence):
        result = func(context, argument_list=[item, result])

    if isinstance(result, list):
        yield from result
    else:
        yield result


@method(function('for-each-pair', nargs=3))
def select(self, context=None):
    func = self[2][1] if self[2].symbol == ':' else self[2]
    if not isinstance(func, XPathFunction):
        func = self.get_argument(context, index=2, cls=XPathFunction)

    for item1, item2 in zip(self[0].select(copy(context)), self[1].select(copy(context))):
        result = func(context, argument_list=[item1, item2])
        if isinstance(result, list):
            yield from result
        else:
            yield result


###
# Math functions signatures
#
signature('function() as xs:double', 'pi', prefix='math')
signature('function(xs:double?) as xs:double?', 'exp', 'exp10', 'log', 'log10',
          'sqrt', 'sin', 'cos', 'tan', 'asin', 'acos', 'atan', prefix='math')
signature('function(xs:double?, numeric) as xs:double?', 'pow', prefix='math')
signature('function(xs:double, xs:double) as xs:double', 'atan2', prefix='math')

signature('function(xs:integer?, xs:string) as xs:string', 'format-integer')
signature('function(xs:integer?, xs:string, xs:string?) as xs:string', 'format-integer')
signature('function(numeric?, xs:string) as xs:string', 'format-number')
signature('function(numeric?, xs:string, xs:string?) as xs:string', 'format-number')
signature('function(xs:dateTime?, xs:string) as xs:string?',
          'format-dateTime', 'format-date', 'format-time')
signature('function(xs:dateTime?, xs:string, xs:string?, xs:string?, xs:string?) as xs:string?',
          'format-dateTime', 'format-date', 'format-time')

signature('function(xs:string?, xs:string) as element(fn:analyze-string-result)',
          'analyze-string')
signature('function(xs:string?, xs:string, xs:string) as element(fn:analyze-string-result)',
          'analyze-string')

signature('function() as xs:string?', 'path')
signature('function(node()?) as xs:string?', 'path')

signature('function() as xs:boolean', 'has-children')
signature('function(node()?) as xs:boolean', 'has-children')
signature('function(node()*) as node()*', 'innermost', 'outermost')
signature('function(item()*) as item()?', 'head', 'tail')
signature('function() as xs:string', 'generate-id')
signature('function(node()?) as xs:string', 'generate-id')

signature('function() as xs:anyURI*', 'uri-collection')
signature('function(xs:string?) as xs:anyURI*', 'uri-collection')

signature('function(xs:string?) as xs:string?', 'unparsed-text')
signature('function(xs:string?, xs:string) as xs:string?', 'unparsed-text')
signature('function(xs:string?) as xs:string*', 'unparsed-text-lines')
signature('function(xs:string?, xs:string) as xs:string*', 'unparsed-text-lines')
signature('function(xs:string?) as xs:boolean', 'unparsed-text-available')
signature('function(xs:string?, xs:string) as xs:boolean', 'unparsed-text-available')

signature('function(xs:string) as xs:string?', 'environment-variable')
signature('function() as xs:string*', 'available-environment-variables')

signature('function(xs:string?) as document-node(element(*))?', 'parse-xml')
signature('function(xs:string?) as document-node()?', 'parse-xml-fragment')
signature('function(item()*) as xs:string', 'serialize')
signature('function(item()*, element(output:serialization-parameters)?) as xs:string',
          'serialize')

signature('function(item()*, function(item()) as item()*) as item()*', 'for-each')
