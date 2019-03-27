# -*- coding: utf-8 -*-
#
# Copyright (c), 2018-2019, SISSA (International School for Advanced Studies).
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

from abc import ABCMeta, abstractmethod
import operator
import re
import decimal
import datetime
import base64
from collections import namedtuple
from calendar import isleap, leapdays

from .compat import PY3, string_base_type, add_metaclass
from .exceptions import ElementPathTypeError, ElementPathValueError

###
# Date/Time helpers
MONTH_DAYS = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
MONTH_DAYS_LEAP = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def adjust_day(year, month, day):
    if month in {1, 3, 5, 7, 8, 10, 12}:
        return day
    elif month in {4, 6, 9, 11}:
        return min(day, 30)
    else:
        return min(day, 29) if isleap(year) else min(day, 28)


def days_from_common_era(year):
    """
    Returns the number of days from from 0001-01-01 to the provided year. For a
    common era year the days are counted until the last day of December, for a
    BCE year the days are counted down from the end to the 1st of January.
    """
    if year > 0:
        return year * 365 + year // 4 - year // 100 + year // 400
    elif year >= -1:
        return year * 366
    else:
        year = -year - 1
        return -(366 + year * 365 + year // 4 - year // 100 + year // 400)


DAYS_IN_4Y = days_from_common_era(4)
DAYS_IN_100Y = days_from_common_era(100)
DAYS_IN_400Y = days_from_common_era(400)


def months2days(year, month, months_delta):
    """
    Converts a delta of months to a delta of days, counting from the 1st day of the month,
    relative to the year and the month passed as arguments.

    :param year: the reference start year, a negative or zero value means a BCE year \
    (0 is 1 BCE, -1 is 2 BCE, -2 is 3 BCE, etc).
    :param month: the starting month (1-12).
    :param months_delta: the number of months, if negative count backwards.
    """
    if not months_delta:
        return 0

    total_months = month - 1 + months_delta
    target_year = year + total_months // 12
    target_month = total_months % 12 + 1

    if month <= 2:
        y_days = 365 * (target_year - year) + leapdays(year, target_year)
    else:
        y_days = 365 * (target_year - year) + leapdays(year + 1, target_year + 1)

    months_days = MONTH_DAYS_LEAP if isleap(target_year) else MONTH_DAYS
    if target_month >= month:
        m_days = sum(months_days[m] for m in range(month, target_month))
        return y_days + m_days if y_days >= 0 else y_days + m_days
    else:
        m_days = sum(months_days[m] for m in range(target_month, month))
        return y_days - m_days if y_days >= 0 else y_days - m_days


class Timezone(datetime.tzinfo):
    """
    A tzinfo implementation for XSD timezone offsets. Offsets must be specified
    between -14:00 and +14:00.

    :param offset: a timedelta instance or an XSD timezone formatted string.
    """
    _maxoffset = datetime.timedelta(hours=14, minutes=0)
    _minoffset = -_maxoffset

    def __init__(self, offset):
        super(Timezone, self).__init__()
        if not isinstance(offset, datetime.timedelta):
            raise ElementPathTypeError("offset must be a datetime.timedelta or an XSD timezone formatted string")
        if offset < self._minoffset or offset > self._maxoffset:
            raise ElementPathValueError("offset must be between -14:00 and +14:00")
        self.offset = offset

    @classmethod
    def fromstring(cls, text):
        if text == 'Z':
            return cls(datetime.timedelta(0))
        elif isinstance(text, string_base_type):
            try:
                hours, minutes = text.split(':')
                hours = int(hours)
                minutes = int(minutes) if hours >= 0 else -int(minutes)
                return cls(datetime.timedelta(hours=hours, minutes=minutes))
            except ValueError:
                raise ElementPathValueError("%r: not an XSD timezone formatted string" % text)

    @classmethod
    def fromduration(cls, duration):
        return cls(datetime.timedelta(seconds=int(duration.seconds)))

    def __getinitargs__(self):
        return self.offset,

    def __eq__(self, other):
        return isinstance(other, Timezone) and self.offset == other.offset

    def __ne__(self, other):
        return not isinstance(other, Timezone) or self.offset != other.offset

    def __hash__(self):
        return hash(self.offset)

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.offset)

    def __str__(self):
        return self.tzname(None)

    def utcoffset(self, dt):
        if not isinstance(dt, datetime.datetime) and dt is not None:
            raise ElementPathTypeError("utcoffset() argument must be a datetime.datetime instance or None")
        return self.offset

    def tzname(self, dt):
        if not isinstance(dt, datetime.datetime) and dt is not None:
            raise ElementPathTypeError("tzname() argument must be a datetime.datetime instance or None")

        if not self.offset:
            return 'Z'
        elif self.offset < datetime.timedelta(0):
            sign, offset = '-', -self.offset
        else:
            sign, offset = '+', self.offset

        hours, minutes = offset.seconds // 3600, offset.seconds // 60 % 60
        return '{}{:02d}:{:02d}'.format(sign, hours, minutes)

    def dst(self, dt):
        if not isinstance(dt, datetime.datetime) and dt is not None:
            raise ElementPathTypeError("dst() argument must be a datetime.datetime instance or None")

    def fromutc(self, dt):
        if isinstance(dt, datetime.datetime):
            return dt + self.offset
        elif dt is not None:
            raise TypeError("fromutc() argument must be a datetime.datetime instance or None")


