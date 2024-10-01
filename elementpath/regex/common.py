#
# Copyright (c), 2016-2024, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""
This module defines common definitions and helper functions for regex subpackage.
"""
from sys import maxunicode
from typing import Optional, Set, Tuple, Union

from elementpath._typing import Iterable, Iterator

I_SHORTCUT_REPLACE = (
    ":A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF"
    "\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD"
)

C_SHORTCUT_REPLACE = (
    "-.0-9:A-Z_a-z\u00B7\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u037D\u037F-\u1FFF\u200C-"
    "\u200D\u203F\u2040\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD"
)

CHARACTER_CLASS_ESCAPED: Set[int] = {ord(c) for c in r'-|.^?*+{}()[]\\'}
"""Code Points of escaped chars in a character class."""

CodePoint = Union[int, Tuple[int, int]]


class RegexError(Exception):
    """
    Error in a regular expression or in a character class specification.
    This exception is derived from `Exception` base class and is raised
    only by the regex subpackage.
    """


def unicode_block_key(name: str) -> str:
    return name.upper().replace(' ', '').replace('_', '').replace('-', '')


def code_point_order(cp: CodePoint) -> int:
    """Ordering function for code points."""
    return cp if isinstance(cp, int) else cp[0]


def code_point_reverse_order(cp: CodePoint) -> int:
    """Reverse ordering function for code points."""
    return cp if isinstance(cp, int) else cp[1] - 1


def iter_code_points(codepoints: Iterable[CodePoint], reverse: bool = False) \
        -> Iterator[CodePoint]:
    """
    Iterates a code points sequence. Three or more consecutive code points are merged in a range.

    :param codepoints: an iterable with code points and code point ranges.
    :param reverse: if `True` reverses the order of the sequence.
    :return: yields code points or code point ranges.
    """
    start_cp = end_cp = 0
    if reverse:
        codepoints = sorted(codepoints, key=code_point_reverse_order, reverse=True)
    else:
        codepoints = sorted(codepoints, key=code_point_order)

    for cp in codepoints:
        if isinstance(cp, int):
            cp = cp, cp + 1

        if not end_cp:
            start_cp, end_cp = cp
            continue
        elif reverse:
            if start_cp <= cp[1]:
                if start_cp > cp[0]:
                    start_cp = cp[0]
                continue
        elif end_cp >= cp[0]:
            if end_cp < cp[1]:
                end_cp = cp[1]
            continue

        if end_cp > start_cp + 1:
            yield start_cp, end_cp
        else:
            yield start_cp
        start_cp, end_cp = cp
    else:
        if end_cp:
            if end_cp > start_cp + 1:
                yield start_cp, end_cp
            else:
                yield start_cp


def get_code_point_range(cp: CodePoint) -> Optional[CodePoint]:
    """
    Returns a code point range.

    :param cp: a single code point or a code point range.
    :return: a code point range or `None` if the argument is not a \
    code point or a code point range.
    """
    if isinstance(cp, int):
        if 0 <= cp <= maxunicode:
            return cp, cp + 1
    else:
        try:
            if isinstance(cp[0], int) and isinstance(cp[1], int):
                if 0 <= cp[0] < cp[1] <= maxunicode + 1:
                    return cp
        except (IndexError, TypeError):
            pass

    return None


def code_point_repr(cp: CodePoint) -> str:
    """
    Returns the string representation of a code point.

    :param cp: an integer or a tuple with at least two integers. \
    Values must be in interval [0, sys.maxunicode].
    """
    if isinstance(cp, int):
        if cp in CHARACTER_CLASS_ESCAPED:
            return r'\%s' % chr(cp)
        return chr(cp)

    if cp[0] in CHARACTER_CLASS_ESCAPED:
        start_char = r'\%s' % chr(cp[0])
    else:
        start_char = chr(cp[0])

    end_cp = cp[1] - 1  # Character ranges include the right bound
    if end_cp in CHARACTER_CLASS_ESCAPED:
        end_char = r'\%s' % chr(end_cp)
    else:
        end_char = chr(end_cp)

    if end_cp > cp[0] + 1:
        return '%s-%s' % (start_char, end_char)
    else:
        return start_char + end_char
