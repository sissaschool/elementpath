#!/usr/bin/env python
#
# Copyright (c), 2022, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import unittest
from xml.etree import ElementTree

from elementpath.sequence_types import is_instance, is_sequence_type, \
    match_sequence_type
from elementpath import XPath2Parser, XPathContext
from elementpath.xpath3 import XPath30Parser
from elementpath.namespaces import XSD_NAMESPACE, XSD_UNTYPED_ATOMIC, \
    XSD_ANY_ATOMIC_TYPE, XSD_ANY_SIMPLE_TYPE
from elementpath.datatypes import UntypedAtomic


class SequenceTypesTest(unittest.TestCase):

    def test_is_instance_method(self):
        self.assertTrue(is_instance(UntypedAtomic(1), XSD_UNTYPED_ATOMIC))
        self.assertFalse(is_instance(1, XSD_UNTYPED_ATOMIC))
        self.assertTrue(is_instance(1, XSD_ANY_ATOMIC_TYPE))
        self.assertFalse(is_instance([1], XSD_ANY_ATOMIC_TYPE))
        self.assertTrue(is_instance(1, XSD_ANY_SIMPLE_TYPE))
        self.assertTrue(is_instance([1], XSD_ANY_SIMPLE_TYPE))

        self.assertTrue(is_instance('foo', '{%s}string' % XSD_NAMESPACE))
        self.assertFalse(is_instance(1, '{%s}string' % XSD_NAMESPACE))
        self.assertTrue(is_instance(1.0, '{%s}double' % XSD_NAMESPACE))
        self.assertFalse(is_instance(1.0, '{%s}float' % XSD_NAMESPACE))

        parser = XPath2Parser(xsd_version='1.1')
        self.assertTrue(is_instance(1.0, '{%s}double' % XSD_NAMESPACE), parser)
        self.assertFalse(is_instance(1.0, '{%s}float' % XSD_NAMESPACE), parser)

        with self.assertRaises(KeyError):
            is_instance('foo', '{%s}unknown' % XSD_NAMESPACE)

    def test_is_sequence_type(self):
        self.assertTrue(is_sequence_type('empty-sequence()'))
        self.assertTrue(is_sequence_type('xs:string'))
        self.assertTrue(is_sequence_type('xs:float+'))
        self.assertTrue(is_sequence_type('element()*'))
        self.assertTrue(is_sequence_type('item()?'))
        self.assertTrue(is_sequence_type('xs:untypedAtomic+'))

        self.assertFalse(is_sequence_type(10))
        self.assertFalse(is_sequence_type(''))
        self.assertFalse(is_sequence_type('empty-sequence()*'))
        self.assertFalse(is_sequence_type('unknown'))
        self.assertFalse(is_sequence_type('unknown?'))
        self.assertFalse(is_sequence_type('tns0:unknown'))

        self.assertTrue(is_sequence_type(' element( ) '))
        self.assertTrue(is_sequence_type(' element( * ) '))
        self.assertFalse(is_sequence_type(' element( *, * ) '))
        self.assertTrue(is_sequence_type('element(A)'))
        self.assertTrue(is_sequence_type('element(A, xs:date)'))
        self.assertTrue(is_sequence_type('element(*, xs:date)'))
        self.assertFalse(is_sequence_type('element(A, B, xs:date)'))

        self.assertFalse(is_sequence_type('function(*)'))

        parser = XPath2Parser()
        self.assertFalse(is_sequence_type('function(*)', parser))

        parser = XPath30Parser()
        self.assertTrue(is_sequence_type('function(*)', parser))

    def test_match_sequence_type_function(self):
        self.assertTrue(match_sequence_type(None, 'empty-sequence()'))
        self.assertTrue(match_sequence_type([], 'empty-sequence()'))
        self.assertFalse(match_sequence_type('', 'empty-sequence()'))

        self.assertFalse(match_sequence_type('', 'empty-sequence()'))

        context = XPathContext(ElementTree.XML('<root><e1/><e2/><e3/></root>'))
        root = context.root

        self.assertTrue(match_sequence_type(root, 'element()'))
        self.assertTrue(match_sequence_type([root], 'element()'))
        self.assertTrue(match_sequence_type(root, 'element()?'))
        self.assertTrue(match_sequence_type(root, 'element()+'))
        self.assertTrue(match_sequence_type(root, 'element()*'))
        self.assertFalse(match_sequence_type(root[:], 'element()'))
        self.assertFalse(match_sequence_type(root[:], 'element()?'))
        self.assertTrue(match_sequence_type(root[:], 'element()+'))
        self.assertTrue(match_sequence_type(root[:], 'element()*'))

        parser = XPath2Parser()
        self.assertTrue(match_sequence_type(UntypedAtomic(1), 'xs:untypedAtomic'))
        self.assertFalse(match_sequence_type(1, 'xs:untypedAtomic'))

        self.assertTrue(match_sequence_type('1', 'xs:string'))
        self.assertFalse(match_sequence_type(1, 'xs:string'))

        with self.assertRaises(NameError) as ctx:
            match_sequence_type('1', 'xs:unknown', parser)
        self.assertIn('XPST0051', str(ctx.exception))

        with self.assertRaises(NameError) as ctx:
            match_sequence_type('1', 'tns0:string', parser)
        self.assertIn('XPST0051', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
