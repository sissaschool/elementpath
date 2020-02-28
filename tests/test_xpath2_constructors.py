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
import datetime
import math
from decimal import Decimal

try:
    import lxml.etree as lxml_etree
except ImportError:
    lxml_etree = None

from elementpath import ElementPathError, XPath2Parser
from elementpath.namespaces import XML_NAMESPACE, XSD_NAMESPACE, XSI_NAMESPACE, \
    XPATH_FUNCTIONS_NAMESPACE
from elementpath.datatypes import Timezone, DateTime, GregorianYear10, \
    YearMonthDuration, DayTimeDuration

try:
    from tests import xpath_test_class
except ImportError:
    import xpath_test_class


class XPath2ConstructorsTest(xpath_test_class.XPathTestCase):
    namespaces = {
        'xml': XML_NAMESPACE,
        'xs': XSD_NAMESPACE,
        'xsi': XSI_NAMESPACE,
        'fn': XPATH_FUNCTIONS_NAMESPACE,
        'eg': 'http://www.example.com/ns/',
        'tst': 'http://xpath.test/ns',
    }

    def setUp(self):
        self.parser = XPath2Parser(self.namespaces, self.variables)

    def check_value(self, path, expected=None, context=None):
        if context is not None:
            context = context.copy()
        try:
            root_token = self.parser.parse(path)
        except ElementPathError as err:
            if isinstance(expected, type) and isinstance(err, expected):
                return
            raise 

        if isinstance(expected, type) and issubclass(expected, Exception):
            self.assertRaises(expected, root_token.evaluate, context)
        elif isinstance(expected, float) and math.isnan(expected):
            value = root_token.evaluate(context)
            if isinstance(value, list):
                self.assertTrue(any(math.isnan(x) for x in value))
            else:
                self.assertTrue(math.isnan(value))

        elif not callable(expected):
            self.assertEqual(root_token.evaluate(context), expected)
        elif isinstance(expected, type):
            value = root_token.evaluate(context)
            self.assertIsInstance(value, expected)
        else:
            self.assertTrue(expected(root_token.evaluate(context)))

    # Wrong XPath expression checker shortcuts
    def wrong_value(self, path):
        self.assertRaises(ValueError, self.parser.parse, path)

    def wrong_type(self, path):
        self.assertRaises(TypeError, self.parser.parse, path)

    def wrong_name(self, path):
        self.assertRaises(NameError, self.parser.parse, path)

    def test_string_constructors(self):
        self.check_value("xs:string(5.0)", '5.0')
        self.check_value('xs:string(" hello  ")', ' hello  ')
        self.check_value('xs:string("\thello \n")', '\thello \n')
        self.check_value('xs:string(())', [])

        self.check_value('xs:normalizedString("hello")', "hello")
        self.check_value('xs:normalizedString(" hello  ")', " hello  ")
        self.check_value('xs:normalizedString("\thello \n")', " hello  ")
        self.check_value('xs:normalizedString(())', [])

        self.check_value('xs:token(" hello  world ")', "hello world")
        self.check_value('xs:token("hello\t world\n")', "hello world")
        self.check_value('xs:token(())', [])

        self.check_value('xs:language(" en ")', "en")
        self.check_value('xs:language(" en-GB ")', "en-GB")
        self.check_value('xs:language("it-IT")', "it-IT")
        self.check_value('xs:language("i-klingon")', 'i-klingon')  # IANA-registered language
        self.check_value('xs:language("x-another-language-code")', 'x-another-language-code')
        self.wrong_value('xs:language("MoreThan8")')
        self.check_value('xs:language(())', [])

        self.check_value('xs:NMTOKEN(" :menù.09-_ ")', ":menù.09-_")
        self.wrong_value('xs:NMTOKEN("alpha+")')
        self.wrong_value('xs:NMTOKEN("hello world")')
        self.check_value('xs:NMTOKEN(())', [])

        self.check_value('xs:Name(" :base ")', ":base")
        self.check_value('xs:Name(" ::level_alpha ")', "::level_alpha")
        self.check_value('xs:Name("level-alpha")', "level-alpha")
        self.check_value('xs:Name("level.alpha\t\n")', "level.alpha")
        self.check_value('xs:Name("__init__ ")', "__init__")
        self.check_value('xs:Name("\u0110")', "\u0110")
        self.wrong_value('xs:Name("2_values")')
        self.wrong_value('xs:Name(" .values ")')
        self.wrong_value('xs:Name(" -values ")')
        self.check_value('xs:Name(())', [])

        self.check_value('xs:NCName(" base ")', "base")
        self.check_value('xs:NCName(" _level_alpha ")', "_level_alpha")
        self.check_value('xs:NCName("level-alpha")', "level-alpha")
        self.check_value('xs:NCName("level.alpha\t\n")', "level.alpha")
        self.check_value('xs:NCName("__init__ ")', "__init__")
        self.check_value('xs:NCName("\u0110")', "\u0110")
        self.wrong_value('xs:NCName("2_values")')
        self.wrong_value('xs:NCName(" .values ")')
        self.wrong_value('xs:NCName(" -values ")')
        self.check_value('xs:NCName(())', [])

        self.check_value('xs:ID("xyz")', 'xyz')
        self.check_value('xs:IDREF("xyz")', 'xyz')
        self.check_value('xs:ENTITY("xyz")', 'xyz')

    def test_qname_constructor(self):
        self.check_value('xs:QName("xs:element")', 'xs:element')
        self.assertRaises(KeyError, self.parser.parse, 'xs:QName("xsd:element")')

    def test_any_uri_constructor(self):
        self.check_value('xs:anyURI("")', '')
        self.check_value('xs:anyURI("https://example.com")', 'https://example.com')
        self.check_value('xs:anyURI("mailto:info@example.com")', 'mailto:info@example.com')
        self.check_value('xs:anyURI("urn:example:com")', 'urn:example:com')
        self.check_value('xs:anyURI("../principi/libertà.html")', '../principi/libertà.html')
        self.check_value('xs:anyURI("../principi/libert%E0.html")', '../principi/libert%E0.html')
        self.check_value('xs:anyURI("../path/page.html#frag")', '../path/page.html#frag')
        self.wrong_value('xs:anyURI("../path/page.html#frag1#frag2")')
        self.wrong_value('xs:anyURI("https://example.com/index%.html")')
        self.wrong_value('xs:anyURI("https://example.com/index.%html")')
        self.wrong_value('xs:anyURI("https://example.com/index.html%  frag")')
        self.check_value('xs:anyURI(())', [])

    def test_boolean_constructor(self):
        self.check_value('xs:boolean(())', [])
        self.check_value('xs:boolean(1)', True)
        self.check_value('xs:boolean(0)', False)

    def test_integer_constructors(self):
        self.wrong_value('xs:integer("hello")')
        self.check_value('xs:integer("19")', 19)
        self.check_value("xs:integer('-5')", -5)

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

    def test_other_numerical_constructors(self):
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

    def test_datetime_constructor(self):
        tz0 = None
        tz1 = Timezone(datetime.timedelta(hours=5, minutes=24))
        self.check_value(
            'xs:dateTime("1969-07-20T20:18:00")', DateTime(1969, 7, 20, 20, 18, tzinfo=tz0)
        )
        self.check_value('xs:dateTime("2000-05-10T21:30:00+05:24")',
                         datetime.datetime(2000, 5, 10, hour=21, minute=30, tzinfo=tz1))
        self.check_value('xs:dateTime("1999-12-31T24:00:00")',
                         datetime.datetime(2000, 1, 1, 0, 0, tzinfo=tz0))

        self.wrong_value('xs:dateTime("2000-05-10t21:30:00+05:24")')
        self.wrong_value('xs:dateTime("2000-5-10T21:30:00+05:24")')
        self.wrong_value('xs:dateTime("2000-05-10T21:3:00+05:24")')
        self.wrong_value('xs:dateTime("2000-05-10T21:13:0+05:24")')
        self.wrong_value('xs:dateTime("2000-05-10T21:13:0")')

    def test_time_constructor(self):
        tz0 = None
        tz1 = Timezone(datetime.timedelta(hours=5, minutes=24))
        self.check_value('xs:time("21:30:00")', datetime.datetime(2000, 1, 1, 21, 30, tzinfo=tz0))
        self.check_value('xs:time("11:15:48+05:24")',
                         datetime.datetime(2000, 1, 1, 11, 15, 48, tzinfo=tz1))

    def test_date_constructor(self):
        tz0 = None
        tz2 = Timezone(datetime.timedelta(hours=-14, minutes=0))
        self.check_value('xs:date("2017-01-19")', datetime.datetime(2017, 1, 19, tzinfo=tz0))
        self.check_value('xs:date("2011-11-11-14:00")', datetime.datetime(2011, 11, 11, tzinfo=tz2))
        self.wrong_value('xs:date("2011-11-11-14:01")')
        self.wrong_value('xs:date("11-11-11")')

    def test_gregorian_constructors(self):
        tz0 = None
        tz1 = Timezone(datetime.timedelta(hours=5, minutes=24))
        tz2 = Timezone(datetime.timedelta(hours=-14, minutes=0))
        self.check_value('xs:gDay("---30")', datetime.datetime(2000, 1, 30, tzinfo=tz0))
        self.check_value('xs:gDay("---21+05:24")', datetime.datetime(2000, 1, 21, tzinfo=tz1))
        self.wrong_value('xs:gDay("---32")')
        self.wrong_value('xs:gDay("--19")')

        self.check_value('xs:gMonth("--09")', datetime.datetime(2000, 9, 1, tzinfo=tz0))
        self.check_value('xs:gMonth("--12")', datetime.datetime(2000, 12, 1, tzinfo=tz0))
        self.wrong_value('xs:gMonth("--9")')
        self.wrong_value('xs:gMonth("-09")')
        self.wrong_value('xs:gMonth("--13")')

        self.check_value('xs:gMonthDay("--07-02")', datetime.datetime(2000, 7, 2, tzinfo=tz0))
        self.check_value('xs:gMonthDay("--07-02-14:00")', datetime.datetime(2000, 7, 2, tzinfo=tz2))
        self.wrong_value('xs:gMonthDay("--7-02")')
        self.wrong_value('xs:gMonthDay("-07-02")')
        self.wrong_value('xs:gMonthDay("--07-32")')

        self.check_value('xs:gYear("2004")', datetime.datetime(2004, 1, 1, tzinfo=tz0))
        self.check_value('xs:gYear("-2004")', GregorianYear10(-2004, tzinfo=tz0))
        self.check_value('xs:gYear("-12540")', GregorianYear10(-12540, tzinfo=tz0))
        self.check_value('xs:gYear("12540")', GregorianYear10(12540, tzinfo=tz0))
        self.wrong_value('xs:gYear("84")')
        self.wrong_value('xs:gYear("821")')
        self.wrong_value('xs:gYear("84")')

        self.check_value('xs:gYearMonth("2004-02")', datetime.datetime(2004, 2, 1, tzinfo=tz0))
        self.wrong_value('xs:gYearMonth("2004-2")')
        self.wrong_value('xs:gYearMonth("204-02")')

    def test_duration_constructor(self):
        self.check_value('xs:duration("P3Y5M1D")', (41, 86400))
        self.check_value('xs:duration("P3Y5M1DT1H")', (41, 90000))
        self.check_value('xs:duration("P3Y5M1DT1H3M2.01S")', (41, Decimal('90182.01')))
        self.wrong_value('xs:duration("P3Y5M1X")')
        self.assertRaises(TypeError, self.parser.parse, 'xs:duration(1)')

    def test_year_month_duration_constructor(self):

        self.check_value('xs:yearMonthDuration("P3Y5M")', (41, 0))
        self.check_value('xs:yearMonthDuration("-P15M")', (-15, 0))
        self.check_value('xs:yearMonthDuration("-P20Y18M")',
                         YearMonthDuration.fromstring("-P21Y6M"))
        self.wrong_value('xs:yearMonthDuration("-P15M1D")')
        self.wrong_value('xs:yearMonthDuration("P15MT1H")')

    def test_day_time_duration_constructor(self):
        self.check_value('xs:dayTimeDuration("-P2DT15H")', DayTimeDuration(seconds=-226800))
        self.check_value('xs:dayTimeDuration("PT240H")', DayTimeDuration.fromstring("P10D"))
        self.check_value('xs:dayTimeDuration("P365D")', DayTimeDuration.fromstring("P365D"))
        self.check_value('xs:dayTimeDuration("-P2DT15H0M0S")',
                         DayTimeDuration.fromstring('-P2DT15H'))
        self.check_value('xs:dayTimeDuration("P3DT10H")', DayTimeDuration.fromstring("P3DT10H"))
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


@unittest.skipIf(lxml_etree is None, "The lxml library is not installed")
class LxmlXPath2ConstructorsTest(XPath2ConstructorsTest):
    etree = lxml_etree


if __name__ == '__main__':
    unittest.main()
