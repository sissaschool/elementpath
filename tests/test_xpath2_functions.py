#!/usr/bin/env python
#
# Copyright (c), 2018-2021, SISSA (International School for Advanced Studies).
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
#           http://www.w3.org/TR/1999/REC-xpath-19991116/
#           http://www.w3.org/TR/2010/REC-xpath20-20101214/
#           http://www.w3.org/TR/2010/REC-xpath-functions-20101214/
#           https://www.w3.org/Consortium/Legal/2015/doc-license
#           https://www.w3.org/TR/charmod-norm/
#
import unittest
import datetime
import io
import locale
import math
import os
import platform
import time
from textwrap import dedent
from decimal import Decimal

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
from elementpath.namespaces import XSI_NAMESPACE, XML_NAMESPACE, XML_ID
from elementpath.datatypes import DateTime10, DateTime, Date10, Date, Time, \
    Timezone, DayTimeDuration, YearMonthDuration, QName, UntypedAtomic
from elementpath.xpath_token import UNICODE_CODEPOINT_COLLATION

try:
    from tests import test_xpath1_parser
except ImportError:
    import test_xpath1_parser

XML_GENERIC_TEST = test_xpath1_parser.XML_GENERIC_TEST

XML_POEM_TEST = """<poem author="Wilhelm Busch">
Kaum hat dies der Hahn gesehen,
Fängt er auch schon an zu krähen:
«Kikeriki! Kikikerikih!!»
Tak, tak, tak! - da kommen sie.
</poem>"""

try:
    from tests import xpath_test_class
except ImportError:
    import xpath_test_class


