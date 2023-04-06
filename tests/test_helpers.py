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
import unittest
import math
from xml.etree import ElementTree
from elementpath.helpers import days_from_common_era, months2days, \
    round_number, is_idrefs, collapse_white_spaces, escape_json_string, \
    get_double, numeric_equal, numeric_not_equal, equal, not_equal, \
    match_wildcard, unescape_json_string, iter_sequence, split_function_test


class HelperFunctionsTest(unittest.TestCase):

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
        self.assertTrue(match_wildcard('foo', '*:*'))
        self.assertTrue(match_wildcard('foo', '*:foo'))
        self.assertFalse(match_wildcard('foo', '*:bar'))
        self.assertTrue(match_wildcard('{ns}foo', '*:foo'))
        self.assertFalse(match_wildcard('{ns}foo', '*:bar'))
        self.assertTrue(match_wildcard('tns:foo', 'tns:*'))
        self.assertFalse(match_wildcard('tns:foo', 'bar:*'))
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


if __name__ == '__main__':
    unittest.main()
