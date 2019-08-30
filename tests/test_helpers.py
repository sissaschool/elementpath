#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c), 2018-2019, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from __future__ import unicode_literals
import unittest
import io
import xml.etree.ElementTree as ElementTree

from elementpath.exceptions import ElementPathError, xpath_error
from elementpath.namespaces import XSD_NAMESPACE, get_namespace, qname_to_prefixed, \
    prefixed_to_qname
from elementpath.xpath_nodes import AttributeNode, NamespaceNode, is_etree_element, \
    is_element_node, is_attribute_node, is_comment_node, is_document_node, \
    is_namespace_node, is_processing_instruction_node, is_text_node, node_attributes, \
    node_base_uri, node_document_uri, node_children, node_is_id, node_is_idrefs, \
    node_nilled, node_kind, node_name
from elementpath.xpath_token import ordinal
from elementpath.xpath_helpers import boolean_value
from elementpath.xpath1_parser import XPath1Parser


class ExceptionHelpersTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.parser = XPath1Parser(namespaces={'xs': XSD_NAMESPACE, 'tst': "http://xpath.test/ns"})

    def test_exception_repr(self):
        err = ElementPathError("unknown error")
        self.assertEqual(str(err), 'unknown error')
        err = ElementPathError("unknown error", code='XPST0001')
        self.assertEqual(str(err), '[XPST0001] unknown error.')
        token = self.parser.symbol_table['true'](self.parser)
        err = ElementPathError("unknown error", code='XPST0001', token=token)
        self.assertEqual(str(err), "'true' function: [XPST0001] unknown error.")

    def test_xpath_error(self):
        self.assertEqual(str(xpath_error('XPST0001')), '[err:XPST0001] Parser not bound to a schema.')
        self.assertEqual(str(xpath_error('err:XPDY0002', "test message")), '[err:XPDY0002] test message.')
        self.assertRaises(ValueError, xpath_error, '')
        self.assertRaises(ValueError, xpath_error, 'error:XPDY0002')


class NamespaceHelpersTest(unittest.TestCase):
    namespaces = {
        'xs': XSD_NAMESPACE,
        'tst': "http://xpath.test/ns"
    }

    # namespaces.py module
    def test_get_namespace_function(self):
        self.assertEqual(get_namespace('A'), '')
        self.assertEqual(get_namespace('{ns}foo'), 'ns')
        self.assertEqual(get_namespace('{}foo'), '')
        self.assertEqual(get_namespace('{A}B{C}'), 'A')

    def test_qname_to_prefixed_function(self):
        self.assertEqual(qname_to_prefixed('{ns}foo', {'bar': 'ns'}), 'bar:foo')
        self.assertEqual(qname_to_prefixed('{ns}foo', {'': 'ns'}), 'foo')
        self.assertEqual(qname_to_prefixed('foo', {'': 'ns'}), 'foo')

    def test_prefixed_to_qname_function(self):
        self.assertEqual(prefixed_to_qname('{ns}foo', {'bar': 'ns'}), '{ns}foo')
        self.assertEqual(prefixed_to_qname('bar:foo', {'bar': 'ns'}), '{ns}foo')
        self.assertEqual(prefixed_to_qname('foo', {'': 'ns'}), '{ns}foo')

        with self.assertRaises(ValueError):
            prefixed_to_qname('bar:foo', self.namespaces)
        with self.assertRaises(ValueError):
            prefixed_to_qname('bar:foo:bar', {'bar': 'ns'})
        with self.assertRaises(ValueError):
            prefixed_to_qname(':foo', {'': 'ns'})
        with self.assertRaises(ValueError):
            prefixed_to_qname('foo:', {'': 'ns'})


class NodeHelpersTest(unittest.TestCase):
    elem = ElementTree.XML('<node a1="10"/>')

    def test_is_etree_element_function(self):
        self.assertTrue(is_etree_element(self.elem))
        self.assertFalse(is_etree_element('text'))
        self.assertFalse(is_etree_element(None))

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
        self.assertTrue(is_text_node('alpha'))
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
        text = u'betelgeuse'
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


class XPathTokenHelpersTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.parser = XPath1Parser(namespaces={'xs': XSD_NAMESPACE, 'tst': "http://xpath.test/ns"})

    def test_ordinal_function(self):
        self.assertEqual(ordinal(1), '1st')
        self.assertEqual(ordinal(2), '2nd')
        self.assertEqual(ordinal(3), '3rd')
        self.assertEqual(ordinal(4), '4th')
        self.assertEqual(ordinal(11), '11th')
        self.assertEqual(ordinal(23), '23rd')
        self.assertEqual(ordinal(34), '34th')

    def test_boolean_value_function(self):
        elem = ElementTree.Element('A')

        self.assertFalse(boolean_value([]))
        self.assertTrue(boolean_value([elem]))
        self.assertFalse(boolean_value([0]))
        self.assertTrue(boolean_value([1]))
        with self.assertRaises(TypeError):
            boolean_value([1, 1])
        with self.assertRaises(TypeError):
            boolean_value(elem)
        self.assertFalse(boolean_value(0))
        self.assertTrue(boolean_value(1))

    def test_get_argument_method(self):
        token = self.parser.symbol_table['true'](self.parser)

        self.assertIsNone(token.get_argument(2))
        with self.assertRaises(TypeError):
            token.get_argument(1, required=True)


if __name__ == '__main__':
    unittest.main()
