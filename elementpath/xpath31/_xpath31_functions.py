#
# Copyright (c), 2018-2021, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
# type: ignore
"""
XPath 3.1 implementation - part 3 (functions)
"""
import json
import random
import re
from datetime import datetime
from decimal import Decimal
from itertools import chain, product
from urllib.request import urlopen

from ..datatypes import AnyAtomicType, DateTime, Timezone, BooleanProxy, \
    DoubleProxy, DoubleProxy10
from ..exceptions import ElementPathTypeError
from ..helpers import WHITESPACES_PATTERN, is_xml_codepoint
from ..namespaces import XPATH_FUNCTIONS_NAMESPACE, XML_BASE
from ..etree import etree_iter_strings, is_etree_element
from ..collations import CollationManager
from ..tree_builders import get_node_tree
from ..xpath_nodes import XPathNode, DocumentNode, ElementNode
from ..xpath_token import XPathFunction, XPathMap, XPathArray
from ..xpath_context import XPathSchemaContext
from ._xpath31_operators import XPath31Parser

method = XPath31Parser.method
function = XPath31Parser.function

XPath31Parser.unregister('string-join')

TIMEZONE_MAP = {
    'UT': '00:00',
    'UTC': '00:00',
    'GMT': '00:00',
    'EST': '-05:00',
    'EDT': '-04:00',
    'CST': '-06:00',
    'CDT': '-05:00',
    'MST': '-07:00',
    'MDT': '-06:00',
    'PST': '-08:00',
    'PDT': '-07:00',
}


@method(function('string-join', nargs=(1, 2),
                 sequence_types=('xs:anyAtomicType*', 'xs:string', 'xs:string')))
def evaluate_string_join_function(self, context=None):
    items = [self.string_value(s) for s in self[0].select(context)]

    if len(self) == 1:
        return ''.join(items)
    return self.get_argument(context, 1, required=True, cls=str).join(items)


@method(function('size', prefix='map', label='map function', nargs=1,
                 sequence_types=('map(*)', 'xs:integer')))
def evaluate_map_size_function(self, context=None):
    return len(self.get_argument(context, required=True, cls=XPathMap))


@method(function('keys', prefix='map', label='map function', nargs=1,
                 sequence_types=('map(*)', 'xs:anyAtomicType*')))
def evaluate_map_keys_function(self, context=None):
    map_ = self.get_argument(context, required=True, cls=XPathMap)
    return map_.keys(context)


@method(function('contains', prefix='map', label='map function', nargs=2,
                 sequence_types=('map(*)', 'xs:anyAtomicType', 'xs:boolean')))
def evaluate_map_contains_function(self, context=None):
    map_ = self.get_argument(context, required=True, cls=XPathMap)
    key = self.get_argument(context, index=1, required=True, cls=AnyAtomicType)
    return key in map_.keys(context)


@method(function('get', prefix='map', label='map function', nargs=2,
                 sequence_types=('map(*)', 'xs:anyAtomicType', 'item()*')))
def evaluate_map_get_function(self, context=None):
    map_ = self.get_argument(context, required=True, cls=XPathMap)
    key = self.get_argument(context, index=1, required=True, cls=AnyAtomicType)
    return map_(context, key)


@method(function('put', prefix='map', label='put function', nargs=3,
                 sequence_types=('map(*)', 'xs:anyAtomicType', 'item()*', 'map(*)')))
def evaluate_map_put_function(self, context=None):
    map_ = self.get_argument(context, required=True, cls=XPathMap)
    key = self.get_argument(context, index=1, required=True, cls=AnyAtomicType)
    value = self[2].evaluate(context)
    if value is None:
        value = []

    items = chain(map_.items(context), [(key, value)])
    return XPathMap(self.parser, items=items)


@method(function('remove', prefix='map', label='remove function', nargs=2,
                 sequence_types=('map(*)', 'xs:anyAtomicType*', 'map(*)')))
def evaluate_map_remove_function(self, context=None):
    map_ = self.get_argument(context, required=True, cls=XPathMap)
    keys = self[1].evaluate(context)
    if keys is None:
        return map_
    elif isinstance(keys, list):
        items = ((k, v) for k, v in map_.items(context) if k not in keys)
    else:
        items = ((k, v) for k, v in map_.items(context) if k != keys)

    return XPathMap(self.parser, items=items)


