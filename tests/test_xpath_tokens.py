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
import math
import xml.etree.ElementTree as ElementTree
from decimal import Decimal

try:
    import xmlschema
except ImportError:
    xmlschema = None
else:
    xmlschema.XMLSchema.meta_schema.build()

from elementpath.exceptions import MissingContextError
from elementpath.datatypes import UntypedAtomic, Int
from elementpath.namespaces import XSD_NAMESPACE, XPATH_FUNCTIONS_NAMESPACE
from elementpath.xpath_nodes import ElementNode, AttributeNode, NamespaceNode, \
    CommentNode, ProcessingInstructionNode, TextNode, DocumentNode, \
    SchemaAttributeNode, TextAttributeNode, EtreeElementNode
from elementpath.helpers import ordinal
from elementpath.xpath_context import XPathContext, XPathSchemaContext
from elementpath.xpath1 import XPath1Parser
from elementpath.xpath2 import XPath2Parser
from elementpath.xpath3 import XPath30Parser, XPath31Parser


class DummyXsdType:
    name = local_name = None
    xsd_version = '1.0'

    @property
    def root_type(self): return self
    @property
    def simple_type(self): return self
    def is_matching(self, name, default_namespace): pass
    def is_empty(self): pass
    def is_simple(self): pass
    def has_simple_content(self): pass
    def has_mixed_content(self): pass
    def is_element_only(self): pass
    def is_list(self): pass
    def is_union(self): pass
    def is_key(self): pass
    def is_qname(self): pass
    def is_notation(self): pass

    @staticmethod
    def validate(obj, *args, **kwargs):
        Int.validate(obj)

    @staticmethod
    def decode(obj, *args, **kwargs):
        return int(obj)


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
                             ['/A', '/A/B[C]', '/A/B[C]/D', '/A/B[C]/D/@a'])

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

    @patch.multiple(DummyXsdType,
                    is_simple=lambda x: False,
                    has_simple_content=lambda x: True)
    def test_select_results(self):
        token = self.parser.parse('.')
        elem = ElementTree.Element('A', attrib={'max': '30'})
        elem.text = '10'
        xsd_type = DummyXsdType()

        context = XPathContext(elem)
        self.assertListEqual(list(token.select_results(context)), [elem])

        context = XPathContext(elem, item=elem)
        setattr(context.root, 'xsd_type', xsd_type)
        self.assertListEqual(list(token.select_results(context)), [elem])

        context = XPathContext(elem)
        context.item = context.root.attributes[0]
        self.assertListEqual(list(token.select_results(context)), ['30'])

        context = XPathContext(elem)
        context.item = context.root.attributes[0]
        setattr(context.item, 'xsd_type', xsd_type)
        self.assertListEqual(list(token.select_results(context)), ['30'])

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

    def test_boolean_value_function(self):
        token = self.parser.parse('true()')
        elem = ElementTree.Element('A')
        context = XPathContext(elem)

        self.assertTrue(token.boolean_value(context.root))
        self.assertFalse(token.boolean_value([]))
        self.assertTrue(token.boolean_value([context.root]))
        self.assertFalse(token.boolean_value([0]))
        self.assertTrue(token.boolean_value([1]))

        with self.assertRaises(TypeError):
            token.boolean_value([1, 1])

        self.assertFalse(token.boolean_value(0))
        self.assertTrue(token.boolean_value(1))
        self.assertTrue(token.boolean_value(1.0))
        self.assertFalse(token.boolean_value(None))

    @patch.multiple(DummyXsdType(),
                    is_simple=lambda x: False,
                    has_simple_content=lambda x: True)
    def test_data_value_function(self):
        token = self.parser.parse('true()')

        if self.parser.version != '1.0':
            xsd_type = DummyXsdType()
            context = XPathContext(ElementTree.XML('<age>19</age>'))
            setattr(context.root, 'xsd_type', xsd_type)
            self.assertEqual(token.data_value(context.root), 19)

        obj = AttributeNode('age', '19')
        self.assertEqual(token.data_value(obj), UntypedAtomic('19'))
        self.assertIsInstance(obj, TextAttributeNode)

        obj = TextAttributeNode('age', '19')
        self.assertEqual(token.data_value(obj), UntypedAtomic('19'))

        obj = NamespaceNode('tns', 'http://xpath.test/ns')
        self.assertEqual(token.data_value(obj), 'http://xpath.test/ns')

        obj = TextNode('19')
        self.assertEqual(token.data_value(obj), UntypedAtomic('19'))

        obj = ElementTree.XML('<root>a<e1>b</e1>c<e2>d</e2>e</root>')
        element_node = ElementNode(obj)
        self.assertEqual(token.data_value(element_node), UntypedAtomic('abcde'))
        self.assertIsInstance(element_node, EtreeElementNode)

        element_node = EtreeElementNode(obj)
        self.assertEqual(token.data_value(element_node), UntypedAtomic('abcde'))

        obj = ElementTree.parse(io.StringIO('<root>a<e1>b</e1>c<e2>d</e2>e</root>'))
        document_node = DocumentNode(obj)
        self.assertEqual(token.data_value(document_node), UntypedAtomic('abcde'))

        obj = ElementTree.Comment("foo bar")
        comment_node = CommentNode(obj)
        self.assertEqual(token.data_value(comment_node), 'foo bar')

        obj = ElementTree.ProcessingInstruction('action', 'nothing to do')
        pi_node = ProcessingInstructionNode(obj)
        self.assertEqual(token.data_value(pi_node), 'nothing to do')

        self.assertIsNone(token.data_value(None))
        self.assertEqual(token.data_value(19), 19)
        self.assertEqual(token.data_value('19'), '19')
        self.assertFalse(token.data_value(False))

        tagged_object = Tagged()
        with self.assertRaises(TypeError):
            token.data_value(tagged_object)

    def test_string_value_function(self):
        token = self.parser.parse('true()')

        document = ElementTree.parse(io.StringIO(u'<A>123<B1>456</B1><B2>789</B2></A>'))
        element = ElementTree.Element('schema')
        comment = ElementTree.Comment('nothing important')
        pi = ElementTree.ProcessingInstruction('action', 'nothing to do')

        document_node = XPathContext(document).root

        context = XPathContext(element)
        element_node = context.root
        attribute_node = TextAttributeNode('id', '0212349350')
        namespace_node = NamespaceNode('xs', 'http://www.w3.org/2001/XMLSchema')
        comment_node = CommentNode(comment)
        pi_node = ProcessingInstructionNode(pi)
        text_node = TextNode('betelgeuse')

        self.assertEqual(token.string_value(document_node), '123456789')
        self.assertEqual(token.string_value(element_node), '')
        self.assertEqual(token.string_value(attribute_node), '0212349350')
        self.assertEqual(token.string_value(namespace_node), 'http://www.w3.org/2001/XMLSchema')
        self.assertEqual(token.string_value(comment_node), 'nothing important')
        self.assertEqual(token.string_value(pi_node), 'nothing to do')
        self.assertEqual(token.string_value(text_node), 'betelgeuse')
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
            element.text = '10'
            typed_elem = EtreeElementNode(elem=element)
            setattr(typed_elem, 'xsd_type', xsd_type)
            self.assertEqual(token.string_value(typed_elem), '10')
            self.assertEqual(token.data_value(typed_elem), 10)

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

    def test_xpath_error(self):
        token = self.parser.parse('.')

        with self.assertRaises(ValueError) as ctx:
            raise token.error('xml:XPST0003')
        self.assertIn('XPTY0004', str(ctx.exception))
        self.assertIn("'xml:XPST0003' is not an XPath error code",
                      str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            raise token.error('err:err:XPST0003')
        self.assertIn('XPTY0004', str(ctx.exception))
        self.assertIn("'err:err:XPST0003' is not an XPath error code",
                      str(ctx.exception))

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

        with self.assertRaises(MissingContextError) as ctx:
            raise token.missing_context()
        self.assertIn('XPDY0002', str(ctx.exception))

    def test_names_disambiguation(self):
        ambiguous_names = [
            symbol for symbol, tk_cls in self.parser.symbol_table.items()
            if self.parser.name_pattern.match(tk_cls.symbol) and '{' not in symbol
        ]

        path = '/'.join(ambiguous_names)
        root_token = self.parser.parse(path)
        for tk in root_token.iter():
            self.assertIn(tk.symbol, ('(root)', '/', '(name)'), msg=tk.symbol)

        for path in ambiguous_names:
            root_token = self.parser.parse(path)
            for tk in root_token.iter():
                self.assertEqual(tk.symbol, '(name)', msg=tk.symbol)


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
        with self.assertRaises(TypeError) as ctx:
            token.bind_namespace('http://xpath.test/ns')
        self.assertIn('XPST0017', str(ctx.exception))
        self.assertIn("a name, a wildcard or a function", str(ctx.exception))

    @unittest.skipIf(xmlschema is None, "xmlschema library required.")
    def test_xsd_type_labeling(self):
        schema = xmlschema.XMLSchema("""
            <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
              <xs:element name="root" type="xs:int"/>
              <xs:attribute name="a" type="xs:string"/>
            </xs:schema>""")
        self.parser.schema = xmlschema.xpath.XMLSchemaProxy(schema)

        try:
            context = XPathSchemaContext(root=schema, axis='self', schema=self.parser.schema)
            self.assertListEqual(list(context.iter_matching_nodes('root')), [])

            tag = '{%s}schema' % XSD_NAMESPACE
            self.assertListEqual(
                list(e.elem for e in context.iter_matching_nodes(tag)), [schema]
            )
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
            context = XPathSchemaContext(root=schema)
            obj = list(context.iter_matching_nodes('root'))
            self.assertIsInstance(obj[0], ElementNode)

            context.axis = 'self'
            root_token.xsd_types = None
            list(context.iter_matching_nodes('root'))
            self.assertIsNone(root_token.xsd_types)

            context.axis = None
            obj = list(context.iter_matching_nodes('root'))
            self.assertIsInstance(obj[0], ElementNode)

            context = XPathSchemaContext(root=schema.meta_schema)
            obj = list(context.iter_matching_nodes('root'))
            self.assertListEqual(obj, [])

            root_token = self.parser.parse('@a')

            context = XPathSchemaContext(root=schema.meta_schema, axis='self')
            xsd_attribute = schema.attributes['a']
            context.item = AttributeNode('a', xsd_attribute)
            setattr(context.item, 'xsd_type', xsd_attribute.type)

            obj = list(context.iter_matching_nodes('a'))
            self.assertIsInstance(obj[0], AttributeNode)
            self.assertIsNotNone(obj[0].xsd_type)

            root_token.xsd_types = None
            context = XPathSchemaContext(root=schema)
            list(context.iter_matching_nodes('a'))
            self.assertIsNone(root_token.xsd_types)

            context = XPathSchemaContext(root=schema.meta_schema, axis='self')
            attribute = context.item = SchemaAttributeNode(schema.attributes['a'])

            obj = list(context.iter_matching_nodes('a'))
            self.assertIsInstance(obj[0], AttributeNode)
            self.assertEqual(obj[0], attribute)
            self.assertIsInstance(obj[0].value, xmlschema.XsdAttribute)
            self.assertIsInstance(next(iter(obj[0].iter_typed_values), None), str)

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
            context = XPathContext(schema)

            try:
                root = context.root[0]
                value = token.string_value(root)  # 'root' element
                self.assertIsInstance(value, str)
                self.assertEqual(value, '1')
            finally:
                self.parser.schema = None


class XPath30TokenTest(XPath2TokenTest):

    @classmethod
    def setUpClass(cls):
        cls.parser = XPath30Parser(namespaces={'xs': XSD_NAMESPACE, 'tst': "http://xpath.test/ns"})


class XPath31TokenTest(XPath30TokenTest):

    @classmethod
    def setUpClass(cls):
        cls.parser = XPath31Parser(namespaces={'xs': XSD_NAMESPACE, 'tst': "http://xpath.test/ns"})


if __name__ == '__main__':
    unittest.main()
