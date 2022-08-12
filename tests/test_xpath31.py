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

from elementpath import XPathContext
from elementpath.xpath3 import XPath31Parser
from elementpath.xpath_token import XPathMap, XPathArray

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

        self.assertDictEqual(token.evaluate()._map, map_value)

        token = self.parser.parse(f"{MAP_WEEKDAYS}('Mo')")
        self.assertEqual(token.evaluate(), 'Monday')

        token = self.parser.parse(f"{MAP_WEEKDAYS}('Mon')")
        self.assertIsNone(token.evaluate())

        token = self.parser.parse(f"let $x := {MAP_WEEKDAYS} return $x('Mo')")
        context = XPathContext(self.etree.XML('<empty/>'))
        self.assertEqual(token.evaluate(context), ['Monday'])

    def test_nested_map(self):
        token = self.parser.parse(MAP_WEEKDAYS)
        self.assertIsInstance(token, XPathMap)

        token = self.parser.parse(f'{NESTED_MAP}("book")("title")')
        self.assertEqual(token.evaluate(), 'Data on the Web')

        token = self.parser.parse(f'{NESTED_MAP}("book")("author")')
        self.assertIsInstance(token.evaluate(), XPathArray)

        token = self.parser.parse(f'{NESTED_MAP}("book")("author")(1)("last")')
        self.assertEqual(token.evaluate(), 'Abiteboul')

    def test_curly_array_constructor(self):
        token = self.parser.parse('array { 1, 2, 5, 7 }')
        self.assertIsInstance(token, XPathArray)

    def test_square_array_constructor(self):
        token = self.parser.parse('[ 1, 2, 5, 7 ]')
        self.assertIsInstance(token, XPathArray)

    def test_array_lookup(self):
        token = self.parser.parse('array { 1, 2, 5, 7 }(4)')
        self.assertEqual(token.evaluate(), 7)

        token = self.parser.parse('[ 1, 2, 5, 7 ](4)')
        self.assertEqual(token.evaluate(), 7)

    def test_map_size_function(self):
        self.check_value('map:size(map{})', 0)
        self.check_value('map:size(map{"true":1, "false":0})', 2)

    def test_map_keys_function(self):
        self.check_value('map:keys(map{})', [])
        self.check_value('map:keys(map{1:"yes", 2:"no"})', [1, 2])

    def test_map_contains_function(self):
        self.check_value('map:contains(map{}, 1)', False)
        self.check_value('map:contains(map{}, "xyz")', False)
        self.check_value('map:contains(map{1:"yes", 2:"no"}, 1)', True)
        self.check_value('map:contains(map{"xyz":23}, "xyz")', True)
        self.check_value('map:contains(map{"abc":23, "xyz":()}, "xyz")', True)

        context = XPathContext(self.etree.XML('<empty/>'))

        expression = f"let $x := {MAP_WEEKDAYS_DE} return map:contains($x, 2)"
        self.check_value(expression, [True], context=context)

        expression = f"let $x := {MAP_WEEKDAYS_DE} return map:contains($x, 9)"
        self.check_value(expression, [False], context=context)

    def test_map_get_function(self):
        context = XPathContext(self.etree.XML('<empty/>'))

        expression = f"let $x := {MAP_WEEKDAYS} return map:get($x, 'Mo')"
        self.check_value(expression, ['Monday'], context=context)

        expression = f"let $x := {MAP_WEEKDAYS} return map:get($x, 'Mon')"
        self.check_value(expression, [], context=context)

    def test_array_size_function(self):
        self.check_value('array:size(["a", "b", "c"])', 3)
        self.check_value('array:size(["a", ["b", "c"]])', 2)
        self.check_value('array:size([ ])', 0)
        self.check_value('array:size([[ ]])', 1)

    def test_array_get_function(self):
        self.check_value('array:get(["a", "b", "c"], 2)', 'b')

        token = self.parser.parse('array:get(["a", ["b", "c"]], 2)')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result._array, ['b', 'c'])

    def test_array_put_function(self):
        token = self.parser.parse(' array:put(["a", "b", "c"], 2, "d")')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result._array, ['a', 'd', 'c'])

        token = self.parser.parse('array:put(["a", "b", "c"], 2, ("d", "e"))')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertListEqual(result._array, ['a', ['d', 'e'], 'c'])

        token = self.parser.parse('array:put(["a"], 1, ["d", "e"])')
        result = token.evaluate()
        self.assertIsInstance(result, XPathArray)
        self.assertIsInstance(result._array[0], XPathArray)
        self.assertListEqual(result._array[0]._array, ['d', 'e'])


@unittest.skipIf(lxml_etree is None, "The lxml library is not installed")
class LxmlXPath31ParserTest(XPath31ParserTest):
    etree = lxml_etree


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