@method(function('entry', prefix='map', label='map:entry function', nargs=2,
                 sequence_types=('xs:anyAtomicType', 'item()*', 'map(*)')))
def evaluate_map_entry_function(self, context=None):
    key = self.get_argument(context, required=True, cls=AnyAtomicType)
    value = self[1].evaluate(context)
    if value is None:
        value = []

    return XPathMap(self.parser, items=[(key, value)])


@method(function('merge', prefix='map', label='map:merge function', nargs=(1, 2),
                 sequence_types=('map(*)*', 'map(*)', 'map(*)')))
def evaluate_map_merge_function(self, context=None):
    duplicates = 'use-first'
    if len(self) > 1:
        options = self.get_argument(context, index=1, required=True, cls=XPathMap)
        for opt, value in options.items(context):
            if opt == 'duplicates':
                if value in ('reject', 'use-first', 'use-last', 'use-any', 'combine'):
                    duplicates = value
                else:
                    raise self.error('FOJS0005')

    items = {}
    for map_ in self[0].select(context):
        for k, v in map_.items(context):
            if k not in items:
                items[k] = v
            elif duplicates == 'reject':
                raise self.error('FOJS0005')
            elif duplicates == 'use-last':
                items[k] = v
            elif duplicates == 'combine':
                try:
                    items[k].append(v)
                except AttributeError:
                    items[k] = [items[k], v]

    return XPathMap(self.parser, items)


@method(function('find', prefix='map', label='map:find function', nargs=2,
                 sequence_types=('map(*)', 'xs:anyAtomicType', 'array(*)')))
def evaluate_map_find_function(self, context=None):
    key = self.get_argument(context, index=1, required=True, cls=AnyAtomicType)
    items = []

    def iter_matching_items(obj):
        if isinstance(obj, list):
            for x in obj:
                iter_matching_items(x)
        elif isinstance(obj, XPathArray):
            for x in obj.items(context):
                iter_matching_items(x)
        elif isinstance(obj, XPathMap):
            for k, v in obj.items(context):
                if k == key:
                    items.append(v)
                    iter_matching_items(v)

    for item in self[0].select(context):
        iter_matching_items(item)

    return XPathArray(self.parser, items)


@method(function('for-each', prefix='map', label='map:for-each function', nargs=2,
                 sequence_types=('map(*)', 'function(xs:anyAtomicType, item()*) as item()*',
                                 'item()*')))
def select_map_for_each_function(self, context=None):
    map_ = self.get_argument(context, required=True, cls=XPathMap)
    func = self.get_argument(context, index=1, required=True, cls=XPathFunction)

    for k, v in map_.items(context):
        yield func(context, k, v)


@method(function('size', prefix='array', label='array function', nargs=1,
                 sequence_types=('array(*)', 'xs:integer')))
def evaluate_array_size_function(self, context=None):
    return len(self.get_argument(context, required=True, cls=XPathArray))


@method(function('get', prefix='array', label='array function', nargs=2,
                 sequence_types=('array(*)', 'xs:integer', 'item()*')))
def evaluate_array_get_function(self, context=None):
    array_ = self.get_argument(context, required=True, cls=XPathArray)
    position = self.get_argument(context, index=1, required=True, cls=int)
    return array_(context, position)


@method(function('put', prefix='array', label='array:put function', nargs=3,
                 sequence_types=('array(*)', 'xs:integer', 'item()*', 'array(*)')))
def evaluate_array_put_function(self, context=None):
    array_ = self.get_argument(context, required=True, cls=XPathArray)
    position = self.get_argument(context, index=1, required=True, cls=int)
    member = self[2].evaluate(context)
    if member is None:
        member = []

    if position <= 0:
        raise self.error('FOAY0002' if position else 'FOAY0001')

    items = array_.items(context)
    try:
        items[position - 1] = member
    except IndexError:
        raise self.error('FOAY0001')

    return XPathArray(self.parser, items=items)


@method(function('insert-before', prefix='array', label='array:insert-before function', nargs=3,
                 sequence_types=('array(*)', 'xs:integer', 'item()*', 'array(*)')))
