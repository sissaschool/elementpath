#!/usr/bin/env python
#
# Copyright (c), 2018-2021, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import unittest
from unittest.mock import patch
import io
import xml.etree.ElementTree as ElementTree

from elementpath.xpath_nodes import AttributeNode, TextNode, TypedAttribute, \
    TypedElement, NamespaceNode, is_etree_element, etree_iter_strings, \
    etree_deep_equal, match_element_node, match_attribute_node, is_comment_node, \
    is_document_node, is_processing_instruction_node, node_attributes, node_base_uri, \
    node_document_uri, node_children, node_nilled, node_kind, node_name, \
    etree_iter_nodes, etree_iterpath
from elementpath.schema_proxy import AbstractXsdType


class DummyXsdType(AbstractXsdType):
    name = local_name = None

    def is_matching(self, name, default_namespace): return False
    def is_empty(self): return False
    def is_simple(self): return False
    def has_simple_content(self): return False
    def has_mixed_content(self): return False
    def is_element_only(self): return False
    def is_key(self): return False
    def is_qname(self): return False
    def is_notation(self): return False
    def decode(self, obj, *args, **kwargs): return None
    def validate(self, obj, *args, **kwargs): pass


class XPathNodesTest(unittest.TestCase):
    elem = ElementTree.XML('<node a1="10"/>')

    def test_is_etree_element_function(self):
        self.assertTrue(is_etree_element(self.elem))
        self.assertFalse(is_etree_element('text'))
        self.assertFalse(is_etree_element(None))

    def test_elem_iter_nodes_function(self):
        root = ElementTree.XML('<A>text1\n<B1 a="10">text2</B1><B2/><B3><C1>text3</C1></B3></A>')

        result = [root, TextNode('text1\n', root),
                  root[0], TextNode('text2', root[0]), root[1],
                  root[2], root[2][0], TextNode('text3', root[2][0])]

        self.assertListEqual(list(etree_iter_nodes(root)), result)
        self.assertListEqual(list(etree_iter_nodes(root, with_root=False)), result[1:])

        with patch.multiple(DummyXsdType, has_mixed_content=lambda x: True):
            xsd_type = DummyXsdType()
            typed_root = TypedElement(root, xsd_type, 'text1')
            self.assertListEqual(list(etree_iter_nodes(typed_root)), result)

        result = result[:4] + [AttributeNode('a', '10', root[0])] + result[4:]
        self.assertListEqual(list(etree_iter_nodes(root, with_attributes=True)), result)

        comment = ElementTree.Comment('foo')
        root[1].append(comment)
        self.assertListEqual(list(etree_iter_nodes(root, with_attributes=True)), result)

    def test_elem_iter_strings_function(self):
        root = ElementTree.XML('<A>text1\n<B1>text2</B1>tail1<B2/><B3><C1>text3</C1></B3>tail2</A>')
        result = ['text1\n', 'text2', 'tail1', 'tail2', 'text3']
        self.assertListEqual(list(etree_iter_strings(root)), result)

        with patch.multiple(DummyXsdType, has_mixed_content=lambda x: True):
            xsd_type = DummyXsdType()
            typed_root = TypedElement(elem=root, xsd_type=xsd_type, value='text1')
            self.assertListEqual(list(etree_iter_strings(typed_root)), result)

        norm_result = ['text1', 'text2', 'tail1', 'tail2', 'text3']
        with patch.multiple(DummyXsdType, is_element_only=lambda x: True):
            xsd_type = DummyXsdType()
            typed_root = TypedElement(elem=root, xsd_type=xsd_type, value='text1')
            self.assertListEqual(list(etree_iter_strings(typed_root)), norm_result)

            comment = ElementTree.Comment('foo')
            root[1].append(comment)
            self.assertListEqual(list(etree_iter_strings(typed_root)), norm_result)

        self.assertListEqual(list(etree_iter_strings(root)), result)

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

    def test_match_element_node_function(self):
        elem = ElementTree.Element('alpha')
        empty_tag_elem = ElementTree.Element('')
        self.assertTrue(match_element_node(elem))
        self.assertTrue(match_element_node(elem, '*'))
        self.assertFalse(match_element_node(empty_tag_elem, '*'))
        with self.assertRaises(ValueError):
            match_element_node(elem, '**')
        with self.assertRaises(ValueError):
            match_element_node(elem, '*:*:*')
        with self.assertRaises(ValueError):
            match_element_node(elem, 'foo:*')
        self.assertFalse(match_element_node(empty_tag_elem, 'foo:*'))
        self.assertFalse(match_element_node(elem, '{foo}*'))

        with patch.multiple(DummyXsdType, has_mixed_content=lambda x: True):
            xsd_type = DummyXsdType()
            typed_elem = TypedElement(elem=elem, xsd_type=xsd_type, value='text1')
            self.assertTrue(match_element_node(typed_elem, '*'))

    def test_match_attribute_node_function(self):
        attr = AttributeNode('a1', '10', parent=None)
        self.assertTrue(match_attribute_node(attr, '*'))
        self.assertTrue(match_attribute_node(TypedAttribute(attr, None, 10), 'a1'))
        with self.assertRaises(ValueError):
            match_attribute_node(attr, '**')
        with self.assertRaises(ValueError):
            match_attribute_node(attr, '*:*:*')
        with self.assertRaises(ValueError):
            match_attribute_node(attr, 'foo:*')
        self.assertTrue(match_attribute_node(attr, '*:a1'))
        self.assertFalse(match_attribute_node(attr, '{foo}*'))
        self.assertTrue(match_attribute_node(AttributeNode('{foo}a1', '10'), '{foo}*'))

        attr = AttributeNode('{http://xpath.test/ns}a1', '10', parent=None)
        self.assertTrue(match_attribute_node(attr, '*:a1'))

    def test_is_comment_node_function(self):
        comment = ElementTree.Comment('nothing important')
        self.assertTrue(is_comment_node(comment))
        self.assertFalse(is_comment_node(self.elem))

    def test_is_document_node_function(self):
        document = ElementTree.parse(io.StringIO('<A/>'))
        self.assertTrue(is_document_node(document))
        self.assertFalse(is_document_node(self.elem))

    def test_is_processing_instruction_node_function(self):
        pi = ElementTree.ProcessingInstruction('action', 'nothing to do')
        self.assertTrue(is_processing_instruction_node(pi))
        self.assertFalse(is_processing_instruction_node(self.elem))

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

        xml_test = '<A xmlns:xml="http://www.w3.org/XML/1998/namespace" ' \
                   'xml:base="http://xpath.test" />'
        document = ElementTree.parse(io.StringIO(xml_test))
        self.assertEqual(node_document_uri(document), 'http://xpath.test')

        xml_test = '<A xmlns:xml="http://www.w3.org/XML/1998/namespace" xml:base="dir1/dir2" />'
        document = ElementTree.parse(io.StringIO(xml_test))
        self.assertIsNone(node_document_uri(document))

        xml_test = '<A xmlns:xml="http://www.w3.org/XML/1998/namespace" ' \
                   'xml:base="http://[xpath.test" />'
        document = ElementTree.parse(io.StringIO(xml_test))
        self.assertIsNone(node_document_uri(document))

    def test_attribute_nodes(self):
        parent = ElementTree.Element('element')
        attribute = AttributeNode('id', '0212349350')

        self.assertEqual(repr(attribute),
                         "AttributeNode(name='id', value='0212349350')")
        self.assertEqual(attribute, AttributeNode('id', '0212349350'))
        self.assertEqual(attribute.as_item(), ('id', '0212349350'))
        self.assertNotEqual(attribute.as_item(), AttributeNode('id', '0212349350'))
        self.assertNotEqual(attribute, AttributeNode('id', '0212349350', parent))

        attribute = AttributeNode('id', '0212349350', parent)
        self.assertEqual(attribute, AttributeNode('id', '0212349350', parent))
        self.assertEqual(attribute.as_item(), ('id', '0212349350'))
        self.assertNotEqual(attribute, AttributeNode('id', '0212349350'))
        self.assertNotEqual(attribute, AttributeNode('id', '0212349350',
                                                     parent=ElementTree.Element('element')))

        attribute = AttributeNode('value', '10', parent)
        self.assertEqual(repr(attribute)[:65],
                         "AttributeNode(name='value', value='10', parent=<Element 'element'")

        with patch.multiple(DummyXsdType, is_simple=lambda x: True):
            xsd_type = DummyXsdType()

            typed_attribute = TypedAttribute(attribute, xsd_type, 10)
            self.assertEqual(repr(typed_attribute), "TypedAttribute(name='value')")
            self.assertEqual(typed_attribute.as_item(), ('value', 10))

            self.assertEqual(typed_attribute, TypedAttribute(attribute, DummyXsdType(), 10))
            self.assertEqual(typed_attribute, TypedAttribute(attribute, None, 10))
            self.assertEqual(typed_attribute,
                             TypedAttribute(AttributeNode('value', '10', parent), xsd_type, 10))
            self.assertNotEqual(typed_attribute, TypedAttribute(attribute, xsd_type, '10'))
            self.assertNotEqual(typed_attribute,
                                TypedAttribute(AttributeNode('value', '10'), xsd_type, 10))

    def test_typed_element_nodes(self):
        element = ElementTree.Element('schema')

        with patch.multiple(DummyXsdType, is_simple=lambda x: True):
            xsd_type = DummyXsdType()

            typed_element = TypedElement(element, xsd_type, None)
            self.assertEqual(repr(typed_element), "TypedElement(tag='schema')")

    def test_text_nodes(self):
        parent = ElementTree.Element('element')
        self.assertEqual(TextNode('alpha'), TextNode('alpha'))
        self.assertEqual(TextNode('alpha', parent), TextNode('alpha', parent))
        self.assertEqual(TextNode('alpha', parent, tail=True),
                         TextNode('alpha', parent, tail=True))
        self.assertEqual(TextNode('alpha', tail=True), TextNode('alpha'))
        self.assertNotEqual(TextNode('alpha', parent), TextNode('alpha'))
        self.assertNotEqual(TextNode('alpha', parent, tail=True),
                            TextNode('alpha', parent))
        self.assertNotEqual(TextNode('alpha', parent),
                            TextNode('alpha', parent=ElementTree.Element('element')))  # != id()

        self.assertFalse(TextNode('alpha', parent).is_tail())
        self.assertTrue(TextNode('alpha', parent, tail=True).is_tail())
        self.assertFalse(TextNode('alpha', tail=True).is_tail())

        self.assertEqual(repr(TextNode('alpha')), "TextNode('alpha')")
        text = TextNode('alpha', parent)
        self.assertTrue(repr(text).startswith("TextNode('alpha', parent=<Element "))
        self.assertTrue(repr(text).endswith(", tail=False)"))
        text = TextNode('alpha', parent, tail=True)
        self.assertTrue(repr(text).endswith(", tail=True)"))

    def test_namespace_nodes(self):
        parent = ElementTree.Element('element')
        namespace = NamespaceNode('tns', 'http://xpath.test/ns')

        self.assertEqual(repr(namespace),
                         "NamespaceNode(prefix='tns', uri='http://xpath.test/ns')")
        self.assertEqual(namespace.value, 'http://xpath.test/ns')
        self.assertEqual(namespace, NamespaceNode('tns', 'http://xpath.test/ns'))
        self.assertEqual(namespace.as_item(), ('tns', 'http://xpath.test/ns'))
        self.assertNotEqual(namespace,
                            NamespaceNode('tns', 'http://xpath.test/ns', parent))

        namespace = NamespaceNode('tns', 'http://xpath.test/ns', parent)
        self.assertEqual(repr(namespace)[:81],
                         "NamespaceNode(prefix='tns', uri='http://xpath.test/ns', "
                         "parent=<Element 'element'")

        self.assertEqual(namespace, NamespaceNode('tns', 'http://xpath.test/ns', parent))
        self.assertEqual(namespace.as_item(), ('tns', 'http://xpath.test/ns'))
        self.assertNotEqual(namespace, NamespaceNode('tns', 'http://xpath.test/ns'))
        self.assertNotEqual(namespace, NamespaceNode('tns', 'http://xpath.test/ns',
                                                     parent=ElementTree.Element('element')))

    def test_node_children_function(self):
        self.assertListEqual(list(node_children(self.elem)), [])
        elem = ElementTree.XML("<A><B1/><B2/></A>")
        self.assertListEqual(list(node_children(elem)), [x for x in elem])
        document = ElementTree.parse(io.StringIO("<A><B1/><B2/></A>"))
        self.assertListEqual(list(node_children(document)), [document.getroot()])
        self.assertIsNone(node_children('a text node'))

    def test_node_nilled_function(self):
        xml_test = '<A xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="true" />'
        self.assertTrue(node_nilled(ElementTree.XML(xml_test)))
        xml_test = '<A xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="false" />'
        self.assertFalse(node_nilled(ElementTree.XML(xml_test)))
        self.assertFalse(node_nilled(ElementTree.XML('<A />')))
        self.assertFalse(node_nilled(TextNode('foo')))

    def test_node_kind_function(self):
        document = ElementTree.parse(io.StringIO(u'<A/>'))
        element = ElementTree.Element('schema')
        attribute = AttributeNode('id', '0212349350')
        namespace = NamespaceNode('xs', 'http://www.w3.org/2001/XMLSchema')
        comment = ElementTree.Comment('nothing important')
        pi = ElementTree.ProcessingInstruction('action', 'nothing to do')
        text = TextNode('betelgeuse')
        self.assertEqual(node_kind(document), 'document-node')
        self.assertEqual(node_kind(element), 'element')
        self.assertEqual(node_kind(attribute), 'attribute')
        self.assertEqual(node_kind(namespace), 'namespace')
        self.assertEqual(node_kind(comment), 'comment')
        self.assertEqual(node_kind(pi), 'processing-instruction')
        self.assertEqual(node_kind(text), 'text')
        self.assertIsNone(node_kind(()))
        self.assertIsNone(node_kind(None))
        self.assertIsNone(node_kind(10))

        with patch.multiple(DummyXsdType, is_simple=lambda x: True):
            xsd_type = DummyXsdType()

            typed_attribute = TypedAttribute(attribute, xsd_type, '0212349350')
            self.assertEqual(node_kind(typed_attribute), 'attribute')

            typed_element = TypedElement(element, xsd_type, None)
            self.assertEqual(node_kind(typed_element), 'element')

    def test_node_name_function(self):
        elem = ElementTree.Element('root')
        attr = AttributeNode('a1', '20')
        namespace = NamespaceNode('xs', 'http://www.w3.org/2001/XMLSchema')
        self.assertEqual(node_name(elem), 'root')
        self.assertEqual(node_name(attr), 'a1')
        self.assertEqual(node_name(namespace), 'xs')
        self.assertIsNone(node_name(()))
        self.assertIsNone(node_name(None))

        with patch.multiple(DummyXsdType, is_simple=lambda x: True):
            xsd_type = DummyXsdType()

            typed_elem = TypedElement(elem=elem, xsd_type=xsd_type, value=10)
            self.assertEqual(node_name(typed_elem), 'root')

            typed_attr = TypedAttribute(attribute=attr, xsd_type=xsd_type, value=20)
            self.assertEqual(node_name(typed_attr), 'a1')

    def test_etree_iterpath(self):
        root = ElementTree.XML('<a><b1><c1/><c2/></b1><b2/><b3><c3/></b3></a>')
        root[2].append(ElementTree.Comment('a comment'))
        root[2].append(ElementTree.Element('c3'))  # duplicated tag

        items = list(etree_iterpath(root))
        self.assertListEqual(items, [
            (root, '.'), (root[0], './b1'), (root[0][0], './b1/c1'),
            (root[0][1], './b1/c2'), (root[1], './b2'), (root[2], './b3'),
            (root[2][0], './b3/c3[1]'), (root[2][2], './b3/c3[2]')
        ])
        self.assertListEqual(list(etree_iterpath(root, path='')), [
            (root, ''), (root[0], 'b1'), (root[0][0], 'b1/c1'),
            (root[0][1], 'b1/c2'), (root[1], 'b2'), (root[2], 'b3'),
            (root[2][0], 'b3/c3[1]'), (root[2][2], 'b3/c3[2]')
        ])
        self.assertListEqual(list(etree_iterpath(root, path='/')), [
            (root, '/'), (root[0], '/b1'), (root[0][0], '/b1/c1'),
            (root[0][1], '/b1/c2'), (root[1], '/b2'), (root[2], '/b3'),
            (root[2][0], '/b3/c3[1]'), (root[2][2], '/b3/c3[2]')
        ])


if __name__ == '__main__':
    unittest.main()
