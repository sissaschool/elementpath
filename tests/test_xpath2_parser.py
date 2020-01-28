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
from decimal import Decimal

try:
    import lxml.etree as lxml_etree
except ImportError:
    lxml_etree = None

from elementpath import *
from elementpath.namespaces import XSI_NAMESPACE
from elementpath.datatypes import DateTime, Date, Time, Timezone, \
    DayTimeDuration, YearMonthDuration, UntypedAtomic, GregorianYear10

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


class XPath2ParserTest(test_xpath1_parser.XPath1ParserTest):

    def setUp(self):
        self.parser = XPath2Parser(namespaces=self.namespaces, variables=self.variables)

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

    def test_xpath_tokenizer2(self):
        self.check_tokenizer("(: this is a comment :)",
                             ['(:', '', 'this', '', 'is', '', 'a', '', 'comment', '', ':)'])
        self.check_tokenizer("last (:", ['last', '', '(:'])

    def test_token_tree2(self):
        self.check_tree('(1 + 6, 2, 10 - 4)', '(, (, (+ (1) (6)) (2)) (- (10) (4)))')
        self.check_tree('/A/B2 union /A/B1', '(union (/ (/ (A)) (B2)) (/ (/ (A)) (B1)))')

    def test_token_source2(self):
        self.check_source("(5, 6) instance of xs:integer+", '(5, 6) instance of xs:integer+')
        self.check_source("$myaddress treat as element(*, USAddress)",
                          "$myaddress treat as element(*, USAddress)")

    def test_xpath_comments(self):
        self.wrong_syntax("(: this is a comment :)")
        self.wrong_syntax("(: this is a (: nested :) comment :)")
        self.check_tree('child (: nasty (:nested :) axis comment :) ::B1', '(child (B1))')
        self.check_tree('child (: nasty "(: but not nested :)" axis comment :) ::B1',
                        '(child (B1))')
        self.check_value("5 (: before operator comment :) < 4", False)  # Before infix operator
        self.check_value("5 < (: after operator comment :) 4", False)  # After infix operator
        self.check_value("true (:# nasty function comment :) ()", True)
        self.check_tree(' (: initial comment :)/ (:2nd comment:)A/B1(: 3rd comment :)/ \n'
                        'C1 (: last comment :)\t', '(/ (/ (/ (A)) (B1)) (C1))')

    def test_comma_operator(self):
        self.check_value("1, 2", [1, 2])
        self.check_value("(1, 2)", [1, 2])
        self.check_value("(-9, 28, 10)", [-9, 28, 10])
        self.check_value("(1, 2)", [1, 2])

        root = self.etree.XML('<A/>')
        self.check_selector("(7.0, /A, 'foo')", root, [7.0, root, 'foo'])
        self.check_selector("7.0, /A, 'foo'", root, [7.0, root, 'foo'])
        self.check_selector("/A, 7.0, 'foo'", self.etree.XML('<dummy/>'), [7.0, 'foo'])

    def test_range_expressions(self):
        # Some cases from https://www.w3.org/TR/xpath20/#construct_seq
        self.check_value("1 to 2", [1, 2])
        self.check_value("1 to 10", list(range(1, 11)))
        self.check_value("(10, 1 to 4)", [10, 1, 2, 3, 4])
        self.check_value("10 to 10", [10])
        self.check_value("15 to 10", [])
        self.check_value("fn:reverse(10 to 15)", [15, 14, 13, 12, 11, 10])

    def test_parenthesized_expressions(self):
        self.check_value("(1, 2, '10')", [1, 2, '10'])
        self.check_value("()", [])

    def test_if_expressions(self):
        root = self.etree.XML('<A><B1><C1/><C2/></B1><B2/><B3><C3/><C4/><C5/></B3></A>')
        self.check_value("if (1) then 2 else 3", 2)
        self.check_selector("if (true()) then /A/B1 else /A/B2", root, root[:1])
        self.check_selector("if (false()) then /A/B1 else /A/B2", root, root[1:2])

        # Cases from XPath 2.0 examples
        root = self.etree.XML('<part discounted="false"><wholesale/><retail/></part>')
        self.check_selector(
            'if ($part/@discounted) then $part/wholesale else $part/retail',
            root, [root[0]], variables={'part': root}
        )
        root = self.etree.XML('<widgets>'
                              '  <widget><unit-cost>25</unit-cost></widget>'
                              '  <widget><unit-cost>10</unit-cost></widget>'
                              '  <widget><unit-cost>15</unit-cost></widget>'
                              '</widgets>')
        self.check_selector(
            'if ($widget1/unit-cost < $widget2/unit-cost) then $widget1 else $widget2',
            root, [root[2]], variables={'widget1': root[0], 'widget2': root[2]}
        )

    def test_quantifier_expressions(self):
        # Cases from XPath 2.0 examples
        root = self.etree.XML('<parts>'
                              '  <part discounted="true" available="true" />'
                              '  <part discounted="false" available="true" />'
                              '  <part discounted="true" />'
                              '</parts>')
        self.check_selector("every $part in /parts/part satisfies $part/@discounted", root, True)
        self.check_selector("every $part in /parts/part satisfies $part/@available", root, False)

        root = self.etree.XML('<emps>'
                              '  <employee><salary>1000</salary><bonus>400</bonus></employee>'
                              '  <employee><salary>1200</salary><bonus>300</bonus></employee>'
                              '  <employee><salary>1200</salary><bonus>200</bonus></employee>'
                              '</emps>')
        self.check_selector("some $emp in /emps/employee satisfies "
                            "   ($emp/bonus > 0.25 * $emp/salary)", root, True)
        self.check_selector("every $emp in /emps/employee satisfies "
                            "   ($emp/bonus < 0.5 * $emp/salary)", root, True)

        context = XPathContext(root=self.etree.XML('<dummy/>'))
        self.check_value("some $x in (1, 2, 3), $y in (2, 3, 4) satisfies $x + $y = 4",
                         True, context)
        self.check_value("every $x in (1, 2, 3), $y in (2, 3, 4) satisfies $x + $y = 4",
                         False, context)

        self.check_value('some $x in (1, 2, "cat") satisfies $x * 2 = 4', True, context)
        self.check_value('every $x in (1, 2, "cat") satisfies $x * 2 = 4', False, context)

    def test_for_expressions(self):
        # Cases from XPath 2.0 examples
        context = XPathContext(root=self.etree.XML('<dummy/>'))
        self.check_value("for $i in (10, 20), $j in (1, 2) return ($i + $j)",
                         [11, 12, 21, 22], context)

        root = self.etree.XML(
            """
            <bib>
                <book>
                    <title>TCP/IP Illustrated</title>
                    <author>Stevens</author>
                    <publisher>Addison-Wesley</publisher>
                </book>
                <book>
                    <title>Advanced Programming in the Unix Environment</title>
                    <author>Stevens</author>
                    <publisher>Addison-Wesley</publisher>
                </book>
                <book>
                    <title>Data on the Web</title>
                    <author>Abiteboul</author>
                    <author>Buneman</author>
                    <author>Suciu</author>
                </book>
            </bib>
            """)

        # Test step-by-step, testing also other basic features.
        self.check_selector("book/author[1]", root, [root[0][1], root[1][1], root[2][1]])
        self.check_selector("book/author[. = $a]", root, [root[0][1], root[1][1]],
                            variables={'a': 'Stevens'})
        self.check_tree("book/author[. = $a][1]", '(/ (book) ([ ([ (author) (= (.) ($ (a)))) (1)))')
        self.check_selector("book/author[. = $a][1]", root, [root[0][1], root[1][1]],
                            variables={'a': 'Stevens'})
        self.check_selector("book/author[. = 'Stevens'][2]", root, [])

        self.check_selector("for $a in fn:distinct-values(book/author) return $a",
                            root, ['Stevens', 'Abiteboul', 'Buneman', 'Suciu'])

        self.check_selector("for $a in fn:distinct-values(book/author) return book/author[. = $a]",
                            root, [root[0][1], root[1][1]] + root[2][1:4])

        self.check_selector("for $a in fn:distinct-values(book/author) "
                            "return book/author[. = $a][1]",
                            root, [root[0][1], root[1][1]] + root[2][1:4])
        self.check_selector(
            "for $a in fn:distinct-values(book/author) "
            "return (book/author[. = $a][1], book[author = $a]/title)",
            root, [root[0][1], root[1][1], root[0][0], root[1][0], root[2][1],
                   root[2][0], root[2][2], root[2][0], root[2][3], root[2][0]]
        )

    def test_boolean_functions2(self):
        root = self.etree.XML('<A><B1/><B2/><B3/></A>')
        self.check_selector("boolean(/A)", root, True)
        self.check_selector("boolean((-10, 35))", root, TypeError)  # Sequence with 2 numeric values
        self.check_selector("boolean((/A, 35))", root, True)

    def test_numerical_expressions2(self):
        self.check_value("5 idiv 2", 2)
        self.check_value("-3.5 idiv -2", 1)
        self.check_value("-3.5 idiv 2", -1)
        self.wrong_value("-3.5 idiv 0")
        self.wrong_value("xs:float('INF') idiv 2")

    def test_comparison_operators(self):
        super(XPath2ParserTest, self).test_comparison_operators()
        self.check_value("0.05 eq 0.05", True)
        self.check_value("19.03 ne 19.02999", True)
        self.check_value("-1.0 eq 1.0", False)
        self.check_value("1 le 2", True)
        self.check_value("3 le 2", False)
        self.check_value("5 ge 9", False)
        self.check_value("5 gt 3", True)
        self.check_value("5 lt 20.0", True)
        self.check_value("false() eq 1", False)
        self.check_value("0 eq false()", True)
        self.check_value("2 * 2 eq 4", True)

        self.check_value("() le 4")
        self.check_value("4 gt ()")
        self.check_value("() eq ()")  # Equality of empty sequences is also an empty sequence

        # From XPath 2.0 examples
        root = self.etree.XML('<collection>'
                              '   <book><author>Kafka</author></book>'
                              '   <book><author>Huxley</author></book>'
                              '   <book><author>Asimov</author></book>'
                              '</collection>')
        context = XPathContext(root=root, variables={'book1': root[0]})
        self.check_value('$book1 / author = "Kafka"', True, context=context)
        self.check_value('$book1 / author eq "Kafka"', True, context=context)

        self.check_value("(1, 2) = (2, 3)", True)
        self.check_value("(2, 3) = (3, 4)", True)
        self.check_value("(1, 2) = (3, 4)", False)
        self.check_value("(1, 2) != (2, 3)", True)  # != is not the inverse of =

        context = XPathContext(root=root, variables={
            'a': UntypedAtomic('1'), 'b': UntypedAtomic('2'), 'c': UntypedAtomic('2.0')
        })
        self.check_value('($a, $b) = ($c, 3.0)', False, context=context)
        self.check_value('($a, $b) = ($c, 2.0)', True, context=context)

        root = self.etree.XML('<root min="10" max="7"/>')
        self.check_value('@min', [AttributeNode('min', '10')], context=XPathContext(root=root))
        self.check_value('@min le @max', True, context=XPathContext(root=root))
        root = self.etree.XML('<root min="80" max="7"/>')
        self.check_value('@min le @max', False, context=XPathContext(root=root))
        self.check_value('@min le @maximum', None, context=XPathContext(root=root))

        root = self.etree.XML('<root><a>1</a><a>10</a><a>30</a><a>50</a></root>')
        self.check_selector("a = (1 to 30)", root, True)
        self.check_selector("a = (2)", root, False)
        self.check_selector("a[1] = (1 to 10, 30)", root, True)
        self.check_selector("a[2] = (1 to 10, 30)", root, True)
        self.check_selector("a[3] = (1 to 10, 30)", root, True)
        self.check_selector("a[4] = (1 to 10, 30)", root, False)

    def test_number_functions2(self):
        # Test cases taken from https://www.w3.org/TR/xquery-operators/#numeric-value-functions
        self.check_value("abs(10.5)", 10.5)
        self.check_value("abs(-10.5)", 10.5)
        self.check_value("round-half-to-even(0.5)", 0)
        self.check_value("round-half-to-even(1.5)", 2)
        self.check_value("round-half-to-even(2.5)", 2)
        self.check_value("round-half-to-even(3.567812E+3, 2)", 3567.81E0)
        self.check_value("round-half-to-even(4.7564E-3, 2)", 0.0E0)
        self.check_value("round-half-to-even(35612.25, -2)", 35600)

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
        self.check_value("fn:avg(())", [])
        self.check_value("fn:avg($seq3)", 4.0, context=context)

        root_token = self.parser.parse("fn:avg((xs:float('INF'), xs:float('-INF')))")
        self.assertTrue(math.isnan(root_token.evaluate(context)))

        root_token = self.parser.parse("fn:avg(($seq3, xs:float('NaN')))")
        self.assertTrue(math.isnan(root_token.evaluate(context)))

        root = self.etree.XML('<a><b>1</b><b>9</b></a>')
        self.check_selector('avg(/a/b/number(text()))', root, 5)

    def test_max_function(self):
        self.check_value("fn:max((3,4,5))", 5)
        self.check_value("fn:max((5, 5.0e0))", 5.0e0)
        self.wrong_type("fn:max((3,4,'Zero'))")
        dt = datetime.datetime.now()
        self.check_value('fn:max((fn:current-date(), xs:date("2001-01-01")))',
                         Date(dt.year, dt.month, dt.day, tzinfo=dt.tzinfo))
        self.check_value('fn:max(("a", "b", "c"))', 'c')

        root = self.etree.XML('<a><b>1</b><b>9</b></a>')
        self.check_selector('max(/a/b/number(text()))', root, 9)

    def test_min_function(self):
        self.check_value("fn:min((3,4,5))", 3)
        self.check_value("fn:min((5, 5.0e0))", 5.0e0)
        self.check_value("fn:min((xs:float(0.0E0), xs:float(-0.0E0)))", 0.0)
        self.check_value('fn:min((fn:current-date(), xs:date("2001-01-01")))',
                         Date.fromstring("2001-01-01"))
        self.check_value('fn:min(("a", "b", "c"))', 'a')

        root = self.etree.XML('<a><b>1</b><b>9</b></a>')
        self.check_selector('min(/a/b/number(text()))', root, 1)

    ###
    # Functions on strings
    def test_codepoints_to_string_function(self):
        self.check_value("codepoints-to-string((2309, 2358, 2378, 2325))", 'अशॊक')

    def test_string_to_codepoints_function(self):
        self.check_value('string-to-codepoints("Thérèse")', [84, 104, 233, 114, 232, 115, 101])
        self.check_value('string-to-codepoints(())', [])

    def test_codepoint_equal_function(self):
        self.check_value("fn:codepoint-equal('abc', 'abc')", True)
        self.check_value("fn:codepoint-equal('abc', 'abcd')", False)
        self.check_value("fn:codepoint-equal('', '')", True)
        self.check_value("fn:codepoint-equal((), 'abc')", [])
        self.check_value("fn:codepoint-equal('abc', ())", [])
        self.check_value("fn:codepoint-equal((), ())", [])

    def test_compare_function(self):
        env_locale_setting = locale.getlocale(locale.LC_COLLATE)

        locale.setlocale(locale.LC_COLLATE, 'C')
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

        self.wrong_type("fn:compare('Strasse', 111)")

        locale.setlocale(locale.LC_COLLATE, env_locale_setting)

    def test_normalize_unicode_function(self):
        self.check_value('fn:normalize-unicode(())', '')
        self.check_value('fn:normalize-unicode("menù")', 'menù')
        self.assertRaises(NotImplementedError, self.parser.parse,
                          'fn:normalize-unicode("à", "FULLY-NORMALIZED")')
        self.wrong_value('fn:normalize-unicode("à", "UNKNOWN")')

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

    def test_count_function2(self):
        super(XPath2ParserTest, self).test_count_function()
        self.check_value("fn:count('')", 1)
        self.check_value("count('')", 1)
        self.check_value("fn:count('abc')", 1)
        self.check_value("fn:count(7)", 1)
        self.check_value("fn:count(())", 0)
        self.check_value("fn:count((1, 2, 3))", 3)
        self.check_value("fn:count((1, 2, ()))", 2)
        self.check_value("fn:count((((()))))", 0)
        self.check_value("fn:count((((), (), ()), (), (), (), ()))", 0)
        self.check_value("count(('1', (2, ())))", 2)
        self.check_value("count(('1', (2, '3')))", 3)
        self.check_value("count(1 to 5)", 5)
        self.check_value("count(reverse((1, 2, 3, 4)))", 4)

        self.check_value('fn:count((xs:decimal("-999999999999999999")))', 1)
        self.check_value('fn:count((xs:float("0")))', 1)
        self.check_value("count(//*[@name='John Doe'])", 0)

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
        self.wrong_type('upper-case((10))')

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

        self.check_value('fn:ends-with ( "tattoo", "tattoo")', True)
        self.check_value('fn:ends-with ( "tattoo", "atto")', False)
        if self.parser.version > '1.0':
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

        self.wrong_value('fn:tokenize("abba", ".?")')
        self.wrong_value('fn:tokenize("abracadabra", "(ab)|(a)", "sxf")')
        self.wrong_value('fn:tokenize("abracadabra", ())')
        self.wrong_value('fn:tokenize("abracadabra", "(ab)|(a)", ())')

    def test_resolve_uri_function(self):
        self.wrong_value('fn:resolve-uri("dir1/dir2")')
        context = XPathContext(root=self.etree.XML('<A/>'))
        parser = XPath2Parser(base_uri='http://www.example.com/ns/')
        self.assertEqual(
            parser.parse('fn:resolve-uri("dir1/dir2")').evaluate(context),
            'http://www.example.com/ns/dir1/dir2'
        )
        self.assertEqual(parser.parse('fn:resolve-uri("/dir1/dir2")').evaluate(context),
                         '/dir1/dir2')
        self.assertEqual(parser.parse('fn:resolve-uri("file:text.txt")').evaluate(context),
                         'http://www.example.com/ns/text.txt')
        self.assertIsNone(parser.parse('fn:resolve-uri(())').evaluate(context))

    def test_predicate(self):
        super(XPath2ParserTest, self).test_predicate()
        root = self.etree.XML('<A><B1><B2/><B2/></B1><C1><C2/><C2/></C1></A>')
        self.check_selector("/(A/*/*)[1]", root, [root[0][0]])
        self.check_selector("/A/*/*[1]", root, [root[0][0], root[1][0]])

    def test_sequence_general_functions(self):
        # Test cases from https://www.w3.org/TR/xquery-operators/#general-seq-funcs
        self.check_value('fn:empty(("hello", "world"))', False)
        self.check_value('fn:exists(("hello", "world"))', True)
        self.check_value('fn:empty(fn:remove(("hello", "world"), 1))', False)
        self.check_value('fn:empty(())', True)
        self.check_value('fn:exists(())', False)
        self.check_value('fn:empty(fn:remove(("hello"), 1))', True)
        self.check_value('fn:exists(fn:remove(("hello"), 1))', False)

        self.check_value('fn:distinct-values((1, 2.0, 3, 2))', [1, 2.0, 3])
        context = XPathContext(
            root=self.etree.XML('<dummy/>'),
            variables={'x': [UntypedAtomic("cherry"), UntypedAtomic("bar"), UntypedAtomic("bar")]}
        )
        self.check_value('fn:distinct-values($x)', ['cherry', 'bar'], context)

        self.check_value('fn:index-of ((10, 20, 30, 40), 35)', [])
        self.check_value('fn:index-of ((10, 20, 30, 30, 20, 10), 20)', [2, 5])
        self.check_value('fn:index-of (("a", "sport", "and", "a", "pastime"), "a")', [1, 4])

        context = XPathContext(root=self.etree.XML('<dummy/>'), variables={'x': ['a', 'b', 'c']})
        self.check_value('fn:insert-before($x, 0, "z")', ['z', 'a', 'b', 'c'], context.copy())
        self.check_value('fn:insert-before($x, 1, "z")', ['z', 'a', 'b', 'c'], context.copy())
        self.check_value('fn:insert-before($x, 2, "z")', ['a', 'z', 'b', 'c'], context.copy())
        self.check_value('fn:insert-before($x, 3, "z")', ['a', 'b', 'z', 'c'], context.copy())
        self.check_value('fn:insert-before($x, 4, "z")', ['a', 'b', 'c', 'z'], context.copy())

        self.check_value('fn:remove($x, 0)', ['a', 'b', 'c'], context)
        self.check_value('fn:remove($x, 1)', ['b', 'c'], context)
        self.check_value('remove($x, 6)', ['a', 'b', 'c'], context)
        self.check_value('fn:remove((), 3)', [])

        self.check_value('reverse($x)', ['c', 'b', 'a'], context)
        self.check_value('fn:reverse(("hello"))', ['hello'], context)
        self.check_value('fn:reverse(())', [])

        self.check_value('fn:subsequence((), 5)', [])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), 1)', [1, 2, 3, 4, 5, 6, 7])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), 0)', [1, 2, 3, 4, 5, 6, 7])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), -1)', [1, 2, 3, 4, 5, 6, 7])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), 10)', [])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), 4)', [4, 5, 6, 7])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), 4, 2)', [4, 5])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), 3, 10)', [3, 4, 5, 6, 7])

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

    def test_qname_functions(self):
        root = self.etree.XML('<p1:A xmlns:p1="ns1" xmlns:p0="ns0">'
                              '  <B1><p2:C xmlns:p2="ns2"/></B1><B2/>'
                              '  <p0:B3><eg:C1 xmlns:eg="http://www.example.com/ns/"/><C2/></p0:B3>'
                              '</p1:A>')
        context = XPathContext(root=root)

        self.check_value('fn:QName("", "person")', 'person')
        self.check_value('fn:QName((), "person")', 'person')
        self.check_value('fn:QName("http://www.example.com/ns/", "person")', 'person')
        self.check_value('fn:QName("http://www.example.com/ns/", "ht:person")', 'ht:person')
        self.wrong_type('fn:QName("", 2)')
        self.wrong_value('fn:QName("http://www.example.com/ns/", "xs:person")')

        self.check_value(
            'fn:prefix-from-QName(fn:QName("http://www.example.com/ns/", "ht:person"))', 'ht'
        )
        self.check_value(
            'fn:prefix-from-QName(fn:QName("http://www.example.com/ns/", "person"))', []
        )
        self.check_value('fn:prefix-from-QName(())', [])
        self.check_value('fn:prefix-from-QName(7)', TypeError)
        self.check_value('fn:prefix-from-QName("7")', ValueError)

        self.check_value(
            'fn:local-name-from-QName(fn:QName("http://www.example.com/ns/", "person"))', 'person'
        )
        self.check_value('fn:local-name-from-QName(())', [])
        self.check_value('fn:local-name-from-QName(8)', TypeError)
        self.check_value('fn:local-name-from-QName("8")', ValueError)

        self.check_value(
            'fn:namespace-uri-from-QName(fn:QName("http://www.example.com/ns/", "person"))',
            'http://www.example.com/ns/'
        )
        self.check_value('fn:namespace-uri-from-QName(())', [])
        self.check_value('fn:namespace-uri-from-QName(1)', TypeError)
        self.check_value('fn:namespace-uri-from-QName("1")', ValueError)
        self.check_selector("fn:namespace-uri-from-QName('p3:C3')", root, KeyError)
        self.check_selector("fn:namespace-uri-from-QName('p3:C3')", root, NameError,
                            namespaces={'p3': ''})

        self.check_value("fn:resolve-QName((), .)", [], context=context.copy())
        self.check_value("fn:resolve-QName('eg:C2', .)", '{http://www.example.com/ns/}C2',
                         context=context.copy())
        self.check_selector("fn:resolve-QName('p3:C3', .)", root, NameError, namespaces={'p3': ''})
        self.check_selector("fn:resolve-QName('p3:C3', .)", root, KeyError)
        self.check_value("fn:resolve-QName(2, .)", TypeError, context=context.copy())
        self.check_value("fn:resolve-QName('2', .)", ValueError, context=context.copy())
        self.check_value("fn:resolve-QName((), 4)", TypeError, context=context.copy())

        self.check_value("fn:namespace-uri-for-prefix('p1', .)", [], context=context.copy())
        self.check_value("fn:namespace-uri-for-prefix(4, .)", TypeError, context=context.copy())
        self.check_value("fn:namespace-uri-for-prefix('p1', 9)", TypeError, context=context.copy())
        self.check_value("fn:namespace-uri-for-prefix('eg', .)",
                         'http://www.example.com/ns/', context=context)
        self.check_selector("fn:namespace-uri-for-prefix('p3', .)",
                            root, NameError, namespaces={'p3': ''})

        # Note: default namespace for XPath 2 tests is 'http://www.example.com/ns/'
        self.check_value("fn:namespace-uri-for-prefix('', .)",
                         'http://www.example.com/ns/', context=context.copy())
        self.check_value("fn:namespace-uri-for-prefix((), .)",
                         'http://www.example.com/ns/', context=context.copy())

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

        with self.assertRaises(TypeError):
            select(root, "fn:in-scope-prefixes('')", namespaces, parser=type(self.parser))

    def test_string_constructors(self):
        self.check_value("xs:string(5.0)", '5.0')
        self.check_value('xs:string(" hello  ")', ' hello  ')
        self.check_value('xs:string("\thello \n")', '\thello \n')
        self.check_value('xs:string(())', [])

        self.check_value('xs:normalizedString("hello")', "hello")
        self.check_value('xs:normalizedString(" hello  ")', " hello  ")
        self.check_value('xs:normalizedString("\thello \n")', " hello  ")
        self.check_value('xs:normalizedString(())', [])

        self.check_value('xs:token(" hello  world ")', "hello world")
        self.check_value('xs:token("hello\t world\n")', "hello world")
        self.check_value('xs:token(())', [])

        self.check_value('xs:language(" en ")', "en")
        self.check_value('xs:language(" en-GB ")', "en-GB")
        self.check_value('xs:language("it-IT")', "it-IT")
        self.check_value('xs:language("i-klingon")', 'i-klingon')  # IANA-registered language
        self.check_value('xs:language("x-another-language-code")', 'x-another-language-code')
        self.wrong_value('xs:language("MoreThan8")')
        self.check_value('xs:language(())', [])

        self.check_value('xs:NMTOKEN(" :menù.09-_ ")', ":menù.09-_")
        self.wrong_value('xs:NMTOKEN("alpha+")')
        self.wrong_value('xs:NMTOKEN("hello world")')
        self.check_value('xs:NMTOKEN(())', [])

        self.check_value('xs:Name(" :base ")', ":base")
        self.check_value('xs:Name(" ::level_alpha ")', "::level_alpha")
        self.check_value('xs:Name("level-alpha")', "level-alpha")
        self.check_value('xs:Name("level.alpha\t\n")', "level.alpha")
        self.check_value('xs:Name("__init__ ")', "__init__")
        self.check_value('xs:Name("\u0110")', "\u0110")
        self.wrong_value('xs:Name("2_values")')
        self.wrong_value('xs:Name(" .values ")')
        self.wrong_value('xs:Name(" -values ")')
        self.check_value('xs:Name(())', [])

        self.check_value('xs:NCName(" base ")', "base")
        self.check_value('xs:NCName(" _level_alpha ")', "_level_alpha")
        self.check_value('xs:NCName("level-alpha")', "level-alpha")
        self.check_value('xs:NCName("level.alpha\t\n")', "level.alpha")
        self.check_value('xs:NCName("__init__ ")', "__init__")
        self.check_value('xs:NCName("\u0110")', "\u0110")
        self.wrong_value('xs:NCName("2_values")')
        self.wrong_value('xs:NCName(" .values ")')
        self.wrong_value('xs:NCName(" -values ")')
        self.check_value('xs:NCName(())', [])

        self.check_value('xs:ID("xyz")', 'xyz')
        self.check_value('xs:IDREF("xyz")', 'xyz')
        self.check_value('xs:ENTITY("xyz")', 'xyz')

    def test_qname_constructor(self):
        self.check_value('xs:QName("xs:element")', 'xs:element')
        self.assertRaises(KeyError, self.parser.parse, 'xs:QName("xsd:element")')

    def test_any_uri_constructor(self):
        self.check_value('xs:anyURI("")', '')
        self.check_value('xs:anyURI("https://example.com")', 'https://example.com')
        self.check_value('xs:anyURI("mailto:info@example.com")', 'mailto:info@example.com')
        self.check_value('xs:anyURI("urn:example:com")', 'urn:example:com')
        self.check_value('xs:anyURI("../principi/libertà.html")', '../principi/libertà.html')
        self.check_value('xs:anyURI("../principi/libert%E0.html")', '../principi/libert%E0.html')
        self.check_value('xs:anyURI("../path/page.html#frag")', '../path/page.html#frag')
        self.wrong_value('xs:anyURI("../path/page.html#frag1#frag2")')
        self.wrong_value('xs:anyURI("https://example.com/index%.html")')
        self.wrong_value('xs:anyURI("https://example.com/index.%html")')
        self.wrong_value('xs:anyURI("https://example.com/index.html%  frag")')
        self.check_value('xs:anyURI(())', [])

    def test_boolean_constructor(self):
        self.check_value('xs:boolean(())', [])
        self.check_value('xs:boolean(1)', True)
        self.check_value('xs:boolean(0)', False)

    def test_integer_constructors(self):
        self.wrong_value('xs:integer("hello")')
        self.check_value('xs:integer("19")', 19)
        self.check_value("xs:integer('-5')", -5)

        self.wrong_value('xs:nonNegativeInteger("-1")')
        self.wrong_value('xs:nonNegativeInteger(-1)')
        self.check_value('xs:nonNegativeInteger(0)', 0)
        self.check_value('xs:nonNegativeInteger(1000)', 1000)
        self.wrong_value('xs:positiveInteger(0)')
        self.check_value('xs:positiveInteger("1")', 1)
        self.wrong_value('xs:negativeInteger(0)')
        self.check_value('xs:negativeInteger(-1)', -1)
        self.wrong_value('xs:nonPositiveInteger(1)')
        self.check_value('xs:nonPositiveInteger(0)', 0)
        self.check_value('xs:nonPositiveInteger("-1")', -1)

    def test_limited_integer_constructors(self):
        self.wrong_value('xs:long("true")')
        self.wrong_value('xs:long("340282366920938463463374607431768211456")')
        self.check_value('xs:long("-20")', -20)
        self.wrong_value('xs:int("-20 91")')
        self.wrong_value('xs:int("9223372036854775808")')
        self.check_value('xs:int("-9223372036854775808")', -2**63)
        self.check_value('xs:int("4611686018427387904")', 2**62)
        self.wrong_value('xs:short("40000")')
        self.check_value('xs:short("9999")', 9999)
        self.check_value('xs:short(-9999)', -9999)
        self.wrong_value('xs:byte(-129)')
        self.wrong_value('xs:byte(128)')
        self.check_value('xs:byte("-128")', -128)
        self.check_value('xs:byte(127)', 127)
        self.check_value('xs:byte(-90)', -90)

        self.wrong_value('xs:unsignedLong("-10")')
        self.check_value('xs:unsignedLong("3")', 3)
        self.wrong_value('xs:unsignedInt("-9223372036854775808")')
        self.check_value('xs:unsignedInt("9223372036854775808")', 2**63)
        self.wrong_value('xs:unsignedShort("-1")')
        self.check_value('xs:unsignedShort("0")', 0)
        self.wrong_value('xs:unsignedByte(-128)')
        self.check_value('xs:unsignedByte("128")', 128)

    def test_other_numerical_constructors(self):
        self.wrong_value('xs:decimal("hello")')
        self.check_value('xs:decimal("19")', 19)
        self.check_value('xs:decimal("19")', Decimal)

        self.wrong_value('xs:double("world")')
        self.check_value('xs:double("39.09")', 39.09)
        self.check_value('xs:double(-5)', -5.0)
        self.check_value('xs:double(-5)', float)

        self.wrong_value('xs:float("..")')
        self.check_value('xs:float(25.05)', 25.05)
        self.check_value('xs:float(-0.00001)', -0.00001)
        self.check_value('xs:float(0.00001)', float)

    def test_datetime_function(self):
        tz0 = None
        tz1 = Timezone(datetime.timedelta(hours=5, minutes=24))
        self.check_value('fn:dateTime(xs:date("1999-12-31"), xs:time("12:00:00"))',
                         datetime.datetime(1999, 12, 31, 12, 0, tzinfo=tz0))
        self.check_value('fn:dateTime(xs:date("1999-12-31"), xs:time("24:00:00"))',
                         datetime.datetime(1999, 12, 31, 0, 0, tzinfo=tz0))

    def test_datetime_constructor(self):
        tz0 = None
        tz1 = Timezone(datetime.timedelta(hours=5, minutes=24))
        self.check_value(
            'xs:dateTime("1969-07-20T20:18:00")', DateTime(1969, 7, 20, 20, 18, tzinfo=tz0)
        )
        self.check_value('xs:dateTime("2000-05-10T21:30:00+05:24")',
                         datetime.datetime(2000, 5, 10, hour=21, minute=30, tzinfo=tz1))
        self.check_value('xs:dateTime("1999-12-31T24:00:00")',
                         datetime.datetime(2000, 1, 1, 0, 0, tzinfo=tz0))

        self.wrong_value('xs:dateTime("2000-05-10t21:30:00+05:24")')
        self.wrong_value('xs:dateTime("2000-5-10T21:30:00+05:24")')
        self.wrong_value('xs:dateTime("2000-05-10T21:3:00+05:24")')
        self.wrong_value('xs:dateTime("2000-05-10T21:13:0+05:24")')
        self.wrong_value('xs:dateTime("2000-05-10T21:13:0")')

    def test_time_constructor(self):
        tz0 = None
        tz1 = Timezone(datetime.timedelta(hours=5, minutes=24))
        self.check_value('xs:time("21:30:00")', datetime.datetime(2000, 1, 1, 21, 30, tzinfo=tz0))
        self.check_value('xs:time("11:15:48+05:24")',
                         datetime.datetime(2000, 1, 1, 11, 15, 48, tzinfo=tz1))

    def test_date_constructor(self):
        tz0 = None
        tz2 = Timezone(datetime.timedelta(hours=-14, minutes=0))
        self.check_value('xs:date("2017-01-19")', datetime.datetime(2017, 1, 19, tzinfo=tz0))
        self.check_value('xs:date("2011-11-11-14:00")', datetime.datetime(2011, 11, 11, tzinfo=tz2))
        self.wrong_value('xs:date("2011-11-11-14:01")')
        self.wrong_value('xs:date("11-11-11")')

    def test_gregorian_constructors(self):
        tz0 = None
        tz1 = Timezone(datetime.timedelta(hours=5, minutes=24))
        tz2 = Timezone(datetime.timedelta(hours=-14, minutes=0))
        self.check_value('xs:gDay("---30")', datetime.datetime(2000, 1, 30, tzinfo=tz0))
        self.check_value('xs:gDay("---21+05:24")', datetime.datetime(2000, 1, 21, tzinfo=tz1))
        self.wrong_value('xs:gDay("---32")')
        self.wrong_value('xs:gDay("--19")')

        self.check_value('xs:gMonth("--09")', datetime.datetime(2000, 9, 1, tzinfo=tz0))
        self.check_value('xs:gMonth("--12")', datetime.datetime(2000, 12, 1, tzinfo=tz0))
        self.wrong_value('xs:gMonth("--9")')
        self.wrong_value('xs:gMonth("-09")')
        self.wrong_value('xs:gMonth("--13")')

        self.check_value('xs:gMonthDay("--07-02")', datetime.datetime(2000, 7, 2, tzinfo=tz0))
        self.check_value('xs:gMonthDay("--07-02-14:00")', datetime.datetime(2000, 7, 2, tzinfo=tz2))
        self.wrong_value('xs:gMonthDay("--7-02")')
        self.wrong_value('xs:gMonthDay("-07-02")')
        self.wrong_value('xs:gMonthDay("--07-32")')

        self.check_value('xs:gYear("2004")', datetime.datetime(2004, 1, 1, tzinfo=tz0))
        self.check_value('xs:gYear("-2004")', GregorianYear10(-2004, tzinfo=tz0))
        self.check_value('xs:gYear("-12540")', GregorianYear10(-12540, tzinfo=tz0))
        self.check_value('xs:gYear("12540")', GregorianYear10(12540, tzinfo=tz0))
        self.wrong_value('xs:gYear("84")')
        self.wrong_value('xs:gYear("821")')
        self.wrong_value('xs:gYear("84")')

        self.check_value('xs:gYearMonth("2004-02")', datetime.datetime(2004, 2, 1, tzinfo=tz0))
        self.wrong_value('xs:gYearMonth("2004-2")')
        self.wrong_value('xs:gYearMonth("204-02")')

    def test_year_from_datetime_function(self):
        self.check_value('fn:year-from-dateTime(xs:dateTime("1999-05-31T13:20:00-05:00"))', 1999)
        self.check_value('fn:year-from-dateTime(xs:dateTime("1999-05-31T21:30:00-05:00"))', 1999)
        self.check_value('fn:year-from-dateTime(xs:dateTime("1999-12-31T19:20:00"))', 1999)
        self.check_value('fn:year-from-dateTime(xs:dateTime("1999-12-31T24:00:00"))', 2000)

    def test_month_from_datetime_function(self):
        self.check_value('fn:month-from-dateTime(xs:dateTime("1999-05-31T13:20:00-05:00"))', 5)
        self.check_value('fn:month-from-dateTime(xs:dateTime("1999-12-31T19:20:00-05:00"))', 12)
        # self.check_value('fn:month-from-dateTime(fn:adjust-dateTime-to-timezone(xs:dateTime('
        #                 '"1999-12-31T19:20:00-05:00"), xs:dayTimeDuration("PT0S")))', 1)

    def test_day_from_datetime_function(self):
        self.check_value('fn:day-from-dateTime(xs:dateTime("1999-05-31T13:20:00-05:00"))', 31)
        self.check_value('fn:day-from-dateTime(xs:dateTime("1999-12-31T20:00:00-05:00"))', 31)
        # self.check_value('fn:day-from-dateTime(fn:adjust-dateTime-to-timezone(xs:dateTime('
        #                  '"1999-12-31T19:20:00-05:00"), xs:dayTimeDuration("PT0S")))', 1)

    def test_hours_from_datetime_function(self):
        self.check_value('fn:hours-from-dateTime(xs:dateTime("1999-05-31T08:20:00-05:00")) ', 8)
        self.check_value('fn:hours-from-dateTime(xs:dateTime("1999-12-31T21:20:00-05:00"))', 21)
        # self.check_value('fn:hours-from-dateTime(fn:adjust-dateTime-to-timezone(xs:dateTime('
        #                  '"1999-12-31T21:20:00-05:00"), xs:dayTimeDuration("PT0S")))', 2)
        self.check_value('fn:hours-from-dateTime(xs:dateTime("1999-12-31T12:00:00")) ', 12)
        self.check_value('fn:hours-from-dateTime(xs:dateTime("1999-12-31T24:00:00"))', 0)

    def test_minutes_from_datetime_function(self):
        self.check_value('fn:minutes-from-dateTime(xs:dateTime("1999-05-31T13:20:00-05:00"))', 20)
        self.check_value('fn:minutes-from-dateTime(xs:dateTime("1999-05-31T13:30:00+05:30"))', 30)

    def test_seconds_from_datetime_function(self):
        self.check_value('fn:seconds-from-dateTime(xs:dateTime("1999-05-31T13:20:00-05:00"))', 0)

    def test_timezone_from_datetime_function(self):
        self.check_value('fn:timezone-from-dateTime(xs:dateTime("1999-05-31T13:20:00-05:00"))',
                         DayTimeDuration(seconds=-18000))

    def test_year_from_date_function(self):
        self.check_value('fn:year-from-date(xs:date("1999-05-31"))', 1999)
        self.check_value('fn:year-from-date(xs:date("2000-01-01+05:00"))', 2000)

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
        self.check_value('fn:seconds-from-time(xs:time("03:59:59.000001"))', 59.000001)

    def test_timezone_from_time_function(self):
        self.check_value('fn:timezone-from-time(xs:time("13:20:00-05:00"))',
                         DayTimeDuration.fromstring('-PT5H'))

    def test_subtract_datetimes(self):
        context = XPathContext(root=self.etree.XML('<A/>'), timezone=Timezone.fromstring('-05:00'))
        self.check_value('xs:dateTime("2000-10-30T06:12:00") - xs:dateTime("1999-11-28T09:00:00Z")',
                         DayTimeDuration.fromstring('P337DT2H12M'), context)
        self.check_value('xs:dateTime("2000-10-30T06:12:00") - xs:dateTime("1999-11-28T09:00:00Z")',
                         DayTimeDuration.fromstring('P336DT21H12M'))

    def test_subtract_dates(self):
        context = XPathContext(root=self.etree.XML('<A/>'), timezone=Timezone.fromstring('Z'))
        self.check_value('xs:date("2000-10-30") - xs:date("1999-11-28")',
                         DayTimeDuration.fromstring('P337D'), context)
        context.timezone = Timezone.fromstring('+05:00')
        self.check_value('xs:date("2000-10-30") - xs:date("1999-11-28Z")',
                         DayTimeDuration.fromstring('P336DT19H'), context)
        self.check_value('xs:date("2000-10-15-05:00") - xs:date("2000-10-10+02:00")',
                         DayTimeDuration.fromstring('P5DT7H'))

        # BCE test cases
        self.check_value('xs:date("0001-01-01") - xs:date("-0001-01-01")',
                         DayTimeDuration.fromstring('P366D'))
        self.check_value('xs:date("-0001-01-01") - xs:date("-0001-01-01")',
                         DayTimeDuration.fromstring('P0D'))
        self.check_value('xs:date("-0001-01-01") - xs:date("0001-01-01")',
                         DayTimeDuration.fromstring('-P366D'))

        self.check_value('xs:date("-0001-01-01") - xs:date("-0001-01-02")',
                         DayTimeDuration.fromstring('-P1D'))
        self.check_value('xs:date("-0001-01-04") - xs:date("-0001-01-01")',
                         DayTimeDuration.fromstring('P3D'))

        self.check_value('xs:date("0200-01-01") - xs:date("-0121-01-01")',
                         DayTimeDuration.fromstring('P116878D'))
        self.check_value('xs:date("-0201-01-01") - xs:date("0120-01-01")',
                         DayTimeDuration.fromstring('-P116877D'))

    def test_subtract_times(self):
        context = XPathContext(root=self.etree.XML('<A/>'), timezone=Timezone.fromstring('-05:00'))
        self.check_value('xs:time("11:12:00Z") - xs:time("04:00:00")',
                         DayTimeDuration.fromstring('PT2H12M'), context)
        self.check_value('xs:time("11:00:00-05:00") - xs:time("21:30:00+05:30")',
                         DayTimeDuration.fromstring('PT0S'), context)
        self.check_value('xs:time("17:00:00-06:00") - xs:time("08:00:00+09:00")',
                         DayTimeDuration.fromstring('PT24H'), context)
        self.check_value('xs:time("24:00:00") - xs:time("23:59:59")',
                         DayTimeDuration.fromstring('-PT23H59M59S'), context)

    def test_add_year_month_duration_to_datetime(self):
        self.check_value('xs:dateTime("2000-10-30T11:12:00") + xs:yearMonthDuration("P1Y2M")',
                         DateTime.fromstring("2001-12-30T11:12:00"))

    def test_add_day_time_duration_to_datetime(self):
        self.check_value('xs:dateTime("2000-10-30T11:12:00") + xs:dayTimeDuration("P3DT1H15M")',
                         DateTime.fromstring("2000-11-02T12:27:00"))

    def test_subtract_year_month_duration_from_datetime(self):
        self.check_value('xs:dateTime("2000-10-30T11:12:00") - xs:yearMonthDuration("P0Y2M")',
                         DateTime.fromstring("2000-08-30T11:12:00"))
        self.check_value('xs:dateTime("2000-10-30T11:12:00") - xs:yearMonthDuration("P1Y2M")',
                         DateTime.fromstring("1999-08-30T11:12:00"))

    def test_subtract_day_time_duration_from_datetime(self):
        self.check_value('xs:dateTime("2000-10-30T11:12:00") - xs:dayTimeDuration("P3DT1H15M")',
                         DateTime.fromstring("2000-10-27T09:57:00"))

    def test_add_year_month_duration_to_date(self):
        self.check_value('xs:date("2000-10-30") + xs:yearMonthDuration("P1Y2M")',
                         Date.fromstring('2001-12-30'))

    def test_subtract_year_month_duration_from_date(self):
        self.check_value('xs:date("2000-10-30") - xs:yearMonthDuration("P1Y2M")',
                         Date.fromstring('1999-08-30'))
        self.check_value('xs:date("2000-02-29Z") - xs:yearMonthDuration("P1Y")',
                         Date.fromstring('1999-02-28Z'))
        self.check_value('xs:date("2000-10-31-05:00") - xs:yearMonthDuration("P1Y1M")',
                         Date.fromstring('1999-09-30-05:00'))

    def test_subtract_day_time_duration_from_date(self):
        self.check_value('xs:date("2000-10-30") - xs:dayTimeDuration("P3DT1H15M")',
                         Date.fromstring('2000-10-26'))

    def test_add_day_time_duration_to_time(self):
        self.check_value('xs:time("11:12:00") + xs:dayTimeDuration("P3DT1H15M")',
                         Time.fromstring('12:27:00'))
        self.check_value('xs:time("23:12:00+03:00") + xs:dayTimeDuration("P1DT3H15M")',
                         Time.fromstring('02:27:00+03:00'))

    def test_subtract_day_time_duration_to_time(self):
        self.check_value('xs:time("11:12:00") - xs:dayTimeDuration("P3DT1H15M")',
                         Time.fromstring('09:57:00'))
        self.check_value('xs:time("08:20:00-05:00") - xs:dayTimeDuration("P23DT10H10M")',
                         Time.fromstring('22:10:00-05:00'))

    def test_duration_constructor(self):
        self.check_value('xs:duration("P3Y5M1D")', (41, 86400))
        self.check_value('xs:duration("P3Y5M1DT1H")', (41, 90000))
        self.check_value('xs:duration("P3Y5M1DT1H3M2.01S")', (41, Decimal('90182.01')))
        self.wrong_value('xs:duration("P3Y5M1X")')
        self.assertRaises(TypeError, self.parser.parse, 'xs:duration(1)')

    def test_year_month_duration_constructor(self):

        self.check_value('xs:yearMonthDuration("P3Y5M")', (41, 0))
        self.check_value('xs:yearMonthDuration("-P15M")', (-15, 0))
        self.check_value('xs:yearMonthDuration("-P20Y18M")',
                         YearMonthDuration.fromstring("-P21Y6M"))
        self.wrong_value('xs:yearMonthDuration("-P15M1D")')
        self.wrong_value('xs:yearMonthDuration("P15MT1H")')

    def test_day_time_duration_constructor(self):
        self.check_value('xs:dayTimeDuration("-P2DT15H")', DayTimeDuration(seconds=-226800))
        self.check_value('xs:dayTimeDuration("PT240H")', DayTimeDuration.fromstring("P10D"))
        self.check_value('xs:dayTimeDuration("P365D")', DayTimeDuration.fromstring("P365D"))
        self.check_value('xs:dayTimeDuration("-P2DT15H0M0S")',
                         DayTimeDuration.fromstring('-P2DT15H'))
        self.check_value('xs:dayTimeDuration("P3DT10H")', DayTimeDuration.fromstring("P3DT10H"))
        self.check_value('xs:dayTimeDuration("PT1S")', (0, 1))
        self.check_value('xs:dayTimeDuration("PT0S")', (0, 0))
        self.wrong_value('xs:yearMonthDuration("P1MT10H")')

    def test_years_from_duration_function(self):
        self.check_value('fn:years-from-duration(())', [])
        self.check_value('fn:years-from-duration(xs:yearMonthDuration("P20Y15M"))', 21)
        self.check_value('fn:years-from-duration(xs:yearMonthDuration("-P15M"))', -1)
        self.check_value('fn:years-from-duration(xs:dayTimeDuration("-P2DT15H"))', 0)

    def test_months_from_duration_function(self):
        self.check_value('fn:months-from-duration(xs:yearMonthDuration("P20Y15M"))', 3)
        self.check_value('fn:months-from-duration(xs:yearMonthDuration("-P20Y18M"))', -6)
        self.check_value('fn:months-from-duration(xs:dayTimeDuration("-P2DT15H0M0S"))', 0)

    def test_days_from_duration_function(self):
        self.check_value('fn:days-from-duration(xs:dayTimeDuration("P3DT10H"))', 3)
        self.check_value('fn:days-from-duration(xs:dayTimeDuration("P3DT55H"))', 5)
        self.check_value('fn:days-from-duration(xs:yearMonthDuration("P3Y5M"))', 0)

    def test_hours_from_duration_function(self):
        self.check_value('fn:hours-from-duration(xs:dayTimeDuration("P3DT10H"))', 10)
        self.check_value('fn:hours-from-duration(xs:dayTimeDuration("P3DT12H32M12S"))', 12)
        self.check_value('fn:hours-from-duration(xs:dayTimeDuration("PT123H"))', 3)
        self.check_value('fn:hours-from-duration(xs:dayTimeDuration("-P3DT10H"))', -10)

    def test_minutes_from_duration_function(self):
        self.check_value('fn:minutes-from-duration(xs:dayTimeDuration("P3DT10H"))', 0)
        self.check_value('fn:minutes-from-duration(xs:dayTimeDuration("-P5DT12H30M"))', -30)

    def test_seconds_from_duration_function(self):
        self.check_value('fn:seconds-from-duration(xs:dayTimeDuration("P3DT10H12.5S"))', 12.5)
        self.check_value('fn:seconds-from-duration(xs:dayTimeDuration("-PT256S"))', -16.0)

    def test_year_month_duration_operators(self):
        self.check_value('xs:yearMonthDuration("P2Y11M") + xs:yearMonthDuration("P3Y3M")',
                         YearMonthDuration(months=74))
        self.check_value('xs:yearMonthDuration("P2Y11M") - xs:yearMonthDuration("P3Y3M")',
                         YearMonthDuration(months=-4))
        self.check_value('xs:yearMonthDuration("P2Y11M") * 2.3',
                         YearMonthDuration.fromstring('P6Y9M'))
        self.check_value('xs:yearMonthDuration("P2Y11M") div 1.5',
                         YearMonthDuration.fromstring('P1Y11M'))
        self.check_value('xs:yearMonthDuration("P3Y4M") div xs:yearMonthDuration("-P1Y4M")', -2.5)

    def test_day_time_duration_operators(self):
        self.check_value('xs:dayTimeDuration("P2DT12H5M") + xs:dayTimeDuration("P5DT12H")',
                         DayTimeDuration.fromstring('P8DT5M'))
        self.check_value('xs:dayTimeDuration("P2DT12H") - xs:dayTimeDuration("P1DT10H30M")',
                         DayTimeDuration.fromstring('P1DT1H30M'))
        self.check_value('xs:dayTimeDuration("PT2H10M") * 2.1',
                         DayTimeDuration.fromstring('PT4H33M'))
        self.check_value('xs:dayTimeDuration("P1DT2H30M10.5S") div 1.5',
                         DayTimeDuration.fromstring('PT17H40M7S'))
        self.check_value(
            'xs:dayTimeDuration("P2DT53M11S") div xs:dayTimeDuration("P1DT10H")',
            Decimal('1.437834967320261437908496732')
        )

    def test_hex_binary_constructor(self):
        self.check_value('xs:hexBinary("84")', b'3834')
        self.check_value('xs:hexBinary(xs:hexBinary("84"))', b'3834')
        self.wrong_type('xs:hexBinary(12)')

    def test_base64_binary_constructor(self):
        self.check_value('xs:base64Binary("84")', b'ODQ=\n')
        self.check_value('xs:base64Binary(xs:base64Binary("84"))', b'ODQ=\n')
        self.check_value('xs:base64Binary("abcefghi")', b'YWJjZWZnaGk=\n')
        self.wrong_type('xs:base64Binary(1e2)')
        self.wrong_type('xs:base64Binary(1.1)')

    def test_document_node_accessor(self):
        document = self.etree.parse(io.StringIO('<A/>'))
        context = XPathContext(root=document)
        self.wrong_syntax("document-node(A)")
        self.wrong_syntax("document-node(*)")
        self.wrong_syntax("document-node(true())")
        self.wrong_syntax("document-node(node())")
        self.wrong_type("document-node(element(A), 1)")
        self.check_select("document-node()", [], context)
        self.check_select("self::document-node()", [document], context)
        self.check_selector("self::document-node(element(A))", document, [document])
        self.check_selector("self::document-node(element(B))", document, [])

    def test_element_accessor(self):
        element = self.etree.Element('schema')
        context = XPathContext(root=element)
        self.wrong_syntax("element('name')")
        self.wrong_syntax("element(A, 'name')")
        self.check_select("element()", [], context)
        self.check_select("self::element()", [element], context)
        self.check_select("self::element(schema)", [element], context)
        self.check_select("self::element(schema, xs:string)", [], context)

        root = self.etree.XML('<A a="10">text<B/>tail<B/></A>')
        context = XPathContext(root)
        self.check_select("element(*)", root[:], context)
        self.check_select("element(B)", root[:], context)
        self.check_select("element(A)", [], context)

    def test_node_and_node_accessors(self):
        element = self.etree.Element('schema')
        element.attrib.update([('id', '0212349350')])

        context = XPathContext(root=element)
        self.check_select("self::node()", [element], context)
        self.check_select("self::attribute()", ['0212349350'], context)

        context.item = 7
        self.check_select("node()", [], context)
        context.item = 10.2
        self.check_select("node()", [], context)

    def test_count_function(self):
        super(XPath2ParserTest, self).test_count_function()
        root = self.etree.XML('<root/>')
        self.check_selector("count(5)", root, 1)
        self.check_value("count((0, 1, 2 + 1, 3 - 1))", 4)

    def test_node_accessor_functions(self):
        root = self.etree.XML('<A xmlns:ns0="%s" id="10"><B1><C1 /><C2 ns0:nil="true" /></B1>'
                              '<B2 /><B3>simple text</B3></A>' % XSI_NAMESPACE)
        self.check_selector("node-name(.)", root, 'A')
        self.check_selector("node-name(/A/B1)", root, 'B1')
        self.check_selector("node-name(/A/*)", root, TypeError)  # Not allowed more than one item!
        self.check_selector("nilled(./B1/C1)", root, False)
        self.check_selector("nilled(./B1/C2)", root, True)

        root = self.etree.XML('<A id="10"><B1> a text, <C1 /><C2>an inner text, </C2>a tail, </B1>'
                              '<B2 /><B3>an ending text </B3></A>')
        self.check_selector("string(.)", root, ' a text, an inner text, a tail, an ending text ')
        self.check_selector("data(.)", root, ' a text, an inner text, a tail, an ending text ')
        self.check_selector("data(.)", root, UntypedAtomic)

    def test_node_set_id_function(self):
        # Backward compatibility with fs:id() of XPath 1
        root = self.etree.XML('<A><B1 xml:id="foo"/><B2/><B3 xml:id="bar"/><B4 xml:id="baz"/></A>')
        self.check_selector('element-with-id("foo")', root, [root[0]])

        self.check_selector('id("foo")', root, ValueError)

        doc = self.etree.parse(
            io.StringIO('<A><B1 xml:id="foo"/><B2/><B3 xml:id="bar"/><B4 xml:id="baz"/></A>')
        )
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
        self.check_selector("idref('ID21256')", doc, [])
        self.check_selector("idref('E21256')", doc, [root[0][0]])

    def test_union_intersect_except_operators(self):
        root = self.etree.XML('<A><B1><C1/><C2/><C3/></B1><B2><C1/><C2/><C3/><C4/></B2><B3/></A>')
        self.check_selector('/A/B2 union /A/B1', root, root[:2])
        self.check_selector('/A/B2 union /A/*', root, root[:])

        self.check_selector('/A/B2 intersect /A/B1', root, [])
        self.check_selector('/A/B2 intersect /A/*', root, [root[1]])
        self.check_selector('/A/B1/* intersect /A/B2/*', root, [])
        self.check_selector('/A/B1/* intersect /A/*/*', root, root[0][:])

        self.check_selector('/A/B2 except /A/B1', root, root[1:2])
        self.check_selector('/A/* except /A/B2', root, [root[0], root[2]])
        self.check_selector('/A/*/* except /A/B2/*', root, root[0][:])
        self.check_selector('/A/B2/* except /A/B1/*', root, root[1][:])
        self.check_selector('/A/B2/* except /A/*/*', root, [])

        root = self.etree.XML('<root><A/><B/><C/></root>')

        # From variables like XPath 2.0 examples
        context = XPathContext(root, variables={
            'seq1': root[:2],  # (A, B)
            'seq2': root[:2],  # (A, B)
            'seq3': root[1:],  # (B, C)
        })
        self.check_select('$seq1 union $seq2', root[:2], context=context)
        self.check_select('$seq2 union $seq3', root[:], context=context)
        self.check_select('$seq1 intersect $seq2', root[:2], context=context)
        self.check_select('$seq2 intersect $seq3', root[1:2], context=context)
        self.check_select('$seq1 except $seq2', [], context=context)
        self.check_select('$seq2 except $seq3', root[:1], context=context)

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
        self.check_value('deep-equal($xt/name[1], "Peter Parker")', False, context=context)

        root = self.etree.XML("""<A xmlns="http://xpath.test/ns"><B1/><B2/><B3/></A>""")
        context = XPathContext(root, variables={'xt': root})
        self.check_value('deep-equal($xt, $xt)', True, context=context)

        self.check_value('deep-equal((1, 2, 3), (1, 2, 3))', True)
        self.check_value('deep-equal((1, 2, 3), (1, 2, 4))', False)
        self.check_value("deep-equal((1, 2, 3), (1, '2', 3))", False)
        self.check_value("deep-equal(('1', '2', '3'), ('1', '2', '3'))", True)
        self.check_value("deep-equal(('1', '2', '3'), ('1', '4', '3'))", False)
        self.check_value("deep-equal((1, 2, 3), (1, 2, 3), 'en_US.UTF-8')", True)

    def test_node_comparison_operators(self):
        # Test cases from https://www.w3.org/TR/xpath20/#id-node-comparisons
        root = self.etree.XML('''
        <books>
            <book><isbn>1558604820</isbn><call>QA76.9 C3845</call></book>
            <book><isbn>0070512655</isbn><call>QA76.9 C3846</call></book>
            <book><isbn>0131477005</isbn><call>QA76.9 C3847</call></book>
        </books>''')
        self.check_selector('/books/book[isbn="1558604820"] is /books/book[call="QA76.9 C3845"]',
                            root, True)
        self.check_selector('/books/book[isbn="0070512655"] is /books/book[call="QA76.9 C3847"]',
                            root, False)
        self.check_selector('/books/book[isbn="not a code"] is /books/book[call="QA76.9 C3847"]',
                            root, [])

        root = self.etree.XML('''
        <transactions>
            <purchase><parcel>28-451</parcel></purchase>
            <sale><parcel>33-870</parcel></sale>
            <purchase><parcel>15-392</parcel></purchase>
            <sale><parcel>35-530</parcel></sale>
            <purchase><parcel>10-639</parcel></purchase>
            <purchase><parcel>10-639</parcel></purchase>
            <sale><parcel>39-729</parcel></sale>
        </transactions>''')

        self.check_selector(
            '/transactions/purchase[parcel="28-451"] << /transactions/sale[parcel="33-870"]',
            root, True
        )
        self.check_selector(
            '/transactions/purchase[parcel="15-392"] >> /transactions/sale[parcel="33-870"]',
            root, True
        )
        self.check_selector(
            '/transactions/purchase[parcel="10-639"] >> /transactions/sale[parcel="33-870"]',
            root, TypeError
        )

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

    def test_adjust_time_to_timezone_function(self):
        context = XPathContext(root=self.etree.XML('<A/>'), timezone=Timezone.fromstring('-05:00'),
                               variables={'tz': DayTimeDuration.fromstring("-PT10H")})

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

    def test_context_functions(self):
        context = XPathContext(root=self.etree.XML('<A/>'))
        self.check_value('fn:current-dateTime()', DateTime.fromdatetime(context.current_dt),
                         context=context)
        self.check_value(path='fn:current-date()', context=context,
                         expected=Date.fromdatetime(context.current_dt.date()),)
        self.check_value(path='fn:current-time()', context=context,
                         expected=Time.fromdatetime(context.current_dt),)
        self.check_value(path='fn:implicit-timezone()', context=context,
                         expected=Timezone(datetime.timedelta(seconds=time.timezone)),)
        self.check_value('fn:static-base-uri()', context=context)

        parser = XPath2Parser(strict=True, base_uri='http://example.com/ns/')
        self.assertEqual(parser.parse('fn:static-base-uri()').evaluate(context),
                         'http://example.com/ns/')

    def test_empty_sequence_type(self):
        self.check_value("() treat as empty-sequence()", [])
        self.check_value("6 treat as empty-sequence()", TypeError)
        self.wrong_syntax("empty-sequence()")

        context = XPathContext(root=self.etree.XML('<A/>'))
        self.check_value("() instance of empty-sequence()", expected=True, context=context)
        self.check_value(". instance of empty-sequence()", expected=False, context=context)

    def test_item_sequence_type(self):
        self.check_value("4 treat as item()", [4])
        self.check_value("() treat as item()", TypeError)
        self.wrong_syntax("item()")

        context = XPathContext(root=self.etree.XML('<A/>'))
        self.check_value(". instance of item()", expected=True, context=context)
        self.check_value("() instance of item()", expected=False, context=context)

        context = XPathContext(root=self.etree.parse(io.StringIO('<A/>')))
        self.check_value(". instance of item()", expected=True, context=context)
        self.check_value("() instance of item()", expected=False, context=context)

    def test_doc_functions(self):
        root = self.etree.XML("<A><B1><C1/></B1><B2/><B3/></A>")
        doc = self.etree.parse(io.StringIO("<a><b1><c1/></b1><b2/><b3/></a>"))
        context = XPathContext(root, documents={'tns0': doc})

        self.check_value("fn:doc(())", context=context)
        self.check_value("fn:doc-available(())", False, context=context)

        self.check_value("fn:doc('tns0')", doc, context=context)
        self.check_value("fn:doc-available('tns0')", True, context=context)

        self.check_value("fn:doc('tns1')", ValueError, context=context)
        self.check_value("fn:doc-available('tns1')", False, context=context)

    def test_collection_function(self):
        root = self.etree.XML("<A><B1><C1/></B1><B2/><B3/></A>")
        doc1 = self.etree.parse(io.StringIO("<a><b1><c1/></b1><b2/><b3/></a>"))
        doc2 = self.etree.parse(io.StringIO("<a1><b11><c11/></b11><b12/><b13/></a1>"))
        context = XPathContext(root, collections={'tns0': [doc1, doc2]})

        self.check_value("fn:collection()", ValueError, context=context)
        self.check_value("fn:collection('tns0')", ValueError, context=context)
        context.default_collection = context.collections['tns0']
        self.check_value("fn:collection()", [doc1, doc2], context=context)
        self.check_value("fn:collection('tns0')", ValueError, context=context)

    def test_root_function(self):
        root = self.etree.XML("<A><B1><C1/></B1><B2/><B3/></A>")
        self.check_value("root()", root, context=XPathContext(root))
        self.check_value("root()", root, context=XPathContext(root, item=root[2]))

        doc = self.etree.XML("<a><b1><c1/></b1><b2/><b3/></a>")

        context = XPathContext(root, variables={'elem': doc[1]})
        self.check_value("fn:root($elem)", context=context.copy())

        context = XPathContext(root, variables={'elem': doc[1]}, documents={'.': doc})
        self.check_value("root($elem)", doc, context=context)

    def test_error_function(self):
        self.assertRaises(ElementPathError, self.check_value, "fn:error()")

    def test_static_analysis_phase(self):
        self.check_value('fn:concat($word, fn:lower-case(" BETA"))', 'alpha beta')
        self.check_value('fn:concat($word, fn:lower-case(10))', TypeError)
        self.check_value('fn:concat($unknown, fn:lower-case(10))', TypeError)


@unittest.skipIf(lxml_etree is None, "The lxml library is not installed")
class LxmlXPath2ParserTest(XPath2ParserTest):
    etree = lxml_etree


if __name__ == '__main__':
    unittest.main()