def evaluate_array_insert_before_function(self, context=None):
    array_ = self.get_argument(context, required=True, cls=XPathArray)
    position = self.get_argument(context, index=1, required=True, cls=int)
    member = self[2].evaluate(context)
    if member is None:
        member = []

    if position <= 0:
        raise self.error('FOAY0002' if position else 'FOAY0001')

    items = array_.items(context)
    try:
        items.insert(position - 1, member)
    except IndexError:
        raise self.error('FOAY0001')

    return XPathArray(self.parser, items=items)


@method(function('append', prefix='array', label='array:append function', nargs=2,
                 sequence_types=('array(*)', 'item()*', 'array(*)')))
def evaluate_array_append_function(self, context=None):
    array_ = self.get_argument(context, required=True, cls=XPathArray)
    appendage = self[1].evaluate(context)
    if appendage is None:
        appendage = []

    items = array_.items(context)
    items.append(appendage)
    return XPathArray(self.parser, items=items)


@method(function('remove', prefix='array', nargs=2,
                 sequence_types=('array(*)', 'xs:integer*', 'array(*)')))
def evaluate_array_remove_function(self, context=None):
    array_ = self.get_argument(context, required=True, cls=XPathArray)
    positions_ = self[1].evaluate(context)
    if positions_ is None:
        return array_

    positions = positions_ if isinstance(positions_, list) else [positions_]
    if any(p <= 0 or p > len(array_) for p in positions):
        raise self.error('FOAY0001')

    items = (v for k, v in enumerate(array_.items(context), 1) if k not in positions)
    return XPathArray(self.parser, items=items)


@method(function('subarray', prefix='array', label='array:subarray function', nargs=(2, 3),
                 sequence_types=('array(*)', 'xs:integer', 'xs:integer', 'array(*)')))
def evaluate_array_subarray_function(self, context=None):
    array_ = self.get_argument(context, required=True, cls=XPathArray)
    start = self.get_argument(context, index=1, required=True, cls=int)
    if start < 1 or start > len(array_) + 1:
        raise self.error('FOAY0001')

    if len(self) > 2:
        length = self.get_argument(context, index=2, required=True, cls=int)
        if length < 0:
            raise self.error('FOAY0002')
        if start + length > len(array_) + 1:
            raise self.error('FOAY0001')
        items = array_.items(context)[start - 1:start + length - 1]
    else:
        items = array_.items(context)[start - 1:]

    return XPathArray(self.parser, items=items)


@method(function('head', prefix='array', label='array:head function', nargs=1,
                 sequence_types=('array(*)', 'item()*')))
def evaluate_array_head_function(self, context=None):
    array_ = self.get_argument(context, required=True, cls=XPathArray)

    items = array_.items(context)
    if not items:
        raise self.error('FOAY0001')
    return items[0]


@method(function('tail', prefix='array', label='array:tail function', nargs=1,
                 sequence_types=('array(*)', 'array(*)')))
def evaluate_array_tail_function(self, context=None):
    array_ = self.get_argument(context, required=True, cls=XPathArray)

    items = array_.items(context)
    if not items:
        raise self.error('FOAY0001')
    return XPathArray(self.parser, items=items[1:])


@method(function('reverse', prefix='array', label='array:reverse function', nargs=1,
                 sequence_types=('array(*)', 'array(*)')))
def evaluate_array_reverse_function(self, context=None):
    array_ = self.get_argument(context, required=True, cls=XPathArray)

    items = array_.items(context)
    return XPathArray(self.parser, items=reversed(items))


@method(function('join', prefix='array', label='array:join function', nargs=1,
                 sequence_types=('array(*)', 'array(*)')))
def evaluate_array_join_function(self, context=None):
    items = []
    for array_ in self[0].select(context):
        if not isinstance(array_, XPathArray):
            raise self.error('XPTY0004')
        items.extend(array_.items(context))

    return XPathArray(self.parser, items=items)


@method(function('flatten', prefix='array', label='array:flatten function', nargs=1,
                 sequence_types=('item()*', 'item()*')))
