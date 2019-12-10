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
"""
XPath 2.0 implementation - part 2 (functions)
"""
import sys
import decimal
import math
import datetime
import time
import re
import locale
import unicodedata
import xml.etree.ElementTree as ElementTree

from .compat import PY3, string_base_type, unicode_chr, urlparse, urljoin, \
    urllib_quote, unicode_type, URLError
from .datatypes import QNAME_PATTERN, DateTime10, Date10, Time, Timezone, Duration, DayTimeDuration
from .namespaces import prefixed_to_qname, get_namespace, XML_ID
from .xpath_context import XPathContext, XPathSchemaContext
from .xpath_nodes import AttributeNode, is_document_node, is_xpath_node, is_element_node, \
    is_attribute_node, node_name, node_is_id, node_is_idrefs, node_nilled, node_base_uri, \
    node_document_uri, node_kind, etree_deep_equal
from .xpath2_parser import XPath2Parser

method = XPath2Parser.method
function = XPath2Parser.function

WRONG_REPLACEMENT_PATTERN = re.compile(r'(?<!\\)\$([^\d]|$)|((?<=[^\\])|^)\\([^$]|$)|\\\\\$')


###
# Sequence types (allowed only for type checking in treat-as/instance-of statements)
@method(function('empty-sequence', nargs=0, label='sequence type'))
def evaluate(self, context=None):
    if context is not None:
        return isinstance(context.item, list) and not context.item


@method(function('item', nargs=0, label='sequence type'))
def evaluate(self, context=None):
    if context is None:
        return
    elif context.item is None:
        return context.root
    else:
        return context.item


###
# Kind tests (sequence types that can appear also in XPath expressions)
@method(function('document-node', nargs=(0, 1), label='kind test'))
def evaluate(self, context=None):
    if context is not None:
        if context.item is None and is_document_node(context.root):
            if not self:
                return context.root
            elif is_element_node(context.root.getroot(), self[0].evaluate(context)):
                return context.root


@method(function('element', nargs=(0, 2), label='kind test'))
def evaluate(self, context=None):
    if context is not None:
        if not self:
            if is_element_node(context.item):
                return context.item
        elif is_element_node(context.item, self[0].evaluate(context)):
            if len(self) == 1:
                return context.item
            elif self.xsd_type is not None:
                type_annotation = self[1].evaluate(context)
                if self.xsd_type.is_matching(type_annotation, self.parser.default_namespace):
                    return context.item


@method(function('schema-attribute', nargs=1, label='kind test'))
def evaluate(self, context=None):
    attribute_name = self[0].source
    qname = prefixed_to_qname(attribute_name, self.parser.namespaces)
    if self.parser.schema.get_attribute(qname) is None:
        self.missing_name("attribute %r not found in schema" % attribute_name)

    if context is not None:
        if is_attribute_node(context.item, qname):
            return context.item


@method(function('schema-element', nargs=1, label='kind test'))
def evaluate(self, context=None):
    element_name = self[0].source
    qname = prefixed_to_qname(element_name, self.parser.namespaces)
    if self.parser.schema.get_element(qname) is None \
            and self.parser.schema.get_substitution_group(qname) is None:
        self.missing_name("element %r not found in schema" % element_name)

    if context is not None:
        if is_element_node(context.item) and context.item.tag == qname:
            return context.item


@method('document-node')
@method('element')
@method('schema-attribute')
@method('schema-element')
def select(self, context=None):
    if context is not None:
        for _ in context.iter_children_or_self():
            item = self.evaluate(context)
            if item is not None:
                yield item


###
# Function for QNames
@method(function('prefix-from-QName', nargs=1))
def evaluate(self, context=None):
    qname = self.get_argument(context)
    if qname is None:
        return []
    elif not isinstance(qname, string_base_type):
        raise self.error('FORG0006', 'argument has an invalid type %r' % type(qname))
    match = QNAME_PATTERN.match(qname)
    if match is None:
        raise self.error('FOCA0002', 'argument must be an xs:QName')
    return match.groupdict()['prefix'] or []


