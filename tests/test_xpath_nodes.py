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
from textwrap import dedent
import io
import xml.etree.ElementTree as ElementTree

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

from elementpath.etree import is_etree_element, etree_iter_strings, \
    etree_deep_equal, etree_iter_paths
from elementpath.datatypes import UntypedAtomic
from elementpath.xpath_nodes import DocumentNode, ElementNode, AttributeNode, TextNode, \
    NamespaceNode, CommentNode, ProcessingInstructionNode, EtreeElementNode, TextAttributeNode
from elementpath.tree_builders import get_node_tree
from elementpath.xpath_context import XPathContext, XPathSchemaContext


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
            typed_root = EtreeElementNode(elem=root)
            setattr(typed_root, 'xsd_type', xsd_type)
            self.assertListEqual(list(etree_iter_strings(typed_root.elem)), result)

        norm_result = ['text1', 'text2', 'tail1', 'tail2', 'text3']
        with patch.multiple(DummyXsdType, is_element_only=lambda x: True):
            xsd_type = DummyXsdType()
            typed_root = EtreeElementNode(elem=root)
            setattr(typed_root, 'xsd_type', xsd_type)
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

    def test_match_name_method(self):
        attr = AttributeNode('a1', '10', parent=None)
        self.assertTrue(attr.match_name('*'))
        self.assertTrue(attr.match_name('a1'))
        self.assertTrue(attr.match_name('*:a1'))
        self.assertFalse(attr.match_name('{foo}*'))
        self.assertFalse(attr.match_name('foo:*'))

        self.assertTrue(
            AttributeNode('{foo}a1', '10').match_name('{foo}*')
        )

        attr = AttributeNode('{http://xpath.test/ns}a1', '10', parent=None)
        self.assertTrue(attr.match_name('*:a1'))

    def test_node_base_uri(self):
        xml_test = '<A xmlns:xml="http://www.w3.org/XML/1998/namespace" xml:base="/" />'

        self.assertEqual(EtreeElementNode(ElementTree.XML(xml_test)).base_uri, '/')
        document = ElementTree.parse(io.StringIO(xml_test))

        self.assertIsNone(DocumentNode(document).base_uri, '/')
        self.assertIsNone(EtreeElementNode(self.elem).base_uri)
        self.assertIsNone(TextNode('a text node').base_uri)

        xml_test = dedent("""\
            <?xml version="1.0"?>
            <e1 xml:base="http://example.org/wine/">
              <e2 xml:base="rosé"/>
            </e1>""")

        root_node = get_node_tree(ElementTree.XML(xml_test))
        self.assertEqual(root_node.base_uri, 'http://example.org/wine/')
        self.assertIsInstance(root_node[0], TextNode)
        self.assertEqual(root_node[1].base_uri, 'http://example.org/wine/rosé')

        xml_test = dedent("""\
            <collection xml:base="http://example.test/xpath/ ">
              <item xml:base="urn:isbn:0451450523"/>
              <item xml:base="urn:isan:0000-0000-2CEA-0000-1-0000-0000-Y "/>
              <item xml:base="urn:ISSN:0167-6423 "/>
              <item xml:base=" urn:ietf:rfc:2648 "/>
              <item xml:base="urn:uuid:6e8bc430-9c3a-11d9-9669-0800200c9a66 "/>
            </collection>""")

        root_node = get_node_tree(ElementTree.XML(xml_test))
        self.assertEqual(root_node.base_uri, 'http://example.test/xpath/')
        self.assertIsInstance(root_node[0], TextNode)
        self.assertEqual(root_node[0].base_uri, 'http://example.test/xpath/')
        self.assertEqual(root_node[1].base_uri, 'urn:isbn:0451450523')
        self.assertIsInstance(root_node[2], TextNode)
        self.assertEqual(root_node[3].base_uri, 'urn:isan:0000-0000-2CEA-0000-1-0000-0000-Y')
        self.assertEqual(root_node[5].base_uri, 'urn:ISSN:0167-6423')
        self.assertEqual(root_node[7].base_uri, 'urn:ietf:rfc:2648')
        self.assertEqual(root_node[9].base_uri, 'urn:uuid:6e8bc430-9c3a-11d9-9669-0800200c9a66')

    def test_node_document_uri_function(self):
        node = EtreeElementNode(self.elem)
        self.assertIsNone(node.document_uri)

        xml_test = '<A xmlns:xml="http://www.w3.org/XML/1998/namespace" xml:base="/root" />'
        document = ElementTree.parse(io.StringIO(xml_test))
        node = DocumentNode(document)
        self.assertIsNone(node.document_uri)

        node = DocumentNode(document, uri=' http://xpath.test/doc.xml ')
        self.assertEqual(node.document_uri, 'http://xpath.test/doc.xml')

        xml_test = '<A xmlns:xml="http://www.w3.org/XML/1998/namespace" ' \
                   'xml:base="http://xpath.test" />'
        document = ElementTree.parse(io.StringIO(xml_test))
        node = DocumentNode(document)
        self.assertIsNone(node.document_uri)

        xml_test = '<A xmlns:xml="http://www.w3.org/XML/1998/namespace" xml:base="dir1/dir2" />'
        document = ElementTree.parse(io.StringIO(xml_test))
        node = DocumentNode(document, uri="dir1/dir2")
        self.assertIsNone(node.document_uri)

        xml_test = '<A xmlns:xml="http://www.w3.org/XML/1998/namespace" ' \
                   'xml:base="http://[xpath.test" />'
        document = ElementTree.parse(io.StringIO(xml_test))
        node = DocumentNode(document, uri="http://[xpath.test")
        self.assertIsNone(node.document_uri)

    def test_attribute_nodes(self):
        parent = self.context.root
        attribute = TextAttributeNode('id', '0212349350')

        self.assertEqual(repr(attribute),
                         "TextAttributeNode(name='id', value='0212349350')")
        self.assertNotEqual(attribute, AttributeNode('id', '0212349350'))
        self.assertEqual(attribute.as_item(), ('id', '0212349350'))
        self.assertNotEqual(attribute.as_item(),
                            AttributeNode('id', '0212349350'))
        self.assertNotEqual(attribute, AttributeNode('id', '0212349350', parent))

        attribute = AttributeNode('id', '0212349350', parent)
        self.assertNotEqual(attribute, AttributeNode('id', '0212349350', parent))
        self.assertEqual(attribute.as_item(), ('id', '0212349350'))

        attribute = AttributeNode('value', '10', parent)
        self.assertEqual(repr(attribute), "TextAttributeNode(name='value', value='10')")

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
                "EtreeElementNode(elem=<Element 'schema' at 0x"
            ))

    def test_text_nodes(self):
        parent = self.context.root

        # equality if and only is the same instance
        text_node = TextNode('alpha')
        self.assertEqual(text_node, text_node)
        self.assertNotEqual(text_node, TextNode('alpha'))

        text_node = TextNode('alpha', parent)
        self.assertEqual(text_node, text_node)
        self.assertNotEqual(text_node, TextNode('alpha', parent))

        text_node = TextNode('alpha', parent)
        self.assertEqual(text_node, text_node)
        self.assertNotEqual(text_node, TextNode('alpha', parent))

        self.assertEqual(repr(TextNode('alpha')), "TextNode('alpha')")
        text_node = TextNode('alpha', parent)
        self.assertEqual(repr(text_node), "TextNode('alpha')")

        self.assertIsNone(text_node.attributes)
        self.assertIsNone(text_node.children)
        self.assertIsNone(text_node.base_uri)
        self.assertIsNone(text_node.document_uri)
        self.assertIsNone(text_node.is_id)
        self.assertIsNone(text_node.is_idrefs)
        self.assertIsNone(text_node.namespace_nodes)
        self.assertIsNone(text_node.nilled)
        self.assertEqual(text_node.node_kind, 'text')
        self.assertIsNone(text_node.node_name)
        self.assertIsNotNone(text_node.parent)
        self.assertEqual(text_node.string_value, 'alpha')
        self.assertEqual(text_node.typed_value, UntypedAtomic('alpha'))
        self.assertIsNone(text_node.unparsed_entity_public_id('foo'))
        self.assertIsNone(text_node.unparsed_entity_system_id('foo'))

    def test_namespace_nodes(self):
        context = self.context
        namespace = NamespaceNode('tns', 'http://xpath.test/ns')

        self.assertIsNone(namespace.attributes)

        self.assertEqual(repr(namespace),
                         "NamespaceNode(prefix='tns', uri='http://xpath.test/ns')")
        self.assertEqual(namespace.value, 'http://xpath.test/ns')
        self.assertNotEqual(namespace, NamespaceNode('tns', 'http://xpath.test/ns'))
        self.assertEqual(namespace.as_item(), ('tns', 'http://xpath.test/ns'))
        self.assertNotEqual(
            namespace, NamespaceNode('tns', 'http://xpath.test/ns', parent=context.root)
        )

        namespace = NamespaceNode('tns', 'http://xpath.test/ns', parent=context.root)
        self.assertEqual(repr(namespace), "NamespaceNode(prefix='tns', uri='http://xpath.test/ns')")

        self.assertNotEqual(namespace,
                            NamespaceNode('tns', 'http://xpath.test/ns', parent=context.root))
        self.assertEqual(namespace.as_item(), ('tns', 'http://xpath.test/ns'))
        self.assertNotEqual(namespace, NamespaceNode('tns', 'http://xpath.test/ns'))

    def test_node_children_function(self):
        self.assertListEqual(EtreeElementNode(self.elem).children, [])
        elem = EtreeElementNode(ElementTree.XML("<A><B1/><B2/></A>"))
        self.assertListEqual(elem.children, [x for x in elem])

        document = DocumentNode(ElementTree.parse(io.StringIO("<A><B1/><B2/></A>")))
        self.assertListEqual(document.children, [])  # not built document
        document.children.append(EtreeElementNode(document.value.getroot(), document))
        self.assertListEqual(document.children, [document.getroot()])

        self.assertIsNone(TextNode('a text node').children)

    def test_node_nilled_property(self):
        xml_test = '<A xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="true" />'
        self.assertTrue(EtreeElementNode(ElementTree.XML(xml_test)).nilled)
        xml_test = '<A xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="false" />'
        self.assertFalse(EtreeElementNode(ElementTree.XML(xml_test)).nilled)
        self.assertFalse(EtreeElementNode(ElementTree.XML('<A />')).nilled)
        self.assertFalse(TextNode('foo').nilled)

    def test_node_kind_property(self):
        document = DocumentNode(ElementTree.parse(io.StringIO(u'<A/>')))
        element = EtreeElementNode(ElementTree.Element('schema'))
        attribute = AttributeNode('id', '0212349350')
        namespace = NamespaceNode('xs', 'http://www.w3.org/2001/XMLSchema')
        comment = CommentNode(ElementTree.Comment('nothing important'))
        pi = ProcessingInstructionNode(
            ElementTree.ProcessingInstruction('action', 'nothing to do')
        )
        text = TextNode('betelgeuse')

        self.assertEqual(document.node_kind, 'document')
        self.assertEqual(element.node_kind, 'element')
        self.assertEqual(attribute.node_kind, 'attribute')
        self.assertEqual(namespace.node_kind, 'namespace')
        self.assertEqual(comment.node_kind, 'comment')
        self.assertEqual(pi.node_kind, 'processing-instruction')
        self.assertEqual(text.node_kind, 'text')

    def test_name_property(self):
        root = self.context.root
        attr = AttributeNode('a1', '20')
        namespace = NamespaceNode('xs', 'http://www.w3.org/2001/XMLSchema')

        self.assertEqual(root.name, 'root')
        self.assertEqual(attr.name, 'a1')
        self.assertEqual(namespace.name, 'xs')

    def test_path_property(self):
        root = ElementTree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2 max="10"/></B3></A>')

        context = XPathContext(root)

        self.assertEqual(context.root.path, '/Q{}A[1]')
        self.assertEqual(context.root[0].path, '/Q{}A[1]/Q{}B1[1]')
        self.assertEqual(context.root[0][0].path, '/Q{}A[1]/Q{}B1[1]/Q{}C1[1]')
        self.assertEqual(context.root[1].path, '/Q{}A[1]/Q{}B2[1]')
        self.assertEqual(context.root[2].path, '/Q{}A[1]/Q{}B3[1]')
        self.assertEqual(context.root[2][0].path, '/Q{}A[1]/Q{}B3[1]/Q{}C1[1]')
        self.assertEqual(context.root[2][1].path, '/Q{}A[1]/Q{}B3[1]/Q{}C2[1]')

        attr = context.root[2][1].attributes[0]
        self.assertEqual(attr.path, '/Q{}A[1]/Q{}B3[1]/Q{}C2[1]/@max')

        document = ElementTree.ElementTree(root)
        context = XPathContext(root=document)
        self.assertEqual(context.root[0][2][0].path, '/Q{}A[1]/Q{}B3[1]/Q{}C1[1]')
        self.assertEqual(context.root[0][2][0].extended_path, '/A[1]/B3[1]/C1[1]')

        root = ElementTree.XML('<A><B1>10</B1><B2 min="1"/><B3/></A>')
        context = XPathContext(root)
        with patch.object(DummyXsdType(), 'is_simple', return_value=True) as xsd_type:
            elem = context.root[0]
            elem.xsd_type = xsd_type
            self.assertEqual(elem.path, '/Q{}A[1]/Q{}B1[1]')

        with patch.object(DummyXsdType(), 'is_simple', return_value=True) as xsd_type:
            context = XPathContext(root)
            attr = context.root[1].attributes[0]
            attr.xsd_type = xsd_type
            self.assertEqual(attr.path, '/Q{}A[1]/Q{}B2[1]/@min')

    def test_path_property_with_namespaces(self):
        root = ElementTree.XML('<tns:A xmlns:tns="foo"><B1><C1/></B1><B2/>'
                               '<B3><C1/><C2 max="10"/></B3></tns:A>')

        context = XPathContext(root, namespaces={'tns': 'foo'})
        self.assertEqual(context.root.path, '/Q{foo}A[1]')
        self.assertEqual(context.root.qname_path, '/tns:A[1]')

        self.assertEqual(context.root[0].path, '/Q{foo}A[1]/Q{}B1[1]')
        self.assertEqual(context.root[0][0].qname_path, '/tns:A[1]/B1[1]/C1[1]')

    def test_element_node_iter(self):
        root = ElementTree.XML('<A>text1\n<B1 a="10">text2</B1><B2/><B3><C1>text3</C1></B3></A>')

        context = XPathContext(root)
        expected = [
            context.root, context.root.namespace_nodes[0],
            context.root[0],
            context.root[1], context.root[1].namespace_nodes[0],
            context.root[1].attributes[0], context.root[1][0],
            context.root[2], context.root[2].namespace_nodes[0],
            context.root[3], context.root[3].namespace_nodes[0],
            context.root[3][0], context.root[3][0].namespace_nodes[0],
            context.root[3][0][0]
        ]

        result = list(context.root.iter())
        self.assertListEqual(result, expected)

        root = ElementTree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2/></B3></A>')
        context = XPathContext(root)

        # iter includes also xml namespace nodes
        self.assertListEqual(
            list(e.elem for e in context.root.iter() if isinstance(e, ElementNode)),
            list(root.iter())
        )

    def test_document_node_iter(self):
        root = ElementTree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2/></B3></A>')
        doc = ElementTree.ElementTree(root)
        context = XPathContext(doc)

        self.assertListEqual(
            list(e.elem for e in context.root.iter() if isinstance(e, ElementNode)),
            list(doc.iter())
        )

    @unittest.skipIf(lxml_etree is None, 'lxml.etree is not installed')
    def test_lazy_attributes_iter__issue_72(self):
        xml = lxml_etree.fromstring('<root id="test"></root>')
        node_tree = get_node_tree(root=xml)

        nodes = list(node for node in node_tree.iter_lazy())
        self.assertListEqual(nodes, [node_tree])

        nodes = list(node for node in node_tree.iter())
        self.assertListEqual(nodes, [
            node_tree, node_tree.namespace_nodes[0], node_tree.attributes[0]
        ])

        nodes = list(node for node in node_tree.iter_lazy())
        self.assertListEqual(nodes, [
            node_tree, node_tree.namespace_nodes[0], node_tree.attributes[0]
        ])

    def test_is_schema_node(self):
        root = ElementTree.XML('<root a="10">text</root>')
        context = XPathContext(root)

        self.assertFalse(context.root.is_schema_node)
        self.assertFalse(context.root.attributes[0].is_schema_node)
        self.assertFalse(context.root.children[0].is_schema_node)

        if xmlschema is not None:
            schema = xmlschema.XMLSchema(dedent("""
                <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
                  <xs:element name="elem"/>
                  <xs:attribute name="attr" type="xs:string"/>
                </xs:schema>"""))

            context = XPathSchemaContext(schema)
            self.assertTrue(context.root.is_schema_node)  # Is the schema
            self.assertTrue(context.root.attributes[0].is_schema_node)
            self.assertTrue(context.root.children[0].is_schema_node)

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
