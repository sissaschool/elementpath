#!/usr/bin/env python
#
# Copyright (c), 2018-2022, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
#
# Note: Many tests are built using the examples of the XPath standards,
#       published by W3C under the W3C Document License.
#
#       References:
#           https://www.w3.org/TR/xpath-3/
#           https://www.w3.org/TR/xpath-30/
#           https://www.w3.org/TR/xpath-31/
#           https://www.w3.org/Consortium/Legal/2015/doc-license
#           https://www.w3.org/TR/charmod-norm/
#
import unittest
import os
from textwrap import dedent
from typing import cast

try:
    import lxml.etree as lxml_etree
except ImportError:
    lxml_etree = None

try:
    import xmlschema
except ImportError:
    xmlschema = None
else:
    xmlschema.XMLSchema.meta_schema.build()

from elementpath import XPathContext, select
from elementpath.etree import etree_deep_equal
from elementpath.datatypes import DateTime, Base64Binary
from elementpath.xpath_nodes import DocumentNode
from elementpath.xpath3 import XPath31Parser
from elementpath.xpath_tokens import XPathMap, XPathArray

try:
    from tests import test_xpath30
except ImportError:
    import test_xpath30

MAP_WEEKDAYS = """\
map {
  "Su" : "Sunday",
  "Mo" : "Monday",
  "Tu" : "Tuesday",
  "We" : "Wednesday",
  "Th" : "Thursday",
  "Fr" : "Friday",
  "Sa" : "Saturday"
}"""

MAP_WEEKDAYS_DE = """\
map{0:"Sonntag", 1:"Montag", 2:"Dienstag",
     3:"Mittwoch", 4:"Donnerstag", 5:"Freitag", 6:"Samstag"}"""


NESTED_MAP = """\
map {
    "book": map {
        "title": "Data on the Web",
        "year": 2000,
        "author": [
            map {
                "last": "Abiteboul",
                "first": "Serge"
            },
            map {
                "last": "Buneman",
                "first": "Peter"
            },
            map {
                "last": "Suciu",
                "first": "Dan"
            }
        ],
        "publisher": "Morgan Kaufmann Publishers",
        "price": 39.95
    }
}"""