def evaluate_array_flatten_function(self, context=None):
    items = []
    for obj in self[0].select(context):
        if isinstance(obj, XPathArray):
            items.extend(obj.iter_flatten(context))
        else:
            items.append(obj)

    return items


@method(function('for-each', prefix='array', label='array:for-each function', nargs=2,
                 sequence_types=('array(*)', 'function(item()*) as item()*', 'array(*)')))
def evaluate_array_for_each_function(self, context=None):
    array_ = self.get_argument(context, required=True, cls=XPathArray)
    func = self.get_argument(context, index=1, required=True, cls=XPathFunction)

    items = array_.items(context)
    return XPathArray(self.parser, items=map(lambda x: func(context, x), items))


@method(function('for-each-pair', prefix='array', label='array:for-each-pair function', nargs=3,
                 sequence_types=('array(*)', 'array(*)', 'function(item()*, item()*) as item()*',
                                 'array(*)')))
def evaluate_array_for_each_pair_function(self, context=None):
    array1 = self.get_argument(context, required=True, cls=XPathArray)
    array2 = self.get_argument(context, index=1, required=True, cls=XPathArray)
    func = self.get_argument(context, index=2, required=True, cls=XPathFunction)

    items = zip(array1.items(context), array2.items(context))
    return XPathArray(self.parser, items=map(lambda x: func(context, *x), items))


@method(function('filter', prefix='array', label='array:filter function', nargs=2,
                 sequence_types=('array(*)', 'function(item()*) as xs:boolean', 'array(*)')))
def evaluate_array_filter_function(self, context=None):
    array_ = self.get_argument(context, required=True, cls=XPathArray)
    func = self.get_argument(context, index=1, required=True, cls=XPathFunction)

    items = array_.items(context)
    return XPathArray(self.parser, items=filter(lambda x: func(context, x), items))


@method(function('fold-left', prefix='array', label='array:fold-left function', nargs=3,
                 sequence_types=('array(*)', 'item()*',
                                 'function(item()*, item()) as item()*', 'item()*')))
@method(function('fold-right', prefix='array', label='array:fold-right function', nargs=3,
                 sequence_types=('array(*)', 'item()*',
                                 'function(item()*, item()) as item()*', 'item()*')))
def select_array_fold_left_right_functions(self, context=None):
    func = self[2][1] if self[2].symbol == ':' else self[2]
    if not isinstance(func, XPathFunction):
        func = self.get_argument(context, index=2, cls=XPathFunction, required=True)
    if func.arity != 2:
        raise self.error('XPTY0004', "function arity must be 2")

    array_ = self.get_argument(context, required=True, cls=XPathArray)
    zero = self.get_argument(context, index=1)

    result = zero

    if self.symbol == 'fold-left':
        for item in array_.items(context):
            result = func(context, result, item)
    else:
        for item in reversed(array_.items(context)):
            result = func(context, item, result)

    if isinstance(result, list):
        yield from result
    else:
        yield result


@method(function('sort', label='sort function', nargs=(1, 3),
                 sequence_types=('item()*', 'xs:string?',
                                 'function(item()) as xs:anyAtomicType*', 'item()*')))
def evaluate_sort_function(self, context=None):
    if len(self) < 2:
        collation = self.parser.default_collation
    else:
        collation = self.get_argument(context, 1, cls=str)
        if collation is None:
            collation = self.parser.default_collation

    with CollationManager(collation, self):
        if len(self) == 3:
            func = self.get_argument(context, index=2, required=True, cls=XPathFunction)
            return sorted(self[0].select(context), key=lambda x: func(context, x))
        else:
            return sorted(self[0].select(context))


@method(function('sort', prefix='array', label='array:sort function', nargs=(1, 3),
                 sequence_types=('array(*)', 'xs:string?',
                                 'function(item()*) as xs:anyAtomicType*', 'array(*)')))
def evaluate_array_sort_function(self, context=None):
    array_ = self.get_argument(context, required=True, cls=XPathArray)

    if len(self) < 2:
        collation = self.parser.default_collation
    else:
        collation = self.get_argument(context, 1, cls=str)
        if collation is None:
            collation = self.parser.default_collation

    with CollationManager(collation, self):
        if len(self) == 3:
            func = self.get_argument(context, index=2, required=True, cls=XPathFunction)
            items = sorted(array_.items(context), key=lambda x: func(context, x))
        else:
            items = sorted(array_.items(context))

    return XPathArray(self.parser, items)


