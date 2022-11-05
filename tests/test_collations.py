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

from elementpath import ElementPathError
from elementpath.collations import UNICODE_CODEPOINT_COLLATION, \
    HTML_ASCII_CASE_INSENSITIVE_COLLATION, CollationManager


class CollationsTest(unittest.TestCase):

    def test_context_manager_init(self):
        manager = CollationManager(collation=UNICODE_CODEPOINT_COLLATION)
        self.assertIsInstance(manager, CollationManager)

        with self.assertRaises(ElementPathError) as ctx:
            CollationManager(collation=None)

        self.assertIn('XPTY0004', str(ctx.exception))
        self.assertIn('collation cannot be an empty sequence', str(ctx.exception))

        # Not raised in __init__()
        manager = CollationManager(collation='unknown')
        self.assertIsInstance(manager, CollationManager)

    def test_context_activation(self):
        with CollationManager(UNICODE_CODEPOINT_COLLATION) as manager:
            self.assertFalse(manager.eq('a', 'A'))
        self.assertIsInstance(manager, CollationManager)

        with self.assertRaises(ElementPathError) as ctx:
            with CollationManager(collation='unknown'):
                pass

        self.assertIn('FOCH0002', str(ctx.exception))
        self.assertIn("Unsupported collation 'unknown'", str(ctx.exception))

    def test_html_ascii_case_insensitive_collation(self):
        with CollationManager(HTML_ASCII_CASE_INSENSITIVE_COLLATION) as manager:
            self.assertTrue(manager.eq('a', 'A'))


if __name__ == '__main__':
    unittest.main()
