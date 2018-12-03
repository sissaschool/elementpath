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
import sys
import datetime
import io
import math
import pickle
from decimal import Decimal
from collections import namedtuple
from xml.etree import ElementTree
import lxml.etree

from elementpath import *
from elementpath.namespaces import (
    XML_NAMESPACE, XSD_NAMESPACE, XSI_NAMESPACE, XPATH_FUNCTIONS_NAMESPACE, XML_LANG_QNAME
)
from elementpath.xsd_types import months2days

try:
    # noinspection PyPackageRequirements
    import xmlschema
except (ImportError, AttributeError):
    xmlschema = None


class UntypedAtomicTest(unittest.TestCase):

    def test_eq(self):
        self.assertTrue(UntypedAtomic(-10) == UntypedAtomic(-10))
        self.assertTrue(UntypedAtomic(5.2) == UntypedAtomic(5.2))
        self.assertTrue(UntypedAtomic('-6.09') == UntypedAtomic('-6.09'))
        self.assertTrue(UntypedAtomic(Decimal('8.91')) == UntypedAtomic(Decimal('8.91')))
        self.assertTrue(UntypedAtomic(False) == UntypedAtomic(False))

        self.assertTrue(UntypedAtomic(-10) == -10)
        self.assertTrue(-10 == UntypedAtomic(-10))
        self.assertTrue('-10' == UntypedAtomic(-10))
        self.assertTrue(bool(False) == UntypedAtomic(False))
        self.assertTrue(Decimal('8.91') == UntypedAtomic(Decimal('8.91')))
        self.assertTrue(UntypedAtomic(Decimal('8.91')) == Decimal('8.91'))

        self.assertFalse(bool(False) == UntypedAtomic(10))
        self.assertFalse(-10.9 == UntypedAtomic(-10))
        self.assertFalse(UntypedAtomic(-10) == -11)

        self.assertFalse(UntypedAtomic(-10.5) == UntypedAtomic(-10))
        self.assertFalse(-10.5 == UntypedAtomic(-10))
        self.assertFalse(-17 == UntypedAtomic(-17.3))

    def test_ne(self):
        self.assertTrue(UntypedAtomic(True) != UntypedAtomic(False))
        self.assertTrue(UntypedAtomic(5.12) != UntypedAtomic(5.2))
        self.assertTrue('29' != UntypedAtomic(5.2))
        self.assertFalse('2.0' != UntypedAtomic('2.0'))

    def test_lt(self):
        self.assertTrue(UntypedAtomic(9.0) < UntypedAtomic(15))
        self.assertTrue(False < UntypedAtomic(True))
        self.assertTrue(UntypedAtomic('78') < 100.0)
        self.assertFalse(UntypedAtomic('100.1') < 100.0)

    def test_le(self):
        self.assertTrue(UntypedAtomic(9.0) <= UntypedAtomic(15))
        self.assertTrue(False <= UntypedAtomic(False))
        self.assertTrue(UntypedAtomic('78') <= 100.0)
        self.assertFalse(UntypedAtomic('100.001') <= 100.0)

    def test_gt(self):
        self.assertTrue(UntypedAtomic(25) > UntypedAtomic(15))
        self.assertTrue(25 > UntypedAtomic(15))
        self.assertTrue(UntypedAtomic(25) > 15)
        self.assertTrue(UntypedAtomic(25) > '15')

    def test_ge(self):
        self.assertTrue(UntypedAtomic(25) >= UntypedAtomic(25))
        self.assertFalse(25 >= UntypedAtomic(25.1))

    def test_conversion(self):
        self.assertEqual(str(UntypedAtomic(25.1)), '25.1')
        self.assertEqual(int(UntypedAtomic(25.1)), 25)
        self.assertEqual(float(UntypedAtomic(25.1)), 25.1)
        self.assertEqual(bool(UntypedAtomic(True)), True)
        if sys.version_info >= (3,):
            self.assertEqual(str(UntypedAtomic(u'Joan Miró')), u'Joan Miró')
        else:
            self.assertEqual(unicode(UntypedAtomic(u'Joan Miró')), u'Joan Miró')
        self.assertEqual(bytes(UntypedAtomic(u'Joan Miró')), b'Joan Mir\xc3\xb3')

    def test_numerical_operators(self):
        self.assertEqual(0.25 * UntypedAtomic(1000), 250)
        self.assertEqual(1200 - UntypedAtomic(1000.0), 200.0)
        self.assertEqual(UntypedAtomic(1000.0) - 250, 750.0)
        self.assertEqual(UntypedAtomic('1000.0') - 250, 750.0)
        self.assertEqual(UntypedAtomic('1000.0') - UntypedAtomic(250), 750.0)
        self.assertEqual(UntypedAtomic(0.75) * UntypedAtomic(100), 75)
        self.assertEqual(UntypedAtomic('0.75') * UntypedAtomic('100'), 75)
        self.assertEqual(UntypedAtomic('9.0') / UntypedAtomic('3'), 3.0)
        self.assertEqual(9.0 / UntypedAtomic('3'), 3.0)
        self.assertEqual(UntypedAtomic('15') * UntypedAtomic('4'), 60)


class DurationTypeTest(unittest.TestCase):

    def test_month2day_function(self):
        # xs:duration ordering related tests
        self.assertEqual(months2days(year=1696, month=9, month_delta=0), 0)
        self.assertEqual(months2days(1696, 9, 1), 30)
        self.assertEqual(months2days(1696, 9, 2), 61)
        self.assertEqual(months2days(1696, 9, 3), 91)
        self.assertEqual(months2days(1696, 9, 4), 122)
        self.assertEqual(months2days(1696, 9, 5), 153)
        self.assertEqual(months2days(1696, 9, 12), 365)
        self.assertEqual(months2days(1696, 9, -1), -31)
        self.assertEqual(months2days(1696, 9, -2), -62)
        self.assertEqual(months2days(1696, 9, -12), -366)

        self.assertEqual(months2days(1697, 2, 0), 0)
        self.assertEqual(months2days(1697, 2, 1), 28)
        self.assertEqual(months2days(1697, 2, 12), 365)
        self.assertEqual(months2days(1697, 2, -1), -31)
        self.assertEqual(months2days(1697, 2, -2), -62)
        self.assertEqual(months2days(1697, 2, -3), -92)
        self.assertEqual(months2days(1697, 2, -12), -366)
        self.assertEqual(months2days(1697, 2, -14), -428)
        self.assertEqual(months2days(1697, 2, -15), -458)

        self.assertEqual(months2days(1903, 3, 0), 0)
        self.assertEqual(months2days(1903, 3, 1), 31)
        self.assertEqual(months2days(1903, 3, 2), 61)
        self.assertEqual(months2days(1903, 3, 3), 92)
        self.assertEqual(months2days(1903, 3, 4), 122)
        self.assertEqual(months2days(1903, 3, 11), 366 - 29)
        self.assertEqual(months2days(1903, 3, 12), 366)
        self.assertEqual(months2days(1903, 3, -1), -28)
        self.assertEqual(months2days(1903, 3, -2), -59)
        self.assertEqual(months2days(1903, 3, -3), -90)
        self.assertEqual(months2days(1903, 3, -12), -365)

        self.assertEqual(months2days(1903, 7, 0), 0)
        self.assertEqual(months2days(1903, 7, 1), 31)
        self.assertEqual(months2days(1903, 7, 2), 62)
        self.assertEqual(months2days(1903, 7, 3), 92)
        self.assertEqual(months2days(1903, 7, 6), 184)
        self.assertEqual(months2days(1903, 7, 12), 366)
        self.assertEqual(months2days(1903, 7, -1), -30)
        self.assertEqual(months2days(1903, 7, -2), -61)
        self.assertEqual(months2days(1903, 7, -6), -181)
        self.assertEqual(months2days(1903, 7, -12), -365)

        # Extra tests
        self.assertEqual(months2days(1900, 3, 0), 0)
        self.assertEqual(months2days(1900, 3, 1), 31)
        self.assertEqual(months2days(1900, 3, 24), 730)
        self.assertEqual(months2days(1900, 3, -1), -28)
        self.assertEqual(months2days(1900, 3, -24), -730)

        self.assertEqual(months2days(1000, 4, 0), 0)
        self.assertEqual(months2days(1000, 4, 1), 30)
        self.assertEqual(months2days(1000, 4, 24), 730)
        self.assertEqual(months2days(1000, 4, -1), -31)
        self.assertEqual(months2days(1000, 4, -24), -730)

    def test_init_format(self):
        self.assertIsInstance(Duration('P1Y'), Duration)
        self.assertIsInstance(Duration('P1M'), Duration)
        self.assertIsInstance(Duration('P1D'), Duration)
        self.assertIsInstance(Duration('PT0H'), Duration)
        self.assertIsInstance(Duration('PT1M'), Duration)
        self.assertIsInstance(Duration('PT0.0S'), Duration)

        self.assertRaises(ValueError, Duration, 'P')
        self.assertRaises(ValueError, Duration, 'PT')
        self.assertRaises(ValueError, Duration, '1Y')
        self.assertRaises(ValueError, Duration, 'P1W1DT5H3M23.9S')
        self.assertRaises(ValueError, Duration, 'P1.5Y')
        self.assertRaises(ValueError, Duration, 'PT1.1H')
        self.assertRaises(ValueError, Duration, 'P1.0DT5H3M23.9S')

    def test_as_string(self):
        self.assertEqual(str(Duration('P3Y1D')), 'P3Y1D')
        self.assertEqual(str(Duration('PT2M10.4S')), 'PT2M10.4S')
        self.assertEqual(str(Duration('PT2400H')), 'P100D')
        self.assertEqual(str(Duration('-P15M')), '-P1Y3M')
        self.assertEqual(str(Duration('-P809YT3H5M5S')), '-P809YT3H5M5S')

    def test_eq(self):
        self.assertEqual(Duration('PT147.5S'), (0, 147.5))
        self.assertEqual(Duration('PT147.3S'), (0, Decimal("147.3")))

        self.assertEqual(Duration('PT2M10.4S'), (0, Decimal("130.4")))
        self.assertEqual(Duration('PT5H3M23.9S'), (0, Decimal("18203.9")))
        self.assertEqual(Duration('P1DT5H3M23.9S'), (0, Decimal("104603.9")))
        self.assertEqual(Duration('P31DT5H3M23.9S'), (0, Decimal("2696603.9")))
        self.assertEqual(Duration('P1Y1DT5H3M23.9S'), (12, Decimal("104603.9")))

        self.assertEqual(Duration('-P809YT3H5M5S'), (-9708, -11105))
        self.assertEqual(Duration('P15M'), (15, 0))
        self.assertEqual(Duration('P1Y'), (12, 0))
        self.assertEqual(Duration('P3Y1D'), (36, 3600 * 24))
        self.assertEqual(Duration('PT2400H'), (0, 8640000))
        self.assertEqual(Duration('PT4500M'), (0, 4500 * 60))
        self.assertEqual(Duration('PT4500M70S'), (0, 4500 * 60 + 70))
        self.assertEqual(Duration('PT5529615.3S'), (0, Decimal('5529615.3')))

    def test_ne(self):
        self.assertNotEqual(Duration('PT147.3S'), None)
        self.assertNotEqual(Duration('PT147.3S'), (0, 147.3))
        self.assertNotEqual(Duration('P3Y1D'), (36, 3600 * 2))
        self.assertNotEqual(Duration('P3Y1D'), (36, 3600 * 24, 0))
        self.assertNotEqual(Duration('P3Y1D'), None)

    def test_lt(self):
        self.assertTrue(Duration('P15M') < Duration('P16M'))
        self.assertFalse(Duration('P16M') < Duration('P16M'))
        self.assertTrue(Duration('P16M') < Duration('P16M1D'))
        self.assertTrue(Duration('P16M') < Duration('P16MT1H'))
        self.assertTrue(Duration('P16M') < Duration('P16MT1M'))
        self.assertTrue(Duration('P16M') < Duration('P16MT1S'))
        self.assertFalse(Duration('P16M') < Duration('P16MT0S'))

    def test_le(self):
        self.assertTrue(Duration('P15M') <= Duration('P16M'))
        self.assertTrue(Duration('P16M') <= Duration('P16M'))
        self.assertTrue(Duration('P16M') <= Duration('P16M1D'))
        self.assertTrue(Duration('P16M') <= Duration('P16MT1H'))
        self.assertTrue(Duration('P16M') <= Duration('P16MT1M'))
        self.assertTrue(Duration('P16M') <= Duration('P16MT1S'))
        self.assertTrue(Duration('P16M') <= Duration('P16MT0S'))

    def test_gt(self):
        self.assertTrue(Duration('P16M') > Duration('P15M'))
        self.assertFalse(Duration('P16M') > Duration('P16M'))

    def test_ge(self):
        self.assertTrue(Duration('P16M') >= Duration('P15M'))
        self.assertTrue(Duration('P16M') >= Duration('P16M'))
        self.assertTrue(Duration('P1Y1DT1S') >= Duration('P1Y1D'))

    def test_incomparable_values(self):
        self.assertFalse(Duration('P1M') < Duration('P30D'))
        self.assertFalse(Duration('P1M') <= Duration('P30D'))
        self.assertFalse(Duration('P1M') > Duration('P30D'))
        self.assertFalse(Duration('P1M') >= Duration('P30D'))