@method(function('json-doc', label='parse-json function', nargs=(1, 2),
                 sequence_types=('xs:string?', 'map(*)', 'item()?')))
@method(function('parse-json', label='parse-json function', nargs=(1, 2),
                 sequence_types=('xs:string?', 'map(*)', 'item()?')))
def evaluate_parse_json_functions(self, context=None):
    if self.symbol == 'json-doc':
        href = self.get_argument(context, cls=str)
        if href is None:
            return None

        with urlopen(href) as fp:
            json_text = fp.read()
    else:
        json_text = self.get_argument(context, cls=str)
        if json_text is None:
            return None

    liberal = False
    duplicates = 'use-first'
    escape = True

    def fallback(*args):
        return '&#xFFFD;'

    if len(self) > 1:
        map_ = self.get_argument(context, index=1, required=True, cls=XPathMap)
        for k, v in map_.items(context):
            if k == 'liberal':
                if not isinstance(v, bool):
                    raise self.error('FOJS0005')
                liberal = v
            elif k == 'duplicates':
                if v not in ('use-first', 'use-last', 'reject'):
                    raise self.error('FOJS0005')
                duplicates = v
            elif k == 'escape':
                if not isinstance(v, bool):
                    raise self.error('FOJS0005')
                escape = v
            elif k == 'fallback':
                if not isinstance(v, XPathFunction):
                    raise self.error('FOJS0005')
                # fallback = v  TODO
            else:
                raise self.error('FOJS0005')

    def json_object_to_xpath(obj):
        items = {}
        for k_, v_ in obj.items():
            if k_ in items:
                if duplicates == 'use-first':
                    continue
                elif duplicates == 'reject':
                    raise self.error('FOJS0003')

            if isinstance(v_, list):
                items[k_] = XPathArray(self.parser, v_)
            else:
                items[k_] = v_

        return XPathMap(self.parser, items)

    kwargs = {'object_hook': json_object_to_xpath}
    if liberal or escape:
        kwargs['strict'] = False
    if liberal:
        def parse_constant(s):
            raise self.error('FOJS0001')

        kwargs['parse_constant'] = parse_constant

    result = json.JSONDecoder(**kwargs).decode(json_text)
    if isinstance(result, list):
        return XPathArray(self.parser, result)
    return result


@method(function('load-xquery-module', label='function', nargs=(1, 2),
                 sequence_types=('xs:string', 'map(*)', 'map(*)')))
def evaluate_load_xquery_module_function(self, context=None):
    module_uri = self.get_argument(context, required=True, cls=str)
    if not module_uri:
        raise self.error('FOQM0001')

    if len(self) > 1:
        options = self.get_argument(context, index=1, required=True, cls=XPathMap)
        for k, v in options.items(context):
            if k == 'xquery-version':
                if not isinstance(v, (int, float, Decimal)):
                    raise self.error('FOQM0005')
            elif k == 'location-hints':
                if not isinstance(v, str) or \
                        not (isinstance(v, list) and all(isinstance(x, str) for x in v)):
                    raise self.error('FOQM0005')
            elif k == 'context-item':
                if isinstance(v, list) and len(v) > 1:
                    raise self.error('FOQM0005')
            elif k == 'variables' or k == 'vendor-options':
                if not isinstance(v, XPathMap) or \
                        any(not isinstance(x, str) for x in v.keys(context)):
                    raise self.error('FOQM0005')
            else:
                raise self.error('FOQM0005')

    raise self.error('FOQM0006')  # XQuery not available


@method(function('transform', label='function', nargs=1,
                 sequence_types=('map(*)', 'map(*)')))
def evaluate_transform_function(self, context=None):
    options = self.get_argument(context, required=True, cls=XPathMap)
    for k, v in options.items(context):
        # Check only 'xslt-version' parameter until an effective
        # XSLT implementation will be loadable.
        if k == 'xslt-version':
            if not isinstance(v, (int, float, Decimal)):
                raise self.error('FOXT0002')

    raise self.error('FOXT0001')  # XSLT not available


