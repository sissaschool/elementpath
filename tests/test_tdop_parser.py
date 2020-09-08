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
import re
from collections import namedtuple

from elementpath.tdop import symbol_to_identifier, Parser, MultiLabel


FakeToken = namedtuple('Token', 'symbol pattern')


def create_fake_tokens(symbols):
    return {s: FakeToken(s, s) for s in symbols}


class ExpressionParser(Parser):
    SYMBOLS = {'(integer)', '+', '-', '(name)', '(end)'}

    @classmethod
    def create_tokenizer(cls, symbol_table):
        return re.compile(r'(\d+)| ([+\-]) | (\w+) | (\S) | \s+')


ExpressionParser.literal('(integer)')
ExpressionParser.register('(name)')
ExpressionParser.register('(end)')


@ExpressionParser.method(ExpressionParser.infix('+', bp=40))
def evaluate(self, context=None):
    return self[0].evaluate(context) + self[1].evaluate(context)


@ExpressionParser.method(ExpressionParser.infix('-', bp=40))
def evaluate(self, context=None):
    return self[0].evaluate(context) - self[1].evaluate(context)


ExpressionParser.build()


class TdopParserTest(unittest.TestCase):

    def test_multi_label_class(self):
        label = MultiLabel('function', 'constructor function')
        self.assertEqual(label, 'function')
        self.assertEqual(label, 'constructor function')
        self.assertNotEqual(label, 'constructor')
        self.assertNotEqual(label, 'operator')
        self.assertEqual(str(label), 'function__constructor_function')
        self.assertEqual(hash(label), hash(('function', 'constructor function')))

        self.assertIn(label, ['function'])
        self.assertNotIn(label, [])
        self.assertNotIn(label, ['not a function'])
        self.assertNotIn(label, {'function'})  # compares not equality but hash

        self.assertIn('function', label)
        self.assertIn('constructor', label)
        self.assertNotIn('axis', label)

        self.assertTrue(label.startswith('function'))
        self.assertTrue(label.startswith('constructor'))
        self.assertTrue(label.endswith('function'))
        self.assertFalse(label.endswith('constructor'))

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
            ('[^']*'|"[^"]*"|(?:\d+|\.\d+)(?:\.\d*)?(?:[Ee][+-]?\d+)?) |       # Literals
            (call|[+]) |  # Symbols
            ([A-Za-z0-9_]+) |       # Names
            (\S) |       # Unknown symbols
            \s+          # Skip extra spaces
        """)

        with self.assertRaises(ValueError):
            Parser.create_tokenizer(create_fake_tokens(['(name)', 'wrong pattern', '+']))

        # Check fix for issue #10
        pattern = Parser.create_tokenizer(create_fake_tokens(
            ['(name)', 'call', '+', '{http://www.w3.org/2000/09/xmldsig#}CryptoBinary']
        ))
        self.assertTrue(
            pattern.pattern.split('\n')[2].strip().startswith(
                r"({http://www.w3.org/2000/09/xmldsig\#}"
            )
        )

    def test_expression(self):
        parser = ExpressionParser()
        token = parser.parse('10 + 6')
        self.assertEqual(token.evaluate(), 16)


if __name__ == '__main__':
    unittest.main()