@add_metaclass(ABCMeta)
class AbstractDateTime(object):
    """
    A class for representing XSD date/time objects. It uses and internal datetime.datetime
    attribute and an integer attribute for processing BCE years or for years after 9999 CE.
    """
    version = '1.0'
    _pattern = re.compile(r'^$')
    _utc_timezone = Timezone(datetime.timedelta(0))

    def __init__(self, year=2000, month=1, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=None):
        if hour == 24 and minute == second == 0:
            hour = 0

        if 1 <= year <= 9999:
            self._year = None
            self._dt = datetime.datetime(year, month, day, hour, minute, second, microsecond, tzinfo)
        elif year == 0:
            raise ElementPathValueError('0 is an illegal value for year')
        elif not isinstance(year, int):
            raise ElementPathTypeError("wrong type %r for year" % type(year))
        else:
            self._year = year
            if isleap(year):
                self._dt = datetime.datetime(4, month, day, hour, minute, second, microsecond, tzinfo)
            else:
                self._dt = datetime.datetime(6, month, day, hour, minute, second, microsecond, tzinfo)

    def __repr__(self):
        fields = self._pattern.groupindex.keys()
        arg_string = ', '.join(
            str(getattr(self, k)) for k in ['year', 'month', 'day', 'hour', 'minute'] if k in fields
        )
        if 'second' in fields:
            if self.microsecond:
                arg_string += ', %d.%06d' % (self.second, self.microsecond)
            else:
                arg_string += ', %d' % self.second

        if self.tzinfo is not None:
            arg_string += ', tzinfo=%r' % self.tzinfo
        return '%s(%s)' % (self.__class__.__name__, arg_string)

    @abstractmethod
    def __str__(self):
        pass

    def __unicode__(self):
        return str(self)

    @property
    def year(self):
        return self._year or self._dt.year

    @property
    def bce(self):
        return self._year is not None and self._year < 0

    @property
    def iso_year(self):
        """The ISO string representation of the year field."""
        year = self.year
        if -9999 <= year < -1:
            return '{:05}'.format(year if self.version == '1.0' else year + 1)
        elif year == -1:
            return '{:04}'.format(year if self.version == '1.0' else year + 1)
        elif 0 <= year <= 9999:
            return '{:04}'.format(year)
        else:
            return str(year)

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

    @classmethod
    def fromstring(cls, datetime_string, tzinfo=None):
        """
        Creates an XSD date/time instance from a string formatted value.

        :param datetime_string: a string containing an XSD formatted date/time specification.
        :param tzinfo: optional implicit timezone information, must be a `Timezone` instance.
        :return: an AbstractDateTime concrete subclass instance.
        """
        if not isinstance(datetime_string, string_base_type):
            raise ElementPathTypeError('1st argument has an invalid type %r' % type(datetime_string))
        elif tzinfo and not isinstance(tzinfo, Timezone):
            raise ElementPathTypeError('2nd argument has an invalid type %r' % type(tzinfo))

        match = cls._pattern.match(datetime_string)
        if match is None:
            raise ElementPathValueError('Invalid datetime string %r for %r' % (datetime_string, cls))

        kwargs = {k: int(v) if k != 'tzinfo' else Timezone.fromstring(v)
                  for k, v in match.groupdict().items() if v is not None}

        if 'tzinfo' not in kwargs and tzinfo is not None:
            kwargs['tzinfo'] = tzinfo
        if 'microsecond' in kwargs:
            pow10 = 6 - len(match.groupdict()['microsecond'])
            kwargs['microsecond'] = 0 if pow10 < 0 else kwargs['microsecond'] * 10**pow10

        year = kwargs.get('year')
        if year is not None and year <= 0 and cls.version != '1.0':
            kwargs['year'] -= 1
        return cls(**kwargs)

    @classmethod
    def fromdatetime(cls, dt, year=None):
        """
        Creates an XSD date/time instance from a datetime.datetime/date/time instance.

        :param dt: the datetime, date or time instance that stores the XSD Date/Time value.
        :param year: if an year is provided the created instance refers to it and the \
        possibly present *dt.year* part is ignored.
        :return: an AbstractDateTime concrete subclass instance.
        """
        if not isinstance(dt, (datetime.datetime, datetime.date, datetime.time)):
            raise ElementPathTypeError('1st argument has an invalid type %r' % type(dt))
        elif year is not None and not isinstance(year, int):
            raise ElementPathTypeError('2nd argument has an invalid type %r' % type(year))

        kwargs = {k: getattr(dt, k) for k in cls._pattern.groupindex.keys() if hasattr(dt, k)}
        if year is not None:
            kwargs['year'] = year
        return cls(**kwargs)

    # Python can't compares offset-naive and offset-aware datetimes
    def _get_operands(self, other):
        if isinstance(other, (self.__class__, datetime.datetime)) or isinstance(self, other.__class__):
            dt = getattr(other, '_dt', other)
            if self._dt.tzinfo is dt.tzinfo:
                return self._dt, dt
            elif self.tzinfo is None:
                return self._dt.replace(tzinfo=self._utc_timezone), dt
            elif dt.tzinfo is None:
                return self._dt, dt.replace(tzinfo=self._utc_timezone)
            else:
                return self._dt, dt
        else:
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))

    def __eq__(self, other):
        try:
            return operator.eq(*self._get_operands(other)) and self.year == other.year
        except ElementPathTypeError:
            return False

    def __ne__(self, other):
        try:
            return operator.ne(*self._get_operands(other)) or self.year != other.year
        except ElementPathTypeError:
            return True


