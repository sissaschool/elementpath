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
from xml.etree import ElementTree
import lxml.etree

from elementpath import *


class ElementPathTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.parser = None

    def check_tree(self, path, expected):
        self.assertEqual(self.parser.parse(path).tree, expected)

    def check_value(self, path, expected, context=None):
        if isinstance(expected, type) and issubclass(expected, Exception):
            self.assertRaises(expected, self.parser.parse(path).eval, context)
        else:
            self.assertEqual(self.parser.parse(path).eval(context), expected)

    def check_select(self, path, root, expected, namespaces=None, schema=None):
        if isinstance(expected, type) and issubclass(expected, Exception):
            self.assertRaises(expected, select, root, path, namespaces, schema, self.parser.__class__)
        else:
            selector = select(root, path, namespaces, schema, self.parser.__class__)
            self.assertEqual(list(selector), expected)

    def wrong_syntax(self, path):
        self.assertRaises(ElementPathSyntaxError, self.parser.parse, path)

    def wrong_value(self, path):
        self.assertRaises(ElementPathValueError, self.parser.parse, path)

    def wrong_type(self, path):
        self.assertRaises(ElementPathTypeError, self.parser.parse, path)


class XPath1ParserTest(ElementPathTest):

    @classmethod
    def setUpClass(cls):
        cls.parser = XPath1Parser()
        cls.etree = ElementTree

    def test_xpath_tokenizer(self):
        def check_tokens(path, expected):
            self.assertEqual([
                lit or op or ref for lit, op, ref in self.parser.__class__.tokenizer.findall(path)
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
                     ['/', 'doc', '/', 'chapter', '[', '5', ']', '/', 'section', '[', '2', ']'])
        check_tokens("chapter//para", ['chapter', '//', 'para'])
        check_tokens("//para", ['//', 'para'])
        check_tokens("//olist/item", ['//', 'olist', '/', 'item'])
        check_tokens(".", ['.'])
        check_tokens(".//para", ['.', '//', 'para'])
        check_tokens("..", ['..'])
        check_tokens("../@lang", ['..', '/', '@', 'lang'])
        check_tokens("chapter[title]", ['chapter', '[', 'title', ']'])
        check_tokens("employee[@secretary and @assistant]",
                     ['employee', '[', '@', 'secretary', '', 'and', '', '@', 'assistant', ']'])

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

    def test_implementation(self):
        self.assertEqual(self.parser.unregistered(), [])

    def test_token_tree(self):
        self.check_tree('child::B1', '(child:: (B1))')
        self.check_tree('A/B//C/D', '(/ (// (/ (A) (B)) (C)) (D))')
        self.check_tree('child::*/child::B1', '(/ (child:: (*)) (child:: (B1)))')
        self.check_tree('attribute::name="Galileo"', '(attribute:: (= (name) (Galileo)))')
        self.check_tree('1 + 2 * 3', '(+ (1) (* (2) (3)))')
        self.check_tree('(1 + 2) * 3', '(* (+ (1) (2)) (3))')
        self.check_tree("false() and true()", '(and (False) (True))')
        self.check_tree("false() or true()", '(or (False) (True))')

    def test_wrong_syntax(self):
        # self.check_value("*", '')
        self.wrong_syntax("     \n     \n   )")
        self.wrong_syntax('child::1')

    # Features tests
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

    def test_logical_expressions(self):
        self.check_value("false() and true()", False)
        self.check_value("false() or true()", True)
        self.check_value("true() or false()", True)
        self.check_value("true() and true()", True)
        self.check_value("1 and 0", False)
        self.check_value("1 and 1", True)
        self.check_value("1 and 'jupiter'", True)
        self.check_value("0 and 'mars'", False)
        #self.check_value("1 and mars", False)

    def test_numerical_expressions(self):
        self.check_value("9 - 1 + 6", 14)
        self.check_value("-3", -3)
        self.check_value("-3", -3)
        self.check_value("-3 * 7", -21)
        self.check_value("(5 * 7) + 9", 44)
        self.check_value("-3 * 7", -21)

    def test_context_variables(self):
        root = self.etree.XML('<A><B1><C/></B1><B2/><B3><C1/><C2/></B3></A>')
        self.check_value("$alpha", ElementPathNameError)
        self.check_value("$alpha", 10, XPathContext(root, variables={'alpha': 10}))

    def test_child_operator(self):
        root = self.etree.XML('<A><B1><C/></B1><B2/><B3><C1/><C2/></B3></A>')
        self.check_select('/', root, [root])  # Should be the XML "document"
        self.check_select('/B1', root, [])
        self.check_select('/A1', root, [])
        self.check_select('/A', root, [root])
        self.check_select('/A/B1', root, [root[0]])
        self.check_select('/A/*', root, [root[0], root[1], root[2]])
        self.check_select('/*/*', root, [root[0], root[1], root[2]])
        self.check_select('/A/B1/C', root, [root[0][0]])
        self.check_select('/A/B1/*', root, [root[0][0]])
        self.check_select('/A/B3/*', root, [root[2][0], root[2][1]])
        self.check_select('child::*/child::B1', root, [root[0]])
        #self.check_select('/A/child::C', root, [root[0]])

    def test_self_shortcut(self):
        root = self.etree.XML('<A><B1><C/></B1><B2/><B3><C1/><C2/></B3></A>')
        self.check_select('.', root, [root])
        self.check_select('/././.', root, [root])
        self.check_select('/A/.', root, [root])
        self.check_select('/A/B1/.', root, [root[0]])
        self.check_select('/A/B1/././.', root, [root[0]])

    def test_descendant_or_self_shortcut(self):
        root = self.etree.XML('<A><B1><C/></B1><B2/><B3><C/><C1/></B3></A>')
        self.check_select('//.', root, [root] + [e for e in root.iter()])
        self.check_select('/A//.', root, [e for e in root.iter()])
        self.check_select('//C1', root, [root[2][1]])
        self.check_select('//B2', root, [root[1]])
        self.check_select('//C', root, [root[0][0], root[2][0]])
        self.check_select('//*', root, [e for e in root.iter()])

    def test_self_axis(self):
        root = self.etree.XML('<A>A text<B1>B1 text</B1><B2/><B3>B3 text</B3></A>')
        self.check_select('self::node()', root, [root])
        self.check_select('self::text()', root, [])

    def test_child_axis(self):
        root = self.etree.XML('<A>A text<B1>B1 text</B1><B2/><B3>B3 text</B3></A>')
        self.check_select('child::B1', root, [])
        self.check_select('child::A', root, [root])
        self.check_select('child::text()', root, ['A text'])
        self.check_select('child::node()', root, [root])
        self.check_select('child::*', root, [root])

    def test_descendant_axis(self):
        root = self.etree.XML('<A><B1><C/></B1><B2/><B3><C1/><C2/></B3></A>')
        self.check_select('descendant::node()', root, [e for e in root.iter()])
        self.check_select('descendant-or-self::node()', root, [root] + [e for e in root.iter()])
        self.check_select('descendant-or-self::node()/.', root, [e for e in root.iter()])

    def test_parent_axis(self):
        root = self.etree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2/></B3><B4><C3><D1/></C3></B4></A>')
        self.check_select('/A/*/C2/..', root, [root[2]])
        self.check_select('/A/*/*/..', root, [root[0], root[2], root[3]])
        self.check_select('//C2/..', root, [root[2]])

    def test_attribute_axis_and_shortcut(self):
        root = self.etree.XML('<A id="1" a="alpha"><B1 b1="beta1"/><B2/><B3 b2="beta2" b3="beta3"/></A>')
        self.check_select('/A/B1/attribute::*', root, ['beta1'])
        self.check_select('/A/B1/@*', root, ['beta1'])
        self.check_select('/A/B3/attribute::*', root, ['beta2', 'beta3'])
        self.check_select('/A/attribute::*', root, ['1', 'alpha'])

    def test_following_axis(self):
        root = self.etree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2/></B3><B4><C1><D1/></C1></B4></A>')
        self.check_select('/A/B1/C1/following::*', root, [
            root[1], root[2], root[2][0], root[2][1], root[3], root[3][0], root[3][0][0]
        ])
        self.check_select('/A/B1/following::C1', root, [root[2][0], root[3][0]])

    def test_following_sibling_axis(self):
        root = self.etree.XML('<A><B1><C1/><C2/><C3/></B1><B2><C1/><C2/><C3/><C4/></B2></A>')
        self.check_select('/A/B1/C1/following-sibling::*', root, [root[0][1], root[0][2]])
        self.check_select('/A/B2/C1/following-sibling::*', root, [root[1][1], root[1][2], root[1][3]])
        self.check_select('/A/B1/C1/following-sibling::C3', root, [root[0][2]])

    def test_ancestor_axes(self):
        root = self.etree.XML('<A><B1><C1/></B1><B2><C1/><D2><E1/><E2/></D2><C2/></B2><B3><C1><D1/></C1></B3></A>')
        self.check_select('/A/B4/C1/ancestor::*', root, [])
        self.check_select('/A/B3/C1/ancestor::*', root, [root, root[2]])
        self.check_select('/A/*/C1/ancestor::*', root, [root, root[0], root[1], root[2]])
        self.check_select('/A/*/C1/ancestor::B3', root, [root[2]])
        self.check_select('/A/B3/C1/ancestor-or-self::*', root, [root, root[2], root[2][0]])
        self.check_select('/A/*/C1/ancestor-or-self::*', root, [
            root, root[0], root[0][0], root[1], root[1][0], root[2], root[2][0]
        ])

    def test_preceding_sibling_axis(self):
        root = self.etree.XML('<A><B1><C1/><C2/><C3/></B1><B2><C1/><C2/><C3/><C4/></B2></A>')
        self.check_select('/A/B1/C2/preceding-sibling::*', root, [root[0][0]])
        self.check_select('/A/B2/C4/preceding-sibling::*', root, [root[1][0], root[1][1], root[1][2]])
        self.check_select('/A/B1/C2/preceding-sibling::C3', root, [root[0][0]])

    def test_preceding_axis(self):
        root = self.etree.XML('<A><B1><C1/><C2/><C3/></B1><B2><C1/><C2/><C3/><C4/></B2></A>')
        self.check_select('/A/B1/C2/preceding::*', root, [root[0][0]])
        self.check_select('/A/B2/C4/preceding::*', root, [
            root[0], root[0][0], root[0][1], root[0][2], root[1][0], root[1][1], root[1][2]
        ])


class LxmlXPath1ParserTest(XPath1ParserTest):

    @classmethod
    def setUpClass(cls):
        cls.parser = XPath1Parser()
        cls.etree = lxml.etree


class XPath2ParserTest(XPath1ParserTest):

    @classmethod
    def setUpClass(cls):
        cls.parser = XPath2Parser()

    def test_token_tree2(self):
        self.check_tree('(1 + 6, 2, 10 - 4)', '(, (, (+ (1) (6)) (2)) (- (10) (4)))')

    def test_wrong_syntax2(self):
        self.wrong_syntax("count(0, 1, 2)")

    def test_aggregate_functions(self):
        self.check_value("count((0, 1, 2 + 1, 3 - 1))", 4)

    def test_if_expression(self):
        self.check_value("if (1) then 2 else 3", 2)


if __name__ == '__main__':
    unittest.main()