class TimezoneTypeTest(unittest.TestCase):

    def test_init_format(self):
        self.assertEqual(Timezone('Z').offset, datetime.timedelta(0))
        self.assertEqual(Timezone('00:00').offset, datetime.timedelta(0))
        self.assertEqual(Timezone('+00:00').offset, datetime.timedelta(0))
        self.assertEqual(Timezone('-00:00').offset, datetime.timedelta(0))
        self.assertEqual(Timezone('-0:0').offset, datetime.timedelta(0))
        self.assertEqual(Timezone('+05:15').offset, datetime.timedelta(hours=5, minutes=15))
        self.assertEqual(Timezone('-11:00').offset, datetime.timedelta(hours=-11))
        self.assertEqual(Timezone('+13:59').offset, datetime.timedelta(hours=13, minutes=59))
        self.assertEqual(Timezone('-13:59').offset, datetime.timedelta(hours=-13, minutes=-59))
        self.assertEqual(Timezone('+14:00').offset, datetime.timedelta(hours=14))
        self.assertEqual(Timezone('-14:00').offset, datetime.timedelta(hours=-14))

        self.assertRaises(ValueError, Timezone, '-15:00')
        self.assertRaises(ValueError, Timezone, '-14:01')
        self.assertRaises(ValueError, Timezone, '+14:01')
        self.assertRaises(ValueError, Timezone, '+10')
        self.assertRaises(ValueError, Timezone, '+10:00:00')

    def test_init_timedelta(self):
        td0 = datetime.timedelta(0)
        td1 = datetime.timedelta(hours=5, minutes=15)
        td2 = datetime.timedelta(hours=-14, minutes=0)
        td3 = datetime.timedelta(hours=-14, minutes=-1)

        self.assertEqual(Timezone(td0).offset, td0)
        self.assertEqual(Timezone(td1).offset, td1)
        self.assertEqual(Timezone(td2).offset, td2)
        self.assertRaises(ValueError, Timezone, td3)
        self.assertRaises(TypeError, Timezone, 0)

    def test_as_string(self):
        self.assertEqual(str(Timezone('+05:00')), 'UTC+05:00')
        self.assertEqual(str(Timezone('-13:15')), 'UTC-13:15')


