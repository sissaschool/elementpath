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
import unittest
import sys
import datetime
import operator
import pickle
import random
from decimal import Decimal
from calendar import isleap
from xml.etree import ElementTree
from elementpath.datatypes import MONTH_DAYS, MONTH_DAYS_LEAP, days_from_common_era, \
    months2days, DateTime, DateTime10, Date, Date10, Time, Timezone, Duration, \
    DayTimeDuration, YearMonthDuration, UntypedAtomic, GregorianYear, GregorianYear10, \
    GregorianYearMonth, GregorianYearMonth10, GregorianMonthDay, GregorianMonth, \
    GregorianDay, AbstractDateTime, OrderedDateTime, NumericProxy, ArithmeticProxy, \
    Id, is_idrefs


class StringTypesTest(unittest.TestCase):

    def test_is_id_function(self):
        self.assertTrue(Id.is_valid(ElementTree.XML('<A>xyz</A>').text))
        self.assertFalse(Id.is_valid(ElementTree.XML('<A>xyz abc</A>').text))
        self.assertFalse(Id.is_valid(ElementTree.XML('<A>12345</A>').text))
        self.assertTrue(Id.is_valid('alpha'))
        self.assertFalse(Id.is_valid('alpha beta'))
        self.assertFalse(Id.is_valid('12345'))

    def test_node_is_idref_function(self):
        self.assertTrue(is_idrefs(ElementTree.XML('<A>xyz</A>').text))
        self.assertTrue(is_idrefs(ElementTree.XML('<A>xyz abc</A>').text))
        self.assertFalse(is_idrefs(ElementTree.XML('<A>12345</A>').text))
        self.assertTrue(is_idrefs('alpha'))
        self.assertTrue(is_idrefs('alpha beta'))
        self.assertFalse(is_idrefs('12345'))


class UntypedAtomicTest(unittest.TestCase):

    def test_init(self):
        self.assertEqual(UntypedAtomic(1).value, '1')
        self.assertEqual(UntypedAtomic(-3.9).value, '-3.9')
        self.assertEqual(UntypedAtomic('alpha').value, 'alpha')
        self.assertEqual(UntypedAtomic(b'beta').value, 'beta')
        self.assertEqual(UntypedAtomic(True).value, 'true')
        self.assertEqual(UntypedAtomic(UntypedAtomic(2)).value, '2')
        self.assertEqual(UntypedAtomic(Date.fromstring('2000-02-01')).value, '2000-02-01')

        with self.assertRaises(TypeError) as err:
            UntypedAtomic(None)
        self.assertEqual(str(err.exception), "None is not an atomic value")

    def test_repr(self):
        self.assertEqual(repr(UntypedAtomic(7)), "UntypedAtomic('7')")

    def test_eq(self):
        self.assertTrue(UntypedAtomic(-10) == UntypedAtomic(-10))
        self.assertTrue(UntypedAtomic(5.2) == UntypedAtomic(5.2))
        self.assertTrue(UntypedAtomic('-6.09') == UntypedAtomic('-6.09'))
        self.assertTrue(UntypedAtomic(Decimal('8.91')) == UntypedAtomic(Decimal('8.91')))
        self.assertTrue(UntypedAtomic(False) == UntypedAtomic(False))

        self.assertTrue(UntypedAtomic(-10) == -10)
        self.assertTrue(-10 == UntypedAtomic(-10))
        self.assertTrue('-10' == UntypedAtomic(-10))
        self.assertTrue(UntypedAtomic(False) == bool(False))
        self.assertTrue(bool(False) == UntypedAtomic(False))
        self.assertTrue(Decimal('8.91') == UntypedAtomic(Decimal('8.91')))
        self.assertTrue(UntypedAtomic(Decimal('8.91')) == Decimal('8.91'))

        self.assertTrue(bool(True) == UntypedAtomic(1))
        with self.assertRaises(ValueError) as ctx:
            _ = bool(True) == UntypedAtomic(10)
        self.assertEqual(str(ctx.exception), "'10' cannot be cast to xs:boolean")

        self.assertFalse(-10.9 == UntypedAtomic(-10))
        self.assertFalse(UntypedAtomic(-10) == -11)

        self.assertFalse(UntypedAtomic(-10.5) == UntypedAtomic(-10))
        self.assertFalse(-10.5 == UntypedAtomic(-10))
        self.assertFalse(-17 == UntypedAtomic(-17.3))

    def test_ne(self):
        self.assertTrue(UntypedAtomic(True) != UntypedAtomic(False))
        self.assertTrue(UntypedAtomic(5.12) != UntypedAtomic(5.2))
        self.assertTrue('29' != UntypedAtomic(5.2))
        self.assertFalse('2.0' != UntypedAtomic('2.0'))

    def test_lt(self):
        self.assertTrue(UntypedAtomic(9.0) < UntypedAtomic(15))
        self.assertTrue(False < UntypedAtomic(True))
        self.assertTrue(UntypedAtomic('78') < 100.0)
        self.assertFalse(UntypedAtomic('100.1') < 100.0)

    def test_le(self):
        self.assertTrue(UntypedAtomic(9.0) <= UntypedAtomic(15))
        self.assertTrue(False <= UntypedAtomic(False))
        self.assertTrue(UntypedAtomic('78') <= 100.0)
        self.assertFalse(UntypedAtomic('100.001') <= 100.0)

    def test_gt(self):
        self.assertTrue(UntypedAtomic(25) > UntypedAtomic(15))
        self.assertTrue(25 > UntypedAtomic(15))
        self.assertTrue(UntypedAtomic(25) > 15)
        self.assertTrue(UntypedAtomic(25) > '15')

    def test_ge(self):
        self.assertTrue(UntypedAtomic(25) >= UntypedAtomic(25))
        self.assertFalse(25 >= UntypedAtomic(25.1))

    def test_add(self):
        self.assertEqual(UntypedAtomic(20) + UntypedAtomic(3), UntypedAtomic(23))
        self.assertEqual(UntypedAtomic(-2) + UntypedAtomic(3), UntypedAtomic(1))
        self.assertEqual(UntypedAtomic(17) + UntypedAtomic(5.1), UntypedAtomic(22.1))
        self.assertEqual(UntypedAtomic('1') + UntypedAtomic('2.7'), UntypedAtomic(3.7))

    def test_conversion(self):
        self.assertEqual(str(UntypedAtomic(25.1)), '25.1')
        self.assertEqual(int(UntypedAtomic(25)), 25)
        with self.assertRaises(ValueError):
            int(UntypedAtomic(25.1))
        self.assertEqual(float(UntypedAtomic(25.1)), 25.1)
        self.assertEqual(bool(UntypedAtomic(True)), True)
        if sys.version_info >= (3,):
            self.assertEqual(str(UntypedAtomic(u'Joan Miró')), u'Joan Miró')
        else:
            self.assertEqual(unicode(UntypedAtomic(u'Joan Miró')), u'Joan Miró')
        self.assertEqual(bytes(UntypedAtomic(u'Joan Miró')), b'Joan Mir\xc3\xb3')

    def test_numerical_operators(self):
        self.assertEqual(0.25 * UntypedAtomic(1000), 250)
        self.assertEqual(1200 - UntypedAtomic(1000.0), 200.0)
        self.assertEqual(UntypedAtomic(1000.0) - 250, 750.0)
        self.assertEqual(UntypedAtomic('1000.0') - 250, 750.0)
        self.assertEqual(UntypedAtomic('1000.0') - UntypedAtomic(250), 750.0)
        self.assertEqual(UntypedAtomic(0.75) * UntypedAtomic(100), 75)
        self.assertEqual(UntypedAtomic('0.75') * UntypedAtomic('100'), 75)
        self.assertEqual(UntypedAtomic('9.0') / UntypedAtomic('3'), 3.0)
        self.assertEqual(9.0 / UntypedAtomic('3'), 3.0)
        self.assertEqual(UntypedAtomic('15') * UntypedAtomic('4'), 60)

    def test_abs(self):
        self.assertEqual(abs(UntypedAtomic(-10)), 10)

    def test_mod(self):
        self.assertEqual(UntypedAtomic(1) % 2, 1)
        self.assertEqual(UntypedAtomic('1') % 2, 1.0)

    def test_hashing(self):
        self.assertEqual(hash(UntypedAtomic(12345)), hash('12345'))
        self.assertIsInstance(hash(UntypedAtomic('alpha')), int)