class OrderedDateTime(AbstractDateTime):
    @abstractmethod
    def __str__(self):
        pass

    @classmethod
    def fromdelta(cls, delta, adjust_timezone=False):
        """
        Creates an XSD dateTime/date instance from a datetime.timedelta related to
        0001-01-01T00:00:00 CE. In case of a date the time part is not counted.

        :param delta: a datetime.timedelta instance.
        :param adjust_timezone: if `True` adjust the timezone of Date objects \
        with eventually present hours and minutes.
        """
        try:
            dt = datetime.datetime(1, 1, 1) + delta
        except OverflowError:
            days = delta.days
            if days > 0:
                y400, days = divmod(days, DAYS_IN_400Y)
                y100, days = divmod(days, DAYS_IN_100Y)
                y4, days = divmod(days, DAYS_IN_4Y)
                y1, days = divmod(days, 365)
                year = y400 * 400 + y100 * 100 + y4 * 4 + y1 + 1
                if y1 == 4 or y100 == 4:
                    year -= 1
                    days = 365

                td = datetime.timedelta(days=days, seconds=delta.seconds, microseconds=delta.microseconds)
                dt = datetime.datetime(4 if isleap(year) else 6, 1, 1) + td

            elif days >= -366:
                year = -1
                td = datetime.timedelta(days=days, seconds=delta.seconds, microseconds=delta.microseconds)
                dt = datetime.datetime(5, 1, 1) + td

            else:
                days = -days - 366
                y400, days = divmod(days, DAYS_IN_400Y)
                y100, days = divmod(days, DAYS_IN_100Y)
                y4, days = divmod(days, DAYS_IN_4Y)
                y1, days = divmod(days, 365)
                year = -y400 * 400 - y100 * 100 - y4 * 4 - y1 - 2
                if y1 == 4 or y100 == 4:
                    year += 1
                    days = 365

                td = datetime.timedelta(days=-days, seconds=delta.seconds, microseconds=delta.microseconds)
                if not td:
                    dt = datetime.datetime(4 if isleap(year + 1) else 6, 1, 1)
                    year += 1
                else:
                    dt = datetime.datetime(5 if isleap(year + 1) else 7, 1, 1) + td
        else:
            year = dt.year

        if issubclass(cls, Date10):
            if adjust_timezone and dt.hour or dt.minute:
                if dt.tzinfo is None:
                    hour, minute = dt.hour, dt.minute
                else:
                    hour = dt.hour - dt.tzinfo.offset.hours
                    minute = dt.minute - dt.tzinfo.offset.minutes

                if hour < 14 or hour == 14 and minute == 0:
                    dt = dt.replace(tzinfo=Timezone(datetime.timedelta(hours=-hour, minutes=-minute)))
                else:
                    dt = dt.replace(tzinfo=Timezone(datetime.timedelta(hours=-dt.hour + 24, minutes=-minute)))
                    dt += datetime.timedelta(days=1)

            return cls(year, dt.month, dt.day, tzinfo=dt.tzinfo)
        return cls(year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond, dt.tzinfo)

    def todelta(self):
        """Returns the datetime.timedelta from 0001-01-01T00:00:00 CE."""
        if self._year is None:
            return self._dt - datetime.datetime(1, 1, 1)

        year, dt = self.year, self._dt
        tzinfo = None if dt.tzinfo is None else self._utc_timezone

        if year > 0:
            m_days = MONTH_DAYS_LEAP if isleap(year) else MONTH_DAYS
            days = days_from_common_era(year - 1) + sum(m_days[m] for m in range(1, dt.month))
        else:
            m_days = MONTH_DAYS_LEAP if isleap(year + 1) else MONTH_DAYS
            days = days_from_common_era(year) + sum(m_days[m] for m in range(1, dt.month))

        delta = (dt - datetime.datetime(dt.year, dt.month, day=1, tzinfo=tzinfo))
        return datetime.timedelta(days=days, seconds=delta.total_seconds())

    def _date_operator(self, op, other):
        if isinstance(other, self.__class__):
            dt1, dt2 = self._get_operands(other)
            if self._year is None and other._year is None:
                return DayTimeDuration.fromtimedelta(dt1 - dt2)
            return DayTimeDuration.fromtimedelta(self.todelta() - other.todelta())

        elif isinstance(other, (DayTimeDuration, datetime.timedelta)):
            delta = other.get_timedelta() if isinstance(other, DayTimeDuration) else other
            try:
                dt = op(self._dt, delta)
            except OverflowError:
                seconds = delta.total_seconds()
                if self.bce ^ (seconds > 0):
                    raise
                dt_seconds = abs((self._dt - datetime.datetime(1, 1, 1)).total_seconds() - seconds)
                dt = datetime.datetime(1, 1, 1) + datetime.timedelta(seconds=dt_seconds)
                bce = not self.bce
            else:
                bce = self.bce

            if 'hour' not in self._pattern.groupindex.keys():
                dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)

        elif isinstance(other, YearMonthDuration):
            month = op(self._dt.month - 1, other.months) % 12 + 1
            year = op(self._dt.year, ((self._dt.month - 1) + other.months) // 12)
            if year > 0:
                bce = self.bce
            else:
                bce = not self.bce
                year = abs(year) + 1
            dt = self._dt.replace(year=year, month=month, day=adjust_day(year, month, self._dt.day))

        else:
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))

        kwargs = {k: getattr(dt, k) for k in self._pattern.groupindex.keys()}
        if bce:
            kwargs['year'] = -kwargs['year']
        return type(self)(**kwargs)

    def __lt__(self, other):
        dt1, dt2 = self._get_operands(other)
        y1, y2 = self.year, other.year
        return y1 < y2 or y1 == y2 and dt1 < dt2

    def __le__(self, other):
        dt1, dt2 = self._get_operands(other)
        y1, y2 = self.year, other.year
        return y1 < y2 or y1 == y2 and dt1 <= dt2

    def __gt__(self, other):
        dt1, dt2 = self._get_operands(other)
        y1, y2 = self.year, other.year
        return y1 > y2 or y1 == y2 and dt1 > dt2

    def __ge__(self, other):
        dt1, dt2 = self._get_operands(other)
        y1, y2 = self.year, other.year
        return y1 > y2 or y1 == y2 and dt1 >= dt2

    def __add__(self, other):
        if isinstance(other, OrderedDateTime):
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))
        return self._date_operator(operator.add, other)

    def __sub__(self, other):
        return self._date_operator(operator.sub, other)


