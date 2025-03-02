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

from elementpath import XPath2Parser, XPathSchemaContext
from elementpath.datatypes import UntypedAtomic

try:
    # noinspection PyPackageRequirements
    import xmlschema
except (ImportError, AttributeError):
    xmlschema = None


@unittest.skipIf(xmlschema is None, "xmlschema library required")
class XMLSchemaContextTest(unittest.TestCase):

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
        schema_context = XPathSchemaContext(self.schema1)

        elem_a = self.schema1.elements['a']
        token = parser.parse('a')

        context = copy(schema_context)
        element_node = context.root[0]
        self.assertIs(element_node.elem, elem_a)
        self.assertIs(element_node.xsd_type, elem_a.type)

        result = token.evaluate(context)
        self.assertListEqual(result, [element_node])

        elem_b1 = elem_a.type.content[0]
        token = parser.parse('a/b1')

        context = copy(schema_context)
        element_node = context.root[0][0]
        self.assertIs(element_node.elem, elem_b1)
        self.assertIs(element_node.xsd_type, elem_b1.type)

        result = token.evaluate(context)
        self.assertListEqual(result, [element_node])

    def test_colon_token(self):
        parser = XPath2Parser(namespaces={'tst': "http://xpath.test/ns"})
        context = XPathSchemaContext(self.schema1)

        token = parser.parse('tst:a')
        self.assertEqual(token.symbol, ':')

        result = token.evaluate(copy(context))
        self.assertListEqual(result, [context.root[0]])

        token = parser.parse('tst:a/b1')
        self.assertEqual(token.symbol, '/')
        self.assertEqual(token[0].symbol, ':')

        result = token.evaluate(copy(context))
        self.assertListEqual(result, [context.root[0][0]])

        token = parser.parse('tst:a/tst:b1')
        result = token.evaluate(copy(context))
        self.assertListEqual(result, [])

        token = parser.parse('tst:a/tst:b3')
        self.assertEqual(token.symbol, '/')
        self.assertEqual(token[0].symbol, ':')

        result = token.evaluate(copy(context))
        self.assertListEqual(result, [context.root[0][2]])

    def test_extended_name_token(self):
        parser = XPath2Parser(strict=False)
        context = XPathSchemaContext(self.schema1)

        token = parser.parse('{http://xpath.test/ns}a')
        self.assertEqual(token.symbol, '{')
        self.assertEqual(token[0].symbol, '(string)')
        self.assertEqual(token[1].symbol, '(name)')
        self.assertEqual(token[1].value, 'a')

        result = token.evaluate(context)
        self.assertListEqual(result, [context.root[0]])

    def test_wildcard_token(self):
        parser = XPath2Parser(default_namespace="http://xpath.test/ns")
        context = XPathSchemaContext(self.schema1)

        elem_a = self.schema1.elements['a']
        elem_b3 = self.schema1.elements['b3']
        token = parser.parse('*')
        self.assertEqual(token.symbol, '*')

        result = token.evaluate(context)
        self.assertListEqual([e.value for e in result], [elem_a, elem_b3])

        token = parser.parse('a/*')
        self.assertEqual(token.symbol, '/')
        self.assertEqual(token[0].symbol, '(name)')
        self.assertEqual(token[1].symbol, '*')

        result = token.evaluate(context)
        self.assertListEqual([e.value for e in result], elem_a.type.content[:])

    def test_dot_shortcut_token(self):
        parser = XPath2Parser(default_namespace="http://xpath.test/ns")
        context = XPathSchemaContext(self.schema1)

        token = parser.parse('.')
        result = token.evaluate(context)
        self.assertListEqual(result, [context.root])

        context = XPathSchemaContext(self.schema1, item=self.schema1)
        token = parser.parse('.')
        result = token.evaluate(context)
        self.assertListEqual(result, [context.root])

        context = XPathSchemaContext(self.schema1, item=self.schema2)
        schema2_node = context.item
        token = parser.parse('.')
        result = token.evaluate(context)
        self.assertListEqual(result, [schema2_node])

    def test_schema_variables(self):
        variable_types = {'a': 'item()', 'b': 'xs:integer?', 'c': 'xs:string'}
        parser = XPath2Parser(
            default_namespace="http://xpath.test/ns",
            variable_types=variable_types,
            schema=self.schema1.xpath_proxy,
        )
        context = XPathSchemaContext(self.schema1)

        token = parser.parse('$a')
        result = token.evaluate(context)
        self.assertIsInstance(result, UntypedAtomic)
        self.assertEqual(result.value, '1')

        token = parser.parse('$b')
        result = token.evaluate(context)
        self.assertIsInstance(result, int)
        self.assertEqual(result, 1)

        token = parser.parse('$c')
        result = token.evaluate(context)
        self.assertIsInstance(result, str)
        self.assertEqual(result, '  alpha\t')

        token = parser.parse('$z')
        self.assertListEqual(token.evaluate(context), [])

    def test_not_applicable_functions(self):
        parser = XPath2Parser(default_namespace="http://xpath.test/ns")
        context = XPathSchemaContext(self.schema1)

        token = parser.parse("fn:collection('filepath')")
        self.assertListEqual(token.evaluate(context), [])

        token = parser.parse("fn:doc-available('tns1')")
        self.assertFalse(token.evaluate(context))

        token = parser.parse("fn:root(.)")
        self.assertListEqual(token.evaluate(context), [])

        token = parser.parse("fn:id('ID21256')")
        self.assertListEqual(token.evaluate(context), [])

        token = parser.parse("fn:idref('ID21256')")
        self.assertListEqual(token.evaluate(context), [])

    def test_if_statement(self):
        parser = XPath2Parser(default_namespace="http://xpath.test/ns")
        context = XPathSchemaContext(self.schema1)

        token = parser.parse('if ($x > 1) then a/b1 else a/b2')
        result = token.evaluate(context)
        self.assertListEqual(result, [context.root[0][1]])

        token = parser.parse('if ($x > xs:date("2010-01-01")) then a/b1 else a/b2')
        result = token.evaluate(context)
        self.assertListEqual(result, [context.root[0][1]])


if __name__ == '__main__':
    unittest.main()
