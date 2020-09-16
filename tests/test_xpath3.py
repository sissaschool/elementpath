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

    def test_pow_math_function(self):
        self.assertIsNone(self.parser.parse('math:pow((), 93.7)').evaluate())
        self.assertEqual(self.parser.parse('math:pow(2, 3)').evaluate(), 8.0)
        self.assertEqual(self.parser.parse('math:pow(-2, 3)').evaluate(), -8.0)
        self.assertEqual(self.parser.parse('math:pow(2, -3)').evaluate(), 0.125)
        self.assertEqual(self.parser.parse('math:pow(-2, -3)').evaluate(), -0.125)
        self.assertEqual(self.parser.parse('math:pow(2, 0)').evaluate(), 1.0)
        self.assertEqual(self.parser.parse('math:pow(0, 0)').evaluate(), 1.0)
        self.assertEqual(self.parser.parse("math:pow(xs:double('INF'), 0)").evaluate(), 1.0)
        self.assertEqual(self.parser.parse("math:pow(xs:double('NaN'), 0)").evaluate(), 1.0)
        self.assertEqual(self.parser.parse("math:pow(-math:pi(), 0)").evaluate(), 1.0)
        self.assertEqual(self.parser.parse('math:pow(0e0, 3)').evaluate(), 0.0)
        self.assertEqual(self.parser.parse('math:pow(0e0, 4)').evaluate(), 0.0)
        self.assertEqual(self.parser.parse('math:pow(-0e0, 3)').evaluate(), 0.0)
        self.assertEqual(self.parser.parse('math:pow(0, 3)').evaluate(), 0.0)
        self.assertEqual(self.parser.parse('math:pow(0e0, -3)').evaluate(), float('inf'))
        self.assertEqual(self.parser.parse('math:pow(0e0, -4)').evaluate(), float('inf'))
        # self.assertEqual(self.parser.parse('math:pow(-0e0, -3)').evaluate(), float('-inf'))
        self.assertEqual(self.parser.parse('math:pow(0, -4)').evaluate(), float('inf'))
        self.assertEqual(self.parser.parse('math:pow(16, 0.5e0)').evaluate(), 4.0)
        self.assertEqual(self.parser.parse('math:pow(16, 0.25e0)').evaluate(), 2.0)
        self.assertEqual(self.parser.parse('math:pow(0e0, -3.0e0)').evaluate(), float('inf'))
        # self.assertEqual(self.parser.parse('math:pow(-0e0, -3.0e0)').evaluate(), float('-inf'))
        self.assertEqual(self.parser.parse('math:pow(0e0, -3.1e0)').evaluate(), float('inf'))
        self.assertEqual(self.parser.parse('math:pow(-0e0, -3.1e0)').evaluate(), float('inf'))
        self.assertEqual(self.parser.parse('math:pow(0e0, 3.0e0)').evaluate(), 0.0)
        self.assertEqual(self.parser.parse('math:pow(-0e0, 3.0e0)').evaluate(), -0.0)
        self.assertEqual(self.parser.parse('math:pow(0e0, 3.1e0)').evaluate(), 0.0)
        self.assertEqual(self.parser.parse('math:pow(-0e0, 3.1e0)').evaluate(), -0.0)

        self.assertEqual(self.parser.parse("math:pow(-1, xs:double('INF'))").evaluate(), 1.0)
        self.assertEqual(self.parser.parse("math:pow(-1, xs:double('-INF'))").evaluate(), 1.0)
        self.assertEqual(self.parser.parse("math:pow(1, xs:double('INF'))").evaluate(), 1.0)
        self.assertEqual(self.parser.parse("math:pow(1, xs:double('-INF'))").evaluate(), 1.0)

        self.assertEqual(self.parser.parse("math:pow(1, xs:double('NaN'))").evaluate(), 1.0)
        self.assertEqual(self.parser.parse('math:pow(-2.5e0, 2.0e0)').evaluate(), 6.25)
        self.assertTrue(math.isnan(self.parser.parse('math:pow(-2.5e0, 2.00000001e0)').evaluate()))

    def test_sqrt_math_function(self):
        self.assertIsNone(self.parser.parse('math:sqrt(())').evaluate())
        self.assertEqual(self.parser.parse('math:sqrt(0.0e0)').evaluate(), 0.0)
        self.assertEqual(self.parser.parse('math:sqrt(-0.0e0)').evaluate(), -0.0)
        self.assertEqual(self.parser.parse('math:sqrt(1.0e6)').evaluate(), 1.0e3)
        self.assertEqual(self.parser.parse('math:sqrt(2.0e0)').evaluate(), 1.4142135623730951)
        self.assertTrue(math.isnan(self.parser.parse('math:sqrt(-2.0e0)').evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:sqrt(xs:double('NaN'))").evaluate()))
        self.assertEqual(self.parser.parse("math:sqrt(xs:double('INF'))").evaluate(), float('inf'))
        self.assertTrue(math.isnan(self.parser.parse("math:sqrt(xs:double('-INF'))").evaluate()))

    def test_sin_math_function(self):
        self.assertIsNone(self.parser.parse('math:sin(())').evaluate())
        self.assertEqual(self.parser.parse('math:sin(0)').evaluate(), 0.0)
        self.assertEqual(self.parser.parse('math:sin(-0.0e0)').evaluate(), -0.0)
        self.assertEqual(self.parser.parse('math:sin(math:pi() div 2)').evaluate(), 1.0)
        self.assertEqual(self.parser.parse('math:sin(-math:pi() div 2)').evaluate(), -1.0)
        self.assertTrue(
            math.isclose(self.parser.parse('math:sin(math:pi())').evaluate(), 0.0, abs_tol=1e-14)
        )
        self.assertTrue(math.isnan(self.parser.parse("math:sin(xs:double('NaN'))").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:sin(xs:double('INF'))").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:sin(xs:double('-INF'))").evaluate()))

    def test_cos_math_function(self):
        self.assertIsNone(self.parser.parse('math:cos(())').evaluate())
        self.assertEqual(self.parser.parse('math:cos(0)').evaluate(), 1.0)
        self.assertEqual(self.parser.parse('math:cos(-0.0e0)').evaluate(), 1.0)
        self.assertTrue(math.isclose(
            self.parser.parse('math:cos(math:pi() div 2)').evaluate(), 0.0, abs_tol=1e-14
        ))
        self.assertTrue(math.isclose(
            self.parser.parse('math:cos(-math:pi() div 2)').evaluate(), 0.0, abs_tol=1e-14
        ))
        self.assertEqual(self.parser.parse('math:cos(math:pi())').evaluate(), -1.0)
        self.assertTrue(math.isnan(self.parser.parse("math:cos(xs:double('NaN'))").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:cos(xs:double('INF'))").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:cos(xs:double('-INF'))").evaluate()))

    def test_tan_math_function(self):
        self.assertIsNone(self.parser.parse('math:tan(())').evaluate())
        self.assertEqual(self.parser.parse('math:tan(0)').evaluate(), 0.0)
        self.assertEqual(self.parser.parse('math:tan(-0.0e0)').evaluate(), -0.0)
        self.assertTrue(math.isclose(
            self.parser.parse('math:tan(math:pi() div 4)').evaluate(), 1.0, abs_tol=1e-14
        ))
        self.assertTrue(math.isclose(
            self.parser.parse('math:tan(-math:pi() div 4)').evaluate(), -1.0, abs_tol=1e-14
        ))
        self.assertTrue(math.isclose(
            self.parser.parse('math:tan(math:pi() div 2)').evaluate(),
            1.633123935319537E16, rel_tol=1e-14
        ))
        self.assertTrue(math.isclose(
            self.parser.parse('math:tan(-math:pi() div 2)').evaluate(),
            -1.633123935319537E16, rel_tol=1e-14
        ))
        self.assertTrue(math.isclose(
            self.parser.parse('math:tan(math:pi())').evaluate(), 0.0, abs_tol=1e-14
        ))
        self.assertTrue(math.isnan(self.parser.parse("math:tan(xs:double('NaN'))").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:tan(xs:double('INF'))").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:tan(xs:double('-INF'))").evaluate()))

    def test_asin_math_function(self):
        self.assertIsNone(self.parser.parse('math:asin(())').evaluate())
        self.assertEqual(self.parser.parse('math:asin(0)').evaluate(), 0.0)
        self.assertEqual(self.parser.parse('math:asin(-0.0e0)').evaluate(), -0.0)
        self.assertTrue(math.isclose(
            self.parser.parse('math:asin(1.0e0)').evaluate(),
            1.5707963267948966e0, rel_tol=1e-14
        ))
        self.assertTrue(math.isclose(
            self.parser.parse('math:asin(-1.0e0)').evaluate(),
            -1.5707963267948966e0, rel_tol=1e-14
        ))
        self.assertTrue(math.isnan(self.parser.parse("math:asin(2.0e0)").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:asin(xs:double('NaN'))").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:asin(xs:double('INF'))").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:asin(xs:double('-INF'))").evaluate()))

    def test_acos_math_function(self):
        self.assertIsNone(self.parser.parse('math:acos(())').evaluate())
        self.assertTrue(math.isclose(
            self.parser.parse('math:acos(0.0e0)').evaluate(),
            1.5707963267948966e0, rel_tol=1e-14
        ))
        self.assertTrue(math.isclose(
            self.parser.parse('math:acos(-0.0e0)').evaluate(),
            1.5707963267948966e0, rel_tol=1e-14
        ))
        self.assertEqual(self.parser.parse('math:acos(1.0)').evaluate(), 0.0)
        self.assertEqual(self.parser.parse('math:acos(-1.0e0)').evaluate(), math.pi)
        self.assertTrue(math.isnan(self.parser.parse("math:acos(2.0e0)").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:acos(xs:double('NaN'))").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:acos(xs:double('INF'))").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:acos(xs:double('-INF'))").evaluate()))

    def test_atan_math_function(self):
        self.assertIsNone(self.parser.parse('math:atan(())').evaluate())
        self.assertEqual(self.parser.parse('math:atan(0)').evaluate(), 0.0)
        self.assertEqual(self.parser.parse('math:atan(-0.0e0)').evaluate(), -0.0)
        self.assertTrue(math.isclose(
            self.parser.parse('math:atan(1.0e0)').evaluate(),
            0.7853981633974483e0, rel_tol=1e-14
        ))
        self.assertTrue(math.isclose(
            self.parser.parse('math:atan(-1.0e0)').evaluate(),
            -0.7853981633974483e0, rel_tol=1e-14
        ))
        self.assertTrue(math.isnan(self.parser.parse("math:atan(xs:double('NaN'))").evaluate()))
        self.assertTrue(math.isclose(
            self.parser.parse("math:atan(xs:double('INF'))").evaluate(),
            1.5707963267948966e0, rel_tol=1e-5
        ))
        self.assertTrue(math.isclose(
            self.parser.parse("math:atan(xs:double('-INF'))").evaluate(),
            -1.5707963267948966e0, rel_tol=1e-5
        ))

    def test_atan2_math_function(self):
        self.assertEqual(self.parser.parse('math:atan2(+0.0e0, 0.0e0)').evaluate(), 0.0)
        self.assertEqual(self.parser.parse('math:atan2(-0.0e0, 0.0e0)').evaluate(), -0.0)
        self.assertEqual(self.parser.parse('math:atan2(+0.0e0, -0.0e0)').evaluate(), math.pi)
        self.assertEqual(self.parser.parse('math:atan2(-0.0e0, -0.0e0)').evaluate(), -math.pi)
        self.assertEqual(self.parser.parse('math:atan2(-1, 0.0e0)').evaluate(), -math.pi / 2)
        self.assertEqual(self.parser.parse('math:atan2(+1, 0.0e0)').evaluate(), math.pi / 2)
        self.assertEqual(self.parser.parse('math:atan2(-0.0e0, -1)').evaluate(), -math.pi)
        self.assertEqual(self.parser.parse('math:atan2(+0.0e0, -1)').evaluate(), math.pi)
        self.assertEqual(self.parser.parse('math:atan2(-0.0e0, +1)').evaluate(), -0.0e0)
        self.assertEqual(self.parser.parse('math:atan2(+0.0e0, +1)').evaluate(), 0.0e0)

    def test_has_children_function(self):
        with self.assertRaises(MissingContextError):
            self.parser.parse('has-children()').evaluate()
        with self.assertRaises(MissingContextError):
            self.parser.parse('fn:has-children(1)').evaluate()

        context = XPathContext(root=self.etree.ElementTree(self.etree.XML('<dummy/>')))
        self.assertTrue(self.parser.parse('has-children()').evaluate(context))
        self.assertTrue(self.parser.parse('has-children(.)').evaluate(context))

        context = XPathContext(root=self.etree.XML('<dummy/>'))
        self.assertFalse(self.parser.parse('has-children()').evaluate(context))
        self.assertFalse(self.parser.parse('has-children(.)').evaluate(context))
        context.item = None
        self.assertFalse(self.parser.parse('has-children()').evaluate(context))
        self.assertFalse(self.parser.parse('has-children(.)').evaluate(context))

        context.variables['elem'] = self.etree.XML('<a><b1/><b2/></a>')
        self.assertTrue(self.parser.parse('has-children($elem)').evaluate(context))
        self.assertFalse(self.parser.parse('has-children($elem/b1)').evaluate(context))

    def test_innermost_function(self):
        with self.assertRaises(MissingContextError):
            self.parser.parse('fn:innermost(A)').evaluate()

        root = self.etree.XML('<a/>')
        document = self.etree.ElementTree(root)
        context = XPathContext(root=document)
        nodes = self.parser.parse('fn:innermost(.)').evaluate(context)
        self.assertIsInstance(nodes, list)
        self.assertEqual(len(nodes), 1)
        self.assertIs(nodes[0], document)

        context = XPathContext(root=root)
        nodes = self.parser.parse('fn:innermost(.)').evaluate(context)
        self.assertIsInstance(nodes, list)
        self.assertEqual(len(nodes), 1)
        self.assertIs(nodes[0], root)

        context = XPathContext(root=document)
        context.variables['nodes'] = [root, document]
        nodes = self.parser.parse('fn:innermost($nodes)').evaluate(context)
        self.assertIsInstance(nodes, list)
        self.assertEqual(len(nodes), 1)
        self.assertIs(nodes[0], document)


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
