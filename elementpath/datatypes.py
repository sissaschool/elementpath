#
# Copyright (c), 2018-2020, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""
XSD atomic datatypes. Includes a class for UntypedAtomic data and classes
for other XSD built-in primitive types. This module raises only built-in
exceptions in order to be reusable in other packages.
"""
from abc import ABCMeta, abstractmethod
import operator
import re
import math
import codecs
import datetime
import base64
from calendar import isleap, leapdays
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

from .namespaces import XSD_NAMESPACE

###
# Data validation helpers

NORMALIZE_PATTERN = re.compile(r'[^\S\xa0]')
WHITESPACES_PATTERN = re.compile(r'[^\S\xa0]+')  # include ASCII 160 (non-breaking space)
NCNAME_PATTERN = re.compile(r'^[^\d\W][\w.\-\u00B7\u0300-\u036F\u203F\u2040]*$')
QNAME_PATTERN = re.compile(
    r'^(?:(?P<prefix>[^\d\W][\w\-.\u00B7\u0300-\u036F\u0387\u06DD\u06DE\u203F\u2040]*):)?'
    r'(?P<local>[^\d\W][\w\-.\u00B7\u0300-\u036F\u0387\u06DD\u06DE\u203F\u2040]*)$',
)
WRONG_ESCAPE_PATTERN = re.compile(r'%(?![a-fA-F\d]{2})')


def collapse_white_spaces(s):
    return WHITESPACES_PATTERN.sub(' ', s).strip(' ')


def is_idrefs(value):
    return isinstance(value, str) and \
        all(NCNAME_PATTERN.match(x) is not None for x in value.split())


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


def round_number(value):
    if math.isnan(value) or math.isinf(value):
        return value

    number = Decimal(value)
    if number > 0:
        return type(value)(number.quantize(Decimal('1'), rounding='ROUND_HALF_UP'))
    else:
        return type(value)(number.quantize(Decimal('1'), rounding='ROUND_HALF_DOWN'))


def normalized_seconds(seconds):
    # Decimal.normalize() does not remove exp every time: eg. Decimal('1E+1')
    return '{:.6f}'.format(seconds).rstrip('0').rstrip('.')


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
            raise TypeError("offset must be a datetime.timedelta")
        if offset < self._minoffset or offset > self._maxoffset:
            raise ValueError("offset must be between -14:00 and +14:00")
        self.offset = offset

    @classmethod
    def fromstring(cls, text):
        try:
            hours, minutes = text.strip().split(':')
            if hours.startswith('-'):
                return cls(datetime.timedelta(hours=int(hours), minutes=-int(minutes)))
            else:
                return cls(datetime.timedelta(hours=int(hours), minutes=int(minutes)))
        except AttributeError:
            raise TypeError("argument is not a string")
        except ValueError:
            if text.strip() == 'Z':
                return cls(datetime.timedelta(0))
            raise ValueError("%r: not an XSD timezone formatted string" % text) from None

    @classmethod
    def fromduration(cls, duration):
        if duration.seconds % 1 != 0:
            raise ValueError("{!r} isn't an integral number of minutes".format(duration))
        return cls(datetime.timedelta(seconds=int(duration.seconds)))

    def __getinitargs__(self):
        return self.offset,

    def __hash__(self):
        return hash(self.offset)

    def __eq__(self, other):
        return isinstance(other, Timezone) and self.offset == other.offset

    def __ne__(self, other):
        return not isinstance(other, Timezone) or self.offset != other.offset

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.offset)

    def __str__(self):
        return self.tzname(None)

    def utcoffset(self, dt):
        if not isinstance(dt, datetime.datetime) and dt is not None:
            raise TypeError("utcoffset() argument must be a "
                            "datetime.datetime instance or None")
        return self.offset

    def tzname(self, dt):
        if not isinstance(dt, datetime.datetime) and dt is not None:
            raise TypeError("tzname() argument must be a "
                            "datetime.datetime instance or None")

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
            raise TypeError("dst() argument must be a "
                            "datetime.datetime instance or None")

    def fromutc(self, dt):
        if isinstance(dt, datetime.datetime):
            return dt + self.offset
        elif dt is not None:
            raise TypeError("fromutc() argument must be a "
                            "datetime.datetime instance or None")


###
# Classes for XSD built-in atomic types. All defined classes use a
# metaclass that adds some common methods and registers each class
# into a dictionary. Some classes of XSD primitive types are defined
# as proxies of basic Python datatypes.

xsd10_atomic_types = {}
"""Dictionary of builtin XSD 1.0 atomic types."""

xsd11_atomic_types = {}
"""Dictionary of builtin XSD 1.1 atomic types."""


class AtomicTypeABCMeta(ABCMeta):
    """
    Metaclass for creating XSD atomic types. The created classes
    are decorated with missing attributes and methods. When a name
    attribute is provided the class is registered into a global map
    of XSD atomic types and also the expanded name is added.
    """
    name = None

    def __new__(mcs, class_name, bases, dict_):
        try:
            name = dict_['name']
        except KeyError:
            name = dict_['name'] = None  # do not inherit name

        if isinstance(name, str):
            expanded_name = dict_['expanded_name'] = '{%s}%s' % (XSD_NAMESPACE, name)
        elif name is None:
            expanded_name = dict_['expanded_name'] = None
        else:
            raise TypeError("attribute 'name' must be a string or None")

        cls = super(AtomicTypeABCMeta, mcs).__new__(mcs, class_name, bases, dict_)

        # Add missing attributes and methods
        if not hasattr(cls, 'version'):
            cls.version = '1.0'
        if not hasattr(cls, 'pattern'):
            cls.pattern = re.compile(r'^$')
        if not hasattr(cls, 'validate'):
            cls.validate = mcs.validate

        cls.is_valid = classmethod(mcs.is_valid)
        cls.invalid_type = classmethod(mcs.invalid_type)
        cls.invalid_value = classmethod(mcs.invalid_value)

        # Register class if it's not already registered
        if not name:
            pass
        elif cls.version == '1.0':
            xsd10_atomic_types[name] = xsd10_atomic_types[expanded_name] = cls
        else:
            xsd11_atomic_types[name] = xsd11_atomic_types[expanded_name] = cls

        return cls

    def validate(cls, value):
        if isinstance(value, cls):
            return
        elif not isinstance(value, str):
            raise cls.invalid_type(value)
        elif cls.pattern.match(value) is None:
            raise cls.invalid_value(value)

    def is_valid(cls, value):
        try:
            cls.validate(value)
        except (TypeError, ValueError):
            return False
        else:
            return True

    def invalid_type(cls, value):
        if cls.name:
            return TypeError('invalid type {!r} for xs:{}'.format(type(value), cls.name))
        return TypeError('invalid type {!r} for {!r}'.format(type(value), cls))

    def invalid_value(cls, value):
        if cls.name:
            return ValueError('invalid value {!r} for xs:{}'.format(value, cls.name))
        return ValueError('invalid value {!r} for {!r}'.format(value, cls))


class AnyAtomicType(metaclass=AtomicTypeABCMeta):
    name = 'anyAtomicType'


class AbstractDateTime(metaclass=AtomicTypeABCMeta):
    """
    A class for representing XSD date/time objects. It uses and internal datetime.datetime
    attribute and an integer attribute for processing BCE years or for years after 9999 CE.
    """
    _utc_timezone = Timezone(datetime.timedelta(0))
    _year = None

    def __init__(self, year=2000, month=1, day=1, hour=0, minute=0,
                 second=0, microsecond=0, tzinfo=None):
        if hour == 24 and minute == second == microsecond == 0:
            delta = datetime.timedelta(days=1)
            hour = 0
        else:
            delta = 0

        if 1 <= year <= 9999:
            self._dt = datetime.datetime(year, month, day, hour, minute,
                                         second, microsecond, tzinfo)
        elif year == 0:
            raise ValueError('0 is an illegal value for year')
        elif not isinstance(year, int):
            raise TypeError("invalid type %r for year" % type(year))
        elif abs(year) > 2 ** 31:
            raise OverflowError("year overflow")
        else:
            self._year = year
            if isleap(year + bool(self.version != '1.0')):
                self._dt = datetime.datetime(4, month, day, hour, minute,
                                             second, microsecond, tzinfo)
            else:
                self._dt = datetime.datetime(6, month, day, hour, minute,
                                             second, microsecond, tzinfo)

        if delta:
            self._dt += delta

    def __repr__(self):
        fields = self.pattern.groupindex.keys()
        arg_string = ', '.join(
            str(getattr(self, k))
            for k in ['year', 'month', 'day', 'hour', 'minute'] if k in fields
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
        raise NotImplementedError()

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
            return '-0001' if self.version == '1.0' else '0000'
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
        if not isinstance(datetime_string, str):
            msg = '1st argument has an invalid type {!r}'
            raise TypeError(msg.format(type(datetime_string)))
        elif tzinfo and not isinstance(tzinfo, Timezone):
            msg = '2nd argument has an invalid type {!r}'
            raise TypeError(msg.format(type(tzinfo)))

        match = cls.pattern.match(datetime_string.strip())
        if match is None:
            msg = 'Invalid datetime string {!r} for {!r}'
            raise ValueError(msg.format(datetime_string, cls))

        kwargs = {k: int(v) if k != 'tzinfo' else Timezone.fromstring(v)
                  for k, v in match.groupdict().items() if v is not None}

        if 'tzinfo' not in kwargs and tzinfo is not None:
            kwargs['tzinfo'] = tzinfo

        if 'microsecond' in kwargs:
            pow10 = 6 - len(match.groupdict()['microsecond'])
            if pow10 == 0:
                pass
            elif pow10 > 0:
                kwargs['microsecond'] = kwargs['microsecond'] * 10**pow10
            elif kwargs['microsecond'] > 999999:
                msg = "Invalid value {} for microsecond"
                raise OverflowError(msg.format(kwargs['microsecond']))
            else:
                kwargs['microsecond'] = int(match.groupdict()['microsecond'][:6])

        if 'year' in kwargs:
            year_digits = match.groupdict()['year'].lstrip('-')
            if year_digits.startswith('0') and len(year_digits) > 4:
                msg = "Invalid datetime string {!r} for {!r} (when year " \
                      "exceeds 4 digits leading zeroes are not allowed)"
                raise ValueError(msg.format(datetime_string, cls))

            if cls.version == '1.0':
                if kwargs['year'] == 0:
                    raise ValueError("year '0000' is an illegal value for XSD 1.0")
            elif kwargs['year'] <= 0:
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
            raise TypeError('1st argument has an invalid type %r' % type(dt))
        elif year is not None and not isinstance(year, int):
            raise TypeError('2nd argument has an invalid type %r' % type(year))

        kwargs = {k: getattr(dt, k) for k in cls.pattern.groupindex.keys() if hasattr(dt, k)}
        if year is not None:
            kwargs['year'] = year
        return cls(**kwargs)

    # Python can't compares offset-naive and offset-aware datetimes
    def _get_operands(self, other):
        if isinstance(other, (self.__class__, datetime.datetime)) or \
                isinstance(self, other.__class__):
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
            raise TypeError("wrong type %r for operand %r" % (type(other), other))

    def __hash__(self):
        return hash((self._dt, self._year))

    def __eq__(self, other):
        try:
            return operator.eq(*self._get_operands(other)) and self.year == other.year
        except TypeError:
            return False

    def __ne__(self, other):
        try:
            return operator.ne(*self._get_operands(other)) or self.year != other.year
        except TypeError:
            return True


class OrderedDateTime(AbstractDateTime):

    @abstractmethod
    def __str__(self):
        raise NotImplementedError()

    @classmethod
    def fromdelta(cls, delta, adjust_timezone=False):
        """
        Creates an XSD dateTime/date instance from a datetime.timedelta related to
        0001-01-01T00:00:00 CE. In case of a date the time part is not counted.

        :param delta: a datetime.timedelta instance.
        :param adjust_timezone: if `True` adjusts the timezone of Date objects \
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

                td = datetime.timedelta(days=days, seconds=delta.seconds,
                                        microseconds=delta.microseconds)
                dt = datetime.datetime(4 if isleap(year) else 6, 1, 1) + td

            elif days >= -366:
                year = -1
                td = datetime.timedelta(days=days, seconds=delta.seconds,
                                        microseconds=delta.microseconds)
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

                td = datetime.timedelta(days=-days, seconds=delta.seconds,
                                        microseconds=delta.microseconds)
                if not td:
                    dt = datetime.datetime(4 if isleap(year + 1) else 6, 1, 1)
                    year += 1
                else:
                    dt = datetime.datetime(5 if isleap(year + 1) else 7, 1, 1) + td
        else:
            year = dt.year

        if issubclass(cls, Date10):
            if adjust_timezone and (dt.hour or dt.minute):
                assert dt.tzinfo is None
                hour, minute = dt.hour, dt.minute

                if hour < 14 or hour == 14 and minute == 0:
                    tz = Timezone(datetime.timedelta(hours=-hour, minutes=-minute))
                    dt = dt.replace(tzinfo=tz)
                else:
                    tz = Timezone(datetime.timedelta(hours=-dt.hour + 24, minutes=-minute))
                    dt = dt.replace(tzinfo=tz)
                    dt += datetime.timedelta(days=1)

            return cls(year, dt.month, dt.day, tzinfo=dt.tzinfo)
        return cls(year, dt.month, dt.day, dt.hour, dt.minute,
                   dt.second, dt.microsecond, dt.tzinfo)

    def todelta(self):
        """Returns the datetime.timedelta from 0001-01-01T00:00:00 CE."""
        if self._year is None:
            return operator.sub(*self._get_operands(datetime.datetime(1, 1, 1)))

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

        elif isinstance(other, datetime.timedelta):
            delta = op(self.todelta(), other)
            return type(self).fromdelta(delta, adjust_timezone=True)

        elif isinstance(other, DayTimeDuration):
            delta = op(self.todelta(), other.get_timedelta())
            if self._dt.tzinfo is None:
                return type(self).fromdelta(delta)

            value = type(self).fromdelta(delta + self._dt.tzinfo.offset)
            value.tzinfo = self._dt.tzinfo
            return value

        elif isinstance(other, YearMonthDuration):
            month = op(self._dt.month - 1, other.months) % 12 + 1
            year = self.year + op(self._dt.month - 1, other.months) // 12
            day = adjust_day(year, month, self._dt.day)

            if year > 0:
                dt = self._dt.replace(year=year, month=month, day=day)
            elif isleap(year):
                dt = self._dt.replace(year=4, month=month, day=day)
            else:
                dt = self._dt.replace(year=6, month=month, day=day)

            kwargs = {k: getattr(dt, k) for k in self.pattern.groupindex.keys()}
            if year <= 0:
                kwargs['year'] = year
            return type(self)(**kwargs)

        else:
            raise TypeError("wrong type %r for operand %r" % (type(other), other))

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
            raise TypeError("wrong type %r for operand %r" % (type(other), other))
        return self._date_operator(operator.add, other)

    def __sub__(self, other):
        return self._date_operator(operator.sub, other)