class XPathTokenTest(unittest.TestCase):

    token = XPath1Parser.symbol_table['(name)'](XPath1Parser(), 'dummy_token')

    def test_integer_decoder(self):
        self.assertRaises(ElementPathValueError, self.token.integer, "alpha")
        self.assertRaises(ElementPathTypeError, self.token.integer, [])
        self.assertEqual(self.token.integer("89"), 89)
        self.assertEqual(self.token.integer("89.1"), 89)
        self.assertEqual(self.token.integer(-71), -71)
        self.assertEqual(self.token.integer(19.5), 19)

    def test_datetime_decoder(self):
        self.assertRaises(
            ElementPathValueError, self.token.datetime, '2001-01-01', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f'
        )
        self.assertEqual(
            self.token.datetime('2001-01-01T23:29:45', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f'),
            datetime.datetime(2001, 1, 1, 23, 29, 45)
        )


class XPath1ParserTest(unittest.TestCase):
    namespaces = {
        'xml': XML_NAMESPACE,
        'xs': XSD_NAMESPACE,
        'xsi': XSI_NAMESPACE,
        'fn': XPATH_FUNCTIONS_NAMESPACE,
        'eg': 'http://www.example.com/example',
    }
    variables = {'values': [10, 20, 5]}
    etree = ElementTree

    def setUp(self):
        self.parser = XPath1Parser(namespaces=self.namespaces, variables=self.variables, strict=True)
        self.token = XPath1Parser.symbol_table['(name)'](self.parser, 'test')

    #
    # Helper methods
    def check_tokenizer(self, path, expected):
        """
        Checks the list of lexemes generated by the parser tokenizer.

        :param path: the XPath expression to be checked.
        :param expected: a list with lexemes generated by the tokenizer.
        """
        self.assertEqual([
            lit or op or ref or unexpected
            for lit, op, ref, unexpected in self.parser.__class__.tokenizer.findall(path)
        ], expected)

    def check_token(self, symbol, expected_label=None, expected_str=None, expected_repr=None, value=None):
        """
        Checks a token class of an XPath parser class. The instance of the token is created
        using the value argument and than is checked against other optional arguments.

        :param symbol: the string that identifies the token class in the parser's symbol table.
        :param expected_label: the expected label for the token instance.
        :param expected_str: the expected string conversion of the token instance.
        :param expected_repr: the expected string representation of the token instance.
        :param value: the value used to create the token instance.
        """
        token = self.parser.symbol_table[symbol](self.parser, value)
        self.assertEqual(token.symbol, symbol)
        if expected_label is not None:
            self.assertEqual(token.label, expected_label)
        if expected_str is not None:
            self.assertEqual(str(token), expected_str)
        if expected_repr is not None:
            self.assertEqual(repr(token), expected_repr)

    def check_tree(self, path, expected):
        """
        Checks the tree string representation of a parsed path.

        :param path: an XPath expression.
        :param expected: the expected result string.
        """
        self.assertEqual(self.parser.parse(path).tree, expected)

    def check_source(self, path, expected):
        """
        Checks the source representation of a parsed path.

        :param path: an XPath expression.
        :param expected: the expected result string.
        """
        self.assertEqual(self.parser.parse(path).source, expected)

    def check_value(self, path, expected=None, context=None):
        """
        Checks the result of the *evaluate* method with an XPath expression. The evaluation
        is applied on the root token of the parsed XPath expression.

        :param path: an XPath expression.
        :param expected: the expected result. Can be a data instance to compare to the result, a type \
        to be used to check the type of the result, a function that accepts the result as argument and \
        returns a boolean value, an exception class that is raised by running the evaluate method.
        :param context: an optional `XPathContext` instance to be passed to evaluate method.
        """
        if context is not None:
            context = context.copy()
        root_token = self.parser.parse(path)
        if isinstance(expected, type) and issubclass(expected, Exception):
            self.assertRaises(expected, root_token.evaluate, context)
        elif not callable(expected):
            self.assertEqual(root_token.evaluate(context), expected)
        elif isinstance(expected, type):
            value = root_token.evaluate(context)
            self.assertTrue(isinstance(value, expected), "%r is not a %r instance." % (value, expected))
        else:
            self.assertTrue(expected(root_token.evaluate(context)))

    def check_select(self, path, expected, context=None):
        """
        Checks the materialized result of the *select* method with an XPath expression.
        The selection is applied on the root token of the parsed XPath expression.

        :param path: an XPath expression.
        :param expected: the expected result. Can be a data instance to compare to the result, \
        a function that accepts the result as argument and returns a boolean value, an exception \
        class that is raised by running the evaluate method.
        :param context: an optional `XPathContext` instance to be passed to evaluate method. If no \
        context is provided the method is called with a dummy context.
        """
        if context is None:
            context = XPathContext(root=self.etree.Element(u'dummy_root'))
        else:
            context = context.copy()
        root_token = self.parser.parse(path)
        if isinstance(expected, type) and issubclass(expected, Exception):
            self.assertRaises(expected, root_token.select, context)
        elif not callable(expected):
            self.assertEqual(list(root_token.select(context)), expected)
        else:
            self.assertTrue(expected(list(root_token.parse(path).select(context))))

    def check_selector(self, path, root, expected, namespaces=None, **kwargs):
        """
        Checks the selector API, namely the *select* function at package level.

        :param path: an XPath expression.
        :param root: an Element or an ElementTree instance.
        :param expected: the expected result. Can be a data instance to compare to the result, a type \
        to be used to check the type of the result, a function that accepts the result as argument and \
        returns a boolean value, an exception class that is raised by running the evaluate method.
        :param namespaces: an optional mapping from prefixes to namespace URIs.
        :param kwargs: other optional arguments for the parser class.
        """
        if isinstance(expected, type) and issubclass(expected, Exception):
            self.assertRaises(expected, select, root, path, namespaces, self.parser.__class__, **kwargs)
        else:
            results = select(root, path, namespaces, self.parser.__class__, **kwargs)
            if isinstance(expected, set):
                self.assertEqual(set(results), expected)
            elif not callable(expected):
                self.assertEqual(results, expected)
            elif isinstance(expected, type):
                self.assertTrue(isinstance(results, expected))
            else:
                self.assertTrue(expected(results))

    # Wrong XPath expression checker shortcuts
    def wrong_syntax(self, path):
        self.assertRaises(ElementPathSyntaxError, self.parser.parse, path)

    def wrong_value(self, path):
        self.assertRaises(ElementPathValueError, self.parser.parse, path)

    def wrong_type(self, path):
        self.assertRaises(ElementPathTypeError, self.parser.parse, path)

    def wrong_name(self, path):
        self.assertRaises(ElementPathNameError, self.parser.parse, path)

    #
    # Test methods
    @unittest.skipIf(sys.version_info < (3,), "Python 2 pickling is not supported.")
    def test_parser_pickling(self):
        if getattr(self.parser, 'schema', None) is None:
            obj = pickle.dumps(self.parser)
            parser = pickle.loads(obj)
            obj = pickle.dumps(self.parser.symbol_table)
            symbol_table = pickle.loads(obj)
            self.assertEqual(self.parser, parser)
            self.assertEqual(self.parser.symbol_table, symbol_table)

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
                         "_string_literal_token(value='hello')", 'hello')
        self.check_token('(integer)', 'literal', "1999 integer",
                         "_integer_literal_token(value=1999)", 1999)
        self.check_token('(float)', 'literal', "3.1415 float",
                         "_float_literal_token(value=3.1415)", 3.1415)
        self.check_token('(decimal)', 'literal', "217.35 decimal",
                         "_decimal_literal_token(value=217.35)", 217.35)
        self.check_token('(name)', 'literal', "'schema' name",
                         "_name_literal_token(value='schema')", 'schema')

        # Axes
        self.check_token('self', 'axis', "'self' axis", "_self_axis_token()")
        self.check_token('child', 'axis', "'child' axis", "_child_axis_token()")
        self.check_token('parent', 'axis', "'parent' axis", "_parent_axis_token()")
        self.check_token('ancestor', 'axis', "'ancestor' axis", "_ancestor_axis_token()")
        self.check_token('preceding', 'axis', "'preceding' axis", "_preceding_axis_token()")
        self.check_token('descendant-or-self', 'axis', "'descendant-or-self' axis")
        self.check_token('following-sibling', 'axis', "'following-sibling' axis")
        self.check_token('preceding-sibling', 'axis', "'preceding-sibling' axis")
        self.check_token('ancestor-or-self', 'axis', "'ancestor-or-self' axis")
        self.check_token('descendant', 'axis', "'descendant' axis")
        if self.parser.version == '1.0':
            self.check_token('attribute', 'axis', "'attribute' axis")
        self.check_token('following', 'axis', "'following' axis")
        self.check_token('namespace', 'axis', "'namespace' axis")

        # Functions
        self.check_token('position', 'function', "'position' function", "_position_function_token()")

        # Operators
        self.check_token('and', 'operator', "'and' operator", "_and_operator_token()")

    def test_implementation(self):
        self.assertEqual(self.parser.unregistered(), [])

    def test_token_tree(self):
        self.check_tree('child::B1', '(child (B1))')
        self.check_tree('A/B//C/D', '(/ (// (/ (A) (B)) (C)) (D))')
        self.check_tree('child::*/child::B1', '(/ (child (*)) (child (B1)))')
        self.check_tree('attribute::name="Galileo"', "(= (attribute (name)) ('Galileo'))")
        self.check_tree('1 + 2 * 3', '(+ (1) (* (2) (3)))')
        self.check_tree('(1 + 2) * 3', '(* (+ (1) (2)) (3))')
        self.check_tree("false() and true()", '(and (false) (true))')
        self.check_tree("false() or true()", '(or (false) (true))')
        self.check_tree("./A/B[C][D]/E", '(/ ([ ([ (/ (/ (.) (A)) (B)) (C)) (D)) (E))')
        self.check_tree("string(xml:lang)", '(string (: (xml) (lang)))')

    def test_token_source(self):
        self.check_source(' child ::B1', 'child::B1')
        self.check_source('false()', 'false()')
        self.check_source("concat('alpha', 'beta', 'gamma')", "concat('alpha', 'beta', 'gamma')")
        self.check_source('1 +2 *  3 ', '1 + 2 * 3')
        self.check_source('(1 + 2) * 3', '(1 + 2) * 3')
        self.check_source(' xs : string ', 'xs:string')
        self.check_source('attribute::name="Galileo"', "attribute::name = 'Galileo'")

    def test_wrong_syntax(self):
        self.wrong_syntax('')
        self.wrong_syntax("     \n     \n   )")
        self.wrong_syntax('child::1')
        self.wrong_syntax("count(0, 1, 2)")
        self.wrong_syntax("{}egg")
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

        # Prefix references
        self.check_tree('xs:string', '(: (xs) (string))')
        self.check_tree('string(xs:unknown)', '(string (: (xs) (unknown)))')

        self.check_value("fn:true()", True)
        self.check_selector("./tst:B1", root, [root[0]], namespaces=namespaces)
        self.check_selector("./tst:*", root, root[:], namespaces=namespaces)

        # Namespace wildcard works only for XPath > 1.0
        if self.parser.version == '1.0':
            self.check_selector("./*:B2", root, Exception, namespaces=namespaces)
        else:
            self.check_selector("./*:B2", root, [root[1]], namespaces=namespaces)

        # QName URI references
        self.parser.strict = False
        self.check_tree('{%s}string' % XSD_NAMESPACE, "({ ('http://www.w3.org/2001/XMLSchema') (string))")
        self.check_tree('string({%s}unknown)' % XSD_NAMESPACE,
                        "(string ({ ('http://www.w3.org/2001/XMLSchema') (unknown)))")
        self.wrong_syntax("{%s" % XSD_NAMESPACE)

        self.check_value("{%s}true()" % XPATH_FUNCTIONS_NAMESPACE, True)
        self.parser.strict = True
        self.wrong_syntax('{%s}string' % XSD_NAMESPACE)

        if not hasattr(self.etree, 'LxmlError') or self.parser.version > '1.0':
            # Do not test with XPath 1.0 on lxml.
            self.check_selector("./{http://www.w3.org/2001/04/xmlenc#}EncryptedData", root, [], strict=False)
            self.check_selector("./{http://xpath.test/ns}B1", root, [root[0]], strict=False)
            self.check_selector("./{http://xpath.test/ns}*", root, root[:], strict=False)

    def test_node_types(self):
        document = self.etree.parse(io.StringIO(u'<A/>'))
        element = self.etree.Element('schema')
        attribute = 'id', '0212349350'
        namespace = namedtuple('Namespace', 'prefix uri')('xs', 'http://www.w3.org/2001/XMLSchema')
        comment = self.etree.Comment('nothing important')
        pi = self.etree.ProcessingInstruction('action', 'nothing to do')
        text = u'aldebaran'
        context = XPathContext(element)
        self.check_select("node()", [document.getroot()], context=XPathContext(document))
        self.check_selector("node()", element, [])
        context.item = attribute
        self.check_select("self::node()", [attribute], context)
        context.item = namespace
        self.check_select("self::node()", [namespace], context)
        context.item = comment
        self.check_select("self::node()", [comment], context)
        self.check_select("self::comment()", [comment], context)
        context.item = pi
        self.check_select("self::node()", [pi], context)
        self.check_select("self::processing-instruction()", [pi], context)
        context.item = text
        self.check_select("self::node()", [text], context)
        self.check_select("text()", [], context)  # Selects the children
        self.check_selector("node()", self.etree.XML('<author>Dickens</author>'), ['Dickens'])
        self.check_selector("text()", self.etree.XML('<author>Dickens</author>'), ['Dickens'])
        self.check_selector("//self::text()", self.etree.XML('<author>Dickens</author>'), ['Dickens'])

    def test_node_set_id_function(self):
        # XPath 1.0 id() function: https://www.w3.org/TR/1999/REC-xpath-19991116/#function-id
        root = self.etree.XML('<A><B1 xml:id="foo"/><B2/><B3 xml:id="bar"/><B4 xml:id="baz"/></A>')
        self.check_selector('id("foo")', root, [root[0]])

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

        self.check_selector("name(.)", root, 'A')
        self.check_selector("name(A)", root, '')
        self.check_selector("local-name(A)", root, '')
        self.check_selector("namespace-uri(A)", root, '')
        self.check_selector("name(B2)", root, 'B2')
        self.check_selector("local-name(B2)", root, 'B2')
        self.check_selector("namespace-uri(B2)", root, '')
        if self.parser.version <= '1.0':
            self.check_selector("name(*)", root, 'B1')

        root = self.etree.XML('<tst:A xmlns:tst="http://xpath.test/ns"><tst:B1/></tst:A>')
        self.check_selector("name(.)", root, 'tst:A', namespaces={'tst': "http://xpath.test/ns"})
        self.check_selector("local-name(.)", root, 'A')
        self.check_selector("namespace-uri(.)", root, 'http://xpath.test/ns')
        self.check_selector("name(tst:B1)", root, 'tst:B1', namespaces={'tst': "http://xpath.test/ns"})
        self.check_selector("name(tst:B1)", root, 'tst:B1', namespaces={'tst': "http://xpath.test/ns", '': ''})

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
        self.check_value("string-length('')", 0)
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

        root = self.etree.XML('<ups-units>'
                              '  <unit><power>40kW</power></unit>'
                              '  <unit><power>20kW</power></unit>'
                              '  <unit><power>30kW</power><model>XYZ</model></unit>'
                              '</ups-units>')
        variables = {'ups1': root[0], 'ups2': root[1], 'ups3': root[2]}
        self.check_selector('string($ups1/power)', root, '40kW', variables=variables)

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

        # From https://www.w3.org/TR/1999/REC-xpath-19991116/#section-Boolean-Functions
        self.check_selector('lang("en")', self.etree.XML('<para xml:lang="en"/>'), True)
        self.check_selector('lang("en")', self.etree.XML('<div xml:lang="en"><para/></div>'), True)
        self.check_selector('lang("en")', self.etree.XML('<para xml:lang="EN"/>'), True)
        self.check_selector('lang("en")', self.etree.XML('<para xml:lang="en-us"/>'), True)
        self.check_selector('lang("en")', self.etree.XML('<para xml:lang="it"/>'), False)

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

    def test_comparison_operators(self):
        self.check_value("0.05 = 0.05", True)
        self.check_value("19.03 != 19.02999", True)
        self.check_value("-1.0 = 1.0", False)
        self.check_value("1 <= 2", True)
        self.check_value("5 >= 9", False)
        self.check_value("5 > 3", True)
        self.check_value("5 < 20.0", True)
        self.check_value("false() = 1", False)
        self.check_value("0 = false()", True)
        self.check_value("2 * 2 = 4", True)

        root = self.etree.XML('<table>'
                              '    <unit id="1"><cost>50</cost></unit>'
                              '    <unit id="2"><cost>30</cost></unit>'
                              '    <unit id="3"><cost>20</cost></unit>'
                              '    <unit id="2"><cost>40</cost></unit>'
                              '</table>')
        self.check_selector("/table/unit[2]/cost <= /table/unit[1]/cost", root, True)
        self.check_selector("/table/unit[2]/cost > /table/unit[position()!=2]/cost", root, True)
        self.check_selector("/table/unit[3]/cost > /table/unit[position()!=3]/cost", root, False)

        self.check_selector(". = 'Dickens'", self.etree.XML('<author>Dickens</author>'), True)

    def test_numerical_expressions(self):
        self.check_value("9", 9)
        self.check_value("-3", -3)
        self.check_value("7.1", Decimal('7.1'))
        self.check_value("0.45e3", 0.45e3)
        self.check_value(" 7+5 ", 12)
        self.check_value("8 - 5", 3)
        self.check_value("-8 - 5", -13)
        self.check_value("5 div 2", 2.5)
        self.check_value("11 mod 3", 2)
        self.check_value("4.5 mod 1.2", Decimal('0.9'))
        self.check_value("1.23E2 mod 0.6E1", 3.0E0)
        self.check_value("-3 * 7", -21)
        self.check_value("9 - 1 + 6", 14)
        self.check_value("(5 * 7) + 9", 44)
        self.check_value("-3 * 7", -21)

    def test_number_functions(self):
        root = self.etree.XML('<A><B1><C/></B1><B2/><B3><C1/><C2/></B3></A>')

        self.check_value("number(5.0)", 5.0)
        self.check_value("number('text')", math.isnan)
        self.check_value("number('-11')", -11)
        self.check_selector("number(9)", root, 9.0)
        self.check_value("sum($values)", 35)

        # Test cases taken from https://www.w3.org/TR/xquery-operators/#numeric-value-functions
        self.check_value("ceiling(10.5)", 11)
        self.check_value("ceiling(-10.5)", -10)
        self.check_value("floor(10.5)", 10)
        self.check_value("floor(-10.5)", -11)
        self.check_value("round(2.5)", 3)
        self.check_value("round(2.4999)", 2)
        self.check_value("round(-2.5)", -2)

    def test_context_variables(self):
        root = self.etree.XML('<A><B1><C/></B1><B2/><B3><C1/><C2/></B3></A>')
        context = XPathContext(root, variables={'alpha': 10, 'id': '19273222'})
        self.check_value("$alpha", None)  # Do not raise if the dynamic context is None
        self.check_value("$alpha", 10, context=context)
        self.check_value("$beta", ElementPathNameError, context=context)
        self.check_value("$id", '19273222', context=context)
        self.wrong_syntax("$id()")

    def test_child_operator(self):
        root = self.etree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2/></B3></A>')
        self.check_selector('/', root, [])
        self.check_selector('/B1', root, [])
        self.check_selector('/A1', root, [])
        self.check_selector('/A', root, [root])
        self.check_selector('/A/B1', root, [root[0]])
        self.check_selector('/A/*', root, [root[0], root[1], root[2]])
        self.check_selector('/*/*', root, [root[0], root[1], root[2]])
        self.check_selector('/A/B1/C1', root, [root[0][0]])
        self.check_selector('/A/B1/*', root, [root[0][0]])
        self.check_selector('/A/B3/*', root, [root[2][0], root[2][1]])
        self.check_selector('child::*/child::C1', root, [root[0][0], root[2][0]])
        self.check_selector('/A/child::B3', root, [root[2]])
        self.check_selector('/A/child::C1', root, [])

    def test_context_item_expression(self):
        root = self.etree.XML('<A><B1><C/></B1><B2/><B3><C1/><C2/></B3></A>')
        self.check_selector('.', root, [root])
        self.check_selector('/././.', root, [])
        self.check_selector('/A/.', root, [root])
        self.check_selector('/A/B1/.', root, [root[0]])
        self.check_selector('/A/B1/././.', root, [root[0]])
        self.check_selector('1/.', root, ElementPathTypeError)

    def test_self_axis(self):
        root = self.etree.XML('<A>A text<B1>B1 text</B1><B2/><B3>B3 text</B3></A>')
        self.check_selector('self::node()', root, [root])
        self.check_selector('self::text()', root, [])

    def test_child_axis(self):
        root = self.etree.XML('<A>A text<B1>B1 text</B1><B2/><B3>B3 text</B3></A>')
        self.check_selector('child::B1', root, [root[0]])
        self.check_selector('child::A', root, [])
        self.check_selector('child::text()', root, ['A text'])
        self.check_selector('child::node()', root, ['A text'] + root[:])
        self.check_selector('child::*', root, root[:])

    def test_descendant_axis(self):
        root = self.etree.XML('<A><B1><C/></B1><B2/><B3><C1/><C2/></B3></A>')
        self.check_selector('descendant::node()', root, [e for e in root.iter()][1:])
        self.check_selector('/descendant::node()', root, [e for e in root.iter()])

    def test_descendant_or_self_axis(self):
        root = self.etree.XML('<A><B1><C/></B1><B2/><B3><C/><C1/></B3></A>')
        self.check_selector('//.', root, [e for e in root.iter()])
        self.check_selector('/A//.', root, [e for e in root.iter()])
        self.check_selector('//C1', root, [root[2][1]])
        self.check_selector('//B2', root, [root[1]])
        self.check_selector('//C', root, [root[0][0], root[2][0]])
        self.check_selector('//*', root, [e for e in root.iter()])
        self.check_selector('descendant-or-self::node()', root, [e for e in root.iter()])
        self.check_selector('descendant-or-self::node()/.', root, [e for e in root.iter()])

    def test_following_axis(self):
        root = self.etree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2/></B3><B4><C1><D1/></C1></B4></A>')
        self.check_selector('/A/B1/C1/following::*', root, [
            root[1], root[2], root[2][0], root[2][1], root[3], root[3][0], root[3][0][0]
        ])
        self.check_selector('/A/B1/following::C1', root, [root[2][0], root[3][0]])

    def test_following_sibling_axis(self):
        root = self.etree.XML('<A><B1><C1/><C2/><C3/></B1><B2><C1/><C2/><C3/><C4/></B2></A>')
        self.check_selector('/A/B1/C1/following-sibling::*', root, [root[0][1], root[0][2]])
        self.check_selector('/A/B2/C1/following-sibling::*', root, [root[1][1], root[1][2], root[1][3]])
        self.check_selector('/A/B1/C1/following-sibling::C3', root, [root[0][2]])

    def test_attribute_abbreviation_and_axis(self):
        root = self.etree.XML('<A id="1" a="alpha"><B1 b1="beta1"/><B2/><B3 b2="beta2" b3="beta3"/></A>')
        self.check_selector('/A/B1/attribute::*', root, ['beta1'])
        self.check_selector('/A/B1/@*', root, ['beta1'])
        self.check_selector('/A/B3/attribute::*', root, {'beta2', 'beta3'})
        self.check_selector('/A/attribute::*', root, {'1', 'alpha'})

    def test_namespace_axis(self):
        root = self.etree.XML('<A xmlns:tst="http://xpath.test/ns"><tst:B1/></A>')
        namespaces = list(self.parser.DEFAULT_NAMESPACES.items()) + [('tst', 'http://xpath.test/ns')]
        self.check_selector('/A/namespace::*', root, expected=set(namespaces), namespaces=namespaces[-1:])

    def test_parent_abbreviation_and_axis(self):
        root = self.etree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2/></B3><B4><C3><D1/></C3></B4></A>')
        self.check_selector('/A/*/C2/..', root, [root[2]])
        self.check_selector('/A/*/*/..', root, [root[0], root[2], root[3]])
        self.check_selector('//C2/..', root, [root[2]])
        self.check_selector('/A/*/C2/parent::node()', root, [root[2]])
        self.check_selector('/A/*/*/parent::node()', root, [root[0], root[2], root[3]])
        self.check_selector('//C2/parent::node()', root, [root[2]])

    def test_ancestor_axes(self):
        root = self.etree.XML('<A><B1><C1/></B1><B2><C1/><D2><E1/><E2/></D2><C2/></B2><B3><C1><D1/></C1></B3></A>')
        self.check_selector('/A/B3/C1/ancestor::*', root, [root, root[2]])
        self.check_selector('/A/B4/C1/ancestor::*', root, [])
        self.check_selector('/A/*/C1/ancestor::*', root, [root, root[0], root[1], root[2]])
        self.check_selector('/A/*/C1/ancestor::B3', root, [root[2]])
        self.check_selector('/A/B3/C1/ancestor-or-self::*', root, [root, root[2], root[2][0]])
        self.check_selector('/A/*/C1/ancestor-or-self::*', root, [
            root, root[0], root[0][0], root[1], root[1][0], root[2], root[2][0]
        ])

    def test_preceding_axes(self):
        root = self.etree.XML('<A><B1><C1/><C2/><C3/></B1><B2><C1/><C2/><C3/><C4/></B2></A>')
        self.check_selector('/A/B1/C2/preceding::*', root, [root[0][0]])
        self.check_selector('/A/B2/C4/preceding::*', root, [
            root[0], root[0][0], root[0][1], root[0][2], root[1][0], root[1][1], root[1][2]
        ])
        self.check_selector('/A/B1/C2/preceding-sibling::*', root, [root[0][0]])
        self.check_selector('/A/B2/C4/preceding-sibling::*', root, [root[1][0], root[1][1], root[1][2]])
        self.check_selector('/A/B1/C2/preceding-sibling::C3', root, [])

    def test_default_axis(self):
        """Tests about when child:: default axis is applied."""
        root = self.etree.XML('<root><a id="1">first<b/></a><a id="2">second</a></root>')
        self.check_selector('/root/a/*', root, [root[0][0]])
        self.check_selector('/root/a/node()', root, ['first', root[0][0], 'second'])
        self.check_selector('/root/a/text()', root, ['first', 'second'])
        self.check_selector('/root/a/attribute::*', root, ['1', '2'])
        if self.parser.version > '1.0':
            # Functions are not allowed after path step in XPath 1.0
            self.check_selector('/root/a/attribute()', root, ['1', '2'])
            self.check_selector('/root/a/element()', root, [root[0][0]])
            self.check_selector('/root/a/name()', root, ['a', 'a'])
            self.check_selector('/root/a/last()', root, [2, 2])
            self.check_selector('/root/a/position()', root, [1, 2])

    def test_predicate(self):
        root = self.etree.XML('<A><B1><C1/><C2/><C3/></B1><B2><C1/><C2/><C3/><C4/></B2></A>')
        self.check_selector('/A/B1[C2]', root, [root[0]])
        self.check_selector('/A/B1[1]', root, [root[0]])
        self.check_selector('/A/B1[2]', root, [])
        self.check_selector('/A/*[2]', root, [root[1]])
        self.check_selector('/A/*[position()<2]', root, [root[0]])
        self.check_selector('/A/*[last()-1]', root, [root[0]])
        self.check_selector('/A/B2/*[position()>=2]', root, root[1][1:])

        root = self.etree.XML("<bib><book><author>Asimov</author></book></bib>")
        self.check_selector("book/author[. = 'Asimov']", root, [root[0][0]])
        self.check_selector("book/author[. = 'Dickens']", root, [])
        self.check_selector("book/author[text()='Asimov']", root, [root[0][0]])

        root = self.etree.XML('<A><B1>hello</B1><B2/><B3>  </B3></A>')
        self.check_selector("/A/*[' ']", root, root[:])
        self.check_selector("/A/*['']", root, [])

    def test_union(self):
        root = self.etree.XML('<A><B1><C1/><C2/><C3/></B1><B2><C1/><C2/><C3/><C4/></B2><B3/></A>')
        self.check_selector('/A/B2 | /A/B1', root, root[:2])
        self.check_selector('/A/B2 | /A/*', root, root[:])

    def test_default_namespace(self):
        root = self.etree.XML('<foo>bar</foo>')
        self.check_selector('/foo', root, [root])
        if type(self.parser) is XPath1Parser:
            # XPath 1.0 ignores the default namespace
            self.check_selector('/foo', root, [root], namespaces={'': 'ns'})  # foo --> foo
        else:
            self.check_selector('/foo', root, [], namespaces={'': 'ns'})  # foo --> {ns}foo
            self.check_selector('/*:foo', root, [root], namespaces={'': 'ns'})  # foo --> {ns}foo

        root = self.etree.XML('<foo xmlns="ns">bar</foo>')
        self.check_selector('/foo', root, [])
        if type(self.parser) is XPath1Parser:
            self.check_selector('/foo', root, [], namespaces={'': 'ns'})
        else:
            self.check_selector('/foo', root, [root], namespaces={'': 'ns'})


