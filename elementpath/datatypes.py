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
from calendar import isleap, leapdays, monthrange

from .compat import PY3, string_base_type, add_metaclass
from .exceptions import ElementPathTypeError, ElementPathValueError


def adjust_day(year, month, day):
    if month in {1, 3, 5, 7, 8, 10, 12}:
        return day
    elif month in {4, 6, 9, 11}:
        return min(day, 30)
    else:
        return min(day, 29) if isleap(year) else min(day, 28)


def months2days(year, month, months_delta):
    """
    Converts a delta of months to a delta of days, counting from the 1st day of the month,
    relative to the year and the month passed as arguments.

    :param year: the reference start year, a negative or zero value means a BCE year.
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

    if target_month >= month:
        m_days = sum(monthrange(target_year, m)[1] for m in range(month, target_month))
        return y_days + m_days if y_days >= 0 else y_days + m_days
    else:
        m_days = sum(monthrange(target_year, m)[1] for m in range(target_month, month))
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
    A class for representing XSD date/time objects. The reference xs:dateTime used is
    the datetime.datetime default 1900-01-01T00:00:00.

    :ivar dt: datetime.datetime instance.
    :ivar bce: if `True` the datetime instance represents a BCE date.
    :ivar y10k: years exceeding 9999 (current value of datetime.MAXYEAR).
    """
    version = '1.1'
    _pattern = re.compile(r'^$')
    _utc_timezone = Timezone(datetime.timedelta(0))

    def __init__(self, year=1900, month=1, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=None):
        if year == 0:
            raise ElementPathValueError('0 is an illegal value for year')
        elif year < -9999:
            self.bce = True
            self.y10k, year = -year - 9999, 9999
        elif year < 0:
            self.bce = True
            self.y10k, year = 0, -year
        elif year > 9999:
            self.bce = False
            self.y10k, year = year - 9999, 9999
        else:
            self.bce = False
            self.y10k = 0

        if hour == 24 and minute == second == 0:
            self.dt = datetime.datetime(year, month, day, 0, minute, second, microsecond, tzinfo)
        else:
            self.dt = datetime.datetime(year, month, day, hour, minute, second, microsecond, tzinfo)

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
        return -(self.dt.year + self.y10k) if self.bce else self.dt.year + self.y10k

    @property
    def iso_year(self):
        """The ISO string representation of the year field."""
        year = self.year
        if -9999 <= year < -1:
            return '{:05}'.format(year + 1 if self.version == '1.1' else year)
        elif year == -1:
            return '{:04}'.format(year + 1 if self.version == '1.1' else year)
        elif 0 <= year <= 9999:
            return '{:04}'.format(year)
        else:
            return str(year)

    @property
    def month(self):
        return self.dt.month

    @property
    def day(self):
        return self.dt.day

    @property
    def hour(self):
        return self.dt.hour

    @property
    def minute(self):
        return self.dt.minute

    @property
    def second(self):
        return self.dt.second

    @property
    def microsecond(self):
        return self.dt.microsecond

    @property
    def tzinfo(self):
        return self.dt.tzinfo

    @tzinfo.setter
    def tzinfo(self, tz):
        self.dt = self.dt.replace(tzinfo=tz)

    @classmethod
    def fromdatetime(cls, dt, bce=False, y10k=0):
        """
        Creates an XSD date/time instance from a datetime.datetime instance.

        :param dt: the datetime.datetime instance that stores the XSD Date/Time value.
        :param bce: if `True` the date value refers to a BCE (Before Common Era) date.
        :param y10k: years exceeding 9999 (current value of datetime.MAXYEAR), 0 for default.
        :return: an AbstractDateTime concrete subclass instance.
        """
        if not isinstance(dt, datetime.datetime):
            raise ElementPathTypeError('1st argument has an invalid type %r' % type(dt))
        elif not isinstance(bce, bool):
            raise ElementPathTypeError('2nd argument has an invalid type %r' % type(bce))
        elif not isinstance(y10k, int):
            raise ElementPathTypeError('3rd argument has an invalid type %r' % type(y10k))

        kwargs = {k: getattr(dt, k) for k in cls._pattern.groupindex.keys()}
        if 'year' in kwargs:
            if y10k:
                if dt.year != 9999:
                    raise ElementPathValueError("with y10k != 0 dt.year must be 9999: %r" % dt)
                kwargs['year'] += y10k if y10k > 0 else -y10k
            if bce:
                kwargs['year'] = - kwargs['year']
        return cls(**kwargs)

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
        if year is not None and year <= 0 and cls.version == '1.1':
            kwargs['year'] -= 1
        return cls(**kwargs)

    # Python can't compares offset-naive and offset-aware datetimes
    def _get_operands(self, other):
        if isinstance(other, (self.__class__, datetime.datetime)) or isinstance(self, other.__class__):
            dt = getattr(other, 'dt', other)
            if self.dt.tzinfo is dt.tzinfo:
                return self.dt, dt
            elif self.tzinfo is None:
                return self.dt.replace(tzinfo=self._utc_timezone), dt
            elif dt.tzinfo is None:
                return self.dt, dt.replace(tzinfo=self._utc_timezone)
            else:
                return self.dt, dt
        else:
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))

    def __eq__(self, other):
        return operator.eq(*self._get_operands(other)) and self.year == other.year