class XPath31ParserTest(test_xpath30.XPath30ParserTest):

    def setUp(self):
        self.parser = XPath31Parser(namespaces=self.namespaces)

    def test_map_weekdays(self):
        token = self.parser.parse(MAP_WEEKDAYS)
        self.assertIsInstance(token, XPathMap)

        map_value = {'Su': 'Sunday',
                     'Mo': 'Monday',
                     'Tu': 'Tuesday',
                     'We': 'Wednesday',
                     'Th': 'Thursday',
                     'Fr': 'Friday',
                     'Sa': 'Saturday'}

        self.assertEqual(token.symbol, 'map')
        self.assertEqual(token.label, 'map')
        self.assertEqual(token.source, f'map{map_value!r}'.replace(': ', ':'))
        self.assertEqual(repr(token), f'XPathMap({self.parser!r}, None)')
        self.assertEqual(str(token), 'not evaluated map constructor with 7 entries')

        self.assertDictEqual(token.evaluate()._map, map_value)
        self.assertEqual(repr(token.evaluate()), f'XPathMap({self.parser!r}, {map_value!r})')
        self.assertEqual(str(token.evaluate()), f'map{map_value!r}')

        token = self.parser.parse(f"{MAP_WEEKDAYS}('Mo')")
        self.assertEqual(token.evaluate(), 'Monday')

        token = self.parser.parse(f"{MAP_WEEKDAYS}('Mon')")
        self.assertEqual(token.evaluate(), [])

        token = self.parser.parse(f"let $x := {MAP_WEEKDAYS} return $x('Mo')")
        context = XPathContext(self.etree.XML('<empty/>'))
        self.assertEqual(token.evaluate(context), ['Monday'])

    def test_nested_map(self):
        token = self.parser.parse(f'{NESTED_MAP}("book")("title")')
        self.assertEqual(token.evaluate(), 'Data on the Web')

        self.assertEqual(token.symbol, '(')
        self.assertEqual(token.label, 'expression')
        self.assertTrue(token.source.startswith("map{'book':map{'title':'Data on the Web', "))
        self.assertTrue(token.source.endswith(", 'price':39.95}}('book')('title')"))
        self.assertEqual(repr(token), f'_LeftParenthesisExpression({self.parser!r})')
        self.assertEqual(str(token), "function call expression")

        token = self.parser.parse(f'{NESTED_MAP}("book")("author")')
        self.assertIsInstance(token.evaluate(), XPathArray)

        token = self.parser.parse(f'{NESTED_MAP}("book")("author")(1)("last")')
        self.assertEqual(token.evaluate(), 'Abiteboul')

    def test_map_ambiguity(self):
        self.parser.namespaces['a'] = 'http://xpath.test/ns'
        try:
            with self.assertRaises(SyntaxError):
                self.parser.parse('map{a:b}')

            token = cast(XPathMap, self.parser.parse('map{a :b}'))
            self.assertEqual(token[0].symbol, '(name)')
            self.assertEqual(token[0].value, 'a')
            self.assertEqual(token._values[0].symbol, '(name)')
            self.assertEqual(token._values[0].value, 'b')

            token = cast(XPathMap, self.parser.parse('map{a: b}'))
            self.assertEqual(token[0].symbol, '(name)')
            self.assertEqual(token[0].value, 'a')
            self.assertEqual(token._values[0].symbol, '(name)')
            self.assertEqual(token._values[0].value, 'b')

            token = self.parser.parse('map{a:b:c}')
            self.assertEqual(token[0].symbol, ':')
            self.assertEqual(token[0].value, 'a:b')
            self.assertEqual(token._values[0].symbol, '(name)')
            self.assertEqual(token._values[0].value, 'c')

            token = self.parser.parse('map{a:*:c}')
            self.assertEqual(token[0].symbol, ':')
            self.assertEqual(token[0].value, 'a:*')
            self.assertEqual(token._values[0].symbol, '(name)')
            self.assertEqual(token._values[0].value, 'c')

            token = self.parser.parse('map{*:b:c}')
            self.assertEqual(token[0].symbol, ':')
            self.assertEqual(token[0].value, '*:b')
            self.assertEqual(token._values[0].symbol, '(name)')
            self.assertEqual(token._values[0].value, 'c')
        finally:
            self.parser.namespaces.pop('a')

    def test_curly_array_constructor(self):
        token = self.parser.parse('array { 1, 2, 5, 7 }')
        self.assertIsInstance(token, XPathArray)

        self.assertEqual(token.symbol, 'array')
        self.assertEqual(token.label, 'array')
        self.assertEqual(token.source, 'array{1, 2, 5, 7}')
        self.assertEqual(repr(token), f'XPathArray({self.parser!r}, None)')
        self.assertEqual(str(token), 'not evaluated curly array constructor with 4 items')

        array = token.evaluate()
        self.assertEqual(repr(array), f'XPathArray({self.parser!r}, [1, 2, 5, 7])')
        self.assertEqual(str(array), '[1, 2, 5, 7]')

    def test_square_array_constructor(self):
        token = self.parser.parse('[ 1, 2, 5, 7 ]')
        self.assertIsInstance(token, XPathArray)

        self.assertEqual(token.symbol, '[')
        self.assertEqual(token.label, 'array')
        self.assertEqual(token.source, '[1, 2, 5, 7]')
        self.assertEqual(repr(token), f'XPathArray({self.parser!r}, None)')
        self.assertEqual(str(token), 'not evaluated square array constructor with 4 items')

        array = token.evaluate()
        self.assertEqual(repr(array), f'XPathArray({self.parser!r}, [1, 2, 5, 7])')
        self.assertEqual(str(array), '[1, 2, 5, 7]')

    def test_array_lookup(self):
        token = self.parser.parse('array { 1, 2, 5, 7 }(4)')
        self.assertEqual(token.evaluate(), 7)
        self.assertEqual(token.source, 'array{1, 2, 5, 7}(4)')
        self.assertEqual(repr(token), f'_LeftParenthesisExpression({self.parser!r})')
        self.assertEqual(str(token), "function call expression")

        token = self.parser.parse('[ 1, 2, 5, 7 ](4)')
        self.assertEqual(token.evaluate(), 7)
        self.assertEqual(token.source, '[1, 2, 5, 7](4)')
        self.assertEqual(repr(token), f'_LeftParenthesisExpression({self.parser!r})')
        self.assertEqual(str(token), "function call expression")

    def test_map_size_function(self):
        token = self.parser.parse('map:size(map{})')
        self.assertEqual(token.evaluate(), 0)
        self.assertEqual(str(token), "'map:size' function")
        self.assertEqual(repr(token), f"_PrefixedReferenceToken({self.parser!r}, 'map:size')")
        self.assertEqual(token.source, 'map:size(map{})')

        self.check_value('map:size(map{"true":1, "false":0})', 2)

    def test_map_keys_function(self):
        token = self.parser.parse('map:keys(map{})')
        self.assertListEqual(token.evaluate(), [])
        self.assertEqual(str(token), "'map:keys' function")
        self.assertEqual(repr(token), f"_PrefixedReferenceToken({self.parser!r}, 'map:keys')")
        self.assertEqual(token.source, 'map:keys(map{})')

        self.check_value('map:keys(map{1:"yes", 2:"no"})', {1, 2})

    def test_map_contains_function(self):
        self.check_value('map:contains(map{}, 1)', False)
        self.check_value('map:contains(map{}, "xyz")', False)
        self.check_value('map:contains(map{1:"yes", 2:"no"}, 1)', True)
        self.check_value('map:contains(map{"xyz":23}, "xyz")', True)
        self.check_value('map:contains(map{"abc":23, "xyz":()}, "xyz")', True)
        self.check_source('map:contains(map{"xyz":23}, "xyz")',
                          "map:contains(map{'xyz':23}, 'xyz')")

        context = XPathContext(self.etree.XML('<empty/>'))

        expression = f"let $x := {MAP_WEEKDAYS_DE} return map:contains($x, 2)"
        self.check_value(expression, [True], context=context)

        expression = f"let $x := {MAP_WEEKDAYS_DE} return map:contains($x, 9)"
        self.check_value(expression, [False], context=context)

    def test_map_get_function(self):
        context = XPathContext(self.etree.XML('<empty/>'))

        expression = f"let $x := {MAP_WEEKDAYS} return map:get($x, 'Mo')"
        self.check_value(expression, ['Monday'], context=context)

        # Tht source property returns a compacted normalized form
        expected = expression.\
            replace('\n', '').\
            replace('\r', '').\
            replace('  ', ' ').\
            replace('"', "'").\
            replace('map {', 'map{').\
            replace('{ ', '{').replace(' : ', ':')
        self.check_source(expression, expected)

        expression = f"let $x := {MAP_WEEKDAYS} return map:get($x, 'Mon')"
        self.check_value(expression, [], context=context)

    def test_map_put_function(self):
        context = XPathContext(self.etree.XML('<empty/>'))
        expression = f'let $week := {MAP_WEEKDAYS_DE} return map:put($week, 6, "Sonnabend")'
        result = XPathMap(self.parser, items={
            0: "Sonntag", 1: "Montag", 2: "Dienstag", 3: "Mittwoch",
            4: "Donnerstag", 5: "Freitag", 6: "Sonnabend"
        })
        self.check_value(expression, [result], context=context)

        expected = expression.\
            replace('\n', '').\
            replace('\r', '').\
            replace('"', "'").\
            replace('     ', ' ')
        self.check_source(expression, expected)

    def test_map_remove_function(self):
        context = XPathContext(self.etree.XML('<empty/>'))

        expression = f'let $week := {MAP_WEEKDAYS_DE} return map:remove($week, 4)'
        result = XPathMap(self.parser, items={
            0: "Sonntag", 1: "Montag", 2: "Dienstag",
            3: "Mittwoch", 5: "Freitag", 6: "Samstag"
        })
        self.check_value(expression, [result], context=context)

        expression = f'let $week := {MAP_WEEKDAYS_DE} return map:remove($week, (0, 6 to 7))'
        result = XPathMap(self.parser, items={
            1: "Montag", 2: "Dienstag", 3: "Mittwoch", 4: "Donnerstag", 5: "Freitag"
        })
        self.check_value(expression, [result], context=context)

        expression = f'let $week := {MAP_WEEKDAYS_DE} return map:remove($week, ())'
        result = XPathMap(self.parser, items={
            0: "Sonntag", 1: "Montag", 2: "Dienstag", 3: "Mittwoch",
            4: "Donnerstag", 5: "Freitag", 6: "Samstag"
        })
        self.check_value(expression, [result], context=context)

        expected = expression.\
            replace('\n', '').\
            replace('\r', '').\
            replace('"', "'").\
            replace('     ', ' ')
        self.check_source(expression, expected)

        expression = f'let $week := {MAP_WEEKDAYS_DE} return map:remove($week, 4)'
        result = XPathMap(self.parser, items={
            0: "Sonntag", 1: "Montag", 2: "Dienstag",
            3: "Mittwoch",  # 4: "Donnerstag",
            5: "Freitag", 6: "Samstag"
        })
        self.check_value(expression, [result], context=context)

    def test_map_entry_function(self):
        context = XPathContext(self.etree.XML('<empty/>'))

        expression = 'map:entry("M", "Monday")'
        result = XPathMap(self.parser, items={'M': 'Monday'})
        self.check_value(expression, result, context=context)
        self.check_source(expression, expression.replace('"', "'"))

        # e.g.: Alternative low level token-based check
        token = self.parser.parse('map:entry("M", "Monday")')
        result = token.evaluate(context)
        self.assertIsInstance(result, XPathMap)
        self.assertEqual(len(result), 1)
        self.assertEqual(result('M', context=context), 'Monday')

    def test_map_merge_function(self):
        week = {0: "Sonntag", 1: "Montag", 2: "Dienstag", 3: "Mittwoch",
                4: "Donnerstag", 5: "Freitag", 6: "Samstag"}
        context = XPathContext(
            root=self.etree.XML('<empty/>'),
            variables={'week': XPathMap(self.parser, week)}
        )

        expression = 'map:merge(())'
        result = XPathMap(self.parser, items={})
        self.check_value(expression, result, context=context)

        expression = 'map:merge((map:entry(0, "no"), map:entry(1, "yes")))'
        result = XPathMap(self.parser, items={0: 'no', 1: 'yes'})
        self.check_value(expression, result, context=context)
        self.check_source(expression, expression.replace('"', "'"))

        expression = 'map:merge(($week, map{7:"Unbekannt"}))'
        result = XPathMap(self.parser, items={
            0: "Sonntag", 1: "Montag", 2: "Dienstag", 3: "Mittwoch",
            4: "Donnerstag", 5: "Freitag", 6: "Samstag", 7: "Unbekannt"
        })
        self.check_value(expression, result, context=context)
        self.check_source(expression, expression.replace('"', "'"))

        expression = 'map:merge(($week, map{6:"Sonnabend"}), map{"duplicates":"use-last"})'
        result = XPathMap(self.parser, items={
            0: "Sonntag", 1: "Montag", 2: "Dienstag", 3: "Mittwoch",
            4: "Donnerstag", 5: "Freitag", 6: "Sonnabend"
        })
        self.check_value(expression, result, context=context)
        self.check_source(expression, expression.replace('"', "'"))

        expression = 'map:merge(($week, map{6:"Sonnabend"}), map{"duplicates":"use-first"}) '
        result = XPathMap(self.parser, items={
            0: "Sonntag", 1: "Montag", 2: "Dienstag", 3: "Mittwoch",
            4: "Donnerstag", 5: "Freitag", 6: "Samstag"
        })
        self.check_value(expression, result, context=context)
        self.check_source(expression, expression.strip().replace('"', "'"))

        expression = 'map:merge(($week, map{6:"Sonnabend"}), map{"duplicates":"combine"})'
        result = XPathMap(self.parser, items={
            0: "Sonntag", 1: "Montag", 2: "Dienstag", 3: "Mittwoch",
            4: "Donnerstag", 5: "Freitag", 6: ["Samstag", "Sonnabend"]
        })
        self.check_value(expression, result, context=context)

    def test_map_find_function(self):
        map1 = XPathMap(self.parser, {0: 'no', 1: 'yes'})
        map2 = XPathMap(self.parser, {0: 'non', 1: 'oui'})
        map3 = XPathMap(self.parser, {0: 'nein', 1: ['ja', 'doch']})

        context = XPathContext(
            root=self.etree.XML('<empty/>'),
            variables={'responses': XPathArray(self.parser, [map1, map2, map3])}
        )

        expression = 'map:find($responses, 0)'
        result = XPathArray(self.parser, items=['no', 'non', 'nein'])
        self.check_value(expression, result, context=context)

        expression = 'map:find($responses, 1)'
        result = XPathArray(self.parser, items=['yes', 'oui', ['ja', 'doch']])
        self.check_value(expression, result, context=context)

        expression = 'map:find($responses, 2)'
        result = XPathArray(self.parser, items=[])
        self.check_value(expression, result, context=context)
        self.check_source(expression, expression)

        array1 = XPathArray(self.parser, items=[])
        map1 = XPathMap(self.parser, {"name": "engine", "id": "YW678", "parts": array1})
        array2 = XPathArray(self.parser, items=[map1])
        map2 = XPathMap(self.parser, {"name": "car", "id": "QZ123", "parts": array2})

        context = XPathContext(
            root=self.etree.XML('<empty/>'),
            variables={'inventory': map2}
        )

        expression = 'map:find($inventory, "parts")'
        result = XPathArray(self.parser, items=[array2, array1])
        self.check_value(expression, result, context=context)
        self.check_source(expression, expression.replace('"', "'"))

        expression = 'let $inventory := map{"name":"car", "id":"QZ123", ' \
                     '"parts": [map{"name":"engine", "id":"YW678", "parts":[]}]} ' \
                     'return map:find($inventory, "parts")'
        token = self.parser.parse(expression)
        self.assertEqual(token.evaluate(context), [result])

    def test_map_for_each_function(self):
        context = XPathContext(self.etree.XML('<empty/>'))

        expression = 'map:for-each(map{1:"yes", 2:"no"}, function($k, $v){$k})'
        self.check_value(expression, [1, 2], context=context)

        expression = 'distinct-values(map:for-each(map{1:"yes", 2:"no"}, ' \
                     'function($k, $v) {$v}))'
        self.check_value(expression, ['yes', 'no'], context=context)
        self.check_source(expression, expression.replace('"', "'"))

        expression = 'map:merge(map:for-each(map{"a":1, "b":2}, ' \
                     'function($k, $v){map:entry($k, $v+1)}))'
        result = XPathMap(self.parser, {'a': 2, 'b': 3})
        self.check_value(expression, result, context=context)

    def test_array_size_function(self):
        self.check_value('array:size(["a", "b", "c"])', 3)
        self.check_value('array:size(["a", ["b", "c"]])', 2)
        self.check_value('array:size([ ])', 0)
        self.check_value('array:size([[ ]])', 1)
        self.check_source('array:size(["a", ["b", "c"]])',
                          "array:size(['a', ['b', 'c']])")

    def test_array_get_function(self):
        expression = 'array:get(["a", "b", "c"], 2)'
        self.check_value(expression, 'b')
        self.check_source(expression, expression.replace('"', "'"))

        token = self.parser.parse('array:get(["a", ["b", "c"]], 2)')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result._array, ['b', 'c'])

    def test_array_put_function(self):
        expression = ' array:put(["a", "b", "c"], 2, "d")'
        token = self.parser.parse(expression)
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), ['a', 'd', 'c'])
        self.check_source(expression, expression.lstrip().replace('"', "'"))

        token = self.parser.parse('array:put(["a", "b", "c"], 2, ("d", "e"))')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), ['a', ['d', 'e'], 'c'])

        token = self.parser.parse('array:put(["a"], 1, ["d", "e"])')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertIsInstance(result.items()[0], XPathArray)
        self.assertListEqual(result.items()[0].items(), ['d', 'e'])

    def test_array_insert_before_function(self):
        expression = 'array:insert-before(["a", "b", "c", "d"], 3, ("x", "y"))'
        token = self.parser.parse(expression)
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), ['a', 'b', ['x', 'y'], 'c', 'd'])
        self.check_source(expression, expression.replace('"', "'"))

        token = self.parser.parse('array:insert-before(["a", "b", "c", "d"], 5, ("x", "y"))')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), ['a', 'b', 'c', 'd', ['x', 'y']])

        token = self.parser.parse('array:insert-before(["a", "b", "c", "d"], 3, ["x", "y"])')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(
            result.items(), ['a', 'b', XPathArray(self.parser, ['x', 'y']), 'c', 'd']
        )

    def test_array_append_function(self):
        token = self.parser.parse('array:append(["a", "b", "c"], "d")')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), ['a', 'b', 'c', 'd'])

        expression = 'array:append(["a", "b", "c"], ("d", "e"))'
        token = self.parser.parse(expression)
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), ['a', 'b', 'c', ['d', 'e']])
        self.check_source(expression, expression.replace('"', "'"))

        token = self.parser.parse('array:append(["a", "b", "c"], ["d", "e"])')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(
            result.items(), ['a', 'b', 'c', XPathArray(self.parser, ['d', 'e'])]
        )

    def test_array_subarray_function(self):
        token = self.parser.parse('array:subarray(["a", "b", "c", "d"], 2)')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), ['b', 'c', 'd'])

        token = self.parser.parse('array:subarray(["a", "b", "c", "d"], 5)')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), [])

        token = self.parser.parse('array:subarray(["a", "b", "c", "d"], 2, 0)')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), [])

        token = self.parser.parse('array:subarray(["a", "b", "c", "d"], 2, 1)')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), ['b'])

        token = self.parser.parse('array:subarray(["a", "b", "c", "d"], 2, 2)')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), ['b', 'c'])

        expression = 'array:subarray(["a", "b", "c", "d"], 5, 0)'
        token = self.parser.parse(expression)
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), [])
        self.check_source(expression, expression.replace('"', "'"))

        expression = 'array:subarray([ ], 1, 0)'
        token = self.parser.parse(expression)
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), [])
        self.check_source(expression, expression.replace('[ ]', '[]'))

    def test_array_head_function(self):
        self.check_value('array:head([5, 6, 7, 8])', 5)
        self.check_value('array:head([("a", "b"), ("c", "d")])', ['a', 'b'])

        expression = 'array:head([["a", "b"], ["c", "d"]])'
        token = self.parser.parse(expression)
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), ['a', 'b'])
        self.check_source(expression, expression.replace('"', "'"))

    def test_array_tail_function(self):
        expression = 'array:tail([5, 6, 7, 8])'
        token = self.parser.parse(expression)
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), [6, 7, 8])
        self.check_source(expression, expression)

        token = self.parser.parse('array:tail([5])')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), [])

    def test_array_reverse_function(self):
        token = self.parser.parse('array:reverse(["a", "b", "c", "d"])')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), ["d", "c", "b", "a"])

        expression = 'array:reverse([("a", "b"), ("c", "d")])'
        token = self.parser.parse(expression)
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), [["c", "d"], ["a", "b"]])
        self.check_source(expression, expression.replace('"', "'"))

        expression = 'array:reverse([(1 to 5)])'
        token = self.parser.parse(expression)
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), [[1, 2, 3, 4, 5]])
        self.check_source(expression, expression)

        token = self.parser.parse('array:reverse([])')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), [])

    def test_array_remove_function(self):
        token = self.parser.parse('array:remove(["a", "b", "c", "d"], 1)')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), ["b", "c", "d"])

        token = self.parser.parse('array:remove(["a", "b", "c", "d"], 2)')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), ["a", "c", "d"])

        token = self.parser.parse('array:remove(["a"], 1)')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), [])

        expression = 'array:remove(["a", "b", "c", "d"], 1 to 3)'
        token = self.parser.parse(expression)
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), ["d"])
        self.check_source(expression, expression.replace('"', "'"))

        token = self.parser.parse('array:remove(["a", "b", "c", "d"], ())')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), ["a", "b", "c", "d"])

        self.wrong_value('array:remove(["a", "b", "c", "d"], 0)', 'FOAY0001')

    def test_array_join_function(self):
        token = self.parser.parse('array:join(())')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), [])

        token = self.parser.parse('array:join([1, 2, 3])')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), [1, 2, 3])

        token = self.parser.parse(' array:join((["a", "b"], ["c", "d"]))')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), ["a", "b", "c", "d"])

        token = self.parser.parse('array:join((["a", "b"], ["c", "d"], [ ]))')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), ["a", "b", "c", "d"])

        expression = 'array:join((["a", "b"], ["c", "d"], [["e", "f"]]))'
        token = self.parser.parse(expression)
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(
            result.items(), ["a", "b", "c", "d", XPathArray(self.parser, ['e', 'f'])]
        )
        self.check_source(expression, expression.replace('"', "'"))

    def test_array_flatten_function(self):
        token = self.parser.parse('array:flatten([1, 4, 6, 5, 3])')
        result = token.evaluate()
        self.assertListEqual(result, [1, 4, 6, 5, 3])

        expression = 'array:flatten(([1, 2, 5], [[10, 11], 12], [], 13))'
        token = self.parser.parse(expression)
        result = token.evaluate()
        self.assertListEqual(result, [1, 2, 5, 10, 11, 12, 13])
        self.check_source(expression, expression)

        expression = 'array:flatten([(1, 0), (1, 1), (0, 1), (0, 0)])'
        token = self.parser.parse(expression)
        result = token.evaluate()
        self.assertListEqual(result, [1, 0, 1, 1, 0, 1, 0, 0])
        self.check_source(expression, expression)

    def test_array_for_each_function(self):
        context = XPathContext(self.etree.XML('<empty/>'))

        expression = 'array:for-each(["A", "B", 1, 2], function($z) {$z instance of xs:integer})'
        token = self.parser.parse(expression)
        result = token.evaluate(context)
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), [False, False, True, True])

        expression = 'array:for-each(["the cat", "sat", "on the mat"], fn:tokenize#1)'
        token = self.parser.parse(expression)
        result = token.evaluate(context)
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), [["the", "cat"], "sat", ["on", "the", "mat"]])
        self.check_source(expression, expression.replace('"', "'"))

    def test_array_for_each_pair_function(self):
        context = XPathContext(self.etree.XML('<empty/>'))

        expression = 'array:for-each-pair(["A", "B", "C"], [1, 2, 3], ' \
                     'function($x, $y) { array {$x, $y}})'
        token = self.parser.parse(expression)
        result = token.evaluate(context)
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), [
            XPathArray(self.parser, ['A', 1]),
            XPathArray(self.parser, ['B', 2]),
            XPathArray(self.parser, ['C', 3])
        ])
        expected = expression.replace('"', "'").replace('{ array ', '{array')
        self.check_source(expression, expected)

        expression = 'let $A := ["A", "B", "C", "D"] ' \
                     'return array:for-each-pair($A, array:tail($A), concat#2)'
        token = self.parser.parse(expression)
        result = token.evaluate(context)
        self.assertListEqual(result, [XPathArray(self.parser, ['AB', 'BC', 'CD'])])
        self.check_source(expression, expression.replace('"', "'"))

    def test_array_filter_function(self):
        context = XPathContext(self.etree.XML('<empty/>'))

        expression = 'array:filter(["A", "B", 1, 2], function($x) {$x instance of xs:integer})'
        token = self.parser.parse(expression)
        result = token.evaluate(context)
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), [1, 2])

        expression = 'array:filter(["the cat", "sat", "on the mat"], ' \
                     'function($s) {fn:count(fn:tokenize($s)) gt 1})'
        token = self.parser.parse(expression)
        result = token.evaluate(context)
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), ["the cat", "on the mat"])
        self.check_source(expression, expression.replace('"', "'"))

        expression = 'array:filter(["A", "B", "", 0, 1], boolean#1)'
        token = self.parser.parse(expression)
        result = token.evaluate(context)
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result.items(), ["A", "B", 1])
        self.check_source(expression, expression.replace('"', "'"))

    def test_array_fold_left_function(self):
        context = XPathContext(self.etree.XML('<empty/>'))

        expression = 'array:fold-left([true(), true(), false()], true(), ' \
                     'function($x, $y){$x and $y})'
        self.check_value(expression, [False], context=context)

        expression = 'array:fold-left([true(), true(), false()], false(), ' \
                     'function($x, $y){$x or $y})'
        self.check_value(expression, [True], context=context)

        expression = 'array:fold-left([1, 2, 3], [], function($x, $y){[$x, $y]})'
        ar1 = XPathArray(self.parser, [])
        ar2 = XPathArray(self.parser, items=[ar1, 1])
        ar3 = XPathArray(self.parser, items=[ar2, 2])
        ar4 = XPathArray(self.parser, items=[ar3, 3])
        self.check_value(expression, [ar4], context=context)
        self.check_source(expression, expression.replace('){', ') {'))

    def test_array_fold_right_function(self):
        context = XPathContext(self.etree.XML('<empty/>'))

        expression = 'array:fold-right([true(), true(), false()], true(), ' \
                     'function($x, $y){$x and $y})'
        self.check_value(expression, [False], context=context)

        expression = 'array:fold-right([true(), true(), false()], false(), ' \
                     'function($x, $y){$x or $y})'
        self.check_value(expression, [True], context=context)

        expression = 'array:fold-right([1,2,3], [], function($x, $y){[$x, $y]})'
        ar1 = XPathArray(self.parser, [])
        ar2 = XPathArray(self.parser, items=[3, ar1])
        ar3 = XPathArray(self.parser, items=[2, ar2])
        ar4 = XPathArray(self.parser, items=[1, ar3])
        self.check_value(expression, [ar4], context=context)
        self.check_source(expression, expression.replace('){', ') {').replace('2,', ' 2, '))

    def test_array_sort_function(self):
        expression = 'array:sort([1, 4, 6, 5, 3])'
        self.check_value(expression, XPathArray(self.parser, [1, 3, 4, 5, 6]))

        expression = 'array:sort([1, -2, 5, 10, -10, 10, 8], (), fn:abs#1)'
        self.check_value(expression, XPathArray(self.parser, [1, -2, 5, 8, 10, -10, 10]))
        self.check_source(expression, expression)

        expression = 'array:sort([(1,0), (1,1), (0,1), (0,0)])'
        self.check_value(expression, XPathArray(self.parser, [[0, 0], [0, 1], [1, 0], [1, 1]]))

    def test_sort_function(self):
        expression = 'fn:sort((1, 4, 6, 5, 3))'
        self.check_value(expression, [1, 3, 4, 5, 6])

        expression = 'fn:sort((1, -2, 5, 10, -10, 10, 8), (), fn:abs#1)'
        self.check_value(expression, [1, -2, 5, 8, 10, -10, 10])
        self.check_source(expression, expression)

    def test_parse_json_function(self):
        expression = 'parse-json(\'{"x":1, "y":[3,4,5]}\')'
        result = XPathMap(self.parser, {'x': 1, 'y': XPathArray(self.parser, [3, 4, 5])})
        self.check_value(expression, result)

        expression = 'parse-json(\'"abcd"\')'
        self.check_value(expression, 'abcd')

        expression = 'parse-json(\'{"x":"\\\\", "y":"\\u0025"}\')'
        result = XPathMap(self.parser, {"x": "\\", "y": "%"})
        self.check_value(expression, result)
        self.check_source(expression, expression)

        expression = 'parse-json(\'{"x":"\\\\", "y":"\\u0025"}\', map{\'escape\':true()})'
        result = XPathMap(self.parser, {"x": "\\\\", "y": "%"})
        self.check_value(expression, result)

        expression = 'parse-json(\'{"x":"\\\\", "y":"\\u0000"}\', ' \
                     'map{\'fallback\':function($s){\'[\'||$s||\']\'}})'
        result = XPathMap(self.parser, {"x": "\\", "y": "[\\u0000]"})

        # fallback inline function requires a context for evaluation
        context = XPathContext(root=self.etree.XML('<empty/>'))
        self.check_value(expression, result, context=context)

    def test_load_xquery_module_function(self):
        self.wrong_value('load-xquery-module("")', 'FOQM0001')

        with self.assertRaises(RuntimeError) as ctx:
            self.check_value('load-xquery-module("./xquery-module")')

        self.assertIn('FOQM0006', str(ctx.exception))

    def test_transform_function(self):
        with self.assertRaises(RuntimeError) as ctx:
            self.check_value('transform(map{})')

        self.assertIn('FOXT0004', str(ctx.exception))

    def test_random_number_generator_function(self):
        context = None

        expression = 'random-number-generator()'
        token = self.parser.parse(expression)
        self.assertEqual(token.source, expression)
        result = token.evaluate()
        self.assertIsInstance(result, XPathMap)

        self.assertListEqual(list(result.keys()), ['number', 'next', 'permute'])
        self.assertTrue(0 <= result('number', context=context) <= 1)

        seq = result('permute', context=context)(range(10))
        _seq = tuple(seq)
        self.assertNotEqual(seq, list(range(10)))
        self.assertNotEqual(seq, result('permute', context=context)(seq))
        self.assertNotEqual(seq, result('permute', context=context)(range(10)))
        self.assertListEqual(seq, list(_seq))

        expression = 'random-number-generator(1000)'
        token = self.parser.parse(expression)
        self.assertEqual(token.source, expression)
        result = token.evaluate()
        self.assertNotEqual(seq, result('permute', context=context)(seq))

    def test_apply_function(self):
        expression = 'fn:apply(fn:concat#3, ["a", "b", "c"])'
        self.check_value(expression, 'abc')
        self.check_source(expression, expression.replace('"', "'"))

        expression = 'fn:apply(fn:concat#3, ["a", "b", "c", "d"])'
        self.wrong_type(expression, 'FOAP0001')

        expression = 'fn:apply(fn:concat#4, array:subarray(["a", "b", "c", "d", "e", "f"], ' \
                     '1, fn:function-arity(fn:concat#4)))'
        self.check_value(expression, 'abcd')
        self.check_source(expression, expression.replace('"', "'"))

    def test_parse_ietf_date_function(self):
        expression = 'fn:parse-ietf-date("Wed, 06 Jun 1994 07:29:35 GMT")'
        result = DateTime.fromstring('1994-06-06T07:29:35Z')
        self.check_value(expression, result)
        self.check_source(expression, expression.replace('"', "'"))

        expression = 'fn:parse-ietf-date("Wed, 6 Jun 94 07:29:35 GMT")'
        result = DateTime.fromstring('1994-06-06T07:29:35Z')
        self.check_value(expression, result)
        self.check_source(expression, expression.replace('"', "'"))

        expression = 'fn:parse-ietf-date("Wed Jun 06 11:54:45 EST 2013")'
        result = DateTime.fromstring('2013-06-06T11:54:45-05:00')
        self.check_value(expression, result)
        self.check_source(expression, expression.replace('"', "'"))

        expression = 'fn:parse-ietf-date("Sunday, 06-Nov-94 08:49:37 GMT")'
        result = DateTime.fromstring('1994-11-06T08:49:37Z')
        self.check_value(expression, result)
        self.check_source(expression, expression.replace('"', "'"))

        expression = 'fn:parse-ietf-date("Wed, 6 Jun 94 07:29:35 +0500")'
        result = DateTime.fromstring('1994-06-06T07:29:35+05:00')
        self.check_value(expression, result)
        self.check_source(expression, expression.replace('"', "'"))

    def test_contains_token_function(self):
        expression = 'fn:contains-token("red green blue ", "red")'
        self.check_value(expression, True)

        expression = 'fn:contains-token(("red", "green", "blue"), " red ")'
        self.check_value(expression, True)
        self.check_source(expression, expression.replace('"', "'"))

        expression = 'fn:contains-token("red, green, blue", "red")'
        self.check_value(expression, False)

        expression = \
            'fn:contains-token("red green blue", "RED", ' \
            '"http://www.w3.org/2005/xpath-functions/collation/html-ascii-case-insensitive")'
        self.check_value(expression, True)
        self.check_source(expression, expression.replace('"', "'"))

    def test_collation_key_function(self):
        expression = 'fn:collation-key("foo")'
        self.check_value(expression, Base64Binary(b'Zm9v'))
        self.check_source(expression, expression.replace('"', "'"))

    def test_lookup_unary_operator(self):
        context = XPathContext(self.etree.XML('<empty/>'))

        expression = '([1, 2, 3], [1, 2, 5], [1, 2, 6])[?3 = 5]'
        result = [XPathArray(self.parser, [1, 2, 5])]
        self.check_value(expression, result, context=context)
        self.check_source(expression, expression)

    def test_lookup_postfix_operator(self):
        expression = '[1, 2, 5, 7]?*'
        self.check_value(expression, [1, 2, 5, 7])
        self.check_source(expression, expression)

        expression = '[[1, 2, 3], [4, 5, 6]]?*'
        result = [
            XPathArray(self.parser, [1, 2, 3]),
            XPathArray(self.parser, [4, 5, 6])
        ]
        self.check_value(expression, result)
        self.check_source(expression, expression)

        expression = 'map { "first" : "Jenna", "last" : "Scott" }?first'
        self.check_value(expression, ['Jenna'])

        self.check_value('[4, 5, 6]?2', [5])

        expression = '(map {"first": "Tom"}, map {"first": "Dick"}, ' \
                     'map {"first": "Harry"})?first'
        self.check_value(expression, ['Tom', 'Dick', 'Harry'])
        expected = expression.\
            replace('"', "'").\
            replace('map ', 'map').\
            replace(': ', ':')
        self.check_source(expression, expected)

        expression = '([1,2,3], [4,5,6])?2'
        self.check_value(expression, [2, 5])
        self.check_source(expression, '([1, 2, 3], [4, 5, 6])?2')

        self.wrong_value('["a","b"]?3', 'FOAY0001')

    def test_lookup_operator_tree(self):
        self.check_tree('$a?2?1', '(? (? ($ (a)) (2)) (1))')
        self.check_tree('$a?2 and $a?3', '(and (? ($ (a)) (2)) (? ($ (a)) (3)))')

        self.check_tree('$a?2?1 and $a?3?4',
                        '(and (? (? ($ (a)) (2)) (1)) (? (? ($ (a)) (3)) (4)))')
        self.check_tree('$a[1] eq 1 and $a[2] eq 2',
                        '(and (eq ([ ($ (a)) (1)) (1)) (eq ([ ($ (a)) (2)) (2)))')
        self.check_tree(
            '$a[1]?2 eq 1 and $a[2]?2 eq 2',
            '(and (eq (? ([ ($ (a)) (1)) (2)) (1)) (eq (? ([ ($ (a)) (2)) (2)) (2)))'
        )

    def test_arrow_operator(self):
        expression = '"foo" => $f("bar")'
        self.check_tree(expression, "(=> ('foo') ($ (f)) ('bar'))")
        self.check_source(expression, expression.replace('"', "'"))

        expression = '"foo" => $f()'
        self.check_tree(expression, "(=> ('foo') ($ (f)) ())")

        expression = '"foo" => upper-case()'
        # self.check_tree(expression, "(=> ('foo') (upper-case) ())")
        self.check_value(expression, 'FOO')
        self.check_source(expression, expression.replace('"', "'"))

    def test_xml_to_json_function(self):
        root = self.etree.XML('<array xmlns="http://www.w3.org/2005/xpath-functions">'
                              '<number>1</number><string>is</string><boolean>1</boolean>'
                              '</array>')

        expression = 'fn:xml-to-json(.)'
        context = XPathContext(root)
        result = '[1,"is",true]'
        self.check_value(expression, result, context=context)
        self.check_source(expression, expression)

        root = self.etree.XML('<map xmlns="http://www.w3.org/2005/xpath-functions">'
                              '<number key="Sunday">1</number><number key="Monday">2</number>'
                              '</map>')

        context = XPathContext(root)
        result = '{"Sunday":1,"Monday":2}'
        self.check_value(expression, result, context=context)

    def test_json_to_xml_function(self):
        context = XPathContext(root=self.etree.XML('<empty/>'))
        root = self.etree.XML(dedent("""\
            <map xmlns="http://www.w3.org/2005/xpath-functions">
              <number key="x">1</number>
              <array key="y">
                <number>3</number>
                <number>4</number>
                <number>5</number>
              </array>
            </map>"""))

        expression = 'json-to-xml(\'{"x": 1, "y": [3,4,5]}\')'
        token = self.parser.parse(expression)
        self.check_source(expression, expression)

        result = token.evaluate(context)
        self.assertIsInstance(result, DocumentNode)
        self.assertTrue(etree_deep_equal(result.value.getroot(), root))

        root = self.etree.XML(dedent("""\
             <string xmlns="http://www.w3.org/2005/xpath-functions">abcd</string>"""))

        token = self.parser.parse('json-to-xml(\'"abcd"\', map{\'liberal\': false()})')
        result = token.evaluate(context)
        self.assertIsInstance(result, DocumentNode)
        self.assertTrue(etree_deep_equal(result.value.getroot(), root))

        root = self.etree.XML(dedent("""\
            <map xmlns="http://www.w3.org/2005/xpath-functions">
              <string key="x">\\</string>
              <string key="y">%</string>
            </map>"""))

        expression = 'json-to-xml(\'{"x": "\\\\", "y": "\\u0025"}\')'
        token = self.parser.parse(expression)
        self.check_source(expression, expression)

        result = token.evaluate(context)
        self.assertIsInstance(result, DocumentNode)
        self.assertTrue(etree_deep_equal(result.value.getroot(), root))

        root = self.etree.XML(dedent("""\
            <map xmlns="http://www.w3.org/2005/xpath-functions">
              <string escaped="true" key="x">\\\\</string>
              <string key="y">%</string>
            </map>"""))

        expression = 'json-to-xml(\'{"x": "\\\\", "y": "\\u0025"}\', ' \
                     'map{\'escape\':true()})'
        token = self.parser.parse(expression)
        self.check_source(expression, expression)

        result = token.evaluate(context)
        self.assertIsInstance(result, DocumentNode)
        self.assertTrue(etree_deep_equal(result.value.getroot(), root))


