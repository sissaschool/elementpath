#!/usr/bin/env python
#
# Copyright (c), 2023-2025, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import decimal
import sys
import unittest
from textwrap import dedent
from xml.etree import ElementTree

try:
    import xmlschema
except ImportError:
    xmlschema = None

from elementpath import get_node_tree
from elementpath.datatypes import QName, UntypedAtomic
from elementpath.xpath_nodes import TextNode, CommentNode, \
    ProcessingInstructionNode
from elementpath.xpath_tokens import XPathMap, XPathArray
from elementpath.serialization import get_serialization_params, \
    serialize_to_xml, serialize_to_json
from elementpath.xpath3 import XPath31Parser


class SerializationTest(unittest.TestCase):

    def test_get_serialization_params_from_map(self):
        parser = XPath31Parser()

        params = XPathMap(parser, items={})
        result = get_serialization_params(params)
        self.assertEqual(result, {})

        params = XPathMap(parser, items={1: 'xml', 'method': None})
        result = get_serialization_params(params)
        self.assertEqual(result, {})

        params = XPathMap(parser, items={'method': 'xml'})
        result = get_serialization_params(params)
        self.assertEqual(result, {'method': 'xml'})

        params = XPathMap(parser, items={'method': 'json'})
        result = get_serialization_params(params)
        self.assertEqual(result, {'method': 'json'})

        params = XPathMap(parser, items={'method': 'adaptive'})
        result = get_serialization_params(params)
        self.assertEqual(result, {'method': 'adaptive'})

        params = XPathMap(parser, items={'indent': True})
        result = get_serialization_params(params)
        self.assertEqual(result, {'indent': True})

        params = XPathMap(parser, items={'indent': False})
        result = get_serialization_params(params)
        self.assertEqual(result, {'indent': False})

        params = XPathMap(parser, items={'indent': UntypedAtomic('true')})
        result = get_serialization_params(params)
        self.assertEqual(result, {'indent': True})

        params = XPathMap(parser, items={'indent': UntypedAtomic('false')})
        result = get_serialization_params(params)
        self.assertEqual(result, {'indent': False})

        params = XPathMap(parser, items={'indent': 'yes'})
        with self.assertRaises(TypeError) as ctx:
            get_serialization_params(params)
        self.assertIn('XPTY0004', str(ctx.exception))

        params = XPathMap(parser, items={'method': 'other'})
        with self.assertRaises(ValueError) as ctx:
            get_serialization_params(params)
        self.assertIn('SEPM0017', str(ctx.exception))

        params = XPathMap(parser, items={'use-character-maps': True})
        with self.assertRaises(TypeError) as ctx:
            get_serialization_params(params)
        self.assertIn('XPTY0004', str(ctx.exception))

        params = XPathMap(parser, items={'omit-xml-declaration': True})
        result = get_serialization_params(params)
        self.assertEqual(result, {'xml_declaration': False})

        params = XPathMap(parser, items={'omit-xml-declaration': False})
        result = get_serialization_params(params)
        self.assertEqual(result, {'xml_declaration': True})

        params = XPathMap(parser, items={'omit-xml-declaration': 'no'})
        with self.assertRaises(TypeError) as ctx:
            get_serialization_params(params)
        self.assertIn('XPTY0004', str(ctx.exception))

        params = XPathMap(parser, items={'item-separator': ';'})
        result = get_serialization_params(params)
        self.assertEqual(result, {'item_separator': ';'})

        params = XPathMap(parser, items={'item-separator': UntypedAtomic('  ')})
        result = get_serialization_params(params)
        self.assertEqual(result, {'item_separator': '  '})

        params = XPathMap(parser, items={'item-separator': True})
        with self.assertRaises(TypeError) as ctx:
            get_serialization_params(params)
        self.assertIn('XPTY0004', str(ctx.exception))

        params = XPathMap(parser, items={'encoding': 'ISO-8859-1'})
        result = get_serialization_params(params)
        self.assertEqual(result, {'encoding': 'ISO-8859-1'})

        params = XPathMap(parser, items={'encoding': False})
        with self.assertRaises(TypeError) as ctx:
            get_serialization_params(params)
        self.assertIn('XPTY0004', str(ctx.exception))

        params = XPathMap(parser, items={'allow-duplicate-names': True})
        result = get_serialization_params(params)
        self.assertEqual(result, {'allow_duplicate_names': True})

        params = XPathMap(parser, items={'allow-duplicate-names': False})
        result = get_serialization_params(params)
        self.assertEqual(result, {'allow_duplicate_names': False})

        params = XPathMap(parser, items={'allow-duplicate-names': 'false'})
        with self.assertRaises(TypeError) as ctx:
            get_serialization_params(params)
        self.assertIn('XPTY0004', str(ctx.exception))

        params = XPathMap(parser, items={'json-node-output-method': 'xml'})
        result = get_serialization_params(params)
        self.assertEqual(result, {'json-node-output-method': 'xml'})

        params = XPathMap(parser, items={'json-node-output-method': True})
        with self.assertRaises(TypeError) as ctx:
            get_serialization_params(params)
        self.assertIn('XPTY0004', str(ctx.exception))

        character_map = XPathMap(parser, {'$': '£'})
        params = XPathMap(parser, {'use-character-maps': character_map})
        result = get_serialization_params(params)
        self.assertEqual(result, {'character_map': {'$': '£'}})

        character_map = XPathMap(parser, {'$': 1})
        params = XPathMap(parser, {'use-character-maps': character_map})
        with self.assertRaises(TypeError) as ctx:
            get_serialization_params(params)
        self.assertIn('XPTY0004', str(ctx.exception))

        character_map = XPathMap(parser, {'$$': '£'})
        params = XPathMap(parser, {'use-character-maps': character_map})
        with self.assertRaises(ValueError) as ctx:
            get_serialization_params(params)
        self.assertIn('SEPM0016', str(ctx.exception))

        params = XPathMap(parser, items={'standalone': False})
        result = get_serialization_params(params)
        self.assertEqual(result, {'standalone': False})

        params = XPathMap(parser, items={'standalone': True})
        result = get_serialization_params(params)
        self.assertEqual(result, {'standalone': True})

        params = XPathMap(parser, items={'standalone': []})
        result = get_serialization_params(params)
        self.assertEqual(result, {})

        params = XPathMap(parser, items={'standalone': 'no'})
        result = get_serialization_params(params)
        self.assertEqual(result, {'standalone': False})

        params = XPathMap(parser, items={'standalone': 'omit'})
        result = get_serialization_params(params)
        self.assertEqual(result, {})

        params = XPathMap(parser, items={'standalone': ' no '})
        with self.assertRaises(TypeError) as ctx:
            get_serialization_params(params)
        self.assertIn('XPTY0004', str(ctx.exception))

        cdata = [
            QName(uri='http://xpath.test/ns', qname='a'),
            QName(uri='http://xpath.test/ns', qname='b'),
            QName(uri='', qname='c')
        ]
        params = XPathMap(parser, items={'cdata-section-elements': cdata})
        result = get_serialization_params(params)
        self.assertEqual(result, {'cdata_section': cdata})

        cdata_array = XPathArray(parser, cdata)
        params = XPathMap(parser, items={'cdata-section-elements': cdata_array})
        result = get_serialization_params(params)
        self.assertEqual(result, {'cdata_section': cdata})

        cdata.append('wrong')
        params = XPathMap(parser, items={'cdata-section-elements': cdata})
        with self.assertRaises(TypeError) as ctx:
            get_serialization_params(params)
        self.assertIn('XPTY0004', str(ctx.exception))

        params = XPathMap(parser, items={'suppress-indentation': QName('', 'foo')})
        result = get_serialization_params(params)
        self.assertEqual(result, {'suppress-indentation': QName('', 'foo')})

        params = XPathMap(parser, items={'suppress-indentation': [QName('', 'foo')]})
        result = get_serialization_params(params)
        self.assertEqual(list(result.values()), [QName('', 'foo')])

        params = XPathMap(parser, items={'suppress-indentation': 'foo'})
        with self.assertRaises(TypeError) as ctx:
            get_serialization_params(params)
        self.assertIn('XPTY0004', str(ctx.exception))

    def test_get_serialization_params_from_element_tree(self):
        namespaces = {'output': "http://www.w3.org/2010/xslt-xquery-serialization"}

        root = ElementTree.XML(dedent("""\
            <output:serialization-parameters
                    xmlns:output="http://www.w3.org/2010/xslt-xquery-serialization">
                <output:method value="xml"/>
                <output:omit-xml-declaration value="yes"/>
                <output:item-separator value="=="/>
            </output:serialization-parameters>"""))

        params = get_node_tree(root, namespaces)
        result = get_serialization_params(params)
        self.assertEqual(result, {'method': 'xml', 'item_separator': '=='})

        root = ElementTree.XML(dedent("""\
            <output:serialization-parameters
                    xmlns:output="http://www.w3.org/2010/xslt-xquery-serialization">
                <output:use-character-maps>
                    <output:character-map character="$" map-string="£"/>
                </output:use-character-maps>
            </output:serialization-parameters>"""))

        params = get_node_tree(root, namespaces)
        result = get_serialization_params(params)
        self.assertEqual(result, {'character_map': {'$': '£'}})

        root = ElementTree.XML(dedent("""\
            <output:serialization-parameters
                    xmlns:output="http://www.w3.org/2010/xslt-xquery-serialization">
                <output:omit-xml-declaration value="no"/>
                <output:standalone value=" no "/>
            </output:serialization-parameters>"""))

        params = get_node_tree(root, namespaces)
        result = get_serialization_params(params)
        self.assertEqual(result, {'standalone': False, 'xml_declaration': True})

    def test_serialize_to_xml_function(self):
        root = ElementTree.XML("<root>1</root>")
        elements = [get_node_tree(root)]
        result = serialize_to_xml(elements)
        self.assertEqual(result, '<root>1</root>')

        root = ElementTree.XML("<root>1</root>")
        elements = [get_node_tree(root)]
        result = serialize_to_xml(elements, xml_declaration=True)
        if sys.version_info < (3, 8):
            self.assertEqual(result, '<root>1</root>')
        else:
            self.assertEqual(result, '<?xml version="1.0" encoding="utf-8"?>\n<root>1</root>')

        cdata = [
            QName(uri='http://xpath.test/ns', qname='a'),
            QName(uri='http://xpath.test/ns', qname='b'),
            QName(uri='', qname='c')
        ]
        result = serialize_to_xml(elements, cdata_section=cdata)
        self.assertEqual(result, '<root>1</root>')

        root1 = ElementTree.XML("<root><c1>£</c1><c2>$</c2></root>")
        root2 = ElementTree.XML("<root><c1>£</c1><c2>€</c2></root>")
        elements = [get_node_tree(root1), get_node_tree(root2)]
        result = serialize_to_xml(elements, character_map={'$': '£'})
        self.assertEqual(result, '<root><c1>£</c1><c2>£</c2></root>'
                                 '<root><c1>£</c1><c2>€</c2></root>')

        root1 = ElementTree.XML("<root1/>")
        root2 = ElementTree.XML("<root2/>")
        elements = [get_node_tree(root1), get_node_tree(root2)]
        result = serialize_to_xml(elements, item_separator='  ')
        self.assertEqual(result, '<root1 />  <root2 />')

        root = ElementTree.XML("<root>1<c/>2<c/>3<c/>4</root>")
        root_node = get_node_tree(root)
        elements = [x for x in root_node.children if isinstance(x, TextNode)]
        result = serialize_to_xml(elements, item_separator='-')
        self.assertEqual(result, '1-2-3-4')

        parser = XPath31Parser()
        elements = [
            XPathArray(parser, [1, 2, 3]),
            XPathArray(parser, [4, 5, 6]),
        ]
        result = serialize_to_xml(elements, item_separator=';')
        self.assertEqual(result, '1;2;3;4;5;6')

        elements = list(range(10))
        result = serialize_to_xml(elements, item_separator=',')
        self.assertEqual(result, '0,1,2,3,4,5,6,7,8,9')

    def test_serialize_to_json_function(self):
        result = serialize_to_json([])
        self.assertEqual(result, 'null')

        result = serialize_to_json(["à"])
        self.assertEqual(result, '"\\u00e0"')

        result = serialize_to_json(["à"], encoding='ascii')
        self.assertEqual(result, '"\\u00e0"')

        root = ElementTree.XML("<root>1</root>")
        elements = [get_node_tree(root)]
        result = serialize_to_json(elements)
        self.assertEqual(result, '"<root>1<\\/root>"')

        document = ElementTree.ElementTree(root)
        elements = [get_node_tree(document)]
        result = serialize_to_json(elements)
        self.assertEqual(result, '"<root>1<\\/root>"')

        root = ElementTree.XML("<root><c1>£</c1><c2>$</c2></root>")
        elements = [get_node_tree(root)]
        result = serialize_to_json(elements)
        self.assertEqual(result, r'"<root><c1>\u00a3<\/c1><c2>$<\/c2><\/root>"')

        root = ElementTree.XML("<root>1<c/>2<c/>3<c/>4</root>")
        elements = [get_node_tree(root)]
        result = serialize_to_json(elements)
        self.assertEqual(result, '"<root>1<c \\/>2<c \\/>3<c \\/>4<\\/root>"')

        root = ElementTree.XML("<root a='bar'>foo</root>")
        root_node = get_node_tree(root)
        result = serialize_to_json(root_node.children)
        self.assertEqual(result, '"foo"')
        result = serialize_to_json(root_node.attributes)
        self.assertEqual(result, '"a=\\"bar\\""')

        comment = ElementTree.Comment(' foo')
        comment_node = CommentNode(content=comment)
        result = serialize_to_json([comment_node])
        self.assertEqual(result, '"<!-- foo-->"')

        pi = ElementTree.ProcessingInstruction('foo bar')
        pi_node = ProcessingInstructionNode(target=pi)
        result = serialize_to_json([pi_node])
        self.assertEqual(result, '"<?foo bar?>"')

        parser = XPath31Parser()

        elements = [XPathArray(parser, [1, 2, 3])]
        result = serialize_to_json(elements)
        self.assertEqual(result, '[1,2,3]')

        elements = [XPathArray(parser, [float('nan'), 2, 3])]
        with self.assertRaises(TypeError) as ctx:
            serialize_to_json(elements)
        self.assertIn('SERE0020', str(ctx.exception))

        elements = [XPathArray(parser, [1, 2, float('inf')])]
        with self.assertRaises(TypeError) as ctx:
            serialize_to_json(elements)
        self.assertIn('SERE0020', str(ctx.exception))

        with self.assertRaises(TypeError) as ctx:
            serialize_to_json([set()])
        self.assertIn('SERE0021', str(ctx.exception))

        elements = list(range(10))
        with self.assertRaises(TypeError) as ctx:
            serialize_to_json(elements)
        self.assertIn('SERE0023', str(ctx.exception))

        elements = [[1, 2, 3]]
        result = serialize_to_json(elements)
        self.assertEqual(result, '[1,2,3]')

        parser = XPath31Parser()
        elements = [XPathMap(parser, [(1, 'one'), (2, 'two'), (3, 'three')])]
        result = serialize_to_json(elements)
        self.assertEqual(result, '{"1":"one","2":"two","3":"three"}')

        elements = [XPathMap(parser, [(1, ['one']), (2, 'two')])]
        result = serialize_to_json(elements)
        self.assertEqual(result, '{"1":["one"],"2":"two"}')

        elements = [XPathMap(parser, [(1, ['one', 'one']), (2, 'two')])]
        result = serialize_to_json(elements)
        self.assertEqual(result, '{"1":["one","one"],"2":"two"}')

        # Previous result was wrong, because ['one', 'one'] is mapped to an array.
        # with self.assertRaises(TypeError) as ctx:
        #    serialize_to_json(elements)
        # self.assertIn('SERE0023', str(ctx.exception))

        elements = [XPathMap(parser, [(QName('', 'one'), 1), ('one', 1)])]
        with self.assertRaises(ValueError) as ctx:
            serialize_to_json(elements)
        self.assertIn('SERE0022', str(ctx.exception))

        result = serialize_to_json(elements, allow_duplicate_names=True)
        self.assertEqual(result, '{"one":1,"one":1}')

        elements = [XPathMap(parser, [(QName('', 'one'), 1), ('two', 2)])]
        result = serialize_to_json(elements)
        self.assertEqual(result, '{"one":1,"two":2}')

        self.assertEqual(serialize_to_json([UntypedAtomic('9.0')]), '"9.0"')
        self.assertEqual(serialize_to_json([decimal.Decimal('9.0')]), '9.0')
        self.assertEqual(serialize_to_json([9.0]), '9.0')


if __name__ == '__main__':
    unittest.main()
