#
# Copyright (c), 2018-2020, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import re
import math
from calendar import isleap, leapdays
from decimal import Decimal
from typing import Optional, Union

###
# Data validation helpers

NORMALIZE_PATTERN = re.compile(r'[^\S\xa0]')
WHITESPACES_PATTERN = re.compile(r'[^\S\xa0]+')  # include ASCII 160 (non-breaking space)
NCNAME_PATTERN = re.compile(r'^[^\d\W][\w.\-\u00B7\u0300-\u036F\u203F\u2040]*$')
QNAME_PATTERN = re.compile(
    r'^(?:(?P<prefix>[^\d\W][\w\-.\u00B7\u0300-\u036F\u0387\u06DD\u06DE\u203F\u2040]*):)?'
    r'(?P<local>[^\d\W][\w\-.\u00B7\u0300-\u036F\u0387\u06DD\u06DE\u203F\u2040]*)$',
)
EQNAME_PATTERN = re.compile(
    r'^(?:Q{(?P<namespace>[^}]+)}|'
    r'(?P<prefix>[^\d\W][\w\-.\u00B7\u0300-\u036F\u0387\u06DD\u06DE\u203F\u2040]*):)?'
    r'(?P<local>[^\d\W][\w\-.\u00B7\u0300-\u036F\u0387\u06DD\u06DE\u203F\u2040]*)$',
)
WRONG_ESCAPE_PATTERN = re.compile(r'%(?![a-fA-F\d]{2})')
XML_NEWLINES_PATTERN = re.compile('\r\n|\r|\n')


def collapse_white_spaces(s: str) -> str:
    return WHITESPACES_PATTERN.sub(' ', s).strip(' ')


def is_idrefs(value: Optional[str]) -> bool:
    return isinstance(value, str) and \
        all(NCNAME_PATTERN.match(x) is not None for x in value.split())


###
# Sequence type checking
SEQUENCE_TYPE_PATTERN = re.compile(r'\s?([()?*+,])\s?')


def normalize_sequence_type(sequence_type: str) -> str:
    sequence_type = WHITESPACES_PATTERN.sub(' ', sequence_type).strip()
    sequence_type = SEQUENCE_TYPE_PATTERN.sub(r'\1', sequence_type)
    return sequence_type.replace(',', ', ').replace(')as', ') as')


###
# Date/Time helpers
MONTH_DAYS = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
MONTH_DAYS_LEAP = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def adjust_day(year: int, month: int, day: int) -> int:
    if month in {1, 3, 5, 7, 8, 10, 12}:
        return day
    elif month in {4, 6, 9, 11}:
        return min(day, 30)
    else:
        return min(day, 29) if isleap(year) else min(day, 28)


def days_from_common_era(year: int) -> int:
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


def months2days(year: int, month: int, months_delta: int) -> int:
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


def round_number(value: Union[float, int, Decimal]) -> Union[float, int, Decimal]:
    if math.isnan(value) or math.isinf(value):
        return value

    number = Decimal(value)
    if number > 0:
        return type(value)(number.quantize(Decimal('1'), rounding='ROUND_HALF_UP'))
    else:
        return type(value)(number.quantize(Decimal('1'), rounding='ROUND_HALF_DOWN'))


def normalized_seconds(seconds: Decimal) -> str:
    # Decimal.normalize() does not remove exp every time: eg. Decimal('1E+1')
    return '{:.6f}'.format(seconds).rstrip('0').rstrip('.')


def is_xml_codepoint(cp: int) -> bool:
    return cp in {0x9, 0xA, 0xD} or \
        0x20 <= cp <= 0xD7FF or \
        0xE000 <= cp <= 0xFFFD or \
        0x10000 <= cp <= 0x10FFFF


def ordinal(n: int) -> str:
    if n in {11, 12, 13}:
        return '%dth' % n

    least_significant_digit = n % 10
    if least_significant_digit == 1:
        return '%dst' % n
    elif least_significant_digit == 2:
        return '%dnd' % n
    elif least_significant_digit == 3:
        return '%drd' % n
    else:
        return '%dth' % n