@method(function('random-number-generator', label='function', nargs=(0, 1),
                 sequence_types=('xs:anyAtomicType?', 'map(xs:string, item())')))
def evaluate_random_number_generator_function(self, context=None):
    seed = self.get_argument(context, cls=AnyAtomicType)
    if not isinstance(seed, (int, str)):
        seed = str(seed)
    random.seed(seed)

    def permute(seq):
        seq = [x for x in seq]
        random.shuffle(seq)
        return seq

    def next_random():
        items = {
            'number': random.random(),
            'next': next_random,
            'permute': permute,
        }
        return XPathMap(self.parser, items)

    return next_random()


@method(function('apply', label='function', nargs=2,
                 sequence_types=('function(*)', 'array(*)', 'item()*')))
def evaluate_apply_function(self, context=None):
    func = self.get_argument(context, required=True, cls=XPathFunction)
    array_ = self.get_argument(context, index=1, required=True, cls=XPathArray)

    try:
        return func(context, *array_.items(context))
    except ElementPathTypeError as err:
        if not err.code.endswith(('XPST0017', 'XPTY0004')):
            raise
        raise self.error('FOAP0001') from None


@method(function('parse-ietf-date', label='function', nargs=1,
                 sequence_types=('xs:string?', 'xs:dateTime?')))
def evaluate_parse_ietf_date_function(self, context=None):
    value = self.get_argument(context, cls=str)
    if value is None:
        return None

    value = WHITESPACES_PATTERN.sub(' ', value).strip()
    value = value.replace(' -', '-').replace('- ', '-')

    tzname_regex = r'\b(UT|UTC|GMT|EST|EDT|CST|CDT|MST|MDT|PST|PDT)\b'
    tzname_match = re.search(tzname_regex, value, re.IGNORECASE)
    if tzname_match is not None:
        # only to let be parsed by strptime()
        value = re.sub(tzname_regex, 'UTC', value, re.IGNORECASE)

    if value and value[0].isalpha():
        # Parse dayname part (that is then ignored)
        try:
            dayname, value = value.split(' ', maxsplit=1)
        except ValueError:
            raise self.error('FORG0010') from None
        else:
            if dayname.endswith(','):
                dayname = dayname[:-1]

            for fmt in ['%A', '%a']:
                try:
                    datetime.strptime(dayname, fmt)
                except ValueError:
                    continue
                else:
                    break
            else:
                raise self.error('FORG0010')

    # Parsing generating every combination
    if value and value[0].isalpha():
        # Parse asctime rule
        fmt_alternatives = (
            ['%b %d %H:%M', '%b-%d %H:%M'],
            ['', ':%S', ':%S.%f'],
            ['', ' %Z', ' %z', ' %z(%Z)'],
            [' %Y', ' %y'],
        )
    else:
        # Parse datespec rule
        fmt_alternatives = (
            ['%d %b ', '%d-%b-', '%d %b-', '%d-%b '],
            ['%Y %H:%M', '%y %H:%M'],
            ['', ':%S', ':%S.%f'],
            ['', ' %Z', ' %z', ' %z(%Z)'],
        )

    for fmt in product(*fmt_alternatives):
        try:
            dt = datetime.strptime(value, ''.join(fmt))
        except ValueError:
            continue
        else:
            if tzname_match is not None and dt.tzinfo is None:
                tzname = tzname_match.group(0).upper()
                dt = dt.replace(tzinfo=Timezone.fromstring(TIMEZONE_MAP[tzname]))

            return DateTime.fromdatetime(dt)
    else:
        raise self.error('FORG0010')


@method(function('contains-token', label='function', nargs=(2, 3),
                 sequence_types=('xs:string*', 'xs:string', 'xs:string', 'xs:boolean')))
def evaluate_contains_token_function(self, context=None):
    token_string = self.get_argument(context, index=1, required=True, cls=str)
    token_string = token_string.strip()

    if len(self) < 3:
        collation = self.parser.default_collation
    else:
        collation = self.get_argument(context, 2, required=True, cls=str)

    with CollationManager(collation, self) as manager:
        for input_string in self[0].select(context):
            if not isinstance(input_string, str):
                raise self.error('XPTY0004')
            if any(manager.eq(token_string, x) for x in input_string.split()):
                return True
        else:
            return False


