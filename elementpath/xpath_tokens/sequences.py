#
# Copyright (c), 2018-2025, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from collections.abc import Iterable
from itertools import chain
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from elementpath.aliases import SequenceType  # noqa: F401
    from aliases import ItemType

__all__ = ['XPathSequence', 'EmptySequence', 'EmptySequenceType']


class XPathSequence(tuple):

    @classmethod
    def empty_sequence(cls) -> 'XPathSequence':
        return EmptySequence

    @classmethod
    def sequence_concat(cls,
                        input1: Iterable['ItemType'],
                        input2: Iterable['ItemType']) -> 'XPathSequence':
        return cls(chain(input1, input2))

    def __add__(self, other: object) -> 'XPathSequence':
        if isinstance(other, (tuple, list)):
            return XPathSequence(chain(self, other))
        return NotImplemented

    def __radd__(self, other: object) -> 'XPathSequence':
        if isinstance(other, (tuple, list)):
            return XPathSequence(chain(other, self))
        return NotImplemented

    def __eq__(self, other: object) -> bool:
        if isinstance(other, list):
            return super().__eq__(tuple(other))
        return super().__eq__(other)

    def __ne__(self, other: object) -> bool:
        if isinstance(other, list):
            return super().__ne__(tuple(other))
        return super().__ne__(other)


class EmptySequenceType(XPathSequence):
    pass


EmptySequence = EmptySequenceType()