class DateTimeTypesTest(unittest.TestCase):

    def test_abstract_classes(self):
        self.assertRaises(TypeError, AbstractDateTime)
        self.assertRaises(TypeError, OrderedDateTime)

    def test_datetime_init(self):
        with self.assertRaises(ValueError) as err:
            DateTime(year=0, month=1, day=1)
        self.assertIn("0 is an illegal value for year", str(err.exception))

        with self.assertRaises(TypeError) as err:
            DateTime(year=-1999.0, month=1, day=1)
        self.assertIn("invalid type <class 'float'> for year", str(err.exception))

    def test_datetime_fromstring(self):
        dt = DateTime.fromstring('2000-10-07T00:00:00')
        self.assertIsInstance(dt, DateTime)
        self.assertEqual(dt._dt, datetime.datetime(2000, 10, 7))

        dt = DateTime.fromstring('-2000-10-07T00:00:00')
        self.assertIsInstance(dt, DateTime)
        self.assertEqual(dt._dt, datetime.datetime(4, 10, 7))
        self.assertEqual(dt._year, -2001)

        dt = DateTime.fromstring('2020-03-05T23:04:10.047')
        self.assertIsInstance(dt, DateTime)
        self.assertEqual(dt._dt, datetime.datetime(2020, 3, 5, 23, 4, 10, 47000))

        with self.assertRaises(TypeError) as err:
            DateTime.fromstring(b'00-10-07')
        self.assertIn("1st argument has an invalid type <class 'bytes'>", str(err.exception))

        with self.assertRaises(TypeError) as err:
            DateTime.fromstring('2010-10-07', tzinfo='Z')
        self.assertIn("2nd argument has an invalid type <class 'str'>", str(err.exception))

        with self.assertRaises(ValueError) as err:
            DateTime.fromstring('2000-10-07')
        self.assertIn("Invalid datetime string", str(err.exception))

        with self.assertRaises(ValueError) as err:
            DateTime.fromstring('00-10-07T00:00:00')
        self.assertIn("Invalid datetime string", str(err.exception))

        with self.assertRaises(ValueError) as err:
            DateTime.fromstring('2020-03-05 23:04:10.047')
        self.assertIn("Invalid datetime string", str(err.exception))

    def test_date_fromstring(self):
        self.assertIsInstance(Date.fromstring('2000-10-07'), Date)
        self.assertIsInstance(Date.fromstring('-2000-10-07'), Date)
        self.assertIsInstance(Date.fromstring('0000-02-29'), Date)

        with self.assertRaises(ValueError) as ctx:
            Date.fromstring('01000-02-29')

        self.assertIn("when year exceeds 4 digits leading zeroes are not allowed",
                      str(ctx.exception))

        dt = Date.fromstring("-0003-01-01")
        self.assertEqual(dt._year, -4)
        self.assertEqual(dt._dt.year, 6)
        self.assertEqual(dt._dt.month, 1)
        self.assertEqual(dt._dt.day, 1)

    def test_fromdatetime(self):
        dt = datetime.datetime(2000, 1, 20)
        self.assertEqual(str(DateTime.fromdatetime(dt)), '2000-01-20T00:00:00')

        with self.assertRaises(TypeError) as err:
            DateTime.fromdatetime('2000-10-07')
        self.assertEqual("1st argument has an invalid type <class 'str'>", str(err.exception))

        with self.assertRaises(TypeError) as err:
            DateTime.fromdatetime(dt, year='0001')
        self.assertEqual("2nd argument has an invalid type <class 'str'>", str(err.exception))

        self.assertEqual(str(DateTime.fromdatetime(dt, year=1)), '0001-01-20T00:00:00')

    def test_iso_year_property(self):
        self.assertEqual(DateTime(2000, 10, 7).iso_year, '2000')
        self.assertEqual(DateTime(20001, 10, 7).iso_year, '20001')
        self.assertEqual(DateTime(-9999, 10, 7).iso_year, '-9998')
        self.assertEqual(DateTime10(-9999, 10, 7).iso_year, '-9999')
        self.assertEqual(DateTime(-1, 10, 7).iso_year, '0000')
        self.assertEqual(DateTime10(-1, 10, 7).iso_year, '-0001')

    def test_datetime_repr(self):
        dt = DateTime.fromstring('2000-10-07T00:00:00')
        self.assertEqual(repr(dt), "DateTime(2000, 10, 7, 0, 0, 0)")
        self.assertEqual(str(dt), '2000-10-07T00:00:00')

        dt = DateTime.fromstring('-0100-04-13T23:59:59')
        self.assertEqual(repr(dt), "DateTime(-101, 4, 13, 23, 59, 59)")
        self.assertEqual(str(dt), '-0100-04-13T23:59:59')

        dt = DateTime10.fromstring('-0100-04-13T10:30:00-04:00')
        if sys.version_info >= (3, 7):
            self.assertEqual(
                repr(dt), "DateTime10(-100, 4, 13, 10, 30, 0, "
                          "tzinfo=Timezone(datetime.timedelta(days=-1, seconds=72000)))"
            )
        else:
            self.assertEqual(repr(dt), "DateTime10(-100, 4, 13, 10, 30, 0, "
                                       "tzinfo=Timezone(datetime.timedelta(-1, 72000)))")
        self.assertEqual(str(dt), '-0100-04-13T10:30:00-04:00')

        dt = DateTime(2001, 1, 1, microsecond=10)
        self.assertEqual(repr(dt), 'DateTime(2001, 1, 1, 0, 0, 0.000010)')
        self.assertEqual(str(dt), '2001-01-01T00:00:00.00001')

    def test_24_hour_datetime(self):
        dt = DateTime.fromstring('0000-09-19T24:00:00Z')
        self.assertEqual(str(dt), '0000-09-20T00:00:00Z')

    def test_date_repr(self):
        dt = Date.fromstring('2000-10-07')
        self.assertEqual(repr(dt), "Date(2000, 10, 7)")
        self.assertEqual(str(dt), '2000-10-07')

        dt = Date.fromstring('-0100-04-13')
        self.assertEqual(repr(dt), "Date(-101, 4, 13)")
        self.assertEqual(str(dt), '-0100-04-13')

        dt = Date10.fromstring('-0100-04-13')
        self.assertEqual(repr(dt), "Date10(-100, 4, 13)")
        self.assertEqual(str(dt), '-0100-04-13')

        dt = Date.fromstring("-0003-01-01")
        self.assertEqual(repr(dt), "Date(-4, 1, 1)")
        self.assertEqual(str(dt), '-0003-01-01')

        dt = Date10.fromstring("-0003-01-01")
        self.assertEqual(repr(dt), "Date10(-3, 1, 1)")
        self.assertEqual(str(dt), '-0003-01-01')

    def test_gregorian_year_repr(self):
        dt = GregorianYear.fromstring('1991')
        self.assertEqual(repr(dt), "GregorianYear(1991)")
        self.assertEqual(str(dt), '1991')

        dt = GregorianYear.fromstring('0000')
        self.assertEqual(repr(dt), "GregorianYear(-1)")
        self.assertEqual(str(dt), '0000')

        dt = GregorianYear10.fromstring('-0050')
        self.assertEqual(repr(dt), "GregorianYear10(-50)")
        self.assertEqual(str(dt), '-0050')

    def test_gregorian_day_repr(self):
        dt = GregorianDay.fromstring('---31')
        self.assertEqual(repr(dt), "GregorianDay(31)")
        self.assertEqual(str(dt), '---31')

        dt = GregorianDay.fromstring('---05Z')
        self.assertEqual(repr(dt), "GregorianDay(5, tzinfo=Timezone(datetime.timedelta(0)))")
        self.assertEqual(str(dt), '---05Z')

    def test_gregorian_month_repr(self):
        dt = GregorianMonth.fromstring('--09')
        self.assertEqual(repr(dt), "GregorianMonth(9)")
        self.assertEqual(str(dt), '--09')

    def test_gregorian_month_day_repr(self):
        dt = GregorianMonthDay.fromstring('--07-23')
        self.assertEqual(repr(dt), "GregorianMonthDay(7, 23)")
        self.assertEqual(str(dt), '--07-23')

    def test_gregorian_year_month_repr(self):
        dt = GregorianYearMonth.fromstring('-1890-12')
        self.assertEqual(repr(dt), "GregorianYearMonth(-1891, 12)")
        self.assertEqual(str(dt), '-1890-12')

        dt = GregorianYearMonth10.fromstring('-0050-04')
        self.assertEqual(repr(dt), "GregorianYearMonth10(-50, 4)")
        self.assertEqual(str(dt), '-0050-04')

    def test_time_repr(self):
        dt = Time.fromstring('20:40:13')
        self.assertEqual(repr(dt), "Time(20, 40, 13)")
        self.assertEqual(str(dt), '20:40:13')

        dt = Time.fromstring('24:00:00')
        self.assertEqual(repr(dt), "Time(0, 0, 0)")
        self.assertEqual(str(dt), '00:00:00')

        dt = Time.fromstring('15:34:29.000037')
        self.assertEqual(repr(dt), "Time(15, 34, 29.000037)")
        self.assertEqual(str(dt), '15:34:29.000037')

    def test_eq_operator(self):
        tz = Timezone.fromstring('-05:00')
        mkdt = DateTime.fromstring

        self.assertTrue(mkdt("2002-04-02T12:00:00-01:00") == mkdt("2002-04-02T17:00:00+04:00"))
        self.assertFalse(mkdt("2002-04-02T12:00:00") == mkdt("2002-04-02T23:00:00+06:00"))
        self.assertFalse(mkdt("2002-04-02T12:00:00") == mkdt("2002-04-02T17:00:00"))
        self.assertTrue(mkdt("2002-04-02T12:00:00") == mkdt("2002-04-02T12:00:00"))
        self.assertTrue(mkdt("2002-04-02T23:00:00-04:00") == mkdt("2002-04-03T02:00:00-01:00"))
        self.assertTrue(mkdt("1999-12-31T24:00:00") == mkdt("2000-01-01T00:00:00"))
        self.assertTrue(mkdt("2005-04-04T24:00:00") == mkdt("2005-04-05T00:00:00"))

        self.assertTrue(
            mkdt("2002-04-02T12:00:00-01:00", tz) == mkdt("2002-04-02T17:00:00+04:00", tz))
        self.assertTrue(mkdt("2002-04-02T12:00:00", tz) == mkdt("2002-04-02T23:00:00+06:00", tz))
        self.assertFalse(mkdt("2002-04-02T12:00:00", tz) == mkdt("2002-04-02T17:00:00", tz))
        self.assertTrue(mkdt("2002-04-02T12:00:00", tz) == mkdt("2002-04-02T12:00:00", tz))
        self.assertTrue(
            mkdt("2002-04-02T23:00:00-04:00", tz) == mkdt("2002-04-03T02:00:00-01:00", tz))
        self.assertTrue(mkdt("1999-12-31T24:00:00", tz) == mkdt("2000-01-01T00:00:00", tz))

        self.assertTrue(mkdt("2005-04-04T24:00:00", tz) == mkdt("2005-04-05T00:00:00", tz))
        self.assertFalse(mkdt("2005-04-04T24:00:00", tz) != mkdt("2005-04-05T00:00:00", tz))

        self.assertTrue(Date.fromstring("-1000-01-01") == Date.fromstring("-1000-01-01"))
        self.assertTrue(Date.fromstring("-10000-01-01") == Date.fromstring("-10000-01-01"))
        self.assertFalse(Date.fromstring("20000-01-01") != Date.fromstring("20000-01-01"))
        self.assertFalse(Date.fromstring("-10000-01-02") == Date.fromstring("-10000-01-01"))

        self.assertFalse(Date.fromstring("-10000-01-02") == (1, 2, 3))  # Wrong type
        self.assertTrue(Date.fromstring("-10000-01-02") != (1, 2, 3))  # Wrong type

    def test_lt_operator(self):
        mkdt = DateTime.fromstring
        mkdate = Date.fromstring

        self.assertTrue(mkdt("2002-04-02T12:00:00-01:00") < mkdt("2002-04-02T17:00:00-01:00"))
        self.assertFalse(mkdt("2002-04-02T18:00:00-01:00") < mkdt("2002-04-02T17:00:00-01:00"))
        self.assertTrue(mkdt("2002-04-02T18:00:00+02:00") < mkdt("2002-04-02T17:00:00Z"))
        self.assertTrue(mkdt("2002-04-02T18:00:00+02:00") < mkdt("2002-04-03T00:00:00Z"))
        self.assertTrue(mkdt("-2002-01-01T10:00:00") < mkdt("2001-01-01T17:00:00Z"))
        self.assertFalse(mkdt("2002-01-01T10:00:00") < mkdt("-2001-01-01T17:00:00Z"))
        self.assertTrue(mkdt("-2002-01-01T10:00:00") < mkdt("-2001-01-01T17:00:00Z"))
        self.assertTrue(mkdt("-12002-01-01T10:00:00") < mkdt("-12001-01-01T17:00:00Z"))
        self.assertFalse(mkdt("12002-01-01T10:00:00") < mkdt("12001-01-01T17:00:00Z"))
        self.assertTrue(mkdt("-10000-01-01T10:00:00Z") < mkdt("-10000-01-01T17:00:00Z"))
        self.assertRaises(TypeError, operator.lt, mkdt("2002-04-02T18:00:00+02:00"),
                          mkdate("2002-04-03"))

    def test_le_operator(self):
        mkdt = DateTime.fromstring
        mkdate = Date.fromstring

        self.assertTrue(mkdt("2002-04-02T12:00:00-01:00") <= mkdt("2002-04-02T12:00:00-01:00"))
        self.assertFalse(mkdt("2002-04-02T18:00:00-01:00") <= mkdt("2002-04-02T17:00:00-01:00"))
        self.assertTrue(mkdt("2002-04-02T18:00:00+01:00") <= mkdt("2002-04-02T17:00:00Z"))
        self.assertTrue(mkdt("-2002-01-01T10:00:00") <= mkdt("2001-01-01T17:00:00Z"))
        self.assertFalse(mkdt("2002-01-01T10:00:00") <= mkdt("-2001-01-01T17:00:00Z"))
        self.assertTrue(mkdt("-2002-01-01T10:00:00") <= mkdt("-2001-01-01T17:00:00Z"))
        self.assertTrue(mkdt("-10000-01-01T10:00:00Z") <= mkdt("-10000-01-01T10:00:00Z"))
        self.assertTrue(mkdt("-190000-01-01T10:00:00Z") <= mkdt("0100-01-01T10:00:00Z"))
        self.assertRaises(TypeError, operator.le, mkdt("2002-04-02T18:00:00+02:00"),
                          mkdate("2002-04-03"))

    def test_gt_operator(self):
        mkdt = DateTime.fromstring
        mkdate = Date.fromstring

        self.assertFalse(mkdt("2002-04-02T12:00:00-01:00") > mkdt("2002-04-02T17:00:00-01:00"))
        self.assertTrue(mkdt("2002-04-02T18:00:00-01:00") > mkdt("2002-04-02T17:00:00-01:00"))
        self.assertFalse(mkdt("2002-04-02T18:00:00+02:00") > mkdt("2002-04-02T17:00:00Z"))
        self.assertFalse(mkdt("2002-04-02T18:00:00+02:00") > mkdt("2002-04-03T00:00:00Z"))
        self.assertTrue(mkdt("2002-01-01T10:00:00") > mkdt("-2001-01-01T17:00:00Z"))
        self.assertFalse(mkdt("-2002-01-01T10:00:00") > mkdt("-2001-01-01T17:00:00Z"))
        self.assertTrue(mkdt("13567-04-18T10:00:00Z") > datetime.datetime.now())
        self.assertFalse(mkdt("15032-11-12T23:17:59Z") > mkdt("15032-11-12T23:17:59Z"))
        self.assertRaises(TypeError, operator.lt, mkdt("2002-04-02T18:00:00+02:00"),
                          mkdate("2002-04-03"))

    def test_ge_operator(self):
        mkdt = DateTime.fromstring
        mkdate = Date.fromstring

        self.assertTrue(mkdt("2002-04-02T12:00:00-01:00") >= mkdt("2002-04-02T12:00:00-01:00"))
        self.assertTrue(mkdt("2002-04-02T18:00:00-01:00") >= mkdt("2002-04-02T17:00:00-01:00"))
        self.assertTrue(mkdt("2002-04-02T18:00:00+01:00") >= mkdt("2002-04-02T17:00:00Z"))
        self.assertFalse(mkdt("-2002-01-01T10:00:00") >= mkdt("2001-01-01T17:00:00Z"))
        self.assertTrue(mkdt("2002-01-01T10:00:00") >= mkdt("-2001-01-01T17:00:00Z"))
        self.assertFalse(mkdt("-2002-01-01T10:00:00") >= mkdt("-2001-01-01T17:00:00Z"))
        self.assertTrue(mkdt("-3000-06-21T00:00:00Z") >= mkdt("-3000-06-21T00:00:00Z"))
        self.assertFalse(mkdt("-3000-06-21T00:00:00Z") >= mkdt("-3000-06-21T01:00:00Z"))
        self.assertTrue(mkdt("15032-11-12T23:17:59Z") >= mkdt("15032-11-12T23:17:59Z"))
        self.assertRaises(TypeError, operator.le, mkdt("2002-04-02T18:00:00+02:00"),
                          mkdate("2002-04-03"))

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

    def test_fromdelta(self):
        self.assertIsNotNone(Date.fromstring('10000-02-28'))
        self.assertEqual(Date.fromdelta(datetime.timedelta(days=0)),
                         Date.fromstring("0001-01-01"))
        self.assertEqual(Date.fromdelta(datetime.timedelta(days=31)),
                         Date.fromstring("0001-02-01"))
        self.assertEqual(Date.fromdelta(datetime.timedelta(days=59)),
                         Date.fromstring("0001-03-01"))
        self.assertEqual(Date.fromdelta(datetime.timedelta(days=151)),
                         Date.fromstring("0001-06-01"))
        self.assertEqual(Date.fromdelta(datetime.timedelta(days=153)),
                         Date.fromstring("0001-06-03"))
        self.assertEqual(DateTime.fromdelta(datetime.timedelta(days=153, seconds=72000)),
                         DateTime.fromstring("0001-06-03T20:00:00"))

        self.assertEqual(Date.fromdelta(datetime.timedelta(days=365)),
                         Date.fromstring("0002-01-01"))
        self.assertEqual(Date.fromdelta(datetime.timedelta(days=396)),
                         Date.fromstring("0002-02-01"))

        self.assertEqual(Date.fromdelta(datetime.timedelta(days=-366)),
                         Date.fromstring("-0000-01-01"))
        self.assertEqual(Date.fromdelta(datetime.timedelta(days=-1)),
                         Date.fromstring("-0000-12-31"))
        self.assertEqual(Date.fromdelta(datetime.timedelta(days=-335)),
                         Date.fromstring("-0000-02-01"))
        self.assertEqual(Date.fromdelta(datetime.timedelta(days=-1)),
                         Date.fromstring("-0000-12-31"))

        self.assertEqual(Date10.fromdelta(datetime.timedelta(days=-366)),
                         Date10.fromstring("-0001-01-01"))
        self.assertEqual(Date10.fromdelta(datetime.timedelta(days=-326)),
                         Date10.fromstring("-0001-02-10"))
        self.assertEqual(Date10.fromdelta(datetime.timedelta(days=-1)),
                         Date10.fromstring("-0001-12-31Z"))

        # With timezone adjusting
        self.assertEqual(Date10.fromdelta(datetime.timedelta(hours=-22), adjust_timezone=True),
                         Date10.fromstring("-0001-12-31-02:00"))
        self.assertEqual(Date10.fromdelta(datetime.timedelta(hours=-27), adjust_timezone=True),
                         Date10.fromstring("-0001-12-31+03:00"))
        self.assertEqual(
            Date10.fromdelta(datetime.timedelta(hours=-27, minutes=-12), adjust_timezone=True),
            Date10.fromstring("-0001-12-31+03:12")
        )
        self.assertEqual(
            DateTime10.fromdelta(datetime.timedelta(hours=-27, minutes=-12, seconds=-5)),
            DateTime10.fromstring("-0001-12-30T20:47:55")
        )

    def test_todelta(self):
        self.assertEqual(Date.fromstring("0001-01-01").todelta(), datetime.timedelta(days=0))
        self.assertEqual(Date.fromstring("0001-02-01").todelta(), datetime.timedelta(days=31))
        self.assertEqual(Date.fromstring("0001-03-01").todelta(), datetime.timedelta(days=59))
        self.assertEqual(Date.fromstring("0001-06-01").todelta(), datetime.timedelta(days=151))
        self.assertEqual(Date.fromstring("0001-06-03").todelta(), datetime.timedelta(days=153))
        self.assertEqual(DateTime.fromstring("0001-06-03T20:00:00").todelta(),
                         datetime.timedelta(days=153, seconds=72000))

        self.assertEqual(Date.fromstring("0001-01-01-01:00").todelta(),
                         datetime.timedelta(seconds=3600))
        self.assertEqual(Date.fromstring("0001-01-01-07:00").todelta(),
                         datetime.timedelta(seconds=3600 * 7))
        self.assertEqual(Date.fromstring("0001-01-01+10:00").todelta(),
                         datetime.timedelta(seconds=-3600 * 10))
        self.assertEqual(Date.fromstring("0001-01-02+10:00").todelta(),
                         DayTimeDuration.fromstring("PT14H").get_timedelta())
        self.assertEqual(Date.fromstring("-0000-12-31-01:00").todelta(),
                         DayTimeDuration.fromstring("-PT23H").get_timedelta())
        self.assertEqual(Date10.fromstring("-0001-12-31-01:00").todelta(),
                         DayTimeDuration.fromstring("-PT23H").get_timedelta())
        self.assertEqual(Date.fromstring("-0000-12-31+01:00").todelta(),
                         DayTimeDuration.fromstring("-P1DT1H").get_timedelta())

        self.assertEqual(Date.fromstring("0002-01-01").todelta(), datetime.timedelta(days=365))
        self.assertEqual(Date.fromstring("0002-02-01").todelta(), datetime.timedelta(days=396))

        self.assertEqual(Date.fromstring("-0000-01-01").todelta(), datetime.timedelta(days=-366))
        self.assertEqual(Date.fromstring("-0000-02-01").todelta(), datetime.timedelta(days=-335))
        self.assertEqual(Date.fromstring("-0000-12-31").todelta(), datetime.timedelta(days=-1))

        self.assertEqual(Date10.fromstring("-0001-01-01").todelta(), datetime.timedelta(days=-366))
        self.assertEqual(Date10.fromstring("-0001-02-10").todelta(), datetime.timedelta(days=-326))
        self.assertEqual(Date10.fromstring("-0001-12-31Z").todelta(), datetime.timedelta(days=-1))
        self.assertEqual(Date10.fromstring("-0001-12-31-02:00").todelta(),
                         datetime.timedelta(hours=-22))
        self.assertEqual(Date10.fromstring("-0001-12-31+03:00").todelta(),
                         datetime.timedelta(hours=-27))
        self.assertEqual(Date10.fromstring("-0001-12-31+03:00").todelta(),
                         datetime.timedelta(hours=-27))
        self.assertEqual(Date10.fromstring("-0001-12-31+03:12").todelta(),
                         datetime.timedelta(hours=-27, minutes=-12))

    def test_to_and_from_delta(self):
        for month, day in [(1, 1), (1, 2), (2, 1), (2, 28), (3, 10), (6, 30), (12, 31)]:
            fmt1 = '{:04}-%s' % '{:02}-{:02}'.format(month, day)
            fmt2 = '{}-%s' % '{:02}-{:02}'.format(month, day)
            days = sum(MONTH_DAYS[m] for m in range(1, month)) + day - 1
            for year in range(1, 15000):
                if year <= 500 or 9900 <= year <= 10100 or random.randint(1, 20) == 1:
                    date_string = fmt1.format(year) if year < 10000 else fmt2.format(year)
                    dt1 = Date10.fromstring(date_string)
                    delta1 = dt1.todelta()
                    delta2 = datetime.timedelta(days=days)
                    self.assertEqual(delta1, delta2,
                                     msg="Failed for %r: %r != %r" % (dt1, delta1, delta2))
                    dt2 = Date10.fromdelta(delta2)
                    self.assertEqual(dt1, dt2,
                                     msg="Failed for year %d: %r != %r" % (year, dt1, dt2))
                days += 366 if isleap(year if month <= 2 else year + 1) else 365

    def test_to_and_from_delta_bce(self):
        for month, day in [(1, 1), (1, 2), (2, 1), (2, 28), (3, 10), (5, 26), (6, 30), (12, 31)]:
            fmt1 = '-{:04}-%s' % '{:02}-{:02}'.format(month, day)
            fmt2 = '{}-%s' % '{:02}-{:02}'.format(month, day)
            days = -sum(MONTH_DAYS_LEAP[m] for m in range(month, 13)) + day - 1
            for year in range(-1, -15000, -1):
                if year >= -500 or -9900 >= year >= -10100 or random.randint(1, 20) == 1:
                    date_string = fmt1.format(abs(year)) if year > -10000 else fmt2.format(year)
                    dt1 = Date10.fromstring(date_string)
                    delta1 = dt1.todelta()
                    delta2 = datetime.timedelta(days=days)
                    self.assertEqual(delta1, delta2,
                                     msg="Failed for %r: %r != %r" % (dt1, delta1, delta2))
                    dt2 = Date10.fromdelta(delta2)
                    self.assertEqual(dt1, dt2,
                                     msg="Failed for year %d: %r != %r" % (year, dt1, dt2))
                days -= 366 if isleap(year if month <= 2 else year + 1) else 365

    def test_add_operator(self):
        date = Date.fromstring
        date10 = Date10.fromstring
        daytime_duration = DayTimeDuration.fromstring

        self.assertEqual(date("0001-01-01") + daytime_duration('P2D'), date("0001-01-03"))
        self.assertEqual(date("0001-01-01") + daytime_duration('-P2D'), date("0000-12-30"))
        self.assertEqual(date("-0001-01-01") + daytime_duration('P2D'), date("-0001-01-03"))
        self.assertEqual(date("-0001-12-01") + daytime_duration('P30D'), date("-0001-12-31"))
        self.assertEqual(date("-0001-12-01") + daytime_duration('P31D'), date("0000-01-01"))
        self.assertEqual(date10("-0001-12-01") + daytime_duration('P31D'), date10("0001-01-01"))

        self.assertEqual(date("0001-01-01") + YearMonthDuration(months=12), Date(2, 1, 1))
        self.assertEqual(date("-0003-01-01") + YearMonthDuration(months=12), Date(-3, 1, 1))
        self.assertEqual(date("-0004-01-01") + YearMonthDuration(months=13), Date(-4, 2, 1))
        self.assertEqual(date("0001-01-05") + YearMonthDuration(months=25), Date(3, 2, 5))

        with self.assertRaises(TypeError) as err:
            date("0001-01-05") + date("0001-01-01")
        self.assertEqual(str(err.exception), "wrong type <class 'elementpath.datatypes.Date'> "
                                             "for operand Date(1, 1, 1)")

        with self.assertRaises(TypeError) as err:
            date("0001-01-05") + 10
        self.assertEqual(str(err.exception), "wrong type <class 'int'> for operand 10")

        self.assertEqual(Time(13, 30, 00) + daytime_duration('PT3M21S'), Time(13, 33, 21))
        self.assertEqual(Time(21, 00, 00) + datetime.timedelta(seconds=105), Time(21, 1, 45))

        with self.assertRaises(TypeError) as err:
            Time(21, 00, 00) + 105
        self.assertEqual(str(err.exception), "wrong type <class 'int'> for operand 105")

    def test_sub_operator(self):
        date = Date.fromstring
        date10 = Date10.fromstring
        daytime_duration = DayTimeDuration.fromstring

        self.assertEqual(date("2002-04-02") - date("2002-04-01"),
                         DayTimeDuration(seconds=86400))
        self.assertEqual(date("-2002-04-02") - date("-2002-04-01"),
                         DayTimeDuration(seconds=86400))
        self.assertEqual(date("-0002-01-01") - date("-0001-12-31"),
                         DayTimeDuration.fromstring('-P729D'))

        self.assertEqual(date("-0101-01-01") - date("-0100-12-31"),
                         DayTimeDuration.fromstring('-P729D'))
        self.assertEqual(date("15032-11-12") - date("15032-11-11"),
                         DayTimeDuration(seconds=86400))
        self.assertEqual(date("-9999-11-12") - date("-9999-11-11"),
                         DayTimeDuration(seconds=86400))
        self.assertEqual(date("-9999-11-12") - date("-9999-11-12"),
                         DayTimeDuration(seconds=0))
        self.assertEqual(date("-9999-11-11") - date("-9999-11-12"),
                         DayTimeDuration(seconds=-86400))

        self.assertEqual(date10("-2001-04-02-02:00") - date10("-2001-04-01"),
                         DayTimeDuration.fromstring('P1DT2H'))

        self.assertEqual(Time(13, 30, 00) - Time(13, 00, 00), daytime_duration('PT30M'))
        self.assertEqual(Time(13, 30, 00) - Time(13, 59, 59), daytime_duration('-PT29M59S'))
        self.assertEqual(Time(13, 30, 00) - daytime_duration('PT3M21S'), Time(13, 26, 39))
        self.assertEqual(Time(21, 00, 00) - datetime.timedelta(seconds=105), Time(20, 58, 15))

        with self.assertRaises(TypeError) as err:
            Time(21, 00, 00) - 105
        self.assertEqual(str(err.exception), "wrong type <class 'int'> for operand 105")

    def test_hashing(self):
        dt = DateTime.fromstring("2002-04-02T12:00:00-01:00")
        self.assertIsInstance(hash(dt), int)


