# -*- coding: utf-8 -*-
#
# Copyright (c), 2018, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""
Helper functions for XPath. Includes test functions for nodes, a class for UntypedAtomic data and
implementation for XPath functions that are reused in many contexts.
"""
from __future__ import division, unicode_literals

from abc import ABCMeta
import operator
import re
import decimal
from datetime import datetime, timedelta, tzinfo
from calendar import leapdays, monthrange

from .compat import PY3, string_base_type, add_metaclass
from .exceptions import ElementPathTypeError, ElementPathValueError


FRACTION_DIGITS_RE_PATTERN = re.compile(r'\.(\d+)$')
ISO_TIMEZONE_RE_PATTERN = re.compile(r'(Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))$')
XSD_DURATION_PATTERN = re.compile(
    r'^(-)?P(?=(?:\d|T))(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?(?:T(?=\d)(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$'
)


def months2days(year, month, month_delta):
    """
    Converts a delta of months to a delta of days, counting from the 1st day of the month,
    relative to the year and the month passed as arguments.
    """
    total_months = month - 1 + month_delta
    target_year = year + total_months // 12
    target_month = total_months % 12 + 1

    if month <= 2:
        y_days = 365 * (target_year - year) + leapdays(year, target_year)
    else:
        y_days = 365 * (target_year - year) + leapdays(year + 1, target_year + 1)

    if target_month >= month:
        m_days = sum(monthrange(target_year, m)[1] for m in range(month, target_month))
        return y_days + m_days if y_days >= 0 else y_days + m_days
    else:
        m_days = sum(monthrange(target_year, m)[1] for m in range(target_month, month))
        return y_days - m_days if y_days >= 0 else y_days - m_days


def check_iso8601_format(value, fmt):
    """
    Performs additional checks on the ISO 8601 format representation.

    :param value: ISO 8601 string value.
    :param fmt: the value string format.
    :raise: a ValueError if the argument is not conforming to ISO 8601.
    """
    if 'T' not in fmt:
        if len(value) < len(fmt) + fmt.count('%Y') * 2 + fmt.count('%f') * 4:
            if '%m' in value or '%d' in value:
                raise ElementPathValueError("%r: months and days must be two digits each" % value)
            else:
                raise ElementPathValueError("%r: hours, minutes and seconds be two digits each" % value)
    elif 't' in value:
        raise ElementPathValueError("%r: 't' separator must be in uppercase" % value)
    else:
        ti = value.index('T')
        if ti < 10:
            raise ElementPathValueError("%r: months and days must be two digits each" % value)
        elif len(value) < ti+9 or value[ti+3] != ':' or value[ti+6] != ':' or not value[ti+7: ti+9].isdigit():
            raise ElementPathValueError("%r: hours, minutes and seconds must be two digits each" % value)


@add_metaclass(ABCMeta)
class AbstractDateTime(object):
    """
    A class for representing XSD date/time objects. The reference xs:dateTime used is
    the datetime.datetime default 1900-01-01T00:00:00.

    :param dt: the datetime.datetime instance that stores the XSD Date/Time value.
    :param bce: if `True` the date value refers to a BCE (Before Common Era) date.
    """
    formats = ()

    def __init__(self, dt, fmt, bce=False):
        if not isinstance(dt, datetime):
            raise ElementPathTypeError("1st argument must be a datetime.datetime instance.")
        elif fmt not in self.formats:
            raise ElementPathValueError("%r is not a date/time format of %r." % (fmt, type(self)))
        elif '%H' not in fmt and (dt.hour or dt.minute or dt.second):
            raise ElementPathValueError("hour, minute, second must be zero for %r instance." % type(self))
        elif '%Y' not in fmt and (dt.year != 1900 or bce):
            raise ElementPathValueError("year must be absent for %r instance." % type(self))
        elif '%m' not in fmt and dt.month != 1:
            raise ElementPathValueError("month must be absent for %r instance." % type(self))
        elif '%d' not in fmt and dt.day != 1:
            raise ElementPathValueError("day must be absent for %r instance." % type(self))

        self._dt = dt
        self._fmt = str(fmt)
        self._bce = bce

    @property
    def dt(self):
        return self._dt

    @property
    def fmt(self):
        return self._fmt

    @property
    def bce(self):
        return self._bce

    def __repr__(self):
        return '%s(dt=%s, fmt=%r, bce=%r)' % (self.__class__.__name__, repr(self._dt)[9:], self._fmt, self._bce)

    def __str__(self):
        if not self._bce:
            return self._dt.strftime(self._fmt) if PY3 else str(self._dt)
        elif PY3:
            return self._dt.strftime(self._fmt.replace('%Y', '{:04}'.format(self._dt.year - 1)))
        else:
            return '-%s' % str(self._dt).replace('{:04}'.format(self._dt.year), '{:04}'.format(self._dt.year - 1))

    def __unicode__(self):
        return str(self)

    @classmethod
    def fromstring(cls, value, tz=None):
        """
        Creates an XSD date/time instance from a string formatted value, trying the
        class formats list.

        :param value: a string containing a formatted date/time specification.
        :param tz: optional timezone information, must be a `Timezone` instance.
        :return: an AbstractDateTime concrete subclass instance.
        """
        if not isinstance(value, string_base_type):
            raise ElementPathTypeError('1st argument has an invalid type %r' % type(value))
        elif tz and not isinstance(tz, Timezone):
            raise ElementPathTypeError('2nd argument has an invalid type %r' % type(value))

        tz_match = ISO_TIMEZONE_RE_PATTERN.search(value)
        dt_part = value if tz_match is None else value[:tz_match.span()[0]]
        year_zero = '0000' in dt_part

        for fmt in cls.formats:
            try:
                if '%f' in fmt:
                    datetime_part, fraction_digits, _ = FRACTION_DIGITS_RE_PATTERN.split(dt_part)
                    dt = datetime.strptime(
                        '%s.%s' % (datetime_part, fraction_digits[:6]),
                        fmt if not year_zero else fmt.replace('%Y', '0000')
                    )
                else:
                    dt = datetime.strptime(dt_part, fmt if not year_zero else fmt.replace('%Y', '0000'))
            except ValueError:
                pass
            else:
                check_iso8601_format(value, fmt)

                if '24:00:00' in fmt:
                    dt = dt + timedelta(days=1)
                    fmt = fmt.replace('24:00:00', '%H:%M:%S')

                if tz_match is not None:
                    dt = dt.replace(tzinfo=Timezone(tz_match.group()))
                elif tz is not None:
                    dt = dt.replace(tzinfo=tz)
                elif not PY3:
                    dt = dt.replace(tzinfo=Timezone('+00:00'))

                if year_zero:
                    return cls(dt=dt.replace(year=1), fmt=fmt, bce=True)
                elif fmt.startswith('-%Y'):
                    return cls(dt=dt.replace(year=dt.year + 1), fmt=fmt, bce=True)
                else:
                    return cls(dt, fmt)
        else:
            if len(cls.formats) == 1:
                raise ElementPathValueError('Invalid value %r for datetime format %r' % (value, cls.formats[0]))
            else:
                raise ElementPathValueError('Invalid value %r for datetime formats %r' % (value, cls.formats))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._dt == other._dt and self._bce == other._bce
        else:
            return self._dt == other and not self._bce



class DateTime(AbstractDateTime):

    formats = ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT24:00:00',
               '-%Y-%m-%dT%H:%M:%S', '-%Y-%m-%dT%H:%M:%S.%f', '-%Y-%m-%dT24:00:00')


class Date(AbstractDateTime):
    formats = ('%Y-%m-%d', '-%Y-%m-%d')


class GregorianDay(AbstractDateTime):
    formats = ('---%d',)


class GregorianMonth(AbstractDateTime):
    formats = ('--%m',)


class GregorianMonthDay(AbstractDateTime):
    formats = ('--%m-%d',)


class GregorianYear(AbstractDateTime):
    formats = ('%Y', '-%Y')


class GregorianYearMonth(AbstractDateTime):
    formats = ('%Y-%m', '-%Y-%m')


class Time(AbstractDateTime):
    formats = ('%H:%M:%S', '%H:%M:%S.%f', '24:00:00')


class Duration(object):
    """
    Base class for the XSD duration types.

    :param months: an integer value that represents years and months.
    :param seconds: a Decimal instance that represents days, hours, minutes, seconds and fractions of seconds.
    """
    def __init__(self, months=0, seconds=0):
        if seconds < 0 < months or months < 0 < seconds:
            raise ElementPathValueError('signs differ: (months=%d, seconds=%d)' % (months, seconds))
        self.months = months
        self.seconds = decimal.Decimal(seconds)

    def __repr__(self):
        return '%s(months=%r, seconds=%s)' % (self.__class__.__name__, self.months, str(self.seconds))

    def __str__(self):
        m = abs(self.months)
        years, months = m // 12, m % 12
        s = abs(self.seconds)
        days, hours, minutes, seconds = int(s // 86400), int(s // 3600 % 24), int(s // 60 % 60), s % 60

        value = '-P' if self.sign else 'P'
        if years or months or days:
            if years:
                value += '%dY' % years
            if months:
                value += '%dM' % months
            if days:
                value += '%dD' % days

        if hours or minutes or seconds:
            value += 'T'
            if hours:
                value += '%dH' % hours
            if minutes:
                value += '%dM' % minutes
            if seconds:
                value += '%sS' % seconds
        elif value[-1] == 'P':
            value += 'T0S'
        return value

    def __unicode__(self):
        return str(self)

    @classmethod
    def fromstring(cls, value):
        """
        Creates a Duration instance from a formatted XSD duration string.

        :param value: the formatted ISO 8601 duration, with no week fragment and an optional decimal \
        part only for seconds fragment. If value is `None` creates a zero duration instance.
        :return: a new Duration instance.
        """
        match = XSD_DURATION_PATTERN.search(value)
        if match is None:
            raise ElementPathValueError('%r is not an xs:duration value.' % value)

        sign, years, months, days, hours, minutes, seconds = match.groups()
        seconds = decimal.Decimal(seconds or 0)
        minutes = int(minutes or 0) + int(seconds // 60)
        seconds = seconds % 60
        hours = int(hours or 0) + minutes // 60
        minutes = minutes % 60
        days = int(days or 0) + hours // 24
        hours = hours % 24
        months = int(months or 0) + 12 * int(years or 0)

        if sign is None:
            seconds = seconds + (days * 24 + hours) * 3600 + minutes * 60
        else:
            months = -months
            seconds = -seconds - (days * 24 + hours) * 3600 - minutes * 60

        return cls(months=months, seconds=seconds)

    @property
    def sign(self):
        return '-' if self.months < 0 or self.seconds < 0 else ''

    def _compare_durations(self, other, op):
        """
        Ordering is defined through comparison of four datetime values.

        Ref: https://www.w3.org/TR/2012/REC-xmlschema11-2-20120405/#duration
        """
        if not isinstance(other, self.__class__):
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))
        m1, s1 = self.months, int(self.seconds)
        m2, s2 = other.months, int(other.seconds)
        ms1, ms2 = int((self.seconds - s1) * 1000000), int((other.seconds - s2) * 1000000)
        return all([
            op(timedelta(months2days(1696, 9, m1), s1, ms1), timedelta(months2days(1696, 9, m2), s2, ms2)),
            op(timedelta(months2days(1697, 2, m1), s1, ms1), timedelta(months2days(1697, 2, m2), s2, ms2)),
            op(timedelta(months2days(1903, 3, m1), s1, ms1), timedelta(months2days(1903, 3, m2), s2, ms2)),
            op(timedelta(months2days(1903, 7, m1), s1, ms1), timedelta(months2days(1903, 7, m2), s2, ms2)),
        ])

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.months == other.months and self.seconds == other.seconds
        else:
            return other == (self.months, self.seconds)

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return self.months != other.months or self.seconds != other.seconds
        else:
            return other != (self.months, self.seconds)

    def __lt__(self, other):
        return self._compare_durations(other, operator.lt)

    def __le__(self, other):
        return self == other or self._compare_durations(other, operator.le)

    def __gt__(self, other):
        return self._compare_durations(other, operator.gt)

    def __ge__(self, other):
        return self == other or self._compare_durations(other, operator.ge)


class YearMonthDuration(Duration):

    def __init__(self, months=0, seconds=0):
        super(YearMonthDuration, self).__init__(months, seconds)
        if self.seconds:
            raise ElementPathValueError('seconds must be 0 for %r.' % self.__class__.__name__)

    def __repr__(self):
        return '%s(months=%r)' % (self.__class__.__name__, self.months)

    def __add__(self, other):
        if not isinstance(other, self.__class__):
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))
        return YearMonthDuration(months=self.months + other.months)

    def __sub__(self, other):
        if not isinstance(other, self.__class__):
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))
        return YearMonthDuration(months=self.months - other.months)

    def __mul__(self, other):
        if not isinstance(other, (float, int, decimal.Decimal)):
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))
        return YearMonthDuration(months=int(float(self.months * other) + 0.5))

    def __truediv__(self, other):
        if isinstance(other, self.__class__):
            return self.months / other.months
        elif isinstance(other, (float, int, decimal.Decimal)):
            return YearMonthDuration(months=int(float(self.months / other) + 0.5))
        else:
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))


class DayTimeDuration(Duration):

    def __init__(self, months=0, seconds=0):
        super(DayTimeDuration, self).__init__(months, seconds)
        if self.months:
            raise ElementPathValueError('months must be 0 for %r.' % self.__class__.__name__)

    def __repr__(self):
        return '%s(seconds=%s)' % (self.__class__.__name__, str(self.seconds))

    def __add__(self, other):
        if not isinstance(other, self.__class__):
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))
        return DayTimeDuration(seconds=self.seconds + other.seconds)

    def __sub__(self, other):
        if not isinstance(other, self.__class__):
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))
        return DayTimeDuration(seconds=self.seconds - other.seconds)

    def __mul__(self, other):
        if not isinstance(other, (float, int, decimal.Decimal)):
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))
        return DayTimeDuration(seconds=int(float(self.seconds * other) + 0.5))

    def __truediv__(self, other):
        if isinstance(other, self.__class__):
            return self.seconds / other.seconds
        elif isinstance(other, (float, int, decimal.Decimal)):
            return DayTimeDuration(seconds=int(float(self.seconds / other) + 0.5))
        else:
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))


class Timezone(tzinfo):
    """
    A tzinfo implementation for XSD timezone offsets. Offsets must be specified
    between -14:00 and +14:00.

    :param offset: a timedelta instance or an XSD timezone formatted string.
    """
    _maxoffset = timedelta(hours=14, minutes=0)
    _minoffset = -_maxoffset

    def __init__(self, offset):
        super(Timezone, self).__init__()
        if offset == 'Z':
            offset = timedelta(0)
        elif isinstance(offset, string_base_type):
            try:
                hours, minutes = offset.split(':')
                hours = int(hours)
                minutes = int(minutes) if hours >= 0 else -int(minutes)
                offset = timedelta(hours=hours, minutes=minutes)
            except ValueError:
                raise ElementPathValueError("offset is not an XSD timezone formatted string")
        elif not isinstance(offset, timedelta):
            raise ElementPathTypeError("offset must be a timedelta or an XSD timezone formatted string")

        if offset < self._minoffset or offset > self._maxoffset:
            raise ElementPathValueError("offset must be between -14:00 and +14:00")
        self.offset = offset

    def __getinitargs__(self):
        return self.offset,

    def __eq__(self, other):
        if type(other) != Timezone:
            return False
        return self.offset == other.offset

    def __hash__(self):
        return hash(self.offset)

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.offset)

    def __str__(self):
        return self.tzname(None)

    def utcoffset(self, dt):
        if not isinstance(dt, datetime) and dt is not None:
            raise ElementPathTypeError("utcoffset() argument must be a datetime instance or None")
        return self.offset

    def tzname(self, dt):
        if not isinstance(dt, datetime) and dt is not None:
            raise ElementPathTypeError("tzname() argument must be a datetime instance or None")

        if not self.offset:
            return 'UTC'
        elif self.offset < timedelta(0):
            sign, offset = '-', -self.offset
        else:
            sign, offset = '+', self.offset

        hours, minutes = offset.seconds // 3600, offset.seconds // 60 % 60
        return 'UTC{}{:02d}:{:02d}'.format(sign, hours, minutes)

    def dst(self, dt):
        if not isinstance(dt, datetime) and dt is not None:
            raise ElementPathTypeError("dst() argument must be a datetime instance or None")

    def fromutc(self, dt):
        if isinstance(dt, datetime):
            return dt + self.offset
        elif dt is not None:
            raise TypeError("fromutc() argument must be a datetime instance or None")


class UntypedAtomic(object):
    """
    Class for xs:untypedAtomic data. Provides special methods for comparing
    and converting to basic data types.

    :param value: the untyped value, usually a string.
    """
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return '%s(value=%r)' % (self.__class__.__name__, self.value)

    def _get_operands(self, other, force_float=True):
        """
        Returns a couple of operands, applying a cast to the instance value based on
        the type of the *other* argument.

        :param other: The other operand, that determines the cast for the untyped instance.
        :param force_float: Force a conversion to float if *other* is an UntypedAtomic instance.
        :return: A couple of values.
        """
        if isinstance(other, UntypedAtomic):
            if force_float:
                return float(self.value), float(other.value)
            else:
                return self.value, other.value
        elif isinstance(other, int):
            return float(self.value), other
        else:
            return type(other)(self.value), other

    def __eq__(self, other):
        return operator.eq(*self._get_operands(other, force_float=False))

    def __ne__(self, other):
        return not operator.eq(*self._get_operands(other, force_float=False))

    def __lt__(self, other):
        return operator.lt(*self._get_operands(other))

    def __le__(self, other):
        return operator.le(*self._get_operands(other))

    def __gt__(self, other):
        return operator.gt(*self._get_operands(other))

    def __ge__(self, other):
        return operator.ge(*self._get_operands(other))

    def __add__(self, other):
        return operator.add(*self._get_operands(other))
    __radd__ = __add__

    def __sub__(self, other):
        return operator.sub(*self._get_operands(other))

    def __rsub__(self, other):
        return operator.sub(*reversed(self._get_operands(other)))

    def __mul__(self, other):
        return operator.mul(*self._get_operands(other))
    __rmul__ = __mul__

    def __truediv__(self, other):
        return operator.truediv(*self._get_operands(other))

    def __rtruediv__(self, other):
        return operator.truediv(*reversed(self._get_operands(other)))

    def __int__(self):
        return int(self.value)

    def __float__(self):
        return float(self.value)

    def __bool__(self):
        return bool(self.value)

    def __abs__(self):
        return abs(self.value)

    if PY3:
        def __str__(self):
            return str(self.value)

        def __bytes__(self):
            return bytes(self.value, encoding='utf-8')

    else:
        def __unicode__(self):
            return unicode(self.value)

        def __str__(self):
            try:
                return str(self.value)
            except UnicodeEncodeError:
                return self.value.encode('utf-8')

        def __bytes__(self):
            return self.value.encode('utf-8')

        def __div__(self, other):
            return operator.truediv(*self._get_operands(other))

        def __rdiv__(self, other):
            return operator.truediv(*reversed(self._get_operands(other)))

        def __long__(self):
            return int(self.value)
