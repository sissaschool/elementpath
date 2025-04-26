#!/usr/bin/env python
#
# Copyright (c), 2025, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import os.path
import unittest
import pathlib

from elementpath import XPath2Parser, XPathContext
from elementpath.extras.pathnodes import PathElementNode, PathDocumentNode


class PathNodesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.path = pathlib.Path(__file__)

    def test_build(self):
        node = PathElementNode(self.path)
        self.assertIsInstance(node, PathElementNode)
        self.assertEqual(len(node.tree.elements), len(self.path.parts))
        self.assertIsInstance(node.tree.root_node, PathDocumentNode)

        for _ in node.parent.iter_descendants():
            pass
        self.assertGreater(len(node.tree.elements), 30)

    def test_build_fragment(self):
        node = PathElementNode(self.path, fragment=True)
        self.assertIsInstance(node, PathElementNode)
        self.assertEqual(len(node.tree.elements), 1)
        self.assertIsInstance(node.tree.root_node, PathElementNode)
        self.assertIs(node.tree.root_node, node)
        self.assertIsNone(node.parent)

    def test_attributes(self):
        node = PathElementNode(self.path, fragment=True)
        self.assertGreater(len(node.attributes), 7)

        for attr in node.attributes:
            self.assertEqual(attr.path, f'/{os.path.basename(__file__)}/@{attr.name}')

    def test_find_mtime(self):
        node = PathElementNode(self.path)
        ancestor = node.parent.parent
        assert ancestor is not None
        path = './/element(dist)/*'
        token = XPath2Parser(strict=False).parse(path)
        context = XPathContext(ancestor)

        for path in token.select(context):
            pass  # print(path)


if __name__ == '__main__':
    unittest.main()