@method(function('local-name-from-QName', nargs=1))
def evaluate(self, context=None):
    qname = self.get_argument(context)
    if qname is None:
        return []
    elif not isinstance(qname, string_base_type):
        raise self.error('FORG0006', 'argument has an invalid type %r' % type(qname))
    match = QNAME_PATTERN.match(qname)
    if match is None:
        raise self.error('FOCA0002', 'argument must be an xs:QName')
    return match.groupdict()['local']


@method(function('namespace-uri-from-QName', nargs=1))
def evaluate(self, context=None):
    qname = self.get_argument(context)
    if qname is None:
        return []
    elif not isinstance(qname, string_base_type):
        raise self.error('FORG0006', 'argument has an invalid type %r' % type(qname))
    match = QNAME_PATTERN.match(qname)
    if match is None:
        raise self.error('FOCA0002', 'argument must be an xs:QName')
    prefix = match.groupdict()['prefix'] or ''

    try:
        namespace = self.parser.namespaces[prefix]
    except KeyError as err:
        raise self.error('FONS0004', 'No namespace found for prefix %s' % str(err))
    else:
        if not namespace and prefix:
            raise self.error('XPST0081', 'Prefix %r is associated to no namespace' % prefix)
        return namespace


@method(function('namespace-uri-for-prefix', nargs=2))
def evaluate(self, context=None):
    if context is not None:
        prefix = self.get_argument(context.copy())
        if prefix is None:
            prefix = ''
        if not isinstance(prefix, string_base_type):
            raise self.error('FORG0006', '1st argument has an invalid type %r' % type(prefix))

        elem = self.get_argument(context, index=1)
        if not is_element_node(elem):
            raise self.error('FORG0006', '2nd argument %r is not a node' % elem)
        ns_uris = {get_namespace(e.tag) for e in elem.iter()}
        for p, uri in self.parser.namespaces.items():
            if uri in ns_uris:
                if p == prefix:
                    if not prefix or uri:
                        return uri
                    else:
                        raise self.error('XPST0081', 'Prefix %r is associated to no namespace' % prefix)
        return []


@method(function('in-scope-prefixes', nargs=1))
def select(self, context=None):
    if context is not None:
        elem = self.get_argument(context)
        if not is_element_node(elem):
            raise self.error('FORG0006', 'argument %r is not a node' % elem)

        if isinstance(context, XPathSchemaContext):
            # For schema context returns prefixes of static namespaces
            for prefix in self.parser.namespaces:
                yield prefix
        elif hasattr(elem, 'nsmap'):
            # For lxml returns Element's prefixes
            for prefix in elem.nsmap:
                yield prefix or ''
        else:
            # For ElementTree returns module registered prefixes
            prefixes = {x for x in self.parser.namespaces}
            etree_nsmap = getattr(ElementTree, '_namespace_map', {})
            prefixes.update(x for x in etree_nsmap.values())
            for prefix in prefixes:
                yield prefix


@method(function('resolve-QName', nargs=2))
def evaluate(self, context=None):
    if context is not None:
        elem = self.get_argument(context, index=1)
        if not is_element_node(elem):
            raise self.error('FORG0006', '2nd argument %r is not a node' % elem)

        qname = self.get_argument(context.copy())
        if qname is None:
            return []
        if not isinstance(qname, string_base_type):
            raise self.error('FORG0006', '1st argument has an invalid type %r' % type(qname))
        match = QNAME_PATTERN.match(qname)
        if match is None:
            raise self.error('FOCA0002', '1st argument must be an xs:QName')
        prefix = match.groupdict()['prefix'] or ''

        ns_uris = {get_namespace(e.tag) for e in elem.iter()}
        for p, uri in self.parser.namespaces.items():
            if uri in ns_uris:
                if not prefix or uri:
                    return '{%s}%s' % (uri, match.groupdict()['local']) if uri else match.groupdict()['local']
                else:
                    raise self.error('XPST0081', 'Prefix %r is associated to no namespace' % prefix)

        if not isinstance(context, XPathSchemaContext):
            raise self.error('FONS0004', 'No namespace found for prefix %r' % prefix)


###
# Accessor functions
@method(function('node-name', nargs=1))
def evaluate(self, context=None):
    return node_name(self.get_argument(context))