class DateTime10(OrderedDateTime):
    """XSD 1.0 xs:dateTime builtin type"""
    name = 'dateTime'
    pattern = re.compile(
        r'^(?P<year>(?:-)?[0-9]*[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})'
        r'(T(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):'
        r'(?P<second>[0-9]{2})(?:\.(?P<microsecond>[0-9]+))?)'
        r'(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$')

    def __init__(self, year, month, day, hour=0, minute=0, second=0, microsecond=0, tzinfo=None):
        super(DateTime10, self).__init__(
            year, month, day, hour, minute, second, microsecond, tzinfo
        )

    def __str__(self):
        if self.microsecond:
            return '{}-{:02}-{:02}T{:02}:{:02}:{:02}.{}{}'.format(
                self.iso_year, self.month, self.day, self.hour, self.minute, self.second,
                '{:06}'.format(self.microsecond).rstrip('0'), str(self.tzinfo or '')
            ).rstrip('0')
        return '{}-{:02}-{:02}T{:02}:{:02}:{:02}{}'.format(
            self.iso_year, self.month, self.day, self.hour,
            self.minute, self.second, str(self.tzinfo or '')
        )


class DateTime(DateTime10):
    """XSD 1.1 xs:dateTime builtin type"""
    name = 'dateTime'
    version = '1.1'