class DateTime10(OrderedDateTime):
    """XSD 1.0 xs:dateTime builtin type"""
    _pattern = re.compile(
        r'^(?P<year>(?:-)?[0-9]*[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})'
        r'(T(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-9]{2})(?:\.(?P<microsecond>[0-9]+))?)?'
        r'(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$')

    def __init__(self, year, month, day, hour=0, minute=0, second=0, microsecond=0, tzinfo=None):
        super(DateTime10, self).__init__(year, month, day, hour, minute, second, microsecond, tzinfo)

    def __str__(self):
        if self.microsecond:
            return '{}-{:02}-{:02}T{:02}:{:02}:{:02}.{:06}{}'.format(
                self.iso_year, self.month, self.day, self.hour, self.minute,
                self.second, self.microsecond, str(self.tzinfo or '')
            )
        return '{}-{:02}-{:02}T{:02}:{:02}:{:02}{}'.format(
            self.iso_year, self.month, self.day, self.hour, self.minute, self.second, str(self.tzinfo or '')
        )


class DateTime(DateTime10):
    """XSD 1.1 xs:dateTime builtin type"""
    version = '1.1'


class Date10(OrderedDateTime):
    """XSD 1.0 xs:date builtin type"""
    _pattern = re.compile(r'^(?P<year>(?:-)?[0-9]*[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})'
                          r'(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$')

    def __init__(self, year, month, day, tzinfo=None):
        super(Date10, self).__init__(year, month, day, tzinfo=tzinfo)

    def __str__(self):
        return '{}-{:02}-{:02}{}'.format(self.iso_year, self.month, self.day, str(self.tzinfo or ''))