@unittest.skipIf(lxml_etree is None, "The lxml library is not installed")
class LxmlXPath31ParserTest(XPath31ParserTest):
    etree = lxml_etree

    def test_regression_ep415_ep420__issue_71(self):
        import lxml.html as lxml_html

        xml_source = dedent("""\
        <hotel>
          <branch location="California">
            <staff>
              <date>2023-10-10</date>
              <given_name>Christopher</given_name>
              <surname>Anderson</surname>
              <age>25</age>
            </staff>
            <staff>
              <date>2023-10-11</date>
              <given_name>Christopher</given_name>
              <surname>Carter</surname>
              <age>30</age>
            </staff>
          </branch>
          <branch location="Las Vegas">
            <staff>
              <given_name>Lisa</given_name>
              <surname>Walker</surname>
              <age>60</age>
            </staff>
            <staff>
              <given_name>Jessica</given_name>
              <surname>Walker</surname>
              <age>32</age>
            </staff>
            <staff>
              <given_name>Jennifer</given_name>
              <surname>Roberts</surname>
              <age>50</age>
            </staff>
          </branch>
        </hotel>
        """)

        queries = [
            'if (count(//hotel/branch/staff) = 5) then true() else false()',
            '//hotel/branch/staff',
            'if (count(/hotel/branch/staff) = 5) then true() else false()',
            '(count(/hotel/branch/staff) = 5)',
            '(count(/hotel/branch/staff))',
            '/hotel/branch/staff',
            'for $i in /hotel/branch/staff return $i/given_name',
            'for $i in //hotel/branch/staff return $i/given_name',
            'distinct-values(for $i in /hotel/branch/staff return $i/given_name)',
            'distinct-values(for $i in //hotel/branch/staff return $i/given_name)',
            'date(/hotel/branch[1]/staff[1]/date) instance of xs:date',
            '/hotel/branch[1]/staff[1]/date cast as xs:date',
        ]

        html_parser = lxml_html.HTMLParser()
        xml_parser = lxml_etree.XMLParser(strip_cdata=False)

        xml_data = bytes(xml_source, encoding='utf-8')
        data_trees = {
            'html': lxml_html.fromstring(xml_data, parser=html_parser),
            'xml': lxml_etree.fromstring(xml_data, parser=xml_parser)
        }

        for query in queries:
            results = []
            for doctype, document in data_trees.items():
                try:
                    res = select(document, query, parser=XPath31Parser)
                except Exception as e:
                    results.append(e)
                else:
                    results.append(res)

            if isinstance(results[0], list):
                self.assertIsInstance(results[1], list)
                self.assertEqual(len(results[0]), len(results[1]))
                for e1, e2 in zip(*results):
                    self.assertEqual(getattr(e1, 'tag', e1), getattr(e2, 'tag', e2))
            else:
                self.assertEqual(results[0], results[1])


