#!/usr/bin/env python
#
# Copyright (c), 2022, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import unittest

from elementpath.compare import deep_compare, get_key_function


class CompareTest(unittest.TestCase):

    def test_deep_compare(self):
        self.assertEqual(deep_compare([1], [1]), 0)

    def test_key_function(self):
        key_function = get_key_function()
        result = sorted([2, 1], key=key_function)
        self.assertListEqual(result, [1, 2])

        result = sorted([2, 1, 0], key=key_function)
        self.assertListEqual(result, [0, 1, 2])

        result = sorted([2, 10, 7], key=key_function)
        self.assertListEqual(result, [2, 7, 10])

        with self.assertRaises(TypeError) as cm:
            sorted(['2', 1, 0], key=key_function)
        self.assertIn('XPTY0004', str(cm.exception))

        result = sorted(['2', '10', '7'], key=key_function)
        self.assertListEqual(result, ['10', '2', '7'])


if __name__ == '__main__':
    unittest.main()
