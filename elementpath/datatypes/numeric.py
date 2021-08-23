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
from typing import Optional

from ..helpers import collapse_white_spaces
from .atomic_types import AtomicTypeMeta, AnyAtomicType


class Float10(float, AnyAtomicType):
    name = 'float'
    pattern = re.compile(
        r'^(?:[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[Ee][+-]?[0-9]+)? |[+-]?INF|NaN)$'
    )

    def __new__(cls, value):
        if isinstance(value, str):
            value = collapse_white_spaces(value)
            if value in {'INF', '-INF', 'NaN'} or cls.xsd_version != '1.0' and value == '+INF':
                pass
            elif value.lower() in {'inf', '+inf', '-inf', 'nan',
                                   'infinity', '+infinity', '-infinity'}:
                raise ValueError('invalid value {!r} for xs:{}'.format(value, cls.name))

        value = super().__new__(cls, value)
        if value > 3.4028235E38:
            return super().__new__(cls, 'INF')
        elif value < -3.4028235E38:
            return super().__new__(cls, '-INF')
        elif -1e-37 < value < 1e-37:
            return super().__new__(cls, -0.0 if str(value).startswith('-') else 0.0)
        return value

    def __hash__(self):
        return super(Float10, self).__hash__()

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
    xsd_version = '1.1'


class Integer(int, metaclass=AtomicTypeMeta):
    """A wrapper for emulating xs:integer and limited integer types."""
    name = 'integer'
    pattern = re.compile(r'^[\-+]?[0-9]+$')
    lower_bound: Optional[int] = None
    higher_bound: Optional[int] = None

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
    lower_bound = 0
    higher_bound: Optional[int] = None


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
