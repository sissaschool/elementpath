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
from textwrap import dedent
try:
    import lxml.etree as lxml_etree
except ImportError:
    lxml_etree = None

from elementpath import AttributeNode, XPathContext, XPath2Parser, MissingContextError
from elementpath.namespaces import XML_LANG, XSD_NAMESPACE, XSD_ANY_ATOMIC_TYPE, XSD_NOTATION
from elementpath.schema_proxy import AbstractXsdSchema

try:
    # noinspection PyPackageRequirements
    import xmlschema
    from xmlschema.xpath import XMLSchemaProxy
except (ImportError, AttributeError):
    xmlschema = None

try:
    from tests import xpath_test_class
except ImportError:
    import xpath_test_class


@unittest.skipIf(xmlschema is None, "xmlschema library required.")
class XMLSchemaProxyTest(xpath_test_class.XPathTestCase):

    @classmethod
    def setUpClass(cls):
        cls.schema = xmlschema.XMLSchema('''
        <!-- Dummy schema for testing proxy API -->
        <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" 
              targetNamespace="http://xpath.test/ns">
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
        self.parser = XPath2Parser(namespaces=self.namespaces, schema=self.schema_proxy)

    def test_abstract_xsd_schema(self):
        class XsdSchema(AbstractXsdSchema):
            @property
            def attrib(self):
                return {}

            def __iter__(self):
                return iter(())

        schema = XsdSchema()
        self.assertEqual(schema.tag, '{http://www.w3.org/2001/XMLSchema}schema')
        self.assertIsNone(schema.text)

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
        self.check_value("schema-element(xs:complexType)", MissingContextError)
        self.check_value("self::schema-element(xs:complexType)", NameError, context)
        self.check_value("self::schema-element(xs:schema)", [context.item], context)
        self.check_tree("schema-element(xs:group)", '(schema-element (: (xs) (group)))')

        context.item = AttributeNode(XML_LANG, 'en')
        self.wrong_syntax("schema-attribute(*)")
        self.wrong_name("schema-attribute(nil)")
        self.wrong_name("schema-attribute(xs:string)")
        self.check_value("schema-attribute(xml:lang)", MissingContextError)
        self.check_value("schema-attribute(xml:lang)", NameError, context)
        self.check_value("self::schema-attribute(xml:lang)", [context.item], context)
        self.check_tree("schema-attribute(xsi:schemaLocation)",
                        '(schema-attribute (: (xsi) (schemaLocation)))')

        token = self.parser.parse("self::schema-attribute(xml:lang)")
        context.item = AttributeNode(XML_LANG, 'en')
        context.axis = 'attribute'
        self.assertEqual(list(token.select(context)), [context.item])

    def test_bind_parser_method(self):
        schema_src = dedent("""
            <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
                <xs:simpleType name="stringType">
                    <xs:restriction base="xs:string"/>
                </xs:simpleType>
            </xs:schema>""")
        schema = xmlschema.XMLSchema(schema_src)

        schema_proxy = XMLSchemaProxy(schema=schema)
        parser = XPath2Parser(namespaces=self.namespaces)
        self.assertFalse(parser.is_schema_bound())

        schema_proxy.bind_parser(parser)
        self.assertTrue(parser.is_schema_bound())
        self.assertIs(schema_proxy, parser.schema)

        # To test AbstractSchemaProxy.bind_parser()
        parser = XPath2Parser(namespaces=self.namespaces)
        super(XMLSchemaProxy, schema_proxy).bind_parser(parser)
        self.assertIs(schema_proxy, parser.schema)
        super(XMLSchemaProxy, schema_proxy).bind_parser(parser)
        self.assertIs(schema_proxy, parser.schema)

    def test_schema_constructors(self):
        schema_src = dedent("""
            <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
                <xs:simpleType name="stringType">
                    <xs:restriction base="xs:string"/>
                </xs:simpleType>
                <xs:simpleType name="intType">
                    <xs:restriction base="xs:int"/>
                </xs:simpleType>
            </xs:schema>""")
        schema = xmlschema.XMLSchema(schema_src)
        schema_proxy = XMLSchemaProxy(schema=schema)
        parser = XPath2Parser(namespaces=self.namespaces, schema=schema_proxy)

        with self.assertRaises(NameError) as ctx:
            parser.schema_constructor(XSD_ANY_ATOMIC_TYPE)
        self.assertIn('XPST0080', str(ctx.exception))

        with self.assertRaises(NameError) as ctx:
            parser.schema_constructor(XSD_NOTATION)
        self.assertIn('XPST0080', str(ctx.exception))

        token = parser.parse('stringType("apple")')
        self.assertEqual(token.symbol, 'stringType')
        self.assertEqual(token.label, 'constructor function')
        self.assertEqual(token.evaluate(), 'apple')

        token = parser.parse('stringType(())')
        self.assertEqual(token.symbol, 'stringType')
        self.assertEqual(token.label, 'constructor function')
        self.assertEqual(token.evaluate(), [])

        token = parser.parse('stringType(10)')
        self.assertEqual(token.symbol, 'stringType')
        self.assertEqual(token.label, 'constructor function')
        self.assertEqual(token.evaluate(), '10')

        token = parser.parse('stringType(.)')
        self.assertEqual(token.symbol, 'stringType')
        self.assertEqual(token.label, 'constructor function')

        token = parser.parse('intType(10)')
        self.assertEqual(token.symbol, 'intType')
        self.assertEqual(token.label, 'constructor function')
        self.assertEqual(token.evaluate(), 10)

        with self.assertRaises(ValueError) as ctx:
            parser.parse('intType(true())')
        self.assertIn('FORG0001', str(ctx.exception))

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

    @unittest.skipIf(xmlschema is None or xmlschema.__version__ < '1.2.3',
                     "Old find API does not work")
    def test_find_api(self):
        schema_src = """<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
                            <xs:element name="test_element" type="xs:string"/>
                        </xs:schema>"""
        schema = xmlschema.XMLSchema(schema_src)
        schema_proxy = XMLSchemaProxy(schema=schema)
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

        context = XPathContext(self.etree.XML('<root min="10" max="20" />'))
        self.assertTrue(token.evaluate(context))

        context = XPathContext(self.etree.XML('<root min="10" max="2" />'))
        self.assertTrue(token.evaluate(context))

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

        context = XPathContext(self.etree.XML('<root min="10" max="20" />'))
        self.assertTrue(token.evaluate(context))
        context = XPathContext(self.etree.XML('<root min="10" max="2" />'))
        self.assertFalse(token.evaluate(context))

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
        self.assertEqual(token[0].xsd_types['a'], schema.maps.types['{%s}string' % XSD_NAMESPACE])
        token = parser.parse("//b")
        self.assertEqual(token[0].xsd_types['b'], schema.maps.types['{%s}integer' % XSD_NAMESPACE])
        token = parser.parse("//values/c")

        self.assertEqual(token[0][0].xsd_types["{http://xpath.test/ns}values"],
                         schema.elements['values'].type)
        self.assertEqual(token[1].xsd_types['c'], schema.maps.types['{%s}boolean' % XSD_NAMESPACE])

        token = parser.parse("values/c")
        self.assertEqual(token[0].xsd_types['{http://xpath.test/ns}values'],
                         schema.elements['values'].type)
        self.assertEqual(token[1].xsd_types['c'], schema.maps.types['{%s}boolean' % XSD_NAMESPACE])

        token = parser.parse("values/*")
        self.assertEqual(token[1].xsd_types, {
            'a': schema.maps.types['{%s}string' % XSD_NAMESPACE],
            'b': schema.maps.types['{%s}integer' % XSD_NAMESPACE],
            'c': schema.maps.types['{%s}boolean' % XSD_NAMESPACE],
            'd': schema.maps.types['{%s}float' % XSD_NAMESPACE],
        })

    def test_elements_and_attributes_type(self):
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
        self.assertEqual(token[0].xsd_types['a'], schema.maps.types['{%s}string' % XSD_NAMESPACE])
        token = parser.parse("//b")
        self.assertEqual(token[0].xsd_types['b'], schema.types['rangeType'])
        token = parser.parse("values/c")

        self.assertEqual(token[0].xsd_types['{http://xpath.test/ns}values'],
                         schema.elements['values'].type)
        self.assertEqual(token[1].xsd_types['c'], schema.maps.types['{%s}boolean' % XSD_NAMESPACE])
        token = parser.parse("//b/@min")
        self.assertEqual(token[0][0].xsd_types['b'], schema.types['rangeType'])

        self.assertEqual(token[1][0].xsd_types['min'],
                         schema.maps.types['{%s}integer' % XSD_NAMESPACE])

        token = parser.parse("values/b/@min")
        self.assertEqual(token[0][0].xsd_types['{http://xpath.test/ns}values'],
                         schema.elements['values'].type)
        self.assertEqual(token[0][1].xsd_types['b'], schema.types['rangeType'])
        self.assertEqual(token[1][0].xsd_types['min'],
                         schema.maps.types['{%s}integer' % XSD_NAMESPACE])

        token = parser.parse("//b/@min lt //b/@max")
        self.assertEqual(token[0][0][0].xsd_types['b'], schema.types['rangeType'])
        self.assertEqual(token[0][1][0].xsd_types['min'],
                         schema.maps.types['{%s}integer' % XSD_NAMESPACE])
        self.assertEqual(token[1][0][0].xsd_types['b'], schema.types['rangeType'])
        self.assertEqual(token[1][1][0].xsd_types['max'],
                         schema.maps.types['{%s}integer' % XSD_NAMESPACE])

        root = self.etree.XML('<values xmlns="http://xpath.test/ns"><b min="19"/></values>')
        self.assertIsNone(token.evaluate(context=XPathContext(root)))

        root = self.etree.XML('<values xmlns="http://xpath.test/ns"><b min="19">30</b></values>')
        self.assertIsNone(token.evaluate(context=XPathContext(root)))

        root = self.etree.XML(
            '<values xmlns="http://xpath.test/ns"><b min="19" max="40">30</b></values>')
        context = XPathContext(root)
        self.assertTrue(token.evaluate(context))

        root = self.etree.XML(
            '<values xmlns="http://xpath.test/ns"><b min="19" max="10">30</b></values>')
        context = XPathContext(root)
        self.assertFalse(token.evaluate(context))

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
class LxmlXMLSchemaProxyTest(XMLSchemaProxyTest):
    etree = lxml_etree


if __name__ == '__main__':
    unittest.main()
