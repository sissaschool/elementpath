#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c), 2018-2019, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import unittest
from collections import namedtuple

from elementpath.tdop_parser import symbol_to_identifier, Parser


FakeToken = namedtuple('Token', 'symbol pattern')


def create_fake_tokens(symbols):
    return {s: FakeToken(s, s) for s in symbols}


class TdopParserTest(unittest.TestCase):

    def test_symbol_to_identifier_function(self):
        self.assertEqual(symbol_to_identifier('_cat10'), '_cat10')
        self.assertEqual(symbol_to_identifier('&'), 'Ampersand')
        self.assertEqual(symbol_to_identifier('('), 'LeftParenthesis')
        self.assertEqual(symbol_to_identifier(')'), 'RightParenthesis')

        self.assertEqual(symbol_to_identifier('(name)'), 'name')
        self.assertEqual(symbol_to_identifier('(name'), 'LeftParenthesis_name')

        self.assertEqual(symbol_to_identifier('-'), 'HyphenMinus')
        self.assertEqual(symbol_to_identifier('_'), 'LowLine')
        self.assertEqual(symbol_to_identifier('-_'), 'HyphenMinus_LowLine')
        self.assertEqual(symbol_to_identifier('--'), 'HyphenMinus_HyphenMinus')

        self.assertEqual(symbol_to_identifier('my-api-call'), 'my_api_call')
        self.assertEqual(symbol_to_identifier('call-'), 'call_')

    def test_create_tokenizer_method(self):
        pattern = Parser.create_tokenizer(create_fake_tokens(['(name)', 'call', '+']))
        self.assertEqual(pattern.pattern, r"""
            ('[^']*' | "[^"]*" | (?:\d+|\.\d+)(?:\.\d*)?(?:[Ee][+-]?\d+)?) |  # Literals (string and numbers)
            (call|[+]) |                                                       # Symbol's patterns
            ([A-Za-z0-9_]+) |                                                            # Names
            (\S) |                                                            # Unexpected characters
            \s+                                                               # Skip extra spaces
        """)

        with self.assertRaises(ValueError):
            Parser.create_tokenizer(create_fake_tokens(['(name)', 'wrong pattern', '+']))

        # Check fix for issue #10
        pattern = Parser.create_tokenizer(create_fake_tokens(
            ['(name)', 'call', '+', '{http://www.w3.org/2000/09/xmldsig#}CryptoBinary']
        ))
        self.assertTrue(
            pattern.pattern.split('\n')[2].strip().startswith(r"({http://www.w3.org/2000/09/xmldsig\#}")
        )


if __name__ == '__main__':
    unittest.main()