class Date(Date10):
    """XSD 1.1 xs:date builtin type"""
    version = '1.1'


class XPathGregorianDay(AbstractDateTime):
    """xs:gDay datatype for XPath expressions"""
    _pattern = re.compile(r'^---(?P<day>[0-9]{2})(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$')

    def __init__(self, day, tzinfo=None):
        super(XPathGregorianDay, self).__init__(day=day, tzinfo=tzinfo)

    def __str__(self):
        return '---{:02}{}'.format(self.day, str(self.tzinfo or ''))


class GregorianDay(XPathGregorianDay, OrderedDateTime):
    """XSD xs:gDay builtin type"""


class XPathGregorianMonth(AbstractDateTime):
    """xs:gMonth datatype for XPath expressions"""
    _pattern = re.compile(r'^--(?P<month>[0-9]{2})(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$')

    def __init__(self, month, tzinfo=None):
        super(XPathGregorianMonth, self).__init__(month=month, tzinfo=tzinfo)

    def __str__(self):
        return '--{:02}{}'.format(self.month, str(self.tzinfo or ''))


class GregorianMonth(XPathGregorianMonth, OrderedDateTime):
    """XSD xs:gMonth builtin type"""


class XPathGregorianMonthDay(AbstractDateTime):
    """xs:gMonthDay datatype for XPath expressions"""
    _pattern = re.compile(r'^--(?P<month>[0-9]{2})-(?P<day>[0-9]{2})'
                          r'(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$')

    def __init__(self, month, day, tzinfo=None):
        super(XPathGregorianMonthDay, self).__init__(month=month, day=day, tzinfo=tzinfo)

    def __str__(self):
        return '--{:02}-{:02}{}'.format(self.month, self.day, str(self.tzinfo or ''))


class GregorianMonthDay(XPathGregorianMonthDay, OrderedDateTime):
    """XSD xs:gMonthDay builtin type"""


class XPathGregorianYear(AbstractDateTime):
    """xs:gYear datatype for XPath expressions"""
    _pattern = re.compile(r'^(?P<year>(?:-)?[0-9]*[0-9]{4})'
                          r'(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$')

    def __init__(self, year, tzinfo=None):
        super(XPathGregorianYear, self).__init__(year, tzinfo=tzinfo)

    def __str__(self):
        return '{}{}'.format(self.iso_year, str(self.tzinfo or ''))


class GregorianYear10(XPathGregorianYear, OrderedDateTime):
    """XSD 1.0 xs:gYear builtin type"""


class GregorianYear(GregorianYear10):
    """XSD 1.1 xs:gYear builtin type"""
    version = '1.1'


class XPathGregorianYearMonth(AbstractDateTime):
    """xs:gYearMonth datatype for XPath expressions"""
    _pattern = re.compile(r'^(?P<year>(?:-)?[0-9]*[0-9]{4})-(?P<month>[0-9]{2})'
                          r'(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$')

    def __init__(self, year, month, tzinfo=None):
        super(XPathGregorianYearMonth, self).__init__(year, month, tzinfo=tzinfo)

    def __str__(self):
        return '{}-{:02}{}'.format(self.iso_year, self.month, str(self.tzinfo or ''))


