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
import decimal
import io
from collections import namedtuple
from xml.etree import ElementTree
import lxml.etree

from elementpath import *

try:
    # noinspection PyPackageRequirements
    import xmlschema
except ImportError:
    xmlschema = None


class XPath1ParserTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.parser = XPath1Parser()
        cls.etree = ElementTree

    def check_tokenizer(self, path, expected):
        self.assertEqual([
            lit or op or ref or unexpected
            for lit, op, ref, unexpected in self.parser.__class__.tokenizer.findall(path)
        ], expected)

    def check_token(self, symbol, expected_label=None, expected_str=None, expected_repr=None, value=None):
        token = self.parser.symbol_table[symbol](self.parser, value)
        self.assertEqual(token.symbol, symbol)
        if expected_label is not None:
            self.assertEqual(token.label, expected_label)
        if expected_str is not None:
            self.assertEqual(str(token), expected_str)
        if expected_repr is not None:
            self.assertEqual(repr(token), expected_repr)

    def check_tree(self, path, expected):
        self.assertEqual(self.parser.parse(path).tree, expected)

    def check_value(self, path, expected, context=None):
        if isinstance(expected, type) and issubclass(expected, Exception):
            self.assertRaises(expected, self.parser.parse(path).evaluate, context)
        else:
            self.assertEqual(self.parser.parse(path).evaluate(context), expected)

    def check_sequence(self, path, expected, context=None):
        if context is None:
            context = XPathContext(root=self.etree.Element(u'dummy_root'))
        if isinstance(expected, type) and issubclass(expected, Exception):
            self.assertRaises(expected, self.parser.parse(path).select, context)
        else:
            self.assertEqual(list(self.parser.parse(path).select(context)), expected)

    def check_select(self, path, root, expected, namespaces=None, **kwargs):
        if isinstance(expected, type) and issubclass(expected, Exception):
            self.assertRaises(expected, select, root, path, namespaces, self.parser.__class__, **kwargs)
        else:
            results = select(root, path, namespaces, self.parser.__class__, **kwargs)
            if isinstance(expected, set):
                self.assertEqual(set(results), expected)
            else:
                self.assertEqual(results, expected)

    def wrong_syntax(self, path):
        self.assertRaises(ElementPathSyntaxError, self.parser.parse, path)

    def wrong_value(self, path):
        self.assertRaises(ElementPathValueError, self.parser.parse, path)

    def wrong_type(self, path):
        self.assertRaises(ElementPathTypeError, self.parser.parse, path)

    def test_xpath_tokenizer(self):
        # tests from the XPath specification
        self.check_tokenizer("*", ['*'])
        self.check_tokenizer("text()", ['text', '(', ')'])
        self.check_tokenizer("@name", ['@', 'name'])
        self.check_tokenizer("@*", ['@', '*'])
        self.check_tokenizer("para[1]", ['para', '[', '1', ']'])
        self.check_tokenizer("para[last()]", ['para', '[', 'last', '(', ')', ']'])
        self.check_tokenizer("*/para", ['*', '/', 'para'])
        self.check_tokenizer("/doc/chapter[5]/section[2]",
                             ['/', 'doc', '/', 'chapter', '[', '5', ']', '/', 'section', '[', '2', ']'])
        self.check_tokenizer("chapter//para", ['chapter', '//', 'para'])
        self.check_tokenizer("//para", ['//', 'para'])
        self.check_tokenizer("//olist/item", ['//', 'olist', '/', 'item'])
        self.check_tokenizer(".", ['.'])
        self.check_tokenizer(".//para", ['.', '//', 'para'])
        self.check_tokenizer("..", ['..'])
        self.check_tokenizer("../@lang", ['..', '/', '@', 'lang'])
        self.check_tokenizer("chapter[title]", ['chapter', '[', 'title', ']'])
        self.check_tokenizer("employee[@secretary and @assistant]",
                             ['employee', '[', '@', 'secretary', '', 'and', '', '@', 'assistant', ']'])

        # additional tests from Python XML etree test cases
        self.check_tokenizer("{http://spam}egg", ['{', 'http', ':', '//', 'spam', '}', 'egg'])
        self.check_tokenizer("./spam.egg", ['.', '/', 'spam.egg'])
        self.check_tokenizer(".//spam:egg", ['.', '//', 'spam', ':', 'egg'])

        # additional tests
        self.check_tokenizer("substring-after()", ['substring-after', '(', ')'])
        self.check_tokenizer("contains('XML','XM')", ['contains', '(', "'XML'", ',', "'XM'", ')'])
        self.check_tokenizer("concat('XML', true(), 10)",
                             ['concat', '(', "'XML'", ',', '', 'true', '(', ')', ',', '', '10', ')'])
        self.check_tokenizer("concat('a', 'b', 'c')", ['concat', '(', "'a'", ',', '', "'b'", ',', '', "'c'", ')'])
        self.check_tokenizer("_last()", ['_last', '(', ')'])
        self.check_tokenizer("last ()", ['last', '', '(', ')'])
        self.check_tokenizer('child::text()', ['child', '::', 'text', '(', ')'])

    def test_tokens(self):
        # Literals
        self.check_token('(string)', 'literal', "'hello' string",
                         "token(symbol='(string)', value='hello')", 'hello')
        self.check_token('(integer)', 'literal', "1999 integer",
                         "token(symbol='(integer)', value=1999)", 1999)
        self.check_token('(float)', 'literal', "3.1415 float",
                         "token(symbol='(float)', value=3.1415)", 3.1415)
        self.check_token('(decimal)', 'literal', "217.35 decimal",
                         "token(symbol='(decimal)', value=217.35)", 217.35)
        self.check_token('(name)', 'literal', "'schema' name",
                         "token(symbol='(name)', value='schema')", 'schema')

        # Axes
        self.check_token('self', 'axis', "self axis", "token(symbol='self')")
        self.check_token('child', 'axis', "child axis", "token(symbol='child')")
        self.check_token('parent', 'axis', "parent axis", "token(symbol='parent')")
        self.check_token('ancestor', 'axis', "ancestor axis", "token(symbol='ancestor')")
        self.check_token('preceding', 'axis', "preceding axis", "token(symbol='preceding')")
        self.check_token('descendant-or-self', 'axis', "descendant-or-self axis")
        self.check_token('following-sibling', 'axis', "following-sibling axis")
        self.check_token('preceding-sibling', 'axis', "preceding-sibling axis")
        self.check_token('ancestor-or-self', 'axis', "ancestor-or-self axis")
        self.check_token('descendant', 'axis', "descendant axis")
        self.check_token('attribute', 'axis', "attribute axis")
        self.check_token('following', 'axis', "following axis")
        self.check_token('namespace', 'axis', "namespace axis")

        # Functions
        self.check_token('position', 'function', "position() function", "token(symbol='position')")

        # Operators
        self.check_token('and', 'operator', "'and' operator", "token(symbol='and')")

    def test_implementation(self):
        self.assertEqual(self.parser.unregistered(), [])

    def test_token_tree(self):
        self.check_tree('child::B1', '(child (B1))')
        self.check_tree('A/B//C/D', '(/ (// (/ (A) (B)) (C)) (D))')
        self.check_tree('child::*/child::B1', '(/ (child (*)) (child (B1)))')
        self.check_tree('attribute::name="Galileo"', '(= (attribute (name)) (Galileo))')
        self.check_tree('1 + 2 * 3', '(+ (1) (* (2) (3)))')
        self.check_tree('(1 + 2) * 3', '(* (+ (1) (2)) (3))')
        self.check_tree("false() and true()", '(and (False) (True))')
        self.check_tree("false() or true()", '(or (False) (True))')
        self.check_tree("./A/B[C][D]/E", '(/ (/ (/ (.) (A)) ([ ([ (B) (C)) (D))) (E))')

    def test_wrong_syntax(self):
        self.wrong_syntax('')
        self.wrong_syntax("     \n     \n   )")
        self.wrong_syntax('child::1')
        self.wrong_syntax("count(0, 1, 2)")
        self.wrong_syntax("{http://spam}egg")
        self.wrong_syntax("./*:*")

    # Features tests
    def test_references(self):
        namespaces = {'tst': "http://xpath.test/ns"}
        root = self.etree.XML("""
        <A xmlns:tst="http://xpath.test/ns">
            <tst:B1 b1="beta1"/>
            <tst:B2/>
            <tst:B3 b2="tst:beta2" b3="beta3"/>
        </A>""")
        self.check_value("fn:true()", True)
        self.check_select("./tst:B1", root, [root[0]], namespaces=namespaces)
        self.check_select("./tst:*", root, root[:], namespaces=namespaces)
        self.check_select("./tst:*", root, root[:], namespaces=namespaces)

        # Namespace wildcard works only for XPath > 1.0
        if self.parser.version == '1.0':
            self.check_select("./*:B2", root, Exception, namespaces=namespaces)
        else:
            self.check_select("./*:B2", root, [root[1]], namespaces=namespaces)

    def test_node_types(self):
        document = self.etree.parse(io.StringIO(u'<A/>'))
        element = self.etree.Element('schema')
        attribute = 'id', '0212349350'
        namespace = namedtuple('Namespace', 'prefix uri')('xs', 'http://www.w3.org/2001/XMLSchema')
        comment = self.etree.Comment('nothing important')
        pi = self.etree.ProcessingInstruction('nothing', 'nothing to do')
        text = u'aldebaran'
        context = XPathContext(element)
        self.check_sequence("node()", [document.getroot()], context=XPathContext(document))
        self.check_sequence("node()", [element], context)
        context.item = attribute
        self.check_sequence("node()", [attribute], context)
        context.item = namespace
        self.check_sequence("node()", [namespace], context)
        context.item = comment
        self.check_sequence("node()", [comment], context)
        self.check_sequence("comment()", [comment], context)
        context.item = pi
        self.check_sequence("node()", [pi], context)
        self.check_sequence("processing-instruction()", [pi], context)
        context.item = text
        self.check_sequence("node()", [text], context)
        self.check_sequence("text()", [text], context)

    def test_node_set_id_function(self):
        # TODO
        pass

    def test_node_set_functions(self):
        root = self.etree.XML('<A><B1><C1/><C2/></B1><B2/><B3><C3/><C4/><C5/></B3></A>')
        context = XPathContext(root, item=root[1], size=3, position=3)
        self.check_value("position()", 0)
        self.check_value("position()", 4, context=context)
        self.check_value("position()<=2", True)
        self.check_value("position()<=2", False, context=context)
        self.check_value("position()=4", True, context=context)
        self.check_value("position()=3", False, context=context)
        self.check_value("last()", 0)
        self.check_value("last()", 3, context=context)
        self.check_value("last()-1", 2, context=context)

        self.check_value("count((0, 1, 2 + 1, 3 - 1))", 4)

        self.check_select("name(.)", root, 'A')
        self.check_select("name(A)", root, '')
        self.check_select("local-name(A)", root, '')
        self.check_select("namespace-uri(A)", root, '')
        self.check_select("name(B2)", root, 'B2')
        self.check_select("local-name(B2)", root, 'B2')
        self.check_select("namespace-uri(B2)", root, '')
        if self.parser.version <= '1.0':
            self.check_select("name(*)", root, 'B1')

        root = self.etree.XML('<tst:A xmlns:tst="http://xpath.test/ns"><tst:B1/></tst:A>')
        self.check_select("name(.)", root, 'tst:A', namespaces={'tst': "http://xpath.test/ns"})
        self.check_select("local-name(.)", root, 'A')
        self.check_select("namespace-uri(.)", root, 'http://xpath.test/ns')
        self.check_select("name(tst:B1)", root, 'tst:B1', namespaces={'tst': "http://xpath.test/ns"})

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
        self.wrong_syntax("boolean()")      # Argument required
        self.wrong_syntax("boolean(1, 5)")  # Too much arguments

    def test_logical_expressions(self):
        self.check_value("false() and true()", False)
        self.check_value("false() or true()", True)
        self.check_value("true() or false()", True)
        self.check_value("true() and true()", True)
        self.check_value("1 and 0", False)
        self.check_value("1 and 1", True)
        self.check_value("1 and 'jupiter'", True)
        self.check_value("0 and 'mars'", False)
        self.check_value("1 and mars", False)

    # TEST: comparison operators

    def test_numerical_expressions(self):
        self.check_value("9", 9)
        self.check_value("-3", -3)
        self.check_value("7.1", decimal.Decimal('7.1'))
        self.check_value("0.45e3", 0.45e3)
        self.check_value(" 7+5 ", 12)
        self.check_value("8 - 5", 3)
        self.check_value("-8 - 5", -13)
        self.check_value("5 div 2", 2.5)
        self.check_value("11 mod 3", 2)
        self.check_value("4.5 mod 1.2", decimal.Decimal('0.9'))
        self.check_value("1.23E2 mod 0.6E1", 3.0E0)
        self.check_value("-3 * 7", -21)
        self.check_value("9 - 1 + 6", 14)
        self.check_value("(5 * 7) + 9", 44)
        self.check_value("-3 * 7", -21)

    def test_context_variables(self):
        root = self.etree.XML('<A><B1><C/></B1><B2/><B3><C1/><C2/></B3></A>')
        context = XPathContext(root, variables={'alpha': 10, 'id': '19273222'})
        self.check_value("$alpha", ElementPathNameError)
        self.check_value("$alpha", 10, context=context)
        self.check_value("$beta", ElementPathNameError, context=context)
        self.check_value("$id", '19273222', context=context)
        self.wrong_syntax("$id()")

    def test_child_operator(self):
        root = self.etree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2/></B3></A>')
        self.check_select('/', root, [])  # a root element is not a document!
        self.check_select('/B1', root, [])
        self.check_select('/A1', root, [])
        self.check_select('/A', root, [root])
        self.check_select('/A/B1', root, [root[0]])
        self.check_select('/A/*', root, [root[0], root[1], root[2]])
        self.check_select('/*/*', root, [root[0], root[1], root[2]])
        self.check_select('/A/B1/C1', root, [root[0][0]])
        self.check_select('/A/B1/*', root, [root[0][0]])
        self.check_select('/A/B3/*', root, [root[2][0], root[2][1]])
        self.check_select('child::*/child::C1', root, [root[0][0], root[2][0]])
        self.check_select('/A/child::B3', root, [root[2]])
        self.check_select('/A/child::C1', root, [])

    def test_context_item_expression(self):
        root = self.etree.XML('<A><B1><C/></B1><B2/><B3><C1/><C2/></B3></A>')
        self.check_select('.', root, [root])
        self.check_select('/././.', root, [])
        self.check_select('/A/.', root, [root])
        self.check_select('/A/B1/.', root, [root[0]])
        self.check_select('/A/B1/././.', root, [root[0]])
        self.check_select('1/.', root, ElementPathTypeError)

    def test_self_axis(self):
        root = self.etree.XML('<A>A text<B1>B1 text</B1><B2/><B3>B3 text</B3></A>')
        self.check_select('self::node()', root, [root])
        self.check_select('self::text()', root, [])

    def test_child_axis(self):
        root = self.etree.XML('<A>A text<B1>B1 text</B1><B2/><B3>B3 text</B3></A>')
        self.check_select('child::B1', root, [root[0]])
        self.check_select('child::A', root, [])
        self.check_select('child::text()', root, ['A text'])
        self.check_select('child::node()', root, ['A text'] + root[:])
        self.check_select('child::*', root, root[:])

    def test_descendant_axis(self):
        root = self.etree.XML('<A><B1><C/></B1><B2/><B3><C1/><C2/></B3></A>')
        self.check_select('descendant::node()', root, [e for e in root.iter()][1:])
        self.check_select('/descendant::node()', root, [e for e in root.iter()])

    def test_descendant_or_self_axis(self):
        root = self.etree.XML('<A><B1><C/></B1><B2/><B3><C/><C1/></B3></A>')
        self.check_select('//.', root, [e for e in root.iter()])
        self.check_select('/A//.', root, [e for e in root.iter()])
        self.check_select('//C1', root, [root[2][1]])
        self.check_select('//B2', root, [root[1]])
        self.check_select('//C', root, [root[0][0], root[2][0]])
        self.check_select('//*', root, [e for e in root.iter()])
        self.check_select('descendant-or-self::node()', root, [e for e in root.iter()])
        self.check_select('descendant-or-self::node()/.', root, [e for e in root.iter()])

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

    def test_attribute_abbreviation_and_axis(self):
        root = self.etree.XML('<A id="1" a="alpha"><B1 b1="beta1"/><B2/><B3 b2="beta2" b3="beta3"/></A>')
        self.check_select('/A/B1/attribute::*', root, ['beta1'])
        self.check_select('/A/B1/@*', root, ['beta1'])
        self.check_select('/A/B3/attribute::*', root, ['beta2', 'beta3'])
        self.check_select('/A/attribute::*', root, {'1', 'alpha'})

    # TODO: Namespace axis

    def test_parent_abbreviation_and_axis(self):
        root = self.etree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2/></B3><B4><C3><D1/></C3></B4></A>')
        self.check_select('/A/*/C2/..', root, [root[2]])
        self.check_select('/A/*/*/..', root, [root[0], root[2], root[3]])
        self.check_select('//C2/..', root, [root[2]])
        self.check_select('/A/*/C2/parent::node()', root, [root[2]])
        self.check_select('/A/*/*/parent::node()', root, [root[0], root[2], root[3]])
        self.check_select('//C2/parent::node()', root, [root[2]])

    def test_ancestor_axes(self):
        root = self.etree.XML('<A><B1><C1/></B1><B2><C1/><D2><E1/><E2/></D2><C2/></B2><B3><C1><D1/></C1></B3></A>')
        self.check_select('/A/B3/C1/ancestor::*', root, [root, root[2]])
        self.check_select('/A/B4/C1/ancestor::*', root, [])
        self.check_select('/A/*/C1/ancestor::*', root, [root, root[0], root[1], root[2]])
        self.check_select('/A/*/C1/ancestor::B3', root, [root[2]])
        self.check_select('/A/B3/C1/ancestor-or-self::*', root, [root, root[2], root[2][0]])
        self.check_select('/A/*/C1/ancestor-or-self::*', root, [
            root, root[0], root[0][0], root[1], root[1][0], root[2], root[2][0]
        ])

    def test_preceding_axes(self):
        root = self.etree.XML('<A><B1><C1/><C2/><C3/></B1><B2><C1/><C2/><C3/><C4/></B2></A>')
        self.check_select('/A/B1/C2/preceding::*', root, [root[0][0]])
        self.check_select('/A/B2/C4/preceding::*', root, [
            root[0], root[0][0], root[0][1], root[0][2], root[1][0], root[1][1], root[1][2]
        ])
        self.check_select('/A/B1/C2/preceding-sibling::*', root, [root[0][0]])
        self.check_select('/A/B2/C4/preceding-sibling::*', root, [root[1][0], root[1][1], root[1][2]])
        self.check_select('/A/B1/C2/preceding-sibling::C3', root, [])

    def test_predicate(self):
        root = self.etree.XML('<A><B1><C1/><C2/><C3/></B1><B2><C1/><C2/><C3/><C4/></B2></A>')
        self.check_select('/A/B1[C2]', root, [root[0]])
        self.check_select('/A/B1[1]', root, [root[0]])
        self.check_select('/A/B1[2]', root, [])
        self.check_select('/A/*[2]', root, [root[1]])
        self.check_select('/A/*[position()<2]', root, [root[0]])
        self.check_select('/A/*[last()-1]', root, [root[0]])
        self.check_select('/A/B2/*[position()>=2]', root, root[1][1:])

    def test_union(self):
        root = self.etree.XML('<A><B1><C1/><C2/><C3/></B1><B2><C1/><C2/><C3/><C4/></B2><B3/></A>')
        self.check_select('/A/B2 | /A/B1', root, root[:2])
        self.check_select('/A/B2 | /A/*', root, root[:])


