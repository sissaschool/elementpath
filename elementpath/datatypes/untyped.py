#
# Copyright (c), 2018-2020, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import operator
from decimal import Decimal
from .atomic_types import AtomicTypeMeta, AnyAtomicType


class UntypedAtomic(metaclass=AtomicTypeMeta):
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
        elif isinstance(value, float):
            self.value = str(value).rstrip('0').rstrip('.')
        elif isinstance(value, Decimal):
            self.value = str(value.normalize())
        elif isinstance(value, UntypedAtomic):
            self.value = value.value
        elif isinstance(value, AnyAtomicType):
            self.value = str(value)
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

        try:
            return type(other).fromstring(self.value), other
        except AttributeError:
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
