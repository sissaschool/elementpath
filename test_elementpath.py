#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c), 2018, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import unittest
import os
from xml.etree import ElementTree as etree
import lxml.etree

from elementpath import *


class TokenizerTest(unittest.TestCase):

    def test_xpath_tokenizer(self):
        def check_tokens(path, expected):
            self.assertEqual([
                lit or op or ref for lit, op, ref in XPath1Parser.tokenizer.findall(path)
            ], expected)

        # tests from the XPath specification
        check_tokens("*", ['*'])
        check_tokens("text()", ['text(', ')'])
        check_tokens("@name", ['@', 'name'])
        check_tokens("@*", ['@', '*'])
        check_tokens("para[1]", ['para', '[', '1', ']'])
        check_tokens("para[last()]", ['para', '[', 'last(', ')', ']'])
        check_tokens("*/para", ['*', '/', 'para'])
        check_tokens("/doc/chapter[5]/section[2]",
              ['/', 'doc', '/', 'chapter', '[', '5', ']',
               '/', 'section', '[', '2', ']'])
        check_tokens("chapter//para", ['chapter', '//', 'para'])
        check_tokens("//para", ['//', 'para'])
        check_tokens("//olist/item", ['//', 'olist', '/', 'item'])
        check_tokens(".", ['.'])
        check_tokens(".//para", ['.', '//', 'para'])
        check_tokens("..", ['..'])
        check_tokens("../@lang", ['..', '/', '@', 'lang'])
        check_tokens("chapter[title]", ['chapter', '[', 'title', ']'])
        check_tokens("employee[@secretary and @assistant]", ['employee',
              '[', '@', 'secretary', '', 'and', '', '@', 'assistant', ']'])

        # additional tests from Python XML etree test cases
        check_tokens("{http://spam}egg", ['{http://spam}egg'])
        check_tokens("./spam.egg", ['.', '/', 'spam.egg'])
        check_tokens(".//{http://spam}egg", ['.', '//', '{http://spam}egg'])

        # additional tests
        check_tokens("(: this is a comment :)", ['(:', '', 'this', '', 'is', '', 'a', '', 'comment', '', ':)'])
        check_tokens("substring-after()", ['substring-after(', ')'])
        check_tokens("contains('XML','XM')", ['contains(', "'XML'", ',', "'XM'", ')'])
        check_tokens("concat('XML', true(), 10)", ['concat(', "'XML'", ',', '', 'true(', ')', ',', '', '10', ')'])
        check_tokens("concat('a', 'b', 'c')", ['concat(', "'a'", ',', '', "'b'", ',', '', "'c'", ')'])


class XPath1ParserTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.parser = XPath1Parser()

    def check_value(self, path, expected):
        self.assertEqual(self.parser.parse(path).eval(), expected)

    def check_tree(self, path, expected):
        self.assertEqual(self.parser.parse(path).tree, expected)

    def check_select(self, path, namespaces, root, expected):
        selector = ElementPathSelector(path, namespaces, parser=XPath1Parser)
        self.assertEqual(list(selector.select(root)), expected)

    def wrong_syntax(self, path):
        self.assertRaises(ElementPathSyntaxError, self.parser.parse, path)

    def wrong_value(self, path):
        self.assertRaises(ElementPathValueError, self.parser.parse, path)

    def wrong_type(self, path):
        self.assertRaises(ElementPathTypeError, self.parser.parse, path)

    def test_implementation(self):
        self.assertEqual(self.parser.unregistered(), [])

    def test_xpath_comment(self):
        self.check_value("(: this is a comment :)", 'this is a comment')
        self.check_value("(: this is a (: nested :) comment :)", 'this is a (: nested :) comment')

    def test_node_set_functions(self):
        pass # self.check_value("position()<=3", '10.0')
        #  self.check_value("contains('XPath','XP')", True)

    def test_string_functions(self):
        self.check_value("string(10.0)", '10.0')
        self.check_value("contains('XPath','XP')", True)
        self.check_value("contains('XP','XPath')", False)
        self.wrong_type("contains('XPath', 20)")
        self.wrong_syntax("contains('XPath', 'XP', 20)")
        self.check_value("concat('alpha', 'beta', 'gamma')", 'alphabetagamma')
        self.wrong_type("concat('alpha', 10, 'gamma')")
        self.wrong_syntax("concat()")
        self.check_value("string-length('hello world')", 11)
        self.check_value("normalize-space('  hello  \t  world ')", 'hello world')
        self.check_value("starts-with('Hello World', 'Hello')", True)
        self.check_value("starts-with('Hello World', 'hello')", False)
        self.check_value("translate('hello world', 'hw', 'HW')", 'Hello World')
        self.wrong_value("translate('hello world', 'hwx', 'HW')")
        self.check_value("substring('Preem Palver', 1)", 'Preem Palver')
        self.check_value("substring('Preem Palver', 2)", 'reem Palver')
        self.check_value("substring('Preem Palver', 7)", 'Palver')
        self.check_value("substring('Preem Palver', 1, 5)", 'Preem')
        self.wrong_type("substring('Preem Palver', 'c', 5)")
        self.wrong_type("substring('Preem Palver', 1, '5')")
        self.check_value("substring-before('Wolfgang Amadeus Mozart', 'Wolfgang')", '')
        self.check_value("substring-before('Wolfgang Amadeus Mozart', 'Amadeus')", 'Wolfgang ')
        self.wrong_type("substring-before('2017-10-27', 10)")
        self.check_value("substring-after('Wolfgang Amadeus Mozart', 'Amadeus ')", 'Mozart')
        self.check_value("substring-after('Wolfgang Amadeus Mozart', 'Mozart')", '')

    def test_boolean_functions(self):
        self.check_value("true()", True)
        self.check_value("false()", False)
        self.check_value("not(false())", True)
        self.check_value("not(true())", False)
        self.check_value("boolean(0)", False)
        self.check_value("boolean(1)", True)
        self.check_value("boolean(-1)", True)
        self.check_value("boolean('hello!')", True)
        self.check_value("boolean('   ')", True)
        self.check_value("boolean('')", False)
        # self.check_value("boolean()", False)  Maybe incorrect

    def test_child_operator(self):
        root = etree.XML('<A><B1><C/></B1><B2/><B3><C1/><C2/></B3></A>')
        self.check_select('/', None, root, [])

    def test_child_axis(self):
        root = etree.XML('<A>A text<B1>B1 text</B1><B2/><B3>B3 text</B3></A>')
        self.check_select('child::B1', None, root, [])
        self.check_select('child::A', None, root, [root])
        self.check_select('child::text()', None, root, ['A text'])
        self.check_select('child::node()', None, root, [root])
        self.check_select('child::*', None, root, [root])
        self.check_select('child::1', None, root, [root])

    def test_attribute_axis(self):
        root = etree.XML('<A id="1" a="alpha"><B1 b="beta1"/><B2/><B3/></A>')
        self.check_select('child::B1', None, root, [])


    def test_token_tree(self):
        self.check_tree('child::B1', '(child:: (B1))')


    def test_wrong_path(self):
        # self.check_value("*", '')
        self.wrong_syntax("     \n     \n   )")


class LxmlEtreeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_dir = os.path.dirname(__file__)
        cls.XML = lxml.etree.XML


if __name__ == '__main__':
    unittest.main()
