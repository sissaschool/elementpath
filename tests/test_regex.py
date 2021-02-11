#!/usr/bin/env python
#
# Copyright (c), 2016-2021, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""
This module runs tests on XML Schema regular expressions.
"""
import unittest
import sys
import re
import string
from itertools import chain
from unicodedata import category

from elementpath.regex import RegexError, CharacterClass, translate_pattern
from elementpath.regex.codepoints import get_code_point_range
from elementpath.regex.unicode_subsets import code_point_repr, \
    iterparse_character_subset, iter_code_points, UnicodeSubset, \
    UNICODE_CATEGORIES


class TestCodePoints(unittest.TestCase):

    def test_iter_code_points(self):
        self.assertEqual(list(iter_code_points([10, 20, 11, 12, 25, (9, 21), 21])), [(9, 22), 25])
        self.assertEqual(list(iter_code_points([10, 20, 11, 12, 25, (9, 20), 21])), [(9, 22), 25])
        self.assertEqual(list(iter_code_points({2, 120, 121, (150, 260)})),
                         [2, (120, 122), (150, 260)])
        self.assertEqual(
            list(iter_code_points([10, 20, (10, 22), 11, 12, 25, 8, (9, 20), 21, 22, 9, 0])),
            [0, (8, 23), 25]
        )
        self.assertEqual(
            list(e for e in iter_code_points([10, 20, 11, 12, 25, (9, 21)], reverse=True)),
            [25, (9, 21)]
        )
        self.assertEqual(
            list(iter_code_points([10, 20, (10, 22), 11, 12, 25, 8, (9, 20), 21, 22, 9, 0],
                                  reverse=True)),
            [25, (8, 23), 0]
        )

    def test_get_code_point_range(self):
        self.assertEqual(get_code_point_range(97), (97, 98))
        self.assertEqual(get_code_point_range((97, 100)), (97, 100))
        self.assertEqual(get_code_point_range([97, 100]), [97, 100])

        self.assertIsNone(get_code_point_range(-1))
        self.assertIsNone(get_code_point_range(sys.maxunicode + 1))
        self.assertIsNone(get_code_point_range((-1, 100)))
        self.assertIsNone(get_code_point_range((97, sys.maxunicode + 2)))
        self.assertIsNone(get_code_point_range(97.0))
        self.assertIsNone(get_code_point_range((97.0, 100)))


class TestParseCharacterSubset(unittest.TestCase):

    def test_expand_ranges(self):
        self.assertListEqual(
            list(iterparse_character_subset('a-e', expand_ranges=True)),
            [ord('a'), ord('b'), ord('c'), ord('d'), ord('e')]
        )

    def test_backslash_character(self):
        self.assertListEqual(list(iterparse_character_subset('\\')), [ord('\\')])
        self.assertListEqual(list(iterparse_character_subset('2-\\')),
                             [(ord('2'), ord('\\') + 1)])
        self.assertListEqual(list(iterparse_character_subset('2-\\\\')),
                             [(ord('2'), ord('\\') + 1), ord('\\')])
        self.assertListEqual(list(iterparse_character_subset('2-\\x')),
                             [(ord('2'), ord('\\') + 1), ord('x')])
        self.assertListEqual(list(iterparse_character_subset('2-\\a-x')),
                             [(ord('2'), ord('\\') + 1), (ord('a'), ord('x') + 1)])
        self.assertListEqual(list(iterparse_character_subset('2-\\{')),
                             [(ord('2'), ord('{') + 1)])

    def test_backslash_escapes(self):
        self.assertListEqual(list(iterparse_character_subset('\\{')), [ord('{')])
        self.assertListEqual(list(iterparse_character_subset('\\(')), [ord('(')])
        self.assertListEqual(list(iterparse_character_subset('\\a')), [ord('\\'), ord('a')])

    def test_square_brackets(self):
        self.assertListEqual(list(iterparse_character_subset('\\[')), [ord('[')])
        self.assertListEqual(list(iterparse_character_subset('[')), [ord('[')])

        with self.assertRaises(RegexError) as ctx:
            list(iterparse_character_subset('[ '))
        self.assertIn("bad character '['", str(ctx.exception))

        with self.assertRaises(RegexError) as ctx:
            list(iterparse_character_subset('x['))
        self.assertIn("bad character '['", str(ctx.exception))

        self.assertListEqual(list(iterparse_character_subset('\\]')), [ord(']')])
        self.assertListEqual(list(iterparse_character_subset(']')), [ord(']')])

        with self.assertRaises(RegexError) as ctx:
            list(iterparse_character_subset('].'))
        self.assertIn("bad character ']'", str(ctx.exception))

        with self.assertRaises(RegexError) as ctx:
            list(iterparse_character_subset('8['))
        self.assertIn("bad character '['", str(ctx.exception))

    def test_character_range(self):
        self.assertListEqual(list(iterparse_character_subset('A-z')),
                             [(ord('A'), ord('z') + 1)])
        self.assertListEqual(list(iterparse_character_subset('\\[-z')),
                             [(ord('['), ord('z') + 1)])

    def test_bad_character_range(self):
        with self.assertRaises(RegexError) as ctx:
            list(iterparse_character_subset('9-2'))
        self.assertIn('bad character range', str(ctx.exception))

        with self.assertRaises(RegexError) as ctx:
            list(iterparse_character_subset('2-\\s'))
        self.assertIn('bad character range', str(ctx.exception))

    def test_parse_multiple_ranges(self):
        self.assertListEqual(
            list(iterparse_character_subset('a-c-1-4x-z-7-9')),
            [(ord('a'), ord('c') + 1), ord('-'), (ord('1'), ord('4') + 1),
             (ord('x'), ord('z') + 1), ord('-'), (55, 58)]
        )


class TestUnicodeSubset(unittest.TestCase):

    def test_creation(self):
        subset = UnicodeSubset([(0, 9), 11, 12, (14, 32), (33, sys.maxunicode + 1)])
        self.assertEqual(subset, [(0, 9), 11, 12, (14, 32), (33, sys.maxunicode + 1)])
        self.assertEqual(UnicodeSubset('0-9'), [(48, 58)])
        self.assertEqual(UnicodeSubset('0-9:'), [(48, 59)])

        subset = UnicodeSubset('a-z')
        self.assertEqual(UnicodeSubset(subset), [(ord('a'), ord('z') + 1)])

    def test_repr(self):
        self.assertEqual(code_point_repr((ord('2'), ord('\\') + 1)), r'2-\\')

        subset = UnicodeSubset('a-z')
        self.assertEqual(repr(subset), "UnicodeSubset('a-z')")
        self.assertEqual(str(subset), "a-z")

        subset = UnicodeSubset((50, 90))
        subset.codepoints.append(sys.maxunicode + 10)  # Invalid subset
        self.assertRaises(ValueError, repr, subset)

    def test_modify(self):
        subset = UnicodeSubset()
        for cp in [50, 90, 10, 90]:
            subset.add(cp)
        self.assertEqual(subset, [10, 50, 90])
        self.assertRaises(ValueError, subset.add, -1)
        self.assertRaises(ValueError, subset.add, sys.maxunicode + 1)
        subset.add((100, 20001))
        subset.discard((100, 19001))
        self.assertEqual(subset, [10, 50, 90, (19001, 20001)])
        subset.add(0)
        subset.discard(1)
        self.assertEqual(subset, [0, 10, 50, 90, (19001, 20001)])
        subset.discard(0)
        self.assertEqual(subset, [10, 50, 90, (19001, 20001)])
        subset.discard((10, 100))
        self.assertEqual(subset, [(19001, 20001)])
        subset.add(20)
        subset.add(19)
        subset.add(30)
        subset.add([30, 33])
        subset.add(30000)
        subset.add(30001)
        self.assertEqual(subset, [(19, 21), (30, 33), (19001, 20001), (30000, 30002)])
        subset.add(22)
        subset.add(21)
        subset.add(22)
        self.assertEqual(subset, [(19, 22), 22, (30, 33), (19001, 20001), (30000, 30002)])
        subset.discard((90, 50000))
        self.assertEqual(subset, [(19, 22), 22, (30, 33)])
        subset.discard(21)
        subset.discard(19)
        self.assertEqual(subset, [20, 22, (30, 33)])
        subset.discard((0, 200))
        self.assertEqual(subset, [])

        with self.assertRaises(ValueError):
            subset.discard(None)
        with self.assertRaises(ValueError):
            subset.discard((10, 11, 12))

    def test_update_method(self):
        subset = UnicodeSubset()
        subset.update('\\\\')
        self.assertListEqual(subset.codepoints, [ord('\\')])
        subset.update('\\$')
        self.assertListEqual(subset.codepoints, [ord('$'), ord('\\')])

        subset.clear()
        subset.update('!--')
        self.assertListEqual(subset.codepoints, [(ord('!'), ord('-') + 1)])

        subset.clear()
        subset.update('!---')
        self.assertListEqual(subset.codepoints, [(ord('!'), ord('-') + 1)])

        subset.clear()
        subset.update('!--a')
        self.assertListEqual(subset.codepoints, [(ord('!'), ord('-') + 1), ord('a')])

        with self.assertRaises(RegexError):
            subset.update('[[')

    def test_difference_update_method(self):
        subset = UnicodeSubset('a-z')
        subset.difference_update('a-c')
        self.assertEqual(subset, UnicodeSubset('d-z'))

        subset = UnicodeSubset('a-z')
        subset.difference_update([(ord('a'), ord('c') + 1)])
        self.assertEqual(subset, UnicodeSubset('d-z'))

    def test_iterate(self):
        subset = UnicodeSubset('a-d')
        self.assertListEqual(list(iter(subset)), [ord('a'), ord('b'), ord('c'), ord('d')])
        self.assertListEqual(list(subset.iter_characters()), ['a', 'b', 'c', 'd'])

    def test_reversed(self):
        subset = UnicodeSubset('0-9ax')
        self.assertEqual(list(reversed(subset)),
                         [ord('x'), ord('a'), ord('9'), 56, 55, 54, 53, 52, 51, 50, 49, 48])

    def test_in_operator(self):
        subset = UnicodeSubset('0-9a-z')

        self.assertIn('a', subset)
        self.assertIn(ord('a'), subset)
        self.assertIn(ord('z'), subset)

        self.assertNotIn('/', subset)
        self.assertNotIn('A', subset)
        self.assertNotIn(ord('A'), subset)
        self.assertNotIn(ord('}'), subset)
        self.assertNotIn(float(ord('a')), subset)

        self.assertNotIn('.', subset)
        subset.update('.')
        self.assertIn('.', subset)
        self.assertNotIn('/', subset)
        self.assertNotIn('-', subset)

    def test_complement(self):
        subset = UnicodeSubset((50, 90, 10, 90))
        self.assertEqual(list(subset.complement()),
                         [(0, 10), (11, 50), (51, 90), (91, sys.maxunicode + 1)])
        subset.add(11)
        self.assertEqual(list(subset.complement()),
                         [(0, 10), (12, 50), (51, 90), (91, sys.maxunicode + 1)])
        subset.add((0, 10))
        self.assertEqual(list(subset.complement()), [(12, 50), (51, 90), (91, sys.maxunicode + 1)])

        s1 = UnicodeSubset(chain(
            UNICODE_CATEGORIES['L'].codepoints,
            UNICODE_CATEGORIES['M'].codepoints,
            UNICODE_CATEGORIES['N'].codepoints,
            UNICODE_CATEGORIES['S'].codepoints
        ))
        s2 = UnicodeSubset(chain(
            UNICODE_CATEGORIES['C'].codepoints,
            UNICODE_CATEGORIES['P'].codepoints,
            UNICODE_CATEGORIES['Z'].codepoints
        ))
        self.assertEqual(s1.codepoints, UnicodeSubset(s2.complement()).codepoints)

        subset = UnicodeSubset((50, 90))
        subset.codepoints.append(70)  # Invalid subset (unordered)
        with self.assertRaises(ValueError) as ctx:
            list(subset.complement())
        self.assertEqual(
            str(ctx.exception), "unordered code points found in UnicodeSubset('2ZF')")

        subset = UnicodeSubset((sys.maxunicode - 1,))
        self.assertEqual(list(subset.complement()), [(0, sys.maxunicode - 1), sys.maxunicode])

    def test_equality(self):
        self.assertFalse(UnicodeSubset() == 0.0)
        self.assertEqual(UnicodeSubset('a-z'), UnicodeSubset('a-kl-z'))

    def test_union_and_intersection(self):
        s1 = UnicodeSubset([50, (90, 200), 10])
        s2 = UnicodeSubset([10, 51, (89, 150), 90])
        self.assertEqual(s1 | s2, [10, (50, 52), (89, 200)])
        self.assertEqual(s1 & s2, [10, (90, 150)])

        subset = UnicodeSubset('a-z')
        subset |= UnicodeSubset('A-Zfx')
        self.assertEqual(subset, UnicodeSubset('A-Za-z'))
        subset |= '0-9'
        self.assertEqual(subset, UnicodeSubset('0-9A-Za-z'))
        subset |= [ord('{'), ord('}')]
        self.assertEqual(subset, UnicodeSubset('0-9A-Za-z{}'))

        subset = UnicodeSubset('a-z')
        subset &= UnicodeSubset('A-Zfx')
        self.assertEqual(subset, UnicodeSubset('fx'))
        subset &= 'xyz'
        self.assertEqual(subset, UnicodeSubset('x'))

        with self.assertRaises(TypeError) as ctx:
            subset = UnicodeSubset('a-z')
            subset |= False
        self.assertIn('unsupported operand type', str(ctx.exception))

        with self.assertRaises(TypeError) as ctx:
            subset = UnicodeSubset('a-z')
            subset &= False
        self.assertIn('unsupported operand type', str(ctx.exception))

    def test_max_and_min(self):
        s1 = UnicodeSubset([10, 51, (89, 151), 90])
        s2 = UnicodeSubset([0, 2, (80, 201), 10000])
        s3 = UnicodeSubset([1])
        self.assertEqual((min(s1), max(s1)), (10, 150))
        self.assertEqual((min(s2), max(s2)), (0, 10000))
        self.assertEqual((min(s3), max(s3)), (1, 1))

    def test_subtraction(self):
        subset = UnicodeSubset([0, 2, (80, 200), 10000])
        self.assertEqual(subset - {2, 120, 121, (150, 260)}, [0, (80, 120), (122, 150), 10000])

        subset = UnicodeSubset('a-z')
        subset -= UnicodeSubset('a-c')
        self.assertEqual(subset, UnicodeSubset('d-z'))

        subset = UnicodeSubset('a-z')
        subset -= 'a-c'
        self.assertEqual(subset, UnicodeSubset('d-z'))

        with self.assertRaises(TypeError) as ctx:
            subset = UnicodeSubset('a-z')
            subset -= False
        self.assertIn('unsupported operand type', str(ctx.exception))

    def test_xor(self):
        subset = UnicodeSubset('a-z')
        subset ^= subset
        self.assertEqual(subset, UnicodeSubset())

        subset = UnicodeSubset('a-z')
        subset ^= UnicodeSubset('a-c')
        self.assertEqual(subset, UnicodeSubset('d-z'))

        subset = UnicodeSubset('a-z')
        subset ^= 'a-f'
        self.assertEqual(subset, UnicodeSubset('g-z'))

        with self.assertRaises(TypeError) as ctx:
            subset = UnicodeSubset('a-z')
            subset ^= False
        self.assertIn('unsupported operand type', str(ctx.exception))

        subset = UnicodeSubset('a-z')
        subset ^= 'A-Za-f'
        self.assertEqual(subset, UnicodeSubset('A-Zg-z'))


class TestCharacterClass(unittest.TestCase):

    def test_char_class_init(self):
        char_class = CharacterClass()
        self.assertEqual(char_class.positive, [])
        self.assertEqual(char_class.negative, [])

        char_class = CharacterClass('a-z')
        self.assertEqual(char_class.positive, [(97, 123)])
        self.assertEqual(char_class.negative, [])

    def test_char_class_repr(self):
        char_class = CharacterClass('a-z')
        self.assertEqual(repr(char_class), 'CharacterClass([a-z])')
        char_class.complement()
        self.assertEqual(repr(char_class), 'CharacterClass([^a-z])')

    def test_char_class_split(self):
        self.assertListEqual(CharacterClass._re_char_set.split(r'2-\\'), [r'2-\\'])

    def test_complement(self):
        char_class = CharacterClass('a-z')
        self.assertListEqual(char_class.positive.codepoints, [(97, 123)])
        self.assertListEqual(char_class.negative.codepoints, [])

        char_class.complement()
        self.assertListEqual(char_class.positive.codepoints, [])
        self.assertListEqual(char_class.negative.codepoints, [(97, 123)])
        self.assertEqual(str(char_class), '[^a-z]')

        char_class = CharacterClass()
        char_class.complement()
        self.assertEqual(len(char_class), sys.maxunicode + 1)

    def test_isub_operator(self):
        char_class = CharacterClass('A-Za-z')
        char_class -= CharacterClass('a-z')
        self.assertEqual(str(char_class), '[A-Z]')

        char_class = CharacterClass('a-z')
        other = CharacterClass('A-Za-c')
        other.complement()
        char_class -= other
        self.assertEqual(str(char_class), '[a-c]')

        char_class = CharacterClass('a-z')
        other = CharacterClass('A-Za-c')
        other.complement()
        other.add('b')
        char_class -= other
        self.assertEqual(str(char_class), '[ac]')

        char_class = CharacterClass('a-c')
        char_class.complement()
        other = CharacterClass('a-z')
        other.complement()
        char_class -= other
        self.assertEqual(str(char_class), '[d-z]')

    def test_in_operator(self):
        char_class = CharacterClass('A-Za-z')
        self.assertIn(100, char_class)
        self.assertIn('d', char_class)
        self.assertNotIn(49, char_class)
        self.assertNotIn('1', char_class)

        char_class.complement()
        self.assertNotIn(100, char_class)
        self.assertNotIn('d', char_class)
        self.assertIn(49, char_class)
        self.assertIn('1', char_class)

    def test_iterate(self):
        char_class = CharacterClass('A-Za-z')
        self.assertEqual(''.join(chr(c) for c in char_class),
                         string.ascii_uppercase + string.ascii_lowercase)

        char_class.complement()
        self.assertEqual(len(''.join(chr(c) for c in char_class)),
                         sys.maxunicode + 1 - len(string.ascii_letters))

    def test_length(self):
        char_class = CharacterClass('0-9A-Z')
        self.assertListEqual(char_class.positive.codepoints, [(48, 58), (65, 91)])
        self.assertListEqual(char_class.negative.codepoints, [])
        self.assertEqual(len(char_class), 36)

        char_class.complement()
        self.assertListEqual(char_class.positive.codepoints, [])
        self.assertListEqual(char_class.negative.codepoints, [(48, 58), (65, 91)])
        self.assertEqual(len(char_class), sys.maxunicode + 1 - 36)

        char_class.add('k-m')
        self.assertListEqual(char_class.positive.codepoints, [(107, 110)])
        self.assertListEqual(char_class.negative.codepoints, [(48, 58), (65, 91)])
        self.assertEqual(str(char_class), '[\x00-/:-@\\[-\U0010ffffk-m]')
        self.assertEqual(len(char_class), sys.maxunicode + 1 - 36)

        char_class.add('K-M')
        self.assertListEqual(char_class.positive.codepoints, [(75, 78), (107, 110)])
        self.assertListEqual(char_class.negative.codepoints, [(48, 58), (65, 91)])
        self.assertEqual(len(char_class), sys.maxunicode + 1 - 33)
        self.assertEqual(str(char_class), '[\x00-/:-@\\[-\U0010ffffK-Mk-m]')

        char_class.clear()
        self.assertListEqual(char_class.positive.codepoints, [])
        self.assertListEqual(char_class.negative.codepoints, [])
        self.assertEqual(len(char_class), 0)

    def test_add(self):
        char_class = CharacterClass()
        self.assertListEqual(char_class.positive.codepoints, [])
        self.assertListEqual(char_class.negative.codepoints, [])
        self.assertEqual(len(char_class), 0)

        char_class.add('0-9')
        self.assertListEqual(char_class.positive.codepoints, [(48, 58)])
        self.assertListEqual(char_class.negative.codepoints, [])
        self.assertEqual(len(char_class), 10)

        char_class.add(r'\p{Nd}')
        self.assertEqual(len(char_class), 630)

        with self.assertRaises(RegexError):
            char_class.add(r'\p{}')

        with self.assertRaises(RegexError):
            char_class.add(r'\p{XYZ}')

        char_class.add(r'\P{Nd}')
        self.assertEqual(len(char_class), sys.maxunicode + 1)

        char_class = CharacterClass()
        char_class.add(r'\p{IsFoo}')

    def test_discard(self):
        char_class = CharacterClass('0-9')
        char_class.discard('6-9')
        self.assertListEqual(char_class.positive.codepoints, [(48, 54)])
        self.assertListEqual(char_class.negative.codepoints, [])
        self.assertEqual(len(char_class), 6)

        char_class.add(r'\p{Nd}')
        self.assertEqual(len(char_class), 630)

        char_class.discard(r'\p{Nd}')
        self.assertEqual(len(char_class), 0)

        with self.assertRaises(RegexError):
            char_class.discard(r'\p{}')

        with self.assertRaises(RegexError):
            char_class.discard(r'\p{XYZ}')

        char_class.add(r'\P{Nd}')
        self.assertEqual(len(char_class), sys.maxunicode + 1 - 630)

        char_class.discard(r'\P{Nd}')
        self.assertEqual(len(char_class), 0)

        char_class = CharacterClass('a-z')
        char_class.discard(r'\p{IsFoo}')
        self.assertEqual(len(char_class), 0)

        char_class = CharacterClass()
        char_class.complement()
        char_class.discard('\\n')
        self.assertListEqual(char_class.positive.codepoints, [(0, 10), (11, 1114112)])
        self.assertListEqual(char_class.negative.codepoints, [])
        self.assertEqual(len(char_class), sys.maxunicode)
        char_class.discard('\\s')
        self.assertListEqual(char_class.positive.codepoints,
                             [(0, 9), (11, 13), (14, 32), (33, 1114112)])
        self.assertEqual(len(char_class), sys.maxunicode - 3)
        char_class.discard('\\S')
        self.assertEqual(len(char_class), 0)

        char_class.clear()
        char_class.negative.codepoints.append(10)
        char_class.discard('\\s')
        self.assertListEqual(char_class.positive.codepoints, [])
        self.assertListEqual(char_class.negative.codepoints, [(9, 11), 13, 32])

        char_class = CharacterClass('\t')
        char_class.complement()
        self.assertListEqual(char_class.negative.codepoints, [9])
        char_class.discard('\\n')
        self.assertListEqual(char_class.positive.codepoints, [])
        self.assertListEqual(char_class.negative.codepoints, [(9, 11)])
        self.assertEqual(len(char_class), sys.maxunicode - 1)


class TestUnicodeCategories(unittest.TestCase):
    """
    Test the subsets of Unicode categories, mainly to check the loaded JSON file.
    """
    def test_unicode_categories(self):
        self.assertEqual(sum(len(v) for k, v in UNICODE_CATEGORIES.items() if len(k) > 1),
                         sys.maxunicode + 1)
        self.assertEqual(min([min(s) for s in UNICODE_CATEGORIES.values()]), 0)
        self.assertEqual(max([max(s) for s in UNICODE_CATEGORIES.values()]), sys.maxunicode)
        base_sets = [set(v) for k, v in UNICODE_CATEGORIES.items() if len(k) > 1]
        self.assertFalse(any(s.intersection(t) for s in base_sets for t in base_sets if s != t))

    @unittest.skipIf(not ((3, 8) <= sys.version_info < (3, 9)), "Test only for Python 3.8")
    def test_unicodedata_category(self):
        for key in UNICODE_CATEGORIES:
            for cp in UNICODE_CATEGORIES[key]:
                uc = category(chr(cp))
                if key == uc or len(key) == 1 and key == uc[0]:
                    continue
                self.assertTrue(
                    False, "Wrong category %r for code point %d (should be %r)." % (uc, cp, key)
                )


class TestPatterns(unittest.TestCase):
    """
    Test of specific regex patterns and their application.
    """
    def test_issue_079(self):
        # Do not escape special characters in character class
        regex = translate_pattern('[^\n\t]+', anchors=False)
        self.assertEqual(regex, '^([^\t\n]+)$(?!\\n\Z)')
        pattern = re.compile(regex)
        self.assertIsNone(pattern.search('first\tsecond\tthird'))
        self.assertEqual(pattern.search('first second third').group(0), 'first second third')

    def test_dot_wildcard(self):
        regex = translate_pattern('.+', anchors=False)
        self.assertEqual(regex, '^([^\r\n]+)$(?!\\n\Z)')
        pattern = re.compile(regex)
        self.assertIsNone(pattern.search('line1\rline2\r'))
        self.assertIsNone(pattern.search('line1\nline2'))
        self.assertIsNone(pattern.search(''))
        self.assertIsNotNone(pattern.search('\\'))
        self.assertEqual(pattern.search('abc').group(0), 'abc')

        regex = translate_pattern('.+T.+(Z|[+-].+)', anchors=False)
        self.assertEqual(regex, '^([^\r\n]+T[^\r\n]+(Z|[\\+\\-][^\r\n]+))$(?!\\n\Z)')
        pattern = re.compile(regex)
        self.assertEqual(pattern.search('12T0A3+36').group(0), '12T0A3+36')
        self.assertEqual(pattern.search('12T0A3Z').group(0), '12T0A3Z')
        self.assertIsNone(pattern.search(''))
        self.assertIsNone(pattern.search('12T0A3Z2'))

    def test_not_spaces(self):
        regex = translate_pattern(r"[\S' ']{1,10}", anchors=False)
        if sys.version_info >= (3,):
            self.assertEqual(
                regex, "^([\x00-\x08\x0b\x0c\x0e-\x1f!-\U0010ffff ']{1,10})$(?!\\n\Z)"
            )

        pattern = re.compile(regex)
        self.assertIsNone(pattern.search('alpha\r'))
        self.assertEqual(pattern.search('beta').group(0), 'beta')
        self.assertIsNone(pattern.search('beta\n'))
        self.assertIsNone(pattern.search('beta\n '))
        self.assertIsNone(pattern.search(''))
        self.assertIsNone(pattern.search('over the maximum length!'))
        self.assertIsNotNone(pattern.search('\\'))
        self.assertEqual(pattern.search('abc').group(0), 'abc')

    def test_category_escape(self):
        regex = translate_pattern('^\\p{IsBasicLatin}*$')
        self.assertEqual(regex, '^[\x00-\x7f]*$(?!\\n\\Z)')
        pattern = re.compile(regex)
        self.assertEqual(pattern.search('').group(0), '')
        self.assertEqual(pattern.search('e').group(0), 'e')
        self.assertIsNone(pattern.search('è'))

        regex = translate_pattern('^[\\p{IsBasicLatin}\\p{IsLatin-1Supplement}]*$')
        self.assertEqual(regex, '^[\x00-\xff]*$(?!\\n\\Z)')
        pattern = re.compile(regex)
        self.assertEqual(pattern.search('e').group(0), 'e')
        self.assertEqual(pattern.search('è').group(0), 'è')
        self.assertIsNone(pattern.search('Ĭ'))

    def test_digit_shortcut(self):
        regex = translate_pattern(r'\d{1,3}\.\d{1,2}', anchors=False)
        self.assertEqual(regex, r'^(\d{1,3}\.\d{1,2})$(?!\n\Z)')
        pattern = re.compile(regex)
        self.assertEqual(pattern.search('12.40').group(0), '12.40')
        self.assertEqual(pattern.search('867.00').group(0), '867.00')
        self.assertIsNone(pattern.search('867.00\n'))
        self.assertIsNone(pattern.search('867.00 '))
        self.assertIsNone(pattern.search('867.000'))
        self.assertIsNone(pattern.search('1867.0'))
        self.assertIsNone(pattern.search('a1.13'))

        regex = translate_pattern(r'[-+]?(\d+|\d+(\.\d+)?%)', anchors=False)
        self.assertEqual(regex, r'^([\+\-]?(\d+|\d+(\.\d+)?%))$(?!\n\Z)')
        pattern = re.compile(regex)
        self.assertEqual(pattern.search('78.8%').group(0), '78.8%')
        self.assertIsNone(pattern.search('867.00'))

    def test_character_class_reordering(self):
        regex = translate_pattern('[A-Z ]', anchors=False)
        self.assertEqual(regex, '^([ A-Z])$(?!\\n\Z)')
        pattern = re.compile(regex)
        self.assertEqual(pattern.search('A').group(0), 'A')
        self.assertEqual(pattern.search('Z').group(0), 'Z')
        self.assertEqual(pattern.search('Q').group(0), 'Q')
        self.assertEqual(pattern.search(' ').group(0), ' ')
        self.assertIsNone(pattern.search('  '))
        self.assertIsNone(pattern.search('AA'))

        regex = translate_pattern(r'[0-9.,DHMPRSTWYZ/:+\-]+', anchors=False)
        self.assertEqual(regex, r'^([\+-\-\.-:DHMPR-TWYZ]+)$(?!\n\Z)')
        pattern = re.compile(regex)
        self.assertEqual(pattern.search('12,40').group(0), '12,40')
        self.assertEqual(pattern.search('YYYY:MM:DD').group(0), 'YYYY:MM:DD')
        self.assertIsNone(pattern.search(''))
        self.assertIsNone(pattern.search('C'))

        regex = translate_pattern('[^: \n\r\t]+', anchors=False)
        self.assertEqual(regex, '^([^\t\n\r :]+)$(?!\\n\Z)')
        pattern = re.compile(regex)
        self.assertEqual(pattern.search('56,41').group(0), '56,41')
        self.assertIsNone(pattern.search('56,41\n'))
        self.assertIsNone(pattern.search('13:20'))

        regex = translate_pattern(r'^[A-Za-z0-9_\-]+(:[A-Za-z0-9_\-]+)?$')
        self.assertEqual(regex, r'^[\-0-9A-Z_a-z]+(:[\-0-9A-Z_a-z]+)?$(?!\n\Z)')
        pattern = re.compile(regex)
        self.assertEqual(pattern.search('fa9').group(0), 'fa9')
        self.assertIsNone(pattern.search('-x_1:_tZ-\n'))
        self.assertEqual(pattern.search('-x_1:_tZ-').group(0), '-x_1:_tZ-')
        self.assertIsNone(pattern.search(''))
        self.assertIsNone(pattern.search('+78'))

        regex = translate_pattern(r'[!%\^\*@~;#,|/]', anchors=False)
        self.assertEqual(regex, r'^([!#%\*,/;@\^\|~])$(?!\n\Z)')
        pattern = re.compile(regex)
        self.assertEqual(pattern.search('#').group(0), '#')
        self.assertEqual(pattern.search('!').group(0), '!')
        self.assertEqual(pattern.search('^').group(0), '^')
        self.assertEqual(pattern.search('|').group(0), '|')
        self.assertEqual(pattern.search('*').group(0), '*')
        self.assertIsNone(pattern.search('**'))
        self.assertIsNone(pattern.search('b'))
        self.assertIsNone(pattern.search(''))

        regex = translate_pattern('[A-Za-z]+:[A-Za-z][A-Za-z0-9\\-]+', anchors=False)
        self.assertEqual(regex, '^([A-Za-z]+:[A-Za-z][\\-0-9A-Za-z]+)$(?!\\n\Z)')
        pattern = re.compile(regex)
        self.assertEqual(pattern.search('zk:xy-9s').group(0), 'zk:xy-9s')
        self.assertIsNone(pattern.search('xx:y'))

    def test_occurrences_qualifiers(self):
        regex = translate_pattern('#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?', anchors=False)
        self.assertEqual(regex, r'^(#[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?)$(?!\n\Z)')
        pattern = re.compile(regex)
        self.assertEqual(pattern.search('#F3D').group(0), '#F3D')
        self.assertIsNone(pattern.search('#F3D\n'))
        self.assertEqual(pattern.search('#F3DA30').group(0), '#F3DA30')
        self.assertIsNone(pattern.search('#F3'))
        self.assertIsNone(pattern.search('#F3D '))
        self.assertIsNone(pattern.search('F3D'))
        self.assertIsNone(pattern.search(''))

    def test_or_operator(self):
        regex = translate_pattern('0|1', anchors=False)
        self.assertEqual(regex, r'^(0|1)$(?!\n\Z)')
        pattern = re.compile(regex)
        self.assertEqual(pattern.search('0').group(0), '0')
        self.assertEqual(pattern.search('1').group(0), '1')
        self.assertIsNone(pattern.search('1\n'))
        self.assertIsNone(pattern.search(''))
        self.assertIsNone(pattern.search('2'))
        self.assertIsNone(pattern.search('01'))
        self.assertIsNone(pattern.search('1\n '))

        regex = translate_pattern(r'\d+[%]|\d*\.\d+[%]', anchors=False)
        self.assertEqual(regex, r'^(\d+[%]|\d*\.\d+[%])$(?!\n\Z)')
        pattern = re.compile(regex)
        self.assertEqual(pattern.search('99%').group(0), '99%')
        self.assertEqual(pattern.search('99.9%').group(0), '99.9%')
        self.assertEqual(pattern.search('.90%').group(0), '.90%')
        self.assertIsNone(pattern.search('%'))
        self.assertIsNone(pattern.search('90.%'))

        regex = translate_pattern('([ -~]|\n|\r|\t)*', anchors=False)
        self.assertEqual(regex, '^(([ -~]|\n|\r|\t)*)$(?!\\n\Z)')
        pattern = re.compile(regex)
        self.assertEqual(pattern.search('ciao\t-~ ').group(0), 'ciao\t-~ ')
        self.assertEqual(pattern.search('\r\r').group(0), '\r\r')
        self.assertEqual(pattern.search('\n -.abc').group(0), '\n -.abc')
        self.assertIsNone(pattern.search('à'))
        self.assertIsNone(pattern.search('\t\n à'))

    def test_character_class_shortcuts(self):
        regex = translate_pattern(r"^[\i-[:]][\c-[:]]*$")
        pattern = re.compile(regex)
        self.assertEqual(pattern.search('x11').group(0), 'x11')
        self.assertIsNone(pattern.search('3a'))

        regex = translate_pattern(r"^\w*$")
        pattern = re.compile(regex)
        self.assertEqual(pattern.search('aA_x7').group(0), 'aA_x7')
        self.assertIsNone(pattern.search('.'))
        self.assertIsNone(pattern.search('-'))

        regex = translate_pattern(r"\W*", anchors=False)
        pattern = re.compile(regex)
        self.assertIsNone(pattern.search('aA_x7'))
        self.assertEqual(pattern.search('.-').group(0), '.-')

        regex = translate_pattern(r"^\d*$")
        pattern = re.compile(regex)
        self.assertEqual(pattern.search('6410').group(0), '6410')
        self.assertIsNone(pattern.search('a'))
        self.assertIsNone(pattern.search('-'))

        regex = translate_pattern(r"^\D*$")
        pattern = re.compile(regex)
        self.assertIsNone(pattern.search('6410'))
        self.assertEqual(pattern.search('a').group(0), 'a')
        self.assertEqual(pattern.search('-').group(0), '-')

        # Pull Request 114
        regex = translate_pattern(r"^[\w]{0,5}$")
        pattern = re.compile(regex)
        self.assertEqual(pattern.search('abc').group(0), 'abc')
        self.assertIsNone(pattern.search('.'))

        regex = translate_pattern(r"^[\W]{0,5}$")
        pattern = re.compile(regex)
        self.assertEqual(pattern.search('.').group(0), '.')
        self.assertIsNone(pattern.search('abc'))

    def test_character_class_range(self):
        regex = translate_pattern('[bc-]')
        self.assertEqual(regex, r'[\-bc]')

    def test_character_class_subtraction(self):
        regex = translate_pattern('[a-z-[aeiuo]]')
        self.assertEqual(regex, '[b-df-hj-np-tv-z]')

        # W3C XSD 1.1 test group RegexTest_422
        regex = translate_pattern('[^0-9-[a-zAE-Z]]')
        self.assertEqual(regex, '[^0-9AE-Za-z]')

        regex = translate_pattern(r'^([^0-9-[a-zAE-Z]]|[\w-[a-zAF-Z]])+$')
        pattern = re.compile(regex)
        self.assertIsNone(pattern.search('azBCDE1234567890BCDEFza'))
        self.assertEqual(pattern.search('BCD').group(0), 'BCD')

    def test_invalid_character_class(self):
        with self.assertRaises(RegexError) as ctx:
            translate_pattern('[[]')
        self.assertIn("invalid character '['", str(ctx.exception))

        with self.assertRaises(RegexError) as ctx:
            translate_pattern('ab]d')
        self.assertIn("unexpected meta character ']'", str(ctx.exception))

        with self.assertRaises(RegexError) as ctx:
            translate_pattern('[abc\\1]')
        self.assertIn("illegal back-reference in character class", str(ctx.exception))

        with self.assertRaises(RegexError) as ctx:
            translate_pattern('[--a]')
        self.assertIn("invalid character range '--'", str(ctx.exception))

        with self.assertRaises(RegexError) as ctx:
            translate_pattern('[a-z-[c-q')
        self.assertIn("unterminated character class", str(ctx.exception))

    def test_empty_character_class(self):
        regex = translate_pattern('[a-[a-f]]', anchors=False)
        self.assertEqual(regex, r'^([^\w\W])$(?!\n\Z)')
        self.assertRaises(RegexError, translate_pattern, '[]')

        self.assertEqual(translate_pattern(r'[\w-[\w]]'), r'[^\w\W]')
        self.assertEqual(translate_pattern(r'[\s-[\s]]'), r'[^\w\W]')
        self.assertEqual(translate_pattern(r'[\c-[\c]]'), r'[^\w\W]')
        self.assertEqual(translate_pattern(r'[\i-[\i]]'), r'[^\w\W]')
        self.assertEqual(translate_pattern('[a-[ab]]'), r'[^\w\W]')
        self.assertEqual(translate_pattern('[^a-[^a]]'), r'[^\w\W]')

    def test_back_references(self):
        self.assertEqual(translate_pattern('(a)\\1'), '(a)\\1')
        self.assertEqual(translate_pattern('(a)\\11'), '(a)\\1[1]')

        regex = translate_pattern('((((((((((((a))))))))))))\\11')
        self.assertEqual(regex, '((((((((((((a))))))))))))\\11')

        with self.assertRaises(RegexError) as ctx:
            translate_pattern('(a)\\1', back_references=False)
        self.assertIn("not allowed escape sequence", str(ctx.exception))

    def test_anchors(self):
        regex = translate_pattern('a^b')
        self.assertEqual(regex, 'a^b')

        regex = translate_pattern('a^b', anchors=False)
        self.assertEqual(regex, '^(a\\^b)$(?!\\n\Z)')

        regex = translate_pattern('ab$')
        self.assertEqual(regex, 'ab$(?!\\n\\Z)')

        regex = translate_pattern('ab$', anchors=False)
        self.assertEqual(regex, '^(ab\\$)$(?!\\n\Z)')

    def test_lazy_quantifiers(self):
        regex = translate_pattern('.*?')
        self.assertEqual(regex, '[^\r\n]*?')
        regex = translate_pattern('[a-z]{2,3}?')
        self.assertEqual(regex, '[a-z]{2,3}?')
        regex = translate_pattern('[a-z]*?')
        self.assertEqual(regex, '[a-z]*?')

        regex = translate_pattern('[a-z]*', lazy_quantifiers=False)
        self.assertEqual(regex, '[a-z]*')

        with self.assertRaises(RegexError) as ctx:
            translate_pattern('.*?', lazy_quantifiers=False)
        self.assertEqual(str(ctx.exception), "unexpected meta character '?' at position 2: '.*?'")

        with self.assertRaises(RegexError):
            translate_pattern('[a-z]{2,3}?', lazy_quantifiers=False)

        with self.assertRaises(RegexError):
            translate_pattern(r'[a-z]{2,3}?\s+', lazy_quantifiers=False)

        with self.assertRaises(RegexError):
            translate_pattern(r'[a-z]+?\s+', lazy_quantifiers=False)

    def test_invalid_quantifiers(self):
        with self.assertRaises(RegexError) as ctx:
            translate_pattern('{1}')
        self.assertIn("unexpected quantifier '{'", str(ctx.exception))

        with self.assertRaises(RegexError) as ctx:
            translate_pattern('.{1,2,3}')
        self.assertIn("invalid quantifier '{'", str(ctx.exception))

        with self.assertRaises(RegexError) as ctx:
            translate_pattern('*')
        self.assertIn("unexpected quantifier '*'", str(ctx.exception))

    def test_invalid_hyphen(self):
        with self.assertRaises(RegexError) as ctx:
            translate_pattern('[a-b-c]')
        self.assertIn("unescaped character '-' at position 4", str(ctx.exception))

        regex = translate_pattern('[a-b-c]', xsd_version='1.1')
        self.assertEqual(regex, '[\\-a-c]')
        self.assertEqual(translate_pattern('[-a-bc]'), regex)
        self.assertEqual(translate_pattern('[a-bc-]'), regex)

    def test_invalid_pattern_groups(self):
        with self.assertRaises(RegexError) as ctx:
            translate_pattern('(?:.*)')
        self.assertIn("invalid '(?...)' extension notation", str(ctx.exception))

        with self.assertRaises(RegexError) as ctx:
            translate_pattern('(.*))')
        self.assertIn("unbalanced parenthesis ')'", str(ctx.exception))

        with self.assertRaises(RegexError) as ctx:
            translate_pattern('((.*)')
        self.assertIn("unterminated subpattern in expression", str(ctx.exception))

    def test_verbose_patterns(self):
        regex = translate_pattern('\\  s*[a-z]+', flags=re.VERBOSE)
        self.assertEqual(regex, '\\s*[a-z]+')
        regex = translate_pattern('\\  p{  Is BasicLatin}+', flags=re.VERBOSE)
        self.assertEqual(regex, '[\x00-\x7f]+')

    def test_backslash_and_escapes(self):
        regex = translate_pattern('\\')
        self.assertEqual(regex, '\\')
        regex = translate_pattern('\\i')
        self.assertTrue(regex.startswith('[:A-Z_a-z'))
        regex = translate_pattern('\\I')
        self.assertTrue(regex.startswith('[^:A-Z_a-z'))
        regex = translate_pattern('\\c')
        self.assertTrue(regex.startswith('[-.0-9:A-Z_a-z'))
        regex = translate_pattern('\\C')
        self.assertTrue(regex.startswith('[^-.0-9:A-Z_a-z'))

    def test_block_escapes(self):
        regex = translate_pattern('\\p{P}')
        self.assertTrue(regex.startswith('[!-#%-'))
        regex = translate_pattern('\\P{P}')
        self.assertTrue(regex.startswith('[^!-#%-'))
        regex = translate_pattern('\\p{IsBasicLatin}')
        self.assertEqual(regex, '[\x00-\x7f]')
        regex = translate_pattern('\\p{IsBasicLatin}', flags=re.IGNORECASE)
        self.assertEqual(regex, '(?-i:[\x00-\x7f])')

        with self.assertRaises(RegexError) as ctx:
            translate_pattern('\\px')
        self.assertIn("a '{' expected", str(ctx.exception))

        with self.assertRaises(RegexError) as ctx:
            translate_pattern('\\p{Pu')
        self.assertIn("truncated unicode block escape", str(ctx.exception))

        with self.assertRaises(RegexError) as ctx:
            translate_pattern('\\p{Unknown}')
        self.assertIn("'Unknown' doesn't match to any Unicode category", str(ctx.exception))

        regex = translate_pattern('\\p{IsUnknown}', xsd_version='1.1')
        self.assertEqual(regex, '[\x00-\U0010fffe]')

        with self.assertRaises(RegexError) as ctx:
            translate_pattern('\\p{IsUnknown}')
        self.assertIn("'IsUnknown' doesn't match to any Unicode block", str(ctx.exception))

    def test_ending_newline_match(self):
        # Related with xmlschema's issue #223
        regex = translate_pattern(
            pattern=r"\d{2}:\d{2}:\d{6,7}",
            back_references=False,
            lazy_quantifiers=False,
            anchors=False
        )
        pattern = re.compile(regex)
        self.assertIsNotNone(pattern.match("38:36:000031"))
        self.assertIsNone(pattern.match("38:36:000031\n"))


if __name__ == '__main__':
    from xmlschema.testing import print_test_header

    print_test_header()
    unittest.main()
