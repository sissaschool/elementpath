#!/usr/bin/env python
#
# Copyright (c), 2018-2020, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import unittest
import xml.etree.ElementTree as ElementTree

from elementpath import *


class XPathSelectorsTest(unittest.TestCase):
    root = ElementTree.XML('<author>Dickens</author>')

    def test_select_function(self):
        self.assertListEqual(select(self.root, 'text()'), ['Dickens'])
        self.assertEqual(select(self.root, '$a', variables={'a': 1}), 1)

        self.assertEqual(
            select(self.root, '$a', variables={'a': 1}, variable_types={'a': 'xs:decimal'}), 1
        )

    def test_iter_select_function(self):
        self.assertListEqual(list(iter_select(self.root, 'text()')), ['Dickens'])
        self.assertListEqual(list(iter_select(self.root, '$a', variables={'a': True})), [True])

    def test_selector_class(self):
        selector = Selector('/A')
        self.assertEqual(repr(selector), "Selector(path='/A', parser=XPath2Parser)")
        self.assertEqual(selector.namespaces, XPath2Parser.DEFAULT_NAMESPACES)

        selector = Selector('text()')
        self.assertListEqual(selector.select(self.root), ['Dickens'])
        self.assertListEqual(list(selector.iter_select(self.root)), ['Dickens'])

        selector = Selector('$a', variables={'a': 1})
        self.assertEqual(selector.select(self.root), 1)
        self.assertListEqual(list(selector.iter_select(self.root)), [1])

    def test_issue_001(self):
        selector = Selector("//FullPath[ends-with(., 'Temp')]")
        self.assertListEqual(selector.select(ElementTree.XML('<A/>')), [])
        self.assertListEqual(selector.select(ElementTree.XML('<FullPath/>')), [])
        root = ElementTree.XML('<FullPath>High Temp</FullPath>')
        self.assertListEqual(selector.select(root), [root])


if __name__ == '__main__':
    unittest.main()
