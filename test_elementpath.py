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
from xml.etree import ElementTree
import lxml.etree

from elementpath import *


class TokenizerTest(unittest.TestCase):

    def test_xpath_tokenizer(self):
        def check(path, expected):
            self.assertEqual([
                lit or op or ref for lit, op, ref in XPath1Parser.tokenizer.findall(path)
            ], expected)

        # tests from the XPath specification
        check("*", ['*'])
        check("text()", ['text(', ')'])
        check("@name", ['@', 'name'])
        check("@*", ['@', '*'])
        check("para[1]", ['para', '[', '1', ']'])
        check("para[last()]", ['para', '[', 'last(', ')', ']'])
        check("*/para", ['*', '/', 'para'])
        check("/doc/chapter[5]/section[2]",
              ['/', 'doc', '/', 'chapter', '[', '5', ']',
               '/', 'section', '[', '2', ']'])
        check("chapter//para", ['chapter', '//', 'para'])
        check("//para", ['//', 'para'])
        check("//olist/item", ['//', 'olist', '/', 'item'])
        check(".", ['.'])
        check(".//para", ['.', '//', 'para'])
        check("..", ['..'])
        check("../@lang", ['..', '/', '@', 'lang'])
        check("chapter[title]", ['chapter', '[', 'title', ']'])
        check("employee[@secretary and @assistant]", ['employee',
              '[', '@', 'secretary', '', 'and', '', '@', 'assistant', ']'])

        # additional tests from Python XML etree test cases
        check("{http://spam}egg", ['{http://spam}egg'])
        check("./spam.egg", ['.', '/', 'spam.egg'])
        check(".//{http://spam}egg", ['.', '//', '{http://spam}egg'])

        # additional tests
        check("(: this is a comment :)", ['(:', '', 'this', '', 'is', '', 'a', '', 'comment', '', ':)'])


class XPath1ParserTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.parser = XPath1Parser()

    def test_xpath_comment(self):
        token = self.parser.parse("(: this is a comment :)")
        print(token)
        token = self.parser.parse("(: this is a (: nested :) comment :)")
        print(token)




class ElementTreeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.XML = ElementTree.XML

    def _test_rel_xpath_boolean(self):
        root = self.XML('<A><B><C/></B></A>')
        el = root[0]
        print(list(XPathSelector('boolean(D)').iter_select(el)))
        self.assertTrue(XPathSelector('boolean(C)').iter_select(el))
        self.assertFalse(next(XPathSelector('boolean(D)').iter_select(el)))


class LxmlEtreeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_dir = os.path.dirname(__file__)
        cls.XML = lxml.etree.XML


if __name__ == '__main__':
    unittest.main()