class LxmlXPath1ParserTest(XPath1ParserTest):
    etree = lxml.etree

    def check_selector(self, path, root, expected, namespaces=None, **kwargs):
        """Check using the selector API (the *select* function of the package)."""
        if isinstance(expected, type) and issubclass(expected, Exception):
            self.assertRaises(expected, select, root, path, namespaces, self.parser.__class__, **kwargs)
        else:
            results = select(root, path, namespaces, self.parser.__class__, **kwargs)
            variables = kwargs.get('variables', {})
            if isinstance(expected, set):
                if namespaces and '' not in namespaces:
                    self.assertEqual(set(root.xpath(path, namespaces=namespaces, **variables)), expected)
                self.assertEqual(set(results), expected)
            elif not callable(expected):
                if namespaces and '' not in namespaces:
                    self.assertEqual(root.xpath(path, namespaces=namespaces, **variables), expected)
                self.assertEqual(results, expected)
            elif isinstance(expected, type):
                self.assertTrue(isinstance(results, expected))
            else:
                self.assertTrue(expected(results))


class XPath2ParserTest(XPath1ParserTest):

    def setUp(self):
        self.parser = XPath2Parser(namespaces=self.namespaces, variables=self.variables)

    def test_xpath_tokenizer2(self):
        self.check_tokenizer("(: this is a comment :)",
                             ['(:', '', 'this', '', 'is', '', 'a', '', 'comment', '', ':)'])
        self.check_tokenizer("last (:", ['last', '', '(:'])

    def test_token_tree2(self):
        self.check_tree('(1 + 6, 2, 10 - 4)', '(, (, (+ (1) (6)) (2)) (- (10) (4)))')
        self.check_tree('/A/B2 union /A/B1', '(union (/ (/ (A)) (B2)) (/ (/ (A)) (B1)))')

    def test_token_source2(self):
        self.check_source("(5, 6) instance of xs:integer+", '(5, 6) instance of xs:integer+')
        self.check_source("$myaddress treat as element(*, USAddress)", "$myaddress treat as element(*, USAddress)")

    def test_xpath_comments(self):
        self.wrong_syntax("(: this is a comment :)")
        self.wrong_syntax("(: this is a (: nested :) comment :)")
        self.check_tree('child (: nasty (:nested :) axis comment :) ::B1', '(child (B1))')
        self.check_tree('child (: nasty "(: but not nested :)" axis comment :) ::B1', '(child (B1))')
        self.check_value("5 (: before operator comment :) < 4", False)  # Before infix operator
        self.check_value("5 < (: after operator comment :) 4", False)  # After infix operator
        self.check_value("true (:# nasty function comment :) ()", True)
        self.check_tree(' (: initial comment :)/ (:2nd comment:)A/B1(: 3rd comment :)/ \nC1 (: last comment :)\t',
                        '(/ (/ (/ (A)) (B1)) (C1))')

    def test_comma_operator(self):
        self.check_value("1, 2", [1, 2])
        self.check_value("(1, 2)", [1, 2])
        self.check_value("(-9, 28, 10)", [-9, 28, 10])
        self.check_value("(1, 2)", [1, 2])

        root = self.etree.XML('<A/>')
        self.check_selector("(7.0, /A, 'foo')", root, [7.0, root, 'foo'])
        self.check_selector("7.0, /A, 'foo'", root, [7.0, root, 'foo'])
        self.check_selector("/A, 7.0, 'foo'", self.etree.XML('<dummy/>'), [7.0, 'foo'])

    def test_range_expressions(self):
        # Some cases from https://www.w3.org/TR/xpath20/#construct_seq
        self.check_value("1 to 2", [1, 2])
        self.check_value("1 to 10", list(range(1, 11)))
        self.check_value("(10, 1 to 4)", [10, 1, 2, 3, 4])
        self.check_value("10 to 10", [10])
        self.check_value("15 to 10", [])
        self.check_value("fn:reverse(10 to 15)", [15, 14, 13, 12, 11, 10])

    def test_parenthesized_expressions(self):
        self.check_value("(1, 2, '10')", [1, 2, '10'])
        self.check_value("()", [])

    def test_if_expressions(self):
        root = self.etree.XML('<A><B1><C1/><C2/></B1><B2/><B3><C3/><C4/><C5/></B3></A>')
        self.check_value("if (1) then 2 else 3", 2)
        self.check_selector("if (true()) then /A/B1 else /A/B2", root, root[:1])
        self.check_selector("if (false()) then /A/B1 else /A/B2", root, root[1:2])

        # Cases from XPath 2.0 examples
        root = self.etree.XML('<part discounted="false"><wholesale/><retail/></part>')
        self.check_selector(
            'if ($part/@discounted) then $part/wholesale else $part/retail',
            root, [root[0]], variables={'part': root}
        )
        root = self.etree.XML('<widgets>'
                              '  <widget><unit-cost>25</unit-cost></widget>'
                              '  <widget><unit-cost>10</unit-cost></widget>'
                              '  <widget><unit-cost>15</unit-cost></widget>'
                              '</widgets>')
        self.check_selector(
            'if ($widget1/unit-cost < $widget2/unit-cost) then $widget1 else $widget2',
            root, [root[2]], variables={'widget1': root[0], 'widget2': root[2]}
        )

    def test_quantifier_expressions(self):
        # Cases from XPath 2.0 examples
        root = self.etree.XML('<parts>'
                              '  <part discounted="true" available="true" />'
                              '  <part discounted="false" available="true" />'
                              '  <part discounted="true" />'
                              '</parts>')
        self.check_selector("every $part in /parts/part satisfies $part/@discounted", root, True)
        self.check_selector("every $part in /parts/part satisfies $part/@available", root, False)

        root = self.etree.XML('<emps>'
                              '  <employee><salary>1000</salary><bonus>400</bonus></employee>'
                              '  <employee><salary>1200</salary><bonus>300</bonus></employee>'
                              '  <employee><salary>1200</salary><bonus>200</bonus></employee>'
                              '</emps>')
        self.check_selector("some $emp in /emps/employee satisfies "
                            "   ($emp/bonus > 0.25 * $emp/salary)", root, True)
        self.check_selector("every $emp in /emps/employee satisfies "
                            "   ($emp/bonus < 0.5 * $emp/salary)", root, True)

        context = XPathContext(root=self.etree.XML('<dummy/>'))
        self.check_value("some $x in (1, 2, 3), $y in (2, 3, 4) satisfies $x + $y = 4", True, context)
        self.check_value("every $x in (1, 2, 3), $y in (2, 3, 4) satisfies $x + $y = 4", False, context)

        self.check_value('some $x in (1, 2, "cat") satisfies $x * 2 = 4', True, context)
        self.check_value('every $x in (1, 2, "cat") satisfies $x * 2 = 4', False, context)

    def test_for_expressions(self):
        # Cases from XPath 2.0 examples
        context = XPathContext(root=self.etree.XML('<dummy/>'))
        self.check_value("for $i in (10, 20), $j in (1, 2) return ($i + $j)", [11, 12, 21, 22], context)

        root = self.etree.XML(
            """
            <bib>
                <book>
                    <title>TCP/IP Illustrated</title>
                    <author>Stevens</author>
                    <publisher>Addison-Wesley</publisher>
                </book>
                <book>
                    <title>Advanced Programming in the Unix Environment</title>
                    <author>Stevens</author>
                    <publisher>Addison-Wesley</publisher>
                </book>
                <book>
                    <title>Data on the Web</title>
                    <author>Abiteboul</author>
                    <author>Buneman</author>
                    <author>Suciu</author>
                </book>
            </bib>
            """)

        # Test step-by-step, testing also other basic features.
        self.check_selector("author[1]", root[0], [root[0][1]])
        self.check_selector("book/author[. = $a]", root, [root[0][1], root[1][1]], variables={'a': 'Stevens'})
        self.check_tree("book/author[. = $a][1]", '([ ([ (/ (book) (author)) (= (.) ($ (a)))) (1))')
        self.check_selector("book/author[. = $a][1]", root, [root[0][1]], variables={'a': 'Stevens'})
        self.check_selector("book/author[. = 'Stevens'][2]", root, [root[1][1]])

        self.check_selector("for $a in fn:distinct-values(book/author) return $a",
                            root, ['Stevens', 'Abiteboul', 'Buneman', 'Suciu'])

        self.check_selector("for $a in fn:distinct-values(book/author) "
                            "return book/author[. = $a]", root, [root[0][1], root[1][1]] + root[2][1:4])

        self.check_selector("for $a in fn:distinct-values(book/author) "
                            "return book/author[. = $a][1]", root, [root[0][1]] + root[2][1:4])
        self.check_selector(
            "for $a in fn:distinct-values(book/author) "
            "return (book/author[. = $a][1], book[author = $a]/title)", root,
            [root[0][1], root[0][0], root[1][0], root[2][1], root[2][0], root[2][2], root[2][0],
             root[2][3], root[2][0]]
        )

    def test_boolean_functions2(self):
        root = self.etree.XML('<A><B1/><B2/><B3/></A>')
        self.check_selector("boolean(/A)", root, True)
        self.check_selector("boolean((-10, 35))", root, ElementPathTypeError)  # Sequence with two numeric values
        self.check_selector("boolean((/A, 35))", root, True)

    def test_numerical_expressions2(self):
        self.check_value("5 idiv 2", 2)
        self.check_value("-3.5 idiv -2", 1)
        self.check_value("-3.5 idiv 2", -1)

    def test_comparison_operators2(self):
        self.check_value("0.05 eq 0.05", True)
        self.check_value("19.03 ne 19.02999", True)
        self.check_value("-1.0 eq 1.0", False)
        self.check_value("1 le 2", True)
        self.check_value("5 ge 9", False)
        self.check_value("5 gt 3", True)
        self.check_value("5 lt 20.0", True)
        self.check_value("false() eq 1", False)
        self.check_value("0 eq false()", True)
        self.check_value("2 * 2 eq 4", True)

        # From XPath 2.0 examples
        root = self.etree.XML('<collection>'
                              '   <book><author>Kafka</author></book>'
                              '   <book><author>Huxley</author></book>'
                              '   <book><author>Asimov</author></book>'
                              '</collection>')
        context = XPathContext(root=root, variables={'book1': root[0]})
        self.check_value('$book1 / author = "Kafka"', True, context=context)
        self.check_value('$book1 / author eq "Kafka"', True, context=context)

        self.check_value("(1, 2) = (2, 3)", True)
        self.check_value("(2, 3) = (3, 4)", True)
        self.check_value("(1, 2) = (3, 4)", False)
        self.check_value("(1, 2) != (2, 3)", True)  # != is not the inverse of =

        context = XPathContext(root=root, variables={
            'a': UntypedAtomic('1'), 'b': UntypedAtomic('2'), 'c': UntypedAtomic('2.0')
        })
        self.check_value('($a, $b) = ($c, 3.0)', False, context=context)
        self.check_value('($a, $b) = ($c, 2.0)', True, context=context)

    def test_number_functions2(self):
        root = self.etree.XML('<A><B1><C/></B1><B2/><B3><C1/><C2/></B3></A>')

        # Test cases taken from https://www.w3.org/TR/xquery-operators/#numeric-value-functions
        self.check_value("abs(10.5)", 10.5)
        self.check_value("abs(-10.5)", 10.5)
        self.check_value("round-half-to-even(0.5)", 0)
        self.check_value("round-half-to-even(1.5)", 2)
        self.check_value("round-half-to-even(2.5)", 2)
        self.check_value("round-half-to-even(3.567812E+3, 2)", 3567.81E0)
        self.check_value("round-half-to-even(4.7564E-3, 2)", 0.0E0)
        self.check_value("round-half-to-even(35612.25, -2)", 35600)

    def test_string_functions2(self):
        # Some test cases from https://www.w3.org/TR/xquery-operators/#string-value-functions
        self.check_value("codepoints-to-string((2309, 2358, 2378, 2325))", u'अशॊक')
        self.check_value(u'string-to-codepoints("Thérèse")', [84, 104, 233, 114, 232, 115, 101])
        self.check_value(u'string-to-codepoints(())', [])

        self.check_value('lower-case("aBcDe01")', 'abcde01')
        self.check_value('lower-case(("aBcDe01"))', 'abcde01')
        self.check_value('lower-case(())', '')
        self.wrong_type('lower-case((10))')

        self.check_value('upper-case("aBcDe01")', 'ABCDE01')
        self.check_value('upper-case(("aBcDe01"))', 'ABCDE01')
        self.check_value('upper-case(())', '')
        self.wrong_type('upper-case((10))')

        self.check_value('encode-for-uri("http://xpath.test")', 'http%3A%2F%2Fxpath.test')
        self.check_value('encode-for-uri("~bébé")', '~b%C3%A9b%C3%A9')
        self.check_value('encode-for-uri("100% organic")', '100%25%20organic')
        self.check_value('encode-for-uri("")', '')
        self.check_value('encode-for-uri(())', '')

        self.check_value('iri-to-uri("http://www.example.com/00/Weather/CA/Los%20Angeles#ocean")',
                         'http://www.example.com/00/Weather/CA/Los%20Angeles#ocean')
        self.check_value('iri-to-uri("http://www.example.com/~bébé")',
                         'http://www.example.com/~b%C3%A9b%C3%A9')
        self.check_value('iri-to-uri("")', '')
        self.check_value('iri-to-uri(())', '')

        self.check_value('escape-html-uri("http://www.example.com/00/Weather/CA/Los Angeles#ocean")',
                         'http://www.example.com/00/Weather/CA/Los Angeles#ocean')
        self.check_value("escape-html-uri(\"javascript:if (navigator.browserLanguage == 'fr') "
                         "window.open('http://www.example.com/~bébé');\")",
                         "javascript:if (navigator.browserLanguage == 'fr') "
                         "window.open('http://www.example.com/~b%C3%A9b%C3%A9');")
        self.check_value('escape-html-uri("")', '')
        self.check_value('escape-html-uri(())', '')

        self.check_value("string-length(())", 0)

        self.check_value("string-join(('Now', 'is', 'the', 'time', '...'), ' ')",
                         "Now is the time ...")
        self.check_value("string-join(('Blow, ', 'blow, ', 'thou ', 'winter ', 'wind!'), '')",
                         'Blow, blow, thou winter wind!')
        self.check_value("string-join((), 'separator')", '')

    def test_sequence_general_functions(self):
        # Test cases from https://www.w3.org/TR/xquery-operators/#general-seq-funcs
        self.check_value('fn:empty(("hello", "world"))', False)
        self.check_value('fn:exists(("hello", "world"))', True)
        self.check_value('fn:empty(fn:remove(("hello", "world"), 1))', False)
        self.check_value('fn:empty(())', True)
        self.check_value('fn:exists(())', False)
        self.check_value('fn:empty(fn:remove(("hello"), 1))', True)
        self.check_value('fn:exists(fn:remove(("hello"), 1))', False)

        self.check_value('fn:distinct-values((1, 2.0, 3, 2))', [1, 2.0, 3])
        context = XPathContext(
            root=self.etree.XML('<dummy/>'),
            variables={'x': [UntypedAtomic("cherry"), UntypedAtomic("bar"), UntypedAtomic("bar")]}
        )
        self.check_value('fn:distinct-values($x)', ['cherry', 'bar'], context)

        self.check_value('fn:index-of ((10, 20, 30, 40), 35)', [])
        self.check_value('fn:index-of ((10, 20, 30, 30, 20, 10), 20)', [2, 5])
        self.check_value('fn:index-of (("a", "sport", "and", "a", "pastime"), "a")', [1, 4])

        context = XPathContext(root=self.etree.XML('<dummy/>'), variables={'x': ['a', 'b', 'c']})
        self.check_value('fn:insert-before($x, 0, "z")', ['z', 'a', 'b', 'c'], context.copy())
        self.check_value('fn:insert-before($x, 1, "z")', ['z', 'a', 'b', 'c'], context.copy())
        self.check_value('fn:insert-before($x, 2, "z")', ['a', 'z', 'b', 'c'], context.copy())
        self.check_value('fn:insert-before($x, 3, "z")', ['a', 'b', 'z', 'c'], context.copy())
        self.check_value('fn:insert-before($x, 4, "z")', ['a', 'b', 'c', 'z'], context.copy())

        self.check_value('fn:remove($x, 0)', ['a', 'b', 'c'], context)
        self.check_value('fn:remove($x, 1)', ['b', 'c'], context)
        self.check_value('remove($x, 6)', ['a', 'b', 'c'], context)
        self.check_value('fn:remove((), 3)', [])

        self.check_value('reverse($x)', ['c', 'b', 'a'], context)
        self.check_value('fn:reverse(("hello"))', ['hello'], context)
        self.check_value('fn:reverse(())', [])

        self.check_value('fn:subsequence((), 5)', [])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), 1)', [1, 2, 3, 4, 5, 6, 7])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), 0)', [1, 2, 3, 4, 5, 6, 7])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), -1)', [1, 2, 3, 4, 5, 6, 7])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), 10)', [])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), 4)', [4, 5, 6, 7])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), 4, 2)', [4, 5])
        self.check_value('fn:subsequence((1, 2, 3, 4, 5, 6, 7), 3, 10)', [3, 4, 5, 6, 7])

        self.check_value('fn:unordered(())', [])
        self.check_value('fn:unordered(("z", 2, "3", "Z", "b", "a"))', [2, '3', 'Z', 'a', 'b', 'z'])

    def test_sequence_cardinality_functions(self):
        self.check_value('fn:zero-or-one(())', [])
        self.check_value('fn:zero-or-one((10))', [10])
        self.wrong_value('fn:zero-or-one((10, 20))')

        self.wrong_value('fn:one-or-more(())')
        self.check_value('fn:one-or-more((10))', [10])
        self.check_value('fn:one-or-more((10, 20, 30, 40))', [10, 20, 30, 40])

        self.check_value('fn:exactly-one((20))', [20])
        self.wrong_value('fn:exactly-one(())')
        self.wrong_value('fn:exactly-one((10, 20, 30, 40))')

    def test_qname_functions(self):
        self.check_value('fn:QName("", "person")', 'person')
        self.check_value('fn:QName((), "person")', 'person')
        self.check_value('fn:QName("http://www.example.com/example", "person")', 'person')
        self.check_value('fn:QName("http://www.example.com/example", "ht:person")', 'ht:person')
        self.wrong_type('fn:QName("", 2)')
        self.wrong_value('fn:QName("http://www.example.com/example", "xs:person")')

        self.check_value('fn:prefix-from-QName(fn:QName("http://www.example.com/example", "ht:person"))', 'ht')
        self.check_value('fn:prefix-from-QName(fn:QName("http://www.example.com/example", "person"))', [])
        self.check_value(
            'fn:local-name-from-QName(fn:QName("http://www.example.com/example", "person"))', 'person'
        )
        self.check_value(
            'fn:namespace-uri-from-QName(fn:QName("http://www.example.com/example", "person"))',
            'http://www.example.com/example'
        )

        root = self.etree.XML('<p1:A xmlns:p1="ns1" xmlns:p0="ns0">'
                              '  <B1><p2:C xmlns:p2="ns2"/></B1><B2/>'
                              '  <p0:B3><eg:C1 xmlns:eg="http://www.example.com/example"/><C2/></p0:B3>'
                              '</p1:A>')
        context = XPathContext(root=root)
        self.check_value("fn:resolve-QName((), .)", [], context=context.copy())
        self.check_value("fn:resolve-QName('eg:C2', .)", '{http://www.example.com/example}C2', context=context.copy())
        self.check_value("fn:namespace-uri-for-prefix('p1', .)", [], context=context.copy())
        self.check_value("fn:namespace-uri-for-prefix('eg', .)", 'http://www.example.com/example', context=context)
        self.check_selector("fn:in-scope-prefixes(.)", root, ['p2', 'p0'], namespaces={'p0': 'ns0', 'p2': 'ns2'})

    def test_string_constructors(self):
        self.check_value('xs:normalizedString("hello")', "hello")
        self.check_value('xs:normalizedString(())', [])

    def test_integer_constructors(self):
        self.wrong_value('xs:integer("hello")')
        self.check_value('xs:integer("19")', 19)

        self.wrong_value('xs:nonNegativeInteger("-1")')
        self.wrong_value('xs:nonNegativeInteger(-1)')
        self.check_value('xs:nonNegativeInteger(0)', 0)
        self.check_value('xs:nonNegativeInteger(1000)', 1000)
        self.wrong_value('xs:positiveInteger(0)')
        self.check_value('xs:positiveInteger("1")', 1)
        self.wrong_value('xs:negativeInteger(0)')
        self.check_value('xs:negativeInteger(-1)', -1)
        self.wrong_value('xs:nonPositiveInteger(1)')
        self.check_value('xs:nonPositiveInteger(0)', 0)
        self.check_value('xs:nonPositiveInteger("-1")', -1)

    def test_limited_integer_constructors(self):
        self.wrong_value('xs:long("true")')
        self.wrong_value('xs:long("340282366920938463463374607431768211456")')
        self.check_value('xs:long("-20")', -20)
        self.wrong_value('xs:int("-20 91")')
        self.wrong_value('xs:int("9223372036854775808")')
        self.check_value('xs:int("-9223372036854775808")', -2**63)
        self.check_value('xs:int("4611686018427387904")', 2**62)
        self.wrong_value('xs:short("40000")')
        self.check_value('xs:short("9999")', 9999)
        self.check_value('xs:short(-9999)', -9999)
        self.wrong_value('xs:byte(-129)')
        self.wrong_value('xs:byte(128)')
        self.check_value('xs:byte("-128")', -128)
        self.check_value('xs:byte(127)', 127)
        self.check_value('xs:byte(-90)', -90)

        self.wrong_value('xs:unsignedLong("-10")')
        self.check_value('xs:unsignedLong("3")', 3)
        self.wrong_value('xs:unsignedInt("-9223372036854775808")')
        self.check_value('xs:unsignedInt("9223372036854775808")', 2**63)
        self.wrong_value('xs:unsignedShort("-1")')
        self.check_value('xs:unsignedShort("0")', 0)
        self.wrong_value('xs:unsignedByte(-128)')
        self.check_value('xs:unsignedByte("128")', 128)

    def test_other_numerical_constructor(self):
        self.wrong_value('xs:decimal("hello")')
        self.check_value('xs:decimal("19")', 19)
        self.check_value('xs:decimal("19")', Decimal)

        self.wrong_value('xs:double("world")')
        self.check_value('xs:double("39.09")', 39.09)
        self.check_value('xs:double(-5)', -5.0)
        self.check_value('xs:double(-5)', float)

        self.wrong_value('xs:float("..")')
        self.check_value('xs:float(25.05)', 25.05)
        self.check_value('xs:float(-0.00001)', -0.00001)
        self.check_value('xs:float(0.00001)', float)

    def test_datetime_constructors(self):
        tzinfo1 = Timezone(datetime.timedelta(hours=5, minutes=24))
        tzinfo2 = Timezone(datetime.timedelta(hours=-14, minutes=0))
        self.check_value('xs:dateTime("1969-07-20T20:18:00")', datetime.datetime(1969, 7, 20, 20, 18))
        self.check_value('xs:dateTime("2000-05-10T21:30:00+05:24")',
                         datetime.datetime(2000, 5, 10, hour=21, minute=30, tzinfo=tzinfo1))
        self.wrong_value('xs:dateTime("2000-05-10t21:30:00+05:24")')
        self.wrong_value('xs:dateTime("2000-5-10T21:30:00+05:24")')
        self.wrong_value('xs:dateTime("2000-05-10T21:3:00+05:24")')
        self.wrong_value('xs:dateTime("2000-05-10T21:13:0+05:24")')
        self.wrong_value('xs:dateTime("2000-05-10T21:13:0")')

        self.check_value('xs:time("21:30:00")', datetime.datetime(1900, 1, 1, 21, 30))
        self.check_value('xs:time("11:15:48+05:24")', datetime.datetime(1900, 1, 1, 11, 15, 48, tzinfo=tzinfo1))

        self.check_value('xs:date("2017-01-19")', datetime.datetime(2017, 1, 19))
        self.check_value('xs:date("2011-11-11-14:00")', datetime.datetime(2011, 11, 11, tzinfo=tzinfo2))
        self.wrong_value('xs:date("2011-11-11-14:01")')
        self.wrong_value('xs:date("11-11-11")')

        self.check_value('xs:gDay("---30")', datetime.datetime(1900, 1, 30))
        self.check_value('xs:gDay("---21+05:24")', datetime.datetime(1900, 1, 21, tzinfo=tzinfo1))
        self.wrong_value('xs:gDay("---32")')
        self.wrong_value('xs:gDay("--19")')

        self.check_value('xs:gMonth("--09")', datetime.datetime(1900, 9, 1))
        self.check_value('xs:gMonth("--12")', datetime.datetime(1900, 12, 1))
        self.wrong_value('xs:gMonth("--9")')
        self.wrong_value('xs:gMonth("-09")')
        self.wrong_value('xs:gMonth("--13")')

        self.check_value('xs:gMonthDay("--07-02")', datetime.datetime(1900, 7, 2))
        self.check_value('xs:gMonthDay("--07-02-14:00")', datetime.datetime(1900, 7, 2, tzinfo=tzinfo2))
        self.wrong_value('xs:gMonthDay("--7-02")')
        self.wrong_value('xs:gMonthDay("-07-02")')
        self.wrong_value('xs:gMonthDay("--07-32")')

        self.check_value('xs:gYear("2004")', datetime.datetime(2004, 1, 1,))
        self.wrong_value('xs:gYear("-2004")')  # TODO: BCDateTime
        self.wrong_value('xs:gYear("12540")')  # TODO: >9999
        self.wrong_value('xs:gYear("84")')
        self.wrong_value('xs:gYear("821")')
        self.wrong_value('xs:gYear("84")')

        self.check_value('xs:gYearMonth("2004-02")', datetime.datetime(2004, 2, 1))
        self.wrong_value('xs:gYearMonth("2004-2")')
        self.wrong_value('xs:gYearMonth("204-02")')

    def test_duration_constructors(self):
        self.check_value('xs:duration("P3Y5M1D")', (41, 86400))
        self.check_value('xs:duration("P3Y5M1DT1H")', (41, 90000))
        self.check_value('xs:duration("P3Y5M1DT1H3M2.01S")', (41, Decimal('90182.01')))
        self.wrong_value('xs:duration("P3Y5M1X")')
        self.assertRaises(TypeError, self.parser.parse, 'xs:duration(1)')

        self.check_value('xs:yearMonthDuration("P3Y5M")', (41, 0))
        self.check_value('xs:yearMonthDuration("-P15M")', (-15, 0))
        self.check_value('xs:yearMonthDuration("-P20Y18M")', YearMonthDuration("-P21Y6M"))
        self.wrong_value('xs:yearMonthDuration("-P15M1D")')
        self.wrong_value('xs:yearMonthDuration("P15MT1H")')

        self.check_value('xs:dayTimeDuration("-P2DT15H")', DayTimeDuration('-PT226800S'))
        self.check_value('xs:dayTimeDuration("PT240H")', DayTimeDuration("P10D"))
        self.check_value('xs:dayTimeDuration("P365D")', DayTimeDuration("P365D"))
        self.check_value('xs:dayTimeDuration("-P2DT15H0M0S")', DayTimeDuration('-P2DT15H'))
        self.check_value('xs:dayTimeDuration("P3DT10H")', DayTimeDuration("P3DT10H"))
        self.check_value('xs:dayTimeDuration("PT1S")', (0, 1))
        self.check_value('xs:dayTimeDuration("PT0S")', (0, 0))
        self.wrong_value('xs:yearMonthDuration("P1MT10H")')

    def test_hex_binary_constructor(self):
        self.check_value('xs:hexBinary("84")', b'3834')
        self.check_value('xs:hexBinary(xs:hexBinary("84"))', b'3834')
        self.wrong_type('xs:hexBinary(12)')

    def test_base64_binary_constructor(self):
        self.check_value('xs:base64Binary("84")', b'ODQ=\n')
        self.check_value('xs:base64Binary(xs:base64Binary("84"))', b'ODQ=\n')
        self.check_value('xs:base64Binary("abcefghi")', b'YWJjZWZnaGk=\n')
        self.wrong_type('xs:base64Binary(1e2)')
        self.wrong_type('xs:base64Binary(1.1)')

    def test_from_duration_functions(self):
        pass  # self.check_value('fn:years-from-duration()', [])

    def test_node_and_item_accessors(self):
        document = self.etree.parse(io.StringIO(u'<A/>'))
        element = self.etree.Element('schema')
        element.attrib.update([('id', '0212349350')])
        context = XPathContext(root=document)
        self.check_select("document-node()", [], context)
        self.check_select("self::document-node()", [document], context)
        self.check_selector("self::document-node(A)", document, [document])
        context = XPathContext(root=element)
        self.check_select("self::element()", [element], context)
        self.check_select("self::node()", [element], context)
        self.check_select("self::attribute()", ['0212349350'], context)

        context.item = 7
        self.check_select("item()", [7], context)
        self.check_select("node()", [], context)
        context.item = 10.2
        self.check_select("item()", [10.2], context)
        self.check_select("node()", [], context)

    def test_node_set_functions2(self):
        root = self.etree.XML('<A><B1><C1/><C2/></B1><B2/><B3><C3/><C4/><C5/></B3></A>')
        self.check_selector("count(5)", root, 1)
        self.check_value("count((0, 1, 2 + 1, 3 - 1))", 4)

    def test_node_accessor_functions(self):
        root = self.etree.XML('<A xmlns:ns0="%s" id="10"><B1><C1 /><C2 ns0:nil="true" /></B1>'
                              '<B2 /><B3>simple text</B3></A>' % XSI_NAMESPACE)
        self.check_selector("node-name(.)", root, 'A')
        self.check_selector("node-name(/A/B1)", root, 'B1')
        self.check_selector("node-name(/A/*)", root, ElementPathTypeError)  # Not allowed more than one item!
        self.check_selector("nilled(./B1/C1)", root, False)
        self.check_selector("nilled(./B1/C2)", root, True)

        root = self.etree.XML('<A id="10"><B1> a text, <C1 /><C2>an inner text, </C2>a tail, </B1>'
                              '<B2 /><B3>an ending text </B3></A>')
        self.check_selector("string(.)", root, ' a text, an inner text, a tail, an ending text ')
        self.check_selector("data(.)", root, ' a text, an inner text, a tail, an ending text ')
        self.check_selector("data(.)", root, UntypedAtomic)

    def test_union_intersect_except(self):
        root = self.etree.XML('<A><B1><C1/><C2/><C3/></B1><B2><C1/><C2/><C3/><C4/></B2><B3/></A>')
        self.check_selector('/A/B2 union /A/B1', root, root[:2])
        self.check_selector('/A/B2 union /A/*', root, root[:])

        self.check_selector('/A/B2 intersect /A/B1', root, [])
        self.check_selector('/A/B2 intersect /A/*', root, [root[1]])
        self.check_selector('/A/B1/* intersect /A/B2/*', root, [])
        self.check_selector('/A/B1/* intersect /A/*/*', root, root[0][:])

        self.check_selector('/A/B2 except /A/B1', root, root[1:2])
        self.check_selector('/A/* except /A/B2', root, [root[0], root[2]])
        self.check_selector('/A/*/* except /A/B2/*', root, root[0][:])
        self.check_selector('/A/B2/* except /A/B1/*', root, root[1][:])
        self.check_selector('/A/B2/* except /A/*/*', root, [])

        root = self.etree.XML('<root><A/><B/><C/></root>')

        # From variables like XPath 2.0 examples
        context = XPathContext(root, variables={
            'seq1': root[:2],  # (A, B)
            'seq2': root[:2],  # (A, B)
            'seq3': root[1:],  # (B, C)
        })
        self.check_select('$seq1 union $seq2', root[:2], context=context)
        self.check_select('$seq2 union $seq3', root[:], context=context)
        self.check_select('$seq1 intersect $seq2', root[:2], context=context)
        self.check_select('$seq2 intersect $seq3', root[1:2], context=context)
        self.check_select('$seq1 except $seq2', [], context=context)
        self.check_select('$seq2 except $seq3', root[:1], context=context)

    def test_node_comparison(self):
        # Test cases from https://www.w3.org/TR/xpath20/#id-node-comparisons
        root = self.etree.XML('''
        <books>
            <book><isbn>1558604820</isbn><call>QA76.9 C3845</call></book>
            <book><isbn>0070512655</isbn><call>QA76.9 C3846</call></book>
            <book><isbn>0131477005</isbn><call>QA76.9 C3847</call></book>
        </books>''')
        self.check_selector('/books/book[isbn="1558604820"] is /books/book[call="QA76.9 C3845"]', root, True)
        self.check_selector('/books/book[isbn="0070512655"] is /books/book[call="QA76.9 C3847"]', root, False)
        self.check_selector('/books/book[isbn="not a code"] is /books/book[call="QA76.9 C3847"]', root, [])

        root = self.etree.XML('''
        <transactions>
            <purchase><parcel>28-451</parcel></purchase>
            <sale><parcel>33-870</parcel></sale>
            <purchase><parcel>15-392</parcel></purchase>
            <sale><parcel>35-530</parcel></sale>
            <purchase><parcel>10-639</parcel></purchase>
            <purchase><parcel>10-639</parcel></purchase>
            <sale><parcel>39-729</parcel></sale>
        </transactions>''')

        self.check_selector(
            '/transactions/purchase[parcel="28-451"] << /transactions/sale[parcel="33-870"]', root, True
        )
        self.check_selector(
            '/transactions/purchase[parcel="15-392"] >> /transactions/sale[parcel="33-870"]', root, True
        )
        self.check_selector(
            '/transactions/purchase[parcel="10-639"] >> /transactions/sale[parcel="33-870"]',
            root, ElementPathTypeError
        )

    def test_error_function(self):
        self.assertRaises(ElementPathError, self.check_value, "fn:error()")


