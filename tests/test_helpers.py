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
import datetime
import re
import unittest
import math
from decimal import Decimal
from xml.etree import ElementTree
from elementpath.helpers import LazyPattern, days_from_common_era, \
    months2days, round_number, is_idrefs, collapse_white_spaces, escape_json_string, \
    get_double, numeric_equal, numeric_not_equal, equal, not_equal, \
    match_wildcard, unescape_json_string, iter_sequence, split_function_test
from elementpath.xpath30.xpath30_helpers import decimal_to_string, int_to_roman, \
    int_to_month, int_to_weekday, int_to_words, int_to_alphabetic, week_in_month, \
    to_ordinal_en, to_ordinal_it, format_digits, ordinal_suffix


class HelperFunctionsTest(unittest.TestCase):

    def test_lazy_pattern(self):
        pattern = LazyPattern(r'^[^\d\W][\w.\-\u00B7\u0300-\u036F\u203F\u2040]*$')
        self.assertIsInstance(pattern, LazyPattern)

        class TestPatterns:
            pattern = LazyPattern(r'^[^\d\W][\w.\-\u00B7\u0300-\u036F\u203F\u2040]*$')

        self.assertIsInstance(TestPatterns.pattern, re.Pattern)
        self.assertIsNotNone(TestPatterns.pattern.match('foo'))
        self.assertIsNone(TestPatterns.pattern.match('foo:bar'))

    def test_node_is_idref_function(self):
        self.assertTrue(is_idrefs(ElementTree.XML('<A>xyz</A>').text))
        self.assertTrue(is_idrefs(ElementTree.XML('<A>xyz abc</A>').text))
        self.assertFalse(is_idrefs(ElementTree.XML('<A>12345</A>').text))
        self.assertTrue(is_idrefs('alpha'))
        self.assertTrue(is_idrefs('alpha beta'))
        self.assertFalse(is_idrefs('12345'))

    def test_days_from_common_era_function(self):
        days4y = 365 * 3 + 366
        days100y = days4y * 24 + 365 * 4
        days400y = days100y * 4 + 1

        self.assertEqual(days_from_common_era(0), 0)
        self.assertEqual(days_from_common_era(1), 365)
        self.assertEqual(days_from_common_era(3), 365 * 3)
        self.assertEqual(days_from_common_era(4), days4y)
        self.assertEqual(days_from_common_era(100), days100y)
        self.assertEqual(days_from_common_era(200), days100y * 2)
        self.assertEqual(days_from_common_era(300), days100y * 3)
        self.assertEqual(days_from_common_era(400), days400y)
        self.assertEqual(days_from_common_era(800), 2 * days400y)
        self.assertEqual(days_from_common_era(-1), -366)
        self.assertEqual(days_from_common_era(-4), -days4y)
        self.assertEqual(days_from_common_era(-5), -days4y - 366)
        self.assertEqual(days_from_common_era(-100), -days100y - 1)
        self.assertEqual(days_from_common_era(-200), -days100y * 2 - 1)
        self.assertEqual(days_from_common_era(-300), -days100y * 3 - 1)
        self.assertEqual(days_from_common_era(-101), -days100y - 366)
        self.assertEqual(days_from_common_era(-400), -days400y)
        self.assertEqual(days_from_common_era(-401), -days400y - 366)
        self.assertEqual(days_from_common_era(-800), -days400y * 2)

    def test_months2days_function(self):
        self.assertEqual(months2days(-119, 1, 12 * 319), 116512)
        self.assertEqual(months2days(200, 1, -12 * 320) - 1, -116877 - 2)

        # 0000 BCE tests
        self.assertEqual(months2days(0, 1, 12), 366)
        self.assertEqual(months2days(0, 1, -12), -365)
        self.assertEqual(months2days(1, 1, 12), 365)
        self.assertEqual(months2days(1, 1, -12), -366)

        # xs:duration ordering related tests
        self.assertEqual(months2days(year=1696, month=9, months_delta=0), 0)
        self.assertEqual(months2days(1696, 9, 1), 30)
        self.assertEqual(months2days(1696, 9, 2), 61)
        self.assertEqual(months2days(1696, 9, 3), 91)
        self.assertEqual(months2days(1696, 9, 4), 122)
        self.assertEqual(months2days(1696, 9, 5), 153)
        self.assertEqual(months2days(1696, 9, 12), 365)
        self.assertEqual(months2days(1696, 9, -1), -31)
        self.assertEqual(months2days(1696, 9, -2), -62)
        self.assertEqual(months2days(1696, 9, -12), -366)

        self.assertEqual(months2days(1697, 2, 0), 0)
        self.assertEqual(months2days(1697, 2, 1), 28)
        self.assertEqual(months2days(1697, 2, 12), 365)
        self.assertEqual(months2days(1697, 2, -1), -31)
        self.assertEqual(months2days(1697, 2, -2), -62)
        self.assertEqual(months2days(1697, 2, -3), -92)
        self.assertEqual(months2days(1697, 2, -12), -366)
        self.assertEqual(months2days(1697, 2, -14), -428)
        self.assertEqual(months2days(1697, 2, -15), -458)

        self.assertEqual(months2days(1903, 3, 0), 0)
        self.assertEqual(months2days(1903, 3, 1), 31)
        self.assertEqual(months2days(1903, 3, 2), 61)
        self.assertEqual(months2days(1903, 3, 3), 92)
        self.assertEqual(months2days(1903, 3, 4), 122)
        self.assertEqual(months2days(1903, 3, 11), 366 - 29)
        self.assertEqual(months2days(1903, 3, 12), 366)
        self.assertEqual(months2days(1903, 3, -1), -28)
        self.assertEqual(months2days(1903, 3, -2), -59)
        self.assertEqual(months2days(1903, 3, -3), -90)
        self.assertEqual(months2days(1903, 3, -12), -365)

        self.assertEqual(months2days(1903, 7, 0), 0)
        self.assertEqual(months2days(1903, 7, 1), 31)
        self.assertEqual(months2days(1903, 7, 2), 62)
        self.assertEqual(months2days(1903, 7, 3), 92)
        self.assertEqual(months2days(1903, 7, 6), 184)
        self.assertEqual(months2days(1903, 7, 12), 366)
        self.assertEqual(months2days(1903, 7, -1), -30)
        self.assertEqual(months2days(1903, 7, -2), -61)
        self.assertEqual(months2days(1903, 7, -6), -181)
        self.assertEqual(months2days(1903, 7, -12), -365)

        # Extra tests
        self.assertEqual(months2days(1900, 3, 0), 0)
        self.assertEqual(months2days(1900, 3, 1), 31)
        self.assertEqual(months2days(1900, 3, 24), 730)
        self.assertEqual(months2days(1900, 3, -1), -28)
        self.assertEqual(months2days(1900, 3, -24), -730)

        self.assertEqual(months2days(1000, 4, 0), 0)
        self.assertEqual(months2days(1000, 4, 1), 30)
        self.assertEqual(months2days(1000, 4, 24), 730)
        self.assertEqual(months2days(1000, 4, -1), -31)
        self.assertEqual(months2days(1000, 4, -24), -730)

        self.assertEqual(months2days(2001, 10, -12), -365)
        self.assertEqual(months2days(2000, 10, -12), -366)
        self.assertEqual(months2days(2000, 2, -12), -365)
        self.assertEqual(months2days(2000, 3, -12), -366)

    def test_round_number_function(self):
        self.assertTrue(math.isnan(round_number(float('NaN'))))
        self.assertTrue(math.isinf(round_number(float('INF'))))
        self.assertTrue(math.isinf(round_number(float('-INF'))))
        self.assertEqual(round_number(10.1), 10)
        self.assertEqual(round_number(9.5), 10)
        self.assertEqual(round_number(-10.1), -10)
        self.assertEqual(round_number(-9.5), -9)

    def test_collapse_white_spaces_function(self):
        self.assertEqual(collapse_white_spaces('  ab  c  '), 'ab c')
        self.assertEqual(collapse_white_spaces('  ab\t\nc  '), 'ab c')

    def test_get_double_function(self):
        self.assertEqual(get_double(1), 1.0)
        self.assertEqual(get_double(1.0), 1.0)

        self.assertIs(get_double('NaN'), math.nan)
        self.assertIs(get_double(float('nan')), math.nan)
        self.assertTrue(math.isinf(get_double('INF')))

        self.assertRaises(ValueError, get_double, 'nan')
        self.assertRaises(ValueError, get_double, 'Inf')
        self.assertRaises(ValueError, get_double, 'alfa')

    def test_numeric_equal_function(self):
        self.assertTrue(numeric_equal(1.0, 1))
        self.assertFalse(numeric_equal(1.000001, 1.0))
        self.assertTrue(numeric_equal(1.0000001, 1.0))
        self.assertFalse(numeric_equal(float('nan'), float('nan')))
        self.assertRaises(TypeError, numeric_equal, 'xyz', 1)

    def test_numeric_not_equal_function(self):
        self.assertFalse(numeric_not_equal(1.0, 1))
        self.assertTrue(numeric_not_equal(1.000001, 1.0))
        self.assertFalse(numeric_not_equal(1.0000001, 1.0))
        self.assertTrue(numeric_not_equal(float('nan'), float('nan')))

    def test_equal_function(self):
        self.assertTrue(equal(1.0, 1))
        self.assertFalse(equal(1.000001, 1.0))
        self.assertFalse(equal(1.0000001, 1.0))
        self.assertTrue(equal(float('nan'), float('nan')))
        self.assertTrue(equal('xyz', 'xyz'))

    def test_not_equal_function(self):
        self.assertFalse(not_equal(1.0, 1))
        self.assertTrue(not_equal(1.000001, 1.0))
        self.assertTrue(not_equal(1.0000001, 1.0))
        self.assertFalse(not_equal(float('nan'), float('nan')))
        self.assertFalse(not_equal('xyz', 'xyz'))

    def test_match_wildcard_function(self):
        self.assertTrue(match_wildcard('foo', '*'))
        self.assertTrue(match_wildcard('foo', '{*}*'))

        # Use only universal names in Clark’s notation:
        # ref. http://www.jclark.com/xml/xmlns.htm
        self.assertFalse(match_wildcard('foo', '*:*'))

        self.assertTrue(match_wildcard('foo', '{*}foo'))
        self.assertFalse(match_wildcard('foo', '{*}bar'))
        self.assertTrue(match_wildcard('{ns}foo', '{*}foo'))
        self.assertFalse(match_wildcard('{ns}foo', '{*}bar'))
        self.assertTrue(match_wildcard('{tns}foo', '{tns}*'))
        self.assertFalse(match_wildcard('{tns}foo', '{bar}*'))
        self.assertTrue(match_wildcard('{ns}foo', '{ns}*'))
        self.assertFalse(match_wildcard('{ns}foo', '{ns}foo'))  # is not a wildcard
        self.assertFalse(match_wildcard('{ns}foo', '{ns}bar'))

    def test_escape_json_string_function(self):
        self.assertEqual(escape_json_string("\""), '\\"')
        self.assertEqual(escape_json_string("\""), '\\"')
        self.assertEqual(escape_json_string('\\"', escaped=True), '\\"')
        self.assertEqual(escape_json_string('\\u000A', escaped=True), '\\u000A')

    def test_unescape_json_string_function(self):
        self.assertEqual(unescape_json_string('foo'), 'foo')
        self.assertEqual(unescape_json_string('\\n'), '\n')
        self.assertEqual(unescape_json_string('\\u0031'), '1')
        self.assertEqual(unescape_json_string('\\"'), '"')
        self.assertEqual(unescape_json_string('\\\\'), '\\')
        self.assertEqual(unescape_json_string('\\u000a'), '\n')
        self.assertEqual(unescape_json_string('\\U0000000a'), '\n')
        self.assertEqual(unescape_json_string('-\\r-'), '-\r-')
        self.assertEqual(unescape_json_string("-\\t-"), '-\t-')

    def test_iter_sequence_function(self):
        self.assertListEqual(list(iter_sequence(None)), [])
        self.assertListEqual(list(iter_sequence([None, 8])), [8])
        self.assertListEqual(list(iter_sequence([])), [])
        self.assertListEqual(list(iter_sequence([[], 8])), [8])
        self.assertListEqual(list(iter_sequence([[], [], []])), [])
        self.assertListEqual(list(iter_sequence([[], 8, [9]])), [8, 9])

    def test_split_function_test_function(self):
        self.assertListEqual(
            split_function_test('element(*)'), []
        )
        self.assertListEqual(
            split_function_test('function(*)'), ['*']
        )
        self.assertListEqual(
            split_function_test('function(item()) as xs:anyAtomicType'),
            ['item()', 'xs:anyAtomicType']
        )
        self.assertListEqual(
            split_function_test('function(xs:string) as xs:integer*'),
            ['xs:string', 'xs:integer*']
        )
        self.assertListEqual(
            split_function_test('function() as map(xs:string, item())'),
            ['map(xs:string, item())']
        )
        self.assertListEqual(
            split_function_test('function(item()*, item()*, item()*) as item()*'),
            ['item()*', 'item()*', 'item()*', 'item()*']
        )


