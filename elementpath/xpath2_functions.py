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
XPath 2.0 implementation - part 2 (functions)
"""
import decimal
import math
import datetime
import time
import re
import locale
import unicodedata
from copy import copy
from urllib.parse import quote as urllib_quote

from .exceptions import ElementPathTypeError
from .datatypes import QNAME_PATTERN, DateTime10, Date10, Date, StringProxy, \
    Time, Duration, DayTimeDuration, UntypedAtomic, AnyURI, QName, Id, is_idrefs
from .namespaces import XML_NAMESPACE, get_namespace, split_expanded_name, XML_ID
from .xpath_context import XPathContext, XPathSchemaContext
from .xpath_nodes import AttributeNode, is_element_node, is_document_node, \
    is_xpath_node, node_name, node_nilled, node_base_uri, node_document_uri, \
    node_kind, etree_deep_equal
from .xpath2_parser import XPath2Parser

method = XPath2Parser.method
function = XPath2Parser.function

WRONG_REPLACEMENT_PATTERN = re.compile(r'(?<!\\)\$([^\d]|$)|((?<=[^\\])|^)\\([^$]|$)|\\\\\$')


###
# Sequence types (allowed only for type checking in treat-as/instance-of statements)
function('empty-sequence', nargs=0, label='sequence type')


@method(function('item', nargs=0, label='sequence type'))
def evaluate(self, context=None):
    if context is None:
        raise self.missing_context()
    elif context.item is None:
        return context.root
    else:
        return context.item


###
# Function for QNames
@method(function('prefix-from-QName', nargs=1))
def evaluate(self, context=None):
    qname = self.get_argument(context)
    if qname is None:
        return []
    elif not isinstance(qname, QName):
        raise self.error('XPTY0004', 'argument has an invalid type %r' % type(qname))
    return qname.prefix or []


@method(function('local-name-from-QName', nargs=1))
def evaluate(self, context=None):
    qname = self.get_argument(context)
    if qname is None:
        return []
    elif not isinstance(qname, QName):
        raise self.error('XPTY0004', 'argument has an invalid type %r' % type(qname))
    return qname.local_name


@method(function('namespace-uri-from-QName', nargs=1))
def evaluate(self, context=None):
    qname = self.get_argument(context)
    if qname is None:
        return []
    elif not isinstance(qname, QName):
        raise self.error('XPTY0004', 'argument has an invalid type %r' % type(qname))
    return qname.namespace or ''


@method(function('namespace-uri-for-prefix', nargs=2))
def evaluate(self, context=None):
    if context is None:
        raise self.missing_context()

    prefix = self.get_argument(context=copy(context))
    if prefix is None:
        prefix = ''
    if not isinstance(prefix, str):
        raise self.error('FORG0006', '1st argument has an invalid type %r' % type(prefix))

    elem = self.get_argument(context, index=1)
    if not is_element_node(elem):
        raise self.error('FORG0006', '2nd argument %r is not an element node' % elem)
    ns_uris = {get_namespace(e.tag) for e in elem.iter()}
    for p, uri in self.parser.namespaces.items():
        if uri in ns_uris:
            if p == prefix:
                if not prefix or uri:
                    return uri
                else:
                    msg = 'Prefix %r is associated to no namespace'
                    raise self.error('XPST0081', msg % prefix)
    return []


@method(function('in-scope-prefixes', nargs=1))
def select(self, context=None):
    if context is None:
        raise self.missing_context()

    elem = self.get_argument(context)
    if not is_element_node(elem):
        raise self.error('FORG0006', 'argument %r is not an element node' % elem)

    if isinstance(context, XPathSchemaContext):
        # For schema context returns prefixes of static namespaces
        yield from self.parser.namespaces
    elif hasattr(elem, 'nsmap'):
        # For lxml returns Element's prefixes
        for prefix in elem.nsmap:
            yield prefix or ''
    else:
        yield from self.parser.namespaces
        # For ElementTree returns module registered prefixes
        prefixes = {x for x in self.parser.namespaces}
        if context.namespaces:
            prefixes.update(x for x in context.namespaces)
        yield from prefixes


@method(function('resolve-QName', nargs=2))
def evaluate(self, context=None):
    qname = self.get_argument(context=copy(context))
    if qname is None:
        return []
    elif not isinstance(qname, str):
        raise self.error('FORG0006', '1st argument has an invalid type %r' % type(qname))

    if context is None:
        raise self.missing_context()

    elem = self.get_argument(context, index=1)
    if not is_element_node(elem):
        raise self.error('FORG0006', '2nd argument %r is not an element node' % elem)

    qname = qname.strip()
    match = QNAME_PATTERN.match(qname)
    if match is None:
        raise self.error('FOCA0002', '1st argument must be an xs:QName')

    prefix = match.groupdict()['prefix'] or ''
    if prefix == 'xml':
        return QName(XML_NAMESPACE, qname)

    try:
        nsmap = {**self.parser.namespaces, **elem.nsmap}
    except AttributeError:
        nsmap = self.parser.namespaces

    for pfx, uri in nsmap.items():
        if pfx == prefix:
            if pfx:
                return QName(uri, '{}:{}'.format(pfx, match.groupdict()['local']))
            else:
                return QName(uri, match.groupdict()['local'])

    if prefix or '' in self.parser.namespaces:
        raise self.error('FONS0004', 'no namespace found for prefix %r' % prefix)
    return QName('', qname)


###
# Accessor functions
@method(function('node-name', nargs=1))
def evaluate(self, context=None):
    name = node_name(self.get_argument(context))
    if name is None:
        return []

    if name.startswith('{'):
        namespace, local_name = split_expanded_name(name)
        for pfx, uri in self.parser.namespaces.items():
            if uri == namespace:
                if pfx:
                    return QName(uri, '{}:{}'.format(pfx, local_name))
                else:
                    return QName(uri, local_name)
        raise self.error('FONS0004', 'no prefix found for namespace {}'.format(namespace))

    try:
        if ':' not in name:
            return QName(self.parser.namespaces.get('', ''), name)
        pfx, _ = name.strip().split(':')
        return QName(self.parser.namespaces[pfx], name)
    except ValueError:
        raise self.error('FORG0001', 'invalid value {!r} for argument'.format(name.strip()))
    except KeyError as err:
        raise self.error('FONS0004', 'no namespace found for prefix {}'.format(err))


@method(function('nilled', nargs=1))
def evaluate(self, context=None):
    result = node_nilled(self.get_argument(context))
    return [] if result is None else result


@method(function('data', nargs=1))
def select(self, context=None):
    for item in self[0].select(context):
        value = self.data_value(item)
        if value is None:
            raise self.error('FOTY0012', "argument node does not have a typed value")
        else:
            yield value


@method(function('base-uri', nargs=(0, 1)))
def evaluate(self, context=None):
    item = self.get_argument(context, default_to_context=True)
    if item is None:
        raise self.missing_context("context item is undefined")
    elif not is_xpath_node(item):
        raise self.wrong_context_type("context item is not a node")
    else:
        return node_base_uri(item)


@method(function('document-uri', nargs=1))
def evaluate(self, context=None):
    if context is None:
        raise self.missing_context()

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
    elif not isinstance(item, (float, int, decimal.Decimal)):
        raise self.wrong_type("Invalid argument type {!r}".format(type(item)))

    precision = 0 if len(self) < 2 else self[1].evaluate(context)
    try:
        round(decimal.Decimal(item), precision)
        return float(round(decimal.Decimal(item), precision))
    except TypeError as err:
        raise self.error('XPTY0004', str(err))
    except decimal.DecimalException as err:
        raise self.error('FOCA0001', str(err))


@method(function('abs', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context)
    if item is None:
        return []
    elif isinstance(item, float) and math.isnan(item):
        return item
    elif is_xpath_node(item):
        value = self.string_value(item)
        try:
            return abs(decimal.Decimal(value))
        except decimal.DecimalException:
            raise self.wrong_value("Invalid string value {!r} for {!r}".format(value, item))
    elif not isinstance(item, (float, int, decimal.Decimal)):
        raise self.wrong_type("Invalid argument type {!r}".format(type(item)))
    else:
        return abs(item)


###
# Aggregate functions
@method(function('avg', nargs=1))
def evaluate(self, context=None):
    values = []
    for item in self[0].select_data_values(context):
        if isinstance(item, (UntypedAtomic, decimal.Decimal)):
            values.append(self.cast_to_number(item, float))
        elif isinstance(item, AnyURI):
            values.append(item.value)
        else:
            values.append(item)

    if not values:
        return values
    elif isinstance(values[0], Duration):
        value = values[0]
        try:
            for item in values[1:]:
                value = value + item
            return value / len(values)
        except TypeError as err:
            raise self.wrong_type(str(err))
    else:
        try:
            return sum(values) / len(values)
        except TypeError as err:
            raise self.wrong_type(str(err))


@method(function('max', nargs=(1, 2)))
@method(function('min', nargs=(1, 2)))
def evaluate(self, context=None):
    values = []
    for item in self[0].select_data_values(context):
        if isinstance(item, (UntypedAtomic, decimal.Decimal)):
            values.append(self.cast_to_number(item, float))
        elif isinstance(item, AnyURI):
            values.append(item.value)
        else:
            values.append(item)

    if any(isinstance(x, float) and math.isnan(x) for x in values):
        return float('nan')

    try:
        if len(self) > 1:
            with self.use_locale(collation=self.get_argument(context, 1)):
                return max(values) if self.symbol == 'max' else min(values)
        return max(values) if self.symbol == 'max' else min(values)
    except TypeError as err:
        raise self.wrong_type(str(err))
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
    try:
        insert_at_pos = max(0, self[1].value - 1)
    except TypeError:
        raise self.error('XPTY0004', '2nd argument must be an xs:integer') from None

    inserted = False
    for pos, result in enumerate(self[0].select(context)):
        if not inserted and pos == insert_at_pos:
            yield from self[2].select(context)
            inserted = True
        yield result

    if not inserted:
        yield from self[2].select(context)


@method(function('index-of', nargs=(2, 3)))
def select(self, context=None):
    value = self[1].evaluate(context)
    for pos, result in enumerate(self[0].select(context), start=1):
        if result == value:
            yield pos


@method(function('remove', nargs=2))
def select(self, context=None):
    position = self[1].evaluate(context)
    if not isinstance(position, int):
        raise self.error('XPTY0004', 'an xs:integer required')

    for pos, result in enumerate(self[0].select(context), start=1):
        if pos != position:
            yield result


@method(function('reverse', nargs=1))
def select(self, context=None):
    yield from reversed([x for x in self[0].select(context)])


@method(function('subsequence', nargs=(2, 3)))
def select(self, context=None):
    starting_loc = self[1].evaluate(context) - 1
    length = self[2].evaluate(context) if len(self) >= 3 else 0
    for pos, result in enumerate(self[0].select(context)):
        try:
            if starting_loc <= pos and (not length or pos < starting_loc + length):
                yield result
        except TypeError as err:
            raise self.error('XPTY0004', str(err)) from None


@method(function('unordered', nargs=1))
def select(self, context=None):
    yield from sorted([x for x in self[0].select(context)], key=lambda x: self.string_value(x))


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
        raise self.error('FORG0004') from None
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
        raise self.error('FORG0005') from None
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

    seq1 = iter(self[0].select(copy(context)))
    seq2 = iter(self[1].select(copy(context)))

    if len(self) > 2:
        with self.use_locale(collation=self.get_argument(context, 2)):
            return deep_equal()
    else:
        return deep_equal()


###
# Regex
@method(function('matches', nargs=(2, 3)))
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
        return re.search(pattern, input_string, flags=flags) is not None
    except re.error:
        # TODO: full XML regex syntax
        raise self.error('FORX0002', "Invalid regular expression %r" % pattern) from None
    except OverflowError as err:
        raise self.error('FOAR0002', str(err)) from None


@method(function('replace', nargs=(3, 4)))
def evaluate(self, context=None):
    input_string = self.get_argument(context, default='', cls=str)
    pattern = self.get_argument(context, 1, required=True, cls=str)
    replacement = self.get_argument(context, 2, required=True, cls=str)
    flags = 0
    if len(self) > 3:
        for c in self.get_argument(context, 3, required=True, cls=str):
            if c in 'smix':
                flags |= getattr(re, c.upper())
            else:
                raise self.error('FORX0001', "Invalid regular expression flag %r" % c)

    try:
        pattern = re.compile(pattern, flags=flags)
    except re.error:
        # TODO: full XML regex syntax
        raise self.error('FORX0002', "Invalid regular expression %r" % pattern)
    else:
        if pattern.search(''):
            msg = "Regular expression %r matches zero-length string"
            raise self.error('FORX0003', msg % pattern.pattern)
        elif WRONG_REPLACEMENT_PATTERN.search(replacement):
            raise self.error('FORX0004', "Invalid replacement string %r" % replacement)
        else:
            for g in range(pattern.groups + 1):
                if '$%d' % g in replacement:
                    replacement = re.sub(r'(?<!\\)\$%d' % g, r'\\g<%d>' % g, replacement)

        return pattern.sub(replacement, input_string)


@method(function('tokenize', nargs=(2, 3)))
def select(self, context=None):
    input_string = self.get_argument(context, cls=str)
    pattern = self.get_argument(context, 1, required=True, cls=str)
    flags = 0
    if len(self) > 2:
        for c in self.get_argument(context, 2, required=True, cls=str):
            if c in 'smix':
                flags |= getattr(re, c.upper())
            else:
                raise self.error('FORX0001', "Invalid regular expression flag %r" % c)

    try:
        pattern = re.compile(pattern, flags=flags)
    except re.error:
        raise self.error('FORX0002', "Invalid regular expression %r" % pattern) from None
    else:
        if pattern.search(''):
            msg = "Regular expression %r matches zero-length string"
            raise self.error('FORX0003', msg % pattern.pattern)

    if input_string:
        for value in pattern.split(input_string):
            if value is not None and pattern.search(value) is None:
                yield value


###
# Functions on anyURI
@method(function('resolve-uri', nargs=(1, 2)))
def evaluate(self, context=None):
    relative = self.get_argument(context, cls=str)
    if len(self) == 1:
        if self.parser.base_uri is None:
            raise self.error('FONS0005')
        elif relative is None:
            return
        elif not AnyURI.is_valid(relative):
            raise self.error('FORG0002', '{!r} is not a valid URI'.format(relative))
        else:
            return self.get_absolute_uri(relative)

    base_uri = self.get_argument(context, index=1, required=True, cls=str)
    if not AnyURI.is_valid(base_uri):
        raise self.error('FORG0002', '{!r} is not a valid URI'.format(base_uri))
    elif relative is None:
        return
    elif not AnyURI.is_valid(relative):
        raise self.error('FORG0002', '{!r} is not a valid URI'.format(relative))
    else:
        return self.get_absolute_uri(relative, base_uri)


###
# String functions
def xml10_chr(cp):
    if cp in {0x9, 0xA, 0xD} \
            or 0x20 <= cp <= 0xD7FF \
            or 0xE000 <= cp <= 0xFFFD \
            or 0x10000 <= cp <= 0x10FFFF:
        return chr(cp)
    raise ValueError("{} is not a valid XML 1.0 codepoint".format(cp))


@method(function('codepoints-to-string', nargs=1))
def evaluate(self, context=None):
    try:
        return ''.join(xml10_chr(cp) for cp in self[0].select(context))
    except TypeError as err:
        raise self.wrong_type(str(err)) from None
    except ValueError as err:
        raise self.error('FOCH0001', str(err)) from None  # Code point not valid


@method(function('string-to-codepoints', nargs=1))
def select(self, context=None):
    try:
        yield from (ord(c) for c in self[0].evaluate(context))
    except TypeError:
        raise self.error('XPTY0004', 'an xs:string required') from None


@method(function('compare', nargs=(2, 3)))
def evaluate(self, context=None):
    comp1 = self.get_argument(context, 0, cls=StringProxy)
    comp2 = self.get_argument(context, 1, cls=StringProxy)
    if not isinstance(comp1, str):
        if comp1 is None:
            return []
        comp1 = str(comp1)
    if not isinstance(comp2, str):
        if comp2 is None:
            return []
        comp2 = str(comp2)

    if len(self) < 3:
        value = locale.strcoll(comp1, comp2)
    else:
        with self.use_locale(collation=self.get_argument(context, 2)):
            value = locale.strcoll(comp1, comp2)

    return 0 if not value else 1 if value > 0 else -1


@method(function('contains', nargs=(2, 3)))
def evaluate(self, context=None):
    arg1 = self.get_argument(context, default='', cls=str)
    arg2 = self.get_argument(context, index=1, default='', cls=str)

    if len(self) < 3:
        return arg2 in arg1
    else:
        with self.use_locale(collation=self.get_argument(context, 2)):
            return arg2 in arg1


@method(function('codepoint-equal', nargs=2))
def evaluate(self, context=None):
    comp1 = self.get_argument(context, 0, cls=str)
    comp2 = self.get_argument(context, 1, cls=str)
    if comp1 is None or comp2 is None:
        return []
    elif len(comp1) != len(comp2):
        return False
    else:
        return all(ord(c1) == ord(c2) for c1, c2 in zip(comp1, comp2))


@method(function('string-join', nargs=(1, 2)))
def evaluate(self, context=None):
    items = [self.string_value(s) for s in self[0].select(context)]
    try:
        return self.get_argument(context, 1, default='', cls=str).join(items)
    except ElementPathTypeError:
        raise
    except TypeError as err:
        raise self.wrong_type("the values must be strings: %s" % err) from None


@method(function('normalize-unicode', nargs=(1, 2)))
def evaluate(self, context=None):
    arg = self.get_argument(context, default='', cls=str)
    if len(self) > 1:
        normalization_form = self.get_argument(context, 1, cls=str)
        if normalization_form is None:
            raise self.wrong_type("2nd argument can't be an empty sequence")
        else:
            normalization_form = normalization_form.strip().upper()
    else:
        normalization_form = 'NFC'

    if normalization_form == 'FULLY-NORMALIZED':
        msg = "%r normalization form not supported" % normalization_form
        raise self.error('FOCH0003', msg)
    if not arg:
        return ''
    elif not normalization_form:
        return arg

    try:
        return unicodedata.normalize(normalization_form, arg)
    except ValueError:
        msg = "unsupported normalization form %r" % normalization_form
        raise self.error('FOCH0003', msg) from None


@method(function('upper-case', nargs=1))
def evaluate(self, context=None):
    return self.get_argument(context, default='', cls=str).upper()


@method(function('lower-case', nargs=1))
def evaluate(self, context=None):
    return self.get_argument(context, default='', cls=str).lower()


@method(function('encode-for-uri', nargs=1))
def evaluate(self, context=None):
    uri_part = self.get_argument(context, cls=str)
    return '' if uri_part is None else urllib_quote(uri_part, safe='~')


@method(function('iri-to-uri', nargs=1))
def evaluate(self, context=None):
    iri = self.get_argument(context, cls=str)
    return '' if iri is None else urllib_quote(iri, safe='-_.!~*\'()#;/?:@&=+$,[]%')


@method(function('escape-html-uri', nargs=1))
def evaluate(self, context=None):
    uri = self.get_argument(context, cls=str)
    if uri is None:
        return ''
    return urllib_quote(uri, safe=''.join(chr(cp) for cp in range(32, 127)))


@method(function('starts-with', nargs=(2, 3)))
def evaluate(self, context=None):
    arg1 = self.get_argument(context, default='', cls=str)
    arg2 = self.get_argument(context, index=1, default='', cls=str)
    return arg1.startswith(arg2)


@method(function('ends-with', nargs=(2, 3)))
def evaluate(self, context=None):
    arg1 = self.get_argument(context, default='', cls=str)
    arg2 = self.get_argument(context, index=1, default='', cls=str)
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
    if item is None:
        return []
    elif item.microsecond:
        return decimal.Decimal('{}.{}'.format(item.second, item.microsecond))
    else:
        return item.second


@method(function('timezone-from-dateTime', nargs=1))
def evaluate(self, context=None):
    item = self.get_argument(context, cls=DateTime10)
    if item is None or item.tzinfo is None:
        return []
    return DayTimeDuration(seconds=item.tzinfo.offset.total_seconds())


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
    if item is None or item.tzinfo is None:
        return []
    return DayTimeDuration(seconds=item.tzinfo.offset.total_seconds())


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
    if item is None or item.tzinfo is None:
        return []
    return DayTimeDuration(seconds=item.tzinfo.offset.total_seconds())


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
    return DateTime10(dt.year, dt.month, dt.day, dt.hour, dt.minute,
                      dt.second, dt.microsecond, dt.tzinfo)


@method(function('current-date', nargs=0))
def evaluate(self, context=None):
    dt = datetime.datetime.now() if context is None else context.current_dt
    try:
        if self.parser.schema.xsd_version == '1.1':
            return Date(dt.year, dt.month, dt.day, tzinfo=dt.tzinfo)
    except (AttributeError, NotImplementedError):
        pass

    return Date10(dt.year, dt.month, dt.day, tzinfo=dt.tzinfo)


@method(function('current-time', nargs=0))
def evaluate(self, context=None):
    dt = datetime.datetime.now() if context is None else context.current_dt
    return Time(dt.hour, dt.minute, dt.second, dt.microsecond, dt.tzinfo)


@method(function('implicit-timezone', nargs=0))
def evaluate(self, context=None):
    if context is not None and context.timezone is not None:
        return DayTimeDuration.fromtimedelta(context.timezone.offset)
    else:
        return DayTimeDuration.fromtimedelta(datetime.timedelta(seconds=time.timezone))


###
# The root function (Ref: https://www.w3.org/TR/2010/REC-xpath-functions-20101214/#func-root)
@method(function('root', nargs=(0, 1)))
def evaluate(self, context=None):
    if context is None:
        raise self.missing_context()
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

        try:
            for uri, doc in context.documents.items():
                doc_context = XPathContext(root=doc)
                if any(item is x for x in doc_context.iter()):
                    return doc
        except AttributeError:
            pass


###
# Functions that generate sequences
XPath2Parser.duplicate('id', 'element-with-id')  # To preserve backwards compatibility
XPath2Parser.unregister('id')


@method(function('id', nargs=(1, 2)))
def select(self, context=None):
    # TODO: PSVI bindings with also xsi:type evaluation
    idrefs = [x for x in self[0].select(context=copy(context))]
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
        if Id.is_valid(elem.text) and any(v == elem.text for x in idrefs for v in x.split()):
            yield elem
            continue
        for attr in map(lambda x: AttributeNode(*x), elem.attrib.items()):
            if any(v == attr.value for x in idrefs for v in x.split()):
                yield elem
                break


@method(function('idref', nargs=(1, 2)))
def select(self, context=None):
    # TODO: PSVI bindings with also xsi:type evaluation
    ids = [x for x in self[0].select(context=copy(context))]
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
        if is_idrefs(elem.text) and any(v in elem.text.split() for x in ids for v in x.split()):
            yield elem
            continue
        for attr in map(lambda x: AttributeNode(*x), elem.attrib.items()):  # pragma: no cover
            if attr.name != XML_ID and any(v in attr.value.split() for x in ids for v in x.split()):
                yield elem
                break


@method(function('doc', nargs=1))
@method(function('doc-available', nargs=1))
def evaluate(self, context=None):
    uri = self.get_argument(context)
    if uri is None:
        return None if self.symbol == 'doc' else False
    elif context is None:
        raise self.missing_context()
    elif not isinstance(uri, str):
        raise self.error('FODC0005')

    uri = self.get_absolute_uri(uri)
    if not isinstance(context, XPathSchemaContext):
        try:
            doc = context.documents[uri]
        except (KeyError, TypeError):
            if self.symbol == 'doc':
                raise self.error('FODC0005')
            return False

        try:
            sequence_type = self.parser.document_types[uri]
        except (KeyError, TypeError):
            sequence_type = 'document-node()'

        if not self.parser.match_sequence_type(doc, sequence_type):
            msg = "Type does not match sequence type {!r}"
            raise self.wrong_sequence_type(msg.format(sequence_type))

        return doc if self.symbol == 'doc' else True


@method(function('collection', nargs=(0, 1)))
def evaluate(self, context=None):
    uri = self.get_argument(context)
    if context is None:
        raise self.missing_context()
    elif isinstance(context, XPathSchemaContext):
        return
    elif not self or uri is None:
        if context.default_collection is None:
            raise self.error('FODC0002', 'no default collection has been defined')

        collection = context.default_collection
        sequence_type = self.parser.default_collection_type
    else:
        uri = self.get_absolute_uri(uri)
        try:
            collection = context.collections[uri]
        except (KeyError, TypeError):
            raise self.error('FODC0004', '{!r} collection not found'.format(uri)) from None

        try:
            sequence_type = self.parser.collection_types[uri]
        except (KeyError, TypeError):
            return collection

    if not self.parser.match_sequence_type(collection, sequence_type):
        msg = "Type does not match sequence type {!r}"
        raise self.wrong_sequence_type(msg.format(sequence_type))

    return collection


###
# The error function
#
# https://www.w3.org/TR/2010/REC-xpath-functions-20101214/#func-error
# https://www.w3.org/TR/xpath-functions/#func-error
#
@method(function('error', nargs=(0, 3)))
def evaluate(self, context=None):
    if not self:
        raise self.error('FOER0000')
    elif len(self) == 1:
        error = self.get_argument(context, cls=str)
        raise self.error(error or 'FOER0000')
    else:
        error = self.get_argument(context, cls=str)
        description = self.get_argument(context, index=1, cls=str)
        raise self.error(error or 'FOER0000', message=description)


###
# The trace function
#
# https://www.w3.org/TR/2010/REC-xpath-functions-20101214/#func-trace
#
@method(function('trace', nargs=2))
def select(self, context=None):
    label = self.get_argument(context, index=1, cls=str)
    for value in self[0].select(context):
        '{} {}'.format(label, str(value).strip())  # TODO
        yield value


# XPath 2.0 definitions continue into module xpath2_constructors