@method(function('nilled', nargs=1))
def evaluate(self, context=None):
    result = node_nilled(self.get_argument(context))
    return [] if result is None else result


@method(function('data', nargs=1))
def select(self, context=None):
    for item in self[0].select(context):
        value = self.data_value(item)
        if value is None:
            raise self.error('FOTY0012', "argument node does not have a typed value: %r" % item)
        else:
            yield value


@method(function('base-uri', nargs=(0, 1)))
def evaluate(self, context=None):
    item = self.get_argument(context)
    if item is None:
        self.missing_context("context item is undefined")
    elif not is_xpath_node(item):
        self.wrong_context_type("context item is not a node")
    else:
        return node_base_uri


@method(function('document-uri', nargs=1))
def evaluate(self, context=None):
    arg = self.get_argument(context)
    return [] if arg is None else node_document_uri(arg)


###
# Number functions
@method(function('round-half-to-even', nargs=(1, 2)))
def evaluate(self, context=None):
    item = self.get_argument(context)
    if item is None:
        return []
    elif isinstance(item, float) and (math.isnan(item) or math.isinf(item)):
        return item

    try:
        precision = 0 if len(self) < 2 else self[1].evaluate(context)
        if PY3 or precision < 0:
            value = round(decimal.Decimal(item), precision)
        else:
            number = decimal.Decimal(item)
            exp = decimal.Decimal('1' if not precision else '.%s1' % ('0' * (precision - 1)))
            value = float(number.quantize(exp, rounding='ROUND_HALF_EVEN'))
    except TypeError as err:
        self.wrong_type(str(err))
    except decimal.DecimalException as err:
        self.wrong_value(str(err))
    else:
        return float(value)


