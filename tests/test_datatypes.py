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
import math
import operator
import pickle
import platform
import random
from decimal import Decimal
from calendar import isleap
from xml.etree import ElementTree

from elementpath.helpers import MONTH_DAYS, MONTH_DAYS_LEAP
from elementpath.datatypes import DateTime, DateTime10, Date, Date10, Time, \
    Timezone, Duration, DayTimeDuration, YearMonthDuration, UntypedAtomic, \
    GregorianYear, GregorianYear10, GregorianYearMonth, GregorianYearMonth10, \
    GregorianMonthDay, GregorianMonth, GregorianDay, AbstractDateTime, NumericProxy, \
    ArithmeticProxy, Id, Notation, QName, Base64Binary, HexBinary, \
    NormalizedString, XsdToken, Language, Float, Float10, Integer, AnyURI, \
    BooleanProxy, DecimalProxy, DoubleProxy10, DoubleProxy, StringProxy
from elementpath.datatypes.atomic_types import AtomicTypeMeta
from elementpath.datatypes.datetime import OrderedDateTime


class AnyAtomicTypeTest(unittest.TestCase):

    def test_invalid_type_name(self):

        with self.assertRaises(TypeError):
            class InvalidAtomicType(metaclass=AtomicTypeMeta):
                name = b'invalid'

    def test_validation(self):
        class AnotherAtomicType(metaclass=AtomicTypeMeta):
            pass

        self.assertIsNone(AnotherAtomicType.validate(AnotherAtomicType()))
        self.assertIsNone(AnotherAtomicType.validate(''))

        with self.assertRaises(TypeError) as ctx:
            AnotherAtomicType.validate(10)
        self.assertIn("invalid type <class 'int'> for <class", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            AnotherAtomicType.validate('x')
        self.assertIn("invalid value 'x' for <class ", str(ctx.exception))


class StringTypesTest(unittest.TestCase):

    def test_is_id_function(self):
        self.assertTrue(Id.is_valid(ElementTree.XML('<A>xyz</A>').text))
        self.assertFalse(Id.is_valid(ElementTree.XML('<A>xyz abc</A>').text))
        self.assertFalse(Id.is_valid(ElementTree.XML('<A>12345</A>').text))
        self.assertTrue(Id.is_valid('alpha'))
        self.assertFalse(Id.is_valid('alpha beta'))
        self.assertFalse(Id.is_valid('12345'))

    def test_new_instance(self):
        self.assertEqual(NormalizedString('  a b\t c\n'), '  a b  c ')
        self.assertEqual(NormalizedString(10.0), '10.0')
        self.assertEqual(XsdToken(10), '10')
        self.assertEqual(Language(True), 'true')

        with self.assertRaises(ValueError) as ctx:
            Language(10), '10'
        self.assertEqual("invalid value '10' for xs:language", str(ctx.exception))


class FloatTypesTest(unittest.TestCase):

    def test_init(self):
        self.assertEqual(Float10(10), 10.0)

        self.assertTrue(math.isnan(Float10('NaN')))
        self.assertTrue(math.isinf(Float10('INF')))
        self.assertTrue(math.isinf(Float10('-INF')))
        with self.assertRaises(ValueError):
            Float10('+INF')

        self.assertTrue(math.isnan(Float('NaN')))
        self.assertTrue(math.isinf(Float('INF')))
        self.assertTrue(math.isinf(Float('-INF')))
        self.assertTrue(math.isinf(Float('+INF')))

        with self.assertRaises(ValueError):
            Float10('nan')

        with self.assertRaises(ValueError):
            Float10('inf')

    def test_hash(self):
        self.assertEqual(hash(Float10(892.1)), hash(892.1))

    def test_equivalence(self):
        self.assertEqual(Float10('10.1'), Float10('10.1'))
        self.assertEqual(Float10('10.1'), Float('10.1'))
        self.assertNotEqual(Float10('10.1001'), Float10('10.1'))
        self.assertFalse(Float10('10.1001') == Float10('10.1'))
        self.assertNotEqual(Float10('10.1001'), Float('10.1'))
        self.assertFalse(Float10('10.1') != Float10('10.1'))
        self.assertEqual(Float10('10.0'), 10)
        self.assertNotEqual(Float10('10.0'), 11)

    def test_addition(self):
        self.assertEqual(Float10('10.1') + Float10('10.1'), 20.2)
        self.assertEqual(Float('10.1') + Float10('10.1'), 20.2)
        self.assertEqual(10.1 + Float10('10.1'), 20.2)

    def test_subtraction(self):
        self.assertEqual(Float10('10.1') - Float10('1.1'), 9.0)
        self.assertEqual(Float('10.1') - Float10('1.1'), 9.0)
        self.assertEqual(10.1 - Float10('1.1'), 9.0)
        self.assertEqual(10 - Float10('1.1'), 8.9)

    def test_multiplication(self):
        self.assertEqual(Float10('10.1') * 2, 20.2)
        self.assertEqual(Float('10.1') * 2.0, 20.2)
        self.assertEqual(2 * Float10('10.1'), 20.2)
        self.assertEqual(2.0 * Float('10.1'), 20.2)

    def test_division(self):
        self.assertEqual(Float10('20.2') / 2, 10.1)
        self.assertEqual(Float('20.2') / 2.0, 10.1)
        self.assertEqual(20.2 / Float10('2'), 10.1)
        self.assertEqual(20 / Float('2'), 10.0)

    def test_module(self):
        self.assertEqual(Float10('20.2') % 3, 20.2 % 3)
        self.assertEqual(Float('20.2') % 3.0, 20.2 % 3.0)
        self.assertEqual(20.2 % Float10('3'), 20.2 % 3)
        self.assertEqual(20 % Float('3.0'), 20 % 3.0)

    def test_abs(self):
        self.assertEqual(abs(Float10('-20.2')), 20.2)


class IntegerTypesTest(unittest.TestCase):

    def test_validate(self):
        self.assertIsNone(Integer.validate(10))
        self.assertIsNone(Integer.validate(Integer(10)))
        self.assertIsNone(Integer.validate('10'))

        with self.assertRaises(TypeError):
            Integer.validate(True)

        with self.assertRaises(ValueError):
            Integer.validate('10.1')


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

    def test_validate(self):
        self.assertIsNone(UntypedAtomic.validate(UntypedAtomic('10')))
        self.assertRaises(TypeError, UntypedAtomic.validate, '10')
        self.assertRaises(TypeError, UntypedAtomic.validate, 10)


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

        dt = DateTime.fromstring('2000-10-07T00:00:00.100000')
        self.assertIsInstance(dt, DateTime)
        self.assertEqual(dt._dt, datetime.datetime(2000, 10, 7, microsecond=100000))

    def test_issue_36_fromstring_with_more_microseconds_digits(self):
        dt = DateTime.fromstring('2000-10-07T00:00:00.00090001')
        self.assertIsInstance(dt, DateTime)
        self.assertEqual(dt._dt, datetime.datetime(2000, 10, 7, microsecond=900))

        dt = DateTime.fromstring('2000-10-07T00:00:00.0009009999')
        self.assertIsInstance(dt, DateTime)
        self.assertEqual(dt._dt, datetime.datetime(2000, 10, 7, microsecond=900))

        dt = DateTime.fromstring('2000-10-07T00:00:00.1000000')
        self.assertIsInstance(dt, DateTime)
        self.assertEqual(dt._dt, datetime.datetime(2000, 10, 7, microsecond=100000))

        # Regression test of issue #36
        tz = Timezone.fromstring('+01:00')
        dt = DateTime.fromstring('2021-02-21T21:43:03.1121296+01:00')
        self.assertIsInstance(dt, DateTime)
        self.assertEqual(dt._dt, datetime.datetime(2021, 2, 21, 21, 43, 3, 112129, tz))

        # From W3C's XQuery/XPath tests
        dt = DateTime.fromstring('9999-12-31T23:59:59.9999999')
        self.assertIsInstance(dt, DateTime)
        self.assertEqual(dt._dt, datetime.datetime(9999, 12, 31, 23, 59, 59, 999999))

    def test_date_fromstring(self):
        self.assertIsInstance(Date.fromstring('2000-10-07'), Date)
        self.assertIsInstance(Date.fromstring('-2000-10-07'), Date)
        self.assertIsInstance(Date.fromstring('0000-02-29'), Date)

        with self.assertRaises(ValueError) as ctx:
            Date10.fromstring('0000-02-29')
        self.assertIn("year '0000' is an illegal value for XSD 1.0", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            Date.fromstring('01000-02-29')
        self.assertIn("when year exceeds 4 digits leading zeroes are not allowed",
                      str(ctx.exception))

        dt = Date.fromstring("-0003-01-01")
        self.assertEqual(dt._year, -4)
        self.assertEqual(dt._dt.year, 6)
        self.assertEqual(dt._dt.month, 1)
        self.assertEqual(dt._dt.day, 1)
        self.assertTrue(dt.bce)

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
        self.assertEqual(str(err.exception),
                         "wrong type <class 'elementpath.datatypes.datetime.Date'> "
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

    def test_init(self):
        self.assertIsInstance(Duration(months=1, seconds=37000), Duration)

        with self.assertRaises(ValueError) as err:
            Duration(months=-1, seconds=1)
        self.assertEqual(str(err.exception), "signs differ: (months=-1, seconds=1)")

        seconds = Decimal('1.0100001')
        self.assertNotEqual(Duration(seconds=seconds).seconds, seconds)

        with self.assertRaises(OverflowError):
            Duration(months=2 ** 32)

        with self.assertRaises(OverflowError):
            Duration(seconds=Decimal('1' * 40))

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

    def test_string_representation(self):
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

        self.assertEqual(str(YearMonthDuration.fromstring('P3Y6M')), 'P3Y6M')
        self.assertEqual(str(YearMonthDuration.fromstring('-P3Y6M')), '-P3Y6M')
        self.assertEqual(str(YearMonthDuration.fromstring('P7M')), 'P7M')
        self.assertEqual(str(YearMonthDuration.fromstring('P2Y')), 'P2Y')

        self.assertEqual(str(DayTimeDuration.fromstring('P1DT6H')), 'P1DT6H')

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

        self.assertEqual(Duration.fromstring('P3Y1D'), UntypedAtomic('P3Y1D'))
        self.assertFalse(Duration.fromstring('P3Y1D') == UntypedAtomic('P3Y2D'))

    def test_ne(self):
        self.assertNotEqual(Duration.fromstring('PT147.3S'), None)
        self.assertNotEqual(Duration.fromstring('PT147.3S'), (0, 147.3))
        self.assertNotEqual(Duration.fromstring('P3Y1D'), (36, 3600 * 2))
        self.assertNotEqual(Duration.fromstring('P3Y1D'), (36, 3600 * 24, 0))
        self.assertNotEqual(Duration.fromstring('P3Y1D'), None)
        self.assertNotEqual(Duration.fromstring('P3Y1D'), Duration.fromstring('P3Y2D'))
        self.assertNotEqual(Duration.fromstring('P3Y1D'), YearMonthDuration.fromstring('P3Y'))

        self.assertNotEqual(Duration.fromstring('P3Y1D'), UntypedAtomic('P3Y2D'))
        self.assertFalse(Duration.fromstring('P3Y1D') != UntypedAtomic('P3Y1D'))

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
        self.assertEqual(daytime_duration('P2D') + Date10(1999, 8, 12),
                         Date10(1999, 8, 14))

        self.assertEqual(year_month_duration('P2Y') + year_month_duration('P1Y'),
                         YearMonthDuration(months=36))
        self.assertEqual(year_month_duration('P2Y') + Date10(1999, 8, 12),
                         Date10(2001, 8, 12))

        with self.assertRaises(TypeError) as err:
            _ = year_month_duration('P2Y') + daytime_duration('P1D')
        self.assertIn("cannot add <class 'elementpath.datatypes.datetime.DayTimeDuration'",
                      str(err.exception))

        with self.assertRaises(TypeError) as err:
            _ = daytime_duration('P1D') + year_month_duration('P2Y')
        self.assertIn("cannot add <class 'elementpath.datatypes.datetime.YearMonthDuration'",
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
        self.assertIn("cannot subtract <class 'elementpath.datatypes.datetime.DayTimeDuration'",
                      str(err.exception))

        with self.assertRaises(TypeError) as err:
            _ = daytime_duration('P1D') - year_month_duration('P2Y')
        self.assertIn("cannot subtract <class 'elementpath.datatypes.datetime.YearMonthDuration'",
                      str(err.exception))

    def test_mul_operator(self):
        daytime_duration = DayTimeDuration.fromstring
        year_month_duration = YearMonthDuration.fromstring

        self.assertEqual(daytime_duration('P1D') * 2, DayTimeDuration(seconds=86400 * 2))
        self.assertEqual(daytime_duration('P2D') * 3.0, DayTimeDuration(seconds=86400 * 6))

        with self.assertRaises(TypeError) as err:
            _ = daytime_duration('P1D') * '2'
        self.assertIn("cannot multiply", str(err.exception))

        with self.assertRaises(ValueError) as err:
            _ = daytime_duration('P1D') * float('nan')
        self.assertIn("cannot multiply", str(err.exception))
        self.assertIn("by NaN", str(err.exception))

        self.assertEqual(year_month_duration('P1Y2M') * 2, YearMonthDuration(months=14 * 2))

        with self.assertRaises(TypeError) as err:
            _ = year_month_duration('P1Y2M') * '2'
        self.assertIn("cannot multiply", str(err.exception))

    def test_div_operator(self):
        daytime_duration = DayTimeDuration.fromstring
        year_month_duration = YearMonthDuration.fromstring

        self.assertEqual(daytime_duration('P4D') / 2, DayTimeDuration(seconds=86400 * 2))
        self.assertEqual(daytime_duration('P1D') / 2.0, DayTimeDuration(86400 // 2))

        with self.assertRaises(TypeError) as err:
            _ = daytime_duration('P2D') / '2'
        self.assertIn("cannot divide", str(err.exception))

        self.assertEqual(year_month_duration('P1Y2M') / 2, YearMonthDuration(months=14 // 2))

        with self.assertRaises(TypeError) as err:
            _ = year_month_duration('P1Y2M') / '2'
        self.assertIn("cannot divide", str(err.exception))

        with self.assertRaises(ValueError) as err:
            daytime_duration('P1D') / float('nan')
        self.assertIn("cannot divide", str(err.exception))
        self.assertIn("by NaN", str(err.exception))

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

        self.assertRaises(TypeError, Timezone.fromstring, -15)
        self.assertRaises(ValueError, Timezone.fromstring, '-15:00')
        self.assertRaises(ValueError, Timezone.fromstring, '-14:01')
        self.assertRaises(ValueError, Timezone.fromstring, '+14:01')
        self.assertRaises(ValueError, Timezone.fromstring, '+10')
        self.assertRaises(ValueError, Timezone.fromstring, '+10:00:00')

        with self.assertRaises(ValueError) as ctx:
            Timezone.fromduration(Duration(seconds=3601))
        self.assertIn("has not an integral number of minutes", str(ctx.exception))

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


class BinaryTypesTest(unittest.TestCase):

    def test_initialization(self):
        self.assertEqual(Base64Binary(b'YWxwaGE='), b'YWxwaGE=')
        self.assertEqual(HexBinary(b'F859'), b'F859')

        self.assertEqual(Base64Binary(Base64Binary(b'YWxwaGE=')), b'YWxwaGE=')
        self.assertEqual(HexBinary(HexBinary(b'F859')), b'F859')

        try:
            self.assertEqual(Base64Binary(HexBinary(b'F859')).decode(),
                             HexBinary(b'F859').decode())
            self.assertEqual(HexBinary(Base64Binary(b'YWxwaGE=')).decode(), b'alpha')
        except TypeError:
            # Issue #3001 of pypy3.6 with codecs.decode(), fixed with PyPy 7.2.0.
            if platform.python_implementation() != 'PyPy':
                raise

    def test_string_representation(self):
        self.assertEqual(repr(Base64Binary(b'YWxwaGE=')), "Base64Binary(b'YWxwaGE=')")
        self.assertEqual(repr(HexBinary(b'F859')), "HexBinary(b'F859')")

    def test_bytes_conversion(self):
        self.assertEqual(bytes(Base64Binary(b'YWxwaGE=')), b'YWxwaGE=')
        self.assertEqual(bytes(HexBinary(b'F859')), b'F859')

    def test_unicode_string_conversion(self):
        self.assertEqual(str(Base64Binary(b'YWxwaGE=')), 'YWxwaGE=')
        self.assertEqual(str(HexBinary(b'F859')), 'F859')

    def test_hash_value(self):
        self.assertEqual(hash(Base64Binary(b'YWxwaGE=')), hash(b'YWxwaGE='))
        self.assertEqual(hash(HexBinary(b'F859')), hash(b'F859'))

    def test_length(self):
        self.assertEqual(len(Base64Binary(b'ZQ==')), 1)
        self.assertEqual(len(Base64Binary(b'YWxwaGE=')), 5)
        self.assertEqual(len(Base64Binary(b'bGNlbmdnamh4eXBy')), 12)
        self.assertEqual(len(HexBinary(b'F859')), 2)

    def test_equality(self):
        self.assertEqual(HexBinary(b'8A7F'), HexBinary(b'8A7F'))
        self.assertEqual(HexBinary(b'8a7f'), HexBinary(b'8a7f'))
        self.assertEqual(HexBinary(b'8a7f'), HexBinary(b'8A7F'))
        self.assertEqual(HexBinary(b'8A7F'), HexBinary(b'8a7f'))

        self.assertEqual(b'8a7f', HexBinary(b'8A7F'))
        self.assertEqual(HexBinary(b'8A7F'), b'8a7f')
        self.assertEqual('8a7f', HexBinary(b'8A7F'))
        self.assertEqual(HexBinary(b'8A7F'), '8a7f')

        self.assertEqual(Base64Binary(b'YWxwaGE='), Base64Binary(b'YWxwaGE='))
        self.assertNotEqual(Base64Binary(b'YWxwaGE='), Base64Binary(b'ywxwaGE='))
        self.assertEqual(Base64Binary(b'YWxwaGE='), UntypedAtomic('YWxwaGE='))
        self.assertEqual(Base64Binary(b'YWxwaGE='), 'YWxwaGE=')
        self.assertEqual(Base64Binary('YWxwaGE='), b'YWxwaGE=')

        self.assertNotEqual(HexBinary(b'F859'), Base64Binary(b'YWxwaGE='))
        self.assertEqual(HexBinary(b'F859'), UntypedAtomic(HexBinary(b'F859')))

    def test_validate(self):
        self.assertIsNone(Base64Binary.validate(Base64Binary(b'YWxwaGE=')))
        self.assertIsNone(Base64Binary.validate(b'YWxwaGE='))

        with self.assertRaises(TypeError):
            Base64Binary.validate(67)

        self.assertIsNone(Base64Binary.validate(b' '))

        with self.assertRaises(ValueError):
            Base64Binary.validate('FF')

        self.assertIsNone(HexBinary.validate(HexBinary(b'F859')))
        self.assertIsNone(HexBinary.validate(b'F859'))

        with self.assertRaises(TypeError):
            HexBinary.validate(67)

        self.assertIsNone(HexBinary.validate(b' '))

        with self.assertRaises(ValueError):
            HexBinary.validate('XY')

    def test_encoder(self):
        self.assertEqual(Base64Binary.encoder(b'alpha'), b'YWxwaGE=')

    def test_decoder(self):
        try:
            self.assertEqual(Base64Binary(b'YWxwaGE=').decode(), b'alpha')
        except TypeError:
            # Issue #3001 of pypy3.6 with codecs.decode(), fixed with PyPy 7.2.0.
            if platform.python_implementation() != 'PyPy':
                raise


class QNameTypesTest(unittest.TestCase):

    def test_initialization(self):
        qname = QName(None, 'foo')
        self.assertEqual(qname.namespace, '')
        self.assertEqual(qname.local_name, 'foo')
        self.assertIsNone(qname.prefix)
        self.assertEqual(qname.expanded_name, 'foo')

        with self.assertRaises(ValueError) as ctx:
            QName(None, 'tns:foo')
        self.assertIn('non-empty prefix with no namespace', str(ctx.exception))

        with self.assertRaises(TypeError) as ctx:
            QName(10, 'foo')
        self.assertIn("invalid type <class 'int'>", str(ctx.exception))

        qname = QName('http://xpath.test/ns', 'foo')
        self.assertEqual(qname.namespace, 'http://xpath.test/ns')
        self.assertEqual(qname.local_name, 'foo')
        self.assertIsNone(qname.prefix)
        self.assertEqual(qname.expanded_name, '{http://xpath.test/ns}foo')

        qname = QName('http://xpath.test/ns', 'tst:foo')
        self.assertEqual(qname.namespace, 'http://xpath.test/ns')
        self.assertEqual(qname.local_name, 'foo')
        self.assertEqual(qname.prefix, 'tst')
        self.assertEqual(qname.expanded_name, '{http://xpath.test/ns}foo')

    def test_string_representation(self):
        qname = QName('http://xpath.test/ns', 'tst:foo')
        self.assertEqual(repr(qname), "QName(uri='http://xpath.test/ns', qname='tst:foo')")

        qname = QName(uri=None, qname='foo')
        self.assertEqual(repr(qname), "QName(uri='', qname='foo')")

        qname = QName(uri='', qname='foo')
        self.assertEqual(repr(qname), "QName(uri='', qname='foo')")

    def test_hash_value(self):
        qname = QName('http://xpath.test/ns', 'tst:foo')
        self.assertEqual(hash(qname), hash(('http://xpath.test/ns', 'foo')))

    def test_equivalence(self):
        qname1 = QName('http://xpath.test/ns1', 'tst1:foo')
        qname2 = QName('http://xpath.test/ns1', 'tst2:foo')
        qname3 = QName('http://xpath.test/ns2', 'tst2:foo')
        self.assertEqual(qname1, qname2)
        self.assertNotEqual(qname1, qname3)
        self.assertNotEqual(qname2, qname3)

        with self.assertRaises(TypeError) as ctx:
            _ = qname1 == 'tst1:foo'
        self.assertIn('cannot compare', str(ctx.exception))

    def test_notation(self):
        with self.assertRaises(TypeError) as ec:
            Notation(None, 'foo')
        self.assertEqual(str(ec.exception), "can't instantiate xs:NOTATION objects")

        class EffectiveNotation(Notation):
            def __init__(self, uri, qname):
                super().__init__(uri, qname)

        notation = EffectiveNotation(None, 'foo')
        self.assertEqual(notation, QName(None, 'foo'))

        notation = EffectiveNotation('http://xpath.test/ns1', 'tst1:foo')
        self.assertEqual(notation, QName('http://xpath.test/ns1', 'tst2:foo'))

        self.assertEqual(hash(notation), hash(('http://xpath.test/ns1', 'foo')))


class AnyUriTest(unittest.TestCase):

    def test_init(self):
        uri = AnyURI('http://xpath.test')
        self.assertEqual(uri, 'http://xpath.test')
        self.assertEqual(AnyURI(b'http://xpath.test'), 'http://xpath.test')
        self.assertEqual(AnyURI(uri), uri)
        self.assertEqual(AnyURI(UntypedAtomic('http://xpath.test')), uri)

        with self.assertRaises(TypeError):
            AnyURI(1)

    def test_string_representation(self):
        self.assertEqual(repr(AnyURI('http://xpath.test')), "AnyURI('http://xpath.test')")

    def test_bool_value(self):
        self.assertTrue(bool(AnyURI('http://xpath.test')))
        self.assertFalse(bool(AnyURI('')))

    def test_hash_value(self):
        self.assertEqual(hash(AnyURI('http://xpath.test')), hash('http://xpath.test'))

    def test_in_operator(self):
        uri = AnyURI('http://xpath.test')
        self.assertIn('xpath', uri)
        self.assertNotIn('example', uri)

    def test_comparison_operators(self):
        uri = AnyURI('http://xpath.test')
        self.assertTrue(uri != 'http://example.test')
        self.assertTrue(uri != AnyURI('http://example.test'))

        with self.assertRaises(TypeError):
            _ = uri == 10

        with self.assertRaises(TypeError):
            _ = uri != 10

        self.assertLess(AnyURI('1'), AnyURI('2'))
        self.assertLess(AnyURI('1'), '2')

        self.assertLessEqual(AnyURI('1'), AnyURI('1'))
        self.assertLessEqual(AnyURI('1'), '1')

        self.assertGreater(AnyURI('2'), AnyURI('1'))
        self.assertGreater(AnyURI('2'), '1')

        self.assertGreaterEqual(AnyURI('1'), AnyURI('1'))
        self.assertGreaterEqual(AnyURI('1'), '1')

    def test_validate(self):
        uri = AnyURI('http://xpath.test')
        self.assertIsNone(AnyURI.validate(uri))
        self.assertIsNone(AnyURI.validate(b'http://xpath.test'))
        self.assertIsNone(AnyURI.validate('http://xpath.test'))

        with self.assertRaises(TypeError):
            AnyURI.validate(1)

        with self.assertRaises(ValueError):
            AnyURI.validate('http:://xpath.test')


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

    def test_boolean_proxy(self):
        self.assertTrue(BooleanProxy(1))
        self.assertFalse(BooleanProxy(float('nan')))

        self.assertIsNone(BooleanProxy.validate(True))
        self.assertIsNone(BooleanProxy.validate('true'))
        self.assertIsNone(BooleanProxy.validate('1'))
        self.assertIsNone(BooleanProxy.validate('false'))
        self.assertIsNone(BooleanProxy.validate('0'))

        with self.assertRaises(TypeError):
            BooleanProxy.validate(1)

        with self.assertRaises(ValueError):
            BooleanProxy.validate('2')

    def test_decimal_proxy(self):
        self.assertIsInstance(DecimalProxy(20.0), Decimal)

        self.assertEqual(Decimal('10'), DecimalProxy('10'))
        self.assertEqual(Decimal('10'), DecimalProxy(Decimal('10')))
        self.assertEqual(Decimal('10.0'), DecimalProxy(10.0))
        self.assertEqual(Decimal(1), DecimalProxy(True))

        with self.assertRaises(TypeError):
            DecimalProxy(None)
        with self.assertRaises(ArithmeticError):
            DecimalProxy([])
        with self.assertRaises(ValueError):
            DecimalProxy('false')
        with self.assertRaises(ValueError):
            DecimalProxy('INF')
        with self.assertRaises(ValueError):
            DecimalProxy('NaN')
        with self.assertRaises(ValueError):
            DecimalProxy(float('nan'))
        with self.assertRaises(ValueError):
            DecimalProxy(float('inf'))

        self.assertIsNone(DecimalProxy.validate(Decimal(-2.0)))
        self.assertIsNone(DecimalProxy.validate(17))
        self.assertIsNone(DecimalProxy.validate('17'))
        with self.assertRaises(ValueError):
            DecimalProxy.validate(Decimal('nan'))
        with self.assertRaises(ValueError):
            DecimalProxy.validate('alpha')
        with self.assertRaises(TypeError):
            DecimalProxy.validate(True)

    def test_double_proxy(self):
        self.assertIsInstance(DoubleProxy10(20), float)

        self.assertEqual(DoubleProxy10('10'), 10.0)
        self.assertTrue(math.isnan(DoubleProxy10('NaN')))
        self.assertTrue(math.isinf(DoubleProxy10('INF')))
        self.assertTrue(math.isinf(DoubleProxy10('-INF')))

        # noinspection PyTypeChecker
        self.assertTrue(math.isinf(DoubleProxy('+INF')))

        with self.assertRaises(ValueError):
            DoubleProxy10('+INF')
        with self.assertRaises(ValueError):
            DoubleProxy('nan')
        with self.assertRaises(ValueError):
            DoubleProxy('inf')

        self.assertIsNone(DoubleProxy10.validate(1.9))
        self.assertIsNone(DoubleProxy10.validate('1.9'))

        with self.assertRaises(TypeError):
            DoubleProxy10.validate(Float10('1.9'))
        with self.assertRaises(ValueError):
            DoubleProxy10.validate('six')

    def test_string_proxy(self):
        self.assertIsInstance(StringProxy(20), str)
        self.assertIsNone(StringProxy.validate('alpha'))
        with self.assertRaises(TypeError):
            StringProxy.validate(b'alpha')


if __name__ == '__main__':
    unittest.main()
