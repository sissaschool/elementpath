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
from itertools import chain

from ..datatypes import AnyAtomicType
from ..xpath_token import XPathMap, XPathArray
from ._xpath31_operators import XPath31Parser

method = XPath31Parser.method
function = XPath31Parser.function

XPath31Parser.unregister('string-join')


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
        self.error('FOAY0002' if position else 'FOAY0001')

    items = array_.items(context)
    try:
        items[position - 1] = member
    except IndexError:
        self.error('FOAY0001')

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


@method(function('subarray', prefix='array', label='array:subarray function', nargs=(2, 3),
                 sequence_types=('array(*)', 'xs:integer', 'xs:integer', 'array(*)')))
def evaluate_array_subarray_function(self, context=None):
    array_ = self.get_argument(context, required=True, cls=XPathArray)
    start = self.get_argument(context, index=1, required=True, cls=int)
    if start < 1 or start > len(array_):
        self.error('FOAY0001')

    if len(self) > 2:
        length = self.get_argument(context, index=2, required=True, cls=int)
        if length <= 0:
            self.error('FOAY0002')
        if start + length > len(array_):
            self.error('FOAY0001')
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
        self.error('FOAY0001')
    return items[0]


@method(function('tail', prefix='array', label='array:tail function', nargs=1,
                 sequence_types=('array(*)', 'array(*)')))
def evaluate_array_head_function(self, context=None):
    array_ = self.get_argument(context, required=True, cls=XPathArray)

    items = array_.items(context)
    if not items:
        self.error('FOAY0001')
    return XPathArray(self.parser, items=items[1:])


@method(function('reverse', prefix='array', label='array:reverse function', nargs=1,
                 sequence_types=('array(*)', 'array(*)')))
def evaluate_array_head_function(self, context=None):
    array_ = self.get_argument(context, required=True, cls=XPathArray)

    items = array_.items(context)
    return XPathArray(self.parser, items=reversed(items))


@method(function('join', prefix='array', label='array:join function', nargs=1,
                 sequence_types=('array(*)', 'array(*)')))
def evaluate_array_join_function(self, context=None):
    items = []
    for array_ in self[0].select(context):
        if not isinstance(array_, XPathArray):
            self.error('XPTY0004')
        items.extend(array_.items(context))

    return XPathArray(self.parser, items=items)


@method(function('flatten', prefix='array', label='array:flatten function', nargs=1,
                 sequence_types=('item()*', 'array(*)')))
def evaluate_array_flatten_function(self, context=None):
    items = []
    for obj in self[0].select(context):
        if isinstance(obj, XPathArray):
            items.extend(obj.iter_flatten(context))
        else:
            items.append(obj)

    return XPathArray(self.parser, items=items)
