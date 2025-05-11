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

from elementpath import AttributeNode, XPathContext, XPath2Parser, MissingContextError, \
    get_node_tree, ElementNode
from elementpath.namespaces import XML_LANG, XSD_NAMESPACE, XSD_ANY_ATOMIC_TYPE, XSD_NOTATION

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
        class GlobalMaps:
            types = {}
            attributes = {}
            elements = {}
            substitution_groups = {}

        class XsdSchema:
            tag = '{%s}schema' % XSD_NAMESPACE
            xsd_version = '1.1'
            maps = GlobalMaps()
            text = None

            @property
            def attrib(self):
                return {}

            def __iter__(self):
                return iter(())

            def find(self, path, namespaces=None):
                return

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

        attribute = context.item = AttributeNode(XML_LANG, 'en')
        self.wrong_syntax("schema-attribute(*)")
        self.wrong_name("schema-attribute(nil)")
        self.wrong_name("schema-attribute(xs:string)")
        self.check_value("schema-attribute(xml:lang)", MissingContextError)
        self.check_value("schema-attribute(xml:lang)", NameError, context)
        self.check_value("self::schema-attribute(xml:lang)", [context.item], context)
        self.check_tree("schema-attribute(xsi:schemaLocation)",
                        '(schema-attribute (: (xsi) (schemaLocation)))')

        token = self.parser.parse("self::schema-attribute(xml:lang)")
        context.item = attribute
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

    def test_xsd_version_api(self):
        self.assertEqual(self.schema_proxy.xsd_version, '1.0')

    def test_find_api(self):
        schema_src = """<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
                            <xs:element name="test_element" type="xs:string"/>
                        </xs:schema>"""
        schema = xmlschema.XMLSchema(schema_src)
        schema_proxy = XMLSchemaProxy(schema=schema)
        self.assertEqual(schema_proxy.find('/test_element'), schema.elements['test_element'])

    def test_get_attribute_api(self):
        self.assertIs(
            self.schema_proxy.get_attribute("{http://xpath.test/ns}test_attribute"),
            self.schema_proxy._schema.maps.attributes["{http://xpath.test/ns}test_attribute"]
        )

    def test_get_element_api(self):
        self.assertIs(
            self.schema_proxy.get_element("{http://xpath.test/ns}test_element"),
            self.schema_proxy._schema.maps.elements["{http://xpath.test/ns}test_element"]
        )

    def test_get_substitution_group_api(self):
        self.assertIsNone(self.schema_proxy.get_substitution_group('x'))

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

        context = XPathContext(
            self.etree.XML('<range min="10" max="20" />'), schema=parser.schema
        )
        self.assertEqual(context.root.type_name, '{http://xpath.test/ns}intRange')
        self.assertEqual(context.root.attributes[0].type_name,
                         '{http://www.w3.org/2001/XMLSchema}int')
        self.assertEqual(context.root.attributes[1].type_name,
                         '{http://www.w3.org/2001/XMLSchema}int')
        self.assertTrue(token.evaluate(context))

        context = XPathContext(
            self.etree.XML('<range min="10" max="2" />'), schema=parser.schema
        )
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
        root = ElementTree.XML(
            '<tns:values xmlns:tns="http://xpath.test/ns">'
            '<a>foo</a><b>8</b><c>true</c><d>2.0</d></tns:values>'
        )
        root_node = get_node_tree(root, namespaces={'': "http://xpath.test/ns"})
        for node in root_node.iter():
            if isinstance(node, ElementNode):
                self.assertFalse(node.is_typed)

        root_node.apply_schema(parser.schema)
        for node in root_node.iter_lazy():
            if isinstance(node, ElementNode):
                self.assertTrue(node.is_typed)

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

        token = parser.parse("//b/@min lt //b/@max")
        root = self.etree.XML('<values xmlns="http://xpath.test/ns"><b min="19"/></values>')
        context = XPathContext(
            root, namespaces={'': "http://xpath.test/ns"}, schema=parser.schema
        )
        self.assertEqual(token.evaluate(context), [])

        root = self.etree.XML('<values xmlns="http://xpath.test/ns"><b min="19">30</b></values>')
        context = XPathContext(
            root, namespaces={'': "http://xpath.test/ns"}, schema=parser.schema
        )
        self.assertEqual(token.evaluate(context), [])

        root = self.etree.XML(
            '<values xmlns="http://xpath.test/ns"><b min="19" max="40">30</b></values>')
        context = XPathContext(
            root, namespaces={'': "http://xpath.test/ns"}, schema=parser.schema
        )
        self.assertTrue(token.evaluate(context))

        root = self.etree.XML(
            '<values xmlns="http://xpath.test/ns"><b min="19" max="10">30</b></values>')
        context = XPathContext(
            root, namespaces={'': "http://xpath.test/ns"}, schema=parser.schema
        )
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

    def test_element_substitution(self):
        schema = xmlschema.XMLSchema(dedent("""
            <xs:schema xmlns="http://xpath.test/ns"
                    xmlns:xs="http://www.w3.org/2001/XMLSchema"
                    targetNamespace="http://xpath.test/ns">
                <xs:element name="values">
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element ref="a" minOccurs="0"/>
                            <xs:element name="b" type="xs:string" minOccurs="0"/>
                            <xs:element ref="c" minOccurs="0"/>
                            <xs:element name="d" type="xs:float" minOccurs="0"/>
                        </xs:sequence>
                    </xs:complexType>
                </xs:element>

                <xs:element name="a" type="xs:integer"/>
                <xs:element name="ax" type="rangeType" substitutionGroup="a"/>
                <xs:element name="c" type="paramsType"/>
                <xs:element name="cx" type="extraParamsType" substitutionGroup="c"/>

                <xs:complexType name="rangeType">
                    <xs:simpleContent>
                        <xs:extension base="xs:integer">
                            <xs:attribute name="min" type="xs:integer"/>
                            <xs:attribute name="max" type="xs:integer"/>
                        </xs:extension>
                    </xs:simpleContent>
                </xs:complexType>

                <xs:complexType name="paramsType">
                    <xs:sequence>
                        <xs:element name="p0" type="xs:float" minOccurs="0"/>
                    </xs:sequence>
                </xs:complexType>

                <xs:complexType name="extraParamsType">
                    <xs:complexContent>
                        <xs:extension base="paramsType">
                            <xs:sequence>
                                <xs:element name="p1" type="xs:string" minOccurs="0"/>
                            </xs:sequence>
                        </xs:extension>
                    </xs:complexContent>
                </xs:complexType>

            </xs:schema>"""))

        schema_proxy = schema.xpath_proxy

        # Some tests to recall difference between local and ref elements
        xml_data = '<values xmlns="http://xpath.test/ns"><a>77</a></values>'
        self.assertTrue(schema.is_valid(xml_data))

        xml_data = '<values xmlns="http://xpath.test/ns"><d>1e10</d></values>'
        self.assertFalse(schema.is_valid(xml_data))

        xml_data = '<p:values xmlns:p="http://xpath.test/ns"><d>1e10</d></p:values>'
        self.assertTrue(schema.is_valid(xml_data))

        xml_data = '<p:values xmlns:p="http://xpath.test/ns"><a>77</a><d>1e10</d></p:values>'
        self.assertFalse(schema.is_valid(xml_data))

        xml_data = '<p:values xmlns:p="http://xpath.test/ns"><p:a>77</p:a><d>1e10</d></p:values>'
        self.assertTrue(schema.is_valid(xml_data))

        # Apply schema to invalid XML data
        xml_data = '<p:values xmlns:p="http://xpath.test/ns"><b min="19"/></p:values>'
        self.assertFalse(schema.is_valid(xml_data))
        root = self.etree.XML(xml_data)

        with self.assertRaises(TypeError):
            XPathContext(root, schema=schema)

        context = XPathContext(root, namespaces={'p': "http://xpath.test/ns"})
        context.root.apply_schema(schema_proxy)

        for node in context.root.iter_lazy():
            if isinstance(node, ElementNode):
                self.assertIsNotNone(node.xsd_type)

        self.assertEqual(context.root.children[0].type_name,
                         '{http://www.w3.org/2001/XMLSchema}string')
        self.assertIsNone(context.root.children[0].attributes[0].xsd_type)  # not found

        xml_data = '<values xmlns="http://xpath.test/ns"><b>foo</b></values>'
        self.assertFalse(schema.is_valid(xml_data))
        root = self.etree.XML(xml_data)

        context = XPathContext(root, namespaces={'': "http://xpath.test/ns"})
        context.root.apply_schema(schema_proxy)
        self.assertIsNone(context.root.children[0].xsd_type)

        # Substitution of simple content
        xml_data = '<values xmlns="http://xpath.test/ns"><a>80</a></values>'
        self.assertTrue(schema.is_valid(xml_data))

        xml_data = '<values xmlns="http://xpath.test/ns"><a min="19">80</a></values>'
        self.assertFalse(schema.is_valid(xml_data))
        root = self.etree.XML(xml_data)

        context = XPathContext(root, namespaces={'': "http://xpath.test/ns"})
        context.root.apply_schema(schema_proxy)
        self.assertEqual(context.root.children[0].type_name,
                         '{http://www.w3.org/2001/XMLSchema}integer')
        self.assertIsNone(context.root.children[0].attributes[0].xsd_type)  # not found

        xml_data = '<values xmlns="http://xpath.test/ns"><ax min="19">80</ax></values>'
        self.assertTrue(schema.is_valid(xml_data))
        root = self.etree.XML(xml_data)

        context = XPathContext(root)
        context.root.apply_schema(schema_proxy)
        self.assertEqual(context.root.children[0].type_name,
                         '{http://xpath.test/ns}rangeType')
        self.assertEqual(context.root.children[0].attributes[0].type_name,
                         '{http://www.w3.org/2001/XMLSchema}integer')

        # Substitution of complex content
        xml_data = ('<p:values xmlns:p="http://xpath.test/ns">'
                    '<p:c><p0>1.0</p0><p1>foo</p1></p:c></p:values>')
        self.assertFalse(schema.is_valid(xml_data))
        root = self.etree.XML(xml_data)

        context = XPathContext(root, namespaces={'p': "http://xpath.test/ns"})
        context.root.apply_schema(schema_proxy)
        self.assertEqual(context.root.children[0].type_name,
                         '{http://xpath.test/ns}paramsType')
        self.assertEqual(context.root.children[0].children[0].type_name,
                         '{http://www.w3.org/2001/XMLSchema}float')
        self.assertEqual(context.root.children[0].children[1].type_name,
                         '{http://www.w3.org/2001/XMLSchema}untyped')

        xml_data = ('<p:values xmlns:p="http://xpath.test/ns">'
                    '<p:cx><p0>1.0</p0><p1>foo</p1></p:cx></p:values>')
        self.assertTrue(schema.is_valid(xml_data))
        root = self.etree.XML(xml_data)

        context = XPathContext(root, namespaces={'p': "http://xpath.test/ns"})
        context.root.apply_schema(schema_proxy)
        self.assertEqual(context.root.children[0].type_name,
                         '{http://xpath.test/ns}extraParamsType')
        self.assertEqual(context.root.children[0].children[0].type_name,
                         '{http://www.w3.org/2001/XMLSchema}float')
        self.assertEqual(context.root.children[0].children[1].type_name,
                         '{http://www.w3.org/2001/XMLSchema}string')

    def test_type_substitution(self):
        schema = xmlschema.XMLSchema(dedent("""
            <xs:schema xmlns="http://xpath.test/ns"
                    xmlns:xs="http://www.w3.org/2001/XMLSchema"
                    targetNamespace="http://xpath.test/ns">
                <xs:element name="values">
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element ref="a" minOccurs="0"/>
                            <xs:element ref="b" minOccurs="0"/>
                        </xs:sequence>
                    </xs:complexType>
                </xs:element>

                <xs:element name="a" type="xs:integer"/>
                <xs:element name="b" type="paramsType"/>

                <xs:complexType name="rangeType">
                    <xs:simpleContent>
                        <xs:extension base="xs:integer">
                            <xs:attribute name="min" type="xs:integer"/>
                            <xs:attribute name="max" type="xs:integer"/>
                        </xs:extension>
                    </xs:simpleContent>
                </xs:complexType>

                <xs:complexType name="paramsType">
                    <xs:sequence>
                        <xs:element name="p0" type="xs:float" minOccurs="0"/>
                    </xs:sequence>
                </xs:complexType>

                <xs:complexType name="extraParamsType">
                    <xs:complexContent>
                        <xs:extension base="paramsType">
                            <xs:sequence>
                                <xs:element name="p1" type="xs:string" minOccurs="0"/>
                            </xs:sequence>
                        </xs:extension>
                    </xs:complexContent>
                </xs:complexType>

            </xs:schema>"""))

        schema_proxy = schema.xpath_proxy

        # Substitution of simple content
        xml_data = dedent("""\
            <values xmlns="http://xpath.test/ns"
                    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
                <a xsi:type="rangeType" min="19">80</a>
            </values>""")

        self.assertTrue(schema.is_valid(xml_data))
        root = self.etree.XML(xml_data)
        namespaces = {'': "http://xpath.test/ns",
                      'xsi': "http://www.w3.org/2001/XMLSchema-instance"}

        context = XPathContext(root, namespaces=namespaces)
        context.root.apply_schema(schema_proxy)

        self.assertEqual(context.root.children[1].type_name,
                         '{http://xpath.test/ns}rangeType')
        self.assertEqual(context.root.children[1].attributes[0].type_name,
                         '{http://www.w3.org/2001/XMLSchema}anyAtomicType')
        self.assertEqual(context.root.children[1].attributes[1].type_name,
                         '{http://www.w3.org/2001/XMLSchema}integer')

        # Substitution of complex content
        xml_data = dedent("""\
            <p:values xmlns:p="http://xpath.test/ns"
                    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
                <p:b xsi:type="p:extraParamsType">
                    <p0>1.0</p0>
                    <p1>foo</p1>
                </p:b>
            </p:values>""")

        self.assertTrue(schema.is_valid(xml_data))
        root = self.etree.XML(xml_data)
        namespaces = {'p': "http://xpath.test/ns",
                      'xsi': "http://www.w3.org/2001/XMLSchema-instance"}

        context = XPathContext(root, namespaces=namespaces)
        context.root.apply_schema(schema_proxy)

        self.assertEqual(context.root.children[1].type_name,
                         '{http://xpath.test/ns}extraParamsType')
        self.assertEqual(context.root.children[1].children[1].type_name,
                         '{http://www.w3.org/2001/XMLSchema}float')
        self.assertEqual(context.root.children[1].children[3].type_name,
                         '{http://www.w3.org/2001/XMLSchema}string')


@unittest.skipIf(xmlschema is None or lxml_etree is None, "both xmlschema and lxml required")
class LxmlXMLSchemaProxyTest(XMLSchemaProxyTest):
    etree = lxml_etree


if __name__ == '__main__':
    unittest.main()
