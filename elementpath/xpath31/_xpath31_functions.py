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
    return map_.contains(context, key)


@method(function('get', prefix='map', label='map function', nargs=2,
                 sequence_types=('map(*)', 'xs:anyAtomicType', 'item()*')))
def evaluate_map_get_function(self, context=None):
    map_ = self.get_argument(context, required=True, cls=XPathMap)
    key = self.get_argument(context, index=1, required=True, cls=AnyAtomicType)
    return map_(context, key)


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


@method(function('put', prefix='array', label='array function', nargs=3,
                 sequence_types=('array(*)', 'xs:integer', 'item()*', 'array(*)')))
def evaluate_array_put_function(self, context=None):
    array_ = self.get_argument(context, required=True, cls=XPathArray)
    position = self.get_argument(context, index=1, required=True, cls=int)

    member = self[2].evaluate(context)
    if member is None:
        member = []
    return array_.put(position, member, context)
