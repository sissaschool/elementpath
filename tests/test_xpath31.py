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

NESTED_MAP = """\
map {
    "book": map {
        "title": "Data on the Web",
        "year": 2000,
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

        self.assertDictEqual(token.evaluate().value, map_value)

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
