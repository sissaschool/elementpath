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
from urllib.parse import urlsplit

from ..namespaces import XPATH_FUNCTIONS_NAMESPACE, XPATH_MATH_FUNCTIONS_NAMESPACE, \
    XSLT_XQUERY_SERIALIZATION_NAMESPACE
from ..xpath_nodes import etree_iterpath, is_xpath_node, \
    is_document_node, is_etree_element, TypedElement
from ..xpath_context import XPathSchemaContext
from ..xpath2 import XPath2Parser
from ..datatypes import NumericProxy, QName
from ..regex import translate_pattern, RegexError


class XPath30Parser(XPath2Parser):
    """
    XPath 3.0 expression parser class.
    """
    version = '3.0'

    SYMBOLS = XPath2Parser.SYMBOLS | {
        'Q{',  # see BracedURILiteral rule

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
        'function-lookup', 'function-name', 'function-arity',
        # 'for-each', 'filter', 'fold-left', 'fold-right', 'for-each-pair',

        # Reserved and node type functions
        # 'function', 'namespace-node', 'switch',
    }

    DEFAULT_NAMESPACES = {
        'math': XPATH_MATH_FUNCTIONS_NAMESPACE, **XPath2Parser.DEFAULT_NAMESPACES
    }


##
# XPath 3.0 definitions
register = XPath30Parser.register
unregister = XPath30Parser.unregister
literal = XPath30Parser.literal
prefix = XPath30Parser.prefix
infix = XPath30Parser.infix
infixr = XPath30Parser.infixr
method = XPath30Parser.method
function = XPath30Parser.function

XPath30Parser.duplicate('{', 'Q{')


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
# Formatting functions
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


# Higher-order functions
# 'function-lookup', 'function-name', 'function-arity',
# 'for-each', 'filter', 'fold-left', 'fold-right', 'for-each-pair',

@method(function('function-lookup', nargs=2))
def evaluate(self, context=None):
    name = self.get_argument(context, cls=QName)
    arity = self.get_argument(context, index=1, cls=int)


@method(function('function-name', nargs=1))
def evaluate(self, context=None):
    function = self.get_argument(context)


@method(function('function-arity', nargs=1))
def evaluate(self, context=None):
    function = self.get_argument(context)


XPath30Parser.build()
