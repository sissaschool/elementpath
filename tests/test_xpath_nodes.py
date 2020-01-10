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
import io
import xml.etree.ElementTree as ElementTree

from elementpath.xpath_nodes import AttributeNode, TextNode, TypedAttribute, \
    TypedElement, NamespaceNode, is_etree_element, elem_iter_strings, \
    etree_deep_equal, is_element_node, is_attribute_node, is_comment_node, \
    is_document_node, is_namespace_node, is_processing_instruction_node, \
    is_text_node, node_attributes, node_base_uri, node_document_uri, \
    node_children, node_is_id, node_is_idrefs, node_nilled, node_kind, node_name


class XPathNodesTest(unittest.TestCase):
    elem = ElementTree.XML('<node a1="10"/>')

    def test_is_etree_element_function(self):
        self.assertTrue(is_etree_element(self.elem))
        self.assertFalse(is_etree_element('text'))
        self.assertFalse(is_etree_element(None))

    def test_elem_iter_strings_function(self):
        root = ElementTree.XML('<A>text1\n<B1>text2</B1>tail1<B2/><B3><C1>text3</C1></B3>tail2</A>')
        result = ['text1\n', 'text2', 'tail1', 'tail2', 'text3']
        self.assertListEqual(list(elem_iter_strings(root)), result)
        self.assertListEqual(list(elem_iter_strings(TypedElement(root, 'text1'))), result)

    def test_etree_deep_equal_function(self):
        root = ElementTree.XML('<A><B1>10</B1><B2 max="20"/>end</A>')
        self.assertTrue(etree_deep_equal(root, root))

        elem = ElementTree.XML('<A><B1>11</B1><B2 max="20"/>end</A>')
        self.assertFalse(etree_deep_equal(root, elem))

        elem = ElementTree.XML('<A><B1>10</B1>30<B2 max="20"/>end</A>')
        self.assertFalse(etree_deep_equal(root, elem))

        elem = ElementTree.XML('<A xmlns:ns="tns"><B1>10</B1><B2 max="20"/>end</A>')
        self.assertTrue(etree_deep_equal(root, elem))

        elem = ElementTree.XML('<A><B1>10</B1><B2 max="20"><C1/></B2>end</A>')
        self.assertFalse(etree_deep_equal(root, elem))

    def test_is_element_node_function(self):
        elem = ElementTree.Element('alpha')
        empty_tag_elem = ElementTree.Element('')
        self.assertTrue(is_element_node(elem, '*'))
        self.assertFalse(is_element_node(empty_tag_elem, '*'))
        with self.assertRaises(ValueError):
            is_element_node(elem, '**')
        with self.assertRaises(ValueError):
            is_element_node(elem, '*:*:*')
        with self.assertRaises(ValueError):
            is_element_node(elem, 'foo:*')
        self.assertFalse(is_element_node(empty_tag_elem, 'foo:*'))
        self.assertFalse(is_element_node(elem, '{foo}*'))

    def test_is_attribute_node_function(self):
        attr = AttributeNode('a1', '10')
        self.assertTrue(is_attribute_node(attr, '*'))
        self.assertTrue(is_attribute_node(TypedAttribute(attr, 10), 'a1'))
        with self.assertRaises(ValueError):
            is_attribute_node(attr, '**')
        with self.assertRaises(ValueError):
            is_attribute_node(attr, '*:*:*')
        with self.assertRaises(ValueError):
            is_attribute_node(attr, 'foo:*')
        self.assertTrue(is_attribute_node(attr, '*:a1'))
        self.assertFalse(is_attribute_node(attr, '{foo}*'))
        self.assertTrue(is_attribute_node(AttributeNode('{foo}a1', '10'), '{foo}*'))

    def test_is_comment_node_function(self):
        comment = ElementTree.Comment('nothing important')
        self.assertTrue(is_comment_node(comment))
        self.assertFalse(is_comment_node(self.elem))

    def test_is_document_node_function(self):
        document = ElementTree.parse(io.StringIO('<A/>'))
        self.assertTrue(is_document_node(document))
        self.assertFalse(is_document_node(self.elem))

    def test_is_namespace_node_function(self):
        namespace = NamespaceNode('xs', 'http://www.w3.org/2001/XMLSchema')
        self.assertTrue(is_namespace_node(namespace))
        self.assertFalse(is_namespace_node(self.elem))

    def test_is_processing_instruction_node_function(self):
        pi = ElementTree.ProcessingInstruction('action', 'nothing to do')
        self.assertTrue(is_processing_instruction_node(pi))
        self.assertFalse(is_processing_instruction_node(self.elem))

    def test_is_text_node_function(self):
        self.assertTrue(is_text_node(TextNode('alpha')))
        self.assertFalse(is_text_node('alpha'))
        self.assertFalse(is_text_node(self.elem))

    def test_node_attributes_function(self):
        self.assertEqual(node_attributes(self.elem), self.elem.attrib)
        self.assertIsNone(node_attributes('a text node'))

    def test_node_base_uri_function(self):
        xml_test = '<A xmlns:xml="http://www.w3.org/XML/1998/namespace" xml:base="/" />'
        self.assertEqual(node_base_uri(ElementTree.XML(xml_test)), '/')
        document = ElementTree.parse(io.StringIO(xml_test))
        self.assertEqual(node_base_uri(document), '/')
        self.assertIsNone(node_base_uri(self.elem))
        self.assertIsNone(node_base_uri('a text node'))

    def test_node_document_uri_function(self):
        self.assertIsNone(node_document_uri(self.elem))

        xml_test = '<A xmlns:xml="http://www.w3.org/XML/1998/namespace" xml:base="/root" />'
        document = ElementTree.parse(io.StringIO(xml_test))
        self.assertEqual(node_document_uri(document), '/root')

        xml_test = '<A xmlns:xml="http://www.w3.org/XML/1998/namespace" xml:base="http://xpath.test" />'
        document = ElementTree.parse(io.StringIO(xml_test))
        self.assertEqual(node_document_uri(document), 'http://xpath.test')

        xml_test = '<A xmlns:xml="http://www.w3.org/XML/1998/namespace" xml:base="dir1/dir2" />'
        document = ElementTree.parse(io.StringIO(xml_test))
        self.assertIsNone(node_document_uri(document))

        xml_test = '<A xmlns:xml="http://www.w3.org/XML/1998/namespace" xml:base="http://[xpath.test" />'
        document = ElementTree.parse(io.StringIO(xml_test))
        self.assertIsNone(node_document_uri(document))

    def test_node_children_function(self):
        self.assertListEqual(list(node_children(self.elem)), [])
        elem = ElementTree.XML("<A><B1/><B2/></A>")
        self.assertListEqual(list(node_children(elem)), elem[:])
        document = ElementTree.parse(io.StringIO("<A><B1/><B2/></A>"))
        self.assertListEqual(list(node_children(document)), [document.getroot()])
        self.assertIsNone(node_children('a text node'))

    def test_node_is_id_function(self):
        self.assertTrue(node_is_id(ElementTree.XML('<A>xyz</A>')))
        self.assertFalse(node_is_id(ElementTree.XML('<A>xyz abc</A>')))
        self.assertFalse(node_is_id(ElementTree.XML('<A>12345</A>')))
        self.assertTrue(node_is_id(AttributeNode('id', 'alpha')))
        self.assertFalse(node_is_id(AttributeNode('id', 'alpha beta')))
        self.assertFalse(node_is_id(AttributeNode('id', '12345')))
        self.assertIsNone(node_is_id('a text node'))

    def test_node_is_idref_function(self):
        self.assertTrue(node_is_idrefs(ElementTree.XML('<A>xyz</A>')))
        self.assertTrue(node_is_idrefs(ElementTree.XML('<A>xyz abc</A>')))
        self.assertFalse(node_is_idrefs(ElementTree.XML('<A>12345</A>')))
        self.assertTrue(node_is_idrefs(AttributeNode('id', 'alpha')))
        self.assertTrue(node_is_idrefs(AttributeNode('id', 'alpha beta')))
        self.assertFalse(node_is_idrefs(AttributeNode('id', '12345')))
        self.assertIsNone(node_is_idrefs('a text node'))

    def test_node_nilled_function(self):
        xml_test = '<A xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="true" />'
        self.assertTrue(node_nilled(ElementTree.XML(xml_test)))
        xml_test = '<A xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="false" />'
        self.assertFalse(node_nilled(ElementTree.XML(xml_test)))
        self.assertFalse(node_nilled(ElementTree.XML('<A />')))

    def test_node_kind_function(self):
        document = ElementTree.parse(io.StringIO(u'<A/>'))
        element = ElementTree.Element('schema')
        attribute = AttributeNode('id', '0212349350')
        namespace = NamespaceNode('xs', 'http://www.w3.org/2001/XMLSchema')
        comment = ElementTree.Comment('nothing important')
        pi = ElementTree.ProcessingInstruction('action', 'nothing to do')
        text = TextNode('betelgeuse')
        self.assertEqual(node_kind(document), 'document')
        self.assertEqual(node_kind(element), 'element')
        self.assertEqual(node_kind(attribute), 'attribute')
        self.assertEqual(node_kind(namespace), 'namespace')
        self.assertEqual(node_kind(comment), 'comment')
        self.assertEqual(node_kind(pi), 'processing-instruction')
        self.assertEqual(node_kind(text), 'text')
        self.assertIsNone(node_kind(None))
        self.assertIsNone(node_kind(10))

    def test_node_name_function(self):
        elem = ElementTree.Element('root')
        attr = AttributeNode('a1', '20')
        namespace = NamespaceNode('xs', 'http://www.w3.org/2001/XMLSchema')
        self.assertEqual(node_name(elem), 'root')
        self.assertEqual(node_name(attr), 'a1')
        self.assertEqual(node_name(namespace), 'xs')


if __name__ == '__main__':
    unittest.main()
