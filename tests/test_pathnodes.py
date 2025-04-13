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
import unittest
import pathlib

from elementpath.extras.pathnodes import PathElementNode, PathDocumentNode, \
    build_path_node_tree


class PathNodesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.path = pathlib.Path(__file__)

    def test_build(self):
        node = build_path_node_tree(self.path)
        self.assertIsInstance(node, PathElementNode)
        self.assertEqual(len(node.tree.elements), len(self.path.parts))
        self.assertIsInstance(node.tree.root_node, PathDocumentNode)
        
        for _ in node.parent.iter_descendants():
            pass
        self.assertGreater(len(node.tree.elements), 30)


if __name__ == '__main__':
    unittest.main()
