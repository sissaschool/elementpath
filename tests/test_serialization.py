#!/usr/bin/env python
#
# Copyright (c), 2023, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import unittest
from textwrap import dedent
from xml.etree import ElementTree

try:
    import xmlschema
except ImportError:
    xmlschema = None

from elementpath import get_node_tree
from elementpath.datatypes import QName, UntypedAtomic
from elementpath.xpath_tokens import XPathMap, XPathArray
from elementpath.serialization import get_serialization_params
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
        self.assertEqual(result, {'allow-duplicate-names': True})

        params = XPathMap(parser, items={'allow-duplicate-names': False})
        result = get_serialization_params(params)
        self.assertEqual(result, {'allow-duplicate-names': False})

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
        self.assertEqual(result, {'cdata-section-elements': cdata})

        cdata_array = XPathArray(parser, cdata)
        params = XPathMap(parser, items={'cdata-section-elements': cdata_array})
        result = get_serialization_params(params)
        self.assertEqual(result, {'cdata-section-elements': cdata})

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
        self.assertListEqual(list(result.values()), [QName('', 'foo')])

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


if __name__ == '__main__':
    unittest.main()
