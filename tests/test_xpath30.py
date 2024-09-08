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
import io
import unittest
import os
import re
import math
import pathlib
import platform
import xml.etree.ElementTree as ElementTree
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

from elementpath import select, XPathContext, MissingContextError, datatypes, XPathFunction
from elementpath.namespaces import XPATH_FUNCTIONS_NAMESPACE
from elementpath.etree import is_etree_element, is_lxml_etree_document, is_etree_document
from elementpath.xpath_nodes import ElementNode, DocumentNode
from elementpath.xpath3 import XPath30Parser
from elementpath.xpath30.xpath30_helpers import PICTURE_PATTERN, \
    int_to_roman, int_to_alphabetic, int_to_words

try:
    from tests import test_xpath2_parser
    from tests import test_xpath2_functions
    from tests import test_xpath2_constructors
except ImportError:
    import test_xpath2_parser
    import test_xpath2_functions
    import test_xpath2_constructors


ANALYZE_STRING_1 = """<analyze-string-result xmlns="http://www.w3.org/2005/xpath-functions">
  <match><group nr="1">2008</group>-<group nr="2">12</group>-<group nr="3">03</group></match>
</analyze-string-result>"""

ANALYZE_STRING_2 = """<analyze-string-result xmlns="http://www.w3.org/2005/xpath-functions">
  <match><group nr="1">A</group><group nr="2">1</group></match>
  <non-match>,</non-match>
  <match><group nr="1">C</group><group nr="2">15</group></match>
  <non-match>,,</non-match>
  <match><group nr="1">D</group><group nr="2">24</group></match>
  <non-match>, </non-match>
  <match><group nr="1">X</group><group nr="2">50</group></match>
  <non-match>,</non-match>
</analyze-string-result>"""


class XPath30ParserTest(test_xpath2_parser.XPath2ParserTest):

    def setUp(self):
        self.parser = XPath30Parser(namespaces=self.namespaces)

    def test_decimal_formats_argument(self):
        decimal_formats = {None: {'decimal-separator': '|', 'grouping-separator': '.'}}
        parser = self.parser.__class__(decimal_formats=decimal_formats)
        expected = {
            'decimal-separator': '|',
            'grouping-separator': '.',
            'exponent-separator': 'e',
            'infinity': 'Infinity',
            'minus-sign': '-', 'NaN': 'NaN',
            'percent': '%',
            'per-mille': '‰',
            'zero-digit': '0',
            'digit': '#',
            'pattern-separator': ';'
        }
        self.assertDictEqual(parser.decimal_formats[None], expected)
        self.assertEqual(
            repr(parser), f"<{parser.__class__.__name__} object at {hex(id(parser))}>"
        )
        self.assertEqual(
            str(parser),
            f'{parser.__class__.__name__}(decimal_formats={parser.decimal_formats})'
        )

        decimal_formats = {'foo': {'decimal-separator': '|', 'grouping-separator': '.'}}
        parser = self.parser.__class__(decimal_formats=decimal_formats)
        self.assertDictEqual(parser.decimal_formats[None],
                             self.parser.__class__.decimal_formats[None])
        self.assertDictEqual(parser.decimal_formats.get('foo'), expected)

    def test_defuse_xml_argument(self):
        parser = self.parser.__class__(defuse_xml=False)
        self.assertFalse(parser.defuse_xml)
        self.assertEqual(
            repr(parser), f'<{parser.__class__.__name__} object at {hex(id(parser))}>'
        )
        self.assertEqual(str(parser), f'{parser.__class__.__name__}(defuse_xml=False)')

        parser = self.parser.__class__({'tst': 'http://xpath.test/ns'}, defuse_xml=False)
        self.assertEqual(
            str(parser),
            f"{parser.__class__.__name__}({{'tst': 'http://xpath.test/ns'}}, defuse_xml=False)"
        )
        self.assertEqual(
            str(parser),
            f"{parser.__class__.__name__}({{'tst': 'http://xpath.test/ns'}}, defuse_xml=False)"
        )

    def test_function_match(self):
        token = self.parser.parse('math:pi()')
        self.assertEqual(
            repr(token), f"<{token.__class__.__name__} object at {hex(id(token))}>"
        )
        self.assertEqual(str(token), "'math:pi' function")
        self.assertEqual(token.source, 'math:pi()')

    def test_braced_uri_literal(self):
        expected_lexemes = ['Q{', 'http', ':', '//', 'xpath.test', '/', 'ns', '}', 'ABC']
        self.check_tokenizer("Q{http://xpath.test/ns}ABC", expected_lexemes)
        self.check_tokenizer("/Q{http://xpath.test/ns}ABC", ['/'] + expected_lexemes)

        self.check_tokenizer("Q{###}ABC", ['Q{', '#', '#', '#', '}', 'ABC'])

        expression = '/Q{http://xpath.test/ns}ABC'
        token = self.parser.parse(expression)
        self.assertEqual(token.symbol, '/')
        self.assertEqual(token[0].symbol, 'Q{')
        self.assertEqual(token.source, expression)

        with self.assertRaises(TypeError) as ctx:
            self.parser.parse('/Q{###}ABC')
        self.assertIn('XQST0046', str(ctx.exception))

        expression = 'Q{http://www.w3.org/2005/xpath-functions/math}pi()'
        token = self.parser.parse(expression)
        self.assertAlmostEqual(token.evaluate(), math.pi)
        self.assertEqual(token.source, expression)

        expression = 'Q{}foo'
        token = self.parser.parse(expression)
        self.assertEqual(token.value, 'foo')

        expression = 'Q{   }foo'
        token = self.parser.parse(expression)
        self.assertEqual(token.value, 'foo')

        expression = 'Q{ bar  }foo'
        token = self.parser.parse(expression)
        self.assertEqual(token.value, '{bar}foo')

        with self.assertRaises(SyntaxError):
            self.parser.parse('Q{   }')

        with self.assertRaises(SyntaxError):
            self.parser.parse('Q{   }  ')

        with self.assertRaises(SyntaxError):
            self.parser.parse('Q{bar}  ')

        # '{' is unusable for non-standard braced URI literals
        # because is used for inline functions body
        with self.assertRaises(SyntaxError):
            self.parser.parse('{http://www.w3.org/2005/xpath-functions/math}pi()')

    def test_concat_operator(self):
        token = self.parser.parse("10 || '/' || 6")
        self.assertEqual(token.evaluate(), "10/6")
        self.assertEqual(token.source, "10 || '/' || 6")

        self.check_tree('"true" || "false"', "(|| ('true') ('false'))")
        self.check_tree('"true"||"false"', "(|| ('true') ('false'))")

    def test_function_test(self):
        func: XPathFunction
        expression = "function($x as item()) as item() { $x }"
        func = cast(XPathFunction, self.parser.parse(expression))
        self.assertTrue(func.match_function_test('function(*)'))
        self.assertEqual(func.source, expression.replace(" $x ", '$x'))

        func = cast(XPathFunction, self.parser.parse("function($x as item()) as xs:integer { $x }"))
        self.assertTrue(func.match_function_test('function(item()) as item()'))

        func = cast(XPathFunction, self.parser.parse("function($x as item()) as item() { $x }"))
        self.assertTrue(func.match_function_test('function(xs:string) as item()'))

    def test_dynamic_function_call(self):
        token = self.parser.parse("$f(2, 3)")
        self.assertEqual(token.source, "$f(2, 3)")

        with self.assertRaises(MissingContextError):
            token.evaluate()

        root = self.etree.XML('<root/>')
        context = XPathContext(root=root, variables={'f': 10})

        with self.assertRaises(TypeError):
            token.evaluate(context)

        context.variables['f'] = self.parser.symbol_table['concat'](self.parser, nargs=2)
        self.assertEqual(token.evaluate(context), '23')

        with self.assertRaises(TypeError):
            self.parser.parse("f(2, 3)")

        with self.assertRaises(MissingContextError):
            token.evaluate()

        token = self.parser.parse('$f[2]("Hi there")')
        self.assertEqual(token.source, "$f[2]('Hi there')")

        with self.assertRaises(MissingContextError):
            token.evaluate()

        context.variables['f'] = self.parser.symbol_table['concat'](self.parser, nargs=2)
        with self.assertRaises(TypeError):
            token.evaluate(context)

        context.variables['f'] = [1, context.variables['f']]
        with self.assertRaises(TypeError):
            token.evaluate(context)

        context.variables['f'] = self.parser.symbol_table['true'](self.parser, nargs=0)
        token = self.parser.parse('$f()[2]')
        self.assertEqual(token.source, "$f()[2]")

        with self.assertRaises(MissingContextError):
            token.evaluate()

        self.assertEqual(token.evaluate(context), [])
        token = self.parser.parse('$f()[1]')
        self.assertTrue(token.evaluate(context))

    def test_let_expression(self):
        expression = 'let $x := 4, $y := 3 return $x + $y'
        token = self.parser.parse(expression)
        self.assertEqual(token.source, expression)

        with self.assertRaises(MissingContextError):
            token.evaluate()

        root = self.etree.XML('<root/>')
        context = XPathContext(root=root)
        self.assertEqual(token.evaluate(context), [7])

    def test_picture_pattern(self):
        self.assertListEqual(PICTURE_PATTERN.findall(''), [])
        self.assertListEqual(PICTURE_PATTERN.findall('a'), [])
        self.assertListEqual(PICTURE_PATTERN.findall('[y]'), ['[y]'])
        self.assertListEqual(PICTURE_PATTERN.findall('[h01][m01][z,2-6]'),
                             ['[h01]', '[m01]', '[z,2-6]'])
        self.assertListEqual(PICTURE_PATTERN.findall('[H٠]:[m٠]:[s٠٠]:[f٠٠٠]'),
                             ['[H٠]', '[m٠]', '[s٠٠]', '[f٠٠٠]'])
        self.assertListEqual(PICTURE_PATTERN.split(' [H٠]:[m٠]:[s٠٠]:[f٠٠٠]'),
                             [' ', ':', ':', ':', ''])
        self.assertListEqual(PICTURE_PATTERN.findall('[y'), [])
        self.assertListEqual(PICTURE_PATTERN.findall('[[y]'), ['[y]'])

    def test_int_to_roman(self):
        self.assertRaises(TypeError, int_to_roman, 3.0)
        self.assertEqual(int_to_roman(0), '0')
        self.assertEqual(int_to_roman(3), 'III')
        self.assertEqual(int_to_roman(4), 'IV')
        self.assertEqual(int_to_roman(5), 'V')
        self.assertEqual(int_to_roman(7), 'VII')
        self.assertEqual(int_to_roman(9), 'IX')
        self.assertEqual(int_to_roman(10), 'X')
        self.assertEqual(int_to_roman(11), 'XI')
        self.assertEqual(int_to_roman(19), 'XIX')
        self.assertEqual(int_to_roman(20), 'XX')
        self.assertEqual(int_to_roman(49), 'XLIX')
        self.assertEqual(int_to_roman(100), 'C')
        self.assertEqual(int_to_roman(489), 'CDLXXXIX')
        self.assertEqual(int_to_roman(2999), 'MMCMXCIX')

    def test_int_to_alphabetic(self):
        self.assertEqual(int_to_alphabetic(4), 'd')
        self.assertEqual(int_to_alphabetic(7), 'g')
        self.assertEqual(int_to_alphabetic(25), 'y')
        self.assertEqual(int_to_alphabetic(26), 'z')
        self.assertEqual(int_to_alphabetic(27), 'aa')
        self.assertEqual(int_to_alphabetic(-29), '-ac')
        self.assertEqual(int_to_alphabetic(890), 'ahf')

    def test_int_to_words(self):
        self.assertEqual(int_to_words(1), 'one')
        self.assertEqual(int_to_words(4), 'four')