class GregorianYearMonth10(XPathGregorianYearMonth, OrderedDateTime):
    """XSD 1.0 xs:gYearMonth builtin type"""


class GregorianYearMonth(GregorianYearMonth10):
    """XSD 1.1 xs:gYearMonth builtin type"""
    version = '1.1'


class Time(AbstractDateTime):
    """XSD xs:time builtin type"""
    _pattern = re.compile(
        r'^(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-9]{2})(?:\.(?P<microsecond>[0-9]+))?'
        r'(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$')

    def __init__(self, hour=0, minute=0, second=0, microsecond=0, tzinfo=None):
        super(Time, self).__init__(hour=hour, minute=minute, second=second, microsecond=microsecond, tzinfo=tzinfo)

    def __str__(self):
        if self.microsecond:
            return '{:02}:{:02}:{:02}.{:06}{}'.format(
                self.hour, self.minute, self.second, self.microsecond, str(self.tzinfo or '')
            )
        return '{:02}:{:02}:{:02}{}'.format(self.hour, self.minute, self.second, str(self.tzinfo or ''))

    def __lt__(self, other):
        return operator.lt(*self._get_operands(other))

    def __le__(self, other):
        return operator.le(*self._get_operands(other))

    def __gt__(self, other):
        return operator.gt(*self._get_operands(other))

    def __ge__(self, other):
        return operator.ge(*self._get_operands(other))

    def __add__(self, other):
        if isinstance(other, DayTimeDuration):
            dt = self._dt + other.get_timedelta()
        elif isinstance(other, datetime.timedelta):
            dt = self._dt + other
        else:
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))
        return Time(dt.hour, dt.minute, dt.second, dt.microsecond, dt.tzinfo)

    def __sub__(self, other):
        if isinstance(other, self.__class__):
            delta = operator.sub(*self._get_operands(other))
            return DayTimeDuration.fromtimedelta(delta)
        elif isinstance(other, DayTimeDuration):
            dt = self._dt - other.get_timedelta()
            return Time(dt.hour, dt.minute, dt.second, dt.microsecond, dt.tzinfo)
        else:
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))