class XPath2ParserTest(XPath1ParserTest):

    @classmethod
    def setUpClass(cls):
        cls.parser = XPath2Parser()
        cls.etree = ElementTree

    def test_xpath_tokenizer2(self):
        self.check_tokenizer("(: this is a comment :)",
                             ['(:', '', 'this', '', 'is', '', 'a', '', 'comment', '', ':)'])
        self.check_tokenizer("last (:", ['last', '', '(:'])

    def test_token_tree2(self):
        self.check_tree('(1 + 6, 2, 10 - 4)', '(, (, (+ (1) (6)) (2)) (- (10) (4)))')
        self.check_tree('/A/B2 union /A/B1', '(union (/ (/ (A)) (B2)) (/ (/ (A)) (B1)))')

    def test_xpath_comments(self):
        self.wrong_syntax("(: this is a comment :)")
        self.wrong_syntax("(: this is a (: nested :) comment :)")
        self.check_tree('child (: nasty (:nested :) axis comment :) ::B1', '(child (B1))')
        self.check_tree('child (: nasty "(: but not nested :)" axis comment :) ::B1', '(child (B1))')
        self.check_value("5 (: before operator comment :) < 4", False)  # Before infix operator
        self.check_value("5 < (: after operator comment :) 4", False)  # After infix operator
        self.check_value("true (: nasty function comment :) ()", True)
        self.check_tree(' (: initial comment :)/ (:2nd comment:)A/B1(: 3rd comment :)/ \nC1 (: last comment :)\t',
                        '(/ (/ (/ (A)) (B1)) (C1))')

    def test_if_expressions(self):
        self.check_value("if (1) then 2 else 3", 2)

    def test_boolean_functions2(self):
        root = self.etree.XML('<A><B1/><B2/><B3/></A>')
        # self.check_select("boolean((A, 35))", root, True)  # Too much arguments

    def test_numerical_expressions2(self):
        self.check_value("5 idiv 2", 2)
        self.check_value("-3.5 idiv -2", 1)
        self.check_value("-3.5 idiv 2", -1)

    def test_node_set_functions2(self):
        root = self.etree.XML('<A><B1><C1/><C2/></B1><B2/><B3><C3/><C4/><C5/></B3></A>')
        self.check_select("count(5)", root, 1)

    def test_union2(self):
        root = self.etree.XML('<A><B1><C1/><C2/><C3/></B1><B2><C1/><C2/><C3/><C4/></B2><B3/></A>')
        self.check_select('/A/B2 union /A/B1', root, root[:2])
        # self.check_select('/A/B2 union /A/*', root, root[:])

    @unittest.skipIf(xmlschema is None, "Skip if xmlschema library is not available.")
    def test_schema(self):
        pass


class LxmlXPath1ParserTest(XPath1ParserTest):

    @classmethod
    def setUpClass(cls):
        cls.parser = XPath1Parser()
        cls.etree = lxml.etree

    def check_select(self, path, root, expected, namespaces=None, **kwargs):
        if isinstance(expected, type) and issubclass(expected, Exception):
            self.assertRaises(expected, select, root, path, namespaces, self.parser.__class__, **kwargs)
        else:
            results = select(root, path, namespaces, self.parser.__class__, **kwargs)
            if isinstance(expected, set):
                self.assertEqual(set(root.xpath(path, namespaces=namespaces)), expected)
                self.assertEqual(set(results), expected)
            else:
                self.assertEqual(root.xpath(path, namespaces=namespaces), expected)
                self.assertEqual(results, expected)


class LxmlXPath2ParserTest(XPath2ParserTest):

    @classmethod
    def setUpClass(cls):
        cls.parser = XPath2Parser()
        cls.etree = lxml.etree


if __name__ == '__main__':
    unittest.main()
