#!/usr/bin/env python
#
# Copyright (c), 2018-2023, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import unittest
import io
import sys
import xml.etree.ElementTree as ElementTree

try:
    import lxml.etree as lxml_etree
except ImportError:
    lxml_etree = None

from elementpath.tree_builders import build_node_tree, \
    build_lxml_node_tree
from elementpath.xpath_nodes import ElementNode, \
    DocumentNode, TextNode, CommentNode, ProcessingInstructionNode


XML_DATA = """\
<?xml version='1.0' encoding='UTF8'?>
<?xml-model type="application/xml"?>
<!-- Document comment -->
<root xmlns:tns="http://elementpath.test/ns">
    <!-- Root comment -->
    <child1>
        child1 text1
        <!-- Child 1 comment -->
        <elem1 a1="value1"/>
        <elem2 a2="value2"/>
        child1 text2
    </child1>
    <child2/>
    <tns:other/>
</root>
"""


class TreeBuildersTest(unittest.TestCase):
    namespaces = {'tns': "http://elementpath.test/ns"}

    def test_build_node_tree_with_element(self):
        root = ElementTree.XML(XML_DATA)
        node = build_node_tree(root, self.namespaces)

        self.assertIsInstance(node, ElementNode)
        self.assertEqual(len(node.children), 7)
        self.assertIsInstance(node.children[0], TextNode)
        self.assertIsInstance(node.children[1], ElementNode)
        self.assertIsInstance(node.children[2], TextNode)
        self.assertIsInstance(node.children[3], ElementNode)
        self.assertIsInstance(node.children[4], TextNode)
        self.assertIsInstance(node.children[5], ElementNode)
        self.assertIsInstance(node.children[6], TextNode)

    def test_build_node_tree_with_element_tree(self):
        root = ElementTree.parse(io.StringIO(XML_DATA))
        node = build_node_tree(root, self.namespaces)

        self.assertIsInstance(node, DocumentNode)
        self.assertEqual(node.position, 1)
        self.assertEqual(len(node.children), 1)

        self.assertIsInstance(node[0], ElementNode)
        self.assertEqual(node[0].position, 2)
        self.assertEqual(len(node[0].children), 7)
        self.assertIsInstance(node[0].children[0], TextNode)
        self.assertIsInstance(node[0].children[1], ElementNode)
        self.assertIsInstance(node[0].children[2], TextNode)
        self.assertIsInstance(node[0].children[3], ElementNode)
        self.assertIsInstance(node[0].children[4], TextNode)
        self.assertIsInstance(node[0].children[5], ElementNode)
        self.assertIsInstance(node[0].children[6], TextNode)

    @unittest.skipIf(sys.version_info <= (3, 8),
                     "Comments not available in ElementTree")
    def test_build_node_tree_with_comments(self):
        parser = ElementTree.XMLParser(
            target=ElementTree.TreeBuilder(
                insert_comments=True, insert_pis=True
            )
        )
        root = ElementTree.XML(XML_DATA, parser=parser)
        node = build_node_tree(root, self.namespaces)
        self.assertIsInstance(node, ElementNode)

        self.assertEqual(len(node.children), 9)
        self.assertIsInstance(node.children[0], TextNode)
        self.assertIsInstance(node.children[1], CommentNode)
        self.assertIsInstance(node.children[2], TextNode)
        self.assertIsInstance(node.children[3], ElementNode)
        self.assertIsInstance(node.children[4], TextNode)
        self.assertIsInstance(node.children[5], ElementNode)
        self.assertIsInstance(node.children[6], TextNode)
        self.assertIsInstance(node.children[5], ElementNode)
        self.assertIsInstance(node.children[6], TextNode)

    @unittest.skipIf(lxml_etree is None, "lxml library is not installed")
    def test_build_lxml_node_tree_with_element(self):
        root = lxml_etree.XML(XML_DATA.encode('utf-8'))
        node = build_lxml_node_tree(root)

        self.assertIsInstance(node, DocumentNode)
        self.assertEqual(node.position, 0)
        self.assertIsNotNone(node.document)
        self.assertEqual(len(node.children), 3)
        self.assertIsInstance(node.children[0], ProcessingInstructionNode)
        self.assertIsInstance(node.children[1], CommentNode)
        self.assertIsInstance(node.children[2], ElementNode)

        self.assertIsInstance(node[2], ElementNode)
        self.assertEqual(node[2].position, 3)
        self.assertEqual(len(node[2].children), 9)
        self.assertIsInstance(node[2].children[0], TextNode)
        self.assertIsInstance(node[2].children[1], CommentNode)
        self.assertIsInstance(node[2].children[2], TextNode)
        self.assertIsInstance(node[2].children[3], ElementNode)
        self.assertIsInstance(node[2].children[4], TextNode)
        self.assertIsInstance(node[2].children[5], ElementNode)
        self.assertIsInstance(node[2].children[6], TextNode)
        self.assertIsInstance(node[2].children[5], ElementNode)
        self.assertIsInstance(node[2].children[6], TextNode)

        node = build_lxml_node_tree(root[1])
        self.assertIsInstance(node, ElementNode)
        self.assertEqual(len(node.children), 7)
        self.assertIsInstance(node.children[0], TextNode)
        self.assertIsInstance(node.children[1], CommentNode)
        self.assertIsInstance(node.children[2], TextNode)
        self.assertIsInstance(node.children[3], ElementNode)
        self.assertIsInstance(node.children[4], TextNode)
        self.assertIsInstance(node.children[5], ElementNode)
        self.assertIsInstance(node.children[6], TextNode)

    @unittest.skipIf(lxml_etree is None, "lxml library is not installed")
    def test_build_lxml_node_tree_with_element_tree(self):
        root = lxml_etree.parse(io.BytesIO(XML_DATA.encode('utf-8')))
        node = build_lxml_node_tree(root)

        self.assertIsInstance(node, DocumentNode)
        self.assertEqual(node.position, 1)
        self.assertIs(node.document, root)
        self.assertEqual(len(node.children), 3)
        self.assertIsInstance(node.children[0], ProcessingInstructionNode)
        self.assertIsInstance(node.children[1], CommentNode)
        self.assertIsInstance(node.children[2], ElementNode)

        self.assertIsInstance(node[2], ElementNode)
        self.assertEqual(node[2].position, 4)
        self.assertEqual(len(node[2].children), 9)
        self.assertIsInstance(node[2].children[0], TextNode)
        self.assertIsInstance(node[2].children[1], CommentNode)
        self.assertIsInstance(node[2].children[2], TextNode)
        self.assertIsInstance(node[2].children[3], ElementNode)
        self.assertIsInstance(node[2].children[4], TextNode)
        self.assertIsInstance(node[2].children[5], ElementNode)
        self.assertIsInstance(node[2].children[6], TextNode)
        self.assertIsInstance(node[2].children[5], ElementNode)
        self.assertIsInstance(node[2].children[6], TextNode)


if __name__ == '__main__':
    unittest.main()
