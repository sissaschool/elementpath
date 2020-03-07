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
import math
import xml.etree.ElementTree as ElementTree
from collections import namedtuple

try:
    import xmlschema
except ImportError:
    xmlschema = None
else:
    xmlschema.XMLSchema.meta_schema.build()

from elementpath.exceptions import MissingContextError
from elementpath.datatypes import UntypedAtomic
from elementpath.namespaces import XSD_NAMESPACE
from elementpath.xpath_nodes import AttributeNode, TypedAttribute, TypedElement, NamespaceNode
from elementpath.xpath_token import ordinal
from elementpath.xpath_context import XPathContext
from elementpath.xpath1_parser import XPath1Parser
from elementpath.xpath2_parser import XPath2Parser


class XPath1TokenTest(unittest.TestCase):

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

    def test_get_argument_method(self):
        token = self.parser.symbol_table['true'](self.parser)

        self.assertIsNone(token.get_argument(2))
        with self.assertRaises(TypeError):
            token.get_argument(1, required=True)

    def test_select_results(self):
        token = self.parser.parse('.')
        elem = ElementTree.Element('A', attrib={'max': '30'})
        elem.text = '10'

        context = XPathContext(elem)
        self.assertListEqual(list(token.select_results(context)), [elem])

        context = XPathContext(elem, item=TypedElement(elem, 10))
        self.assertListEqual(list(token.select_results(context)), [elem])

        context = XPathContext(elem, item=AttributeNode('max', '30'))
        self.assertListEqual(list(token.select_results(context)), ['30'])

        context = XPathContext(elem, item=TypedAttribute(AttributeNode('max', '30'), 30))
        self.assertListEqual(list(token.select_results(context)), [30])

        attribute = namedtuple('XsdAttribute', 'name type')('max', 'xs:string')
        context = XPathContext(elem, item=TypedAttribute(AttributeNode('max', attribute), 30))
        self.assertListEqual(list(token.select_results(context)), [attribute])

        context = XPathContext(elem, item=10)
        self.assertListEqual(list(token.select_results(context)), [10])

        context = XPathContext(elem, item='10')
        self.assertListEqual(list(token.select_results(context)), ['10'])

    def test_boolean_value_function(self):
        token = self.parser.parse('true()')
        elem = ElementTree.Element('A')
        with self.assertRaises(TypeError):
            token.boolean_value(elem)

        self.assertFalse(token.boolean_value([]))
        self.assertTrue(token.boolean_value([elem]))
        self.assertFalse(token.boolean_value([0]))
        self.assertTrue(token.boolean_value([1]))
        with self.assertRaises(TypeError):
            token.boolean_value([1, 1])
        with self.assertRaises(TypeError):
            token.boolean_value(elem)
        self.assertFalse(token.boolean_value(0))
        self.assertTrue(token.boolean_value(1))

    def test_data_value_function(self):
        token = self.parser.parse('true()')
        self.assertIsNone(token.data_value(None))

    def test_string_value_function(self):
        token = self.parser.parse('true()')

        document = ElementTree.parse(io.StringIO(u'<A>123<B1>456</B1><B2>789</B2></A>'))
        element = ElementTree.Element('schema')
        attribute = AttributeNode('id', '0212349350')
        namespace = NamespaceNode('xs', 'http://www.w3.org/2001/XMLSchema')
        comment = ElementTree.Comment('nothing important')
        pi = ElementTree.ProcessingInstruction('action', 'nothing to do')
        text = 'betelgeuse'
        self.assertEqual(token.string_value(document), '123456789')
        self.assertEqual(token.string_value(element), '')
        self.assertEqual(token.string_value(attribute), '0212349350')
        self.assertEqual(token.string_value(namespace), 'http://www.w3.org/2001/XMLSchema')
        self.assertEqual(token.string_value(comment), 'nothing important')
        self.assertEqual(token.string_value(pi), 'action nothing to do')
        self.assertEqual(token.string_value(text), 'betelgeuse')
        self.assertEqual(token.string_value(None), '')
        self.assertEqual(token.string_value(10), '10')

    def test_number_value_function(self):
        token = self.parser.parse('true()')
        self.assertEqual(token.number_value("19"), 19)
        self.assertTrue(math.isnan(token.number_value("not a number")))

    def test_compare_operator(self):
        token1 = self.parser.parse('true()')
        token2 = self.parser.parse('false()')
        self.assertEqual(token1, token1)
        self.assertNotEqual(token1, token2)
        self.assertNotEqual(token2, 'false()')

    def test_arity_property(self):
        token = self.parser.parse('true()')
        self.assertEqual(token.symbol, 'true')
        self.assertEqual(token.label, 'function')
        self.assertEqual(token.arity, 0)

        token = self.parser.parse('2 + 5')
        self.assertEqual(token.symbol, '+')
        self.assertEqual(token.label, 'operator')
        self.assertEqual(token.arity, 2)

    def test_source_property(self):
        token = self.parser.parse('last()')
        self.assertEqual(token.symbol, 'last')
        self.assertEqual(token.label, 'function')
        self.assertEqual(token.source, 'last()')

        token = self.parser.parse('2.0')
        self.assertEqual(token.symbol, '(decimal)')
        self.assertEqual(token.label, 'literal')
        self.assertEqual(token.source, '2.0')

    def test_iter_method(self):
        token = self.parser.parse('2 + 5')
        items = [tk for tk in token.iter()]
        self.assertListEqual(items, [token[0], token, token[1]])

    def test_xpath_error_shortcuts(self):
        token = self.parser.parse('.')

        with self.assertRaises(ValueError) as err:
            token.wrong_value()
        self.assertIn('FOCA0002', str(err.exception))

        with self.assertRaises(TypeError) as err:
            token.wrong_type()
        self.assertIn('FORG0006', str(err.exception))

        with self.assertRaises(ValueError) as err:
            token.missing_schema()
        self.assertIn('XPST0001', str(err.exception))

        with self.assertRaises(MissingContextError) as err:
            token.missing_context()
        self.assertIn('XPDY0002', str(err.exception))

        with self.assertRaises(TypeError) as err:
            token.wrong_context_type()
        self.assertIn('XPTY0004', str(err.exception))

        with self.assertRaises(ValueError) as err:
            token.missing_sequence()
        self.assertIn('XPST0005', str(err.exception))

        with self.assertRaises(NameError) as err:
            token.missing_name()
        self.assertIn('XPST0008', str(err.exception))

        with self.assertRaises(NameError) as err:
            token.missing_axis()
        self.assertIn('XPST0010', str(err.exception))

        with self.assertRaises(TypeError) as err:
            token.wrong_nargs()
        self.assertIn('XPST0017', str(err.exception))

        with self.assertRaises(TypeError) as err:
            token.wrong_step_result()
        self.assertIn('XPTY0018', str(err.exception))

        with self.assertRaises(TypeError) as err:
            token.wrong_intermediate_step_result()
        self.assertIn('XPTY0019', str(err.exception))

        with self.assertRaises(TypeError) as err:
            token.wrong_axis_argument()
        self.assertIn('XPTY0020', str(err.exception))

        with self.assertRaises(TypeError) as err:
            token.wrong_sequence_type()
        self.assertIn('XPDY0050', str(err.exception))

        with self.assertRaises(NameError) as err:
            token.unknown_atomic_type()
        self.assertIn('XPST0051', str(err.exception))

        with self.assertRaises(NameError) as err:
            token.wrong_target_type()
        self.assertIn('XPST0080', str(err.exception))

        with self.assertRaises(NameError) as err:
            token.unknown_namespace()
        self.assertIn('XPST0081', str(err.exception))


