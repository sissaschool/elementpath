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
from elementpath.xpath_collations import UNICODE_CODEPOINT_COLLATION, \
    HTML_ASCII_CASE_INSENSITIVE_COLLATION, XPathCollationManager


class XPathCollationsTest(unittest.TestCase):

    def test_context_manager_init(self):
        manager = XPathCollationManager(collation=UNICODE_CODEPOINT_COLLATION)
        self.assertIsInstance(manager, XPathCollationManager)

        with self.assertRaises(ElementPathError) as ctx:
            XPathCollationManager(collation=None)

        self.assertIn('XPTY0004', str(ctx.exception))
        self.assertIn('collation cannot be an empty sequence', str(ctx.exception))

        # Not raised in __init__()
        manager = XPathCollationManager(collation='unknown')
        self.assertIsInstance(manager, XPathCollationManager)

    def test_context_activation(self):
        with XPathCollationManager(UNICODE_CODEPOINT_COLLATION) as manager:
            self.assertFalse(manager.eq('a', 'A'))
        self.assertIsInstance(manager, XPathCollationManager)

        with self.assertRaises(ElementPathError) as ctx:
            with XPathCollationManager(collation='unknown'):
                pass

        self.assertIn('FOCH0002', str(ctx.exception))
        self.assertIn("Unsupported collation 'unknown'", str(ctx.exception))

    def test_html_ascii_case_insensitive_collation(self):
        with XPathCollationManager(HTML_ASCII_CASE_INSENSITIVE_COLLATION) as manager:
            self.assertTrue(manager.eq('a', 'A'))


if __name__ == '__main__':
    unittest.main()
