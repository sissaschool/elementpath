#
# Copyright (c), 2018-2020, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from abc import abstractmethod
from typing import Any, Callable, Union
import re
import codecs

from ..helpers import collapse_white_spaces
from .atomic_types import AtomicTypeMeta
from .untyped import UntypedAtomic


class AbstractBinary(metaclass=AtomicTypeMeta):
    """
    Abstract class for xs:base64Binary data.

    :param value: a string or a binary data or an untyped atomic instance.
    """
    value: bytes
    invalid_type: Callable[[Any], TypeError]

    def __init__(self, value: Union[str, bytes, UntypedAtomic, 'AbstractBinary']) -> None:
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

    def __repr__(self) -> str:
        return '%s(%r)' % (self.__class__.__name__, self.value)

    def __bytes__(self) -> bytes:
        return self.value

    @classmethod
    def validate(cls, value: object) -> None:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def encoder(value: bytes) -> bytes:
        raise NotImplementedError()

    @abstractmethod
    def decode(self) -> bytes:
        raise NotImplementedError()


class Base64Binary(AbstractBinary):
    name = 'base64Binary'
    pattern = re.compile(
        r'((?:(?:[A-Za-z0-9+/] ?){4})*(?:(?:[A-Za-z0-9+/] ?){3}[A-Za-z0-9+/]|'
        r'(?:[A-Za-z0-9+/] ?){2}'
        r'[AEIMQUYcgkosw048] ?=|[A-Za-z0-9+/] ?[AQgw] ?= ?=))?'
    )

    @classmethod
    def validate(cls, value: object) -> None:
        if isinstance(value, cls):
            return
        elif isinstance(value, bytes):
            value = value.decode()
        elif not isinstance(value, str):
            raise cls.invalid_type(value)

        value = value.replace(' ', '')
        if value:
            match = cls.pattern.match(value)
            if match is None or match.group(0) != value:
                raise cls.invalid_value(value)

    def __str__(self) -> str:
        return self.value.decode('utf-8')

    def __hash__(self) -> int:
        return hash(self.value)

    def __len__(self) -> int:
        if self.value[-2] == ord('='):
            return len(self.value) // 4 * 3 - 2
        elif self.value[-1] == ord('='):
            return len(self.value) // 4 * 3 - 1
        return len(self.value) // 4 * 3

    def __eq__(self, other: object) -> bool:
        if isinstance(other, self.__class__):
            return self.value == other.value
        elif isinstance(other, UntypedAtomic):
            return self.value == self.__class__(other).value
        elif isinstance(other, str):
            return self.value == other.encode()
        return isinstance(other, bytes) and self.value == other

    @staticmethod
    def encoder(value: bytes) -> bytes:
        return codecs.encode(value, 'base64').rstrip(b'\n')

    def decode(self) -> bytes:
        return codecs.decode(self.value, 'base64')


class HexBinary(AbstractBinary):
    name = 'hexBinary'
    pattern = re.compile(r'^([0-9a-fA-F]{2})*$')

    @classmethod
    def validate(cls, value: object) -> None:
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
    def encoder(value: bytes) -> bytes:
        return codecs.encode(value, 'hex')

    def decode(self) -> bytes:
        return codecs.decode(self.value, 'hex')

    def __str__(self) -> str:
        return self.value.decode('utf-8').upper()

    def __hash__(self) -> int:
        return hash(self.value.upper())

    def __len__(self) -> int:
        return len(self.value) // 2

    def __eq__(self, other: object) -> bool:
        if isinstance(other, self.__class__):
            return self.value.upper() == other.value.upper()
        elif isinstance(other, UntypedAtomic):
            return self.value.upper() == self.__class__(other).value.upper()
        elif isinstance(other, str):
            return self.value.upper() == other.encode().upper()
        return isinstance(other, bytes) and self.value.upper() == other.upper()