class DateTimeStamp(DateTime):
    """XSD 1.1 xs:dateTimeStamp builtin type"""
    name = 'dateTimeStamp'
    pattern = re.compile(
        r'^(?P<year>(?:-)?[0-9]*[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})'
        r'(T(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):'
        r'(?P<second>[0-9]{2})(?:\.(?P<microsecond>[0-9]+))?)'
        r'(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))$')


class Date10(OrderedDateTime):
    """XSD 1.0 xs:date builtin type"""
    name = 'date'
    pattern = re.compile(r'^(?P<year>(?:-)?[0-9]*[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})'
                         r'(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$')

    def __init__(self, year, month, day, tzinfo=None):
        super(Date10, self).__init__(year, month, day, tzinfo=tzinfo)

    def __str__(self):
        return '{}-{:02}-{:02}{}'.format(
            self.iso_year, self.month, self.day, str(self.tzinfo or '')
        )


class Date(Date10):
    """XSD 1.1 xs:date builtin type"""
    name = 'date'
    version = '1.1'


class GregorianDay(OrderedDateTime):
    """XSD xs:gDay builtin type"""
    name = 'gDay'
    pattern = re.compile(r'^---(?P<day>[0-9]{2})'
                         r'(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$')

    def __init__(self, day, tzinfo=None):
        super(GregorianDay, self).__init__(day=day, tzinfo=tzinfo)

    def __str__(self):
        return '---{:02}{}'.format(self.day, str(self.tzinfo or ''))


class GregorianMonth(OrderedDateTime):
    """XSD xs:gMonth builtin type"""
    name = 'gMonth'
    pattern = re.compile(r'^--(?P<month>[0-9]{2})'
                         r'(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$')

    def __init__(self, month, tzinfo=None):
        super(GregorianMonth, self).__init__(month=month, tzinfo=tzinfo)

    def __str__(self):
        return '--{:02}{}'.format(self.month, str(self.tzinfo or ''))


class GregorianMonthDay(OrderedDateTime):
    """XSD xs:gMonthDay builtin type"""
    name = 'gMonthDay'
    pattern = re.compile(r'^--(?P<month>[0-9]{2})-(?P<day>[0-9]{2})'
                         r'(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$')

    def __init__(self, month, day, tzinfo=None):
        super(GregorianMonthDay, self).__init__(month=month, day=day, tzinfo=tzinfo)

    def __str__(self):
        return '--{:02}-{:02}{}'.format(self.month, self.day, str(self.tzinfo or ''))


class GregorianYear10(OrderedDateTime):
    """XSD 1.0 xs:gYear builtin type"""
    name = 'gYear'
    pattern = re.compile(r'^(?P<year>(?:-)?[0-9]*[0-9]{4})'
                         r'(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$')

    def __init__(self, year, tzinfo=None):
        super(GregorianYear10, self).__init__(year, tzinfo=tzinfo)

    def __str__(self):
        return '{}{}'.format(self.iso_year, str(self.tzinfo or ''))


class GregorianYear(GregorianYear10):
    """XSD 1.1 xs:gYear builtin type"""
    name = 'gYear'
    version = '1.1'


class GregorianYearMonth10(OrderedDateTime):
    """XSD 1.0 xs:gYearMonth builtin type"""
    name = 'gYearMonth'
    pattern = re.compile(r'^(?P<year>(?:-)?[0-9]*[0-9]{4})-(?P<month>[0-9]{2})'
                         r'(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$')

    def __init__(self, year, month, tzinfo=None):
        super(GregorianYearMonth10, self).__init__(year, month, tzinfo=tzinfo)

    def __str__(self):
        return '{}-{:02}{}'.format(self.iso_year, self.month, str(self.tzinfo or ''))


class GregorianYearMonth(GregorianYearMonth10):
    """XSD 1.1 xs:gYearMonth builtin type"""
    name = 'gYearMonth'
    version = '1.1'


class Time(AbstractDateTime):
    """XSD xs:time builtin type"""
    name = 'time'
    pattern = re.compile(
        r'^(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):'
        r'(?P<second>[0-9]{2})(?:\.(?P<microsecond>[0-9]+))?'
        r'(?P<tzinfo>Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))?$')

    def __init__(self, hour=0, minute=0, second=0, microsecond=0, tzinfo=None):
        if hour == 24 and minute == second == microsecond == 0:
            hour = 0
        super(Time, self).__init__(
            hour=hour, minute=minute, second=second, microsecond=microsecond, tzinfo=tzinfo
        )

    def __str__(self):
        if self.microsecond:
            return '{:02}:{:02}:{:02}.{}{}'.format(
                self.hour, self.minute, self.second,
                '{:06}'.format(self.microsecond).rstrip('0'),
                str(self.tzinfo or '')
            )
        return '{:02}:{:02}:{:02}{}'.format(
            self.hour, self.minute, self.second, str(self.tzinfo or '')
        )

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
            raise TypeError("wrong type %r for operand %r" % (type(other), other))
        return Time(dt.hour, dt.minute, dt.second, dt.microsecond, dt.tzinfo)

    def __sub__(self, other):
        if isinstance(other, self.__class__):
            delta = operator.sub(*self._get_operands(other))
            return DayTimeDuration.fromtimedelta(delta)
        elif isinstance(other, DayTimeDuration):
            dt = self._dt - other.get_timedelta()
            return Time(dt.hour, dt.minute, dt.second, dt.microsecond, dt.tzinfo)
        elif isinstance(other, datetime.timedelta):
            dt = self._dt - other
            return Time(dt.hour, dt.minute, dt.second, dt.microsecond, dt.tzinfo)
        else:
            raise TypeError("wrong type %r for operand %r" % (type(other), other))


