#!/usr/bin/env python
#
# Copyright (c), 2018-2025, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import unittest

from elementpath.sequences import empty_sequence, XSequence


class XPathSequenceTest(unittest.TestCase):

    def test_string_repr(self):
        self.assertEqual(repr(XSequence([])), 'XSequence([])')
        self.assertEqual(repr(XSequence([1, 2, 3])), 'XSequence([1, 2, 3])')
        self.assertEqual(repr(XSequence((x for x in [1, 2, 3]))), 'XSequence([1, 2, 3])')
        self.assertEqual(repr(XSequence([1])), 'XSequence([1])')

        self.assertEqual(str(XSequence([1, 2, 3])), '(1, 2, 3)')
        self.assertEqual(str(XSequence([1])), '(1)')
        self.assertEqual(str(XSequence()), '()')

        self.assertEqual(repr(XSequence([1, 2, 3])), 'XSequence([1, 2, 3])')
        self.assertEqual(repr(XSequence([1])), 'XSequence([1])')
        self.assertEqual(repr(XSequence()), 'XSequence([])')

    def test_initialization(self):
        sequence = XSequence([1, 2, 3])
        self.assertEqual(sequence, [1, 2, 3])

    def test_comparison(self):
        self.assertNotEqual(empty_sequence(), ())
        self.assertEqual(empty_sequence(), [])
        self.assertNotEqual((), empty_sequence())
        self.assertEqual([], empty_sequence())
        self.assertNotEqual(empty_sequence(), 0)
        self.assertNotEqual(empty_sequence(), '')
        self.assertNotEqual(empty_sequence(), 1)

        self.assertEqual(XSequence([1]), 1)
        self.assertEqual(XSequence([1]), [1])
        self.assertEqual(XSequence([1]), 1)

    def test_concatenation(self):
        sequence = XSequence([1, 2, 3])
        self.assertEqual(sequence + [4], [1, 2, 3, 4])
        self.assertEqual([] + sequence, [1, 2, 3])
        self.assertEqual([-1, 0] + sequence, [-1, 0, 1, 2, 3])

        s1 = XSequence([1, 2, 3])
        s2 = XSequence([4, 5, 6])
        self.assertEqual(s1 + s2, [1, 2, 3, 4, 5, 6])
        self.assertEqual(s2 + s1, [4, 5, 6, 1, 2, 3])

    def test_nested_sequence(self):
        self.assertEqual(list(iter(XSequence([]))), [])

        # with self.assertRaises(TypeError):
        #     list(iter(XSequence([None, 8])))
        with self.assertRaises(TypeError):
            list(iter(XSequence([[], 8])))
        with self.assertRaises(TypeError):
            list(iter(XSequence([[], [], []])))
        with self.assertRaises(TypeError):
            list(iter(XSequence([[], 8, [9]])))


if __name__ == '__main__':
    unittest.main()
