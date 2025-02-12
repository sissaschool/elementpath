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
from xml.etree import ElementTree

from elementpath import XPath2Parser
from elementpath.xpath_nodes import EtreeElementNode
from elementpath.tree_builders import get_node_tree
from elementpath.compare import deep_equal, deep_compare, get_key_function


class CompareTest(unittest.TestCase):

    def test_deep_equal_function(self):
        parser = XPath2Parser()
        token = parser.parse('true()')

        with self.assertRaises(TypeError):
            deep_equal([token], [1])

        with self.assertRaises(TypeError):
            deep_equal([1], [token])

        self.assertTrue(deep_equal([1], [1]))
        self.assertFalse(deep_equal([1], [2]))
        self.assertFalse(deep_equal([1, 1], [1]))
        self.assertFalse(deep_equal([1], [1, 1]))

        root = ElementTree.Element('root')
        elem = ElementTree.Element('elem')
        element = EtreeElementNode(elem)
        self.assertTrue(deep_equal([element], [element]))
        self.assertFalse(deep_equal([1], [element]))
        self.assertFalse(deep_equal([EtreeElementNode(root)], [element]))

        root = ElementTree.XML('<root a="1">text<child b="2"/>tail<child/></root>')
        element = get_node_tree(root)
        document = get_node_tree(ElementTree.ElementTree(root))
        self.assertTrue(deep_equal([element], [element]))
        self.assertTrue(deep_equal([document], [document]))

        root1 = ElementTree.XML('<root a="1">text<child b="2"/>tail</root>')
        element1 = get_node_tree(root1)
        document1 = get_node_tree(ElementTree.ElementTree(root1))
        self.assertFalse(deep_equal([element], [element1]))
        self.assertFalse(deep_equal([document], [document1]))

        root1 = ElementTree.XML('<root a="1"><child b="2"/>tail<child/></root>')
        element1 = get_node_tree(root1)
        document1 = get_node_tree(ElementTree.ElementTree(root1))
        self.assertFalse(deep_equal([element], [element1]))
        self.assertFalse(deep_equal([document], [document1]))

        root1 = ElementTree.XML('<root a="1">text<child b="3"/>tail<child/></root>')
        element1 = get_node_tree(root1)
        document1 = get_node_tree(ElementTree.ElementTree(root1))
        self.assertFalse(deep_equal([element], [element1]))
        self.assertFalse(deep_equal([document], [document1]))

    def test_deep_compare(self):
        parser = XPath2Parser()
        token = parser.parse('true()')

        with self.assertRaises(TypeError):
            deep_compare([token], [1])

        with self.assertRaises(TypeError):
            deep_compare([1], [token])

        self.assertEqual(deep_compare([1], [1]), 0)
        self.assertEqual(deep_compare([1], [2]), -1)
        self.assertEqual(deep_compare([1, 1], [1]), 1)
        self.assertEqual(deep_compare([1], [1, 1]), -1)

        root = ElementTree.Element('root')
        elem = ElementTree.Element('elem')
        element = EtreeElementNode(elem)
        self.assertEqual(deep_compare([element], [element]), 0)

        with self.assertRaises(TypeError):
            deep_compare([1], [element])

        self.assertEqual(deep_compare([EtreeElementNode(root)], [element]), 1)

        root = ElementTree.XML('<root a="1">text<child b="2"/>tail<child/></root>')
        element = get_node_tree(root)
        document = get_node_tree(ElementTree.ElementTree(root))
        self.assertEqual(deep_compare([element], [element]), 0)
        self.assertEqual(deep_compare([document], [document]), 0)

        root1 = ElementTree.XML('<root a="1">text<child b="2"/>tail</root>')
        element1 = get_node_tree(root1)
        document1 = get_node_tree(ElementTree.ElementTree(root1))
        self.assertEqual(deep_compare([element], [element1]), -1)
        self.assertEqual(deep_compare([document], [document1]), -1)

        root1 = ElementTree.XML('<root a="1"><child b="2"/>tail<child/></root>')
        element1 = get_node_tree(root1)
        document1 = get_node_tree(ElementTree.ElementTree(root1))
        self.assertEqual(deep_compare([element], [element1]), 1)
        self.assertEqual(deep_compare([document], [document1]), 1)

        root1 = ElementTree.XML('<root a="1">text<child b="3"/>tail<child/></root>')
        element1 = get_node_tree(root1)
        document1 = get_node_tree(ElementTree.ElementTree(root1))
        self.assertEqual(deep_compare([element], [element1]), -1)
        self.assertEqual(deep_compare([document], [document1]), -1)

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
