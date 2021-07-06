#!/usr/bin/env python
#
# Copyright (c), 2021, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import unittest
from copy import copy
from textwrap import dedent

from elementpath import TypedElement, XPath2Parser
from elementpath.datatypes import UntypedAtomic

try:
    # noinspection PyPackageRequirements
    import xmlschema
    from xmlschema.xpath import XMLSchemaContext
except (ImportError, AttributeError):
    xmlschema = None


@unittest.skipIf(xmlschema is None, "xmlschema library required.")
class XMLSchemaProxyTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.schema1 = xmlschema.XMLSchema(dedent('''\
        <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
              xmlns="http://xpath.test/ns" targetNamespace="http://xpath.test/ns">
          <xs:element name="a">
            <xs:complexType>
              <xs:sequence>
                <xs:element name="b1" type="xs:string" />
                <xs:element name="b2" type="xs:int" />
                <xs:element ref="b3"/>
              </xs:sequence>
            </xs:complexType>
          </xs:element>
          <xs:element name="b3" type="xs:float"/>
        </xs:schema>'''))

        cls.schema2 = xmlschema.XMLSchema(dedent('''\
        <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
          <xs:element name="root" type="xs:string"/>
        </xs:schema>'''))

    def test_name_token(self):
        parser = XPath2Parser(default_namespace="http://xpath.test/ns")
        context = XMLSchemaContext(self.schema1)

        elem_a = self.schema1.elements['a']
        token = parser.parse('a')
        self.assertIsNone(token.xsd_types)

        result = token.evaluate(copy(context))
        self.assertEqual(token.xsd_types, {"{http://xpath.test/ns}a": elem_a.type})
        self.assertListEqual(result, [TypedElement(elem_a, elem_a.type, UntypedAtomic('1'))])

        elem_b1 = elem_a.type.content[0]
        token = parser.parse('a/b1')
        self.assertIsNone(token[0].xsd_types)
        self.assertIsNone(token[1].xsd_types)

        result = token.evaluate(copy(context))
        self.assertEqual(token[0].xsd_types, {"{http://xpath.test/ns}a": elem_a.type})
        self.assertEqual(token[1].xsd_types, {"b1": elem_b1.type})
        self.assertListEqual(result, [TypedElement(elem_b1, elem_b1.type, '  alpha\t')])

    def test_colon_token(self):
        parser = XPath2Parser(namespaces={'tst': "http://xpath.test/ns"})
        context = XMLSchemaContext(self.schema1)

        elem_a = self.schema1.elements['a']
        token = parser.parse('tst:a')
        self.assertEqual(token.symbol, ':')
        self.assertIsNone(token.xsd_types)

        result = token.evaluate(copy(context))
        self.assertEqual(token.xsd_types, {"{http://xpath.test/ns}a": elem_a.type})
        self.assertListEqual(result, [TypedElement(elem_a, elem_a.type, UntypedAtomic('1'))])

        elem_b1 = elem_a.type.content[0]
        token = parser.parse('tst:a/b1')
        self.assertEqual(token.symbol, '/')
        self.assertEqual(token[0].symbol, ':')
        self.assertIsNone(token[0].xsd_types)
        self.assertIsNone(token[1].xsd_types)

        result = token.evaluate(copy(context))
        self.assertListEqual(result, [TypedElement(elem_b1, elem_b1.type, '  alpha\t')])
        self.assertEqual(token[0].xsd_types, {"{http://xpath.test/ns}a": elem_a.type})
        self.assertEqual(token[1].xsd_types, {"b1": elem_b1.type})

        token = parser.parse('tst:a/tst:b1')
        result = token.evaluate(copy(context))
        self.assertListEqual(result, [])
        self.assertEqual(token[0].xsd_types, {"{http://xpath.test/ns}a": elem_a.type})
        self.assertIsNone(token[1].xsd_types)

        elem_b3 = elem_a.type.content[2]
        token = parser.parse('tst:a/tst:b3')
        self.assertEqual(token.symbol, '/')
        self.assertEqual(token[0].symbol, ':')
        self.assertIsNone(token[0].xsd_types)
        self.assertIsNone(token[1].xsd_types)

        result = token.evaluate(copy(context))
        self.assertListEqual(result, [TypedElement(elem_b3, elem_b3.type, 1.0)])
        self.assertEqual(token[0].xsd_types, {"{http://xpath.test/ns}a": elem_a.type})
        self.assertEqual(token[1].xsd_types, {"{http://xpath.test/ns}b3": elem_b3.type})

    def test_extended_name_token(self):
        parser = XPath2Parser(strict=False)
        context = XMLSchemaContext(self.schema1)

        elem_a = self.schema1.elements['a']
        token = parser.parse('{http://xpath.test/ns}a')
        self.assertEqual(token.symbol, '{')
        self.assertIsNone(token.xsd_types)
        self.assertEqual(token[0].symbol, '(string)')
        self.assertEqual(token[1].symbol, '(name)')
        self.assertEqual(token[1].value, 'a')

        result = token.evaluate(context)
        self.assertListEqual(result, [TypedElement(elem_a, elem_a.type, UntypedAtomic('1'))])
        self.assertEqual(token.xsd_types, {"{http://xpath.test/ns}a": elem_a.type})
        self.assertIsNone(token[0].xsd_types)
        self.assertIsNone(token[1].xsd_types)

    def test_wildcard_token(self):
        parser = XPath2Parser(default_namespace="http://xpath.test/ns")
        context = XMLSchemaContext(self.schema1)

        elem_a = self.schema1.elements['a']
        elem_b3 = self.schema1.elements['b3']
        token = parser.parse('*')
        self.assertEqual(token.symbol, '*')
        self.assertIsNone(token.xsd_types)

        result = token.evaluate(context)
        self.assertListEqual(result, [elem_a, elem_b3])
        self.assertEqual(token.xsd_types, {"{http://xpath.test/ns}a": elem_a.type,
                                           "{http://xpath.test/ns}b3": elem_b3.type})

        token = parser.parse('a/*')
        self.assertEqual(token.symbol, '/')
        self.assertEqual(token[0].symbol, '(name)')
        self.assertEqual(token[1].symbol, '*')

        result = token.evaluate(context)
        self.assertListEqual(result, elem_a.type.content[:])
        self.assertIsNone(token.xsd_types)
        self.assertEqual(token[0].xsd_types, {"{http://xpath.test/ns}a": elem_a.type})
        self.assertEqual(token[1].xsd_types, {'b1': elem_a.type.content[0].type,
                                              'b2': elem_a.type.content[1].type,
                                              '{http://xpath.test/ns}b3': elem_b3.type})

    def test_dot_shortcut_token(self):
        parser = XPath2Parser(default_namespace="http://xpath.test/ns")
        context = XMLSchemaContext(self.schema1)

        elem_a = self.schema1.elements['a']
        elem_b3 = self.schema1.elements['b3']

        token = parser.parse('.')
        self.assertIsNone(token.xsd_types)
        result = token.evaluate(context)
        self.assertListEqual(result, [self.schema1])
        self.assertEqual(token.xsd_types, {"{http://xpath.test/ns}a": elem_a.type,
                                           "{http://xpath.test/ns}b3": elem_b3.type})

        context = XMLSchemaContext(self.schema1, item=self.schema1)
        token = parser.parse('.')
        self.assertIsNone(token.xsd_types)
        result = token.evaluate(context)
        self.assertListEqual(result, [self.schema1])
        self.assertEqual(token.xsd_types, {"{http://xpath.test/ns}a": elem_a.type,
                                           "{http://xpath.test/ns}b3": elem_b3.type})

        context = XMLSchemaContext(self.schema1, item=self.schema2)
        token = parser.parse('.')
        self.assertIsNone(token.xsd_types)
        result = token.evaluate(context)
        self.assertListEqual(result, [self.schema2])
        self.assertIsNone(token.xsd_types)

    def test_schema_variables(self):
        variable_types = {'a': 'item()', 'b': 'xs:integer?', 'c': 'xs:string'}
        parser = XPath2Parser(default_namespace="http://xpath.test/ns",
                              variable_types=variable_types)
        context = XMLSchemaContext(self.schema1)

        token = parser.parse('$a')
        result = token.evaluate(context)
        self.assertIsInstance(result, UntypedAtomic)
        self.assertEqual(result.value, '')

        token = parser.parse('$b')
        result = token.evaluate(context)
        self.assertIsInstance(result, int)
        self.assertEqual(result, 1)

        token = parser.parse('$c')
        result = token.evaluate(context)
        self.assertIsInstance(result, str)
        self.assertEqual(result, '  alpha\t')

        token = parser.parse('$z')
        with self.assertRaises(NameError):
            token.evaluate(context)

    def test_not_applicable_functions(self):
        parser = XPath2Parser(default_namespace="http://xpath.test/ns")
        context = XMLSchemaContext(self.schema1)

        token = parser.parse("fn:collection('filepath')")
        self.assertIsNone(token.evaluate(context))

        token = parser.parse("fn:doc-available('tns1')")
        self.assertIsNone(token.evaluate(context))

        token = parser.parse("fn:root(.)")
        self.assertIsNone(token.evaluate(context))

        token = parser.parse("fn:id('ID21256')")
        self.assertListEqual(token.evaluate(context), [])

        token = parser.parse("fn:idref('ID21256')")
        self.assertListEqual(token.evaluate(context), [])


if __name__ == '__main__':
    unittest.main()