class LxmlXPath2ParserTest(XPath2ParserTest):
    etree = lxml.etree


@unittest.skipIf(xmlschema is None, "xmlschema library >= v0.9.31 required.")
class XPath2ParserXMLSchemaTest(XPath2ParserTest):

    if xmlschema:
        schema = XMLSchemaProxy(
            schema=xmlschema.XMLSchema('''
            <!-- Dummy schema, only for tests -->
            <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" targetNamespace="http://xpath.test/ns">
            <xs:element name="test_element" type="xs:string"/>
            <xs:attribute name="test_attribute" type="xs:string"/>
            </xs:schema>''')
        )
    else:
        schema = None

    def setUp(self):
        self.parser = XPath2Parser(namespaces=self.namespaces, schema=self.schema, variables=self.variables)

    def test_xmlschema_proxy(self):
        context = XPathContext(root=self.etree.XML('<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"/>'))

        self.wrong_name("schema-element(nil)")
        self.wrong_name("schema-element(xs:string)")
        self.check_value("schema-element(xs:complexType)", None)
        self.check_value("schema-element(xs:schema)", context.item, context)
        self.check_tree("schema-element(xs:group)", '(schema-element (: (xs) (group)))')

        context.item = AttributeNode(XML_LANG_QNAME, 'en')
        self.wrong_name("schema-attribute(nil)")
        self.wrong_name("schema-attribute(xs:string)")
        self.check_value("schema-attribute(xml:lang)", None)
        self.check_value("schema-attribute(xml:lang)", context.item, context)
        self.check_tree("schema-attribute(xsi:schemaLocation)", '(schema-attribute (: (xsi) (schemaLocation)))')

    @unittest.skipIf(xmlschema is None, "The xmlschema library is not installed.")
    def test_instance_expression(self):
        element = self.etree.Element('schema')
        context = XPathContext(element)

        # Test cases from https://www.w3.org/TR/xpath20/#id-instance-of
        self.check_value("5 instance of xs:integer", True)
        self.check_value("5 instance of xs:decimal", True)
        self.check_value("(5, 6) instance of xs:integer+", True)
        self.check_value(". instance of element()", True, context)

        self.check_value("(5, 6) instance of xs:integer", False)
        self.check_value("(5, 6) instance of xs:integer*", True)
        self.check_value("(5, 6) instance of xs:integer?", False)

        self.check_value("5 instance of empty-sequence()", False)
        self.check_value("() instance of empty-sequence()", True)

    @unittest.skipIf(xmlschema is None, "The xmlschema library is not installed.")
    def test_treat_expression(self):
        element = self.etree.Element('schema')
        context = XPathContext(element)

        self.check_value("5 treat as xs:integer", [5])
        # self.check_value("5 treat as xs:string", ElementPathTypeError)   # FIXME: a bug of xmlschema!
        self.check_value("5 treat as xs:decimal", [5])
        self.check_value("(5, 6) treat as xs:integer+", [5, 6])
        self.check_value(". treat as element()", [element], context)

        self.check_value("(5, 6) treat as xs:integer", ElementPathTypeError)
        self.check_value("(5, 6) treat as xs:integer*", [5, 6])
        self.check_value("(5, 6) treat as xs:integer?", ElementPathTypeError)

        self.check_value("5 treat as empty-sequence()", ElementPathTypeError)
        self.check_value("() treat as empty-sequence()", [])

    def test_castable_expression(self):
        self.check_value("5 castable as xs:integer", True)
        self.check_value("'5' castable as xs:integer", True)
        self.check_value("'hello' castable as xs:integer", False)
        self.check_value("('5', '6') castable as xs:integer", False)
        self.check_value("() castable as xs:integer", False)
        self.check_value("() castable as xs:integer?", True)

    def test_cast_expression(self):
        self.check_value("5 cast as xs:integer", 5)
        self.check_value("'5' cast as xs:integer", 5)
        self.check_value("'hello' cast as xs:integer", ElementPathValueError)
        self.check_value("('5', '6') cast as xs:integer", ElementPathTypeError)
        self.check_value("() cast as xs:integer", ElementPathValueError)
        self.check_value("() cast as xs:integer?", [])

    def test_atomic_constructors(self):
        self.check_value("xs:integer('5')", 5)
        # self.check_value("xs:string(5.0)", '5.0')  # TODO: multi-value token


class LxmlXPath2ParserXMLSchemaTest(XPath2ParserXMLSchemaTest):
    etree = lxml.etree


if __name__ == '__main__':
    unittest.main()
