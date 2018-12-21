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
XSD atomic datatypes for XPath. Includes a class for UntypedAtomic data and some
classes for XSD datetime and duration types.
"""
from __future__ import division, unicode_literals

from abc import ABCMeta
import operator
import re
import decimal
from datetime import datetime, timedelta, tzinfo
from calendar import isleap, leapdays, monthrange

from .compat import PY3, string_base_type, add_metaclass
from .exceptions import ElementPathTypeError, ElementPathValueError


FRACTION_DIGITS_RE_PATTERN = re.compile(r'\.(\d+)$')
ISO_TIMEZONE_RE_PATTERN = re.compile(r'(Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))$')
XSD_DURATION_PATTERN = re.compile(
    r'^(-)?P(?=(?:\d|T))(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?(?:T(?=\d)(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$'
)


def adjust_day(year, month, day):
    if month in {1, 3, 5, 7, 8, 10, 12}:
        return day
    elif month in {4, 6, 9, 11}:
        return min(day, 30)
    else:
        return min(day, 29) if isleap(year) else min(day, 28)


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


@add_metaclass(ABCMeta)
class AbstractDateTime(object):
    """
    A class for representing XSD date/time objects. The reference xs:dateTime used is
    the datetime.datetime default 1900-01-01T00:00:00.

    :param dt: the datetime.datetime instance that stores the XSD Date/Time value.
    :param bce: if `True` the date value refers to a BCE (Before Common Era) date.
    """
    formats = ('%Y-%m-%dT%H:%M:%S.%f',)

    def __init__(self, dt, bce=False):
        if not isinstance(dt, datetime):
            raise ElementPathTypeError("1st argument must be a datetime.datetime instance.")
        elif not isinstance(bce, bool):
            raise ElementPathTypeError("2nd argument must be a %r instance." % bool)

        fmt = '-%s' % self.formats[0] if bce else self.formats[0]
        if dt.microsecond and '%f' not in fmt:
            if '%S' not in fmt:
                raise ElementPathValueError("microsecond must be zero for %r instance." % type(self))
            else:
                fmt += '.%f'

        if '%H' not in fmt and (dt.hour or dt.minute or dt.second):
            raise ElementPathValueError("hour, minute, second must be zero for %r instance." % type(self))
        elif '%Y' not in fmt and (dt.year != 1900 or bce):
            raise ElementPathValueError("year must be absent for %r instance." % type(self))
        elif '%m' not in fmt and dt.month != 1:
            raise ElementPathValueError("month must be absent for %r instance." % type(self))
        elif '%d' not in fmt and dt.day != 1:
            if dt.day != 2 or '%H:%M:%S' not in fmt:
                raise ElementPathValueError("day must be absent for %r instance." % type(self))

        self._dt = dt
        self._bce = bce
        self._fmt = fmt

    @property
    def dt(self):
        return self._dt

    @dt.setter
    def dt(self, dt):
        self._dt = dt

    @property
    def fmt(self):
        return self._fmt

    @property
    def bce(self):
        return self._bce

    @property
    def year(self):
        return self._dt.year

    @property
    def month(self):
        return self._dt.month

    @property
    def day(self):
        return self._dt.day

    @property
    def hour(self):
        return self._dt.hour

    @property
    def minute(self):
        return self._dt.minute

    @property
    def second(self):
        return self._dt.second

    @property
    def microsecond(self):
        return self._dt.microsecond

    @property
    def tzinfo(self):
        return self._dt.tzinfo

    @tzinfo.setter
    def tzinfo(self, tz):
        self._dt = self._dt.replace(tzinfo=tz)

    def __repr__(self):
        return '%s(dt=%s, bce=%r)' % (self.__class__.__name__, repr(self._dt)[9:], self._bce)

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
    def fromstring(cls, text, tz=None, version='1.1'):
        """
        Creates an XSD date/time instance from a string formatted value, trying the
        class formats list.

        :param text: a string containing an XSD formatted date/time specification.
        :param tz: optional implicit timezone information, must be a `Timezone` instance.
        :param version: the XSD version to use for parsing the string.
        :return: an AbstractDateTime concrete subclass instance.
        """
        if not isinstance(text, string_base_type):
            raise ElementPathTypeError('1st argument has an invalid type %r' % type(text))
        elif tz and not isinstance(tz, Timezone):
            raise ElementPathTypeError('2nd argument has an invalid type %r' % type(text))

        tz_match = ISO_TIMEZONE_RE_PATTERN.search(text)
        dt_part = text if tz_match is None else text[:tz_match.span()[0]]
        year_zero = '0000' in dt_part[:5]

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
                # Check ISO 8601 format restrictions
                if 't' in text:
                    raise ElementPathValueError("%r: 't' separator must be in uppercase" % text)

                regex = fmt.replace('%Y', r'\d{4}').replace('%m', r'(?P<month>\d{1,2})'). \
                    replace('%d', r'(?P<day>\d{1,2})').replace('%H', r'(?P<hour>\d{1,2})'). \
                    replace('%M', r'(?P<minute>\d{1,2})').replace('%S', r'(?P<second>\d{1,2})'). \
                    replace('.', r'\.').replace('%f', r'\d{1,6}')

                match = re.match(regex, text)
                if match is None:
                    raise ElementPathValueError("unmatched value %r for format %r" % (text, fmt))

                for k, v in match.groupdict().items():
                    if len(v) < 2:
                        raise ElementPathValueError("%r: %s must be two digits" % (k, v))

                # Adapt the value and add timezone info
                if '24:00:00' in fmt:
                    if '%d' in fmt:
                        dt += timedelta(days=1)
                    fmt = fmt.replace('24:00:00', '%H:%M:%S')

                if tz_match is not None:
                    dt = dt.replace(tzinfo=Timezone.fromstring(tz_match.group()))
                elif tz is not None:
                    dt = dt.replace(tzinfo=tz)

                if '%Y' not in fmt:
                    return cls(dt)
                elif year_zero:
                    if version == '1.0':
                        raise ElementPathValueError('%r: "0000" is an illegal year value for XSD 1.0' % text)
                    return cls(dt.replace(year=1), True)
                elif not fmt.startswith('-%Y'):
                    return cls(dt, False)
                elif version == '1.0':
                    return cls(dt, True)
                else:
                    return cls(dt.replace(year=dt.year + 1), True)
        else:
            if len(cls.formats) == 1:
                raise ElementPathValueError('Invalid value %r for datetime format %r' % (text, cls.formats[0]))
            else:
                raise ElementPathValueError('Invalid value %r for datetime formats %r' % (text, cls.formats))

    def replace(self, **kwargs):
        if '%Y' in self._fmt:
            return type(self)(self._dt.replace(**kwargs), self._bce)
        else:
            return type(self)(self._dt.replace(**kwargs))

    def _date_operator(self, op, other):
        if isinstance(other, self.__class__):
            if self._bce ^ other.bce:
                dt1, dt2 = self._get_operands(other)
                delta1 = op(dt1, datetime(1, 1, 1, tzinfo=dt1.tzinfo))
                delta2 = op(dt2, datetime(1, 1, 1, tzinfo=dt2.tzinfo))
                delta = timedelta(seconds=delta1.total_seconds() + delta2.total_seconds())
            else:
                delta = operator.sub(*self._get_operands(other))
            return DayTimeDuration.fromtimedelta(-delta if self.bce else delta)
        elif isinstance(other, DayTimeDuration):
            delta = other.get_timedelta()
            try:
                dt = op(self.dt, delta)
            except OverflowError:
                seconds = delta.total_seconds()
                if self.bce ^ (seconds > 0):
                    raise
                dt_seconds = abs((self.dt - datetime(1, 1, 1)).total_seconds() - seconds)
                dt = datetime(1, 1, 1) + timedelta(seconds=dt_seconds)
                bce = not self.bce
            else:
                bce = self.bce

            if '%H' not in self._fmt:
                dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            return type(self)(dt, bce)

        elif isinstance(other, YearMonthDuration):
            month = op(self.dt.month - 1, other.months) % 12 + 1
            year = op(self.dt.year, ((self.dt.month - 1) + other.months) // 12)
            if year > 0:
                bce = self.bce
            else:
                bce = not self.bce
                year = abs(year) + 1
            dt = self.dt.replace(year=year, month=month, day=adjust_day(year, month, self.dt.day))
            return type(self)(dt, bce)
        else:
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))

    # For Py2 compatibility: Python 2 can't compares offset-naive and offset-aware datetimes
    def _get_operands(self, other):
        dt = getattr(other, 'dt', other)
        if self._dt.tzinfo is dt.tzinfo:
            return self._dt, dt
        elif self.tzinfo is None:
            return self._dt.replace(tzinfo=Timezone(timedelta(0))), dt
        elif dt.tzinfo is None:
            return self._dt, dt.replace(tzinfo=Timezone(timedelta(0)))
        else:
            return self._dt, dt

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return operator.eq(*self._get_operands(other)) and self._bce == other._bce
        elif isinstance(other, datetime):
            return operator.eq(*self._get_operands(other)) and not self._bce
        else:
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))

    def __lt__(self, other):
        if not isinstance(other, self.__class__):
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))
        elif self._bce ^ other.bce:
            return self._bce
        elif self._bce:
            return operator.gt(*self._get_operands(other))
        else:
            return operator.lt(*self._get_operands(other))

    def __le__(self, other):
        if not isinstance(other, self.__class__):
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))
        elif self._bce ^ other.bce:
            return self._bce
        elif self._bce:
            return operator.ge(*self._get_operands(other))
        else:
            return operator.le(*self._get_operands(other))

    def __gt__(self, other):
        if not isinstance(other, self.__class__):
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))
        elif self._bce ^ other.bce:
            return not self._bce
        elif self._bce:
            return operator.lt(*self._get_operands(other))
        else:
            return operator.gt(*self._get_operands(other))

    def __ge__(self, other):
        if not isinstance(other, self.__class__):
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))
        elif self._bce ^ other.bce:
            return not self._bce
        elif self._bce:
            return operator.le(*self._get_operands(other))
        else:
            return operator.ge(*self._get_operands(other))


class DateTime(AbstractDateTime):
    """Class for representing xs:dateTime data."""
    formats = ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT24:00:00',
               '-%Y-%m-%dT%H:%M:%S', '-%Y-%m-%dT%H:%M:%S.%f', '-%Y-%m-%dT24:00:00')

    def __add__(self, other):
        if isinstance(other, self.__class__):
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))
        return self._date_operator(operator.add, other)

    def __sub__(self, other):
        return self._date_operator(operator.sub, other)


class Date(AbstractDateTime):
    """Class for representing xs:date data."""
    formats = ('%Y-%m-%d', '-%Y-%m-%d')

    def __add__(self, other):
        if isinstance(other, self.__class__):
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))
        return self._date_operator(operator.add, other)

    def __sub__(self, other):
        return self._date_operator(operator.sub, other)


class GregorianDay(AbstractDateTime):
    """Class for representing xs:gDay data."""
    formats = ('---%d',)

    def __init__(self, dt):
        super(GregorianDay, self).__init__(dt)


class GregorianMonth(AbstractDateTime):
    """Class for representing xs:gMonth data."""
    formats = ('--%m',)

    def __init__(self, dt):
        super(GregorianMonth, self).__init__(dt)


class GregorianMonthDay(AbstractDateTime):
    """Class for representing xs:gMonthDay data."""
    formats = ('--%m-%d',)

    def __init__(self, dt):
        super(GregorianMonthDay, self).__init__(dt)


class GregorianYear(AbstractDateTime):
    """Class for representing xs:gYear data."""
    formats = ('%Y', '-%Y')


class GregorianYearMonth(AbstractDateTime):
    """Class for representing xs:gYearMonth data."""
    formats = ('%Y-%m', '-%Y-%m')


class Time(AbstractDateTime):
    """Class for representing xs:time data."""
    formats = ('%H:%M:%S', '%H:%M:%S.%f', '24:00:00')

    def __init__(self, dt):
        super(Time, self).__init__(dt)

    def __add__(self, other):
        if isinstance(other, DayTimeDuration):
            dt = self.dt + other.get_timedelta()
            return Time(dt.replace(year=1900, month=1, day=1))
        else:
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))

    def __sub__(self, other):
        if isinstance(other, self.__class__):
            delta = operator.sub(*self._get_operands(other))
            return DayTimeDuration.fromtimedelta(delta)
        elif isinstance(other, DayTimeDuration):
            dt = self.dt - other.get_timedelta()
            return Time(dt.replace(year=1900, month=1, day=1))
        else:
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))


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
    def fromstring(cls, text):
        """
        Creates a Duration instance from a formatted XSD duration string.

        :param text: an ISO 8601 representation without week fragment and an optional decimal part \
        only for seconds fragment.
        """
        match = XSD_DURATION_PATTERN.search(text)
        if match is None:
            raise ElementPathValueError('%r is not an xs:duration value.' % text)

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

    if not PY3:
        def __div__(self, other):
            return self.__truediv__(other)


class DayTimeDuration(Duration):

    def __init__(self, months=0, seconds=0):
        super(DayTimeDuration, self).__init__(months, seconds)
        if self.months:
            raise ElementPathValueError('months must be 0 for %r.' % self.__class__.__name__)

    @classmethod
    def fromtimedelta(cls, td):
        return cls(seconds=decimal.Decimal('{}.{:06}'.format(td.days * 86400 + td.seconds, td.microseconds)))

    def get_timedelta(self):
        return timedelta(seconds=int(self.seconds), microseconds=int(self.seconds % 1 * 1000000))

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

    if not PY3:
        def __div__(self, other):
            return self.__truediv__(other)


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
        if not isinstance(offset, timedelta):
            raise ElementPathTypeError("offset must be a timedelta or an XSD timezone formatted string")
        if offset < self._minoffset or offset > self._maxoffset:
            raise ElementPathValueError("offset must be between -14:00 and +14:00")
        self.offset = offset

    @classmethod
    def fromstring(cls, text):
        if text == 'Z':
            return cls(timedelta(0))
        elif isinstance(text, string_base_type):
            try:
                hours, minutes = text.split(':')
                hours = int(hours)
                minutes = int(minutes) if hours >= 0 else -int(minutes)
                return cls(timedelta(hours=hours, minutes=minutes))
            except ValueError:
                raise ElementPathValueError("%r: not an XSD timezone formatted string" % text)

    @classmethod
    def fromduration(cls, duration):
        return cls(timedelta(seconds=int(duration.seconds)))

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