@method(function('collation-key', label='function', nargs=(1, 2),
                 sequence_types=('xs:string', 'xs:string', 'xs:base64Binary')))
def evaluate_collation_key_function(self, context=None):
    self.get_argument(context, required=True, cls=str)
    if len(self) > 1:
        self.get_argument(context, index=1, required=True, cls=str)

    raise self.error('FOCH0004')


NULL_TAG = f'{{{XPATH_FUNCTIONS_NAMESPACE}}}null'
BOOLEAN_TAG = f'{{{XPATH_FUNCTIONS_NAMESPACE}}}boolean'
NUMBER_TAG = f'{{{XPATH_FUNCTIONS_NAMESPACE}}}number'
STRING_TAG = f'{{{XPATH_FUNCTIONS_NAMESPACE}}}string'
ARRAY_TAG = f'{{{XPATH_FUNCTIONS_NAMESPACE}}}array'
MAP_TAG = f'{{{XPATH_FUNCTIONS_NAMESPACE}}}map'


@method(function('xml-to-json', label='function', nargs=(1, 2),
                 sequence_types=('node()?', 'map(*)', 'xs:string?')))
def evaluate_xml_to_json_function(self, context=None):
    input_node = self.get_argument(context, cls=XPathNode)
    if input_node is None:
        return None

    indent = False
    if len(self) > 1:
        options = self.get_argument(context, index=1, required=True, cls=XPathMap)
        indent = options(context, 'indent')
        if indent is not None and isinstance(indent, bool):
            raise self.error('FOJS0005')

    if isinstance(input_node, DocumentNode):
        root = input_node.value.getroot()
    elif isinstance(input_node, ElementNode):
        root = input_node.value
    else:
        raise self.error('FOJS0006')

    def elem_to_json(elements):
        chunks = []

        for child in elements:
            if callable(child.tag):
                continue

            if child.tag == NULL_TAG:
                chunks.append('null')

            elif child.tag == BOOLEAN_TAG:
                if BooleanProxy(''.join(etree_iter_strings(child))):
                    chunks.append('true')
                else:
                    chunks.append('false')

            elif child.tag == NUMBER_TAG:
                value = ''.join(etree_iter_strings(child))
                try:
                    if self.parser.xsd_version == '1.0':
                        number = DoubleProxy10(value)
                    else:
                        number = DoubleProxy(value)
                except ValueError:
                    chunks.append('nan')
                else:
                    chunks.append(str(number).rstrip('0').rstrip('.'))

            elif child.tag == STRING_TAG:
                value = ''.join(etree_iter_strings(child))
                if child.get('escaped') == 'true':
                    value = json.dumps(value)

                chunks.append(f'"{value}"')

            elif child.tag == ARRAY_TAG:
                chunks.append(f'[{elem_to_json(child)}]')

            elif child.tag == MAP_TAG:
                map_chunks = []
                for e in child:
                    key = e.get('key')
                    if child.get('escaped-key') == 'true':
                        key = json.dumps(key, ensure_ascii=True)

                    map_chunks.append(f'"{key}":{elem_to_json((e,))}')
                chunks.append('{%s}' % ','.join(map_chunks))

        return ','.join(chunks)

    return elem_to_json((root,))


@method(function('json-to-xml', label='function', nargs=(1, 2),
                 sequence_types=('xs:string?', 'map(*)', 'document-node()?')))
