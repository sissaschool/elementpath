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
import xml.etree.ElementTree as ElementTree
import io
try:
    import lxml.etree as lxml_etree
except ImportError:
    lxml_etree = None

from elementpath import AttributeNode, XPathContext, XPath2Parser, ElementPathTypeError
from elementpath.namespaces import XML_LANG, XSD_NAMESPACE

try:
    # noinspection PyPackageRequirements
    import xmlschema
    from xmlschema.xpath import XMLSchemaProxy  # it works if xmlschema~=1.0.14
except (ImportError, AttributeError):
    xmlschema = None

try:
    from tests import test_xpath2_parser
except ImportError:
    import test_xpath2_parser


@unittest.skipIf(xmlschema is None, "xmlschema library required.")
class XPath2ParserXMLSchemaTest(test_xpath2_parser.XPath2ParserTest):

    @classmethod
    def setUpClass(cls):
        cls.schema = xmlschema.XMLSchema('''
        <!-- Dummy schema for testing proxy API -->
        <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" targetNamespace="http://xpath.test/ns">
          <xs:element name="test_element" type="xs:string"/>
          <xs:attribute name="test_attribute" type="xs:string"/>
          <xs:element name="A">
            <xs:complexType>
              <xs:sequence>
                <xs:element name="B1"/>
                <xs:element name="B2"/>
                <xs:element name="B3"/>
              </xs:sequence>
            </xs:complexType>
          </xs:element>
        </xs:schema>''')

    def setUp(self):
        self.schema_proxy = XMLSchemaProxy(self.schema)
        self.parser = XPath2Parser(namespaces=self.namespaces, schema=self.schema_proxy,
                                   variables=self.variables)

    def test_schema_proxy_init(self):
        schema_src = """<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
                            <xs:element name="test_element" type="xs:string"/>
                        </xs:schema>"""
        schema_tree = ElementTree.parse(io.StringIO(schema_src))

        self.assertIsInstance(XMLSchemaProxy(), XMLSchemaProxy)
        self.assertIsInstance(XMLSchemaProxy(xmlschema.XMLSchema(schema_src)), XMLSchemaProxy)
        with self.assertRaises(TypeError):
            XMLSchemaProxy(schema=schema_tree)
        with self.assertRaises(TypeError):
            XMLSchemaProxy(schema=xmlschema.XMLSchema(schema_src),
                           base_element=schema_tree)
        with self.assertRaises(TypeError):
            XMLSchemaProxy(schema=xmlschema.XMLSchema(schema_src),
                           base_element=schema_tree.getroot())

        schema = xmlschema.XMLSchema(schema_src)
        with self.assertRaises(ValueError):
            XMLSchemaProxy(base_element=schema.elements['test_element'])

    def test_xmlschema_proxy(self):
        context = XPathContext(
            root=self.etree.XML('<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"/>')
        )

        self.wrong_syntax("schema-element(*)")
        self.wrong_name("schema-element(nil)")
        self.wrong_name("schema-element(xs:string)")
        self.check_value("self::schema-element(xs:complexType)", [])
        self.check_value("self::schema-element(xs:schema)", [context.item], context)
        self.check_tree("schema-element(xs:group)", '(schema-element (: (xs) (group)))')

        context.item = AttributeNode(XML_LANG, 'en')
        self.wrong_syntax("schema-attribute(*)")
        self.wrong_name("schema-attribute(nil)")
        self.wrong_name("schema-attribute(xs:string)")
        self.check_value("self::schema-attribute(xml:lang)", [])
        self.check_select("schema-attribute(xml:lang)", [])
        self.check_value("self::schema-attribute(xml:lang)", [context.item], context)
        self.check_tree("schema-attribute(xsi:schemaLocation)",
                        '(schema-attribute (: (xsi) (schemaLocation)))')

    def test_bind_parser_method(self):
        schema_src = """<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
                            <xs:simpleType name="test_type">
                              <xs:restriction base="xs:string"/>
                            </xs:simpleType>
                        </xs:schema>"""
        schema = xmlschema.XMLSchema(schema_src)

        schema_proxy = XMLSchemaProxy(schema=schema)
        parser = XPath2Parser(namespaces=self.namespaces)
        schema_proxy.bind_parser(parser)
        self.assertIs(schema_proxy, parser.schema)
        parser = XPath2Parser(namespaces=self.namespaces)
        super(XMLSchemaProxy, schema_proxy).bind_parser(parser)
        self.assertIs(schema_proxy, parser.schema)
        super(XMLSchemaProxy, schema_proxy).bind_parser(parser)
        self.assertIs(schema_proxy, parser.schema)

    def test_get_context_method(self):
        schema_proxy = XMLSchemaProxy()
        self.assertIsInstance(schema_proxy.get_context(), XPathContext)
        self.assertIsInstance(super(XMLSchemaProxy, schema_proxy).get_context(), XPathContext)

    def test_get_type_api(self):
        schema_proxy = XMLSchemaProxy()
        self.assertIsNone(schema_proxy.get_type('unknown'))
        self.assertEqual(schema_proxy.get_type('{%s}string' % XSD_NAMESPACE),
                         xmlschema.XMLSchema.builtin_types()['string'])

    def test_get_primitive_type_api(self):
        schema_proxy = XMLSchemaProxy()
        short_type = schema_proxy.get_type('{%s}short' % XSD_NAMESPACE)
        decimal_type = schema_proxy.get_type('{%s}decimal' % XSD_NAMESPACE)
        self.assertEqual(schema_proxy.get_primitive_type(short_type), decimal_type)

        ntokens_type = schema_proxy.get_type('{%s}NMTOKENS' % XSD_NAMESPACE)
        string_type = schema_proxy.get_type('{%s}string' % XSD_NAMESPACE)
        self.assertEqual(schema_proxy.get_primitive_type(ntokens_type), string_type)

        facet_type = schema_proxy.get_type('{%s}facet' % XSD_NAMESPACE)
        any_type = schema_proxy.get_type('{%s}anyType' % XSD_NAMESPACE)
        self.assertEqual(schema_proxy.get_primitive_type(facet_type), any_type)
        self.assertEqual(schema_proxy.get_primitive_type(any_type), any_type)

        any_simple_type = schema_proxy.get_type('{%s}anySimpleType' % XSD_NAMESPACE)
        self.assertEqual(schema_proxy.get_primitive_type(any_simple_type), any_simple_type)

    def test_find_api(self):
        schema_src = """<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
                            <xs:element name="test_element" type="xs:string"/>
                        </xs:schema>"""
        schema = xmlschema.XMLSchema(schema_src)
        schema_proxy = XMLSchemaProxy(schema=schema)
        if xmlschema.__version__ == '1.0.14':
            self.assertIsNone(schema_proxy.find('/test_element'))  # Not implemented!
        else:
            self.assertEqual(schema_proxy.find('/test_element'), schema.elements['test_element'])

    def test_is_instance_api(self):
        self.assertFalse(self.schema_proxy.is_instance(True, '{%s}integer' % XSD_NAMESPACE))
        self.assertTrue(self.schema_proxy.is_instance(5, '{%s}integer' % XSD_NAMESPACE))
        self.assertFalse(self.schema_proxy.is_instance('alpha', '{%s}integer' % XSD_NAMESPACE))
        self.assertTrue(self.schema_proxy.is_instance('alpha', '{%s}string' % XSD_NAMESPACE))
        self.assertTrue(self.schema_proxy.is_instance('alpha beta', '{%s}token' % XSD_NAMESPACE))
        self.assertTrue(self.schema_proxy.is_instance('alpha', '{%s}Name' % XSD_NAMESPACE))
        self.assertFalse(self.schema_proxy.is_instance('alpha beta', '{%s}Name' % XSD_NAMESPACE))
        self.assertFalse(self.schema_proxy.is_instance('1alpha', '{%s}Name' % XSD_NAMESPACE))
        self.assertTrue(self.schema_proxy.is_instance('alpha', '{%s}NCName' % XSD_NAMESPACE))
        self.assertFalse(self.schema_proxy.is_instance('eg:alpha', '{%s}NCName' % XSD_NAMESPACE))

    def test_cast_as_api(self):
        schema_proxy = XMLSchemaProxy()
        self.assertEqual(schema_proxy.cast_as('19', '{%s}short' % XSD_NAMESPACE), 19)

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
        parser = XPath2Parser(namespaces=self.namespaces,
                              schema=XMLSchemaProxy(schema, schema.elements['range']))
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
        parser = XPath2Parser(namespaces=self.namespaces,
                              schema=XMLSchemaProxy(schema, schema.elements['range']))
        self.assertRaises(TypeError, parser.parse, '@min le @max')

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

        token = parser.parse("//b/@min lt //b/@max")
        self.assertEqual(token[0][0][0].xsd_type, schema.types['rangeType'])
        self.assertEqual(token[0][1][0].xsd_type, schema.maps.types['{%s}integer' % XSD_NAMESPACE])
        self.assertEqual(token[1][0][0].xsd_type, schema.types['rangeType'])
        self.assertEqual(token[1][1][0].xsd_type, schema.maps.types['{%s}integer' % XSD_NAMESPACE])

        root = self.etree.XML('<values xmlns="http://xpath.test/ns"><b min="19"/></values>')
        with self.assertRaises(TypeError):
            token.evaluate(context=XPathContext(root))

        root = self.etree.XML('<values xmlns="http://xpath.test/ns"><b min="19">30</b></values>')
        self.assertIsNone(token.evaluate(context=XPathContext(root)))

        root = self.etree.XML('<values xmlns="http://xpath.test/ns"><b min="19" max="40">30</b></values>')
        context = XPathContext(root)
        self.assertTrue(token.evaluate(context))

        root = self.etree.XML('<values xmlns="http://xpath.test/ns"><b min="19" max="10">30</b></values>')
        context = XPathContext(root)
        self.assertFalse(token.evaluate(context))

    def test_instance_of_expression(self):
        element = self.etree.Element('schema')

        # Test cases from https://www.w3.org/TR/xpath20/#id-instance-of
        self.check_value("5 instance of xs:integer", True)
        self.check_value("5 instance of xs:decimal", True)
        self.check_value("9.0 instance of xs:integer",
                         False if [int(n) for n in xmlschema.__version__.split('.')] >= [1, 0, 8] else True)
        self.check_value("(5, 6) instance of xs:integer+", True)

        context = XPathContext(element)
        self.check_value(". instance of element()", True, context)
        context.item = None
        self.check_value(". instance of element()", False, context)

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
        self.check_value("'hello' cast as xs:integer", ValueError)
        self.check_value("('5', '6') cast as xs:integer", TypeError)
        self.check_value("() cast as xs:integer", TypeError)
        self.check_value("() cast as xs:integer?", [])
        self.check_value('"1" cast as xs:boolean', True)
        self.check_value('"0" cast as xs:boolean', False)

    def test_issue_10(self):
        schema = xmlschema.XMLSchema('''
            <xs:schema xmlns="http://xpath.test/ns#" xmlns:xs="http://www.w3.org/2001/XMLSchema"
                    targetNamespace="http://xpath.test/ns#">
                <xs:element name="root" type="rootType" />
                <xs:simpleType name="rootType">
                    <xs:restriction base="xs:string"/>
                </xs:simpleType>
            </xs:schema>''')

        # TODO: test fail with xmlschema-1.0.17+, added namespaces as temporary fix for test.
        #  A fix for xmlschema.xpath.ElementPathMixin._get_xpath_namespaces() is required.
        root = schema.find('root', namespaces={'': 'http://xpath.test/ns#'})
        self.assertEqual(getattr(root, 'tag', None), '{http://xpath.test/ns#}root')


@unittest.skipIf(xmlschema is None or lxml_etree is None, "both xmlschema and lxml required")
class LxmlXPath2ParserXMLSchemaTest(XPath2ParserXMLSchemaTest):
    etree = lxml_etree


if __name__ == '__main__':
    unittest.main()
