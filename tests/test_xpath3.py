#!/usr/bin/env python
#
# Copyright (c), 2018-2020, SISSA (International School for Advanced Studies).
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
import math

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

from elementpath import *
from elementpath.xpath3 import XPath30Parser, XPath31Parser

try:
    from tests import test_xpath2_parser
except ImportError:
    import test_xpath2_parser


class XPath3ParserTest(test_xpath2_parser.XPath2ParserTest):

    def setUp(self):
        self.parser = XPath30Parser(namespaces=self.namespaces)

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

    def test_pi_math_function(self):
        token = self.parser.parse('math:pi()')
        self.assertEqual(token.evaluate(), math.pi)

    def test_exp_math_function(self):
        token = self.parser.parse('math:exp(())')
        self.assertIsNone(token.evaluate())
        self.assertEqual(self.parser.parse('math:exp(0)').evaluate(), 1.0)
        self.assertEqual(self.parser.parse('math:exp(1)').evaluate(), 2.718281828459045)
        self.assertEqual(self.parser.parse('math:exp(2)').evaluate(), 7.38905609893065)
        self.assertEqual(self.parser.parse('math:exp(-1)').evaluate(), 0.36787944117144233)
        self.assertEqual(self.parser.parse('math:exp(math:pi())').evaluate(), 23.140692632779267)
        self.assertTrue(math.isnan(self.parser.parse('math:exp(xs:double("NaN"))').evaluate()))
        self.assertEqual(self.parser.parse("math:exp(xs:double('INF'))").evaluate(), float('inf'))
        self.assertEqual(self.parser.parse("math:exp(xs:double('-INF'))").evaluate(), 0.0)

    def test_exp10_math_function(self):
        token = self.parser.parse('math:exp10(())')
        self.assertIsNone(token.evaluate())
        self.assertEqual(self.parser.parse('math:exp10(0)').evaluate(), 1.0)
        self.assertEqual(self.parser.parse('math:exp10(1)').evaluate(), 10)
        self.assertEqual(self.parser.parse('math:exp10(0.5)').evaluate(), 3.1622776601683795)
        self.assertEqual(self.parser.parse('math:exp10(-1)').evaluate(), 0.1)
        self.assertTrue(math.isnan(self.parser.parse('math:exp10(xs:double("NaN"))').evaluate()))
        self.assertEqual(self.parser.parse("math:exp10(xs:double('INF'))").evaluate(), float('inf'))
        self.assertEqual(self.parser.parse("math:exp10(xs:double('-INF'))").evaluate(), 0.0)

    def test_log_math_function(self):
        token = self.parser.parse('math:log(())')
        self.assertIsNone(token.evaluate())
        self.assertEqual(self.parser.parse('math:log(0)').evaluate(), float('-inf'))
        self.assertEqual(self.parser.parse('math:log(math:exp(1))').evaluate(), 1.0)
        self.assertEqual(self.parser.parse('math:log(1.0e-3)').evaluate(), -6.907755278982137)
        self.assertEqual(self.parser.parse('math:log(2)').evaluate(), 0.6931471805599453)
        self.assertTrue(math.isnan(self.parser.parse('math:log(-1)').evaluate()))
        self.assertTrue(math.isnan(self.parser.parse('math:log(xs:double("NaN"))').evaluate()))
        self.assertEqual(self.parser.parse("math:log(xs:double('INF'))").evaluate(), float('inf'))
        self.assertTrue(math.isnan(self.parser.parse('math:log(xs:double("-INF"))').evaluate()))

    def test_log10_math_function(self):
        token = self.parser.parse('math:log10(())')
        self.assertIsNone(token.evaluate())
        self.assertEqual(self.parser.parse('math:log10(0)').evaluate(), float('-inf'))
        self.assertEqual(self.parser.parse('math:log10(1.0e3)').evaluate(), 3.0)
        self.assertEqual(self.parser.parse('math:log10(1.0e-3)').evaluate(), -3.0)
        self.assertEqual(self.parser.parse('math:log10(2)').evaluate(), 0.3010299956639812)
        self.assertTrue(math.isnan(self.parser.parse('math:log10(-1)').evaluate()))
        self.assertTrue(math.isnan(self.parser.parse('math:log10(xs:double("NaN"))').evaluate()))
        self.assertEqual(self.parser.parse("math:log10(xs:double('INF'))").evaluate(), float('inf'))
        self.assertTrue(math.isnan(self.parser.parse('math:log10(xs:double("-INF"))').evaluate()))


@unittest.skipIf(lxml_etree is None, "The lxml library is not installed")
class LxmlXPath3ParserTest(XPath3ParserTest):
    etree = lxml_etree


class XPath31ParserTest(XPath3ParserTest):

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
class LxmlXPath31ParserTest(XPath31ParserTest):
    etree = lxml_etree


if __name__ == '__main__':
    unittest.main()
