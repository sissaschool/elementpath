#
# Copyright (c), 2018-2025, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from collections.abc import Sequence
from typing import NoReturn

__all__ = ['EmptySequenceType', 'EmptySequence']


class EmptySequenceType(Sequence):
    """A singleton sequence with no elements."""
    _instance: 'EmptySequenceType'

    def __new__(cls) -> 'EmptySequenceType':
        if not hasattr(cls, 'instance'):
            cls._instance = super().__new__(cls)
        return cls._instance

    def __getitem__(self, index: int) -> NoReturn:
        raise IndexError(index)

    def __len__(self) -> int:
        return 0

    def __repr__(self) -> str:
        return '()'


EmptySequence = EmptySequenceType()
