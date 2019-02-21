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
import unittest
import lxml.etree

from elementpath import *
from elementpath.namespaces import XML_LANG_QNAME, XSD_NAMESPACE

try:
    # noinspection PyPackageRequirements
    import xmlschema
except (ImportError, AttributeError):
    xmlschema = None

try:
    from tests import test_xpath2_parser
except ImportError:
    # Python2 fallback
    import test_xpath2_parser


@unittest.skipIf(xmlschema is None, "xmlschema library required.")
class XPath2ParserXMLSchemaTest(test_xpath2_parser.XPath2ParserTest):

    schema = XMLSchemaProxy(
        schema=xmlschema.XMLSchema('''
        <!-- Dummy schema for testing proxy API -->
        <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" targetNamespace="http://xpath.test/ns">
          <xs:element name="test_element" type="xs:string"/>
          <xs:attribute name="test_attribute" type="xs:string"/>
        </xs:schema>''')
    )

    def setUp(self):
        self.parser = XPath2Parser(namespaces=self.namespaces, schema=self.schema, variables=self.variables)

    def test_xmlschema_proxy(self):
        context = XPathContext(root=self.etree.XML('<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"/>'))

        self.wrong_name("schema-element(nil)")
        self.wrong_name("schema-element(xs:string)")
        self.check_value("schema-element(xs:complexType)", None)
        self.check_value("schema-element(xs:schema)", context.item, context)
        self.check_tree("schema-element(xs:group)", '(schema-element (: (xs) (group)))')

        context.item = AttributeNode(XML_LANG_QNAME, 'en')
        self.wrong_name("schema-attribute(nil)")
        self.wrong_name("schema-attribute(xs:string)")
        self.check_value("schema-attribute(xml:lang)", None)
        self.check_value("schema-attribute(xml:lang)", context.item, context)
        self.check_tree("schema-attribute(xsi:schemaLocation)", '(schema-attribute (: (xsi) (schemaLocation)))')

    def test_is_instance_api(self):
        self.assertFalse(self.schema.is_instance(True, '{%s}integer' % XSD_NAMESPACE))
        self.assertTrue(self.schema.is_instance(5, '{%s}integer' % XSD_NAMESPACE))
        self.assertFalse(self.schema.is_instance('alpha', '{%s}integer' % XSD_NAMESPACE))
        self.assertTrue(self.schema.is_instance('alpha', '{%s}string' % XSD_NAMESPACE))
        self.assertTrue(self.schema.is_instance('alpha beta', '{%s}token' % XSD_NAMESPACE))
        self.assertTrue(self.schema.is_instance('alpha', '{%s}Name' % XSD_NAMESPACE))
        self.assertFalse(self.schema.is_instance('alpha beta', '{%s}Name' % XSD_NAMESPACE))
        self.assertFalse(self.schema.is_instance('1alpha', '{%s}Name' % XSD_NAMESPACE))
        self.assertTrue(self.schema.is_instance('alpha', '{%s}NCName' % XSD_NAMESPACE))
        self.assertFalse(self.schema.is_instance('eg:alpha', '{%s}NCName' % XSD_NAMESPACE))

    def test_attributes_type(self):
        parser = XPath2Parser(namespaces=self.namespaces)
        token = parser.parse("@min le @max")
        self.assertTrue(token.evaluate(context=XPathContext(self.etree.XML('<root min="10" max="20" />'))))
        self.assertTrue(token.evaluate(context=XPathContext(self.etree.XML('<root min="10" max="2" />'))))

        schema = xmlschema.XMLSchema('''
            <xs:schema xmlns="http://xpath.test/ns" xmlns:xs="http://www.w3.org/2001/XMLSchema"
                targetNamespace="http://xpath.test/ns">
              <xs:element name="range" type="intRange"/>
              <xs:complexType name="intRange">
                <xs:attribute name="min" type="xs:int"/>
                <xs:attribute name="max" type="xs:int"/>
              </xs:complexType>
            </xs:schema>''')
        parser = XPath2Parser(namespaces=self.namespaces, schema=XMLSchemaProxy(schema, schema.elements['range']))
        token = parser.parse("@min le @max")
        self.assertTrue(token.evaluate(context=XPathContext(self.etree.XML('<root min="10" max="20" />'))))
        self.assertFalse(token.evaluate(context=XPathContext(self.etree.XML('<root min="10" max="2" />'))))

        schema = xmlschema.XMLSchema('''
            <xs:schema xmlns="http://xpath.test/ns" xmlns:xs="http://www.w3.org/2001/XMLSchema"
                targetNamespace="http://xpath.test/ns">
              <xs:element name="range" type="intRange"/>
              <xs:complexType name="intRange">
                <xs:attribute name="min" type="xs:int"/>
                <xs:attribute name="max" type="xs:string"/>
              </xs:complexType>
            </xs:schema>''')
        parser = XPath2Parser(namespaces=self.namespaces, schema=XMLSchemaProxy(schema, schema.elements['range']))
        if PY3:
            self.assertRaises(TypeError, parser.parse, '@min le @max')
        else:
            # In Python 2 strings and numbers are comparable and strings are 'greater than' numbers.
            token = parser.parse("@min le @max")
            self.assertTrue(token.evaluate(context=XPathContext(self.etree.XML('<root min="10" max="20" />'))))
            self.assertTrue(token.evaluate(context=XPathContext(self.etree.XML('<root min="10" max="2" />'))))

    def test_elements_type(self):
        schema = xmlschema.XMLSchema('''
            <xs:schema xmlns="http://xpath.test/ns" xmlns:xs="http://www.w3.org/2001/XMLSchema"
                    targetNamespace="http://xpath.test/ns">
                <xs:element name="values">
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element name="a" type="xs:string"/>
                            <xs:element name="b" type="xs:integer"/>
                            <xs:element name="c" type="xs:boolean"/>
                            <xs:element name="d" type="xs:float"/>
                        </xs:sequence>
                    </xs:complexType>
                </xs:element>
            </xs:schema>''')
        parser = XPath2Parser(namespaces={'': "http://xpath.test/ns", 'xs': XSD_NAMESPACE},
                              schema=XMLSchemaProxy(schema))
        token = parser.parse("//a")
        self.assertEqual(token[0].xsd_type, schema.maps.types['{%s}string' % XSD_NAMESPACE])
        token = parser.parse("//b")
        self.assertEqual(token[0].xsd_type, schema.maps.types['{%s}integer' % XSD_NAMESPACE])
        token = parser.parse("//values/c")
        self.assertEqual(token[0][0].xsd_type, schema.elements['values'].type)
        self.assertEqual(token[1].xsd_type, schema.maps.types['{%s}boolean' % XSD_NAMESPACE])
        token = parser.parse("values/c")
        self.assertEqual(token[0].xsd_type, schema.elements['values'].type)
        self.assertEqual(token[1].xsd_type, schema.maps.types['{%s}boolean' % XSD_NAMESPACE])

        schema = xmlschema.XMLSchema('''
            <xs:schema xmlns="http://xpath.test/ns" xmlns:xs="http://www.w3.org/2001/XMLSchema"
                    targetNamespace="http://xpath.test/ns">
                <xs:element name="values">
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element name="a" type="xs:string"/>
                            <xs:element name="b" type="rangeType"/>
                            <xs:element name="c" type="xs:boolean"/>
                            <xs:element name="d" type="xs:float"/>
                        </xs:sequence>
                    </xs:complexType>
                </xs:element>
                <xs:complexType name="rangeType">
                    <xs:simpleContent>
                        <xs:extension base="xs:integer">
                            <xs:attribute name="min" type="xs:integer"/>
                            <xs:attribute name="max" type="xs:integer"/>
                        </xs:extension>
                    </xs:simpleContent>
                </xs:complexType>
            </xs:schema>''')
        parser = XPath2Parser(namespaces={'': "http://xpath.test/ns", 'xs': XSD_NAMESPACE},
                              schema=XMLSchemaProxy(schema))
        token = parser.parse("//a")
        self.assertEqual(token[0].xsd_type, schema.maps.types['{%s}string' % XSD_NAMESPACE])
        token = parser.parse("//b")
        self.assertEqual(token[0].xsd_type, schema.types['rangeType'])
        token = parser.parse("values/c")
        self.assertEqual(token[0].xsd_type, schema.elements['values'].type)
        self.assertEqual(token[1].xsd_type, schema.maps.types['{%s}boolean' % XSD_NAMESPACE])
        token = parser.parse("//b/@min")
        self.assertEqual(token[0][0].xsd_type, schema.types['rangeType'])
        self.assertEqual(token[1][0].xsd_type, schema.maps.types['{%s}integer' % XSD_NAMESPACE])
        token = parser.parse("values/b/@min")
        self.assertEqual(token[0][0].xsd_type, schema.elements['values'].type)
        self.assertEqual(token[0][1].xsd_type, schema.types['rangeType'])
        self.assertEqual(token[1][0].xsd_type, schema.maps.types['{%s}integer' % XSD_NAMESPACE])

        context = XPathContext(root=self.etree.XML('<values xmlns="http://xpath.test/ns"><b min="19"/></values>'))
        token = parser.parse("//b/@min lt //b/@max")
        self.assertEqual(token[0][0][0].xsd_type, schema.types['rangeType'])
        self.assertEqual(token[0][1][0].xsd_type, schema.maps.types['{%s}integer' % XSD_NAMESPACE])
        self.assertEqual(token[1][0][0].xsd_type, schema.types['rangeType'])
        self.assertEqual(token[1][1][0].xsd_type, schema.maps.types['{%s}integer' % XSD_NAMESPACE])
        self.assertIsNone(token.evaluate(context))

    def test_instance_of_expression(self):
        element = self.etree.Element('schema')
        context = XPathContext(element)

        # Test cases from https://www.w3.org/TR/xpath20/#id-instance-of
        self.check_value("5 instance of xs:integer", True)
        self.check_value("5 instance of xs:decimal", True)
        self.check_value("9.0 instance of xs:integer", False if xmlschema.__version__ >= '1.0.8' else True)
        self.check_value("(5, 6) instance of xs:integer+", True)
        self.check_value(". instance of element()", True, context)

        self.check_value("(5, 6) instance of xs:integer", False)
        self.check_value("(5, 6) instance of xs:integer*", True)
        self.check_value("(5, 6) instance of xs:integer?", False)

        self.check_value("5 instance of empty-sequence()", False)
        self.check_value("() instance of empty-sequence()", True)

    def test_treat_as_expression(self):
        element = self.etree.Element('schema')
        context = XPathContext(element)

        self.check_value("5 treat as xs:integer", [5])
        # self.check_value("5 treat as xs:string", ElementPathTypeError)   # FIXME: a bug of xmlschema!
        self.check_value("5 treat as xs:decimal", [5])
        self.check_value("(5, 6) treat as xs:integer+", [5, 6])
        self.check_value(". treat as element()", [element], context)

        self.check_value("(5, 6) treat as xs:integer", ElementPathTypeError)
        self.check_value("(5, 6) treat as xs:integer*", [5, 6])
        self.check_value("(5, 6) treat as xs:integer?", ElementPathTypeError)

        self.check_value("5 treat as empty-sequence()", ElementPathTypeError)
        self.check_value("() treat as empty-sequence()", [])

    def test_castable_expression(self):
        self.check_value("5 castable as xs:integer", True)
        self.check_value("'5' castable as xs:integer", True)
        self.check_value("'hello' castable as xs:integer", False)
        self.check_value("('5', '6') castable as xs:integer", False)
        self.check_value("() castable as xs:integer", False)
        self.check_value("() castable as xs:integer?", True)

    def test_cast_expression(self):
        self.check_value("5 cast as xs:integer", 5)
        self.check_value("'5' cast as xs:integer", 5)
        self.check_value("'hello' cast as xs:integer", ElementPathValueError)
        self.check_value("('5', '6') cast as xs:integer", ElementPathTypeError)
        self.check_value("() cast as xs:integer", ElementPathValueError)
        self.check_value("() cast as xs:integer?", [])
        self.check_value('"1" cast as xs:boolean', True)
        self.check_value('"0" cast as xs:boolean', False)


@unittest.skipIf(xmlschema is None, "xmlschema library >= v1.0.7 required.")
class LxmlXPath2ParserXMLSchemaTest(XPath2ParserXMLSchemaTest):
    etree = lxml.etree


if __name__ == '__main__':
    unittest.main()