class DurationTypesTest(unittest.TestCase):

    def test_months2days_function(self):
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

    def test_init(self):
        self.assertIsInstance(Duration(months=1, seconds=37000), Duration)

        with self.assertRaises(ValueError) as err:
            Duration(months=-1, seconds=1)
        self.assertEqual(str(err.exception), "signs differ: (months=-1, seconds=1)")

        self.assertEqual(DayTimeDuration(300).seconds, 300)
        self.assertEqual(YearMonthDuration(10).months, 10)

    def test_init_fromstring(self):
        self.assertIsInstance(Duration.fromstring('P1Y'), Duration)
        self.assertIsInstance(Duration.fromstring('P1M'), Duration)
        self.assertIsInstance(Duration.fromstring('P1D'), Duration)
        self.assertIsInstance(Duration.fromstring('PT0H'), Duration)
        self.assertIsInstance(Duration.fromstring('PT1M'), Duration)
        self.assertIsInstance(Duration.fromstring('PT0.0S'), Duration)

        self.assertRaises(ValueError, Duration.fromstring, 'P')
        self.assertRaises(ValueError, Duration.fromstring, 'PT')
        self.assertRaises(ValueError, Duration.fromstring, '1Y')
        self.assertRaises(ValueError, Duration.fromstring, 'P1W1DT5H3M23.9S')
        self.assertRaises(ValueError, Duration.fromstring, 'P1.5Y')
        self.assertRaises(ValueError, Duration.fromstring, 'PT1.1H')
        self.assertRaises(ValueError, Duration.fromstring, 'P1.0DT5H3M23.9S')

        self.assertIsInstance(DayTimeDuration.fromstring('PT0.0S'), DayTimeDuration)

        with self.assertRaises(ValueError) as err:
            DayTimeDuration.fromstring('P1MT0.0S')
        self.assertEqual(str(err.exception), "months must be 0 for 'DayTimeDuration'")

        self.assertIsInstance(YearMonthDuration.fromstring('P1Y'), YearMonthDuration)

        with self.assertRaises(ValueError) as err:
            YearMonthDuration.fromstring('P1YT10S')
        self.assertEqual(str(err.exception), "seconds must be 0 for 'YearMonthDuration'")

    def test_repr(self):
        self.assertEqual(repr(Duration(months=1, seconds=86400)),
                         'Duration(months=1, seconds=86400)')
        self.assertEqual(repr(Duration.fromstring('P3Y1D')),
                         'Duration(months=36, seconds=86400)')
        self.assertEqual(repr(YearMonthDuration.fromstring('P3Y6M')),
                         'YearMonthDuration(months=42)')
        self.assertEqual(repr(DayTimeDuration.fromstring('P1DT6H')),
                         'DayTimeDuration(seconds=108000)')

    def test_as_string(self):
        self.assertEqual(str(Duration.fromstring('P3Y1D')), 'P3Y1D')
        self.assertEqual(str(Duration.fromstring('PT2M10.4S')), 'PT2M10.4S')
        self.assertEqual(str(Duration.fromstring('PT2400H')), 'P100D')
        self.assertEqual(str(Duration.fromstring('-P15M')), '-P1Y3M')
        self.assertEqual(str(Duration.fromstring('-P809YT3H5M5S')), '-P809YT3H5M5S')
        self.assertEqual(str(Duration.fromstring('-PT1H8S')), '-PT1H8S')
        self.assertEqual(str(Duration.fromstring('PT2H5M')), 'PT2H5M')
        self.assertEqual(str(Duration.fromstring('P0Y')), 'PT0S')

    def test_eq(self):
        self.assertEqual(Duration.fromstring('PT147.5S'), (0, 147.5))
        self.assertEqual(Duration.fromstring('PT147.3S'), (0, Decimal("147.3")))

        self.assertEqual(Duration.fromstring('PT2M10.4S'), (0, Decimal("130.4")))
        self.assertEqual(Duration.fromstring('PT5H3M23.9S'), (0, Decimal("18203.9")))
        self.assertEqual(Duration.fromstring('P1DT5H3M23.9S'), (0, Decimal("104603.9")))
        self.assertEqual(Duration.fromstring('P31DT5H3M23.9S'), (0, Decimal("2696603.9")))
        self.assertEqual(Duration.fromstring('P1Y1DT5H3M23.9S'), (12, Decimal("104603.9")))

        self.assertEqual(Duration.fromstring('-P809YT3H5M5S'), (-9708, -11105))
        self.assertEqual(Duration.fromstring('P15M'), (15, 0))
        self.assertEqual(Duration.fromstring('P1Y'), (12, 0))
        self.assertEqual(Duration.fromstring('P3Y1D'), (36, 3600 * 24))
        self.assertEqual(Duration.fromstring('PT2400H'), (0, 8640000))
        self.assertEqual(Duration.fromstring('PT4500M'), (0, 4500 * 60))
        self.assertEqual(Duration.fromstring('PT4500M70S'), (0, 4500 * 60 + 70))
        self.assertEqual(Duration.fromstring('PT5529615.3S'), (0, Decimal('5529615.3')))

    def test_ne(self):
        self.assertNotEqual(Duration.fromstring('PT147.3S'), None)
        self.assertNotEqual(Duration.fromstring('PT147.3S'), (0, 147.3))
        self.assertNotEqual(Duration.fromstring('P3Y1D'), (36, 3600 * 2))
        self.assertNotEqual(Duration.fromstring('P3Y1D'), (36, 3600 * 24, 0))
        self.assertNotEqual(Duration.fromstring('P3Y1D'), None)
        self.assertNotEqual(Duration.fromstring('P3Y1D'), Duration.fromstring('P3Y2D'))
        self.assertNotEqual(Duration.fromstring('P3Y1D'), YearMonthDuration.fromstring('P3Y'))

    def test_lt(self):
        self.assertTrue(Duration(months=15) < Duration(months=16))
        self.assertFalse(Duration(months=16) < Duration(months=16))
        self.assertTrue(Duration(months=16) < Duration.fromstring('P16M1D'))
        self.assertTrue(Duration(months=16) < Duration.fromstring('P16MT1H'))
        self.assertTrue(Duration(months=16) < Duration.fromstring('P16MT1M'))
        self.assertTrue(Duration(months=16) < Duration.fromstring('P16MT1S'))
        self.assertFalse(Duration(months=16) < Duration.fromstring('P16MT0S'))

        self.assertTrue(Time(20, 15, 0) < Time(21, 0, 0))
        self.assertFalse(Time(21, 15, 0) < Time(21, 0, 0))

        with self.assertRaises(TypeError) as err:
            _ = Duration(months=16) < 16
        self.assertEqual(str(err.exception), "wrong type <class 'int'> for operand 16")

    def test_le(self):
        self.assertTrue(Duration(months=15) <= Duration(months=16))
        self.assertTrue(Duration(months=16) <= Duration(16))
        self.assertTrue(Duration(months=16) <= Duration.fromstring('P16M1D'))
        self.assertTrue(Duration(months=16) <= Duration.fromstring('P16MT1H'))
        self.assertTrue(Duration(months=16) <= Duration.fromstring('P16MT1M'))
        self.assertTrue(Duration(months=16) <= Duration.fromstring('P16MT1S'))
        self.assertTrue(Duration(months=16) <= Duration.fromstring('P16MT0S'))
        self.assertTrue(Time(11, 10, 35) <= Time(11, 10, 35))
        self.assertFalse(Time(11, 10, 35) <= Time(11, 10, 34))

    def test_gt(self):
        self.assertTrue(Duration(months=16) > Duration(15))
        self.assertFalse(Duration(months=16) > Duration(16))
        self.assertFalse(Time(23, 59, 59) > Time(23, 59, 59))
        self.assertTrue(Time(9, 0, 0) > Time(8, 59, 59))

    def test_ge(self):
        self.assertTrue(Duration(16) >= Duration(15))
        self.assertTrue(Duration(16) >= Duration(16))
        self.assertTrue(Duration.fromstring('P1Y1DT1S') >= Duration.fromstring('P1Y1D'))
        self.assertTrue(Time(23, 59, 59) >= Time(23, 59, 59))
        self.assertFalse(Time(23, 59, 58) >= Time(23, 59, 59))

    def test_incomparable_values(self):
        self.assertFalse(Duration(1) < Duration.fromstring('P30D'))
        self.assertFalse(Duration(1) <= Duration.fromstring('P30D'))
        self.assertFalse(Duration(1) > Duration.fromstring('P30D'))
        self.assertFalse(Duration(1) >= Duration.fromstring('P30D'))

    def test_add_operator(self):
        daytime_duration = DayTimeDuration.fromstring
        year_month_duration = YearMonthDuration.fromstring

        self.assertEqual(daytime_duration('P2D') + daytime_duration('P1D'),
                         DayTimeDuration(seconds=86400 * 3))

        self.assertEqual(year_month_duration('P2Y') + year_month_duration('P1Y'),
                         YearMonthDuration(months=36))

        with self.assertRaises(TypeError) as err:
            _ = year_month_duration('P2Y') + daytime_duration('P1D')
        self.assertIn("cannot add <class 'elementpath.datatypes.DayTimeDuration'",
                      str(err.exception))

        with self.assertRaises(TypeError) as err:
            _ = daytime_duration('P1D') + year_month_duration('P2Y')
        self.assertIn("cannot add <class 'elementpath.datatypes.YearMonthDuration'",
                      str(err.exception))

    def test_sub_operator(self):
        daytime_duration = DayTimeDuration.fromstring
        year_month_duration = YearMonthDuration.fromstring

        self.assertEqual(daytime_duration('P2D') - daytime_duration('P1D'),
                         DayTimeDuration(seconds=86400))

        self.assertEqual(year_month_duration('P2Y') - year_month_duration('P1Y'),
                         YearMonthDuration(months=12))

        with self.assertRaises(TypeError) as err:
            _ = year_month_duration('P2Y') - daytime_duration('P1D')
        self.assertIn("cannot subtract <class 'elementpath.datatypes.DayTimeDuration'",
                      str(err.exception))

        with self.assertRaises(TypeError) as err:
            _ = daytime_duration('P1D') - year_month_duration('P2Y')
        self.assertIn("cannot subtract <class 'elementpath.datatypes.YearMonthDuration'",
                      str(err.exception))

    def test_mul_operator(self):
        daytime_duration = DayTimeDuration.fromstring
        year_month_duration = YearMonthDuration.fromstring

        self.assertEqual(daytime_duration('P1D') * 2, DayTimeDuration(seconds=86400 * 2))

        with self.assertRaises(TypeError) as err:
            _ = daytime_duration('P1D') * '2'
        self.assertIn("cannot multiply", str(err.exception))

        self.assertEqual(year_month_duration('P1Y2M') * 2, YearMonthDuration(months=14 * 2))

        with self.assertRaises(TypeError) as err:
            _ = year_month_duration('P1Y2M') * '2'
        self.assertIn("cannot multiply", str(err.exception))

    def test_div_operator(self):
        daytime_duration = DayTimeDuration.fromstring
        year_month_duration = YearMonthDuration.fromstring

        self.assertEqual(daytime_duration('P4D') / 2, DayTimeDuration(seconds=86400 * 2))

        with self.assertRaises(TypeError) as err:
            _ = daytime_duration('P2D') / '2'
        self.assertIn("cannot divide", str(err.exception))

        self.assertEqual(year_month_duration('P1Y2M') / 2, YearMonthDuration(months=14 / 2))

        with self.assertRaises(TypeError) as err:
            _ = year_month_duration('P1Y2M') / '2'
        self.assertIn("cannot divide", str(err.exception))

    def test_hashing(self):
        self.assertIsInstance(hash(Duration(16)), int)