class XPath30HelperFunctionsTest(unittest.TestCase):

    def test_ordinal_suffix(self):
        self.assertEqual(ordinal_suffix(1), 'st')
        self.assertEqual(ordinal_suffix(2), 'nd')
        self.assertEqual(ordinal_suffix(3), 'rd')
        for n in range(4, 21):
            self.assertEqual(ordinal_suffix(n), 'th')

        self.assertEqual(ordinal_suffix(21), 'st')
        self.assertEqual(ordinal_suffix(22), 'nd')
        self.assertEqual(ordinal_suffix(23), 'rd')
        self.assertEqual(ordinal_suffix(24), 'th')

        self.assertEqual(ordinal_suffix(100), 'th')
        self.assertEqual(ordinal_suffix(100000), 'th')

    def test_to_ordinal_en(self):
        self.assertEqual(to_ordinal_en('one'), 'first')
        self.assertEqual(to_ordinal_en('two'), 'second')
        self.assertEqual(to_ordinal_en('three'), 'third')
        self.assertEqual(to_ordinal_en('four'), 'fourth')
        self.assertEqual(to_ordinal_en('five'), 'fifth')
        self.assertEqual(to_ordinal_en('six'), 'sixth')
        self.assertEqual(to_ordinal_en('seven'), 'seventh')
        self.assertEqual(to_ordinal_en('eight'), 'eighth')
        self.assertEqual(to_ordinal_en('nine'), 'ninth')
        self.assertEqual(to_ordinal_en('ten'), 'tenth')
        self.assertEqual(to_ordinal_en('eleven'), 'eleventh')
        self.assertEqual(to_ordinal_en('twelve'), 'twelfth')
        self.assertEqual(to_ordinal_en('thirteen'), 'thirteenth')
        self.assertEqual(to_ordinal_en('fourteen'), 'fourteenth')
        self.assertEqual(to_ordinal_en('fifteen'), 'fifteenth')
        self.assertEqual(to_ordinal_en('sixteen'), 'sixteenth')
        self.assertEqual(to_ordinal_en('seventeen'), 'seventeenth')
        self.assertEqual(to_ordinal_en('eighteen'), 'eighteenth')
        self.assertEqual(to_ordinal_en('nineteen'), 'nineteenth')
        self.assertEqual(to_ordinal_en('twenty'), 'twentieth')
        self.assertEqual(to_ordinal_en('twenty-one'), 'twenty-first')
        self.assertEqual(to_ordinal_en('twenty-two'), 'twenty-second')
        self.assertEqual(to_ordinal_en('twenty-three'), 'twenty-third')
        self.assertEqual(to_ordinal_en('twenty-four'), 'twenty-fourth')
        self.assertEqual(to_ordinal_en('thirty'), 'thirtieth')
        self.assertEqual(to_ordinal_en('thirty-one'), 'thirty-first')
        self.assertEqual(to_ordinal_en('thirty-two'), 'thirty-second')
        self.assertEqual(to_ordinal_en('thirty-three'), 'thirty-third')
        self.assertEqual(to_ordinal_en('thirty-four'), 'thirty-fourth')
        self.assertEqual(to_ordinal_en('forty'), 'fortieth')
        self.assertEqual(to_ordinal_en('fifty'), 'fiftieth')
        self.assertEqual(to_ordinal_en('sixty'), 'sixtieth')
        self.assertEqual(to_ordinal_en('seventy'), 'seventieth')
        self.assertEqual(to_ordinal_en('eighty'), 'eightieth')
        self.assertEqual(to_ordinal_en('ninety'), 'ninetieth')
        self.assertEqual(to_ordinal_en('one-hundred'), 'one-hundredth')
        self.assertEqual(to_ordinal_en('one hundred'), 'one hundredth')
        self.assertEqual(to_ordinal_en('one hundred and two'), 'one hundred and second')
        self.assertEqual(to_ordinal_en('two-hundred'), 'two-hundredth')

    def test_to_ordinal_it(self):
        self.assertEqual(to_ordinal_it('uno'), 'primo')
        self.assertEqual(to_ordinal_it('due'), 'secondo')
        self.assertEqual(to_ordinal_it('tre'), 'terzo')
        self.assertEqual(to_ordinal_it('quattro'), 'quarto')
        self.assertEqual(to_ordinal_it('sedici'), 'sedicesimo')
        self.assertEqual(to_ordinal_it('diciassette'), 'diciassettesimo')

        self.assertEqual(to_ordinal_it(
            'quindici', '%spellout-ordinal-feminine'), 'quindicesima'
        )

    def test_decimal_to_string(self):
        self.assertEqual(decimal_to_string(Decimal('3.14')), '3.14')
        self.assertEqual(decimal_to_string(Decimal('0.00')), '0.00')
        self.assertEqual(decimal_to_string(Decimal('-0.0')), '-0.0')
        self.assertNotEqual(decimal_to_string(-Decimal('0.0')), '-0.0')
        self.assertEqual(decimal_to_string(-Decimal('90.891')), '-90.891')
        self.assertEqual(decimal_to_string(Decimal('009.00')), '9.00')

    def test_int_to_roman(self):
        self.assertEqual(int_to_roman(1900), 'MCM')
        self.assertEqual(int_to_roman(1), 'I')
        self.assertEqual(int_to_roman(2), 'II')
        self.assertEqual(int_to_roman(3), 'III')
        self.assertEqual(int_to_roman(4), 'IV')
        self.assertEqual(int_to_roman(5), 'V')
        self.assertEqual(int_to_roman(6), 'VI')
        self.assertEqual(int_to_roman(7), 'VII')
        self.assertEqual(int_to_roman(8), 'VIII')
        self.assertEqual(int_to_roman(9), 'IX')
        self.assertEqual(int_to_roman(10), 'X')
        self.assertEqual(int_to_roman(11), 'XI')
        self.assertEqual(int_to_roman(12), 'XII')
        self.assertEqual(int_to_roman(13), 'XIII')
        self.assertEqual(int_to_roman(14), 'XIV')
        self.assertEqual(int_to_roman(15), 'XV')
        self.assertEqual(int_to_roman(48), 'XLVIII')
        self.assertEqual(int_to_roman(49), 'XLIX')
        self.assertEqual(int_to_roman(99), 'XCIX')
        self.assertEqual(int_to_roman(100), 'C')
        self.assertEqual(int_to_roman(499), 'CDXCIX')
        self.assertEqual(int_to_roman(1000), 'M')

    def test_int_to_month(self):
        self.assertEqual(int_to_month(9), 'september')
        self.assertEqual(int_to_month(9, 'it'), 'settembre')
        self.assertEqual(int_to_month(9, 'de'), 'september')
        self.assertRaises(KeyError, int_to_month, 13)

    def test_int_to_weekday(self):
        self.assertEqual(int_to_weekday(1), 'monday')
        self.assertEqual(int_to_weekday(1), 'monday')
        self.assertEqual(int_to_weekday(1, 'it'), 'lunedì')
        self.assertRaises(KeyError, int_to_weekday, 8)

    def test_week_in_month(self):
        dt = datetime.datetime(1900, 1, 1)
        self.assertEqual(week_in_month(dt), 1)
        dt = datetime.datetime(1900, 1, 10)
        self.assertEqual(week_in_month(dt), 2)

    def test_int_to_alphabetic(self):
        self.assertEqual(int_to_alphabetic(1), 'a')
        self.assertEqual(int_to_alphabetic(2), 'b')
        self.assertEqual(int_to_alphabetic(3), 'c')
        self.assertEqual(int_to_alphabetic(40), 'an')

    def test_int_to_words(self):
        self.assertEqual(int_to_words(1), 'one')
        self.assertEqual(int_to_words(2), 'two')
        self.assertEqual(int_to_words(3), 'three')
        self.assertEqual(int_to_words(100), 'one hundred')
        self.assertEqual(int_to_words(8754), 'eight thousand seven hundred and fifty-four')

    def test_format_digits(self):
        self.assertEqual(format_digits('0', '#'), '0')
        self.assertEqual(format_digits('123456789', '000,00,00'), '12345,67,89')
        self.assertEqual(format_digits('150000', '##֊000'), '150֊000')

        self.assertEqual(format_digits('5', '٩', '٠١٢٣٤٥٦٧٨٩'), '٥')
        self.assertEqual(format_digits('6', '٩', '٠١٢٣٤٥٦٧٨٩'), '٦')

        kwargs = dict(grouping_separator=',')
        self.assertEqual(format_digits('987654321', '###,##0,00', **kwargs), '9876,543,21')
        self.assertEqual(format_digits('3', '0000', **kwargs), '0003')
        self.assertEqual(format_digits('10', '##', **kwargs), '10')
        self.assertEqual(format_digits('01', '00', **kwargs), '01')
        self.assertEqual(format_digits('123456789', '###,##,00', **kwargs), '12345,67,89')
        self.assertEqual(format_digits('123456789', '####,###,##,0', **kwargs), '123,456,78,9')
        self.assertEqual(format_digits('123456789', '###,##,00', **kwargs), '12345,67,89')
        self.assertEqual(format_digits('123456789', '####,###,##,0', **kwargs), '123,456,78,9')
        self.assertEqual(format_digits('12', '9,999', **kwargs), '0,012')
        self.assertEqual(format_digits('34', '99', **kwargs), '34')

        args = ['12', '0.000', '0123456789', '#', '.']
        self.assertEqual(format_digits(*args), '0.012')

        args = ['4030201', '!!!,!!!,٠٠٠', '٠١٢٣٤٥٦٧٨٩', '!', ',']
        self.assertEqual(format_digits(*args), '٤,٠٣٠,٢٠١')

        args = ['050600', '٠٠٠٠٠٠', '٠١٢٣٤٥٦٧٨٩', '!', ',']
        self.assertEqual(format_digits(*args), '٠٥٠٦٠٠')

        args = ['4030201', '!!!,!!!,٠٠٠', '٠١٢٣٤٥٦٧٨٩', '!', ',']
        self.assertEqual(format_digits(*args), '٤,٠٣٠,٢٠١')

        args = ['26931', '!!!,!!!', '0123456789', '!', ',']
        self.assertEqual(format_digits(*args), '26,931')

        args = ['400', '!!!', '0123456789', '!', ',']
        self.assertEqual(format_digits(*args), '400')


if __name__ == '__main__':
    unittest.main()
