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

from elementpath.sequences import xlist, empty_sequence, \
    sequence_concat, sequence_count, iterate_sequence, XSequence


class ListSequencesTest(unittest.TestCase):

    def test_string_repr(self):
        self.assertEqual(repr(xlist([])), '[]')
        self.assertEqual(repr(xlist([1, 2, 3])), '[1, 2, 3]')
        self.assertEqual(repr(xlist((x for x in [1, 2, 3]))), '[1, 2, 3]')
        self.assertEqual(repr(xlist([1])), '[1]')

        self.assertEqual(str(xlist([1, 2, 3])), '[1, 2, 3]')
        self.assertEqual(str(xlist([1])), '[1]')
        self.assertEqual(str(xlist()), '[]')

        self.assertEqual(repr(xlist([1, 2, 3])), '[1, 2, 3]')
        self.assertEqual(repr(xlist([1])), '[1]')
        self.assertEqual(repr(xlist()), '[]')

    def test_empty_sequence(self):
        self.assertNotEqual(empty_sequence(), ())
        self.assertEqual(empty_sequence(), [])
        self.assertEqual(empty_sequence(), xlist())
        self.assertNotIsInstance(empty_sequence(), xlist)

    def test_sequence_concat(self):
        self.assertListEqual(sequence_concat([], []), [])
        self.assertListEqual(sequence_concat([1], []), [1])
        self.assertTrue(sequence_concat([1], []) == 1)
        self.assertListEqual(sequence_concat([], [4]), [4])
        self.assertListEqual(sequence_concat([1], [8]), [1, 8])

        self.assertNotIsInstance(sequence_concat([], []), xlist)
        self.assertIsInstance(sequence_concat([], [5]), xlist)
        self.assertNotIsInstance(sequence_concat([1], [8]), xlist)

    def test_count(self):
        self.assertEqual(sequence_count(['a', 'b', 'c']), 3)

    def test_iterate_sequence(self):
        def action(item, pos):
            yield item * pos

        self.assertEqual(iterate_sequence([1, 2, 3], action=action), [1, 4, 9])

        def action(item, pos):
            yield item
            yield item * pos

        self.assertEqual(iterate_sequence([1, 2, 3], action=action), [1, 1, 2, 4, 3, 9])


class XSequenceTest(unittest.TestCase):

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

    def test_sequence_count(self):
        self.assertEqual(XSequence.sequence_count(['a', 'b', 'c']), 3)

    def test_nested_sequence(self):
        self.assertEqual(list(iter(XSequence([]))), [])

        with self.assertRaises(TypeError):
            list(iter(XSequence([[], 8])))
        with self.assertRaises(TypeError):
            list(iter(XSequence([[], [], []])))
        with self.assertRaises(TypeError):
            list(iter(XSequence([[], 8, [9]])))

    def test_empty_sequence(self):
        self.assertEqual(XSequence.empty_sequence(), ())
        self.assertIsInstance(XSequence.empty_sequence(), XSequence)

    def test_sequence_concat(self):
        self.assertEqual(XSequence.sequence_concat([], []), [])
        self.assertIsInstance(XSequence.sequence_concat([], []), XSequence)

        result = XSequence.sequence_concat([90, ], [32])
        self.assertIsInstance(result, XSequence)
        self.assertEqual(empty_sequence(), [])

    def test_iterate_sequence(self):
        def action(item, pos):
            yield item * pos

        result = XSequence.iterate_sequence([1, 2, 3], action=action)
        self.assertEqual(result, [1, 4, 9])
        self.assertIsInstance(result, XSequence)

        def action(item, pos):
            yield item
            yield item * pos

        result = XSequence.iterate_sequence([1, 2, 3], action=action)
        self.assertEqual(result, [1, 1, 2, 4, 3, 9])
        self.assertIsInstance(result, XSequence)


if __name__ == '__main__':
    unittest.main()