class TimezoneTypeTest(unittest.TestCase):

    def test_init_format(self):
        self.assertEqual(Timezone.fromstring('Z').offset, datetime.timedelta(0))
        self.assertEqual(Timezone.fromstring('00:00').offset, datetime.timedelta(0))
        self.assertEqual(Timezone.fromstring('+00:00').offset, datetime.timedelta(0))
        self.assertEqual(Timezone.fromstring('-00:00').offset, datetime.timedelta(0))
        self.assertEqual(Timezone.fromstring('-0:0').offset, datetime.timedelta(0))
        self.assertEqual(Timezone.fromstring('+05:15').offset,
                         datetime.timedelta(hours=5, minutes=15))
        self.assertEqual(Timezone.fromstring('-11:00').offset, datetime.timedelta(hours=-11))
        self.assertEqual(Timezone.fromstring('+13:59').offset,
                         datetime.timedelta(hours=13, minutes=59))
        self.assertEqual(Timezone.fromstring('-13:59').offset,
                         datetime.timedelta(hours=-13, minutes=-59))
        self.assertEqual(Timezone.fromstring('+14:00').offset, datetime.timedelta(hours=14))
        self.assertEqual(Timezone.fromstring('-14:00').offset, datetime.timedelta(hours=-14))

        self.assertRaises(ValueError, Timezone.fromstring, '-15:00')
        self.assertRaises(ValueError, Timezone.fromstring, '-14:01')
        self.assertRaises(ValueError, Timezone.fromstring, '+14:01')
        self.assertRaises(ValueError, Timezone.fromstring, '+10')
        self.assertRaises(ValueError, Timezone.fromstring, '+10:00:00')

    def test_init_timedelta(self):
        td0 = datetime.timedelta(0)
        td1 = datetime.timedelta(hours=5, minutes=15)
        td2 = datetime.timedelta(hours=-14, minutes=0)
        td3 = datetime.timedelta(hours=-14, minutes=-1)

        self.assertEqual(Timezone(td0).offset, td0)
        self.assertEqual(Timezone(td1).offset, td1)
        self.assertEqual(Timezone(td2).offset, td2)
        self.assertRaises(ValueError, Timezone, td3)
        self.assertRaises(TypeError, Timezone, 0)

    def test_as_string(self):
        self.assertEqual(str(Timezone.fromstring('+05:00')), '+05:00')
        self.assertEqual(str(Timezone.fromstring('-13:15')), '-13:15')

    def test_eq_operator(self):
        self.assertEqual(Timezone.fromstring('+05:00'), Timezone.fromstring('+05:00'))

    def test_ne_operator(self):
        self.assertNotEqual(Timezone.fromstring('+05:00'), Timezone.fromstring('+06:00'))

    def test_hashing(self):
        self.assertIsInstance(hash(Timezone.fromstring('+05:00')), int)

    def test_utcoffset_method(self):
        tz = Timezone.fromstring('+05:00')
        self.assertIs(tz.utcoffset(dt=None), tz.offset)
        with self.assertRaises(TypeError):
            tz.utcoffset(dt='+05:00')

    def test_tzname_method(self):
        tz = Timezone.fromstring('+05:00')
        self.assertEqual(tz.tzname(dt=None), '+05:00')
        with self.assertRaises(TypeError):
            tz.tzname(dt='+05:00')

    def test_dst_method(self):
        tz = Timezone.fromstring('+05:00')
        self.assertEqual(tz.dst(dt=None), None)
        with self.assertRaises(TypeError):
            tz.dst(dt='+05:00')

    def test_fromutc_method(self):
        tz = Timezone.fromstring('+05:00')
        dt = datetime.datetime(2000, 1, 20)
        self.assertEqual(tz.fromutc(dt=dt), datetime.datetime(2000, 1, 20, 5, 0))
        self.assertEqual(tz.fromutc(dt=None), None)
        with self.assertRaises(TypeError):
            tz.fromutc(dt='+05:00')

    def test_serialization(self):
        for protocol in range(pickle.HIGHEST_PROTOCOL):
            tz = Timezone.fromstring('+11:00')
            obj = pickle.dumps(tz)
            self.assertEqual(pickle.loads(obj), tz,
                             msg="Pickle load fails for protocol %d" % protocol)