class XPath2FunctionsTest(xpath_test_class.XPathTestCase):

    def setUp(self):
        self.parser = XPath2Parser(namespaces=self.namespaces)

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

    def test_boolean_function(self):
        root = self.etree.XML('<A><B1/><B2/><B3/></A>')
        self.check_selector("boolean(/A)", root, True)
        self.check_selector("boolean((-10, 35))", root, TypeError)  # Sequence with 2 numeric values
        self.check_selector("boolean((/A, 35))", root, True)

    def test_abs_function(self):
        # Test cases taken from https://www.w3.org/TR/xquery-operators/#numeric-value-functions
        self.check_value("abs(10.5)", 10.5)
        self.check_value("abs(-10.5)", 10.5)
        self.check_value("abs(())")

        root = self.etree.XML('<root>-10</root>')
        context = XPathContext(root, item=float('nan'))
        self.check_value("abs(.)", float('nan'), context=context)

        context = XPathContext(root)
        self.check_value("abs(.)", 10, context=context)
        context = XPathContext(root=self.etree.XML('<root>foo</root>'))

        self.wrong_type('abs("10")', 'XPTY0004', 'invalid argument type')

        with self.assertRaises(ValueError) as err:
            self.check_value("abs(.)", 10, context=context)
        self.assertIn('FOCA0002', str(err.exception))
        self.assertIn('invalid string value', str(err.exception))

    def test_round_half_to_even_function(self):
        self.check_value("round-half-to-even(())")
        self.check_value("round-half-to-even(0.5)", 0)
        self.check_value("round-half-to-even(1)", 1)
        self.check_value("round-half-to-even(1.5)", 2)
        self.check_value("round-half-to-even(2.5)", 2)
        self.check_value("round-half-to-even(xs:float(2.5))", 2)
        self.check_value("round-half-to-even(3.567812E+3, 2)", 3567.81E0)
        self.check_value("round-half-to-even(4.7564E-3, 2)", 0.0E0)
        self.check_value("round-half-to-even(35612.25, -2)", 35600)
        self.wrong_type('round-half-to-even(3.5, "2")', 'XPTY0004')
        self.check_value('fn:round-half-to-even(xs:double("1.0E300"))', 1.0E300)
        self.check_value('fn:round-half-to-even(4.8712122, 8328782878)', 4.8712122)

        root = self.etree.XML('<root/>')
        context = XPathContext(root, item=float('nan'))
        self.check_value("round-half-to-even(.)", float('nan'), context=context)

        self.wrong_type('round-half-to-even("wrong")', 'XPTY0004', 'invalid argument type')

    def test_sum_function(self):
        self.check_value("sum((10, 15, 6, -2))", 29)

    def test_avg_function(self):
        context = XPathContext(root=self.etree.XML('<A/>'),
                               variables={
                                   'd1': YearMonthDuration.fromstring("P20Y"),
                                   'd2': YearMonthDuration.fromstring("P10M"),
                                   'seq3': [3, 4, 5]
                               })
        self.check_value("fn:avg($seq3)", 4.0, context=context)
        self.check_value("fn:avg(($d1, $d2))", YearMonthDuration.fromstring("P125M"),
                         context=context)
        root_token = self.parser.parse("fn:avg(($d1, $seq3))")
        self.assertRaises(TypeError, root_token.evaluate, context=context)
        self.check_value("fn:avg(())")
        self.wrong_type("fn:avg('10')", 'FORG0006')
        self.check_value("fn:avg($seq3)", 4.0, context=context)
        self.check_value('avg((xs:float(1), xs:untypedAtomic(2), xs:integer(0)))', 1)
        self.check_value('avg((1.0, 2.0, 3.0))', 2)
        self.wrong_type('avg((xs:float(1), true(), xs:integer(0)))', 'FORG0006')
        self.wrong_type('avg((xs:untypedAtomic(3), xs:integer(3), "three"))',
                        'FORG0006', 'unsupported operand')

        root_token = self.parser.parse("fn:avg((xs:float('INF'), xs:float('-INF')))")
        self.assertTrue(math.isnan(root_token.evaluate(context)))

        root_token = self.parser.parse("fn:avg(($seq3, xs:float('NaN')))")
        self.assertTrue(math.isnan(root_token.evaluate(context)))

        root = self.etree.XML('<a><b>1</b><b>9</b></a>')
        self.check_selector('avg(/a/b/number(text()))', root, 5)

    def test_max_function(self):
        self.check_value("fn:max(())", [])
        self.check_value("fn:max((3,4,5))", 5)
        self.check_value("fn:max((3, 4, xs:float('NaN')))", float('nan'))
        self.check_value("fn:max((3,4,5), 'en_US.UTF-8')", 5)
        self.check_value("fn:max((5, 5.0e0))", 5.0e0)
        self.check_value("fn:max((xs:float(1.0E0), xs:double(15.0)))", 15.0)
        self.wrong_type("fn:max((3,4,'Zero'))")
        dt = datetime.datetime.now()
        self.check_value('fn:max((fn:current-date(), xs:date("2001-01-01")))',
                         Date(dt.year, dt.month, dt.day, tzinfo=dt.tzinfo))
        self.check_value('fn:max(("a", "b", "c"))', 'c')

        root = self.etree.XML('<a><b>1</b><b>9</b></a>')
        self.check_selector('max(/a/b/number(text()))', root, 9)
        self.check_selector('max(/a/b)', root, 9)

        self.check_value(
            'max((xs:anyURI("http://xpath.test/ns0"), xs:anyURI("http://xpath.test/ns1")))',
            datatypes.AnyURI("http://xpath.test/ns1")
        )
        self.check_value('max((xs:dayTimeDuration("P1D"), xs:dayTimeDuration("P2D")))',
                         datatypes.DayTimeDuration(seconds=3600 * 48))
        self.wrong_type('max(QName("http://xpath.test/ns", "foo"))',
                        'FORG0006', 'xs:QName is not an ordered type')
        self.wrong_type('max(xs:duration("P1Y"))', 'FORG0006',
                        'xs:duration is not an ordered type')

    def test_min_function(self):
        self.check_value("fn:min(())", [])
        self.check_value("fn:min((3,4,5))", 3)
        self.check_value("fn:min((3, 4, xs:float('NaN')))", float('nan'))
        self.check_value("fn:min((5, 5.0e0))", 5.0e0)
        self.check_value("fn:min((xs:float(0.0E0), xs:float(-0.0E0)))", 0.0)
        self.check_value("fn:min((xs:float(1.0E0), xs:double(15.0)))", 1.0)
        self.check_value('fn:min((fn:current-date(), xs:date("2001-01-01")))',
                         Date.fromstring("2001-01-01"))
        self.check_value('fn:min(("a", "b", "c"))', 'a')

        root = self.etree.XML('<a><b>1</b><b>9</b></a>')
        self.check_selector('min(/a/b/number(text()))', root, 1)
        self.check_selector('min(/a/b)', root, 1)

        self.check_value(
            'min((xs:anyURI("http://xpath.test/ns0"), xs:anyURI("http://xpath.test/ns1")))',
            datatypes.AnyURI("http://xpath.test/ns0")
        )
        self.check_value('min((xs:dayTimeDuration("P1D"), xs:dayTimeDuration("P2D")))',
                         datatypes.DayTimeDuration(seconds=3600 * 24))
        self.wrong_type('min(QName("http://xpath.test/ns", "foo"))', 'FORG0006')
        self.wrong_type('min(xs:duration("P1Y"))', 'FORG0006')

    ###
    # Functions on strings
    def test_codepoints_to_string_function(self):
        self.check_value("codepoints-to-string((2309, 2358, 2378, 2325))", 'अशॊक')
        self.check_value("codepoints-to-string(2309)", 'अ')
        self.wrong_value("codepoints-to-string((55296))", 'FOCH0001')
        self.wrong_type("codepoints-to-string(('z'))", 'XPTY0004')
        self.wrong_type("codepoints-to-string((2309.1))", 'FORG0006')

    def test_string_to_codepoints_function(self):
        self.check_value('string-to-codepoints("Thérèse")', [84, 104, 233, 114, 232, 115, 101])
        self.check_value('string-to-codepoints(())')
        self.wrong_type('string-to-codepoints(84)', 'XPTY0004')
        self.check_value('string-to-codepoints(("Thérèse"))', [84, 104, 233, 114, 232, 115, 101])
        self.wrong_type('string-to-codepoints(("Thér", "èse"))', 'XPTY0004')

    def test_codepoint_equal_function(self):
        self.check_value("fn:codepoint-equal('abc', 'abc')", True)
        self.check_value("fn:codepoint-equal('abc', 'abcd')", False)
        self.check_value("fn:codepoint-equal('', '')", True)
        self.check_value("fn:codepoint-equal((), 'abc')")
        self.check_value("fn:codepoint-equal('abc', ())")
        self.check_value("fn:codepoint-equal((), ())")

    def test_compare_function(self):
        env_locale_setting = locale.getlocale(locale.LC_COLLATE)

        locale.setlocale(locale.LC_COLLATE, 'C')
        try:
            self.assertEqual(locale.getlocale(locale.LC_COLLATE), (None, None))

            self.check_value("fn:compare('abc', 'abc')", 0)
            self.check_value("fn:compare('abc', 'abd')", -1)
            self.check_value("fn:compare('abc', 'abb')", 1)
            self.check_value("fn:compare('foo bar', 'foo bar')", 0)
            self.check_value("fn:compare('', '')", 0)
            self.check_value("fn:compare('abc', 'abcd')", -1)
            self.check_value("fn:compare('', ' foo bar')", -1)
            self.check_value("fn:compare('abcd', 'abc')", 1)
            self.check_value("fn:compare('foo bar', '')", 1)

            self.check_value('fn:compare("a","A")', 1)
            self.check_value('fn:compare("A","a")', -1)
            self.check_value('fn:compare("+++","++")', 1)
            self.check_value('fn:compare("1234","123")', 1)

            self.check_value("fn:count(fn:compare((), ''))", 0)
            self.check_value("fn:count(fn:compare('abc', ()))", 0)

            self.check_value("compare(xs:anyURI('http://example.com/'), 'http://example.com/')", 0)
            self.check_value(
                "compare(xs:untypedAtomic('http://example.com/'), 'http://example.com/')", 0
            )

            self.check_value('compare("&#65537;", "&#65538;", '
                             '"http://www.w3.org/2005/xpath-functions/collation/codepoint")', -1)

            self.check_value('compare("&#65537;", "&#65520;", '
                             '"http://www.w3.org/2005/xpath-functions/collation/codepoint")', 1)

            # Issue #17
            self.check_value("fn:compare('Strassen', 'Straße')", -1)

            if platform.system() != 'Linux':
                return

            locale.setlocale(locale.LC_COLLATE, 'en_US.UTF-8')
            self.check_value("fn:compare('Strasse', 'Straße')", -1)
            self.check_value("fn:compare('Strassen', 'Straße')", 1)

            try:
                self.check_value("fn:compare('Strasse', 'Straße', 'it_IT.UTF-8')", -1)
                self.check_value("fn:compare('Strassen', 'Straße')", 1)
            except locale.Error:
                pass  # Skip test if 'it_IT.UTF-8' is an unknown locale setting

            try:
                self.check_value("fn:compare('Strasse', 'Straße', 'de_DE.UTF-8')", -1)
            except locale.Error:
                pass  # Skip test if 'de_DE.UTF-8' is an unknown locale setting

            try:
                self.check_value("fn:compare('Strasse', 'Straße', 'deutsch')", -1)
            except locale.Error:
                pass  # Skip test if 'deutsch' is an unknown locale setting

            with self.assertRaises(locale.Error) as cm:
                self.check_value("fn:compare('Strasse', 'Straße', 'invalid_collation')")
            self.assertIn('FOCH0002', str(cm.exception))

            self.wrong_type("fn:compare('Strasse', 111)", 'XPTY0004')
            self.wrong_type('fn:compare("1234", 1234)', 'XPTY0004')

        finally:
            locale.setlocale(locale.LC_COLLATE, env_locale_setting)

    def test_normalize_unicode_function(self):
        self.check_value('fn:normalize-unicode(())', '')
        self.check_value('fn:normalize-unicode("menù")', 'menù')
        self.wrong_type('fn:normalize-unicode(xs:hexBinary("84"))', 'XPTY0004')

        self.assertRaises(ElementPathValueError, self.parser.parse,
                          'fn:normalize-unicode("à", "FULLY-NORMALIZED")')
        self.check_value('fn:normalize-unicode("à", "")', 'à')
        self.wrong_value('fn:normalize-unicode("à", "UNKNOWN")')
        self.wrong_type('fn:normalize-unicode("à", ())', 'XPTY0004', "can't be an empty sequence")

        # https://www.w3.org/TR/charmod-norm/#normalization_forms
        self.check_value("fn:normalize-unicode('\u01FA')", '\u01FA')
        self.check_value("fn:normalize-unicode('\u01FA', 'NFD')", '\u0041\u030A\u0301')
        self.check_value("fn:normalize-unicode('\u01FA', 'NFKC')", '\u01FA')
        self.check_value("fn:normalize-unicode('\u01FA', 'NFKD')", '\u0041\u030A\u0301')

        self.check_value("fn:normalize-unicode('\u00C5\u0301')", '\u01FA')
        self.check_value("fn:normalize-unicode('\u00C5\u0301', 'NFD')", '\u0041\u030A\u0301')
        self.check_value("fn:normalize-unicode('\u00C5\u0301', 'NFKC')", '\u01FA')
        self.check_value("fn:normalize-unicode('\u00C5\u0301', ' nfkd ')", '\u0041\u030A\u0301')

        self.check_value("fn:normalize-unicode('\u212B\u0301')", '\u01FA')
        self.check_value("fn:normalize-unicode('\u212B\u0301', 'NFD')", '\u0041\u030A\u0301')
        self.check_value("fn:normalize-unicode('\u212B\u0301', 'NFKC')", '\u01FA')
        self.check_value("fn:normalize-unicode('\u212B\u0301', 'NFKD')", '\u0041\u030A\u0301')

        self.check_value("fn:normalize-unicode('\u0041\u030A\u0301')", '\u01FA')
        self.check_value("fn:normalize-unicode('\u0041\u030A\u0301', 'NFD')",
                         '\u0041\u030A\u0301')
        self.check_value("fn:normalize-unicode('\u0041\u030A\u0301', 'NFKC')", '\u01FA')
        self.check_value("fn:normalize-unicode('\u0041\u030A\u0301', 'NFKD')", '\u0041\u030A\u0301')

        self.check_value("fn:normalize-unicode('\uFF21\u030A\u0301')", '\uFF21\u030A\u0301')
        self.check_value("fn:normalize-unicode('\uFF21\u030A\u0301', 'NFD')",
                         '\uFF21\u030A\u0301')
        self.check_value("fn:normalize-unicode('\uFF21\u030A\u0301', 'NFKC')", '\u01FA')
        self.check_value("fn:normalize-unicode('\uFF21\u030A\u0301', 'NFKD')",
                         '\u0041\u030A\u0301')

    def test_count_function(self):
        self.check_value("fn:count('')", 1)
        self.check_value("count('')", 1)
        self.check_value("fn:count('abc')", 1)
        self.check_value("fn:count(7)", 1)
        self.check_value("fn:count(())", 0)
        self.check_value("fn:count((1, 2, 3))", 3)
        self.check_value("fn:count((1, 2, ()))", 2)
        self.check_value("fn:count((((()))))", 0)
        self.check_value("fn:count((((), (), ()), (), (), (), ()))", 0)
        self.check_value('fn:count((1, 2 to ()))', 1)
        self.check_value("count(('1', (2, ())))", 2)
        self.check_value("count(('1', (2, '3')))", 3)
        self.check_value("count(1 to 5)", 5)
        self.check_value("count(reverse((1, 2, 3, 4)))", 4)

        root = self.etree.XML('<root/>')
        self.check_selector("count(5)", root, 1)
        self.check_value("count((0, 1, 2 + 1, 3 - 1))", 4)

        self.check_value('fn:count((xs:decimal("-999999999999999999")))', 1)
        self.check_value('fn:count((xs:float("0")))', 1)

        self.check_value("count(//*[@name='John Doe'])", MissingContextError)
        context = XPathContext(self.etree.XML('<root/>'))
        self.check_value("count(//*[@name='John Doe'])", 0, context)

        with self.assertRaises(TypeError) as cm:
            self.check_value("fn:count()")
        self.assertIn('XPST0017', str(cm.exception))

        with self.assertRaises(TypeError) as cm:
            self.check_value("fn:count(1, ())")
        self.assertIn('XPST0017', str(cm.exception))

        with self.assertRaises(TypeError) as cm:
            self.check_value("fn:count(1, 2)")
        self.assertIn('XPST0017', str(cm.exception))

    def test_lower_case_function(self):
        self.check_value('lower-case("aBcDe01")', 'abcde01')
        self.check_value('lower-case(("aBcDe01"))', 'abcde01')
        self.check_value('lower-case(())', '')
        self.wrong_type('lower-case((10))')

        root = self.etree.XML(XML_GENERIC_TEST)
        self.check_selector("a[lower-case(@id) = 'a_id']", root, [root[0]])
        self.check_selector("a[lower-case(@id) = 'a_i']", root, [])
        self.check_selector("//b[lower-case(.) = 'some content']", root, [root[0][0]])
        self.check_selector("//b[lower-case((.)) = 'some content']", root, [root[0][0]])
        self.check_selector("//none[lower-case((.)) = 'some content']", root, [])

    def test_upper_case_function(self):
        self.check_value('upper-case("aBcDe01")', 'ABCDE01')
        self.check_value('upper-case(("aBcDe01"))', 'ABCDE01')
        self.check_value('upper-case(())', '')
        self.wrong_type('upper-case((10))', 'XPTY0004', "1st argument is <class 'int'>")

        root = self.etree.XML(XML_GENERIC_TEST)
        self.check_selector("a[upper-case(@id) = 'A_ID']", root, [root[0]])
        self.check_selector("a[upper-case(@id) = 'A_I']", root, [])
        self.check_selector("//b[upper-case(.) = 'SOME CONTENT']", root, [root[0][0]])
        self.check_selector("//b[upper-case((.)) = 'SOME CONTENT']", root, [root[0][0]])
        self.check_selector("//none[upper-case((.)) = 'SOME CONTENT']", root, [])

    def test_encode_for_uri_function(self):
        self.check_value('encode-for-uri("http://xpath.test")', 'http%3A%2F%2Fxpath.test')
        self.check_value('encode-for-uri("~bébé")', '~b%C3%A9b%C3%A9')
        self.check_value('encode-for-uri("100% organic")', '100%25%20organic')
        self.check_value('encode-for-uri("")', '')
        self.check_value('encode-for-uri(())', '')

    def test_iri_to_uri_function(self):
        self.check_value('iri-to-uri("http://www.example.com/00/Weather/CA/Los%20Angeles#ocean")',
                         'http://www.example.com/00/Weather/CA/Los%20Angeles#ocean')
        self.check_value('iri-to-uri("http://www.example.com/~bébé")',
                         'http://www.example.com/~b%C3%A9b%C3%A9')
        self.check_value('iri-to-uri("")', '')
        self.check_value('iri-to-uri(())', '')

    def test_escape_html_uri_function(self):
        self.check_value(
            'escape-html-uri("http://www.example.com/00/Weather/CA/Los Angeles#ocean")',
            'http://www.example.com/00/Weather/CA/Los Angeles#ocean'
        )
        self.check_value("escape-html-uri(\"javascript:if (navigator.browserLanguage == 'fr') "
                         "window.open('http://www.example.com/~bébé');\")",
                         "javascript:if (navigator.browserLanguage == 'fr') "
                         "window.open('http://www.example.com/~b%C3%A9b%C3%A9');")
        self.check_value('escape-html-uri("")', '')
        self.check_value('escape-html-uri(())', '')

    def test_string_join_function(self):
        self.check_value("string-join(('Now', 'is', 'the', 'time', '...'), ' ')",
                         "Now is the time ...")
        self.check_value("string-join(('Blow, ', 'blow, ', 'thou ', 'winter ', 'wind!'), '')",
                         'Blow, blow, thou winter wind!')
        self.check_value("string-join((), 'separator')", '')

        self.check_value("string-join(('a', 'b', 'c'), ', ')", 'a, b, c')
        self.wrong_type("string-join(('a', 'b', 'c'), 8)", 'XPTY0004', 'type of the 2nd argument')
        self.check_value("string-join(('a', 4, 'c'), ', ')", 'a, 4, c')

        root = self.etree.XML(XML_GENERIC_TEST)
        self.check_selector("a[string-join((@id, 'foo', 'bar'), ' ') = 'a_id foo bar']",
                            root, [root[0]])
        self.check_selector("a[string-join((@id, 'foo'), ',') = 'a_id,foo']",
                            root, [root[0]])
        self.check_selector("//b[string-join((., 'bar'), ' ') = 'some content bar']",
                            root, [root[0][0]])
        self.check_selector("//b[string-join((., 'bar'), ',') = 'some content,bar']",
                            root, [root[0][0]])
        self.check_selector("//b[string-join((., 'bar'), ',') = 'some content bar']", root, [])
        self.check_selector("//none[string-join((., 'bar'), ',') = 'some content,bar']", root, [])

    def test_matches_function(self):
        self.check_value('fn:matches("abracadabra", "bra")', True)
        self.check_value('fn:matches("abracadabra", "^a.*a$")', True)
        self.check_value('fn:matches("abracadabra", "^bra")', False)

        self.wrong_value('fn:matches("abracadabra", "bra", "k")')
        self.wrong_value('fn:matches("abracadabra", "[bra")')
        self.wrong_value('fn:matches("abracadabra", "a{1,99999999999999999999999999}")',
                         'FORX0002')

        if platform.python_implementation() != 'PyPy' or self.etree is not lxml_etree:
            poem_context = XPathContext(root=self.etree.XML(XML_POEM_TEST))
            self.check_value('fn:matches(., "Kaum.*krähen")', False, context=poem_context)
            self.check_value('fn:matches(., "Kaum.*krähen", "s")', True, context=poem_context)
            self.check_value('fn:matches(., "^Kaum.*gesehen,$", "m")', True, context=poem_context)
            self.check_value('fn:matches(., "^Kaum.*gesehen,$")', False, context=poem_context)
            self.check_value('fn:matches(., "kiki", "i")', True, context=poem_context)

        root = self.etree.XML(XML_GENERIC_TEST)
        self.check_selector("a[matches(@id, '^a_id$')]", root, [root[0]])
        self.check_selector("a[matches(@id, 'a.id')]", root, [root[0]])
        self.check_selector("a[matches(@id, '_id')]", root, [root[0]])
        self.check_selector("a[matches(@id, 'a!')]", root, [])
        self.check_selector("//b[matches(., '^some.content$')]", root, [root[0][0]])
        self.check_selector("//b[matches(., '^content')]", root, [])
        self.check_selector("//none[matches(., '.*')]", root, [])

    def test_ends_with_function(self):
        self.check_value('fn:ends-with("abracadabra", "bra")', True)
        self.check_value('fn:ends-with("abracadabra", "a")', True)
        self.check_value('fn:ends-with("abracadabra", "cbra")', False)

        root = self.etree.XML(XML_GENERIC_TEST)
        self.check_selector("a[ends-with(@id, 'a_id')]", root, [root[0]])
        self.check_selector("a[ends-with(@id, 'id')]", root, [root[0]])
        self.check_selector("a[ends-with(@id, 'a!')]", root, [])
        self.check_selector("//b[ends-with(., 'some content')]", root, [root[0][0]])
        self.check_selector("//b[ends-with(., 't')]", root, [root[0][0]])
        self.check_selector("//none[ends-with(., 's')]", root, [])

        self.check_value('fn:ends-with ( "tattoo", "tattoo", "http://www.w3.org/'
                         '2005/xpath-functions/collation/codepoint")', True)
        self.check_value('fn:ends-with ( "tattoo", "atto", "http://www.w3.org/'
                         '2005/xpath-functions/collation/codepoint")', False)
        self.check_value("ends-with((), ())", True)

    def test_replace_function(self):
        self.check_value('fn:replace("abracadabra", "bra", "*")', "a*cada*")
        self.check_value('fn:replace("abracadabra", "a.*a", "*")', "*")
        self.check_value('fn:replace("abracadabra", "a.*?a", "*")', "*c*bra")
        self.check_value('fn:replace("abracadabra", "a", "")', "brcdbr")
        self.check_value('fn:replace("abracadabra", "a", "", "i")', "brcdbr")
        self.wrong_value('fn:replace("abracadabra", "a", "", "z")')
        self.wrong_value('fn:replace("abracadabra", "[a", "")')
        self.wrong_type('fn:replace("abracadabra")')

        self.check_value('fn:replace("abracadabra", "a(.)", "a$1$1")', "abbraccaddabbra")
        self.wrong_value('replace("abc", "a(.)", "$x")', 'FORX0004', 'Invalid replacement string')
        self.wrong_value('fn:replace("abracadabra", ".*?", "$1")')
        self.check_value('fn:replace("AAAA", "A+", "b")', "b")
        self.check_value('fn:replace("AAAA", "A+?", "b")', "bbbb")
        self.check_value('fn:replace("darted", "^(.*?)d(.*)$", "$1c$2")', "carted")
        self.check_value('fn:replace("abcd", "(ab)|(a)", "[1=$1][2=$2]")', "[1=ab][2=]cd")

        root = self.etree.XML(XML_GENERIC_TEST)
        self.check_selector("a[replace(@id, '^a_id$', 'foo') = 'foo']", root, [root[0]])
        self.check_selector("a[replace(@id, 'a.id', 'foo') = 'foo']", root, [root[0]])
        self.check_selector("a[replace(@id, '_id', 'no') = 'ano']", root, [root[0]])
        self.check_selector("//b[replace(., '^some.content$', 'new') = 'new']", root, [root[0][0]])
        self.check_selector("//b[replace(., '^content', '') = '']", root, [])
        self.check_selector("//none[replace(., '.*', 'a') = 'a']", root, [])

    def test_tokenize_function(self):
        self.check_value('fn:tokenize("abracadabra", "(ab)|(a)")', ['', 'r', 'c', 'd', 'r', ''])
        self.check_value(r'fn:tokenize("The cat sat on the mat", "\s+")',
                         ['The', 'cat', 'sat', 'on', 'the', 'mat'])
        self.check_value(r'fn:tokenize("1, 15, 24, 50", ",\s*")', ['1', '15', '24', '50'])
        self.check_value('fn:tokenize("1,15,,24,50,", ",")', ['1', '15', '', '24', '50', ''])
        self.check_value(r'fn:tokenize("Some unparsed <br> HTML <BR> text", "\s*<br>\s*", "i")',
                         ['Some unparsed', 'HTML', 'text'])
        self.check_value('fn:tokenize("", "(ab)|(a)")', [])

        self.wrong_value('fn:tokenize("abc", "[a")', 'FORX0002', 'Invalid regular expression')
        self.wrong_value('fn:tokenize("abc", ".*?")', 'FORX0003', 'matches zero-length string')
        self.wrong_value('fn:tokenize("abba", ".?")')
        self.wrong_value('fn:tokenize("abracadabra", "(ab)|(a)", "sxf")')
        self.wrong_type('fn:tokenize("abracadabra", ())')
        self.wrong_type('fn:tokenize("abracadabra", "(ab)|(a)", ())')

    def test_resolve_uri_function(self):
        self.check_value('fn:resolve-uri("dir1/dir2", "file:///home/")', 'file:///home/dir1/dir2')
        self.wrong_value('fn:resolve-uri("dir1/dir2", "home/")', '')
        self.wrong_value('fn:resolve-uri("dir1/dir2")')
        self.check_value('fn:resolve-uri((), "http://xpath.test")')

        self.wrong_value('fn:resolve-uri("file:://file1.txt", "http://xpath.test")',
                         'FORG0002', "'file:://file1.txt' is not a valid URI")
        self.wrong_value('fn:resolve-uri("dir1/dir2", "http:://xpath.test")',
                         'FORG0002', "'http:://xpath.test' is not a valid URI")

        self.parser.base_uri = 'http://www.example.com/ns/'
        try:
            self.check_value('fn:resolve-uri("dir1/dir2")', 'http://www.example.com/ns/dir1/dir2')
            self.check_value('fn:resolve-uri("/dir1/dir2")', '/dir1/dir2')
            self.check_value('fn:resolve-uri("file:text.txt")', 'file:text.txt')
            self.check_value('fn:resolve-uri(())')

            self.wrong_value('fn:resolve-uri("http:://xpath.test")',
                             'FORG0002', "'http:://xpath.test' is not a valid URI")
        finally:
            self.parser.base_uri = None

    def test_empty_function(self):
        # Test cases from https://www.w3.org/TR/xquery-operators/#general-seq-funcs
        self.check_value('fn:empty(("hello", "world"))', False)
        self.check_value('fn:empty(fn:remove(("hello", "world"), 1))', False)
        self.check_value('fn:empty(())', True)
        self.check_value("empty(() * ())", True)
        self.check_value('fn:empty(fn:remove(("hello"), 1))', True)
        self.check_value('fn:empty((xs:double("0")))', False)

    def test_exists_function(self):
        self.check_value('fn:exists(("hello", "world"))', True)
        self.check_value('fn:exists(())', False)
        self.check_value('fn:exists(fn:remove(("hello"), 1))', False)
        self.check_value('fn:exists((xs:int("-1873914410")))', True)

    def test_distinct_values_function(self):
        self.check_value('fn:distinct-values((1, 2.0, 3, 2))', [1, 2.0, 3])
        context = XPathContext(
            root=self.etree.XML('<root/>'),
            variables={
                'x': [UntypedAtomic("foo"), UntypedAtomic("bar"), UntypedAtomic("bar")]
            }
        )
        self.check_value('fn:distinct-values($x)', ['foo', 'bar'], context)

        context = XPathContext(
            root=self.etree.XML('<root/>'),
            variables={'x': [UntypedAtomic("foo"), float('nan'), UntypedAtomic("bar")]}
        )
        token = self.parser.parse('fn:distinct-values($x)')
        results = token.evaluate(context)
        self.assertEqual(results[0], 'foo')
        self.assertTrue(math.isnan(results[1]))
        self.assertEqual(results[2], 'bar')

        root = self.etree.XML('<root/>')
        self.check_selector(
            "fn:distinct-values((xs:float('NaN'), xs:double('NaN'), xs:float('NaN')))",
            root, math.isnan
        )
        self.check_value('fn:distinct-values((xs:float("0"), xs:float("0")))', [0.0])
        self.check_value(
            'fn:distinct-values("foo", "{}")'.format(UNICODE_CODEPOINT_COLLATION), ['foo']
        )

    def test_index_of_function(self):
        self.check_value('fn:index-of ((10, 20, 30, 40), 35)', [])
        self.wrong_type('fn:index-of ((10, 20, 30, 40), ())', 'XPTY0004')
        self.check_value('fn:index-of ((10, 20, 30, 30, 20, 10), 20)', [2, 5])
        self.check_value('fn:index-of (("a", "sport", "and", "a", "pastime"), "a")', [1, 4])
        self.check_value(
            'fn:index-of (("foo", "bar"), "bar", "{}")'.format(UNICODE_CODEPOINT_COLLATION), [2]
        )

        # Issue #28
        root = self.etree.XML("""<root>
            <incode>030</incode>
            <descript></descript>
        </root>""")

        test1 = "/root/descript[index-of(('030','031'), '030')]"
        test2 = "/root/descript[ancestor::root/incode = '030']"
        test3 = "/root/descript[index-of(('030','031'), ancestor::root/incode)]"

        self.check_selector(test1, root, [root[1]])
        self.check_selector(test2, root, [root[1]])
        self.check_selector(test3, root, [root[1]])

    def test_insert_before_function(self):
        context = XPathContext(root=self.etree.XML('<root/>'),
                               variables={'x': ['a', 'b', 'c']})
        self.check_value('fn:insert-before($x, 0, "z")', ['z', 'a', 'b', 'c'], context)
        self.check_value('fn:insert-before($x, 1, "z")', ['z', 'a', 'b', 'c'], context)
        self.check_value('fn:insert-before($x, 2, "z")', ['a', 'z', 'b', 'c'], context)
        self.check_value('fn:insert-before($x, 3, "z")', ['a', 'b', 'z', 'c'], context)
        self.check_value('fn:insert-before($x, 4, "z")', ['a', 'b', 'c', 'z'], context)
        self.wrong_type('fn:insert-before($x, "1", "z")', 'XPTY0004', context=context)

    def test_remove_function(self):
        context = XPathContext(root=self.etree.XML('<root/>'),
                               variables={'x': ['a', 'b', 'c']})
        self.check_value('fn:remove($x, 0)', ['a', 'b', 'c'], context)
        self.check_value('fn:remove($x, 1)', ['b', 'c'], context)
        self.check_value('remove($x, 6)', ['a', 'b', 'c'], context)
        self.wrong_type('remove($x, "6")', 'XPTY0004', context=context)
        self.check_value('fn:remove((), 3)', [])

    def test_reverse_function(self):
        context = XPathContext(root=self.etree.XML('<root/>'),
                               variables={'x': ['a', 'b', 'c']})
        self.check_value('reverse($x)', ['c', 'b', 'a'], context)
        self.check_value('fn:reverse(("hello"))', ['hello'], context)
        self.check_value('fn:reverse(())', [])

    def test_subsequence_function(self):
        self.check_value('fn:subsequence((), 5)', [])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), 1)', [1, 2, 3, 4, 5, 6, 7])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), 0)', [1, 2, 3, 4, 5, 6, 7])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), -1)', [1, 2, 3, 4, 5, 6, 7])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), 10)', [])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), 4)', [4, 5, 6, 7])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), 4, 2)', [4, 5])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), 3, 10)', [3, 4, 5, 6, 7])

        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), xs:float("INF"))', [])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), xs:float("-INF"))',
                         [1, 2, 3, 4, 5, 6, 7])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), 5, xs:float("-INF"))', [])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), 5, xs:float("INF"))', [5, 6, 7])

    def test_unordered_function(self):
        self.check_value('fn:unordered(())', [])
        self.check_value('fn:unordered(("z", 2, "3", "Z", "b", "a"))', [2, '3', 'Z', 'a', 'b', 'z'])

    def test_sequence_cardinality_functions(self):
        self.check_value('fn:zero-or-one(())', [])
        self.check_value('fn:zero-or-one((10))', [10])
        self.wrong_value('fn:zero-or-one((10, 20))')

        self.wrong_value('fn:one-or-more(())')
        self.check_value('fn:one-or-more((10))', [10])
        self.check_value('fn:one-or-more((10, 20, 30, 40))', [10, 20, 30, 40])

        self.check_value('fn:exactly-one((20))', [20])
        self.wrong_value('fn:exactly-one(())')
        self.wrong_value('fn:exactly-one((10, 20, 30, 40))')

    def test_qname_function(self):
        self.check_value('fn:string(fn:QName("", "person"))', 'person')
        self.check_value('fn:string(fn:QName((), "person"))', 'person')
        self.check_value('fn:string(fn:QName("http://www.example.com/ns/", "person"))', 'person')
        self.check_value('fn:string(fn:QName("http://www.example.com/ns/", "ht:person"))',
                         'ht:person')
        self.check_value('fn:string(fn:QName("http://www.example.com/ns/", "xs:person"))',
                         'xs:person')

        self.wrong_value('fn:QName("http://www.example.com/ns/", "@person")')
        self.wrong_type('fn:QName(1.0, "person")', 'XPTY0004', '1st argument has an invalid type')
        self.wrong_type('fn:QName("", 2)', 'XPTY0004', '2nd argument has an invalid type')
        self.wrong_value('fn:QName("", "3")', 'FOCA0002', 'invalid value')
        self.wrong_value('fn:QName("", "xs:int")', 'FOCA0002',
                         'cannot associate a non-empty prefix with no namespace')
        self.wrong_type('fn:QName("http://www.example.com/ns/")',
                        'XPST0017', '2nd argument missing')
        self.wrong_type('fn:QName("http://www.example.com/ns/", "person"',
                        'XPST0017', 'Wrong number of arguments')

        if xmlschema is not None:
            schema = xmlschema.XMLSchema("""
                <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" 
                    xmlns:tns="http://foo.test">
                  <xs:element name="root"/>
                </xs:schema>""")

            with self.schema_bound_parser(schema.xpath_proxy):
                context = self.parser.schema.get_context()
                self.check_value('fn:QName("http://www.example.com/ns/", "@person")',
                                 expected=ValueError, context=context)

    def test_prefix_from_qname_function(self):
        self.check_value(
            'fn:prefix-from-QName(fn:QName("http://www.example.com/ns/", "ht:person"))', 'ht'
        )
        self.check_value(
            'fn:prefix-from-QName(fn:QName("http://www.example.com/ns/", "person"))', []
        )
        self.check_value('fn:prefix-from-QName(())')
        self.check_value('fn:prefix-from-QName(7)', TypeError)
        self.check_value('fn:prefix-from-QName("7")', TypeError)

    def test_local_name_from_qname_function(self):
        self.check_value(
            'fn:local-name-from-QName(fn:QName("http://www.example.com/ns/", "person"))', 'person'
        )
        self.check_value('fn:local-name-from-QName(())')
        self.check_value('fn:local-name-from-QName(8)', TypeError)
        self.check_value('fn:local-name-from-QName("8")', TypeError)

    def test_namespace_uri_from_qname_function(self):
        root = self.etree.XML('<p1:A xmlns:p1="ns1" xmlns:p0="ns0">'
                              '  <B1><p2:C xmlns:p2="ns2"/></B1><B2/>'
                              '  <p0:B3><eg:C1 xmlns:eg="http://www.example.com/ns/"/><C2/></p0:B3>'
                              '</p1:A>')
        self.check_value(
            'fn:namespace-uri-from-QName(fn:QName("http://www.example.com/ns/", "person"))',
            'http://www.example.com/ns/'
        )
        self.check_value('fn:namespace-uri-from-QName(())')
        self.check_value('fn:namespace-uri-from-QName(1)', TypeError)
        self.check_value('fn:namespace-uri-from-QName("1")', TypeError)
        self.check_selector("fn:namespace-uri-from-QName(xs:QName('p3:C3'))", root, KeyError)
        self.check_selector("fn:namespace-uri-from-QName(xs:QName('p3:C3'))", root, ValueError,
                            namespaces={'p3': ''})

    def test_resolve_qname_function(self):
        root = self.etree.XML('<p1:A xmlns:p1="ns1" xmlns:p0="ns0">'
                              '  <B1><p2:C xmlns:p2="ns2"/></B1><B2/>'
                              '  <p0:B3><eg:C1 xmlns:eg="http://www.example.com/ns/"/><C2/></p0:B3>'
                              '</p1:A>')
        context = XPathContext(root=root)

        self.check_value("fn:resolve-QName((), .)", context=context)
        self.check_value("fn:string(fn:resolve-QName('eg:C2', .))", 'eg:C2', context=context)
        self.check_selector("fn:resolve-QName('p3:C3', .)", root, ValueError, namespaces={'p3': ''})
        self.check_raise("fn:resolve-QName('p3:C3', .)", KeyError, 'FONS0004',
                         "no namespace found for prefix 'p3'", context=context)
        self.check_value("fn:resolve-QName('C3', .)", QName('', 'C3'), context=context)

        self.check_value("fn:resolve-QName(2, .)", TypeError, context=context)
        self.check_value("fn:resolve-QName('2', .)", ValueError, context=context)
        self.check_value("fn:resolve-QName((), 4)", context=context)
        self.wrong_type("fn:resolve-QName('p3:C3', 4)", 'FORG0006',
                        '2nd argument 4 is not an element node', context=context)

        root = self.etree.XML('<A><B1><C/></B1><B2/><B3><C1/><C2/></B3></A>')
        self.check_selector("fn:resolve-QName('C3', .)", root,
                            [QName('', 'C3')], namespaces={'': ''})
        self.check_selector("fn:resolve-QName('xml:lang', .)", root,
                            [QName(XML_NAMESPACE, 'lang')])

    def test_namespace_uri_for_prefix_function(self):

        root = self.etree.XML('<p1:A xmlns:p1="ns1" xmlns:p0="ns0">'
                              '  <B1><p2:C xmlns:p2="ns2"/></B1><B2/>'
                              '  <p0:B3><eg:C1 xmlns:eg="http://www.example.com/ns/"/><C2/></p0:B3>'
                              '</p1:A>')
        context = XPathContext(root=root)

        self.check_value("fn:namespace-uri-for-prefix('p1', .)", context=context)
        self.check_value("fn:namespace-uri-for-prefix(4, .)", TypeError, context=context)
        self.check_value("fn:namespace-uri-for-prefix('p1', 9)", TypeError, context=context)
        self.check_value("fn:namespace-uri-for-prefix('eg', .)",
                         'http://www.example.com/ns/', context=context)
        self.check_selector("fn:namespace-uri-for-prefix('p3', .)",
                            root, NameError, namespaces={'p3': ''})

        # Note: default namespace for XPath 2 tests is 'http://www.example.com/ns/'
        self.check_value("fn:namespace-uri-for-prefix('', .)", context=context)
        self.check_value(
            'fn:namespace-uri-from-QName(fn:QName("http://www.example.com/ns/", "person"))',
            'http://www.example.com/ns/'
        )
        self.check_value("fn:namespace-uri-for-prefix('', .)", context=context)
        self.check_value("fn:namespace-uri-for-prefix((), .)", context=context)

    def test_in_scope_prefixes_function(self):
        root = self.etree.XML('<p1:A xmlns:p1="ns1" xmlns:p0="ns0">'
                              '  <B1><p2:C xmlns:p2="ns2"/></B1><B2/>'
                              '  <p0:B3><eg:C1 xmlns:eg="http://www.example.com/ns/"/><C2/></p0:B3>'
                              '</p1:A>')

        namespaces = {'p0': 'ns0', 'p2': 'ns2'}
        prefixes = select(root, "fn:in-scope-prefixes(.)", namespaces, parser=type(self.parser))
        if self.etree is lxml_etree:
            self.assertIn('p0', prefixes)
            self.assertIn('p1', prefixes)
            self.assertNotIn('p2', prefixes)
        else:
            self.assertIn('p0', prefixes)
            self.assertNotIn('p1', prefixes)
            self.assertIn('p2', prefixes)

            # Provides namespaces through the dynamic context
            selector = Selector("fn:in-scope-prefixes(.)", parser=type(self.parser))
            prefixes = selector.select(root, namespaces=namespaces)

            self.assertIn('p0', prefixes)
            self.assertNotIn('p1', prefixes)
            self.assertIn('p2', prefixes)

        with self.assertRaises(TypeError):
            select(root, "fn:in-scope-prefixes('')", namespaces, parser=type(self.parser))

        root = self.etree.XML('<tns:A xmlns:tns="ns1" xmlns:xml="{}"/>'.format(XML_NAMESPACE))
        namespaces = {'tns': 'ns1', 'xml': XML_NAMESPACE}
        prefixes = select(root, "fn:in-scope-prefixes(.)", namespaces, parser=type(self.parser))
        if self.etree is lxml_etree:
            self.assertIn('tns', prefixes)
            self.assertIn('xml', prefixes)
            self.assertNotIn('fn', prefixes)
        else:
            self.assertIn('tns', prefixes)
            self.assertIn('xml', prefixes)
            self.assertIn('fn', prefixes)

        if xmlschema is not None:
            schema = xmlschema.XMLSchema("""
                <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" 
                    xmlns:tns="http://foo.test">
                  <xs:element name="root"/>
                </xs:schema>""")

            with self.schema_bound_parser(schema.xpath_proxy):
                context = self.parser.schema.get_context()
                prefixes = {'xml', 'xs', 'xlink', 'fn', 'err', 'xsi', 'eg', 'tst'}
                self.check_value("fn:in-scope-prefixes(.)", prefixes, context)

    def test_datetime_function(self):
        tz = Timezone(datetime.timedelta(hours=5, minutes=24))

        self.check_value('fn:dateTime((), xs:time("24:00:00"))', [])
        self.check_value('fn:dateTime(xs:date("1999-12-31"), ())', [])
        self.check_value('fn:dateTime(xs:date("1999-12-31"), xs:time("12:00:00"))',
                         datetime.datetime(1999, 12, 31, 12, 0))
        self.check_value('fn:dateTime(xs:date("1999-12-31"), xs:time("24:00:00"))',
                         datetime.datetime(1999, 12, 31, 0, 0))
        self.check_value('fn:dateTime(xs:date("1999-12-31"), xs:time("13:00:00+05:24"))',
                         datetime.datetime(1999, 12, 31, 13, 0, tzinfo=tz))
        self.wrong_value('fn:dateTime(xs:date("1999-12-31+03:00"), xs:time("13:00:00+05:24"))',
                         'FORG0008', 'inconsistent timezones')

        self.check_value('fn:dateTime(xs:date("1999-12-31"), xs:time("12:00:00"))', DateTime10)
        with self.assertRaises(AssertionError):
            self.check_value('fn:dateTime(xs:date("1999-12-31"), xs:time("12:00:00"))', DateTime)

        self.parser._xsd_version = '1.1'
        try:
            self.check_value('fn:dateTime(xs:date("1999-12-31"), xs:time("12:00:00"))',
                             DateTime(1999, 12, 31, 12))
            self.check_value('fn:dateTime(xs:date("1999-12-31"), xs:time("12:00:00"))', DateTime)
        finally:
            self.parser._xsd_version = '1.0'

    def test_year_from_datetime_function(self):
        self.check_value('fn:year-from-dateTime(xs:dateTime("1999-05-31T13:20:00-05:00"))', 1999)
        self.check_value('fn:year-from-dateTime(xs:dateTime("1999-05-31T21:30:00-05:00"))', 1999)
        self.check_value('fn:year-from-dateTime(xs:dateTime("1999-12-31T19:20:00"))', 1999)
        self.check_value('fn:year-from-dateTime(xs:dateTime("1999-12-31T24:00:00"))', 2000)
        self.check_value('fn:year-from-dateTime(())')

    def test_month_from_datetime_function(self):
        self.check_value('fn:month-from-dateTime(xs:dateTime("1999-05-31T13:20:00-05:00"))', 5)
        self.check_value('fn:month-from-dateTime(xs:dateTime("1999-12-31T19:20:00-05:00"))', 12)
        self.check_value('fn:month-from-dateTime(fn:adjust-dateTime-to-timezone(xs:dateTime('
                         '"1999-12-31T19:20:00-05:00"), xs:dayTimeDuration("PT0S")))', 1)

    def test_day_from_datetime_function(self):
        self.check_value('fn:day-from-dateTime(xs:dateTime("1999-05-31T13:20:00-05:00"))', 31)
        self.check_value('fn:day-from-dateTime(xs:dateTime("1999-12-31T20:00:00-05:00"))', 31)
        self.check_value('fn:day-from-dateTime(fn:adjust-dateTime-to-timezone(xs:dateTime('
                         '"1999-12-31T19:20:00-05:00"), xs:dayTimeDuration("PT0S")))', 1)

    def test_hours_from_datetime_function(self):
        self.check_value('fn:hours-from-dateTime(xs:dateTime("1999-05-31T08:20:00-05:00")) ', 8)
        self.check_value('fn:hours-from-dateTime(xs:dateTime("1999-12-31T21:20:00-05:00"))', 21)
        self.check_value('fn:hours-from-dateTime(fn:adjust-dateTime-to-timezone(xs:dateTime('
                         '"1999-12-31T21:20:00-05:00"), xs:dayTimeDuration("PT0S")))', 2)
        self.check_value('fn:hours-from-dateTime(xs:dateTime("1999-12-31T12:00:00")) ', 12)
        self.check_value('fn:hours-from-dateTime(xs:dateTime("1999-12-31T24:00:00"))', 0)

    def test_minutes_from_datetime_function(self):
        self.check_value('fn:minutes-from-dateTime(xs:dateTime("1999-05-31T13:20:00-05:00"))', 20)
        self.check_value('fn:minutes-from-dateTime(xs:dateTime("1999-05-31T13:30:00+05:30"))', 30)

    def test_seconds_from_datetime_function(self):
        self.check_value('fn:seconds-from-dateTime(xs:dateTime("1999-05-31T13:20:00-05:00"))', 0)
        self.check_value('seconds-from-dateTime(xs:dateTime("2001-02-03T08:23:12.43"))',
                         Decimal('12.43'))

    def test_timezone_from_datetime_function(self):
        self.check_value('fn:timezone-from-dateTime(xs:dateTime("1999-05-31T13:20:00-05:00"))',
                         DayTimeDuration(seconds=-18000))
        self.check_value('fn:timezone-from-dateTime(())')

    def test_year_from_date_function(self):
        self.check_value('fn:year-from-date(xs:date("1999-05-31"))', 1999)
        self.check_value('fn:year-from-date(xs:date("2000-01-01+05:00"))', 2000)
        self.check_value('year-from-date(())')

    def test_month_from_date_function(self):
        self.check_value('fn:month-from-date(xs:date("1999-05-31-05:00"))', 5)
        self.check_value('fn:month-from-date(xs:date("2000-01-01+05:00"))', 1)

    def test_day_from_date_function(self):
        self.check_value('fn:day-from-date(xs:date("1999-05-31-05:00"))', 31)
        self.check_value('fn:day-from-date(xs:date("2000-01-01+05:00"))', 1)

    def test_timezone_from_date_function(self):
        self.check_value('fn:timezone-from-date(xs:date("1999-05-31-05:00"))',
                         DayTimeDuration.fromstring('-PT5H'))
        self.check_value('fn:timezone-from-date(xs:date("2000-06-12Z"))',
                         DayTimeDuration.fromstring('PT0H'))
        self.check_value('fn:timezone-from-date(xs:date("2000-06-12"))')

    def test_hours_from_time_function(self):
        self.check_value('fn:hours-from-time(xs:time("11:23:00"))', 11)
        self.check_value('fn:hours-from-time(xs:time("21:23:00"))', 21)
        self.check_value('fn:hours-from-time(xs:time("01:23:00+05:00"))', 1)
        self.check_value('fn:hours-from-time(fn:adjust-time-to-timezone(xs:time("01:23:00+05:00"), '
                         'xs:dayTimeDuration("PT0S")))', 20)
        self.check_value('fn:hours-from-time(xs:time("24:00:00"))', 0)

    def test_minutes_from_time_function(self):
        self.check_value('fn:minutes-from-time(xs:time("13:00:00Z"))', 0)
        self.check_value('fn:minutes-from-time(xs:time("09:45:10"))', 45)

    def test_seconds_from_time_function(self):
        self.check_value('fn:seconds-from-time(xs:time("13:20:10.5"))', 10.5)
        self.check_value('fn:seconds-from-time(xs:time("20:50:10.0"))', 10.0)
        self.check_value('fn:seconds-from-time(xs:time("03:59:59.000001"))', Decimal('59.000001'))

    def test_timezone_from_time_function(self):
        self.check_value('fn:timezone-from-time(xs:time("13:20:00-05:00"))',
                         DayTimeDuration.fromstring('-PT5H'))
        self.check_value('timezone-from-time(())')

    def test_years_from_duration_function(self):
        self.check_value('fn:years-from-duration(())')
        self.check_value('fn:years-from-duration(xs:yearMonthDuration("P20Y15M"))', 21)
        self.check_value('fn:years-from-duration(xs:yearMonthDuration("-P15M"))', -1)
        self.check_value('fn:years-from-duration(xs:dayTimeDuration("-P2DT15H"))', 0)

    def test_months_from_duration_function(self):
        self.check_value('fn:months-from-duration(())')
        self.check_value('fn:months-from-duration(xs:yearMonthDuration("P20Y15M"))', 3)
        self.check_value('fn:months-from-duration(xs:yearMonthDuration("-P20Y18M"))', -6)
        self.check_value('fn:months-from-duration(xs:dayTimeDuration("-P2DT15H0M0S"))', 0)

    def test_days_from_duration_function(self):
        self.check_value('fn:days-from-duration(())')
        self.check_value('fn:days-from-duration(xs:dayTimeDuration("P3DT10H"))', 3)
        self.check_value('fn:days-from-duration(xs:dayTimeDuration("P3DT55H"))', 5)
        self.check_value('fn:days-from-duration(xs:yearMonthDuration("P3Y5M"))', 0)

    def test_hours_from_duration_function(self):
        self.check_value('fn:hours-from-duration(())')
        self.check_value('fn:hours-from-duration(xs:dayTimeDuration("P3DT10H"))', 10)
        self.check_value('fn:hours-from-duration(xs:dayTimeDuration("P3DT12H32M12S"))', 12)
        self.check_value('fn:hours-from-duration(xs:dayTimeDuration("PT123H"))', 3)
        self.check_value('fn:hours-from-duration(xs:dayTimeDuration("-P3DT10H"))', -10)

    def test_minutes_from_duration_function(self):
        self.check_value('fn:minutes-from-duration(())')
        self.check_value('fn:minutes-from-duration(xs:dayTimeDuration("P3DT10H"))', 0)
        self.check_value('fn:minutes-from-duration(xs:dayTimeDuration("-P5DT12H30M"))', -30)

    def test_seconds_from_duration_function(self):
        self.check_value('fn:seconds-from-duration(())')
        self.check_value('fn:seconds-from-duration(xs:dayTimeDuration("P3DT10H12.5S"))', 12.5)
        self.check_value('fn:seconds-from-duration(xs:dayTimeDuration("-PT256S"))', -16.0)

    def test_node_accessor_functions(self):
        root = self.etree.XML('<A xmlns:ns0="%s" id="10"><B1><C1 /><C2 ns0:nil="true" /></B1>'
                              '<B2 /><B3>simple text</B3></A>' % XSI_NAMESPACE)

        self.check_selector("node-name(.)", root, QName('', 'A'))
        self.check_selector("node-name(/A/B1)", root, QName('', 'B1'))
        self.check_selector("node-name(/A/*)", root, TypeError)  # Not allowed more than one item!

        self.check_selector("nilled(./B1/C1)", root, False)
        self.check_selector("nilled(./B1/C2)", root, True)
        self.check_raise("nilled(.)", MissingContextError)

        context = XPathContext(root)
        self.check_value('nilled(())', context=context)
        self.wrong_type('nilled(8)', 'XPTY0004', 'an XPath node required', context=context)

        self.check_value('node-name(())', context=context)
        self.wrong_type('node-name(8)', 'XPTY0004', 'an XPath node required', context=context)
        self.check_value('node-name(.)', context=XPathContext(self.etree.ElementTree(root)))

        root = self.etree.XML('<tst:root xmlns:tst="http://xpath.test/ns" tst:a="10"/>')
        self.check_value('node-name(.)', QName('http://xpath.test/ns', 'root'),
                         context=XPathContext(root))
        self.check_value('node-name(./@tst:a)', QName('http://xpath.test/ns', 'a'),
                         context=XPathContext(root))

        root = self.etree.XML('<root a="10"/>')
        self.check_value('node-name(./@a)', QName('', 'a'), context=XPathContext(root))

        root = self.etree.XML('<tst0:root xmlns:tst0="http://xpath.test/ns0"/>')
        self.check_raise('node-name(.)', KeyError, 'FONS0004',
                         'no prefix found for namespace http://xpath.test/ns0',
                         context=XPathContext(root))

    def test_string_and_data_functions(self):
        root = self.etree.XML('<A id="10"><B1> a text, <C1 /><C2>an inner text, </C2>a tail, </B1>'
                              '<B2 /><B3>an ending text </B3></A>')

        self.check_selector("/*/string()", root,
                            [' a text, an inner text, a tail, an ending text '])
        self.check_selector("string(.)", root, ' a text, an inner text, a tail, an ending text ')
        self.check_selector("data(.)", root, ' a text, an inner text, a tail, an ending text ')
        self.check_selector("data(.)", root, UntypedAtomic)
        self.check_selector("data(())", root, [])
        self.check_value("string()", MissingContextError)

        context = XPathContext(root=self.etree.XML('<A/>'))
        parser = XPath2Parser(base_uri='http://www.example.com/ns/')
        self.assertEqual(parser.parse('data(fn:resolve-uri(()))').evaluate(context), [])

    @unittest.skipIf(xmlschema is None, "The xmlschema library is not installed")
    def test_data_function_with_typed_nodes(self):
        schema = xmlschema.XMLSchema(dedent("""\
            <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
              <xs:element name="root">
                <xs:complexType>
                  <xs:sequence>
                    <xs:element name="child1" type="xs:int"/>
                    <xs:element name="child2" type="xs:string"/>
                  </xs:sequence>
                </xs:complexType>
              </xs:element>
            </xs:schema>"""))

        self.parser.schema = xmlschema.xpath.XMLSchemaProxy(schema)
        try:
            root = self.etree.XML('<root/>')
            self.wrong_value("data(/root)", 'FOTY0012', 'node does not have a typed value',
                             context=XPathContext(root))
            self.wrong_value("data(.)", 'FOTY0012', 'node does not have a typed value',
                             context=XPathContext(root))
        finally:
            self.parser.schema = None

    def test_node_set_id_function(self):
        root = self.etree.XML('<A><B1 xml:id="foo"/><B2/><B3 xml:id="bar"/><B4 xml:id="baz"/></A>')
        self.check_selector('element-with-id("foo")', root, [root[0]])
        self.check_selector('id("foo")', root, [root[0]])

        doc = self.etree.ElementTree(root)
        root = doc.getroot()
        self.check_selector('id("foo")', doc, [root[0]])
        self.check_selector('id("fox")', doc, [])
        self.check_selector('id("foo baz")', doc, [root[0], root[3]])
        self.check_selector('id(("foo", "baz"))', doc, [root[0], root[3]])
        self.check_selector('id(("foo", "baz bar"))', doc, [root[0], root[2], root[3]])
        self.check_selector('id("baz bar foo")', doc, [root[0], root[2], root[3]])

        # From XPath documentation
        doc = self.etree.parse(io.StringIO("""
            <employee xml:id="ID21256">
               <empnr>E21256</empnr>
               <first>John</first>
               <last>Brown</last>
            </employee>"""))
        root = doc.getroot()

        self.check_selector("id('ID21256')", doc, [root])
        self.check_selector("id('E21256')", doc, [root[0]])
        self.check_selector('element-with-id("ID21256")', doc, [root])
        self.check_selector('element-with-id("E21256")', doc, [root])

        with self.assertRaises(MissingContextError) as err:
            self.check_value("id('ID21256')")
        self.assertIn('XPDY0002', str(err.exception))

        context = XPathContext(doc, variables={'x': 11})
        with self.assertRaises(TypeError) as err:
            self.check_value("id('ID21256', $x)", context=context)
        self.assertIn('XPTY0004', str(err.exception))

        context = XPathContext(doc, item=11, variables={'x': 11})
        with self.assertRaises(TypeError) as err:
            self.check_value("id('ID21256', $x)", context=context)
        self.assertIn('XPTY0004', str(err.exception))

        context = XPathContext(doc, item=root, variables={'x': root})
        self.check_value("id('ID21256', $x)", [root], context=context)

        # Id on root element
        root = self.etree.XML("<empnr>E21256</empnr>")
        self.check_selector("id('E21256')", root, [root])
        self.check_selector('element-with-id("E21256")', root, [])

    @unittest.skipIf(xmlschema is None, "xmlschema library is not installed ...")
    def test_node_set_id_function_with_schema(self):
        root = self.etree.XML(dedent("""\
            <employee xml:id="ID21256">
               <empnr>E21256</empnr>
               <first>John</first>
               <last>Brown</last>
            </employee>"""))
        doc = self.etree.ElementTree(root)

        # Test with matching value of type xs:ID
        schema = xmlschema.XMLSchema(dedent("""\
            <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
              <xs:import namespace="http://www.w3.org/XML/1998/namespace"/>
              <xs:element name="employee">
                <xs:complexType>
                  <xs:sequence>
                    <xs:element name="empnr" type="xs:ID"/>
                    <xs:element name="first" type="xs:string"/>
                    <xs:element name="last" type="xs:string"/>
                  </xs:sequence>
                  <xs:attribute ref="xml:id"/>
                </xs:complexType>
              </xs:element>
            </xs:schema>"""))

        self.assertTrue(schema.is_valid(root))
        with self.schema_bound_parser(schema.xpath_proxy):
            context = XPathContext(doc)
            self.check_select("id('ID21256')", [root], context)
            self.check_select("id('E21256')", [root[0]], context)

        # Test with matching value of type xs:string
        schema = xmlschema.XMLSchema(dedent("""\
            <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
              <xs:import namespace="http://www.w3.org/XML/1998/namespace"/>
              <xs:element name="employee">
                <xs:complexType>
                  <xs:sequence>
                    <xs:element name="empnr" type="xs:string"/>
                    <xs:element name="first" type="xs:string"/>
                    <xs:element name="last" type="xs:string"/>
                  </xs:sequence>
                  <xs:attribute ref="xml:id"/>
                </xs:complexType>
              </xs:element>
            </xs:schema>"""))

        self.assertTrue(schema.is_valid(root))
        with self.schema_bound_parser(schema.xpath_proxy):
            context = XPathContext(doc)
            self.check_select("id('E21256')", [], context)

    @unittest.skipIf(xmlschema is None, "xmlschema library is not installed ...")
    def test_node_set_id_function_with_wrong_schema(self):
        root = self.etree.XML(dedent("""\
            <employee xml:id="ID21256">
               <empnr>E21256</empnr>
               <first>John</first>
               <last>Brown</last>
            </employee>"""))
        doc = self.etree.ElementTree(root)

        schema = xmlschema.XMLSchema(dedent("""\
            <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
              <xs:element name="empnr" type="xs:ID"/>
            </xs:schema>"""))

        self.assertFalse(schema.is_valid(root))
        with self.schema_bound_parser(schema.xpath_proxy):
            context = XPathContext(doc)
            self.check_select("id('ID21256')", [], context)
            self.check_select("id('E21256')", [], context)

        schema = xmlschema.XMLSchema(dedent("""\
            <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
              <xs:element name="employee" type="xs:string"/>
            </xs:schema>"""))

        self.assertFalse(schema.is_valid(root))
        with self.schema_bound_parser(schema.xpath_proxy):
            context = XPathContext(doc)
            self.check_select("id('ID21256')", [], context)
            self.check_select("id('E21256')", [], context)

    def test_node_set_idref_function(self):
        doc = self.etree.parse(io.StringIO("""
            <employees>
                <employee xml:id="ID21256">
                   <empnr>E21256</empnr>
                   <first>John</first>
                   <last>Brown</last>
                </employee>
                <employee xml:id="ID21257">
                   <empnr>E21257</empnr>
                   <first>John</first>
                   <last>Doe</last>
                </employee>
            </employees>"""))

        root = doc.getroot()
        self.check_value("idref('ID21256')", MissingContextError)
        self.check_selector("idref('ID21256')", doc, [])
        self.check_selector("idref('E21256')", doc, [root[0][0]])
        self.check_selector("idref('ID21256')", root, [])

        context = XPathContext(doc, variables={'x': 11})
        self.wrong_type("idref('ID21256', $x)", 'XPTY0004', context=context)

        context = XPathContext(doc, item=root, variables={'x': root})
        self.check_value("idref('ID21256', $x)", [], context=context)

        attribute = AttributeNode(XML_ID, 'ID21256', parent=root[0])
        context = XPathContext(doc, item=root, variables={'x': attribute})
        self.check_value("idref('ID21256', $x)", [], context=context)

        context = XPathContext(root, variables={'x': None})
        context.item = None
        self.check_value("idref('ID21256', $x)", [], context=context)

    def test_deep_equal_function(self):
        root = self.etree.XML("""
            <attendees> 
                <name last='Parker' first='Peter'/>
                <name last='Barker' first='Bob'/>
                <name last='Parker' first='Peter'/>
            </attendees>""")
        context = XPathContext(root, variables={'xt': root})

        self.check_value('fn:deep-equal($xt, $xt)', True, context=context)
        self.check_value('deep-equal($xt, $xt/*)', False, context=context)
        self.check_value('deep-equal($xt/name[1], $xt/name[2])', False, context=context)
        self.check_value('deep-equal($xt/name[1], $xt/name[3])', True, context=context)
        self.check_value('deep-equal($xt/name[1], $xt/name[3]/@last)', False, context=context)
        self.check_value('deep-equal($xt/name[1]/@last, $xt/name[3]/@last)', True, context=context)
        self.check_value('deep-equal($xt/name[1]/@last, $xt/name[2]/@last)', False, context=context)
        self.check_value('deep-equal($xt/name[1], "Peter Parker")', False, context=context)

        root = self.etree.XML("""<A xmlns="http://xpath.test/ns"><B1/><B2/><B3/></A>""")
        context = XPathContext(root, variables={'xt': root})
        self.check_value('deep-equal($xt, $xt)', True, context=context)

        self.check_value('deep-equal((1, 2, 3), (1, 2, 3))', True)
        self.check_value('deep-equal((1, 2, 3), (1, (), 3))', False)
        self.check_value('deep-equal((true(), 2, 3), (1, 2, 3))', False)
        self.check_value('deep-equal((true(), 2, 3), (true(), 2, 3))', True)
        self.check_value('deep-equal((1, 2, 3), (true(), 2, 3))', False)

        self.check_value('deep-equal((xs:untypedAtomic("1"), 2, 3), (1, 2, 3))', False)
        self.check_value('deep-equal((1, 2, 3), (xs:untypedAtomic("1"), 2, 3))', False)
        self.check_value(
            'deep-equal((xs:untypedAtomic("1"), 2, 3), (xs:untypedAtomic("2"), 2, 3))', False
        )
        self.check_value(
            'deep-equal((xs:untypedAtomic("1"), 2, 3), (xs:untypedAtomic("1"), 2, 3))', True
        )

        self.check_value('deep-equal((), (1, 2, 3))', False)
        self.check_value('deep-equal((1, 2, 3), (1, 2, 4))', False)
        self.check_value("deep-equal((1, 2, 3), (1, '2', 3))", False)
        self.check_value("deep-equal(('1', '2', '3'), ('1', '2', '3'))", True)
        self.check_value("deep-equal(('1', '2', '3'), ('1', '4', '3'))", False)
        self.check_value("deep-equal((1, 2, 3), (1, 2, 3), 'en_US.UTF-8')", True)

        self.check_value('fn:deep-equal(xs:float("NaN"), xs:double("NaN"))', True)
        self.check_value('fn:deep-equal(xs:float("NaN"), 1.0)', False)
        self.check_value('fn:deep-equal(1.0, xs:double("NaN"))', False)

        self.check_value('deep-equal((1.1E0, 2E0, 3), (1.1, 2.0, 3))', True)
        self.check_value('deep-equal((1.1E0, 2E0, 3), (1.1, 2.1, 3))', False)
        self.check_value('deep-equal((1E0, 2E0, 3), (1, 2, 3))', True)
        self.check_value('deep-equal((1E0, 2E0, 3), (1, 4, 3))', False)

        self.check_value('deep-equal((1.1, 2.0, 3), (1.1E0, 2E0, 3))', True)
        self.check_value('deep-equal((1.1, 2.1, 3), (1.1E0, 2E0, 3))', False)
        self.check_value('deep-equal((1, 2, 3), (1E0, 2E0, 3))', True)
        self.check_value('deep-equal((1, 4, 3), (1E0, 2E0, 3))', False)

        self.check_value('deep-equal(3.1, xs:anyURI("http://xpath.test"))   ', False)

        variables = {'a': [TextNode('alpha')],
                     'b': [TextNode('beta')]}
        context = XPathContext(root, variables=variables)
        self.check_value('deep-equal($a, $a)', True, context=context)
        self.check_value('deep-equal($a, $b)', False, context=context)

        variables = {'a': [AttributeNode('a', '10')],
                     'b': [AttributeNode('b', '10')]}
        context = XPathContext(root, variables=variables)
        self.check_value('deep-equal($a, $a)', True, context=context)
        self.check_value('deep-equal($a, $b)', False, context=context)

        variables = {'a': [NamespaceNode('tns0', 'http://xpath.test/ns')],
                     'b': [NamespaceNode('tns1', 'http://xpath.test/ns')]}
        context = XPathContext(root, variables=variables)
        self.check_value('deep-equal($a, $a)', True, context=context)
        self.check_value('deep-equal($a, $b)', False, context=context)

    def test_adjust_datetime_to_timezone_function(self):
        context = XPathContext(root=self.etree.XML('<A/>'), timezone=Timezone.fromstring('-05:00'),
                               variables={'tz': DayTimeDuration.fromstring("-PT10H")})

        self.check_value('fn:adjust-dateTime-to-timezone(xs:dateTime("2002-03-07T10:00:00-07:00"))',
                         DateTime.fromstring('2002-03-07T12:00:00-05:00'), context)
        self.check_value('fn:adjust-dateTime-to-timezone(xs:dateTime("2002-03-07T10:00:00"))',
                         DateTime.fromstring('2002-03-07T10:00:00'))
        self.check_value('fn:adjust-dateTime-to-timezone(xs:dateTime("2002-03-07T10:00:00"))',
                         DateTime.fromstring('2002-03-07T10:00:00-05:00'), context)
        self.check_value('fn:adjust-dateTime-to-timezone(xs:dateTime("2002-03-07T10:00:00"), $tz)',
                         DateTime.fromstring('2002-03-07T10:00:00-10:00'), context)
        self.check_value(
            'fn:adjust-dateTime-to-timezone(xs:dateTime("2002-03-07T10:00:00-07:00"), $tz)',
            DateTime.fromstring('2002-03-07T07:00:00-10:00'), context
        )
        self.check_value('fn:adjust-dateTime-to-timezone(xs:dateTime("2002-03-07T10:00:00-07:00"), '
                         'xs:dayTimeDuration("PT10H"))',
                         DateTime.fromstring('2002-03-08T03:00:00+10:00'), context)
        self.check_value('fn:adjust-dateTime-to-timezone(xs:dateTime("2002-03-07T00:00:00+01:00"), '
                         'xs:dayTimeDuration("-PT8H"))',
                         DateTime.fromstring('2002-03-06T15:00:00-08:00'), context)
        self.check_value('fn:adjust-dateTime-to-timezone(xs:dateTime("2002-03-07T10:00:00"), ())',
                         DateTime.fromstring('2002-03-07T10:00:00'), context)
        self.check_value(
            'fn:adjust-dateTime-to-timezone(xs:dateTime("2002-03-07T10:00:00-07:00"), ())',
            DateTime.fromstring('2002-03-07T10:00:00'), context
        )

        self.check_value('fn:adjust-dateTime-to-timezone((), ())')

    def test_adjust_date_to_timezone_function(self):
        context = XPathContext(root=self.etree.XML('<A/>'), timezone=Timezone.fromstring('-05:00'),
                               variables={'tz': DayTimeDuration.fromstring("-PT10H")})

        self.check_value('fn:adjust-date-to-timezone(xs:date("2002-03-07"))',
                         Date.fromstring('2002-03-07-05:00'), context)
        self.check_value('fn:adjust-date-to-timezone(xs:date("2002-03-07-07:00"))',
                         Date.fromstring('2002-03-07-05:00'), context)
        self.check_value('fn:adjust-date-to-timezone(xs:date("2002-03-07"), $tz)',
                         Date.fromstring('2002-03-07-10:00'), context)
        self.check_value('fn:adjust-date-to-timezone(xs:date("2002-03-07"), ())',
                         Date.fromstring('2002-03-07'), context)
        self.check_value('fn:adjust-date-to-timezone(xs:date("2002-03-07-07:00"), ())',
                         Date.fromstring('2002-03-07'), context)
        self.check_value('fn:adjust-date-to-timezone(xs:date("2002-03-07-07:00"), $tz)',
                         Date.fromstring('2002-03-06-10:00'), context)

        self.check_value('fn:adjust-date-to-timezone((), ())')
        self.check_value('adjust-date-to-timezone(xs:date("-25252734927766555-06-07+02:00"), '
                         'xs:dayTimeDuration("PT0S"))', OverflowError)

    def test_adjust_time_to_timezone_function(self):
        context = XPathContext(root=self.etree.XML('<A/>'), timezone=Timezone.fromstring('-05:00'),
                               variables={'tz': DayTimeDuration.fromstring("-PT10H")})

        self.check_value('fn:adjust-time-to-timezone(())')
        self.check_value('fn:adjust-time-to-timezone((), ())')

        self.check_value('fn:adjust-time-to-timezone(xs:time("10:00:00"))',
                         Time.fromstring('10:00:00-05:00'), context)
        self.check_value('fn:adjust-time-to-timezone(xs:time("10:00:00-07:00"))',
                         Time.fromstring('12:00:00-05:00'), context)
        self.check_value('fn:adjust-time-to-timezone(xs:time("10:00:00"), $tz)',
                         Time.fromstring('10:00:00-10:00'), context)
        self.check_value('fn:adjust-time-to-timezone(xs:time("10:00:00-07:00"), $tz)',
                         Time.fromstring('07:00:00-10:00'), context)
        self.check_value('fn:adjust-time-to-timezone(xs:time("10:00:00"), ())',
                         Time.fromstring('10:00:00'), context)
        self.check_value('fn:adjust-time-to-timezone(xs:time("10:00:00-07:00"), ())',
                         Time.fromstring('10:00:00'), context)
        self.check_value('fn:adjust-time-to-timezone(xs:time("10:00:00-07:00"), '
                         'xs:dayTimeDuration("PT10H"))',
                         Time.fromstring('03:00:00+10:00'), context)

    def test_default_collation_function(self):
        default_collation = self.parser.default_collation
        self.check_value('fn:default-collation()', default_collation)

    def test_context_datetime_functions(self):
        context = XPathContext(root=self.etree.XML('<A/>'))

        self.check_value('fn:current-dateTime()', context=context,
                         expected=DateTime10.fromdatetime(context.current_dt))
        self.check_value(path='fn:current-date()', context=context,
                         expected=Date10.fromdatetime(context.current_dt.date()))
        self.check_value(path='fn:current-time()', context=context,
                         expected=Time.fromdatetime(context.current_dt))
        self.check_value(path='fn:implicit-timezone()', context=context,
                         expected=DayTimeDuration(seconds=time.timezone))
        context.timezone = Timezone.fromstring('-05:00')
        self.check_value(path='fn:implicit-timezone()', context=context,
                         expected=DayTimeDuration.fromstring('-PT5H'))

        self.parser._xsd_version = '1.1'
        try:
            self.check_value('fn:current-dateTime()', context=context,
                             expected=DateTime.fromdatetime(context.current_dt))
            self.check_value(path='fn:current-date()', context=context,
                             expected=Date.fromdatetime(context.current_dt.date()))
        finally:
            self.parser._xsd_version = '1.0'

    def test_static_base_uri_function(self):
        context = XPathContext(root=self.etree.XML('<A/>'))
        self.check_value('fn:static-base-uri()', context=context)

        parser = XPath2Parser(strict=True, base_uri='http://example.com/ns/')
        self.assertEqual(parser.parse('fn:static-base-uri()').evaluate(context),
                         'http://example.com/ns/')

    def test_base_uri_function(self):
        context = XPathContext(root=self.etree.XML('<A/>'))
        with self.assertRaises(MissingContextError) as err:
            self.check_value('fn:base-uri(())')
        self.assertIn('XPDY0002', str(err.exception))
        self.assertIn('context item is undefined', str(err.exception))

        self.check_value('fn:base-uri(9)', MissingContextError)
        self.check_value('fn:base-uri(9)', TypeError, context=context)
        self.check_value('fn:base-uri()', context=context)
        self.check_value('fn:base-uri(())', context=context)

        context = XPathContext(root=self.etree.XML('<A xml:base="/base_path/"/>'))
        self.check_value('fn:base-uri()', '/base_path/', context=context)

    def test_document_uri_function(self):
        document = self.etree.parse(io.StringIO('<A/>'))
        context = XPathContext(root=document)
        self.check_value('fn:document-uri(())', context=context)
        self.check_value('fn:document-uri(.)', context=context)

        context = XPathContext(root=document.getroot(), item=document,
                               documents={'/base_path/': document})
        self.check_value('fn:document-uri(.)', context=context)

        context = XPathContext(root=document, documents={'/base_path/': document})
        self.check_value('fn:document-uri(.)', '/base_path/', context=context)

        context = XPathContext(root=document, documents={
            '/base_path/': self.etree.parse(io.StringIO('<A/>')),
        })
        self.check_value('fn:document-uri(.)', context=context)

        document = self.etree.parse(io.StringIO('<A xml:base="/base_path/"/>'))
        context = XPathContext(root=document)
        self.check_value('fn:document-uri(.)', '/base_path/', context=context)

    def test_doc_functions(self):
        root = self.etree.XML("<A><B1><C1/></B1><B2/><B3/></A>")
        doc = self.etree.parse(io.StringIO("<a><b1><c1/></b1><b2/><b3/></a>"))
        context = XPathContext(root, documents={'tns0': doc})

        self.check_value("fn:doc(())", context=context)
        self.check_value("fn:doc-available(())", False, context=context)
        self.wrong_value('fn:doc-available(xs:untypedAtomic("2"))', 'FODC0002', context=context)
        self.wrong_type('fn:doc-available(2)', 'XPTY0004', context=context)

        self.check_value("fn:doc('tns0')", doc, context=context)
        self.check_value("fn:doc-available('tns0')", True, context=context)

        self.check_value("fn:doc('tns1')", ValueError, context=context)
        self.check_value("fn:doc-available('tns1')", False, context=context)

        self.parser.base_uri = "/path1"
        self.check_value("fn:doc('http://foo.test')", ValueError, context=context)
        self.check_value("fn:doc-available('http://foo.test')", False, context=context)
        self.parser.base_uri = None

        doc = self.etree.XML("<a><b1><c1/></b1><b2/><b3/></a>")
        context = XPathContext(root, documents={'tns0': doc})

        self.wrong_type("fn:doc('tns0')", 'XPDY0050', context=context)
        self.wrong_type("fn:doc-available('tns0')", 'XPDY0050', context=context)

        context = XPathContext(root, documents={'file.xml': None})
        self.wrong_value("fn:doc('file.xml')", 'FODC0002', context=context)
        self.wrong_value("fn:doc('unknown')", 'FODC0002', context=context)
        self.check_value("fn:doc-available('unknown')", False, context=context)

        dirpath = os.path.dirname(__file__)
        self.wrong_value("fn:doc('{}')".format(dirpath), 'FODC0005', context=context)

    def test_collection_function(self):
        root = self.etree.XML("<A><B1><C1/></B1><B2/><B3/></A>")
        doc1 = self.etree.parse(io.StringIO("<a><b1><c1/></b1><b2/><b3/></a>"))
        doc2 = self.etree.parse(io.StringIO("<a1><b11><c11/></b11><b12/><b13/></a1>"))
        context = XPathContext(root, collections={'tns0': [doc1, doc2]})

        self.check_value("fn:collection('tns0')", [doc1, doc2], context=context)

        self.parser.collection_types = {'tns0': 'node()*'}
        self.check_value("fn:collection('tns0')", [doc1, doc2], context=context)
        self.parser.collection_types = {'tns0': 'node()'}
        self.check_value("fn:collection('tns0')", TypeError, context=context)

        self.check_value("fn:collection()", ValueError, context=context)
        context.default_collection = context.collections['tns0']
        self.check_value("fn:collection()", [doc1, doc2], context=context)
        self.parser.default_collection_type = 'node()'
        self.check_value("fn:collection()", TypeError, context=context)
        self.parser.default_collection_type = 'node()*'

        context = XPathContext(root)
        self.wrong_value("fn:collection('filepath')", 'FODC0002', context=context)
        self.wrong_value("fn:collection('dirpath/')", 'FODC0003', context=context)

    def test_root_function(self):
        root = self.etree.XML("<A><B1><C1/></B1><B2/><B3/></A>")
        self.check_value("root()", root, context=XPathContext(root))
        self.check_value("root()", root, context=XPathContext(root, item=root[2]))

        with self.assertRaises(TypeError) as err:
            self.check_value("root()", root, context=XPathContext(root, item=10))
        self.assertIn('XPTY0004', str(err.exception))

        with self.assertRaises(TypeError) as err:
            self.check_value("root(7)", root, context=XPathContext(root))
        self.assertIn('XPTY0004', str(err.exception))

        context = XPathContext(root, variables={'elem': root[1]})
        self.check_value("fn:root(())", context=context)
        self.check_value("fn:root($elem)", root, context=context)

        doc = self.etree.XML("<a><b1><c1/></b1><b2/><b3/></a>")

        context = XPathContext(root, variables={'elem': doc[1]})
        self.check_value("fn:root($elem)", context=context)

        context = XPathContext(root, variables={'elem': doc[1]}, documents={})
        self.check_value("fn:root($elem)", context=context)

        context = XPathContext(root, variables={'elem': doc[1]}, documents={'.': doc})
        self.check_value("root($elem)", doc, context=context)

        doc2 = self.etree.XML("<a><b1><c1/></b1><b2/><b3/></a>")

        context = XPathContext(root, variables={'elem': doc2[1]}, documents={'.': doc})
        self.check_value("root($elem)", context=context)

        context = XPathContext(root, variables={'elem': doc2[1]},
                               documents={'.': doc, 'doc2': doc2})
        self.check_value("root($elem)", doc2, context=context)

        if xmlschema is not None:
            schema = xmlschema.XMLSchema(dedent("""\
                <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" 
                    xmlns:tns="http://foo.test">
                  <xs:element name="root"/>
                </xs:schema>"""))

            with self.schema_bound_parser(schema.xpath_proxy):
                context = self.parser.schema.get_context()
                self.check_value("fn:root()", None, context)

    def test_error_function(self):
        with self.assertRaises(ElementPathError) as err:
            self.check_value('fn:error()')
        self.assertEqual(str(err.exception), '[err:FOER0000] Unidentified error')

        with self.assertRaises(ElementPathError) as err:
            self.check_value('fn:error("err:XPST0001")')
        self.assertIn(
            "[err:XPTY0004] the type of the 1st argument is <class 'str'>", str(err.exception)
        )

        with self.assertRaises(ElementPathError) as err:
            self.check_value(
                "fn:error(fn:QName('http://www.w3.org/2005/xqt-errors', 'err:XPST0001'))"
            )
        self.assertEqual(str(err.exception), '[err:XPST0001] Parser not bound to a schema')

        with self.assertRaises(ElementPathError) as err:
            self.check_value(
                "fn:error(fn:QName('http://www.w3.org/2005/xqt-errors', 'err:XPST0001'), "
                "'Missing schema')"
            )
        self.assertEqual(str(err.exception), '[err:XPST0001] Missing schema')

    def test_trace_function(self):
        self.check_value('trace((), "trace message")', [])
        self.check_value('trace("foo", "trace message")', ['foo'])


@unittest.skipIf(lxml_etree is None, "The lxml library is not installed")
class LxmlXPath2FunctionsTest(XPath2FunctionsTest):
    etree = lxml_etree


if __name__ == '__main__':
    unittest.main()
