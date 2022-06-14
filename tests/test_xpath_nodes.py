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

from elementpath.etree import is_etree_element, etree_iter_strings, \
    etree_deep_equal, etree_iter_paths
from elementpath.xpath_nodes import DocumentNode, ElementNode, AttributeNode, TextNode, \
    NamespaceNode, CommentNode, ProcessingInstructionNode, match_element_node, match_attribute_node
from elementpath.xpath_context import XPathContext


class DummyXsdType:
    name = local_name = None

    def is_matching(self, name, default_namespace): pass
    def is_empty(self): pass
    def is_simple(self): pass
    def has_simple_content(self): pass
    def has_mixed_content(self): pass
    def is_element_only(self): pass
    def is_key(self): pass
    def is_qname(self): pass
    def is_notation(self): pass
    def decode(self, obj, *args, **kwargs): return int(obj)
    def validate(self, obj, *args, **kwargs): pass


class XPathNodesTest(unittest.TestCase):
    elem = ElementTree.XML('<node a1="10"/>')

    def setUp(self):
        root = ElementTree.Element('root')
        self.context = XPathContext(root)  # Dummy context for creating nodes

    def test_is_etree_element_function(self):
        self.assertTrue(is_etree_element(self.elem))
        self.assertFalse(is_etree_element('text'))
        self.assertFalse(is_etree_element(None))

    def test_elem_iter_strings_function(self):
        root = ElementTree.XML('<A>text1\n<B1>text2</B1>tail1<B2/><B3><C1>text3</C1></B3>tail2</A>')
        result = ['text1\n', 'text2', 'tail1', 'tail2', 'text3']
        self.assertListEqual(list(etree_iter_strings(root)), result)

        with patch.multiple(DummyXsdType, has_mixed_content=lambda x: True):
            xsd_type = DummyXsdType()
            typed_root = ElementNode(self.context, elem=root, xsd_type=xsd_type)
            self.assertListEqual(list(etree_iter_strings(typed_root.elem)), result)

        norm_result = ['text1', 'text2', 'tail1', 'tail2', 'text3']
        with patch.multiple(DummyXsdType, is_element_only=lambda x: True):
            xsd_type = DummyXsdType()
            typed_root = ElementNode(self.context, elem=root, xsd_type=xsd_type)
            self.assertListEqual(list(etree_iter_strings(typed_root.elem, True)), norm_result)

            comment = ElementTree.Comment('foo')
            root[1].append(comment)
            self.assertListEqual(list(etree_iter_strings(typed_root.elem, True)), norm_result)

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
            typed_elem = ElementNode(self.context, elem=elem, xsd_type=xsd_type)
            self.assertTrue(match_element_node(typed_elem, '*'))

    def test_match_attribute_node_function(self):
        attr = AttributeNode(self.context, 'a1', '10', parent=None)
        self.assertTrue(match_attribute_node(attr, '*'))
        self.assertTrue(match_attribute_node(attr, 'a1'))
        with self.assertRaises(ValueError):
            match_attribute_node(attr, '**')
        with self.assertRaises(ValueError):
            match_attribute_node(attr, '*:*:*')
        with self.assertRaises(ValueError):
            match_attribute_node(attr, 'foo:*')
        self.assertTrue(match_attribute_node(attr, '*:a1'))
        self.assertFalse(match_attribute_node(attr, '{foo}*'))
        self.assertTrue(
            match_attribute_node(AttributeNode(self.context, '{foo}a1', '10'), '{foo}*')
        )

        attr = AttributeNode(self.context, '{http://xpath.test/ns}a1', '10', parent=None)
        self.assertTrue(match_attribute_node(attr, '*:a1'))

    def test_node_base_uri(self):
        xml_test = '<A xmlns:xml="http://www.w3.org/XML/1998/namespace" xml:base="/" />'

        context = XPathContext(ElementTree.XML('<empty/>'))

        self.assertEqual(ElementNode(context, ElementTree.XML(xml_test)).base_uri, '/')
        document = ElementTree.parse(io.StringIO(xml_test))
        self.assertIsNone(DocumentNode(context, document).base_uri)
        self.assertIsNone(ElementNode(context, self.elem).base_uri)
        self.assertIsNone(TextNode(context, 'a text node').base_uri)

    def test_node_document_uri_function(self):
        node = ElementNode(self.context, self.elem)
        self.assertIsNone(node.document_uri)

        xml_test = '<A xmlns:xml="http://www.w3.org/XML/1998/namespace" xml:base="/root" />'
        document = ElementTree.parse(io.StringIO(xml_test))
        node = DocumentNode(self.context, document)
        self.assertEqual(node.document_uri, '/root')

        xml_test = '<A xmlns:xml="http://www.w3.org/XML/1998/namespace" ' \
                   'xml:base="http://xpath.test" />'
        document = ElementTree.parse(io.StringIO(xml_test))
        node = DocumentNode(self.context, document)
        self.assertEqual(node.document_uri, 'http://xpath.test')

        xml_test = '<A xmlns:xml="http://www.w3.org/XML/1998/namespace" xml:base="dir1/dir2" />'
        document = ElementTree.parse(io.StringIO(xml_test))
        node = DocumentNode(self.context, document)
        self.assertIsNone(node.document_uri)

        xml_test = '<A xmlns:xml="http://www.w3.org/XML/1998/namespace" ' \
                   'xml:base="http://[xpath.test" />'
        document = ElementTree.parse(io.StringIO(xml_test))
        node = DocumentNode(self.context, document)
        self.assertIsNone(node.document_uri)

    def test_attribute_nodes(self):
        parent = self.context.root
        attribute = AttributeNode(self.context, 'id', '0212349350')

        self.assertEqual(repr(attribute),
                         "AttributeNode(name='id', value='0212349350')")
        self.assertNotEqual(attribute, AttributeNode(self.context, 'id', '0212349350'))
        self.assertEqual(attribute.as_item(), ('id', '0212349350'))
        self.assertNotEqual(attribute.as_item(),
                            AttributeNode(self.context, 'id', '0212349350'))
        self.assertNotEqual(attribute, AttributeNode(self.context, 'id', '0212349350', parent))

        attribute = AttributeNode(self.context, 'id', '0212349350', parent)
        self.assertNotEqual(attribute, AttributeNode(self.context, 'id', '0212349350', parent))
        self.assertEqual(attribute.as_item(), ('id', '0212349350'))

        attribute = AttributeNode(self.context, 'value', '10', parent)
        self.assertEqual(repr(attribute), "AttributeNode(name='value', value='10')")

        with patch.multiple(DummyXsdType, is_simple=lambda x: True):
            xsd_type = DummyXsdType()
            attribute.xsd_type = xsd_type
            self.assertEqual(attribute.as_item(), ('value', '10'))

    def test_typed_element_nodes(self):
        element = ElementTree.Element('schema')

        with patch.multiple(DummyXsdType, is_simple=lambda x: True):
            xsd_type = DummyXsdType()
            context = XPathContext(element)
            context.root.xsd_type = xsd_type
            self.assertTrue(repr(context.root).startswith(
                "ElementNode(elem=<Element 'schema' at 0x"
            ))

    def test_text_nodes(self):
        context, parent = self.context, self.context.root

        # equality if and only is the same instance
        text_node = TextNode(context, 'alpha')
        self.assertEqual(text_node, text_node)
        self.assertNotEqual(text_node, TextNode(context, 'alpha'))

        text_node = TextNode(context, 'alpha', parent)
        self.assertEqual(text_node, text_node)
        self.assertNotEqual(text_node, TextNode(context, 'alpha', parent))

        text_node = TextNode(context, 'alpha', parent)
        self.assertEqual(text_node, text_node)
        self.assertNotEqual(text_node, TextNode(context, 'alpha', parent))

        self.assertEqual(repr(TextNode(context, 'alpha')), "TextNode(value='alpha')")
        text_node = TextNode(context, 'alpha', parent)
        self.assertEqual(repr(text_node), "TextNode(value='alpha')")

    def test_namespace_nodes(self):
        context, parent = self.context, self.context.root
        namespace = NamespaceNode(context, 'tns', 'http://xpath.test/ns')

        self.assertEqual(repr(namespace),
                         "NamespaceNode(prefix='tns', uri='http://xpath.test/ns')")
        self.assertEqual(namespace.value, 'http://xpath.test/ns')
        self.assertNotEqual(namespace, NamespaceNode(context, 'tns', 'http://xpath.test/ns'))
        self.assertEqual(namespace.as_item(), ('tns', 'http://xpath.test/ns'))
        self.assertNotEqual(
            namespace, NamespaceNode(context, 'tns', 'http://xpath.test/ns', parent=context.root)
        )

        namespace = NamespaceNode(context, 'tns', 'http://xpath.test/ns', parent=context.root)
        self.assertEqual(repr(namespace), "NamespaceNode(prefix='tns', uri='http://xpath.test/ns')")

        self.assertNotEqual(namespace,
                            NamespaceNode(context, 'tns', 'http://xpath.test/ns', parent=context.root))
        self.assertEqual(namespace.as_item(), ('tns', 'http://xpath.test/ns'))
        self.assertNotEqual(namespace, NamespaceNode(context, 'tns', 'http://xpath.test/ns'))
        self.assertNotEqual(namespace, NamespaceNode(context, 'tns', 'http://xpath.test/ns',
                                                     parent=ElementTree.Element('element')))

    def test_node_children_function(self):
        self.assertListEqual(ElementNode(self.context, self.elem).children, [])
        elem = ElementNode(self.context, ElementTree.XML("<A><B1/><B2/></A>"))
        self.assertListEqual(elem.children, [x for x in elem])

        document = DocumentNode(self.context, ElementTree.parse(io.StringIO("<A><B1/><B2/></A>")))
        self.assertListEqual(document.children, [])  # not built document
        document.children.append(ElementNode(self.context, document.value.getroot(), document))
        self.assertListEqual(document.children, [document.getroot()])

        self.assertIsNone(TextNode(self.context, 'a text node').children)

    def test_node_nilled_function(self):
        xml_test = '<A xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="true" />'
        self.assertTrue(ElementNode(self.context, ElementTree.XML(xml_test)).nilled)
        xml_test = '<A xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="false" />'
        self.assertFalse(ElementNode(self.context, ElementTree.XML(xml_test)).nilled)
        self.assertFalse(ElementNode(self.context, ElementTree.XML('<A />')).nilled)
        self.assertFalse(TextNode(self.context, 'foo').nilled)

    def test_node_kind_function(self):
        document = DocumentNode(self.context, ElementTree.parse(io.StringIO(u'<A/>')))
        element = ElementNode(self.context, ElementTree.Element('schema'))
        attribute = AttributeNode(self.context, 'id', '0212349350')
        namespace = NamespaceNode(self.context, 'xs', 'http://www.w3.org/2001/XMLSchema')
        comment = CommentNode(self.context, ElementTree.Comment('nothing important'))
        pi = ProcessingInstructionNode(
            self.context, ElementTree.ProcessingInstruction('action', 'nothing to do')
        )
        text = TextNode(self.context, 'betelgeuse')

        self.assertEqual(document.kind, 'document')
        self.assertEqual(element.kind, 'element')
        self.assertEqual(attribute.kind, 'attribute')
        self.assertEqual(namespace.kind, 'namespace')
        self.assertEqual(comment.kind, 'comment')
        self.assertEqual(pi.kind, 'processing-instruction')
        self.assertEqual(text.kind, 'text')

        with patch.multiple(DummyXsdType, is_simple=lambda x: True):
            xsd_type = DummyXsdType()

            attribute = AttributeNode(self.context, 'id', '0212349350', xsd_type=xsd_type)
            self.assertEqual(attribute.kind, 'attribute')

            typed_element = ElementNode(self.context, element.elem, xsd_type=xsd_type)
            self.assertEqual(typed_element.kind, 'element')

    def test_node_name_function(self):
        root = self.context.root
        attr = AttributeNode(self.context, 'a1', '20')
        namespace = NamespaceNode(self.context, 'xs', 'http://www.w3.org/2001/XMLSchema')

        self.assertEqual(root.name, 'root')
        self.assertEqual(attr.name, 'a1')
        self.assertEqual(namespace.name, 'xs')

        with patch.multiple(DummyXsdType, is_simple=lambda x: True):
            xsd_type = DummyXsdType()

            typed_elem = ElementNode(self.context, elem=root.elem, xsd_type=xsd_type)
            self.assertEqual(typed_elem.name, 'root')

            typed_attr = AttributeNode(self.context, 'a1', value='20', xsd_type=xsd_type)
            self.assertEqual(typed_attr.name, 'a1')

    def test_element_node_iter(self):
        root = ElementTree.XML('<A>text1\n<B1 a="10">text2</B1><B2/><B3><C1>text3</C1></B3></A>')

        context = XPathContext(root)
        result = [context.root, context.root.namespaces[0],
                  context.root[0],
                  context.root[1], context.root[1].namespaces[0], context.root[1].attributes[0], context.root[1][0],
                  context.root[2], context.root[2].namespaces[0],
                  context.root[3], context.root[3].namespaces[0],
                  context.root[3][0], context.root[3][0].namespaces[0], context.root[3][0][0]]

        self.assertListEqual(list(context.root.iter()), result)
        self.assertListEqual(list(context.root.iter(with_self=False)), result[1:])

    def test_etree_iter_paths(self):
        root = ElementTree.XML('<a><b1><c1/><c2/></b1><b2/><b3><c3/></b3></a>')
        root[2].append(ElementTree.Comment('a comment'))
        root[2].append(ElementTree.Element('c3'))  # duplicated tag

        items = list(etree_iter_paths(root))
        self.assertListEqual(items, [
            (root, '.'), (root[0], './Q{}b1[1]'),
            (root[0][0], './Q{}b1[1]/Q{}c1[1]'),
            (root[0][1], './Q{}b1[1]/Q{}c2[1]'),
            (root[1], './Q{}b2[1]'), (root[2], './Q{}b3[1]'),
            (root[2][0], './Q{}b3[1]/Q{}c3[1]'),
            (root[2][1], './Q{}b3[1]/comment()[1]'),
            (root[2][2], './Q{}b3[1]/Q{}c3[2]')
        ])
        self.assertListEqual(list(etree_iter_paths(root, path='')), [
            (root, ''), (root[0], 'Q{}b1[1]'),
            (root[0][0], 'Q{}b1[1]/Q{}c1[1]'),
            (root[0][1], 'Q{}b1[1]/Q{}c2[1]'),
            (root[1], 'Q{}b2[1]'), (root[2], 'Q{}b3[1]'),
            (root[2][0], 'Q{}b3[1]/Q{}c3[1]'),
            (root[2][1], 'Q{}b3[1]/comment()[1]'),
            (root[2][2], 'Q{}b3[1]/Q{}c3[2]')
        ])
        self.assertListEqual(list(etree_iter_paths(root, path='/')), [
            (root, '/'), (root[0], '/Q{}b1[1]'),
            (root[0][0], '/Q{}b1[1]/Q{}c1[1]'),
            (root[0][1], '/Q{}b1[1]/Q{}c2[1]'),
            (root[1], '/Q{}b2[1]'), (root[2], '/Q{}b3[1]'),
            (root[2][0], '/Q{}b3[1]/Q{}c3[1]'),
            (root[2][1], '/Q{}b3[1]/comment()[1]'),
            (root[2][2], '/Q{}b3[1]/Q{}c3[2]')
        ])


if __name__ == '__main__':
    unittest.main()