class TypeProxiesTest(unittest.TestCase):

    def test_instance_check(self):
        self.assertIsInstance(10, NumericProxy)
        self.assertIsInstance(17.8, NumericProxy)
        self.assertIsInstance(Decimal('18.12'), NumericProxy)
        self.assertNotIsInstance(True, NumericProxy)
        self.assertNotIsInstance(Duration.fromstring('P1Y'), NumericProxy)

        self.assertIsInstance(10, ArithmeticProxy)

    def test_subclass_check(self):
        self.assertFalse(issubclass(bool, NumericProxy))
        self.assertFalse(issubclass(str, NumericProxy))
        self.assertTrue(issubclass(int, NumericProxy))
        self.assertTrue(issubclass(float, NumericProxy))
        self.assertTrue(issubclass(Decimal, NumericProxy))
        self.assertFalse(issubclass(DateTime10, NumericProxy))

        self.assertFalse(issubclass(bool, ArithmeticProxy))
        self.assertFalse(issubclass(str, ArithmeticProxy))
        self.assertTrue(issubclass(int, ArithmeticProxy))
        self.assertTrue(issubclass(float, ArithmeticProxy))
        self.assertTrue(issubclass(Decimal, ArithmeticProxy))

    # noinspection PyArgumentList
    def test_instance_build(self):
        self.assertEqual(NumericProxy(), 0.0)
        self.assertEqual(NumericProxy(9), 9.0)
        self.assertEqual(NumericProxy('49'), 49.0)
        self.assertEqual(ArithmeticProxy(), 0.0)
        self.assertEqual(ArithmeticProxy(8.0), 8.0)
        self.assertEqual(ArithmeticProxy('81.0'), 81.0)


if __name__ == '__main__':
    unittest.main()