class XPath2TokenTest(XPath1TokenTest):

    @classmethod
    def setUpClass(cls):
        cls.parser = XPath2Parser(namespaces={'xs': XSD_NAMESPACE, 'tst': "http://xpath.test/ns"})

    @unittest.skipIf(xmlschema is None, "xmlschema library required.")
    def test_add_xsd_type(self):
        schema = xmlschema.XMLSchema("""
            <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
              <xs:element name="a1" type="xs:int"/>
              <xs:element name="a2" type="xs:string"/>
              <xs:element name="a3" type="xs:boolean"/>
            </xs:schema>""")

        root_token = self.parser.parse('a1')
        self.assertIsNone(root_token.xsd_types)
        root_token.add_xsd_type('a1', schema.meta_schema.types['int'])
        self.assertEqual(root_token.xsd_types, {'a1': schema.meta_schema.types['int']})

        self.parser.schema = xmlschema.xpath.XMLSchemaProxy(schema)

        try:
            root_token = self.parser.parse('a1')
            self.assertEqual(root_token.xsd_types, {'a1': schema.meta_schema.types['int']})
            root_token = self.parser.parse('a2')
            self.assertEqual(root_token.xsd_types, {'a2': schema.meta_schema.types['string']})
            root_token = self.parser.parse('a3')
            self.assertEqual(root_token.xsd_types, {'a3': schema.meta_schema.types['boolean']})

            root_token = self.parser.parse('*')
            self.assertEqual(root_token.xsd_types, {
                'a1': schema.meta_schema.types['int'],
                'a2': schema.meta_schema.types['string'],
                'a3': schema.meta_schema.types['boolean'],
            })

            root_token = self.parser.parse('.')
            self.assertIsNone(root_token.xsd_types)
            self.parser.schema = xmlschema.xpath.XMLSchemaProxy(schema, schema.elements['a2'])
            root_token = self.parser.parse('.')
            self.assertEqual(root_token.xsd_types, {'a2': schema.meta_schema.types['string']})

        finally:
            self.parser.schema = None

        schema = xmlschema.XMLSchema("""
            <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
              <xs:element name="a" type="aType"/>
              <xs:complexType name="aType">
                <xs:sequence>
                  <xs:element name="b1" type="b1Type"/>
                  <xs:element name="b2" type="b2Type"/>
                  <xs:element name="b3" type="b3Type"/>
                </xs:sequence>
              </xs:complexType>
              <xs:complexType name="b1Type">
                <xs:sequence>
                  <xs:element name="c1" type="xs:int"/>
                  <xs:element name="c2" type="xs:string"/>
                </xs:sequence>
              </xs:complexType>
              <xs:complexType name="b2Type">
                <xs:sequence>
                  <xs:element name="c1" type="xs:string"/>
                  <xs:element name="c2" type="xs:string"/>
                </xs:sequence>
              </xs:complexType>
              <xs:complexType name="b3Type">
                <xs:sequence>
                  <xs:element name="c1" type="xs:boolean"/>
                  <xs:element name="c2" type="xs:string"/>
                </xs:sequence>
              </xs:complexType>
            </xs:schema>""")
        self.parser.schema = xmlschema.xpath.XMLSchemaProxy(schema, schema.elements['a'])

        try:
            root_token = self.parser.parse('.')
            self.assertEqual(root_token.xsd_types, {'a': schema.types['aType']})
            root_token = self.parser.parse('*')
            self.assertEqual(root_token.xsd_types, {
                'b1': schema.types['b1Type'],
                'b2': schema.types['b2Type'],
                'b3': schema.types['b3Type'],
            })

            root_token = self.parser.parse('b1')
            self.assertEqual(root_token.xsd_types, {'b1': schema.types['b1Type']})
            root_token = self.parser.parse('b2')
            self.assertEqual(root_token.xsd_types, {'b2': schema.types['b2Type']})

            root_token = self.parser.parse('b')
            self.assertIsNone(root_token.xsd_types)

            root_token = self.parser.parse('*/c1')
            self.assertEqual(root_token[0].xsd_types, {
                'b1': schema.types['b1Type'],
                'b2': schema.types['b2Type'],
                'b3': schema.types['b3Type'],
            })
            self.assertEqual(root_token[1].xsd_types, {'c1': [
                schema.meta_schema.types['int'],
                schema.meta_schema.types['string'],
                schema.meta_schema.types['boolean'],
            ]})

            root_token = self.parser.parse('*/c2')
            self.assertEqual(root_token[1].xsd_types, {'c2': schema.meta_schema.types['string']})

            root_token = self.parser.parse('*/*')
            self.assertEqual(root_token[1].xsd_types, {
                'c1': [schema.meta_schema.types['int'],
                       schema.meta_schema.types['string'],
                       schema.meta_schema.types['boolean']],
                'c2': schema.meta_schema.types['string']
            })

        finally:
            self.parser.schema = None

    @unittest.skipIf(xmlschema is None, "xmlschema library required.")
    def test_match_xsd_type(self):
        schema = xmlschema.XMLSchema("""
            <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
              <xs:element name="root" type="xs:int"/>
              <xs:attribute name="a" type="xs:string"/>
            </xs:schema>""")
        self.parser.schema = xmlschema.xpath.XMLSchemaProxy(schema)

        try:
            root_token = self.parser.parse('root')
            self.assertEqual(root_token.xsd_types, {'root': schema.meta_schema.types['int']})

            obj = root_token.match_xsd_type(schema.elements['root'], 'root')
            self.assertIsInstance(obj, TypedElement)
            self.assertEqual(root_token.xsd_types, {'root': schema.meta_schema.types['int']})

            root_token.xsd_types = None
            root_token.match_xsd_type(schema, 'root')
            self.assertIsNone(root_token.xsd_types)

            obj = root_token.match_xsd_type(schema.elements['root'], 'root')
            self.assertIsInstance(obj, TypedElement)

            obj = root_token.match_xsd_type(schema.meta_schema.types['string'], 'root')
            self.assertIsNone(obj)

            root_token = self.parser.parse('@a')
            self.assertEqual(root_token[0].xsd_types, {'a': schema.meta_schema.types['string']})

            attribute = AttributeNode('a', schema.attributes['a'])
            obj = root_token.match_xsd_type(attribute, 'a')
            self.assertIsInstance(obj, TypedAttribute)
            self.assertEqual(root_token[0].xsd_types, {'a': schema.meta_schema.types['string']})

            root_token.xsd_types = None
            root_token.match_xsd_type(schema, 'a')
            self.assertIsNone(root_token.xsd_types)

            obj = root_token.match_xsd_type(attribute, 'a')
            self.assertIsInstance(obj, TypedAttribute)
            self.assertEqual(obj[0], attribute)
            self.assertIsInstance(obj[1], str)
            self.assertEqual(root_token[0].xsd_types, {'a': schema.meta_schema.types['string']})

        finally:
            self.parser.schema = None

    @unittest.skipIf(xmlschema is None, "xmlschema library required.")
    def test_get_xsd_type(self):
        schema = xmlschema.XMLSchema("""
            <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
              <xs:element name="root" type="xs:int"/>
              <xs:attribute name="a" type="xs:string"/>
            </xs:schema>""")

        root_token = self.parser.parse('root')
        self.assertIsNone(root_token.xsd_types)
        self.assertIsNone(root_token.get_xsd_type('root'))

        self.parser.schema = xmlschema.xpath.XMLSchemaProxy(schema)

        try:
            root_token = self.parser.parse('root')
            self.assertEqual(root_token.xsd_types, {'root': schema.meta_schema.types['int']})

            xsd_type = root_token.get_xsd_type('root')
            self.assertEqual(xsd_type, schema.meta_schema.types['int'])
            self.assertIsNone(root_token.get_xsd_type('node'))

            root_token.add_xsd_type('node', schema.meta_schema.types['float'])
            root_token.add_xsd_type('node', schema.meta_schema.types['boolean'])
            root_token.add_xsd_type('node', schema.meta_schema.types['decimal'])

            xsd_type = root_token.get_xsd_type('node')
            self.assertEqual(xsd_type, schema.meta_schema.types['float'])

            xsd_type = root_token.get_xsd_type(AttributeNode('node', 'false'))
            self.assertEqual(xsd_type, schema.meta_schema.types['boolean'])
            xsd_type = root_token.get_xsd_type(AttributeNode('node', 'alpha'))
            self.assertEqual(xsd_type, schema.meta_schema.types['float'])

            elem = ElementTree.Element('node')
            elem.text = 'false'
            xsd_type = root_token.get_xsd_type(elem)
            self.assertEqual(xsd_type, schema.meta_schema.types['boolean'])
            elem.text = 'alpha'
            xsd_type = root_token.get_xsd_type(elem)
            self.assertEqual(xsd_type, schema.meta_schema.types['float'])

        finally:
            self.parser.schema = None

        schema = xmlschema.XMLSchema("""
            <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
              <xs:element name="a" type="aType"/>
              <xs:complexType name="aType">
                <xs:sequence>
                  <xs:element name="b1" type="xs:int"/>
                  <xs:element name="b2" type="xs:boolean"/>
                </xs:sequence>
              </xs:complexType>
            </xs:schema>""")
        self.parser.schema = xmlschema.xpath.XMLSchemaProxy(schema)

        try:
            root_token = self.parser.parse('a')
            elem = ElementTree.Element('a')
            elem.append(ElementTree.Element('b1'))
            elem.append(ElementTree.Element('b2'))
            elem[0].text = 14
            elem[1].text = 'true'

            self.assertEqual(root_token.get_xsd_type(elem), schema.types['aType'])

            root_token.add_xsd_type('a', schema.meta_schema.types['float'])
            self.assertEqual(root_token.get_xsd_type(elem), schema.types['aType'])

            root_token.xsd_types['a'].insert(0, schema.meta_schema.types['boolean'])
            self.assertEqual(root_token.get_xsd_type(elem), schema.types['aType'])

            del elem[1]
            self.assertEqual(root_token.get_xsd_type(elem), schema.meta_schema.types['boolean'])

        finally:
            self.parser.schema = None

    @unittest.skipIf(xmlschema is None, "xmlschema library required.")
    def test_get_typed_node(self):
        schema = xmlschema.XMLSchema("""
            <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
              <xs:element name="root" type="xs:int"/>
              <xs:attribute name="a" type="xs:int"/>
            </xs:schema>""")

        self.parser.schema = xmlschema.xpath.XMLSchemaProxy(schema)

        try:
            root_token = self.parser.parse('root')
            elem = ElementTree.Element('root')
            elem.text = '49'
            node = root_token.get_typed_node(elem)
            self.assertIsInstance(node, TypedElement)
            self.assertEqual(node[1], 49)

            elem.text = 'beta'
            with self.assertRaises(TypeError) as err:
                root_token.get_typed_node(elem)
            self.assertIn('XPDY0050', str(err.exception))
            self.assertIn('does not match sequence type', str(err.exception))

            root_token.xsd_types['root'] = schema.meta_schema.types['anySimpleType']
            elem.text = '36'
            node = root_token.get_typed_node(elem)
            self.assertIsInstance(node, TypedElement)
            self.assertIsInstance(node[1], UntypedAtomic)
            self.assertEqual(node[1], 36)

            root_token.xsd_types['root'] = schema.meta_schema.types['anyType']
            self.assertIs(root_token.get_typed_node(elem), elem)

            root_token = self.parser.parse('@a')
            self.assertEqual(root_token[0].xsd_types, {'a': schema.meta_schema.types['int']})

            attribute = AttributeNode('a', '10')
            node = root_token[0].get_typed_node(attribute)
            self.assertIsInstance(node, TypedAttribute)
            self.assertEqual(node[1], 10)

            root_token[0].xsd_types['a'] = schema.meta_schema.types['anyType']
            node = root_token[0].get_typed_node(attribute)
            self.assertIsInstance(node, TypedAttribute)
            self.assertIsInstance(node[1], UntypedAtomic)
            self.assertEqual(node[1], 10)

        finally:
            self.parser.schema = None

    def test_string_value_function(self):
        super(XPath2TokenTest, self).test_string_value_function()

        if xmlschema is not None:
            schema = xmlschema.XMLSchema("""
                <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
                  <xs:element name="root" type="xs:int"/>
                </xs:schema>""")

            token = self.parser.parse('.')
            self.parser.schema = xmlschema.xpath.XMLSchemaProxy(schema)
            try:
                value = token.string_value(schema.elements['root'])
                self.assertIsInstance(value, str)
                self.assertEqual(value, '1')
            finally:
                self.parser.schema = None

    @unittest.skipIf(xmlschema is None, "xmlschema library required.")
    def test_schema_node_value(self):
        schema = xmlschema.XMLSchema("""
            <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
              <xs:element name="a" type="aType"/>
              <xs:complexType name="aType">
                <xs:sequence>
                  <xs:element name="b1" type="xs:int"/>
                  <xs:element name="b2" type="xs:boolean"/>
                </xs:sequence>
              </xs:complexType>
              
              <xs:element name="b" type="xs:int"/>
              <xs:element name="c"/>
              
              <xs:element name="d" type="dType"/>
              <xs:simpleType name="dType">
                <xs:restriction base="xs:float"/>
              </xs:simpleType>
              
              <xs:element name="e" type="eType"/>
              <xs:simpleType name="eType">
                <xs:union memberTypes="xs:string xs:integer xs:boolean"/>
              </xs:simpleType>
            </xs:schema>""")

        token = self.parser.parse('true()')

        with self.assertRaises(ValueError) as err:
            token.schema_node_value(schema.elements['d'])
        self.assertIn('XPST0001', str(err.exception))

        self.parser.schema = xmlschema.xpath.XMLSchemaProxy()
        try:
            token.string_value(schema.elements['a'])
        finally:
            self.parser.schema = None

        self.parser.schema = xmlschema.xpath.XMLSchemaProxy(schema)
        try:
            with self.assertRaises(TypeError) as err:
                token.schema_node_value(schema)
            self.assertIn('FORG0006', str(err.exception))

            value = token.schema_node_value(schema.elements['a'])
            self.assertIsInstance(value, UntypedAtomic)
            self.assertEqual(value, UntypedAtomic(value=''))

            value = token.schema_node_value(schema.elements['b'])
            self.assertIsInstance(value, int)
            self.assertEqual(value, 1)

            value = token.schema_node_value(schema.elements['c'])
            self.assertIsInstance(value, UntypedAtomic)
            self.assertEqual(value, UntypedAtomic(value='1'))

            value = token.schema_node_value(schema.elements['d'])
            self.assertIsInstance(value, float)
            self.assertEqual(value, 1.0)

            value = token.schema_node_value(schema.elements['e'])
            self.assertIsInstance(value, UntypedAtomic)
            self.assertEqual(value, UntypedAtomic(value='1'))
        finally:
            self.parser.schema = None


if __name__ == '__main__':
    unittest.main()
