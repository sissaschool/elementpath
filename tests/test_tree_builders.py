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
from textwrap import dedent

try:
    import lxml.etree as lxml_etree
except ImportError:
    lxml_etree = None

try:
    import xmlschema
except ImportError:
    xmlschema = None
else:
    xmlschema.XMLSchema.meta_schema.build()

from elementpath.tree_builders import build_node_tree, \
    build_lxml_node_tree, build_schema_node_tree
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
        <elem1 xmlns:xml="http://www.w3.org/XML/1998/namespace" a1="value1"/>
        <elem2 a2="value2"/>
        child1 text2
    </child1>
    <child2/>
    <tns:other/>
    <?PI-target PI content?>
</root>
<?xml-model type="application/xml"?>
<!-- Document comment 2 -->
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

        for k, node in enumerate(node.iter(), start=1):
            self.assertEqual(k, node.position, msg=node)

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

        for k, node in enumerate(node.iter(), start=1):
            self.assertEqual(k, node.position, msg=node)

    @unittest.skipIf(sys.version_info <= (3, 8),
                     "Comments not available in ElementTree")
    def test_build_node_tree_with_comments_and_pis(self):
        parser = ElementTree.XMLParser(
            target=ElementTree.TreeBuilder(
                insert_comments=True, insert_pis=True
            )
        )
        root = ElementTree.XML(XML_DATA, parser=parser)
        node = build_node_tree(root, self.namespaces)
        self.assertIsInstance(node, ElementNode)

        self.assertEqual(len(node.children), 11)
        self.assertIsInstance(node.children[0], TextNode)
        self.assertIsInstance(node.children[1], CommentNode)
        self.assertIsInstance(node.children[2], TextNode)
        self.assertIsInstance(node.children[3], ElementNode)
        self.assertIsInstance(node.children[4], TextNode)
        self.assertIsInstance(node.children[5], ElementNode)
        self.assertIsInstance(node.children[6], TextNode)
        self.assertIsInstance(node.children[7], ElementNode)
        self.assertIsInstance(node.children[8], TextNode)
        self.assertIsInstance(node.children[9], ProcessingInstructionNode)
        self.assertIsInstance(node.children[10], TextNode)

        for k, node in enumerate(node.iter(), start=1):
            self.assertEqual(k, node.position, msg=node)

    @unittest.skipIf(lxml_etree is None, "lxml library is not installed")
    def test_build_lxml_node_tree_with_element(self):
        root = lxml_etree.XML(XML_DATA.encode('utf-8'))
        node = build_lxml_node_tree(root)

        self.assertIsInstance(node, DocumentNode)
        self.assertEqual(node.position, 1)
        self.assertIsNotNone(node.document)
        self.assertEqual(len(node.children), 5)
        self.assertIsInstance(node.children[0], ProcessingInstructionNode)
        self.assertIsInstance(node.children[1], CommentNode)
        self.assertIsInstance(node.children[2], ElementNode)
        self.assertIsInstance(node.children[3], ProcessingInstructionNode)
        self.assertIsInstance(node.children[4], CommentNode)

        self.assertIsInstance(node[2], ElementNode)
        self.assertEqual(node[2].position, 4)
        self.assertEqual(len(node[2].children), 11)
        self.assertIsInstance(node[2].children[0], TextNode)
        self.assertIsInstance(node[2].children[1], CommentNode)
        self.assertIsInstance(node[2].children[2], TextNode)
        self.assertIsInstance(node[2].children[3], ElementNode)
        self.assertIsInstance(node[2].children[4], TextNode)
        self.assertIsInstance(node[2].children[5], ElementNode)
        self.assertIsInstance(node[2].children[6], TextNode)
        self.assertIsInstance(node[2].children[5], ElementNode)
        self.assertIsInstance(node[2].children[6], TextNode)

        for k, node in enumerate(node.iter(), start=1):
            self.assertEqual(k, node.position, msg=node)

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

        for k, node in enumerate(node.iter(), start=1):
            self.assertEqual(k, node.position, msg=node)

    @unittest.skipIf(lxml_etree is None, "lxml library is not installed")
    def test_build_lxml_node_tree_with_element_tree(self):
        root = lxml_etree.parse(io.BytesIO(XML_DATA.encode('utf-8')))
        node = build_lxml_node_tree(root)

        self.assertIsInstance(node, DocumentNode)
        self.assertEqual(node.position, 1)
        self.assertIs(node.document, root)
        self.assertEqual(len(node.children), 5)
        self.assertIsInstance(node.children[0], ProcessingInstructionNode)
        self.assertIsInstance(node.children[1], CommentNode)
        self.assertIsInstance(node.children[2], ElementNode)
        self.assertIsInstance(node.children[3], ProcessingInstructionNode)
        self.assertIsInstance(node.children[4], CommentNode)

        self.assertIsInstance(node[2], ElementNode)
        self.assertEqual(node[2].position, 4)
        self.assertEqual(len(node[2].children), 11)
        self.assertIsInstance(node[2].children[0], TextNode)
        self.assertIsInstance(node[2].children[1], CommentNode)
        self.assertIsInstance(node[2].children[2], TextNode)
        self.assertIsInstance(node[2].children[3], ElementNode)
        self.assertIsInstance(node[2].children[4], TextNode)
        self.assertIsInstance(node[2].children[5], ElementNode)
        self.assertIsInstance(node[2].children[6], TextNode)
        self.assertIsInstance(node[2].children[5], ElementNode)
        self.assertIsInstance(node[2].children[6], TextNode)

        for k, node in enumerate(node.iter(), start=1):
            self.assertEqual(k, node.position, msg=node)

        root = lxml_etree.ElementTree()
        self.assertIsNone(root.getroot())
        node = build_lxml_node_tree(root)

        self.assertIsInstance(node, DocumentNode)
        self.assertEqual(node.position, 1)
        self.assertIs(node.document, root)
        self.assertEqual(len(node.children), 0)

        for k, node in enumerate(node.iter(), start=1):
            self.assertEqual(k, node.position, msg=node)

    @unittest.skipIf(xmlschema is None, "xmlschema library is not installed!")
    def test_build_schema_node_tree(self):
        schema = xmlschema.XMLSchema(dedent("""\n
            <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
                <xs:element name="root">
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element name="elem1"/>
                            <xs:element name="elem2"/>
                            <xs:element name="elem3"/>
                            <xs:element ref="root"/>
                        </xs:sequence>
                    </xs:complexType>
                </xs:element>
            </xs:schema>"""))

        root_node = build_schema_node_tree(schema)
        self.assertIs(root_node.elem, schema)
        self.assertIsInstance(root_node.elements, dict)

        for node in root_node.elements.values():
            self.assertIs(node.elements, root_node.elements)
        self.assertEqual(len(root_node.elements), 7)

        global_elements = []
        root_node = build_schema_node_tree(schema, global_elements=global_elements)
        self.assertIs(root_node.elem, schema)
        self.assertIn(root_node, global_elements)

        for node in root_node.elements.values():
            self.assertIs(node.elements, root_node.elements)
        self.assertEqual(len(root_node.elements), 7)

        root_node = build_schema_node_tree(schema.elements['root'])
        self.assertIs(root_node.elem, schema.elements['root'])

        self.assertIsInstance(root_node.elements, dict)
        for node in root_node.elements.values():
            self.assertIs(node.elements, root_node.elements)
        self.assertEqual(len(root_node.elements), 6)

    def test_document_order__issue_079(self):
        xml_source = '<A>10<B a="2" b="3">11</B>12<B a="2"/>13<B>14</B></A>'
        root = ElementTree.XML(xml_source)
        root_node = build_node_tree(root)

        for k, node in enumerate(root_node.iter(), start=1):
            self.assertEqual(k, node.position, msg=node)

        if lxml_etree is not None:
            root = lxml_etree.XML(xml_source)
            root_node = build_lxml_node_tree(root)

            for k, node in enumerate(root_node.iter(), start=1):
                self.assertEqual(k, node.position, msg=node)

        xml_source = '<A>10<B a="2" b="3"><C>11</C></B>12<B a="2"/>13<B>14</B></A>'
        root = ElementTree.XML(xml_source)
        root_node = build_node_tree(root)

        for k, node in enumerate(root_node.iter(), start=1):
            self.assertEqual(k, node.position, msg=node)

        if lxml_etree is not None:
            root = lxml_etree.XML(xml_source)
            root_node = build_lxml_node_tree(root)

            for k, node in enumerate(root_node.iter(), start=1):
                self.assertEqual(k, node.position, msg=node)


if __name__ == '__main__':
    unittest.main()