@unittest.skipIf(lxml_etree is None, "The lxml library is not installed")
class LxmlXPath30ParserTest(XPath30ParserTest):
    etree = lxml_etree


class XPath30FunctionsTest(test_xpath2_functions.XPath2FunctionsTest):

    maxDiff = 1024

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
        self.assertEqual(token.evaluate(), [])
        self.assertEqual(token.source, 'math:exp(())')

        self.assertAlmostEqual(self.parser.parse('math:exp(0)').evaluate(), 1.0)
        self.assertAlmostEqual(self.parser.parse('math:exp(1)').evaluate(),
                               2.718281828459045)
        self.assertAlmostEqual(self.parser.parse('math:exp(2)').evaluate(),
                               7.38905609893065)
        self.assertAlmostEqual(self.parser.parse('math:exp(-1)').evaluate(),
                               0.36787944117144233)
        self.assertAlmostEqual(self.parser.parse('math:exp(math:pi())').evaluate(),
                               23.140692632779267)

        expression = 'math:exp(xs:double("NaN"))'
        self.assertTrue(math.isnan(self.parser.parse(expression).evaluate()))
        self.check_source(expression, expression.replace('"', "'"))

        self.assertEqual(self.parser.parse("math:exp(xs:double('INF'))").evaluate(), float('inf'))

        expression = "math:exp(xs:double('-INF'))"
        self.assertAlmostEqual(self.parser.parse(expression).evaluate(), 0.0)
        self.check_source(expression, expression.replace('"', "'"))

    def test_exp10_math_function(self):
        token = self.parser.parse('math:exp10(())')
        self.assertEqual(token.evaluate(), [])
        self.assertEqual(token.source, 'math:exp10(())')

        self.assertAlmostEqual(self.parser.parse('math:exp10(0)').evaluate(), 1.0)
        self.assertAlmostEqual(self.parser.parse('math:exp10(1)').evaluate(), 10)
        self.assertAlmostEqual(self.parser.parse('math:exp10(0.5)').evaluate(),
                               3.1622776601683795)
        self.assertAlmostEqual(self.parser.parse('math:exp10(-1)').evaluate(), 0.1)
        self.assertTrue(math.isnan(self.parser.parse('math:exp10(xs:double("NaN"))').evaluate()))
        self.assertEqual(self.parser.parse("math:exp10(xs:double('INF'))").evaluate(), float('inf'))
        self.assertAlmostEqual(self.parser.parse("math:exp10(xs:double('-INF'))").evaluate(), 0.0)

    def test_log_math_function(self):
        token = self.parser.parse('math:log(())')
        self.assertEqual(token.evaluate(), [])
        self.assertEqual(token.source, 'math:log(())')

        self.assertEqual(self.parser.parse('math:log(0)').evaluate(), float('-inf'))
        self.assertAlmostEqual(self.parser.parse('math:log(math:exp(1))').evaluate(), 1.0)
        self.assertAlmostEqual(self.parser.parse('math:log(1.0e-3)').evaluate(), -6.907755278982137)
        self.assertAlmostEqual(self.parser.parse('math:log(2)').evaluate(), 0.6931471805599453)
        self.assertTrue(math.isnan(self.parser.parse('math:log(-1)').evaluate()))
        self.assertTrue(math.isnan(self.parser.parse('math:log(xs:double("NaN"))').evaluate()))
        self.assertEqual(self.parser.parse("math:log(xs:double('INF'))").evaluate(), float('inf'))
        self.assertTrue(math.isnan(self.parser.parse('math:log(xs:double("-INF"))').evaluate()))

    def test_log10_math_function(self):
        token = self.parser.parse('math:log10(())')
        self.assertEqual(token.evaluate(), [])
        self.assertEqual(token.source, 'math:log10(())')

        self.assertEqual(self.parser.parse('math:log10(0)').evaluate(), float('-inf'))
        self.assertAlmostEqual(self.parser.parse('math:log10(1.0e3)').evaluate(), 3.0)
        self.assertAlmostEqual(self.parser.parse('math:log10(1.0e-3)').evaluate(), -3.0)
        self.assertAlmostEqual(self.parser.parse('math:log10(2)').evaluate(), 0.3010299956639812)
        self.assertTrue(math.isnan(self.parser.parse('math:log10(-1)').evaluate()))
        self.assertTrue(math.isnan(self.parser.parse('math:log10(xs:double("NaN"))').evaluate()))
        self.assertEqual(self.parser.parse("math:log10(xs:double('INF'))").evaluate(), float('inf'))
        self.assertTrue(math.isnan(self.parser.parse('math:log10(xs:double("-INF"))').evaluate()))

    def test_pow_math_function(self):
        self.assertEqual(self.parser.parse('math:pow((), 93.7)').evaluate(), [])
        self.assertAlmostEqual(self.parser.parse('math:pow(2, 3)').evaluate(), 8.0)
        self.assertAlmostEqual(self.parser.parse('math:pow(-2, 3)').evaluate(), -8.0)
        self.assertAlmostEqual(self.parser.parse('math:pow(2, -3)').evaluate(), 0.125)
        self.assertAlmostEqual(self.parser.parse('math:pow(-2, -3)').evaluate(), -0.125)
        self.assertAlmostEqual(self.parser.parse('math:pow(2, 0)').evaluate(), 1.0)
        self.assertAlmostEqual(self.parser.parse('math:pow(0, 0)').evaluate(), 1.0)
        self.assertAlmostEqual(self.parser.parse("math:pow(xs:double('INF'), 0)").evaluate(), 1.0)
        self.assertAlmostEqual(self.parser.parse("math:pow(xs:double('NaN'), 0)").evaluate(), 1.0)
        self.assertAlmostEqual(self.parser.parse("math:pow(-math:pi(), 0)").evaluate(), 1.0)
        self.assertAlmostEqual(self.parser.parse('math:pow(0e0, 3)').evaluate(), 0.0)
        self.assertAlmostEqual(self.parser.parse('math:pow(0e0, 4)').evaluate(), 0.0)
        self.assertAlmostEqual(self.parser.parse('math:pow(-0e0, 3)').evaluate(), 0.0)
        self.assertAlmostEqual(self.parser.parse('math:pow(0, 3)').evaluate(), 0.0)
        self.assertEqual(self.parser.parse('math:pow(0e0, -3)').evaluate(), float('inf'))
        self.assertEqual(self.parser.parse('math:pow(0e0, -4)').evaluate(), float('inf'))
        self.assertEqual(self.parser.parse('math:pow(-0e0, -3)').evaluate(), float('-inf'))
        self.assertEqual(self.parser.parse('math:pow(0, -4)').evaluate(), float('inf'))
        self.assertAlmostEqual(self.parser.parse('math:pow(16, 0.5e0)').evaluate(), 4.0)
        self.assertAlmostEqual(self.parser.parse('math:pow(16, 0.25e0)').evaluate(), 2.0)
        self.assertEqual(self.parser.parse('math:pow(0e0, -3.0e0)').evaluate(), float('inf'))
        self.assertEqual(self.parser.parse('math:pow(-0e0, -3.0e0)').evaluate(), float('-inf'))
        self.assertEqual(self.parser.parse('math:pow(0e0, -3.1e0)').evaluate(), float('inf'))
        self.assertEqual(self.parser.parse('math:pow(-0e0, -3.1e0)').evaluate(), float('inf'))
        self.assertAlmostEqual(self.parser.parse('math:pow(0e0, 3.0e0)').evaluate(), 0.0)
        self.assertAlmostEqual(self.parser.parse('math:pow(-0e0, 3.0e0)').evaluate(), -0.0)
        self.assertAlmostEqual(self.parser.parse('math:pow(0e0, 3.1e0)').evaluate(), 0.0)
        self.assertAlmostEqual(self.parser.parse('math:pow(-0e0, 3.1e0)').evaluate(), -0.0)

        self.assertAlmostEqual(self.parser.parse("math:pow(-1, xs:double('INF'))").evaluate(), 1.0)
        self.assertAlmostEqual(self.parser.parse("math:pow(-1, xs:double('-INF'))").evaluate(), 1.0)
        self.assertAlmostEqual(self.parser.parse("math:pow(1, xs:double('INF'))").evaluate(), 1.0)
        self.assertAlmostEqual(self.parser.parse("math:pow(1, xs:double('-INF'))").evaluate(), 1.0)

        self.assertAlmostEqual(self.parser.parse("math:pow(1, xs:double('NaN'))").evaluate(), 1.0)
        self.assertAlmostEqual(self.parser.parse('math:pow(-2.5e0, 2.0e0)').evaluate(), 6.25)
        self.assertTrue(math.isnan(self.parser.parse('math:pow(-2.5e0, 2.00000001e0)').evaluate()))

        self.check_source('math:pow(0e0, 3.1e0)', 'math:pow(0.0, 3.1)')

    def test_sqrt_math_function(self):
        self.assertEqual(self.parser.parse('math:sqrt(())').evaluate(), [])
        self.assertAlmostEqual(self.parser.parse('math:sqrt(0.0e0)').evaluate(), 0.0)
        self.assertAlmostEqual(self.parser.parse('math:sqrt(-0.0e0)').evaluate(), -0.0)
        self.assertAlmostEqual(self.parser.parse('math:sqrt(1.0e6)').evaluate(), 1.0e3)
        self.assertAlmostEqual(self.parser.parse('math:sqrt(2.0e0)').evaluate(), 1.4142135623730951)
        self.assertTrue(math.isnan(self.parser.parse('math:sqrt(-2.0e0)').evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:sqrt(xs:double('NaN'))").evaluate()))
        self.assertEqual(self.parser.parse("math:sqrt(xs:double('INF'))").evaluate(), float('inf'))
        self.assertTrue(math.isnan(self.parser.parse("math:sqrt(xs:double('-INF'))").evaluate()))

        self.check_source('math:sqrt(1.0e6)', 'math:sqrt(1000000.0)')

    def test_sin_math_function(self):
        self.assertEqual(self.parser.parse('math:sin(())').evaluate(), [])
        self.assertAlmostEqual(self.parser.parse('math:sin(0)').evaluate(), 0.0)
        self.assertAlmostEqual(self.parser.parse('math:sin(-0.0e0)').evaluate(), -0.0)
        self.assertAlmostEqual(self.parser.parse('math:sin(math:pi() div 2)').evaluate(), 1.0)
        self.assertAlmostEqual(self.parser.parse('math:sin(-math:pi() div 2)').evaluate(), -1.0)
        self.assertAlmostEqual(self.parser.parse('math:sin(math:pi())').evaluate(), 0.0, places=13)
        self.assertTrue(math.isnan(self.parser.parse("math:sin(xs:double('NaN'))").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:sin(xs:double('INF'))").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:sin(xs:double('-INF'))").evaluate()))

        expression = 'math:sin(-math:pi() div 2)'
        token = self.parser.parse(expression)
        self.assertEqual(token.source, expression)
        self.assertEqual(
            repr(token[1]), f'<XPathFunction math:sin#1 at {hex(id(token[1]))}>'
        )
        self.assertEqual(str(token[1]), "'math:sin' function")

    def test_cos_math_function(self):
        self.assertEqual(self.parser.parse('math:cos(())').evaluate(), [])
        self.assertAlmostEqual(self.parser.parse('math:cos(0)').evaluate(), 1.0)
        self.assertAlmostEqual(self.parser.parse('math:cos(-0.0e0)').evaluate(), 1.0)
        self.assertAlmostEqual(self.parser.parse('math:cos(math:pi() div 2)').evaluate(),
                               0.0, places=13)
        self.assertAlmostEqual(self.parser.parse('math:cos(-math:pi() div 2)').evaluate(),
                               0.0, places=13)
        self.assertAlmostEqual(self.parser.parse('math:cos(math:pi())').evaluate(), -1.0)
        self.assertTrue(math.isnan(self.parser.parse("math:cos(xs:double('NaN'))").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:cos(xs:double('INF'))").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:cos(xs:double('-INF'))").evaluate()))

        expression = "math:cos(xs:double('INF'))"
        token = self.parser.parse(expression)
        self.assertEqual(token.source, expression)
        self.assertEqual(
            repr(token[1]), f'<XPathFunction math:cos#1 at {hex(id(token[1]))}>'
        )
        self.assertEqual(str(token[1]), "'math:cos' function")

    def test_tan_math_function(self):
        self.assertEqual(self.parser.parse('math:tan(())').evaluate(), [])
        self.assertAlmostEqual(self.parser.parse('math:tan(0)').evaluate(), 0.0)
        self.assertAlmostEqual(self.parser.parse('math:tan(-0.0e0)').evaluate(), -0.0)
        self.assertAlmostEqual(self.parser.parse('math:tan(math:pi() div 4)').evaluate(),
                               1.0, places=13)
        self.assertAlmostEqual(self.parser.parse('math:tan(-math:pi() div 4)').evaluate(),
                               -1.0, places=13)
        self.assertAlmostEqual(self.parser.parse('math:tan(math:pi() div 2)').evaluate(),
                               1.633123935319537E16, places=13)
        self.assertAlmostEqual(self.parser.parse('math:tan(-math:pi() div 2)').evaluate(),
                               -1.633123935319537E16, places=13)
        self.assertAlmostEqual(self.parser.parse('math:tan(math:pi())').evaluate(),
                               0.0, places=13)
        self.assertTrue(math.isnan(self.parser.parse("math:tan(xs:double('NaN'))").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:tan(xs:double('INF'))").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:tan(xs:double('-INF'))").evaluate()))

        expression = 'math:tan(-0.0e0)'
        token = self.parser.parse(expression)
        self.assertEqual(token.source, 'math:tan(-0.0)')
        self.assertEqual(
            repr(token[1]), f"<XPathFunction math:tan#1 at {hex(id(token[1]))}>"
        )
        self.assertEqual(str(token[1]), "'math:tan' function")

    def test_asin_math_function(self):
        self.assertEqual(self.parser.parse('math:asin(())').evaluate(), [])
        self.assertAlmostEqual(self.parser.parse('math:asin(0)').evaluate(), 0.0)
        self.assertAlmostEqual(self.parser.parse('math:asin(-0.0e0)').evaluate(), -0.0)
        self.assertAlmostEqual(
            self.parser.parse('math:asin(1.0e0)').evaluate(),
            1.5707963267948966e0, places=13
        )
        self.assertAlmostEqual(
            self.parser.parse('math:asin(-1.0e0)').evaluate(),
            -1.5707963267948966e0, places=13
        )
        self.assertTrue(math.isnan(self.parser.parse("math:asin(2.0e0)").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:asin(xs:double('NaN'))").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:asin(xs:double('INF'))").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:asin(xs:double('-INF'))").evaluate()))

    def test_acos_math_function(self):
        self.assertEqual(self.parser.parse('math:acos(())').evaluate(), [])
        self.assertAlmostEqual(
            self.parser.parse('math:acos(0.0e0)').evaluate(),
            1.5707963267948966e0, places=13
        )
        self.assertAlmostEqual(
            self.parser.parse('math:acos(-0.0e0)').evaluate(),
            1.5707963267948966e0, places=13
        )
        self.assertAlmostEqual(self.parser.parse('math:acos(1.0)').evaluate(), 0.0)
        self.assertAlmostEqual(self.parser.parse('math:acos(-1.0e0)').evaluate(), math.pi)
        self.assertTrue(math.isnan(self.parser.parse("math:acos(2.0e0)").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:acos(xs:double('NaN'))").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:acos(xs:double('INF'))").evaluate()))
        self.assertTrue(math.isnan(self.parser.parse("math:acos(xs:double('-INF'))").evaluate()))

    def test_atan_math_function(self):
        self.assertEqual(self.parser.parse('math:atan(())').evaluate(), [])
        self.assertAlmostEqual(self.parser.parse('math:atan(0)').evaluate(), 0.0)
        self.assertAlmostEqual(self.parser.parse('math:atan(-0.0e0)').evaluate(), -0.0)
        self.assertAlmostEqual(
            self.parser.parse('math:atan(1.0e0)').evaluate(),
            0.7853981633974483e0, places=13
        )
        self.assertAlmostEqual(
            self.parser.parse('math:atan(-1.0e0)').evaluate(),
            -0.7853981633974483e0, places=13
        )
        self.assertTrue(math.isnan(self.parser.parse("math:atan(xs:double('NaN'))").evaluate()))
        self.assertAlmostEqual(
            self.parser.parse("math:atan(xs:double('INF'))").evaluate(),
            1.5707963267948966e0, places=5
        )
        self.assertAlmostEqual(
            self.parser.parse("math:atan(xs:double('-INF'))").evaluate(),
            -1.5707963267948966e0, places=5
        )

    def test_atan2_math_function(self):
        self.assertAlmostEqual(self.parser.parse('math:atan2(+0.0e0, 0.0e0)').evaluate(), 0.0)
        self.assertAlmostEqual(self.parser.parse('math:atan2(-0.0e0, 0.0e0)').evaluate(), -0.0)
        self.assertAlmostEqual(self.parser.parse('math:atan2(+0.0e0, -0.0e0)').evaluate(), math.pi)
        self.assertAlmostEqual(self.parser.parse('math:atan2(-0.0e0, -0.0e0)').evaluate(), -math.pi)
        self.assertAlmostEqual(self.parser.parse('math:atan2(-1, 0.0e0)').evaluate(), -math.pi / 2)
        self.assertAlmostEqual(self.parser.parse('math:atan2(+1, 0.0e0)').evaluate(), math.pi / 2)
        self.assertAlmostEqual(self.parser.parse('math:atan2(-0.0e0, -1)').evaluate(), -math.pi)
        self.assertAlmostEqual(self.parser.parse('math:atan2(+0.0e0, -1)').evaluate(), math.pi)
        self.assertAlmostEqual(self.parser.parse('math:atan2(-0.0e0, +1)').evaluate(), -0.0e0)
        self.assertAlmostEqual(self.parser.parse('math:atan2(+0.0e0, +1)').evaluate(), 0.0e0)

    def test_analyze_string_function(self):
        expression = 'fn:analyze-string("The cat sat on the mat.", "unmatchable")'
        token = self.parser.parse(expression)
        self.assertEqual(token.source, expression.replace('"', "'"))
        self.assertEqual(
            repr(token[1]), f'<XPathFunction fn:analyze-string at {hex(id(token[1]))}>'
        )
        self.assertEqual(str(token[1]), "'fn:analyze-string' function")

        context = XPathContext(root=self.etree.XML('<root/>'))

        result = token.evaluate(context)
        self.assertIsInstance(result, ElementNode)
        root = result.elem
        self.assertEqual(len(root), 1)
        self.assertEqual(root[0].text, "The cat sat on the mat.")

        token = self.parser.parse(r'fn:analyze-string("The cat sat on the mat.", "\w+")')
        result = token.evaluate(context)
        self.assertIsInstance(result, ElementNode)
        root = result.elem
        self.assertEqual(len(root), 12)
        chunks = ['The', ' ', 'cat', ' ', 'sat', ' ', 'on', ' ', 'the', ' ', 'mat', '.']
        for k in range(len(chunks)):
            if k % 2:
                self.assertEqual(root[k].tag, '{http://www.w3.org/2005/xpath-functions}non-match')
            else:
                self.assertEqual(root[k].tag, '{http://www.w3.org/2005/xpath-functions}match')
            self.assertEqual(root[k].text, chunks[k])

        token = self.parser.parse(r'fn:analyze-string("2008-12-03", "^(\d+)\-(\d+)\-(\d+)$")')
        result = token.evaluate(context)
        self.assertIsInstance(result, ElementNode)
        root = result.elem
        self.assertEqual(len(root), 1)

        ElementTree.register_namespace('', XPATH_FUNCTIONS_NAMESPACE)
        self.assertEqual(
            ElementTree.tostring(root, encoding='utf-8').decode('utf-8'),
            re.sub(r'\n\s*', '', ANALYZE_STRING_1)
        )

        token = self.parser.parse('fn:analyze-string("A1,C15,,D24, X50,", "([A-Z])([0-9]+)")')
        result = token.evaluate(context)
        self.assertIsInstance(result, ElementNode)
        root = result.elem
        self.assertEqual(len(root), 8)
        self.assertEqual(
            ElementTree.tostring(root, encoding='utf-8').decode('utf-8'),
            re.sub(r'\n\s*', '', ANALYZE_STRING_2)
        )

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

        context.item = ElementNode(self.etree.XML('<root/>'))
        self.assertFalse(self.parser.parse('has-children()').evaluate(context))
        self.assertFalse(self.parser.parse('has-children(.)').evaluate(context))

        context.variables['elem'] = ElementNode(self.etree.XML('<a><b1/><b2/></a>'))
        self.assertTrue(self.parser.parse('has-children($elem)').evaluate(context))
        self.assertFalse(self.parser.parse('has-children($elem/b1)').evaluate(context))

        expression = 'has-children($elem/b1)'
        token = self.parser.parse(expression)
        self.assertEqual(token.source, expression)
        self.assertEqual(
            repr(token), f'<XPathFunction fn:has-children at {hex(id(token))}>'
        )
        self.assertEqual(str(token), "'fn:has-children' function")

    def test_innermost_function(self):
        with self.assertRaises(MissingContextError):
            self.parser.parse('fn:innermost(A)').evaluate()

        root = self.etree.XML('<a/>')
        document = self.etree.ElementTree(root)
        context = XPathContext(root=document)
        nodes = self.parser.parse('fn:innermost(.)').evaluate(context)
        self.assertIsInstance(nodes, list)
        self.assertEqual(len(nodes), 1)
        self.assertIs(nodes[0], context.root)

        context = XPathContext(root=root)
        nodes = self.parser.parse('fn:innermost(.)').evaluate(context)
        self.assertIsInstance(nodes, list)
        self.assertEqual(len(nodes), 1)
        self.assertIs(nodes[0], context.root)

        context = XPathContext(root=document, variables={'nodes': [root, document]})
        nodes = self.parser.parse('fn:innermost($nodes)').evaluate(context)
        self.assertIsInstance(nodes, list)
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], ElementNode)
        self.assertIs(nodes[0].value, root)

        root = self.etree.XML('<a><b1><c1/></b1><b2/></a>')
        document = self.etree.ElementTree(root)
        context = XPathContext(
            root=document, variables={'nodes': [root, document, root[0], root[0]]}
        )
        nodes = self.parser.parse('fn:innermost($nodes)').evaluate(context)
        self.assertIsInstance(nodes, list)
        self.assertEqual(len(nodes), 1)
        self.assertIs(nodes[0].value, root[0])

        context = XPathContext(
            root=document,
            variables={'nodes': [document, root[0][0], root, document, root[0], root[1]]}
        )
        nodes = self.parser.parse('fn:innermost($nodes)').evaluate(context)
        self.assertIsInstance(nodes, list)
        self.assertEqual(len(nodes), 2)
        self.assertIs(nodes[0].value, root[0][0])
        self.assertIs(nodes[1].value, root[1])

        expression = 'innermost($nodes)'
        token = self.parser.parse(expression)
        self.assertEqual(token.source, expression)
        self.assertEqual(
            repr(token), f'<XPathFunction fn:innermost#1 at {hex(id(token))}>'
        )
        self.assertEqual(str(token), "'fn:innermost' function")

    def test_outermost_function(self):
        with self.assertRaises(MissingContextError):
            self.parser.parse('fn:outermost(A)').evaluate()

        root = self.etree.XML('<a/>')
        document = self.etree.ElementTree(root)
        context = XPathContext(root=document)
        nodes = self.parser.parse('fn:outermost(.)').evaluate(context)
        self.assertIsInstance(nodes, list)
        self.assertEqual(len(nodes), 1)
        self.assertIs(nodes[0], context.root)

        context = XPathContext(root=root)
        nodes = self.parser.parse('fn:outermost(.)').evaluate(context)
        self.assertIsInstance(nodes, list)
        self.assertEqual(len(nodes), 1)
        self.assertIs(nodes[0], context.root)

        context = XPathContext(root=document, variables={'nodes': [root, document]})
        nodes = self.parser.parse('fn:outermost($nodes)').evaluate(context)
        self.assertIsInstance(nodes, list)
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], DocumentNode)
        self.assertIs(nodes[0].value, document)

        root = self.etree.XML('<a><b1><c1/></b1><b2/></a>')
        document = self.etree.ElementTree(root)
        context = XPathContext(
            root=document,
            variables={'nodes': [root, document, root[0], document]}
        )

        nodes = self.parser.parse('fn:outermost($nodes)').evaluate(context)
        self.assertIsInstance(nodes, list)
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], DocumentNode)
        self.assertIs(nodes[0].value, document)

        context = XPathContext(
            root=document,
            variables={'nodes': [document, root[0][0], root, document, root[0], root[1]]}
        )
        nodes = self.parser.parse('fn:outermost($nodes)').evaluate(context)
        self.assertIsInstance(nodes, list)
        self.assertEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], DocumentNode)
        self.assertIs(nodes[0].value, document)

        context = XPathContext(
            root=document, variables={'nodes': [root[0][0], root[1], root[0]]}
        )
        nodes = self.parser.parse('fn:outermost($nodes)').evaluate(context)
        self.assertIsInstance(nodes, list)
        self.assertEqual(len(nodes), 2)
        self.assertIs(nodes[0].value, root[0])
        self.assertIs(nodes[1].value, root[1])

        expression = 'outermost($nodes)'
        token = self.parser.parse(expression)
        self.assertEqual(token.source, expression)
        self.assertEqual(
            repr(token), f'<XPathFunction fn:outermost#1 at {hex(id(token))}>'
        )
        self.assertEqual(str(token), "'fn:outermost' function")

    def test_parse_xml_function(self):
        with self.assertRaises(MissingContextError):
            self.parser.parse('fn:parse-xml("<alpha>abcd</alpha>")').evaluate()

        root = self.etree.XML('<root/>')
        context = XPathContext(root=self.etree.ElementTree(root))

        document = self.parser.parse('fn:parse-xml("<alpha>abcd</alpha>")').evaluate(context)

        self.assertIsInstance(document, DocumentNode)
        self.assertTrue(is_etree_element(document.document.getroot()))
        self.assertEqual(document.document.getroot().tag, 'alpha')
        self.assertEqual(document.document.getroot().text, 'abcd')

        if self.etree is lxml_etree:
            self.assertTrue(is_lxml_etree_document(document.document))
        else:
            self.assertFalse(is_lxml_etree_document(document.document))

        self.assertEqual(document.document.getroot().tag, 'alpha')
        self.assertEqual(document.document.getroot().text, 'abcd')

        self.assertEqual(self.parser.parse('fn:parse-xml(())').evaluate(), [])

        with self.assertRaises(ValueError) as ctx:
            self.parser.parse('fn:parse-xml("<alpha>abcd<alpha>")').evaluate(context)

        self.assertIn('FODC0006', str(ctx.exception))
        self.assertIn('not a well-formed XML document', str(ctx.exception))

        expression = "parse-xml('<alpha>abcd<alpha>')"
        token = self.parser.parse(expression)
        self.assertEqual(token.source, expression)
        self.assertEqual(
            repr(token), f'<XPathFunction fn:parse-xml#1 at {hex(id(token))}>'
        )
        self.assertEqual(str(token), "'fn:parse-xml' function")

    def test_parse_xml_fragment_function(self):
        root = self.etree.XML('<root/>')
        context = XPathContext(root=self.etree.ElementTree(root))

        result = self.parser.parse(
            'fn:parse-xml-fragment("<root><alpha>abcd</alpha><beta>abcd</beta></root>")'
        ).evaluate(context)
        self.assertIsInstance(result, DocumentNode)

        document = result.document
        self.assertTrue(is_etree_element(document.getroot()))
        self.assertEqual(document.getroot().tag, 'root')
        self.assertEqual(document.getroot()[0].tag, 'alpha')
        self.assertEqual(document.getroot()[0].text, 'abcd')
        self.assertEqual(document.getroot()[1].tag, 'beta')
        self.assertEqual(document.getroot()[1].text, 'abcd')

        # Fragments that are not valid formal documents
        result = self.parser.parse(
            'fn:parse-xml-fragment("<alpha>abcd</alpha><beta>abcd</beta>")'
        ).evaluate(context)
        self.assertIsInstance(result, DocumentNode)
        self.assertTrue(result.is_extended())
        self.assertTrue(is_etree_document(result.document))
        self.assertEqual(result[0].elem.tag, 'alpha')
        self.assertEqual(result[0].elem.text, 'abcd')
        self.assertEqual(result[1].elem.tag, 'beta')
        self.assertEqual(result[1].elem.text, 'abcd')

        result = self.parser.parse(
            'fn:parse-xml-fragment("He was <i>so</i> kind")'
        ).evaluate(context)
        self.assertIsInstance(result, DocumentNode)
        if not is_lxml_etree_document(result.document):
            self.assertTrue(result.is_extended())

        self.assertTrue(is_etree_document(result.document))
        self.assertEqual(result[0].value, 'He was ')
        self.assertEqual(result[1].elem.tag, 'i')
        self.assertEqual(result[1].elem.text, 'so')
        self.assertEqual(result[1].elem.tail, ' kind')

        result = self.parser.parse('fn:parse-xml-fragment("")').evaluate(context)
        self.assertTrue(is_etree_document(result.document))
        self.assertEqual(len(result.children), 0)

        result = self.parser.parse('fn:parse-xml-fragment(" ")').evaluate(context)
        self.assertTrue(is_etree_document(result.document))
        self.assertEqual(result[0].value, ' ')

        with self.assertRaises(MissingContextError):
            self.parser.parse(
                'fn:parse-xml(\'<xml version="1.0" encoding="utf8" standalone="yes"?></a>\')'
            ).evaluate()

        root = self.etree.XML('<root/>')
        context = XPathContext(root=self.etree.ElementTree(root))

        with self.assertRaises(ValueError) as ctx:
            self.parser.parse(
                'fn:parse-xml(\'<xml version="1.0" encoding="utf8" standalone="yes"?></a>\')'
            ).evaluate(context)

        self.assertIn('FODC0006', str(ctx.exception))
        self.assertIn('not a well-formed XML document', str(ctx.exception))

        expression = "parse-xml-fragment(' ')"
        token = self.parser.parse(expression)
        self.assertEqual(token.source, expression)
        self.assertEqual(
            repr(token), f'<XPathFunction fn:parse-xml-fragment#1 at {hex(id(token))}>'
        )
        self.assertEqual(str(token), "'fn:parse-xml-fragment' function")

    def test_serialize_function(self):
        root = self.etree.XML('<root/>')
        document = self.etree.ElementTree(root)
        context = XPathContext(
            root=document,
            variables={
                'params': ElementTree.XML(
                    '<output:serialization-parameters '
                    '    xmlns:output="http://www.w3.org/2010/xslt-xquery-serialization">'
                    '  <output:omit-xml-declaration value="yes"/>'
                    '</output:serialization-parameters>'
                 ),
                'data': self.etree.XML("<a b='3'/>")
            }
        )
        result = self.parser.parse('fn:serialize($data, $params)').evaluate(context)
        self.assertEqual(result.replace(' />', '/>'), '<a b="3"/>')

    def test_odd_children_serialization__issue_056(self):
        root = self.etree.XML('<root>This is <b>important</b>.</root>')
        context = XPathContext(root)
        expected = '<root>This is <b>important</b>.</root>'
        self.check_value('fn:serialize(.)', expected, context=context)

        context = XPathContext(root)
        expected = 'This is <b>important</b>.'
        self.check_value('fn:serialize(node())', expected, context=context)

    def test_head_function(self):
        self.assertEqual(self.parser.parse('fn:head(1 to 5)').evaluate(), 1)
        self.assertEqual(self.parser.parse('fn:head(("a", "b", "c"))').evaluate(), 'a')
        self.assertEqual(self.parser.parse('fn:head(())').evaluate(), [])

    def test_tail_function(self):
        self.assertListEqual(self.parser.parse('fn:tail(1 to 5)').evaluate(), [2, 3, 4, 5])
        self.assertListEqual(self.parser.parse('fn:tail(("a", "b", "c"))').evaluate(), ['b', 'c'])
        self.assertListEqual(self.parser.parse('fn:tail(("a"))').evaluate(), [])
        self.assertListEqual(self.parser.parse('fn:tail(())').evaluate(), [])

    def test_generate_id_function(self):
        with self.assertRaises(MissingContextError):
            self.parser.parse('fn:generate-id()').evaluate()

        with self.assertRaises(TypeError) as ctx:
            self.parser.parse('fn:generate-id(1)').evaluate()

        self.assertIn('XPTY0004', str(ctx.exception))
        self.assertIn('argument is not a node', str(ctx.exception))

        root = self.etree.XML('<root/>')
        context = XPathContext(root=root)
        result = self.parser.parse('fn:generate-id()').evaluate(context)
        self.assertEqual(result, 'ID{}'.format(id(context.item)))

        result = self.parser.parse('fn:generate-id(.)').evaluate(context)
        self.assertEqual(result, 'ID{}'.format(id(context.item)))

        context.item = 1
        with self.assertRaises(TypeError) as ctx:
            self.parser.parse('fn:generate-id()').evaluate(context)

        self.assertIn('XPTY0004', str(ctx.exception))
        self.assertIn('context item is not a node', str(ctx.exception))

    def test_unparsed_text_function(self):
        with self.assertRaises(ValueError) as ctx:
            self.parser.parse('fn:unparsed-text("alpha#fragment")').evaluate()
        self.assertIn('FOUT1170', str(ctx.exception))

        self.assertEqual(self.parser.parse('fn:unparsed-text(())').evaluate(), [])

        if platform.system() != 'Windows':
            filepath = pathlib.Path(__file__).absolute().parent.joinpath('resources/sample.xml')
            file_lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<root>abc àèéìù</root>']

            # Checks before that the resource text file is accessible and its content is as expected
            with filepath.open() as fp:
                text = fp.read()
            self.assertListEqual([x.strip() for x in text.strip().split('\n')], file_lines)

            path = 'fn:unparsed-text("file://{}")'.format(str(filepath))
            text = self.parser.parse(path).evaluate()
            self.assertListEqual([x.strip() for x in text.strip().split('\n')], file_lines)

            path = 'fn:unparsed-text("file://{}", "unknown")'.format(str(filepath))
            with self.assertRaises(ValueError) as ctx:
                self.parser.parse(path).evaluate()
            self.assertIn('FOUT1190', str(ctx.exception))

    def test_environment_variable_function(self):
        with self.assertRaises(MissingContextError):
            self.parser.parse('fn:environment-variable("PATH")').evaluate()

        root = self.etree.XML('<root/>')
        context = XPathContext(root=root)
        path = 'fn:environment-variable("PATH")'
        self.assertEqual(self.parser.parse(path).evaluate(context), [])
        context = XPathContext(root=root, allow_environment=True)

        try:
            key = list(os.environ)[0]
        except IndexError:
            pass
        else:
            path = 'fn:environment-variable("{}")'.format(key)
            self.assertEqual(self.parser.parse(path).evaluate(context), os.environ[key])

    def test_available_environment_variables_function(self):
        with self.assertRaises(MissingContextError):
            self.parser.parse('fn:available-environment-variables()').evaluate()

        root = self.etree.XML('<root/>')
        context = XPathContext(root=root)
        path = 'fn:available-environment-variables()'
        self.assertEqual(self.parser.parse(path).evaluate(context), [])
        context = XPathContext(root=root, allow_environment=True)
        self.assertListEqual(self.parser.parse(path).evaluate(context), list(os.environ))

    def test_inline_function_expression(self):
        expression = "function() as xs:integer+ {2, 3, 5, 7, 11, 13}"
        token = self.parser.parse(expression)
        with self.assertRaises(MissingContextError):
            token.evaluate()

        self.assertEqual(token.source, expression)
        self.assertEqual(
            repr(token), f'<_InlineFunction object at {hex(id(token))}>'
        )
        self.assertEqual(str(token), "inline function")

        root = self.etree.XML('<root/>')
        context = XPathContext(root=root, variables={'a': 9.0, 'b': 3.0})
        self.assertListEqual(token(context=context), [2, 3, 5, 7, 11, 13])

        expression = "function($a as xs:double, $b as xs:double) " \
                     "as xs:double {$a * $b} (9.0, 3.0)"
        token = self.parser.parse(expression)
        with self.assertRaises(MissingContextError):
            token.evaluate()

        self.assertEqual(token.source, expression.replace('} (', '}('))

        root = self.etree.XML('<root/>')
        context = XPathContext(root=root)
        self.assertAlmostEqual(token.evaluate(context), 27.0)

        token = self.parser.parse("function($a) { $a } (10)")
        with self.assertRaises(MissingContextError):
            token.evaluate()
        self.assertEqual(token.evaluate(context), 10)

    def test_function_lookup(self):
        expression = "fn:function-lookup(xs:QName('fn:substring'), 2)('abcd', 2)"
        token = self.parser.parse(expression)
        self.assertEqual(token.evaluate(), "bcd")
        self.assertEqual(token.source, expression)
        self.assertEqual(
            repr(token[0][1]), f'<XPathFunction fn:function-lookup#2 at {hex(id(token[0][1]))}>'
        )
        self.assertEqual(str(token[0][1]), "'fn:function-lookup' function")

        with self.xsd_version_parser('1.1'):
            token = self.parser.parse("(fn:function-lookup(xs:QName('xs:dateTimeStamp'), 1), "
                                      "xs:dateTime#1)[1] ('2011-11-11T11:11:11Z')")

            with self.assertRaises(MissingContextError):
                token.evaluate()  # Context is required by predicate selector [1]

            root = self.etree.XML('<root/>')
            context = XPathContext(root=root)
            dts = datatypes.DateTimeStamp.fromstring('2011-11-11T11:11:11Z')
            self.assertEqual(token.evaluate(context), dts)

    def test_function_name(self):
        token = self.parser.parse("fn:function-name(fn:substring#2) ")
        result = datatypes.QName("http://www.w3.org/2005/xpath-functions", "fn:substring")
        self.assertEqual(token.evaluate(), result)

        expression = "fn:function-name(function($node) {count($node/*)})"
        token = self.parser.parse(expression)
        self.assertEqual(token.source, expression)
        self.assertEqual(
            repr(token[1]), f'<XPathFunction fn:function-name#1 at {hex(id(token[1]))}>'
        )
        self.assertEqual(str(token[1]), "'fn:function-name' function")

        # Context is not used if the argument is a function
        self.assertEqual(token.evaluate(), [])
        root = self.etree.XML('<root><c1/><c2/><c3/></root>')
        context = XPathContext(root=root, variables={'node': root})
        self.assertEqual(token.evaluate(context), [])

    def test_function_arity(self):
        token = self.parser.parse("fn:function-arity(fn:substring#2)")
        self.assertEqual(token.evaluate(), 2)

        expression = "fn:function-arity(function($node) {name($node)})"
        token = self.parser.parse(expression)
        self.assertEqual(token.source, expression)
        self.assertEqual(
            repr(token[1]), f'<XPathFunction fn:function-arity#1 at {hex(id(token[1]))}>'
        )
        self.assertEqual(str(token[1]), "'fn:function-arity' function")

        # Context is not used if the argument is a function
        self.assertEqual(token.evaluate(), 1)
        root = self.etree.XML('<root/>')
        context = XPathContext(root=root, variables={'node': root})
        self.assertEqual(token.evaluate(context), 1)

    def test_for_each(self):
        expression = 'fn:for-each(1 to 5, function($a) {$a * $a})'
        token = self.parser.parse(expression)
        self.assertEqual(token.source, expression)
        self.assertEqual(
            repr(token[1]), f'<XPathFunction fn:for-each#2 at {hex(id(token[1]))}>'
        )
        self.assertEqual(str(token[1]), "'fn:for-each' function")

        with self.assertRaises(MissingContextError):
            token.evaluate()

        root = self.etree.XML('<root/>')
        context = XPathContext(root=root)
        self.assertListEqual(token.evaluate(context), [1, 4, 9, 16, 25])

        token = self.parser.parse('fn:for-each(("john", "jane"), fn:string-to-codepoints#1)')
        self.assertListEqual(token.evaluate(context), [106, 111, 104, 110, 106, 97, 110, 101])

        token = self.parser.parse('fn:for-each(("23", "29"), xs:int#1)')
        self.assertListEqual(token.evaluate(context), [23, 29])

    def test_filter(self):
        expression = 'fn:filter(1 to 10, function($a) {$a mod 2 = 0})'
        token = self.parser.parse(expression)
        self.assertEqual(token.source, expression)
        self.assertEqual(
            repr(token[1]), f'<XPathFunction fn:filter#2 at {hex(id(token[1]))}>'
        )
        self.assertEqual(str(token[1]), "'fn:filter' function")

        with self.assertRaises(MissingContextError):
            token.evaluate()

        root = self.etree.XML('<root/>')
        context = XPathContext(root=root)
        self.assertListEqual(token.evaluate(context), [2, 4, 6, 8, 10])

    def test_fold_left(self):
        expression = 'fn:fold-left(1 to 5, 0, function($a, $b) {$a + $b})'
        token = self.parser.parse(expression)
        self.assertEqual(token.source, expression)
        self.assertEqual(
            repr(token[1]), f'<XPathFunction fn:fold-left#3 at {hex(id(token[1]))}>'
        )
        self.assertEqual(str(token[1]), "'fn:fold-left' function")

        with self.assertRaises(MissingContextError):
            token.evaluate()

        root = self.etree.XML('<root/>')
        context = XPathContext(root=root)
        self.assertListEqual(token.evaluate(context), [15])

        token = self.parser.parse('fn:fold-left((2,3,5,7), 1, function($a, $b) { $a * $b })')
        self.assertListEqual(token.evaluate(context), [210])

        token = self.parser.parse(
            'fn:fold-left((true(), false(), false()), false(), function($a, $b) { $a or $b })')
        self.assertListEqual(token.evaluate(context), [True])

        token = self.parser.parse(
            'fn:fold-left((true(), false(), false()), false(), function($a, $b) { $a and $b })')
        self.assertListEqual(token.evaluate(context), [False])

        token = self.parser.parse(
            'fn:fold-left(1 to 5, (), function($a, $b) {($b, $a)})')
        self.assertListEqual(token.evaluate(context), [5, 4, 3, 2, 1])

        token = self.parser.parse(
            'fn:fold-left(1 to 5, "", fn:concat(?, ".", ?))')
        self.assertListEqual(token.evaluate(context), [".1.2.3.4.5"])

        token = self.parser.parse(
            'fn:fold-left(1 to 5, "$zero", fn:concat("$f(", ?, ", ", ?, ")"))')
        self.assertListEqual(token.evaluate(context), ["$f($f($f($f($f($zero, 1), 2), 3), 4), 5)"])

    def test_fold_right(self):
        expression = 'fn:fold-right(1 to 5, 0, function($a, $b) {$a + $b})'
        token = self.parser.parse(expression)
        self.assertEqual(token.source, expression)
        self.assertEqual(
            repr(token[1]), f'<XPathFunction fn:fold-right#3 at {hex(id(token[1]))}>'
        )
        self.assertEqual(str(token[1]), "'fn:fold-right' function")

        with self.assertRaises(MissingContextError):
            token.evaluate()

        root = self.etree.XML('<root/>')
        context = XPathContext(root=root)
        self.assertListEqual(token.evaluate(context), [15])

        token = self.parser.parse('fn:fold-right(1 to 5, "", fn:concat(?, ".", ?))')
        self.assertListEqual(token.evaluate(context), ["1.2.3.4.5."])

        token = self.parser.parse(
            'fn:fold-right(1 to 5, "$zero", concat("$f(", ?, ", ", ?, ")"))')
        self.assertListEqual(token.evaluate(context), ["$f(1, $f(2, $f(3, $f(4, $f(5, $zero)))))"])

    def test_for_each_pair(self):
        expression = 'fn:for-each-pair(("a", "b", "c"), ("x", "y", "z"), concat#2)'
        token = self.parser.parse(expression)
        self.assertEqual(token.source, expression.replace('"', "'"))
        self.assertEqual(
            repr(token[1]), f'<XPathFunction fn:for-each-pair#3 at {hex(id(token[1]))}>'
        )
        self.assertEqual(str(token[1]), "'fn:for-each-pair' function")
        self.assertListEqual(token.evaluate(), ["ax", "by", "cz"])

        token = self.parser.parse('fn:for-each-pair(1 to 5, 1 to 5, function($a, $b){10*$a + $b})')

        with self.assertRaises(MissingContextError):
            token.evaluate()

        root = self.etree.XML('<root/>')
        context = XPathContext(root=root)
        self.assertListEqual(token.evaluate(context), [11, 22, 33, 44, 55])

    def test_format_integer(self):
        self.check_value("format-integer(57, 'I')", 'LVII')
        self.check_value("format-integer(594, 'i')", 'dxciv')

        self.check_value("format-integer(7, 'a')", 'g')
        self.check_value("format-integer(-90956, 'A')", '-EDNH')

        self.check_value("format-integer(123, 'w')",
                         'one hundred and twenty-three')
        self.check_value("format-integer(-8912, 'W')",
                         "-EIGHT THOUSAND NINE HUNDRED AND TWELVE")
        self.check_value("format-integer(17089674, 'Ww')",
                         "Seventeen Million Eighty-Nine Thousand Six Hundred And Seventy-Four")

        self.check_value("format-integer(123, '0000')", '0123')
        self.check_source("format-integer(-8912, 'W')")

    def test_path_function__issue_067(self):
        xml_sample = dedent("""
            <root>
                <item>
                    <name>item 1</name>
                    <value>value 1</value>
                </item>
            </root>""")

        root = self.etree.parse(io.StringIO(xml_sample))
        paths = select(root, '//*/path()', parser=self.parser.__class__)
        expected = [
            '/Q{}root[1]',
            '/Q{}root[1]/Q{}item[1]',
            '/Q{}root[1]/Q{}item[1]/Q{}name[1]',
            '/Q{}root[1]/Q{}item[1]/Q{}value[1]'
        ]
        self.assertListEqual(paths, expected)

        root = self.etree.XML(xml_sample)
        paths = select(root, '//*/path()', parser=self.parser.__class__)

        expected = [
            'Q{http://www.w3.org/2005/xpath-functions}root()',
            'Q{http://www.w3.org/2005/xpath-functions}root()/Q{}item[1]',
            'Q{http://www.w3.org/2005/xpath-functions}root()/Q{}item[1]/Q{}name[1]',
            'Q{http://www.w3.org/2005/xpath-functions}root()/Q{}item[1]/Q{}value[1]'
        ]
        self.assertListEqual(paths, expected)

    def test_path_function_with_namespaces(self):
        xml_sample = dedent("""
            <tns:root xmlns:tns="http://xpath.test/ns">
                <item>
                    <name>item 1</name>
                    <foo:value xmlns:foo="bar">value 1</foo:value>
                </item>
            </tns:root>""")

        root = self.etree.parse(io.StringIO(xml_sample))
        paths = select(root, '//*/path()', parser=self.parser.__class__)
        expected = [
            '/Q{http://xpath.test/ns}root[1]',
            '/Q{http://xpath.test/ns}root[1]/Q{}item[1]',
            '/Q{http://xpath.test/ns}root[1]/Q{}item[1]/Q{}name[1]',
            '/Q{http://xpath.test/ns}root[1]/Q{}item[1]/Q{bar}value[1]'
        ]
        self.assertListEqual(paths, expected)

        root = self.etree.XML(xml_sample)
        paths = select(root, '//*/path()', parser=self.parser.__class__)

        expected = [
            'Q{http://www.w3.org/2005/xpath-functions}root()',
            'Q{http://www.w3.org/2005/xpath-functions}root()/Q{}item[1]',
            'Q{http://www.w3.org/2005/xpath-functions}root()/Q{}item[1]/Q{}name[1]',
            'Q{http://www.w3.org/2005/xpath-functions}root()/Q{}item[1]/Q{bar}value[1]'
        ]
        self.assertListEqual(paths, expected)

    def test_path_function_with_same_child(self):
        xml_sample = dedent("""
            <tns:root xmlns:tns="http://xpath.test/ns">
                <item>
                    <name>item 1</name>
                    <value>value 1</value>
                    <name>item 2</name>
                    <name>item 3</name>
                </item>
                <item2/>
                <item/>
            </tns:root>""")

        root = self.etree.parse(io.StringIO(xml_sample))
        paths = select(root, '//*/path()', parser=self.parser.__class__)
        expected = [
            '/Q{http://xpath.test/ns}root[1]',
            '/Q{http://xpath.test/ns}root[1]/Q{}item[1]',
            '/Q{http://xpath.test/ns}root[1]/Q{}item[1]/Q{}name[1]',
            '/Q{http://xpath.test/ns}root[1]/Q{}item[1]/Q{}value[1]',
            '/Q{http://xpath.test/ns}root[1]/Q{}item[1]/Q{}name[2]',
            '/Q{http://xpath.test/ns}root[1]/Q{}item[1]/Q{}name[3]',
            '/Q{http://xpath.test/ns}root[1]/Q{}item2[1]',
            '/Q{http://xpath.test/ns}root[1]/Q{}item[2]',
        ]
        self.assertListEqual(paths, expected)


@unittest.skipIf(lxml_etree is None, "The lxml library is not installed")
class LxmlXPath30FunctionsTest(XPath30FunctionsTest):
    etree = lxml_etree


class XPath30ConstructorsTest(test_xpath2_constructors.XPath2ConstructorsTest):
    def setUp(self):
        self.parser = XPath30Parser(namespaces=self.namespaces)


@unittest.skipIf(lxml_etree is None, "The lxml library is not installed")
class LxmlXPath30ConstructorsTest(XPath30ConstructorsTest):
    etree = lxml_etree


if __name__ == '__main__':
    unittest.main()
