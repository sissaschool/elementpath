#
# Copyright (c), 2016-2020, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""
Parse and translate XML Schema regular expressions to Python regex syntax.
"""
import re
from sys import maxunicode

from .unicode_subsets import RegexError, UnicodeSubset, unicode_subset
from .character_classes import I_SHORTCUT_REPLACE, C_SHORTCUT_REPLACE, CharacterClass

_RE_HYPHENS = re.compile(r'(?<!\\)--')
_RE_QUANTIFIER = re.compile(r'{\d+(,(\d+)?)?}')
_RE_FORBIDDEN_ESCAPES = re.compile(
    r'(?<!\\)\\(U[0-9a-fA-F]{8}|u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|o{\d+}|\d+|A|Z|z|B|b|o)'
)


def get_python_pattern(pattern, back_references=True, lazy_quantifiers=True,
                       is_syntax=True, anchors=True):
    """
    Translates a pattern regex expression to a Python regex pattern.

    :param pattern: the source XML Schema regular expression.
    :param back_references: if `True` supports back-references and capturing groups.
    :param lazy_quantifiers: if `True` supports lazy quantifiers (*?, +?).
    :param is_syntax: if `True` supports 'Is' prefix on unicode scripts.
    :param anchors: if `True` supports ^ and $ anchors, otherwise anchors \
    are added at expression boundaries.
    """
    def parse_character_class():
        nonlocal pos
        nonlocal msg

        pos += 1
        if pattern[pos] == '^':
            pos += 1
            negative = True
        else:
            negative = False

        group_pos = pos
        while True:
            if pattern[pos] == '[':
                msg = "invalid character '[' at position {}: {!r}"
                raise RegexError(msg.format(pos, pattern))
            elif pattern[pos] == '\\':
                pos += 2
            elif pattern[pos] == ']' or pattern[pos:pos + 2] == '-[':
                if pos == group_pos:
                    msg = "empty character class at position {}: {!r}"
                    raise RegexError(msg.format(pos, pattern))

                if _RE_HYPHENS.search(pattern[group_pos:pos]) and pos - group_pos > 2:
                    msg = "invalid character range '--' at position {}: {!r}"
                    raise RegexError(msg.format(pos, pattern))

                char_class = CharacterClass(pattern[group_pos:pos], is_syntax)
                if negative:
                    char_class.complement()
                break
            else:
                pos += 1

        if pattern[pos] != ']':
            # Parse a group subtraction
            pos += 1
            subtracted_class = parse_character_class()
            pos += 1
            if pattern[pos] != ']':
                msg = "unterminated character group at position {}: {!r}"
                raise RegexError(msg.format(pos, pattern))
            char_class -= subtracted_class

        return char_class

    group_open_char = '(' if back_references else '(?:'
    regex = [] if anchors else ['^%s' % group_open_char]
    pos = 0
    pattern_len = len(pattern)
    nested_groups = 0

    match = _RE_FORBIDDEN_ESCAPES.search(pattern)
    if match:
        msg = "not allowed escape sequence {!r} at position {}: {!r}"
        raise RegexError(msg.format(match.group(), match.span()[0], pattern))

    while pos < pattern_len:
        ch = pattern[pos]
        if ch == '.':
            regex.append('[^\r\n]')
        elif ch in ('^', '$'):
            if not anchors:
                msg = "unexpected anchor {!r} at position {}: {!r}"
                raise RegexError(msg.format(ch, pos, pattern))
            regex.append(ch)
        elif ch == '[':
            try:
                char_group = parse_character_class()
            except IndexError:
                msg = "unterminated character group at position {}: {!r}"
                raise RegexError(msg.format(pos, pattern))
            else:
                char_group_repr = str(char_group)
                if char_group_repr == '[^]':
                    regex.append(r'[\w\W]')
                elif char_group_repr == '[]':
                    regex.append(r'[^\w\W]')
                else:
                    regex.append(char_group_repr)

        elif ch == '{':
            if pos == 0:
                msg = "unexpected quantifier {!r} at position {}: {!r}"
                raise RegexError(msg.format(ch, pos, pattern))

            match = _RE_QUANTIFIER.match(pattern[pos:])
            if match is None:
                msg = "invalid quantifier {!r} at position {}: {!r}"
                raise RegexError(msg.format(ch, pos, pattern))

            regex.append(match.group())
            pos += len(match.group())
            if pos < pattern_len and pattern[pos] in ('?', '+', '*'):
                msg = "unexpected meta character {!r} at position {}: {!r}"
                raise RegexError(msg.format(pattern[pos], pos, pattern))
            continue

        elif ch == '(':
            if pattern[pos:pos + 2] == '(?':
                msg = "invalid '(?...)' extension notation ad position {}: {!r}"
                raise RegexError(msg.format(pos, pattern))

            nested_groups += 1
            regex.append(group_open_char)

        elif ch == ']':
            msg = "unexpected meta character {!r} at position {}: {!r}"
            raise RegexError(msg.format(ch, pos, pattern))

        elif ch == ')':
            if nested_groups == 0:
                msg = "unbalanced parenthesis ')' at position {}: {!r}"
                raise RegexError(msg.format(pos, pattern))

            nested_groups -= 1
            regex.append(ch)

        elif ch in ('?', '+', '*'):
            if pos == 0:
                msg = "unexpected quantifier {!r} at position {}: {!r}"
                raise RegexError(msg.format(ch, pos, pattern))
            elif pos < pattern_len - 1 and pattern[pos + 1] in ('?', '+', '*', '{'):
                msg = "unexpected meta character {!r} at position {}: {!r}"
                raise RegexError(msg.format(pattern[pos + 1], pos + 1, pattern))

            regex.append(ch)

        elif ch == '\\':
            pos += 1
            if pos >= pattern_len:
                regex.append('\\')
            elif pattern[pos] == 'i':
                regex.append('[%s]' % I_SHORTCUT_REPLACE)
            elif pattern[pos] == 'I':
                regex.append('[^%s]' % I_SHORTCUT_REPLACE)
            elif pattern[pos] == 'c':
                regex.append('[%s]' % C_SHORTCUT_REPLACE)
            elif pattern[pos] == 'C':
                regex.append('[^%s]' % C_SHORTCUT_REPLACE)
            elif pattern[pos] in 'pP':
                block_pos = pos - 1
                try:
                    if pattern[pos + 1] != '{':
                        raise RegexError("a '{' expected, found %r." % pattern[pos + 1])
                    while pattern[pos] != '}':
                        pos += 1
                except (IndexError, ValueError):
                    msg = "truncated unicode block escape at position {}: {!r}"
                    raise RegexError(msg.format(block_pos, pattern))

                try:
                    p_shortcut_set = unicode_subset(pattern[block_pos + 3:pos])
                except RegexError:
                    if not is_syntax or not pattern[3:].startswith('Is'):
                        raise
                    regex.append('[%s]' % UnicodeSubset([(0, maxunicode)]))
                else:
                    if pattern[block_pos + 1] == 'p':
                        regex.append('[%s]' % p_shortcut_set)
                    else:
                        regex.append('[^%s]' % p_shortcut_set)
            else:
                regex.append('\\%s' % pattern[pos])
        else:
            regex.append(ch)
        pos += 1

    if nested_groups > 0:
        raise RegexError("unterminated subpattern in expression: %r" % pattern)

    if not anchors:
        regex.append(r')$')
    return ''.join(regex)