class Duration(AnyAtomicType):
    """
    Base class for the XSD duration types.

    :param months: an integer value that represents years and months.
    :param seconds: a Decimal instance that represents days, hours, minutes, \
    seconds and fractions of seconds.
    """
    name = 'duration'
    pattern = re.compile(
        r'^(-)?P(?=(?:[0-9]|T))(?:([0-9]+)Y)?(?:([0-9]+)M)?(?:([0-9]+)D)?'
        r'(?:T(?=[0-9])(?:([0-9]+)H)?(?:([0-9]+)M)?(?:([0-9]+(?:\.[0-9]+)?)S)?)?$'
    )

    def __init__(self, months=0, seconds=0):
        if seconds < 0 < months or months < 0 < seconds:
            raise ValueError('signs differ: (months=%d, seconds=%d)' % (months, seconds))
        elif abs(months) > 2 ** 31:
            raise OverflowError("months duration overflow")
        elif abs(seconds) > 2 ** 63:
            raise OverflowError("seconds duration overflow")

        self.months = months
        try:
            self.seconds = Decimal(seconds).quantize(Decimal('1.000000'))
        except InvalidOperation:
            self.seconds = Decimal(seconds)

    def __repr__(self):
        return '{}(months={!r}, seconds={})'.format(
            self.__class__.__name__, self.months, normalized_seconds(self.seconds)
        )

    def __str__(self):
        m = abs(self.months)
        years, months = m // 12, m % 12
        s = self.seconds.copy_abs()
        days = int(s // 86400)
        hours = int(s // 3600 % 24)
        minutes = int(s // 60 % 60)
        seconds = s % 60

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
                value += '%sS' % normalized_seconds(seconds)

        elif value[-1] == 'P':
            value += 'T0S'
        return value

    @classmethod
    def fromstring(cls, text):
        """
        Creates a Duration instance from a formatted XSD duration string.

        :param text: an ISO 8601 representation without week fragment and an optional decimal part \
        only for seconds fragment.
        """
        if not isinstance(text, str):
            msg = 'argument has an invalid type {!r}'
            raise TypeError(msg.format(type(text)))

        match = cls.pattern.match(text.strip())
        if match is None:
            raise ValueError('%r is not an xs:duration value' % text)

        sign, years, months, days, hours, minutes, seconds = match.groups()
        seconds = Decimal(seconds or 0)
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
                raise ValueError('months must be 0 for %r' % cls.__name__)
            return cls(seconds=seconds)
        elif cls is YearMonthDuration:
            if seconds:
                raise ValueError('seconds must be 0 for %r' % cls.__name__)
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
            raise TypeError("wrong type %r for operand %r" % (type(other), other))

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

    def __hash__(self):
        return hash((self.months, self.seconds))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.months == other.months and self.seconds == other.seconds
        elif isinstance(other, UntypedAtomic):
            return self.__eq__(self.fromstring(other.value))
        else:
            return other == (self.months, self.seconds)

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return self.months != other.months or self.seconds != other.seconds
        elif isinstance(other, UntypedAtomic):
            return self.__ne__(self.fromstring(other.value))
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

    name = 'yearMonthDuration'

    def __init__(self, months=0):
        super(YearMonthDuration, self).__init__(months, 0)

    def __repr__(self):
        return '%s(months=%r)' % (self.__class__.__name__, self.months)

    def __str__(self):
        m = abs(self.months)
        years, months = m // 12, m % 12

        if not years:
            return '-P%dM' % months if self.months < 0 else 'P%dM' % months
        elif not months:
            return '-P%dY' % years if self.months < 0 else 'P%dY' % years
        elif self.months < 0:
            return '-P%dY%dM' % (years, months)
        else:
            return 'P%dY%dM' % (years, months)

    def __add__(self, other):
        if isinstance(other, self.__class__):
            return YearMonthDuration(months=self.months + other.months)
        elif isinstance(other, (DateTime10, Date10)):
            return other + self
        raise TypeError("cannot add %r to %r" % (type(other), type(self)))

    def __sub__(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError("cannot subtract %r from %r" % (type(other), type(self)))
        return YearMonthDuration(months=self.months - other.months)

    def __mul__(self, other):
        if not isinstance(other, (float, int, Decimal)):
            raise TypeError("cannot multiply a %r by %r" % (type(self), type(other)))
        return YearMonthDuration(months=int(round_number(self.months * other)))

    def __truediv__(self, other):
        if isinstance(other, self.__class__):
            return self.months / other.months
        elif isinstance(other, (float, int, Decimal)):
            return YearMonthDuration(months=int(round_number(self.months / other)))
        else:
            raise TypeError("cannot divide a %r by %r" % (type(self), type(other)))


class DayTimeDuration(Duration):

    name = 'dayTimeDuration'

    def __init__(self, seconds=0):
        super(DayTimeDuration, self).__init__(0, seconds)

    @classmethod
    def fromtimedelta(cls, td):
        return cls(seconds=Decimal(
            '{}.{:06}'.format(td.days * 86400 + td.seconds, td.microseconds)
        ))

    def get_timedelta(self):
        return datetime.timedelta(
            seconds=int(self.seconds), microseconds=int(self.seconds % 1 * 1000000)
        )

    def __repr__(self):
        return '%s(seconds=%s)' % (self.__class__.__name__, normalized_seconds(self.seconds))

    def __add__(self, other):
        if isinstance(other, (Time, Date10)):
            return other + self
        elif not isinstance(other, self.__class__):
            raise TypeError("cannot add %r to %r" % (type(other), type(self)))
        return DayTimeDuration(self.seconds + other.seconds)

    def __sub__(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError("cannot subtract %r from %r" % (type(other), type(self)))
        return DayTimeDuration(seconds=self.seconds - other.seconds)

    def __mul__(self, other):
        if not isinstance(other, (float, int, Decimal)):
            raise TypeError("cannot multiply a %r by %r" % (type(self), type(other)))
        elif math.isnan(other):
            raise ValueError("cannot multiply a %r by NaN" % type(self))

        if isinstance(other, (int, Decimal)):
            seconds = self.seconds * other
        else:
            seconds = self.seconds * Decimal.from_float(other)
        if math.isinf(seconds):
            raise OverflowError("overflow when multiplying a %r by a number" % type(self))
        return DayTimeDuration(seconds)

    def __truediv__(self, other):
        if isinstance(other, self.__class__):
            return self.seconds / other.seconds
        elif not isinstance(other, (float, int, Decimal)):
            raise TypeError("cannot divide a %r by %r" % (type(self), type(other)))
        elif math.isnan(other):
            raise ValueError("cannot divide a %r by NaN" % type(self))

        if isinstance(other, (int, Decimal)):
            seconds = self.seconds / other
        else:
            seconds = self.seconds / Decimal.from_float(other)
        if math.isinf(seconds):
            raise OverflowError("overflow when dividing a %r by a number" % type(self))
        return DayTimeDuration(seconds)


class NormalizedString(str, metaclass=AtomicTypeABCMeta):
    name = 'normalizedString'
    pattern = re.compile('^[^\t\r]*$')

    def __new__(cls, obj):
        try:
            return super().__new__(cls, NORMALIZE_PATTERN.sub(' ', obj))
        except TypeError:
            return super().__new__(cls, obj)


class XsdToken(NormalizedString):
    name = 'token'
    pattern = re.compile(r'^[\S\xa0]*(?: [\S\xa0]+)*$')

    def __new__(cls, value):
        if not isinstance(value, str):
            value = str(value)
        else:
            value = collapse_white_spaces(value)

        match = cls.pattern.match(value)
        if match is None:
            raise ValueError('invalid value {!r} for xs:{}'.format(value, cls.name))
        return super(NormalizedString, cls).__new__(cls, value)


class Language(XsdToken):
    name = 'language'
    pattern = re.compile(r'^[a-zA-Z]{1,8}(-[a-zA-Z0-9]{1,8})*$')

    def __new__(cls, value):
        if isinstance(value, bool):
            value = 'true' if value else 'false'
        elif not isinstance(value, str):
            value = str(value)
        else:
            value = collapse_white_spaces(value)

        match = cls.pattern.match(value)
        if match is None:
            raise ValueError('invalid value {!r} for xs:{}'.format(value, cls.name))
        return super(NormalizedString, cls).__new__(cls, value)


class Name(XsdToken):
    name = 'Name'
    pattern = re.compile(r'^(?:[^\d\W]|:)[\w.\-:\u00B7\u0300-\u036F\u203F\u2040]*$')


class NCName(Name):
    name = 'NCName'
    pattern = re.compile(r'^[^\d\W][\w.\-\u00B7\u0300-\u036F\u203F\u2040]*$')


class Id(NCName):
    name = 'ID'


class Idref(NCName):
    name = 'IDREF'


class Entity(NCName):
    name = 'ENTITY'


class NMToken(XsdToken):
    name = 'NMTOKEN'
    pattern = re.compile(r'^[\w.\-:\u00B7\u0300-\u036F\u203F\u2040]+$')


class AbstractBinary(metaclass=AtomicTypeABCMeta):
    """
    Abstract class for xs:base64Binary data.

    :param value: a string or a binary data or an untyped atomic instance.
    """
    def __init__(self, value):
        if isinstance(value, self.__class__):
            self.value = value.value
        elif isinstance(value, AbstractBinary):
            self.value = self.encoder(value.decode())
        else:
            if isinstance(value, UntypedAtomic):
                value = collapse_white_spaces(value.value)
            elif isinstance(value, str):
                value = collapse_white_spaces(value)
            elif isinstance(value, bytes):
                value = collapse_white_spaces(value.decode('utf-8'))
            else:
                raise self.invalid_type(value)

            self.validate(value)
            self.value = value.replace(' ', '').encode('ascii')

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.value)

    def __bytes__(self):
        return self.value

    def __str__(self):
        return self.value.decode('utf-8')

    def __eq__(self, other):
        if isinstance(other, (AbstractBinary, UntypedAtomic)):
            return self.value == other.value
        return self.value == other

    @staticmethod
    @abstractmethod
    def encoder(value):
        raise NotImplementedError()

    @abstractmethod
    def decode(self):
        raise NotImplementedError()


class Base64Binary(AbstractBinary):
    name = 'base64Binary'
    pattern = re.compile(
        r'((?:(?:[A-Za-z0-9+/] ?){4})*(?:(?:[A-Za-z0-9+/] ?){3}[A-Za-z0-9+/]|(?:[A-Za-z0-9+/] ?){2}'
        r'[AEIMQUYcgkosw048] ?=|[A-Za-z0-9+/] ?[AQgw] ?= ?=))?'
    )

    @classmethod
    def validate(cls, value):
        if isinstance(value, cls):
            return
        elif isinstance(value, bytes):
            value = value.decode()
        elif not isinstance(value, str):
            raise cls.invalid_type(value)

        value = value.replace(' ', '')
        if not value:
            return True

        match = cls.pattern.match(value)
        if match is None or match.group(0) != value:
            raise cls.invalid_value(value)

        try:
            base64.standard_b64decode(value)
        except (ValueError, TypeError):
            raise cls.invalid_value(value)

    @staticmethod
    def encoder(value):
        return codecs.encode(value, 'base64').rstrip(b'\n')

    def decode(self):
        return codecs.decode(self.value, 'base64')


class HexBinary(AbstractBinary):
    name = 'hexBinary'
    pattern = re.compile(r'^([0-9a-fA-F]{2})*$')

    @classmethod
    def validate(cls, value):
        if isinstance(value, cls):
            return
        elif isinstance(value, bytes):
            value = value.decode()
        elif not isinstance(value, str):
            raise cls.invalid_type(value)

        value = value.strip()
        if cls.pattern.match(value) is None:
            raise cls.invalid_value(value)

    @staticmethod
    def encoder(value):
        return codecs.encode(value, 'hex')

    def decode(self):
        return codecs.decode(self.value, 'hex')

    def __str__(self):
        return self.value.decode('utf-8').upper()

    def __eq__(self, other):
        if isinstance(other, (AbstractBinary, UntypedAtomic)):
            return self.value.lower() == other.value.lower()
        return isinstance(other, (str, bytes)) and self.value.lower() == other.lower()


class Float10(float, AnyAtomicType):
    name = 'float'
    pattern = re.compile(
        r'^(?:[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[Ee][+-]?[0-9]+)? |[+-]?INF|NaN)$'
    )

    def __new__(cls, value):
        if isinstance(value, str):
            value = collapse_white_spaces(value)
            if value in {'INF', '-INF', 'NaN'} or cls.version != '1.0' and value == '+INF':
                pass
            elif value.lower() in {'inf', '+inf', '-inf', 'nan',
                                   'infinity', '+infinity', '-infinity'}:
                raise ValueError('invalid value {!r} for xs:{}'.format(value, cls.name))

        value = super().__new__(cls, value)
        if -1e-37 < value < 1e-37:
            return super().__new__(cls, 0.0)
        return value

    def __init__(self, value, version='1.0'):
        if version != '1.0':
            self.version = version
        super().__init__()

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            if super(Float10, self).__eq__(other):
                return True
            return math.isclose(self, other, rel_tol=1e-7, abs_tol=0.0)
        return super(Float10, self).__eq__(other)

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            if super(Float10, self).__eq__(other):
                return False
            return not math.isclose(self, other, rel_tol=1e-7, abs_tol=0.0)
        return super(Float10, self).__ne__(other)

    def __add__(self, other):
        if isinstance(other, (self.__class__, int)):
            return self.__class__(super(Float10, self).__add__(other))
        return super(Float10, self).__add__(other)

    def __radd__(self, other):
        if isinstance(other, (self.__class__, int)):
            return self.__class__(super(Float10, self).__radd__(other))
        return super(Float10, self).__radd__(other)

    def __sub__(self, other):
        if isinstance(other, (self.__class__, int)):
            return self.__class__(super(Float10, self).__sub__(other))
        return super(Float10, self).__sub__(other)

    def __rsub__(self, other):
        if isinstance(other, (self.__class__, int)):
            return self.__class__(super(Float10, self).__rsub__(other))
        return super(Float10, self).__rsub__(other)

    def __mul__(self, other):
        if isinstance(other, (self.__class__, int)):
            return self.__class__(super(Float10, self).__mul__(other))
        return super(Float10, self).__mul__(other)

    def __rmul__(self, other):
        if isinstance(other, (self.__class__, int)):
            return self.__class__(super(Float10, self).__rmul__(other))
        return super(Float10, self).__rmul__(other)

    def __truediv__(self, other):
        if isinstance(other, (self.__class__, int)):
            return self.__class__(super(Float10, self).__truediv__(other))
        return super(Float10, self).__truediv__(other)

    def __rtruediv__(self, other):
        if isinstance(other, (self.__class__, int)):
            return self.__class__(super(Float10, self).__rtruediv__(other))
        return super(Float10, self).__rtruediv__(other)

    def __mod__(self, other):
        if isinstance(other, (self.__class__, int)):
            return self.__class__(super(Float10, self).__mod__(other))
        return super(Float10, self).__mod__(other)

    def __rmod__(self, other):
        if isinstance(other, (self.__class__, int)):
            return self.__class__(super(Float10, self).__rmod__(other))
        return super(Float10, self).__rmod__(other)

    def __abs__(self):
        return self.__class__(super(Float10, self).__abs__())


class Float(Float10):
    name = 'float'
    version = '1.1'


class Integer(int, metaclass=AtomicTypeABCMeta):
    """A wrapper for emulating xs:integer and limited integer types."""
    name = 'integer'
    pattern = re.compile(r'^[\-+]?[0-9]+$')
    lower_bound, higher_bound = None, None

    def __init__(self, value):
        if self.lower_bound is not None and self < self.lower_bound:
            raise ValueError("value {} is too low for {!r}".format(value, self.__class__))
        elif self.higher_bound is not None and self >= self.higher_bound:
            raise ValueError("value {} is too high for {!r}".format(value, self.__class__))
        super(Integer, self).__init__()

    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is Integer:
            return issubclass(subclass, int) and not issubclass(subclass, bool)
        return NotImplemented

    @classmethod
    def validate(cls, value):
        if isinstance(value, cls):
            return
        elif cls.name == 'integer' and isinstance(value, int) and not isinstance(value, bool):
            return
        elif not isinstance(value, str):
            raise cls.invalid_type(value)
        elif cls.pattern.match(value) is None:
            raise cls.invalid_value(value)


class NonPositiveInteger(Integer):
    name = 'nonPositiveInteger'
    lower_bound, higher_bound = None, 1


class NegativeInteger(NonPositiveInteger):
    name = 'negativeInteger'
    lower_bound, higher_bound = None, 0


class Long(Integer):
    name = 'long'
    lower_bound, higher_bound = -2**63, 2**63


class Int(Long):
    name = 'int'
    lower_bound, higher_bound = -2**31, 2**31


class Short(Int):
    name = 'short'
    lower_bound, higher_bound = -2**15, 2**15


class Byte(Short):
    name = 'byte'
    lower_bound, higher_bound = -2**7, 2**7


class NonNegativeInteger(Integer):
    name = 'nonNegativeInteger'
    lower_bound, higher_bound = 0, None


class PositiveInteger(NonNegativeInteger):
    name = 'positiveInteger'
    lower_bound, higher_bound = 1, None


class UnsignedLong(NonNegativeInteger):
    name = 'unsignedLong'
    lower_bound, higher_bound = 0, 2**64


class UnsignedInt(UnsignedLong):
    name = 'unsignedInt'
    lower_bound, higher_bound = 0, 2**32


class UnsignedShort(UnsignedInt):
    name = 'unsignedShort'
    lower_bound, higher_bound = 0, 2**16


class UnsignedByte(UnsignedShort):
    name = 'unsignedByte'
    lower_bound, higher_bound = 0, 2**8


class AnyURI(AnyAtomicType):
    """
    Class for xs:anyURI data.

    :param value: a string or an untyped atomic instance.
    """
    name = 'anyURI'

    def __init__(self, value):
        if isinstance(value, str):
            self.value = collapse_white_spaces(value)
        elif isinstance(value, bytes):
            self.value = collapse_white_spaces(value.decode('utf-8'))
        elif isinstance(value, self.__class__):
            self.value = value.value
        elif isinstance(value, UntypedAtomic):
            self.value = collapse_white_spaces(value.value)
        else:
            raise TypeError('the argument has an invalid type %r' % type(value))

        self.validate(self.value)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.value)

    def __str__(self):
        return self.value

    def __bool__(self):
        return bool(self.value)  # For effective boolean value

    def __hash__(self):
        return hash(self.value)

    def __contains__(self, item):
        return item in self.value

    def __eq__(self, other):
        if isinstance(other, (AnyURI, UntypedAtomic)):
            return self.value == other.value
        elif isinstance(other, (bool, float, Decimal, Integer)):
            raise TypeError("cannot compare {} with xs:{}".format(type(other), self.name))
        return self.value == other

    def __ne__(self, other):
        if isinstance(other, (AnyURI, UntypedAtomic)):
            return self.value != other.value
        elif isinstance(other, (bool, float, Decimal, Integer)):
            raise TypeError("cannot compare {} with xs:{}".format(type(other), self.name))
        return self.value != other

    def __lt__(self, other):
        if isinstance(other, (AnyURI, UntypedAtomic)):
            return self.value < other.value
        return self.value < other

    def __le__(self, other):
        if isinstance(other, (AnyURI, UntypedAtomic)):
            return self.value <= other.value
        return self.value <= other

    def __gt__(self, other):
        if isinstance(other, (AnyURI, UntypedAtomic)):
            return self.value > other.value
        return self.value > other

    def __ge__(self, other):
        if isinstance(other, (AnyURI, UntypedAtomic)):
            return self.value >= other.value
        return self.value >= other

    @classmethod
    def validate(cls, value):
        if isinstance(value, cls):
            return
        elif isinstance(value, bytes):
            value = value.decode()
        elif not isinstance(value, str):
            raise cls.invalid_type(value)

        try:
            url_parts = urlparse(value)
            _ = url_parts.port  # check invalid port!
        except ValueError as err:
            msg = 'invalid value {!r} for xs:{} ({})'
            raise ValueError(msg.format(value, cls.name, str(err))) from None
        else:
            if url_parts.path.startswith(':'):
                raise cls.invalid_value(value)
            elif value.count('#') > 1:
                msg = 'invalid value {!r} for xs:{} (too many # characters)'
                raise ValueError(msg.format(value, cls.name))
            elif WRONG_ESCAPE_PATTERN.search(value) is not None:
                msg = 'invalid value {!r} for xs:{} (wrong escaping)'
                raise ValueError(msg.format(value, cls.name))


class Notation(metaclass=AtomicTypeABCMeta):
    name = 'NOTATION'
    pattern = re.compile(
        r'^(?:(?P<prefix>[^\d\W][\w\-.\u00B7\u0300-\u036F\u0387\u06DD\u06DE\u203F\u2040]*):)?'
        r'(?P<local>[^\d\W][\w\-.\u00B7\u0300-\u036F\u0387\u06DD\u06DE\u203F\u2040]*)$',
    )

    @abstractmethod
    def __new__(cls, *args, **kwargs):
        raise NotImplementedError()

    @classmethod
    def validate(cls, value):
        if isinstance(value, cls):
            return
        elif isinstance(value, bytes):
            value = value.decode()
        elif not isinstance(value, str):
            raise cls.invalid_type(value)

        if any(cls.pattern.match(x) for x in value.split()):
            raise cls.invalid_value(value)


class QName(AnyAtomicType):
    """
    XPath compliant QName, bound with a prefix and a namespace.

    :param uri: the bound namespace URI, must be a not empty \
    URI if a prefixed name is provided for the 2nd argument.
    :param qname: the prefixed name or a local name.
    """
    name = 'QName'
    pattern = re.compile(
        r'^(?:(?P<prefix>[^\d\W][\w\-.\u00B7\u0300-\u036F\u0387\u06DD\u06DE\u203F\u2040]*):)?'
        r'(?P<local>[^\d\W][\w\-.\u00B7\u0300-\u036F\u0387\u06DD\u06DE\u203F\u2040]*)$',
    )

    def __init__(self, uri, qname):
        if uri is None:
            self.namespace = ''
        elif isinstance(uri, str):
            self.namespace = uri
        else:
            raise TypeError('the 1st argument has an invalid type %r' % type(uri))

        if not isinstance(qname, str):
            raise TypeError('the 2nd argument has an invalid type %r' % type(qname))
        self.qname = qname.strip()

        match = self.pattern.match(self.qname)
        if match is None:
            raise ValueError('invalid value {!r} for an xs:QName'.format(self.qname))

        self.prefix = match.groupdict()['prefix']
        self.local_name = match.groupdict()['local']
        if not uri and self.prefix:
            msg = '{!r}: cannot associate a non-empty prefix with no namespace'
            raise ValueError(msg.format(self))

    @property
    def expanded_name(self):
        if not self.namespace:
            return self.local_name
        return '{%s}%s' % (self.namespace, self.local_name)

    def __repr__(self):
        if not self.namespace:
            return '%s(%r)' % (self.__class__.__name__, self.qname)
        return '%s(%r, namespace=%r)' % (self.__class__.__name__, self.qname, self.namespace)

    def __str__(self):
        return self.qname

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError("cannot compare {!r} to {!r}".format(type(self), type(other)))
        return self.namespace == other.namespace and self.local_name == other.local_name


class UntypedAtomic(metaclass=AtomicTypeABCMeta):
    """
    Class for xs:untypedAtomic data. Provides special methods for comparing
    and converting to basic data types.

    :param value: the untyped value, usually a string.
    """
    name = 'untypedAtomic'

    @classmethod
    def validate(cls, value):
        if not isinstance(value, (cls, str)):
            raise cls.invalid_type(value)

    def __init__(self, value):
        if isinstance(value, str):
            self.value = value
        elif isinstance(value, bytes):
            self.value = value.decode('utf-8')
        elif isinstance(value, bool):
            self.value = 'true' if value else 'false'
        elif isinstance(value, (UntypedAtomic, AnyURI)):
            self.value = value.value
        elif isinstance(value, QName):
            self.value = value.qname
        elif isinstance(value, AbstractBinary):
            self.value = value.value.decode('utf-8')
        elif isinstance(value, (AbstractDateTime, Duration, int)):
            self.value = str(value)
        elif isinstance(value, float):
            self.value = str(value).rstrip('0').rstrip('.')
        elif isinstance(value, Decimal):
            self.value = str(value.normalize())
        else:
            raise TypeError("{!r} is not an atomic value".format(value))

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.value)

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
            return self.value, other.value
        elif isinstance(other, bool):
            # Cast to xs:boolean
            value = self.value.strip()
            if value not in {'0', '1', 'true', 'false'}:
                raise ValueError("{!r} cannot be cast to xs:boolean".format(self.value))
            return value in ('1', 'true'), other
        elif isinstance(other, int):
            return float(self.value), other
        elif isinstance(other, str):
            return str(self.value), other
        elif isinstance(other, (AbstractDateTime, Duration)):
            return type(other).fromstring(self.value), other
        else:
            return type(other)(self.value), other

    def __hash__(self):
        return hash(self.value)

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
        return bool(self.value)  # For effective boolean value, not for cast to xs:boolean.

    def __abs__(self):
        return abs(Decimal(self.value))

    def __mod__(self, other):
        return operator.mod(*self._get_operands(other))

    def __str__(self):
        return self.value

    def __bytes__(self):
        return bytes(self.value, encoding='utf-8')


####
# Type proxies for basic Python datatypes: a proxy class creates
# and validates its Python datatype and virtual registered types.

class BooleanProxy(metaclass=AtomicTypeABCMeta):
    name = 'boolean'
    pattern = re.compile(r'^(?:true|false|1|0)$')

    def __new__(cls, value):
        if isinstance(value, bool):
            return value
        elif isinstance(value, (int, float, Decimal)):
            if math.isnan(value):
                return False
            return bool(value)
        elif isinstance(value, UntypedAtomic):
            value = value.value
        elif not isinstance(value, str):
            raise TypeError('invalid type {!r} for xs:{}'.format(type(value), cls.name))

        if value.strip() not in {'true', 'false', '1', '0'}:
            raise ValueError('invalid value {!r} for xs:{}'.format(value, cls.name))
        return 't' in value or '1' in value

    @classmethod
    def __subclasshook__(cls, subclass):
        return issubclass(subclass, bool)

    @classmethod
    def validate(cls, value):
        if isinstance(value, bool):
            return
        elif not isinstance(value, str):
            raise cls.invalid_type(value)
        elif cls.pattern.match(value) is None:
            raise cls.invalid_value(value)


class DecimalProxy(metaclass=AtomicTypeABCMeta):
    name = 'decimal'
    pattern = re.compile(r'^(?:[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))$')

    def __new__(cls, value):
        if isinstance(value, (str, UntypedAtomic)):
            value = collapse_white_spaces(str(value)).replace(' ', '')
            if cls.pattern.match(value) is None:
                raise cls.invalid_value(value)
        elif isinstance(value, (float, Float10, Decimal)):
            if math.isinf(value) or math.isnan(value):
                raise cls.invalid_value(value)
        try:
            return Decimal(value)
        except ArithmeticError:
            raise ArithmeticError('invalid value {!r} for xs:{}'.format(value, cls.name))

    @classmethod
    def __subclasshook__(cls, subclass):
        return issubclass(subclass, (int, Decimal, Integer)) and not issubclass(subclass, bool)

    @classmethod
    def validate(cls, value):
        if isinstance(value, (int, Decimal, Integer)) and not isinstance(value, bool):
            return
        elif not isinstance(value, str):
            raise cls.invalid_type(value)
        elif cls.pattern.match(value) is None:
            raise cls.invalid_value(value)


class DoubleProxy10(metaclass=AtomicTypeABCMeta):
    name = 'double'
    pattern = re.compile(
        r'^(?:[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[Ee][+-]?[0-9]+)? |[+-]?INF|NaN)$'
    )

    def __new__(cls, value):
        if isinstance(value, str):
            value = collapse_white_spaces(value)
            if value in {'INF', '-INF', 'NaN'} or cls.version != '1.0' and value == '+INF':
                pass
            elif value.lower() in {'inf', '+inf', '-inf', 'nan',
                                   'infinity', '+infinity', '-infinity'}:
                raise ValueError('invalid value {!r} for xs:{}'.format(value, cls.name))
        return float(value)

    @classmethod
    def __subclasshook__(cls, subclass):
        return issubclass(subclass, float) and not issubclass(subclass, Float10)

    @classmethod
    def validate(cls, value):
        if isinstance(value, float) and not isinstance(value, Float10):
            return
        elif not isinstance(value, str):
            raise cls.invalid_type(value)
        elif cls.pattern.match(value) is None:
            raise cls.invalid_value(value)


class DoubleProxy(DoubleProxy10):
    name = 'double'
    version = '1.1'


class StringProxy(metaclass=AtomicTypeABCMeta):
    name = 'string'

    def __new__(cls, *args, **kwargs):
        return str(*args, **kwargs)

    @classmethod
    def __subclasshook__(cls, subclass):
        return issubclass(subclass, str)

    @classmethod
    def validate(cls, value):
        if not isinstance(value, str):
            raise cls.invalid_type(value)


####
# Type proxies for multiple type-checking in XPath expressions
class NumericTypeMeta(type):
    """Metaclass for checking numeric classes and instances."""

    def __instancecheck__(cls, instance):
        return isinstance(instance, (int, float, Decimal)) and not isinstance(instance, bool)

    def __subclasscheck__(cls, subclass):
        if issubclass(subclass, bool):
            return False
        return issubclass(subclass, int) or issubclass(subclass, float) \
            or issubclass(subclass, Decimal)


class NumericProxy(metaclass=NumericTypeMeta):
    """Proxy for xs:numeric related types. Builds xs:float instances."""

    def __new__(cls, *args, **kwargs):
        return float(*args, **kwargs)


class ArithmeticTypeMeta(type):
    """Metaclass for checking numeric, datetime and duration classes/instances."""

    def __instancecheck__(cls, instance):
        return isinstance(
            instance, (int, float, Decimal, AbstractDateTime, Duration, UntypedAtomic)
        ) and not isinstance(instance, bool)

    def __subclasscheck__(cls, subclass):
        if issubclass(subclass, bool):
            return False
        return issubclass(subclass, int) or issubclass(subclass, float) or \
            issubclass(subclass, Decimal) or issubclass(subclass, Duration) \
            or issubclass(subclass, AbstractDateTime) or issubclass(subclass, UntypedAtomic)


class ArithmeticProxy(metaclass=ArithmeticTypeMeta):
    """Proxy for arithmetic related types. Builds xs:float instances."""

    def __new__(cls, *args, **kwargs):
        return float(*args, **kwargs)


##
# Register not derived XSD primitive types as virtual subclasses of AnyAtomicType

AnyAtomicType.register(BooleanProxy)
AnyAtomicType.register(Base64Binary)
AnyAtomicType.register(DecimalProxy)
AnyAtomicType.register(StringProxy)
AnyAtomicType.register(Date10)
AnyAtomicType.register(DateTime10)
AnyAtomicType.register(DoubleProxy10)
AnyAtomicType.register(GregorianDay)
AnyAtomicType.register(GregorianMonth)
AnyAtomicType.register(GregorianMonthDay)
AnyAtomicType.register(GregorianYear10)
AnyAtomicType.register(GregorianYearMonth10)
AnyAtomicType.register(HexBinary)
AnyAtomicType.register(Notation)
AnyAtomicType.register(Time)
AnyAtomicType.register(UntypedAtomic)
StringProxy.register(NormalizedString)

xsd11_atomic_types.update(
    (k, v) for k, v in xsd10_atomic_types.items() if k not in xsd11_atomic_types
)
XSD_BUILTIN_TYPES = xsd10_atomic_types

ATOMIC_VALUES = {
    'untypedAtomic': UntypedAtomic('1'),
    'anyType': UntypedAtomic('1'),
    'anySimpleType': UntypedAtomic('1'),
    'anyAtomicType': UntypedAtomic('1'),
    'boolean': True,
    'decimal': Decimal('1.0'),
    'double': 1.0,
    'float': Float10(1.0),
    'string': '  alpha\t',
    'date': Date.fromstring('2000-01-01'),
    'dateTime': DateTime.fromstring('2000-01-01T12:00:00'),
    'gDay': GregorianDay.fromstring('---31'),
    'gMonth': GregorianMonth.fromstring('--12'),
    'gMonthDay': GregorianMonthDay.fromstring('--12-01'),
    'gYear': GregorianYear.fromstring('1999'),
    'gYearMonth': GregorianYearMonth.fromstring('1999-09'),
    'time': Time.fromstring('09:26:54'),
    'duration': Duration.fromstring('P1MT1S'),
    'dayTimeDuration': DayTimeDuration.fromstring('P1DT1S'),
    'yearMonthDuration': YearMonthDuration.fromstring('P1Y1M'),
    'QName': QName(XSD_NAMESPACE, 'xs:element'),
    'anyURI': AnyURI('https://example.com'),
    'normalizedString': NormalizedString(' alpha  '),
    'token': XsdToken('a token'),
    'language': Language('en-US'),
    'Name': Name('_a.name::'),
    'NCName': NCName('nc-name'),
    'ID': Id('id1'),
    'IDREF': Idref('id_ref1'),
    'ENTITY': Entity('entity1'),
    'NMTOKEN': NMToken('a_token'),
    'base64Binary': Base64Binary(b'YWxwaGE='),
    'hexBinary': HexBinary(b'31'),
    'dateTimeStamp': DateTimeStamp.fromstring('2000-01-01T12:00:00+01:00'),
    'integer': Integer(1),
    'long': Long(1),
    'int': Int(1),
    'short': Short(1),
    'byte': Byte(1),
    'positiveInteger': PositiveInteger(1),
    'negativeInteger': NegativeInteger(-1),
    'nonPositiveInteger': NonPositiveInteger(0),
    'nonNegativeInteger': NonNegativeInteger(0),
    'unsignedLong': UnsignedLong(1),
    'unsignedInt': UnsignedInt(1),
    'unsignedShort': UnsignedShort(1),
    'unsignedByte': UnsignedByte(1),
}

__all__ = ['xsd10_atomic_types', 'xsd11_atomic_types', 'ATOMIC_VALUES', 'XSD_BUILTIN_TYPES',
           'is_idrefs', 'NumericProxy', 'ArithmeticProxy', 'QNAME_PATTERN', 'AnyAtomicType',
           'AbstractDateTime', 'DateTime10', 'DateTime', 'DateTimeStamp', 'Date10',
           'Date', 'GregorianDay', 'GregorianMonth', 'GregorianMonthDay', 'GregorianYear10',
           'GregorianYear', 'GregorianYearMonth10', 'GregorianYearMonth', 'Time',
           'Timezone', 'Duration', 'YearMonthDuration', 'DayTimeDuration', 'StringProxy',
           'NormalizedString', 'XsdToken', 'Language', 'Name', 'NCName', 'Id', 'Idref',
           'Entity', 'NMToken', 'Base64Binary', 'HexBinary', 'Float10', 'Float',
           'Integer', 'NonPositiveInteger', 'NegativeInteger', 'Long', 'Int', 'Short',
           'Byte', 'NonNegativeInteger', 'PositiveInteger', 'UnsignedLong', 'UnsignedInt',
           'UnsignedShort', 'UnsignedByte', 'AnyURI', 'Notation', 'QName', 'BooleanProxy',
           'DecimalProxy', 'DoubleProxy10', 'DoubleProxy', 'UntypedAtomic']
