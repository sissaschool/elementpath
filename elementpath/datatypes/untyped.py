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
from typing import Any, Tuple, Union
from .atomic_types import AtomicTypeMeta, AnyAtomicType


class UntypedAtomic(metaclass=AtomicTypeMeta):
    """
    Class for xs:untypedAtomic data. Provides special methods for comparing
    and converting to basic data types.

    :param value: the untyped value, usually a string.
    """
    name = 'untypedAtomic'
    value: str

    @classmethod
    def validate(cls, value: object) -> None:
        if not isinstance(value, cls):
            raise cls.invalid_type(value)

    def __init__(self, value: Union[str, bytes, bool, float, Decimal,
                                    'UntypedAtomic', AnyAtomicType]) -> None:
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

    def __repr__(self) -> str:
        return '%s(%r)' % (self.__class__.__name__, self.value)

    def _get_operands(self, other: Any, force_float: bool = True) -> Tuple[Any, Any]:
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

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: Any) -> Any:
        return operator.eq(*self._get_operands(other, force_float=False))

    def __ne__(self, other: Any) -> Any:
        return not operator.eq(*self._get_operands(other, force_float=False))

    def __lt__(self, other: Any) -> Any:
        return operator.lt(*self._get_operands(other))

    def __le__(self, other: Any) -> Any:
        return operator.le(*self._get_operands(other))

    def __gt__(self, other: Any) -> Any:
        return operator.gt(*self._get_operands(other))

    def __ge__(self, other: Any) -> Any:
        return operator.ge(*self._get_operands(other))

    def __add__(self, other: Any) -> Any:
        return operator.add(*self._get_operands(other))
    __radd__ = __add__

    def __sub__(self, other: Any) -> Any:
        return operator.sub(*self._get_operands(other))

    def __rsub__(self, other: Any) -> Any:
        return operator.sub(*reversed(self._get_operands(other)))

    def __mul__(self, other: Any) -> Any:
        return operator.mul(*self._get_operands(other))
    __rmul__ = __mul__

    def __truediv__(self, other: Any) -> Any:
        return operator.truediv(*self._get_operands(other))

    def __rtruediv__(self, other: Any) -> Any:
        return operator.truediv(*reversed(self._get_operands(other)))

    def __int__(self) -> int:
        return int(self.value)

    def __float__(self) -> float:
        return float(self.value)

    def __bool__(self) -> bool:
        return bool(self.value)  # For effective boolean value, not for cast to xs:boolean.

    def __abs__(self) -> Decimal:
        return abs(Decimal(self.value))

    def __mod__(self, other: Any) -> Any:
        return operator.mod(*self._get_operands(other))

    def __str__(self) -> str:
        return self.value

    def __bytes__(self) -> bytes:
        return bytes(self.value, encoding='utf-8')