class Duration(object):
    """
    Base class for the XSD duration types.

    :param months: an integer value that represents years and months.
    :param seconds: a Decimal instance that represents days, hours, minutes, seconds and fractions of seconds.
    """
    _pattern = re.compile(
        r'^(-)?P(?=(?:[0-9]|T))(?:([0-9]+)Y)?(?:([0-9]+)M)?(?:([0-9]+)D)?'
        r'(?:T(?=[0-9])(?:([0-9]+)H)?(?:([0-9]+)M)?(?:([0-9]+(?:\.[0-9]+)?)S)?)?$'
    )

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
        match = cls._pattern.match(text)
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

        if cls is DayTimeDuration:
            if months:
                raise ElementPathValueError('months must be 0 for %r.' % cls.__name__)
            return cls(seconds=seconds)
        elif cls is YearMonthDuration:
            if seconds:
                raise ElementPathValueError('seconds must be 0 for %r.' % cls.__name__)
            return cls(months=months)
        return cls(months=months, seconds=seconds)

    @property
    def sign(self):
        return '-' if self.months < 0 or self.seconds < 0 else ''

    def _compare_durations(self, other, op):
        """
        Ordering is defined through comparison of four datetime.datetime values.

        Ref: https://www.w3.org/TR/2012/REC-xmlschema11-2-20120405/#duration
        """
        if not isinstance(other, self.__class__):
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))
        m1, s1 = self.months, int(self.seconds)
        m2, s2 = other.months, int(other.seconds)
        ms1, ms2 = int((self.seconds - s1) * 1000000), int((other.seconds - s2) * 1000000)
        return all([
            op(datetime.timedelta(months2days(1696, 9, m1), s1, ms1),
               datetime.timedelta(months2days(1696, 9, m2), s2, ms2)),
            op(datetime.timedelta(months2days(1697, 2, m1), s1, ms1),
               datetime.timedelta(months2days(1697, 2, m2), s2, ms2)),
            op(datetime.timedelta(months2days(1903, 3, m1), s1, ms1),
               datetime.timedelta(months2days(1903, 3, m2), s2, ms2)),
            op(datetime.timedelta(months2days(1903, 7, m1), s1, ms1),
               datetime.timedelta(months2days(1903, 7, m2), s2, ms2)),
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

    def __init__(self, months=0):
        super(YearMonthDuration, self).__init__(months, 0)

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

    def __init__(self, seconds=0):
        super(DayTimeDuration, self).__init__(0, seconds)

    @classmethod
    def fromtimedelta(cls, td):
        return cls(seconds=decimal.Decimal('{}.{:06}'.format(td.days * 86400 + td.seconds, td.microseconds)))

    def get_timedelta(self):
        return datetime.timedelta(seconds=int(self.seconds), microseconds=int(self.seconds % 1 * 1000000))

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


####
# XSD atomic builtins validators and values

XsdBuiltin = namedtuple('XsdBuiltin', 'validator value')
"""A namedtuple-based type for describing XSD builtin types."""

WHITESPACES_PATTERN = re.compile(r'\s+')
NMTOKEN_PATTERN = re.compile(r'^[\w.\-:]+$', flags=0 if PY3 else re.U)
NAME_PATTERN = re.compile(r'^(?:[^\d\W]|:)[\w.\-:]*$', flags=0 if PY3 else re.U)
NCNAME_PATTERN = re.compile(r'^[^\d\W][\w.\-]*$', flags=0 if PY3 else re.U)
QNAME_PATTERN = re.compile(
    r'^(?:(?P<prefix>[^\d\W][\w\-.\xb7\u0387\u06DD\u06DE]*):)?(?P<local>[^\d\W][\w\-.\xb7\u0387\u06DD\u06DE]*)$',
    flags=0 if PY3 else re.U
)
HEX_BINARY_PATTERN = re.compile(r'^[0-9a-fA-F]+$')
NOT_BASE64_BINARY_PATTERN = re.compile(r'[^0-9a-zA-z+/= \t\n]')
LANGUAGE_CODE_PATTERN = re.compile(r'^([a-zA-Z]{2}|[iI]-[a-zA-Z]+|[xX]-[a-zA-Z]{1,8})(-[a-zA-Z]{1,8})*$')
WRONG_ESCAPE_PATTERN = re.compile(r'%(?![a-eA-E\d]{2})')


def base64_binary_validator(x):
    if not isinstance(x, string_base_type) or NOT_BASE64_BINARY_PATTERN.match(x) is None:
        return False
    try:
        base64.standard_b64decode(x)
    except (ValueError, TypeError):
        return False
    else:
        return True


def hex_binary_validator(x):
    return isinstance(x, string_base_type) and not len(x) % 2 and HEX_BINARY_PATTERN.match(x) is not None


def ncname_validator(x):
    return isinstance(x, string_base_type) and NCNAME_PATTERN.match(x) is not None


XSD_BUILTIN_TYPES = {
    'string': XsdBuiltin(
        lambda x: isinstance(x, string_base_type), value='  alpha\t'
    ),
    'decimal': XsdBuiltin(
        lambda x: isinstance(x, (int, float, decimal.Decimal)), value=decimal.Decimal('1.0')
    ),
    'double': XsdBuiltin(
        lambda x: isinstance(x, float), value=1.0
    ),
    'float': XsdBuiltin(
        lambda x: isinstance(x, float), value=1.0
    ),
    'date': XsdBuiltin(
        lambda x: isinstance(x, Date), value=Date.fromstring('2000-01-01')
    ),
    'dateTime': XsdBuiltin(
        lambda x: isinstance(x, DateTime), value=DateTime.fromstring('2000-01-01T12:00:00')
    ),
    'gDay': XsdBuiltin(
        lambda x: isinstance(x, GregorianDay), value=GregorianDay.fromstring('---31')
    ),
    'gMonth': XsdBuiltin(
        lambda x: isinstance(x, GregorianMonth), value=GregorianMonth.fromstring('--12')
    ),
    'gMonthDay': XsdBuiltin(
        lambda x: isinstance(x, GregorianMonthDay), value=GregorianMonthDay.fromstring('--12-01')
    ),
    'gYear': XsdBuiltin(
        lambda x: isinstance(x, GregorianYear), value=GregorianYear.fromstring('1999')
    ),
    'gYearMonth': XsdBuiltin(
        lambda x: isinstance(x, GregorianYearMonth), value=GregorianYearMonth.fromstring('1999-09')
    ),
    'time': XsdBuiltin(
        lambda x: isinstance(x, Time), value=Time.fromstring('09:26:54')
    ),
    'duration': XsdBuiltin(
        lambda x: isinstance(x, Duration), value=Duration.fromstring('P1MT1S')
    ),
    'dayTimeDuration': XsdBuiltin(
        lambda x: isinstance(x, DayTimeDuration), value=DayTimeDuration.fromstring('P1DT1S')
    ),
    'yearMonthDuration': XsdBuiltin(
        lambda x: isinstance(x, YearMonthDuration), value=YearMonthDuration.fromstring('P1Y1M')
    ),
    'QName': XsdBuiltin(
        lambda x: isinstance(x, string_base_type) and QNAME_PATTERN.match(x) is not None, value='xs:element'
    ),
    'NOTATION': XsdBuiltin(
        lambda x: isinstance(x, string_base_type), value='alpha'
    ),
    'anyURI': XsdBuiltin(
        lambda x: isinstance(x, string_base_type), value='https://example.com'
    ),
    'normalizedString': XsdBuiltin(
        lambda x: isinstance(x, string_base_type) and '\t' not in x and '\r' not in x, value=' alpha  ',
    ),
    'token': XsdBuiltin(
        lambda x: isinstance(x, string_base_type) and WHITESPACES_PATTERN.match(x) is None, value='a token'
    ),
    'language': XsdBuiltin(
        lambda x: isinstance(x, string_base_type) and LANGUAGE_CODE_PATTERN.match(x) is not None, value='en-US'
    ),
    'Name': XsdBuiltin(
        lambda x: isinstance(x, string_base_type) and NAME_PATTERN.match(x) is not None, value='_a.name::'
    ),
    'NCName': XsdBuiltin(
        ncname_validator, value='nc-name'
    ),
    'ID': XsdBuiltin(
        ncname_validator, value='id1'
    ),
    'IDREF': XsdBuiltin(
        ncname_validator, value='id_ref1'
    ),
    'ENTITY': XsdBuiltin(
        ncname_validator, value='entity1'
    ),
    'NMTOKEN': XsdBuiltin(
        lambda x: isinstance(x, string_base_type) and NMTOKEN_PATTERN.match(x) is not None, value='a_token'
    ),
    'base64Binary': XsdBuiltin(
        base64_binary_validator, value=b'YWxwaGE='
    ),
    'hexBinary': XsdBuiltin(
        hex_binary_validator, value=b'31'
    ),
    'dateTimeStamp': XsdBuiltin(
        lambda x: isinstance(x, string_base_type), value='2000-01-01T12:00:00+01:00'
    ),
    'integer': XsdBuiltin(
        lambda x: isinstance(x, int), value=1
    ),
    'long': XsdBuiltin(
        lambda x: isinstance(x, int) and (-2**63 <= x < 2**63), value=1
    ),
    'int': XsdBuiltin(
        lambda x: isinstance(x, int) and (-2**31 <= x < 2**31), value=1
    ),
    'short': XsdBuiltin(
        lambda x: isinstance(x, int) and (-2**15 <= x < 2**15), value=1
    ),
    'byte': XsdBuiltin(
        lambda x: isinstance(x, int) and (-2**7 <= x < 2**7), value=1
    ),
    'positiveInteger': XsdBuiltin(
        lambda x: isinstance(x, int) and x > 0, value=1
    ),
    'negativeInteger': XsdBuiltin(
        lambda x: isinstance(x, int) and x < 0, value=-1
    ),
    'nonPositiveInteger': XsdBuiltin(
        lambda x: isinstance(x, int) and x <= 0, value=0
    ),
    'nonNegativeInteger': XsdBuiltin(
        lambda x: isinstance(x, int) and x >= 0, value=0
    ),
    'unsignedLong': XsdBuiltin(
        lambda x: isinstance(x, int) and (0 <= x < 2**64), value=1
    ),
    'unsignedInt': XsdBuiltin(
        lambda x: isinstance(x, int) and (0 <= x < 2**32), value=1
    ),
    'unsignedShort': XsdBuiltin(
        lambda x: isinstance(x, int) and (0 <= x < 2**16), value=1
    ),
    'unsignedByte': XsdBuiltin(
        lambda x: isinstance(x, int) and (0 <= x < 2**8), value=1
    ),
    'boolean': XsdBuiltin(
        lambda x: isinstance(x, bool), value=True
    ),
}