class OrderedDateTime(AbstractDateTime):

    @abstractmethod
    def __str__(self):
        pass

    @property
    def common_era_delta(self):
        """Property that returns the datetime.timedelta from 0001-01-01T00:00:00 CE."""
        dt, year = self.dt, self.year
        tzinfo = None if dt.tzinfo is None else self._utc_timezone
        if self.bce:
            days = -months2days(year + 1, dt.month, -year * 12 - dt.month + 1)
            delta = (dt - datetime.datetime(dt.year, dt.month, day=1, tzinfo=tzinfo))
            return datetime.timedelta(days=days, seconds=delta.total_seconds())
        else:
            days = -months2days(year, dt.month, -(year - 1) * 12 - dt.month + 1)
            delta = (dt - datetime.datetime(dt.year, dt.month, day=1, tzinfo=tzinfo))
            return datetime.timedelta(days=days, seconds=delta.total_seconds())

    def _date_operator(self, op, other):
        if isinstance(other, self.__class__):
            dt1, dt2 = self._get_operands(other)
            if not self.bce and not other.bce and self.y10k == 0 and other.y10k == 0:
                return DayTimeDuration.fromtimedelta(dt1 - dt2)
            return DayTimeDuration.fromtimedelta(self.common_era_delta - other.common_era_delta)

        elif isinstance(other, (DayTimeDuration, datetime.timedelta)):
            delta = other.get_timedelta() if isinstance(other, DayTimeDuration) else other
            try:
                dt = op(self.dt, delta)
            except OverflowError:
                seconds = delta.total_seconds()
                if self.bce ^ (seconds > 0):
                    raise
                dt_seconds = abs((self.dt - datetime.datetime(1, 1, 1)).total_seconds() - seconds)
                dt = datetime.datetime(1, 1, 1) + datetime.timedelta(seconds=dt_seconds)
                bce = not self.bce
            else:
                bce = self.bce

            if 'hour' not in self._pattern.groupindex.keys():
                dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)

        elif isinstance(other, YearMonthDuration):
            month = op(self.dt.month - 1, other.months) % 12 + 1
            year = op(self.dt.year, ((self.dt.month - 1) + other.months) // 12)
            if year > 0:
                bce = self.bce
            else:
                bce = not self.bce
                year = abs(year) + 1
            dt = self.dt.replace(year=year, month=month, day=adjust_day(year, month, self.dt.day))
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


class DateTime(OrderedDateTime):
    """Class for representing xs:dateTime data."""
    _pattern = re.compile(r'^(?P<year>(?:-)?\d*\d{4})-(?P<month>\d{2})-(?P<day>\d{2})'
                          r'(T(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})(?:\.(?P<microsecond>\d+))?)?'
                          r'(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$')

    def __init__(self, year, month, day, hour=0, minute=0, second=0, microsecond=0, tzinfo=None):
        super(DateTime, self).__init__(year, month, day, hour, minute, second, microsecond, tzinfo)

    def __str__(self):
        if self.microsecond:
            return '{}-{:02}-{:02}T{:02}:{:02}:{:02}.{:06}{}'.format(
                self.iso_year, self.month, self.day, self.hour, self.minute,
                self.second, self.microsecond, str(self.tzinfo or '')
            )
        return '{}-{:02}-{:02}T{:02}:{:02}:{:02}{}'.format(
            self.iso_year, self.month, self.day, self.hour, self.minute, self.second, str(self.tzinfo or '')
        )


class DateTime10(DateTime):
    version = '1.0'


class Date(OrderedDateTime):
    """Class for representing xs:date data."""
    _pattern = re.compile(r'^(?P<year>(?:-)?\d*\d{4})-(?P<month>\d{2})-(?P<day>\d{2})'
                          r'(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$')

    def __init__(self, year, month, day, tzinfo=None):
        super(Date, self).__init__(year, month, day, tzinfo=tzinfo)

    def __str__(self):
        return '{}-{:02}-{:02}{}'.format(self.iso_year, self.month, self.day, str(self.tzinfo or ''))


class Date10(Date):
    version = '1.0'


class GregorianDay(AbstractDateTime):
    """Class for representing xs:gDay data."""
    _pattern = re.compile(r'^---(?P<day>\d{2})(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$')

    def __init__(self, day, tzinfo=None):
        super(GregorianDay, self).__init__(day=day, tzinfo=tzinfo)

    def __str__(self):
        return '---{:02}{}'.format(self.day, str(self.tzinfo or ''))


class GregorianMonth(AbstractDateTime):
    """Class for representing xs:gMonth data."""
    _pattern = re.compile(r'^--(?P<month>\d{2})(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$')

    def __init__(self, month, tzinfo=None):
        super(GregorianMonth, self).__init__(month=month, tzinfo=tzinfo)

    def __str__(self):
        return '--{:02}{}'.format(self.month, str(self.tzinfo or ''))


class GregorianMonthDay(AbstractDateTime):
    """Class for representing xs:gMonthDay data."""
    _pattern = re.compile(r'^--(?P<month>\d{2})-(?P<day>\d{2})'
                          r'(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$')

    def __init__(self, month, day, tzinfo=None):
        super(GregorianMonthDay, self).__init__(month=month, day=day, tzinfo=tzinfo)

    def __str__(self):
        return '--{:02}-{:02}{}'.format(self.month, self.day, str(self.tzinfo or ''))


class GregorianYear(AbstractDateTime):
    """Class for representing xs:gYear data."""
    _pattern = re.compile(r'^(?P<year>(?:-)?\d*\d{4})'
                          r'(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$')

    def __init__(self, year, tzinfo=None):
        super(GregorianYear, self).__init__(year, tzinfo=tzinfo)

    def __str__(self):
        return '{}{}'.format(self.iso_year, str(self.tzinfo or ''))


class GregorianYear10(GregorianYear):
    version = '1.0'


class GregorianYearMonth(AbstractDateTime):
    """Class for representing xs:gYearMonth data."""
    _pattern = re.compile(r'^(?P<year>(?:-)?\d*\d{4})-(?P<month>\d{2})'
                          r'(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$')

    def __init__(self, year, month, tzinfo=None):
        super(GregorianYearMonth, self).__init__(year, month, tzinfo=tzinfo)

    def __str__(self):
        return '{}-{:02}{}'.format(self.iso_year, self.month, str(self.tzinfo or ''))


class GregorianYearMonth10(GregorianYearMonth):
    version = '1.0'


class Time(AbstractDateTime):
    """Class for representing xs:time data."""
    _pattern = re.compile(r'^(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})(?:\.(?P<microsecond>\d+))?'
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
            dt = self.dt + other.get_timedelta()
        elif isinstance(other, datetime.timedelta):
            dt = self.dt + other
        else:
            raise ElementPathTypeError("wrong type %r for operand %r." % (type(other), other))
        return Time(dt.hour, dt.minute, dt.second, dt.microsecond, dt.tzinfo)

    def __sub__(self, other):
        if isinstance(other, self.__class__):
            delta = operator.sub(*self._get_operands(other))
            return DayTimeDuration.fromtimedelta(delta)
        elif isinstance(other, DayTimeDuration):
            dt = self.dt - other.get_timedelta()
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
        r'^(-)?P(?=(?:\d|T))(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?(?:T(?=\d)(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$'
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