def evaluate_json_to_xml_function(self, context=None):
    json_text = self.get_argument(context, cls=str)
    if json_text is None or isinstance(context, XPathSchemaContext):
        return None
    elif context is not None:
        etree = context.etree
    else:
        raise self.missing_context()

    def escape_json_string(s):
        s = s.replace('\b', r'\b').\
            replace('\r', r'\r').\
            replace('\n', r'\n').\
            replace('\t', r'\t').\
            replace('\f', r'\f').\
            replace('/', r'\/')
        return ''.join(x if is_xml_codepoint(ord(x)) else fr'\u{ord(x):04x}' for x in s)

    def _fallback(*args):
        return '&#xFFFD;'

    liberal = False
    validate = False
    duplicates = None
    escape = False
    fallback = _fallback

    if len(self) > 1:
        options = self.get_argument(context, index=1, required=True, cls=XPathMap)

        for key, value in options.items(context):
            if key == 'liberal':
                if not isinstance(value, bool):
                    raise self.error('XPTY0004')
                liberal = value

            elif key == 'duplicates':
                if not isinstance(value, str):
                    raise self.error('XPTY0004')
                elif value not in ('reject', 'retain', 'use-first'):
                    raise self.error('FOJS0005')
                duplicates = value

            elif key == 'validate':
                if not isinstance(value, bool):
                    raise self.error('XPTY0004')
                validate = value

            elif key == 'escape':
                if not isinstance(value, bool):
                    raise self.error('XPTY0004')
                escape = value

            elif key == 'fallback':
                if not isinstance(value, XPathFunction):
                    raise self.error('XPTY0004')
                fallback = value

            else:
                raise self.error('FOJS0005')

        if duplicates is None:
            duplicates = 'reject' if validate else 'retain'
        elif validate and duplicates == 'retain':
            raise self.error('FOJS0005')

    def value_to_etree(v, **attrib):
        if v is None:
            elem = etree.Element(NULL_TAG, **attrib)
        elif isinstance(v, list):
            elem = etree.Element(ARRAY_TAG, **attrib)
            for item in v:
                elem.append(value_to_etree(item))
        elif isinstance(v, bool):
            elem = etree.Element(BOOLEAN_TAG, **attrib)
            elem.text = 'true' if v else 'false'
        elif isinstance(v, (int, float)):
            elem = etree.Element(NUMBER_TAG, **attrib)
            elem.text = str(v)
        elif isinstance(v, str):
            if not escape:
                v = ''.join(x if is_xml_codepoint(ord(x)) else fallback(x) for x in v)
                elem = etree.Element(STRING_TAG, **attrib)
            else:
                v = escape_json_string(v)
                if '\\' in v:
                    elem = etree.Element(STRING_TAG, escaped='true', **attrib)
                else:
                    elem = etree.Element(STRING_TAG, **attrib)

            elem.text = v

        elif is_etree_element(v):
            v.attrib.update(attrib)
            return v
        else:
            raise ElementPathTypeError(f'unexpected type {type(v)}')

        return elem

    def json_object_to_etree(obj):
        keys = set()
        items = []
        for k, v in obj:
            if k not in keys:
                keys.add(k)
            elif duplicates == 'use-first':
                continue
            elif duplicates == 'reject':
                raise self.error('FOJS0003')

            if not escape:
                k = ''.join(x if is_xml_codepoint(ord(x)) else fallback(x) for x in k)
                k = k.replace('"', '&#34;')
                attrib = {'key': k}
            else:
                k = escape_json_string(k)
                if '\\' in k:
                    attrib = {'escaped-key': 'true', 'key': k}
                else:
                    attrib = {'key': k}

            items.append(value_to_etree(v, **attrib))

        elem = etree.Element(MAP_TAG)
        for item in items:
            elem.append(item)
        return elem

    kwargs = {'object_pairs_hook': json_object_to_etree}
    if liberal or escape:
        kwargs['strict'] = False
    if liberal:
        def parse_constant(s):
            raise self.error('FOJS0001')

        kwargs['parse_constant'] = parse_constant

    try:
        if json_text.startswith('\uFEFF'):
            # Exclude BOM character
            result = json.JSONDecoder(**kwargs).decode(json_text[1:])
        else:
            result = json.JSONDecoder(**kwargs).decode(json_text)
    except json.JSONDecodeError as err:
        raise self.error('FOJS0001', str(err)) from None

    if is_etree_element(result):
        document = etree.ElementTree(result)
    else:
        document = etree.ElementTree(value_to_etree(result))

    root = document.getroot()
    if XML_BASE not in root.attrib and self.parser.base_uri:
        root.set(XML_BASE, self.parser.base_uri)

    if validate:
        try:
            from ..validators import validate_json_to_xml
        except ImportError:
            raise self.error('FOJS0004')
        else:
            validate_json_to_xml(document.getroot())

    return get_node_tree(document, namespaces={'j': XPATH_FUNCTIONS_NAMESPACE})
