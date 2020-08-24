#
# Copyright (c), 2016-2020, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import re
from itertools import chain
from sys import maxunicode
from collections.abc import MutableSet

from .unicode_subsets import RegexError, UnicodeSubset, UNICODE_CATEGORIES, unicode_subset


I_SHORTCUT_REPLACE = (
    ":A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF"
    "\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD"
)

C_SHORTCUT_REPLACE = (
    "-.0-9:A-Z_a-z\u00B7\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u037D\u037F-\u1FFF\u200C-"
    "\u200D\u203F\u2040\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD"
)

S_SHORTCUT_SET = UnicodeSubset(' \n\t\r')
D_SHORTCUT_SET = UnicodeSubset()
D_SHORTCUT_SET._codepoints = UNICODE_CATEGORIES['Nd'].codepoints
I_SHORTCUT_SET = UnicodeSubset(I_SHORTCUT_REPLACE)
C_SHORTCUT_SET = UnicodeSubset(C_SHORTCUT_REPLACE)
W_SHORTCUT_SET = UnicodeSubset(chain(
    UNICODE_CATEGORIES['L'].codepoints,
    UNICODE_CATEGORIES['M'].codepoints,
    UNICODE_CATEGORIES['N'].codepoints,
    UNICODE_CATEGORIES['S'].codepoints
))

# Single and Multi character escapes
CHARACTER_ESCAPES = {
    # Single-character escapes
    '\\n': '\n',
    '\\r': '\r',
    '\\t': '\t',
    '\\|': '|',
    '\\.': '.',
    '\\-': '-',
    '\\^': '^',
    '\\?': '?',
    '\\*': '*',
    '\\+': '+',
    '\\{': '{',
    '\\}': '}',
    '\\(': '(',
    '\\)': ')',
    '\\[': '[',
    '\\]': ']',
    '\\\\': '\\',

    # Multi-character escapes
    '\\s': S_SHORTCUT_SET,
    '\\S': S_SHORTCUT_SET,
    '\\d': D_SHORTCUT_SET,
    '\\D': D_SHORTCUT_SET,
    '\\i': I_SHORTCUT_SET,
    '\\I': I_SHORTCUT_SET,
    '\\c': C_SHORTCUT_SET,
    '\\C': C_SHORTCUT_SET,
    '\\w': W_SHORTCUT_SET,
    '\\W': W_SHORTCUT_SET,
}


class CharacterClass(MutableSet):
    """
    A set class to represent XML Schema/XQuery/XPath regex character class.

    TODO: implement __ior__, __iand__, __ixor__ operators for a full mutable set class.
    """
    _re_char_set = re.compile(r'(?<!.-)(\\[nrt|.\-^?*+{}()\]sSdDiIcCwW]|\\[pP]{[a-zA-Z\-0-9]+})')
    _re_unicode_ref = re.compile(r'\\([pP]){([\w\d-]+)}')

    def __init__(self, charset=None, is_syntax=True):
        self.is_syntax = is_syntax
        self.positive = UnicodeSubset()
        self.negative = UnicodeSubset()
        if charset:
            self.add(charset)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, str(self))

    def __str__(self):
        if not self.negative:
            return '[%s]' % str(self.positive)
        elif not self.positive:
            return '[^%s]' % str(self.negative)
        else:
            return '[%s%s]' % (
                str(UnicodeSubset(self.negative.complement())), str(self.positive)
            )

    def __contains__(self, char):
        if self.negative:
            return ord(char) not in self.negative or ord(char) in self.positive
        return ord(char) in self.positive

    def __iter__(self):
        if self.negative:
            return (
                cp for cp in range(maxunicode + 1)
                if cp in self.positive or cp not in self.negative
            )
        return iter(sorted(self.positive))

    def __len__(self):
        return len(self.positive) + len(self.negative)

    def __isub__(self, other):
        if self.negative:
            if other.negative:
                self.positive |= (other.negative - self.negative)
                self.negative.clear()
            self.negative |= other.positive
        elif other.negative:
            self.positive &= other.negative
        self.positive -= other.positive
        return self

    def add(self, charset):
        for part in self._re_char_set.split(charset):
            if part in CHARACTER_ESCAPES:
                value = CHARACTER_ESCAPES[part]
                if isinstance(value, str):
                    self.positive.update(value)
                elif part[-1].islower():
                    self.positive |= value
                else:
                    self.negative |= value
            elif part.startswith('\\p') or part.startswith('\\P'):
                if self._re_unicode_ref.search(part) is None:
                    raise RegexError("wrong Unicode block specification %r" % part)

                try:
                    subset = unicode_subset(part[3:-1])
                except RegexError:
                    if self.is_syntax == '1.0' or not part[3:].startswith('Is'):
                        raise
                    self.positive |= UnicodeSubset([(0, maxunicode)])
                else:
                    if part.startswith('\\p'):
                        self.positive |= subset
                    else:
                        self.negative |= subset
            else:
                self.positive.update(part)

    def discard(self, charset):
        for part in self._re_char_set.split(charset):
            if part in CHARACTER_ESCAPES:
                value = CHARACTER_ESCAPES[part]
                if isinstance(value, str):
                    self.positive.difference_update(value)
                elif part[-1].islower():
                    self.positive -= value
                else:
                    self.negative -= value
            elif part.startswith('\\p') or part.startswith('\\P'):
                if self._re_unicode_ref.search(part) is None:
                    raise RegexError("wrong Unicode block specification %r" % part)

                try:
                    subset = unicode_subset(part[3:-1])
                except RegexError:
                    if self.is_syntax == '1.0' or not part[3:].startswith('Is'):
                        raise
                    self.positive -= UnicodeSubset([(0, maxunicode)])
                else:
                    if part.startswith('\\p'):
                        self.positive -= subset
                    else:
                        self.negative -= subset
            else:
                self.positive.difference_update(part)

    def clear(self):
        self.positive.clear()
        self.negative.clear()

    def complement(self):
        self.positive, self.negative = self.negative, self.positive
