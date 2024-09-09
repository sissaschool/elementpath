#
# Copyright (c), 2024, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""
Version related imports for subscriptable types for type annotations (no builtins).
"""
import sys

if sys.version_info < (3, 9):
    from typing import Callable, Counter, Deque, Iterable, Iterator, \
        Mapping, Match, MutableMapping, MutableSequence, MutableSet, Pattern, Sequence
else:
    from collections import deque as Deque, Counter  # noqa
    from collections.abc import Callable, Iterable, Iterator, Mapping, MutableMapping, \
        MutableSequence, MutableSet, Sequence
    from re import Match, Pattern


__all__ = ['Callable', 'Counter', 'Deque', 'Iterable', 'Iterator', 'Match',
           'Mapping', 'MutableMapping', 'MutableSequence', 'MutableSet',
           'Pattern', 'Sequence']
