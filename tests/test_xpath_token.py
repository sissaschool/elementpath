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

from elementpath.namespaces import XSD_NAMESPACE
from elementpath.xpath_nodes import AttributeNode, TypedAttribute, TypedElement, NamespaceNode
from elementpath.xpath_token import ordinal
from elementpath.xpath_context import XPathContext
from elementpath.xpath1_parser import XPath1Parser


class XPathTokenTest(unittest.TestCase):

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
        text = u'betelgeuse'
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


if __name__ == '__main__':
    unittest.main()