class XPath31FunctionsTest(test_xpath30.XPath30FunctionsTest):

    maxDiff = 1024

    def setUp(self):
        self.parser = XPath31Parser(namespaces=self.namespaces)

        # Make sure the tests are repeatable.
        env_vars_to_tweak = 'LC_ALL', 'LANG'
        self.current_env_vars = {v: os.environ.get(v) for v in env_vars_to_tweak}
        for v in self.current_env_vars:
            os.environ[v] = 'en_US.UTF-8'

    def tearDown(self):
        if hasattr(self, 'current_env_vars'):
            for v in self.current_env_vars:
                if self.current_env_vars[v] is not None:
                    os.environ[v] = self.current_env_vars[v]


@unittest.skipIf(lxml_etree is None, "The lxml library is not installed")
class LxmlXPath31FunctionsTest(XPath31FunctionsTest):
    etree = lxml_etree


class XPath31ConstructorsTest(test_xpath30.XPath30ConstructorsTest):
    def setUp(self):
        self.parser = XPath31Parser(namespaces=self.namespaces)


@unittest.skipIf(lxml_etree is None, "The lxml library is not installed")
class LxmlXPath31ConstructorsTest(XPath31ConstructorsTest):
    etree = lxml_etree


if __name__ == '__main__':
    unittest.main()