@method(function('abs', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context)
    if item is None:
        return []
    elif isinstance(item, float) and math.isnan(item):
        return item

    try:
        return abs(self.string_value(item) if is_xpath_node(item) else item)
    except TypeError as err:
        self.wrong_type(str(err))


###
# Aggregate functions
@method(function('avg', nargs=1))
def evaluate(self, context=None):
    result = [x for x in self[0].select(context)]
    if not result:
        return result
    elif isinstance(result[0], Duration):
        value = result[0]
        try:
            for item in result[1:]:
                value = value + item
            return value / len(result)
        except TypeError as err:
            self.wrong_type(str(err))
    else:
        try:
            return sum(result) / len(result)
        except TypeError as err:
            self.wrong_type(str(err))


@method(function('max', nargs=(1, 2)))
@method(function('min', nargs=(1, 2)))
def evaluate(self, context=None):
    arg = self[0].select(context)
    func = max if self.symbol == 'max' else min
    try:
        if len(self) > 1:
            with self.use_locale(collation=self.get_argument(context, 1)):
                return func(arg)
        return func(arg)
    except TypeError as err:
        self.wrong_type(str(err))
    except ValueError:
        return []


###
# General functions for sequences
@method(function('empty', nargs=1))
@method(function('exists', nargs=1))
def evaluate(self, context=None):
    return next(iter(self.select(context)))


@method('empty')
def select(self, context=None):
    try:
        next(iter(self[0].select(context)))
    except StopIteration:
        yield True
    else:
        yield False


@method('exists')
def select(self, context=None):
    try:
        next(iter(self[0].select(context)))
    except StopIteration:
        yield False
    else:
        yield True


@method(function('distinct-values', nargs=(1, 2)))
def select(self, context=None):
    nan = False
    results = []
    for item in self[0].select(context):
        value = self.data_value(item)
        if context is not None:
            context.item = value
        if not nan and isinstance(value, float) and math.isnan(value):
            yield value
            nan = True
        elif value not in results:
            yield value
            results.append(value)


@method(function('insert-before', nargs=3))
def select(self, context=None):
    insert_at_pos = max(0, self[1].value - 1)
    inserted = False
    for pos, result in enumerate(self[0].select(context)):
        if not inserted and pos == insert_at_pos:
            for item in self[2].select(context):
                yield item
            inserted = True
        yield result

    if not inserted:
        for item in self[2].select(context):
            yield item


@method(function('index-of', nargs=(1, 3)))
def select(self, context=None):
    value = self[1].evaluate(context)
    for pos, result in enumerate(self[0].select(context)):
        if result == value:
            yield pos + 1


@method(function('remove', nargs=2))
def select(self, context=None):
    target = self[1].evaluate(context) - 1
    for pos, result in enumerate(self[0].select(context)):
        if pos != target:
            yield result


@method(function('reverse', nargs=1))
def select(self, context=None):
    for result in reversed([x for x in self[0].select(context)]):
        yield result


@method(function('subsequence', nargs=(2, 3)))
def select(self, context=None):
    starting_loc = self[1].evaluate(context) - 1
    length = self[2].evaluate(context) if len(self) >= 3 else 0
    for pos, result in enumerate(self[0].select(context)):
        if starting_loc <= pos and (not length or pos < starting_loc + length):
            yield result


@method(function('unordered', nargs=1))
def select(self, context=None):
    for result in sorted([x for x in self[0].select(context)], key=lambda x: self.string_value(x)):
        yield result


###
# Cardinality functions for sequences
@method(function('zero-or-one', nargs=1))
def select(self, context=None):
    results = iter(self[0].select(context))
    try:
        item = next(results)
    except StopIteration:
        return

    try:
        next(results)
    except StopIteration:
        yield item
    else:
        raise self.error('FORG0003')


@method(function('one-or-more', nargs=1))
def select(self, context=None):
    results = iter(self[0].select(context))
    try:
        item = next(results)
    except StopIteration:
        raise self.error('FORG0004')
    else:
        yield item
        while True:
            try:
                yield next(results)
            except StopIteration:
                break


@method(function('exactly-one', nargs=1))
def select(self, context=None):
    results = iter(self[0].select(context))
    try:
        item = next(results)
    except StopIteration:
        raise self.error('FORG0005')
    else:
        try:
            next(results)
        except StopIteration:
            yield item
        else:
            raise self.error('FORG0005')


###
# Comparing sequences
@method(function('deep-equal', nargs=(2, 3)))
def evaluate(self, context=None):

    def deep_equal():
        while True:
            value1 = next(seq1, None)
            value2 = next(seq2, None)
            if (value1 is None) ^ (value2 is None):
                return False
            elif value1 is None:
                return True
            elif (is_xpath_node(value1)) ^ (is_xpath_node(value2)):
                return False
            elif not is_xpath_node(value1):
                if value1 != value2:
                    return False
            elif node_kind(value1) != node_kind(value2):
                return False
            elif not is_element_node(value1):
                if value1 != value2:
                    return False
            elif not etree_deep_equal(value1, value2):
                return False

    if context is None:
        seq1 = iter(self[0].select())
        seq2 = iter(self[1].select())
    else:
        seq1 = iter(self[0].select(context.copy()))
        seq2 = iter(self[1].select(context.copy()))

    if len(self) > 2:
        with self.use_locale(collation=self.get_argument(context, 2)):
            return deep_equal()
    else:
        return deep_equal()


###
# Regex
@method(function('matches', nargs=(2, 3)))
def evaluate(self, context=None):
    input_string = self.get_argument(context, default='', cls=string_base_type)
    pattern = self.get_argument(context, 1, required=True, cls=string_base_type)
    flags = 0
    if len(self) > 2:
        for c in self.get_argument(context, 2, required=True, cls=string_base_type):
            if c in 'smix':
                flags |= getattr(re, c.upper())
            else:
                raise self.error('FORX0001', "Invalid regular expression flag %r" % c)

    try:
        return re.search(pattern, input_string, flags=flags) is not None
    except re.error:
        raise self.error('FORX0002', "Invalid regular expression %r" % pattern)  # TODO: full XML regex syntax


@method(function('replace', nargs=(3, 4)))
def evaluate(self, context=None):
    input_string = self.get_argument(context, default='', cls=string_base_type)
    pattern = self.get_argument(context, 1, required=True, cls=string_base_type)
    replacement = self.get_argument(context, 2, required=True, cls=string_base_type)
    flags = 0
    if len(self) > 3:
        for c in self.get_argument(context, 3, required=True, cls=string_base_type):
            if c in 'smix':
                flags |= getattr(re, c.upper())
            else:
                raise self.error('FORX0001', "Invalid regular expression flag %r" % c)

    try:
        pattern = re.compile(pattern, flags=flags)
    except re.error:
        raise self.error('FORX0002', "Invalid regular expression %r" % pattern)  # TODO: full XML regex syntax
    else:
        if pattern.search(''):
            raise self.error('FORX0003', "Regular expression %r matches zero-length string" % pattern.pattern)
        elif WRONG_REPLACEMENT_PATTERN.search(replacement):
            raise self.error('FORX0004', "Invalid replacement string %r" % replacement)
        else:
            if sys.version_info >= (3, 5):
                for g in range(pattern.groups + 1):
                    if '$%d' % g in replacement:
                        replacement = re.sub(r'(?<!\\)\$%d' % g, r'\\g<%d>' % g, replacement)
            else:
                match = pattern.search(input_string)
                for g in range(pattern.groups + 1):
                    if '$%d' % g in replacement:
                        if match and match.group(g) is not None:
                            replacement = re.sub(r'(?<!\\)\$%d' % g, r'\\g<%d>' % g, replacement)
                        else:
                            replacement = re.sub(r'(?<!\\)\$%d' % g, '', replacement)

        return pattern.sub(replacement, input_string)


@method(function('tokenize', nargs=(2, 3)))
def select(self, context=None):
    input_string = self.get_argument(context, cls=string_base_type)
    pattern = self.get_argument(context, 1, required=True, cls=string_base_type)
    flags = 0
    if len(self) > 2:
        for c in self.get_argument(context, 2, required=True, cls=string_base_type):
            if c in 'smix':
                flags |= getattr(re, c.upper())
            else:
                raise self.error('FORX0001', "Invalid regular expression flag %r" % c)

    try:
        pattern = re.compile(pattern, flags=flags)
    except re.error:
        raise self.error('FORX0002', "Invalid regular expression %r" % pattern)
    else:
        if pattern.search(''):
            raise self.error('FORX0003', "Regular expression %r matches zero-length string" % pattern.pattern)

    if input_string:
        for value in pattern.split(input_string):
            if value is not None and pattern.search(value) is None:
                yield value


###
# Functions on anyURI
@method(function('resolve-uri', nargs=(1, 2)))
def evaluate(self, context=None):
    relative = self.get_argument(context, cls=string_base_type)
    if len(self) == 2:
        base_uri = self.get_argument(context, index=1, required=True, cls=string_base_type)
        base_uri = urlparse(base_uri).geturl()
    elif self.parser.base_uri is None:
        raise self.error('FONS0005')
    else:
        base_uri = self.parser.base_uri

    if relative is not None:
        url_parts = urlparse(relative)
        if url_parts.path.startswith('/'):
            return relative
        elif url_parts.scheme:
            return urljoin(base_uri, relative.split(':')[1])
        else:
            return urljoin(base_uri, relative)


###
# String functions
@method(function('codepoints-to-string', nargs=1))
def evaluate(self, context=None):
    return ''.join(unicode_chr(cp) for cp in self[0].select(context))


@method(function('string-to-codepoints', nargs=1))
def select(self, context=None):
    for char in self[0].evaluate(context):
        yield ord(char)


@method(function('compare', nargs=(2, 3)))
def evaluate(self, context=None):
    comp1 = self.get_argument(context, 0, cls=string_base_type)
    comp2 = self.get_argument(context, 1, cls=string_base_type)
    if comp1 is None or comp2 is None:
        return []

    if len(self) < 3:
        locale.setlocale(locale.LC_ALL, '')
        value = locale.strcoll(comp1, comp2)
    else:
        with self.use_locale(collation=self.get_argument(context, 2)):
            value = locale.strcoll(comp1, comp2)

    return 1 if value > 0 else -1 if value < 0 else 0


@method(function('codepoint-equal', nargs=2))
def evaluate(self, context=None):
    comp1 = self.get_argument(context, 0, cls=string_base_type)
    comp2 = self.get_argument(context, 1, cls=string_base_type)
    if comp1 is None or comp2 is None:
        return []
    elif len(comp1) != len(comp2):
        return False
    else:
        return all(ord(c1) == ord(c2) for c1, c2 in zip(comp1, comp2))


@method(function('string-join', nargs=2))
def evaluate(self, context=None):
    items = [self.string_value(s) if is_element_node(s) or is_attribute_node(s) else s
             for s in self[0].select(context)]
    try:
        return self.get_argument(context, 1, cls=string_base_type).join(items)
    except AttributeError as err:
        self.wrong_type("the separator must be a string: %s" % err)
    except TypeError as err:
        self.wrong_type("the values must be strings: %s" % err)


@method(function('normalize-unicode', nargs=(1, 2)))
def evaluate(self, context=None):
    arg = self.get_argument(context, default='', cls=string_base_type)
    if len(self) > 1:
        normalization_form = self.get_argument(context, 1, cls=string_base_type)
        if normalization_form is None:
            self.wrong_type("2nd argument can't be an empty sequence")
        else:
            normalization_form = normalization_form.strip().upper()
    else:
        normalization_form = 'NFC'

    if normalization_form == 'FULLY-NORMALIZED':
        raise NotImplementedError("%r normalization form not supported" % normalization_form)
    if arg is None:
        return ''
    elif not isinstance(arg, unicode_type):
        arg = arg.decode('utf-8')

    try:
        return unicodedata.normalize(normalization_form, arg)
    except ValueError:
        raise self.error('FOCH0003', "unsupported normalization form %r" % normalization_form)


@method(function('upper-case', nargs=1))
def evaluate(self, context=None):
    arg = self.get_argument(context, cls=string_base_type)
    try:
        return '' if arg is None else arg.upper()
    except AttributeError:
        self.wrong_type("the argument must be a string: %r" % arg)


@method(function('lower-case', nargs=1))
def evaluate(self, context=None):
    arg = self.get_argument(context, cls=string_base_type)
    try:
        return '' if arg is None else arg.lower()
    except AttributeError:
        self.wrong_type("the argument must be a string: %r" % arg)


@method(function('encode-for-uri', nargs=1))
def evaluate(self, context=None):
    uri_part = self.get_argument(context, cls=string_base_type)
    try:
        return '' if uri_part is None else urllib_quote(uri_part, safe='~')
    except TypeError:
        self.wrong_type("the argument must be a string: %r" % uri_part)


@method(function('iri-to-uri', nargs=1))
def evaluate(self, context=None):
    iri = self.get_argument(context, cls=string_base_type)
    try:
        return '' if iri is None else urllib_quote(iri, safe='-_.!~*\'()#;/?:@&=+$,[]%')
    except TypeError:
        self.wrong_type("the argument must be a string: %r" % iri)


@method(function('escape-html-uri', nargs=1))
def evaluate(self, context=None):
    uri = self.get_argument(context, cls=string_base_type)
    try:
        return '' if uri is None else urllib_quote(uri, safe=''.join(chr(cp) for cp in range(32, 127)))
    except TypeError:
        self.wrong_type("the argument must be a string: %r" % uri)


@method(function('starts-with', nargs=(2, 3)))
def evaluate(self, context=None):
    arg1 = self.get_argument(context, default='', cls=string_base_type)
    arg2 = self.get_argument(context, index=1, default='', cls=string_base_type)
    return arg1.startswith(arg2)


@method(function('ends-with', nargs=(2, 3)))
def evaluate(self, context=None):
    arg1 = self.get_argument(context, default='', cls=string_base_type)
    arg2 = self.get_argument(context, index=1, default='', cls=string_base_type)
    return arg1.endswith(arg2)


###
# Functions on durations, dates and times
@method(function('years-from-duration', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context, cls=Duration)
    if item is None:
        return []
    else:
        return item.months // 12 if item.months >= 0 else -(abs(item.months) // 12)


@method(function('months-from-duration', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context, cls=Duration)
    if item is None:
        return []
    else:
        return item.months % 12 if item.months >= 0 else -(abs(item.months) % 12)


@method(function('days-from-duration', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context, cls=Duration)
    if item is None:
        return []
    else:
        return item.seconds // 86400 if item.seconds >= 0 else -(abs(item.seconds) // 86400)


@method(function('hours-from-duration', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context, cls=Duration)
    if item is None:
        return []
    else:
        return item.seconds // 3600 % 24 if item.seconds >= 0 else -(abs(item.seconds) // 3600 % 24)


@method(function('minutes-from-duration', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context, cls=Duration)
    if item is None:
        return []
    else:
        return item.seconds // 60 % 60 if item.seconds >= 0 else -(abs(item.seconds) // 60 % 60)


@method(function('seconds-from-duration', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context, cls=Duration)
    if item is None:
        return []
    else:
        return item.seconds % 60 if item.seconds >= 0 else -(abs(item.seconds) % 60)


@method(function('year-from-dateTime', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context, cls=DateTime10)
    return [] if item is None else -(item.year + 1) if item.bce else item.year


@method(function('month-from-dateTime', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context, cls=DateTime10)
    return [] if item is None else item.month


@method(function('day-from-dateTime', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context, cls=DateTime10)
    return [] if item is None else item.day


@method(function('hours-from-dateTime', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context, cls=DateTime10)
    return [] if item is None else item.hour


@method(function('minutes-from-dateTime', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context, cls=DateTime10)
    return [] if item is None else item.minute


@method(function('seconds-from-dateTime', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context, cls=DateTime10)
    return [] if item is None else item.second


@method(function('timezone-from-dateTime', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context, cls=DateTime10)
    return [] if item is None else DayTimeDuration(seconds=item.tzinfo.offset.total_seconds())


@method(function('year-from-date', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context, cls=Date10)
    return [] if item is None else item.year


@method(function('month-from-date', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context, cls=Date10)
    return [] if item is None else item.month


@method(function('day-from-date', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context, cls=Date10)
    return [] if item is None else item.day


@method(function('timezone-from-date', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context, cls=Date10)
    return [] if item is None else DayTimeDuration(seconds=item.tzinfo.offset.total_seconds())


@method(function('hours-from-time', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context, cls=Time)
    return [] if item is None else item.hour


@method(function('minutes-from-time', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context, cls=Time)
    return [] if item is None else item.minute


@method(function('seconds-from-time', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context, cls=Time)
    return [] if item is None else item.second + item.microsecond / 1000000.0


@method(function('timezone-from-time', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context, cls=Time)
    return [] if item is None else DayTimeDuration(seconds=item.tzinfo.offset.total_seconds())


###
# Timezone adjustment functions
@method(function('adjust-dateTime-to-timezone', nargs=(1, 2)))
def evaluate(self, context=None):
    return self.adjust_datetime(context, DateTime10)


@method(function('adjust-date-to-timezone', nargs=(1, 2)))
def evaluate(self, context=None):
    return self.adjust_datetime(context, Date10)


@method(function('adjust-time-to-timezone', nargs=(1, 2)))
def evaluate(self, context=None):
    return self.adjust_datetime(context, Time)


###
# Static context functions
@method(function('default-collation', nargs=0))
def evaluate(self, context=None):
    return self.parser.default_collation


@method(function('static-base-uri', nargs=0))
def evaluate(self, context=None):
    if self.parser.base_uri is not None:
        return self.parser.base_uri


###
# Dynamic context functions
@method(function('current-dateTime', nargs=0))
def evaluate(self, context=None):
    dt = datetime.datetime.now() if context is None else context.current_dt
    return DateTime10(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond, dt.tzinfo)


@method(function('current-date', nargs=0))
def evaluate(self, context=None):
    dt = datetime.datetime.now() if context is None else context.current_dt
    return Date10(dt.year, dt.month, dt.day, tzinfo=dt.tzinfo)


@method(function('current-time', nargs=0))
def evaluate(self, context=None):
    dt = datetime.datetime.now() if context is None else context.current_dt
    return Time(dt.hour, dt.minute, dt.second, dt.microsecond, dt.tzinfo)


@method(function('implicit-timezone', nargs=0))
def evaluate(self, context=None):
    if context is not None and context.timezone is not None:
        return context.timezone
    else:
        return Timezone(datetime.timedelta(seconds=time.timezone))


###
# The root function (Ref: https://www.w3.org/TR/2010/REC-xpath-functions-20101214/#func-root)
@method(function('root', nargs=(0, 1)))
def evaluate(self, context=None):
    if context is None:
        raise self.error('XPDY0002')
    elif isinstance(context, XPathSchemaContext):
        return
    elif not self:
        if context.item is None or is_xpath_node(context.item):
            return context.root
        else:
            raise self.error('XPTY0004')
    else:
        item = self.get_argument(context)
        if not is_xpath_node(item):
            raise self.error('XPTY0004')
        elif any(item is x for x in context.iter()):
            return context.root

        for uri, doc in context.documents.items():
            doc_context = XPathContext(root=doc)
            if any(item is x for x in doc_context.iter()):
                return doc


###
# Functions that generate sequences
XPath2Parser.duplicate('id', 'element-with-id')  # To preserve backwards compatibility
XPath2Parser.unregister('id')


@method(function('id', nargs=(1, 2)))
def select(self, context=None):
    # TODO: PSVI bindings with also xsi:type evaluation
    idrefs = list(self[0].select(None if context is None else context.copy()))
    node = self.get_argument(context, index=1, default_to_context=True)
    if context is None or node is not context.item:
        if not is_document_node(node):
            raise self.error('FODC0001', 'cannot retrieve document root')
        root = node
    else:
        if not is_document_node(context.root):
            raise self.error('FODC0001')
        elif not is_xpath_node(node):
            raise self.error('XPTY0004')
        root = context.root

    for elem in root.iter():
        if node_is_id(elem) and any(v == elem.text for x in idrefs for v in x.split()):
            yield elem
            continue
        for attr in map(lambda x: AttributeNode(*x), elem.attrib.items()):
            if any(v == attr.value for x in idrefs for v in x.split()):
                yield elem
                break


@method(function('idref', nargs=(1, 2)))
def select(self, context=None):
    # TODO: PSVI bindings with also xsi:type evaluation
    ids = list(self[0].select(None if context is None else context.copy()))
    node = self.get_argument(context, index=1, default_to_context=True)
    if context is None or node is not context.item:
        if not is_document_node(node):
            raise self.error('FODC0001', 'cannot retrieve document root')
        root = node
    else:
        if not is_document_node(context.root):
            raise self.error('FODC0001')
        elif not is_xpath_node(node):
            raise self.error('XPTY0004')
        root = context.root

    for elem in root.iter():
        if node_is_idrefs(elem) and any(v in elem.text.split() for x in ids for v in x.split()):
            yield elem
            continue
        for attr in map(lambda x: AttributeNode(*x), elem.attrib.items()):
            if attr.name != XML_ID and any(v in attr.value.split() for x in ids for v in x.split()):
                yield elem
                break


@method(function('doc', nargs=1))
@method(function('doc-available', nargs=1))
def evaluate(self, context=None):
    uri = self.get_argument(context)
    if uri is None:
        return None if self.symbol == 'doc' else False

    try:
        uri = self.get_absolute_uri(uri)
    except URLError:
        raise self.error('FODC0005')

    if context is not None and not isinstance(context, XPathSchemaContext):
        try:
            doc = context.documents[uri]
        except KeyError:
            if self.symbol == 'doc':
                raise self.error('FODC0005')
            return False
        else:
            if not is_document_node(doc):
                raise self.error('FODC0005')
            return doc if self.symbol == 'doc' else True


@method(function('collection', nargs=(0, 1)))
def evaluate(self, context=None):
    uri = self.get_argument(context)
    if context is None or isinstance(context, XPathSchemaContext):
        return
    elif not self or uri is None:
        if context.default_collection is None:
            raise self.error('FODC0002', 'no default collection has been defined')
        return context.default_collection

    try:
        uri = self.get_absolute_uri(uri)
    except URLError:
        raise self.error('FODC0004')

    try:
        return self.parser.collections[uri]
    except KeyError:
        raise self.error('FODC0004', '{!r} collection not found'.format(uri))


###
# The error function (Ref: https://www.w3.org/TR/xpath20/#func-error)
@method(function('error', nargs=(0, 3)))
def evaluate(self, context=None):
    if not self:
        raise self.error('FOER0000')
    elif len(self) == 1:
        item = self.get_argument(context)
        raise self.error(item or 'FOER0000')


# XPath 2.0 definitions continue into module xpath2_constructors
