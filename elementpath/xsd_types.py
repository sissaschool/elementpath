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

import operator
import re
import decimal
from datetime import datetime, timedelta, tzinfo
from calendar import leapdays, monthrange

from .compat import PY3, string_base_type
from .exceptions import ElementPathTypeError, ElementPathValueError


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


class Duration(object):
    """
    Class for the xs:duration type. Instances are created from ISO 8601 durations, with the restriction
    of no weeks fragment and an optional decimal part admitted only for seconds fragment.

    :param value: the formatted ISO 8601 duration, with no week fragment and an optional decimal part \
    only for seconds fragment.
    """
    def __init__(self, value):
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
            self.months = months
            self.seconds = seconds + (days * 24 + hours) * 3600 + minutes * 60
        else:
            self.months = -months
            self.seconds = -seconds - (days * 24 + hours) * 3600 - minutes * 60

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, str(self))

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

    def __init__(self, value):
        super(YearMonthDuration, self).__init__(value)
        if self.seconds:
            raise ElementPathValueError('seconds must be 0 for %r.' % self.__class__.__name__)


class DayTimeDuration(Duration):

    def __init__(self, value):
        super(DayTimeDuration, self).__init__(value)
        if self.months:
            raise ElementPathValueError('months must be 0 for %r.' % self.__class__.__name__)


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
