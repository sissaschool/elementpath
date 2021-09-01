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
import io
import locale
import math
import xml.etree.ElementTree as ElementTree
from collections import namedtuple
from decimal import Decimal

try:
    import xmlschema
except ImportError:
    xmlschema = None
else:
    xmlschema.XMLSchema.meta_schema.build()

from elementpath.exceptions import MissingContextError
from elementpath.datatypes import UntypedAtomic
from elementpath.namespaces import XSD_NAMESPACE, XPATH_FUNCTIONS_NAMESPACE
from elementpath.xpath_nodes import AttributeNode, TypedAttribute, \
    TypedElement, NamespaceNode, TextNode
from elementpath.xpath_token import UNICODE_CODEPOINT_COLLATION
from elementpath.helpers import ordinal
from elementpath.xpath_context import XPathContext, XPathSchemaContext
from elementpath.xpath1 import XPath1Parser
from elementpath.xpath2 import XPath2Parser


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
    def decode(self, obj, *args, **kwargs): pass
    def validate(self, obj, *args, **kwargs): pass


class Tagged(object):
    tag = 'root'

    def __repr__(self):
        return 'Tagged(tag=%r)' % self.tag


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

    def test_position(self):
        parser = XPath2Parser()

        token = parser.parse("(1, 2, 3, 4)")
        self.assertEqual(token.symbol, '(')
        self.assertEqual(token.position, (1, 1))

        token = parser.parse("(: Comment line :)\n\n (1, 2, 3, 4)")
        self.assertEqual(token.symbol, '(')
        self.assertEqual(token.position, (3, 2))

    def test_iter_method(self):
        token = self.parser.parse('2 + 5')
        items = [tk for tk in token.iter()]
        self.assertListEqual(items, [token[0], token, token[1]])

        token = self.parser.parse('/A/B[C]/D/@a')
        self.assertEqual(token.tree, '(/ (/ (/ (/ (A)) ([ (B) (C))) (D)) (@ (a)))')
        self.assertListEqual(list(tk.value for tk in token.iter()),
                             ['/', 'A', '/', 'B', '[', 'C', '/', 'D', '/', '@', 'a'])
        self.assertListEqual(list(tk.value for tk in token.iter('(name)')),
                             ['A', 'B', 'C', 'D', 'a'])

        self.assertListEqual(list(tk.source for tk in token.iter('/')),
                             ['/ A', '/ A / B[C]', '/ A / B[C] / D', '/ A / B[C] / D / @ a'])

    def test_iter_leaf_elements_method(self):
        token = self.parser.parse('2 + 5')
        self.assertListEqual(list(token.iter_leaf_elements()), [])

        token = self.parser.parse('/A/B[C]/D/@a')
        self.assertListEqual(list(token.iter_leaf_elements()), [])

        token = self.parser.parse('/A/B[C]/D')
        self.assertListEqual(list(token.iter_leaf_elements()), ['D'])

        token = self.parser.parse('/A/B[C]')
        self.assertEqual(token.tree, '(/ (/ (A)) ([ (B) (C)))')
        self.assertListEqual(list(token.iter_leaf_elements()), ['B'])

    def test_get_argument_method(self):
        token = self.parser.symbol_table['true'](self.parser)

        self.assertIsNone(token.get_argument(2))
        with self.assertRaises(TypeError):
            token.get_argument(1, required=True)

    @patch.multiple(DummyXsdType, is_simple=lambda x: False, has_simple_content=lambda x: True)
    def test_select_results(self):
        token = self.parser.parse('.')
        elem = ElementTree.Element('A', attrib={'max': '30'})
        elem.text = '10'
        xsd_type = DummyXsdType()

        context = XPathContext(elem)
        self.assertListEqual(list(token.select_results(context)), [elem])

        context = XPathContext(elem, item=TypedElement(elem, xsd_type, 10))
        self.assertListEqual(list(token.select_results(context)), [elem])

        context = XPathContext(elem, item=AttributeNode('max', '30'))
        self.assertListEqual(list(token.select_results(context)), ['30'])

        item = TypedAttribute(AttributeNode('max', '30'), xsd_type, 30)
        context = XPathContext(elem, item=item)
        self.assertListEqual(list(token.select_results(context)), [30])

        attribute = namedtuple('XsdAttribute', 'name local_name type')('max', 'max', xsd_type)
        item = TypedAttribute(AttributeNode('max', attribute), xsd_type, 30)
        context = XPathContext(elem, item=item)
        self.assertListEqual(list(token.select_results(context)), [attribute])

        context = XPathContext(elem, item=10)
        self.assertListEqual(list(token.select_results(context)), [10])

        context = XPathContext(elem, item='10')
        self.assertListEqual(list(token.select_results(context)), ['10'])

    def test_cast_to_double(self):
        token = self.parser.parse('.')
        self.assertEqual(token.cast_to_double(1), 1.0)

        with self.assertRaises(ValueError) as ctx:
            token.cast_to_double('nan')
        self.assertIn('FORG0001', str(ctx.exception))

        if self.parser.version != '1.0':
            self.parser._xsd_version = '1.1'
            self.assertEqual(token.cast_to_double('1'), 1.0)
            self.parser._xsd_version = '1.0'

    def test_atomization_function(self):
        root = ElementTree.Element('root')
        token = self.parser.parse('/unknown/.')
        context = XPathContext(root)
        self.assertListEqual(list(token.atomization(context)), [])

        if self.parser.version > '1.0':
            token = self.parser.parse('((), 1, 3, "a")')
            self.assertListEqual(list(token.atomization()), [1, 3, 'a'])

    def test_use_locale_context_manager(self):
        token = self.parser.parse('true()')
        with token.use_locale(UNICODE_CODEPOINT_COLLATION):
            self.assertEqual(locale.getlocale(locale.LC_COLLATE), ('en_US', 'UTF-8'))

        try:
            with token.use_locale('de_DE.UTF-8'):
                self.assertEqual(locale.getlocale(locale.LC_COLLATE), ('de_DE', 'UTF-8'))
        except locale.Error:
            pass  # Skip test if 'de_DE.UTF-8' is an unknown locale setting

        with self.assertRaises(TypeError) as cm:
            with token.use_locale(None):
                pass
        self.assertIn('XPTY0004', str(cm.exception))
        self.assertIn('collation cannot be an empty sequence', str(cm.exception))

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
        self.assertTrue(token.boolean_value(1.0))
        self.assertFalse(token.boolean_value(None))

    def test_data_value_function(self):
        token = self.parser.parse('true()')

        if self.parser.version != '1.0':
            with patch.multiple(DummyXsdType(), is_simple=lambda x: False,
                                has_simple_content=lambda x: True) as xsd_type:
                obj = TypedElement(ElementTree.XML('<age>19</age>'), xsd_type, 19)
                self.assertEqual(token.data_value(obj), 19)

        obj = AttributeNode('age', '19')
        self.assertEqual(token.data_value(obj), UntypedAtomic('19'))

        obj = NamespaceNode('tns', 'http://xpath.test/ns')
        self.assertEqual(token.data_value(obj), 'http://xpath.test/ns')

        obj = TextNode('19')
        self.assertEqual(token.data_value(obj), UntypedAtomic('19'))

        obj = ElementTree.XML('<root>a<e1>b</e1>c<e2>d</e2>e</root>')
        self.assertEqual(token.data_value(obj), UntypedAtomic('abcde'))

        obj = ElementTree.parse(io.StringIO('<root>a<e1>b</e1>c<e2>d</e2>e</root>'))
        self.assertEqual(token.data_value(obj), UntypedAtomic('abcde'))

        obj = ElementTree.Comment("foo bar")
        self.assertEqual(token.data_value(obj), 'foo bar')

        obj = ElementTree.ProcessingInstruction('action', 'nothing to do')
        self.assertEqual(token.data_value(obj), 'action nothing to do')

        self.assertIsNone(token.data_value(None))
        self.assertEqual(token.data_value(19), 19)
        self.assertEqual(token.data_value('19'), '19')
        self.assertFalse(token.data_value(False))

        tagged_object = Tagged()
        self.assertIsNone(token.data_value(tagged_object))

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

        self.assertEqual(token.string_value(Decimal(+1999)), '1999')
        self.assertEqual(token.string_value(Decimal('+1999')), '1999')
        self.assertEqual(token.string_value(Decimal('+19.0010')), '19.001')

        self.assertEqual(token.string_value(10), '10')
        self.assertEqual(token.string_value(1e99), '1E99')
        self.assertEqual(token.string_value(1e-05), '1E-05')
        self.assertEqual(token.string_value(1.00), '1')
        self.assertEqual(token.string_value(+19.0010), '19.001')

        self.assertEqual(token.string_value(float('nan')), 'NaN')
        self.assertEqual(token.string_value(float('inf')), 'INF')
        self.assertEqual(token.string_value(float('-inf')), '-INF')

        self.assertEqual(token.string_value(()), '()')

        tagged_object = Tagged()
        self.assertEqual(token.string_value(tagged_object), "Tagged(tag='root')")

        with patch.multiple(DummyXsdType, is_simple=lambda x: True):
            xsd_type = DummyXsdType()
            typed_elem = TypedElement(elem=element, xsd_type=xsd_type, value=10)
            self.assertEqual(token.string_value(typed_elem), '10')
            typed_elem = TypedElement(elem=element, xsd_type=xsd_type, value=None)
            self.assertEqual(token.string_value(typed_elem), '')

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

    def test_expected_method(self):
        token = self.parser.parse('.')
        self.assertIsNone(token.expected('.'))

        with self.assertRaises(SyntaxError) as ctx:
            raise token.expected('*')
        self.assertIn('XPST0003', str(ctx.exception))

    def test_unexpected_method(self):
        token = self.parser.parse('.')
        self.assertIsNone(token.unexpected('*'))

        with self.assertRaises(SyntaxError) as ctx:
            raise token.unexpected('.')
        self.assertIn('XPST0003', str(ctx.exception))

        with self.assertRaises(SyntaxError) as ctx:
            raise token.unexpected('.', message="unknown error")
        self.assertIn('XPST0003', str(ctx.exception))
        self.assertIn('unknown error', str(ctx.exception))

        with self.assertRaises(TypeError) as ctx:
            raise token.unexpected('.', code='XPST0017')
        self.assertIn('XPST0017', str(ctx.exception))

    def test_xpath_error_code(self):
        parser = XPath2Parser()
        token = parser.parse('.')

        self.assertEqual(token.error_code('XPST0003'), 'err:XPST0003')
        parser.namespaces['error'] = parser.namespaces.pop('err')
        self.assertEqual(token.error_code('XPST0003'), 'error:XPST0003')
        parser.namespaces.pop('error')
        self.assertEqual(token.error_code('XPST0003'), 'XPST0003')

    def test_xpath_error(self):
        token = self.parser.parse('.')

        with self.assertRaises(ValueError) as ctx:
            raise token.error('xml:XPST0003')
        self.assertIn('XPTY0004', str(ctx.exception))
        self.assertIn("'http://www.w3.org/2005/xqt-errors' namespace is required",
                      str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            raise token.error('err:err:XPST0003')
        self.assertIn('XPTY0004', str(ctx.exception))
        self.assertIn("is not a prefixed name", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            raise token.error('XPST9999')
        self.assertIn('XPTY0004', str(ctx.exception))
        self.assertIn("unknown XPath error code", str(ctx.exception))

    def test_xpath_error_shortcuts(self):
        token = self.parser.parse('.')

        with self.assertRaises(ValueError) as ctx:
            raise token.wrong_value()
        self.assertIn('FOCA0002', str(ctx.exception))

        with self.assertRaises(TypeError) as ctx:
            raise token.wrong_type()
        self.assertIn('FORG0006', str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            raise token.missing_schema()
        self.assertIn('XPST0001', str(ctx.exception))

        with self.assertRaises(MissingContextError) as ctx:
            raise token.missing_context()
        self.assertIn('XPDY0002', str(ctx.exception))

        with self.assertRaises(TypeError) as ctx:
            raise token.wrong_context_type()
        self.assertIn('XPTY0004', str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            raise token.missing_sequence()
        self.assertIn('XPST0005', str(ctx.exception))

        with self.assertRaises(NameError) as ctx:
            raise token.missing_name()
        self.assertIn('XPST0008', str(ctx.exception))

        if self.parser.compatibility_mode:
            with self.assertRaises(NameError) as ctx:
                raise token.missing_axis()
            self.assertIn('XPST0010', str(ctx.exception))
        else:
            with self.assertRaises(SyntaxError) as ctx:
                raise token.missing_axis()
            self.assertIn('XPST0003', str(ctx.exception))

        with self.assertRaises(TypeError) as ctx:
            raise token.wrong_nargs()
        self.assertIn('XPST0017', str(ctx.exception))

        with self.assertRaises(TypeError) as ctx:
            raise token.wrong_step_result()
        self.assertIn('XPTY0018', str(ctx.exception))

        with self.assertRaises(TypeError) as ctx:
            raise token.wrong_intermediate_step_result()
        self.assertIn('XPTY0019', str(ctx.exception))

        with self.assertRaises(TypeError) as ctx:
            raise token.wrong_axis_argument()
        self.assertIn('XPTY0020', str(ctx.exception))

        with self.assertRaises(TypeError) as ctx:
            raise token.wrong_sequence_type()
        self.assertIn('XPDY0050', str(ctx.exception))

        with self.assertRaises(NameError) as ctx:
            raise token.unknown_atomic_type()
        self.assertIn('XPST0051', str(ctx.exception))

        with self.assertRaises(NameError) as ctx:
            raise token.wrong_target_type()
        self.assertIn('XPST0080', str(ctx.exception))

        with self.assertRaises(NameError) as ctx:
            raise token.unknown_namespace()
        self.assertIn('XPST0081', str(ctx.exception))


class XPath2TokenTest(XPath1TokenTest):

    @classmethod
    def setUpClass(cls):
        cls.parser = XPath2Parser(namespaces={'xs': XSD_NAMESPACE, 'tst': "http://xpath.test/ns"})

    def test_bind_namespace_method(self):
        token = self.parser.parse('true()')
        self.assertIsNone(token.bind_namespace(XPATH_FUNCTIONS_NAMESPACE))
        with self.assertRaises(TypeError) as ctx:
            token.bind_namespace(XSD_NAMESPACE)
        self.assertIn('XPST0017', str(ctx.exception))
        self.assertIn("a name, a wildcard or a constructor function", str(ctx.exception))

        token = self.parser.parse("xs:string(10.1)")
        with self.assertRaises(TypeError) as ctx:
            token.bind_namespace(XSD_NAMESPACE)
        self.assertIn('XPST0017', str(ctx.exception))
        self.assertIn("a name, a wildcard or a constructor function", str(ctx.exception))

        self.assertIsNone(token[1].bind_namespace(XSD_NAMESPACE))
        with self.assertRaises(TypeError) as ctx:
            token[1].bind_namespace(XPATH_FUNCTIONS_NAMESPACE)
        self.assertIn("a function expected", str(ctx.exception))

        token = self.parser.parse("tst:foo")
        with self.assertRaises(SyntaxError) as ctx:
            token.bind_namespace('http://xpath.test/ns')
        self.assertIn('XPST0003', str(ctx.exception))
        self.assertIn("a name, a wildcard or a function", str(ctx.exception))

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
        root_token.add_xsd_type(schema.elements['a1'])
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

            # With the schema as base element all the global elements are added.
            root_token = self.parser.parse('.')
            self.assertEqual(root_token.xsd_types, {
                'a1': schema.meta_schema.types['int'],
                'a2': schema.meta_schema.types['string'],
                'a3': schema.meta_schema.types['boolean'],
            })

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
    def test_add_xsd_type_alternatives(self):
        schema = xmlschema.XMLSchema("""
            <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
              <xs:element name="root" type="xs:int"/>
              <xs:attribute name="a" type="xs:string"/>
            </xs:schema>""")

        root_token = self.parser.parse('root')
        self.assertIsNone(root_token.add_xsd_type('xs:string'))  # ignore non-schema items
        self.assertIsNone(root_token.xsd_types)

        xsd_type = root_token.add_xsd_type(schema.elements['root'])
        self.assertEqual(root_token.xsd_types, {'root': schema.meta_schema.types['int']})
        self.assertIs(xsd_type, schema.meta_schema.types['int'])

        root_token.xsd_types = None
        typed_element = TypedElement(schema.elements['root'], xsd_type, 1)
        xsd_type = root_token.add_xsd_type(typed_element)
        self.assertEqual(root_token.xsd_types, {'root': schema.meta_schema.types['int']})
        self.assertIs(xsd_type, schema.meta_schema.types['int'])

        attribute = AttributeNode('a', schema.attributes['a'])
        typed_attribute = TypedAttribute(attribute, schema.meta_schema.types['string'], 'alpha')
        xsd_type = root_token.add_xsd_type(typed_attribute)
        self.assertEqual(root_token.xsd_types, {'a': schema.meta_schema.types['string'],
                                                'root': schema.meta_schema.types['int']})
        self.assertIs(xsd_type, schema.meta_schema.types['string'])

    @unittest.skipIf(xmlschema is None, "xmlschema library required.")
    def test_select_xsd_nodes(self):
        schema = xmlschema.XMLSchema("""
            <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
              <xs:element name="root" type="xs:int"/>
              <xs:attribute name="a" type="xs:string"/>
            </xs:schema>""")
        self.parser.schema = xmlschema.xpath.XMLSchemaProxy(schema)

        try:
            root_token = self.parser.parse('.')
            self.assertEqual(root_token.xsd_types, {
                'root': schema.elements['root'].type,
            })

            context = XPathSchemaContext(root=schema, axis='self')
            self.assertListEqual(list(root_token.select_xsd_nodes(context, 'root')), [])

            tag = '{%s}schema' % XSD_NAMESPACE
            self.assertListEqual(list(root_token.select_xsd_nodes(context, tag)), [schema])

            context.item = None
            self.assertListEqual(list(root_token.select_xsd_nodes(context, 'root')), [])

            context.item = None
            result = list(root_token.select_xsd_nodes(context, tag))
            self.assertListEqual(result, [None])  # Schema as document node
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

            context = XPathSchemaContext(root=schema)
            obj = list(root_token.select_xsd_nodes(context, 'root'))
            self.assertIsInstance(obj[0], TypedElement)
            self.assertEqual(root_token.xsd_types, {'root': schema.meta_schema.types['int']})

            context.axis = 'self'
            root_token.xsd_types = None
            list(root_token.select_xsd_nodes(context, 'root'))
            self.assertIsNone(root_token.xsd_types)

            context.axis = None
            obj = list(root_token.select_xsd_nodes(context, 'root'))
            self.assertIsInstance(obj[0], TypedElement)

            context = XPathSchemaContext(root=schema.meta_schema)
            obj = list(root_token.select_xsd_nodes(context, 'root'))
            self.assertListEqual(obj, [])

            root_token = self.parser.parse('@a')
            self.assertEqual(root_token[0].xsd_types, {'a': schema.meta_schema.types['string']})

            attribute = AttributeNode('a', schema.attributes['a'])
            context = XPathSchemaContext(root=schema.meta_schema, item=attribute, axis='self')

            obj = list(root_token.select_xsd_nodes(context, 'a'))
            self.assertIsInstance(obj[0], TypedAttribute)
            self.assertEqual(root_token[0].xsd_types, {'a': schema.meta_schema.types['string']})

            root_token.xsd_types = None
            context = XPathSchemaContext(root=schema)
            list(root_token.select_xsd_nodes(context, 'a'))
            self.assertIsNone(root_token.xsd_types)

            context = XPathSchemaContext(root=schema.meta_schema, item=attribute, axis='self')
            obj = list(root_token.select_xsd_nodes(context, 'a'))
            self.assertIsInstance(obj[0], TypedAttribute)
            self.assertEqual(obj[0].attribute, attribute)
            self.assertIsInstance(obj[0].value, str)
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

            TestElement = namedtuple('XsdElement', 'name local_name type')
            root_token.add_xsd_type(
                TestElement('node', 'node', schema.meta_schema.types['float'])
            )
            root_token.add_xsd_type(
                TestElement('node', 'node', schema.meta_schema.types['boolean'])
            )
            root_token.add_xsd_type(
                TestElement('node', 'node', schema.meta_schema.types['decimal'])
            )

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

            typed_element = TypedElement(elem, xsd_type, False)
            self.assertIs(xsd_type, root_token.get_xsd_type(typed_element))

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

            TestElement = namedtuple('XsdElement', 'name local_name type')
            root_token.add_xsd_type(TestElement('a', 'a', schema.meta_schema.types['float']))
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
            self.assertIsInstance(node.xsd_type, xmlschema.XsdType)
            self.assertEqual(node.value, 49)
            self.assertIs(root_token.get_typed_node(node), node)

            elem.text = 'beta'
            with self.assertRaises(TypeError) as err:
                root_token.get_typed_node(elem)
            self.assertIn('XPDY0050', str(err.exception))
            self.assertIn('does not match sequence type', str(err.exception))

            root_token.xsd_types['root'] = schema.meta_schema.types['anySimpleType']
            elem.text = '36'
            node = root_token.get_typed_node(elem)
            self.assertIsInstance(node, TypedElement)
            self.assertIsInstance(node.xsd_type, xmlschema.XsdType)
            self.assertIsInstance(node.value, UntypedAtomic)
            self.assertEqual(node.value, 36)

            root_token.xsd_types['root'] = schema.meta_schema.types['anyType']
            node = root_token.get_typed_node(elem)
            self.assertIs(node.elem, elem)

            root_token = self.parser.parse('@a')
            self.assertEqual(root_token[0].xsd_types, {'a': schema.meta_schema.types['int']})

            attribute = AttributeNode('a', '10')
            node = root_token[0].get_typed_node(attribute)
            self.assertIsInstance(node, TypedAttribute)
            self.assertIsInstance(node.xsd_type, xmlschema.XsdType)
            self.assertEqual(node.value, 10)

            root_token[0].xsd_types['a'] = schema.meta_schema.types['anyType']
            node = root_token[0].get_typed_node(attribute)
            self.assertIsInstance(node, TypedAttribute)
            self.assertIsInstance(node.xsd_type, xmlschema.XsdType)
            self.assertIsInstance(node.value, UntypedAtomic)
            self.assertEqual(node.value, 10)

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


if __name__ == '__main__':
    unittest.main()
