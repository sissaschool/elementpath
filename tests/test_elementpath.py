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
#
# Note: Many tests in imported modules are built using the examples of the
#       XPath standards, published by W3C under the W3C Document License.
#
#       References:
#           http://www.w3.org/TR/1999/REC-xpath-19991116/
#           http://www.w3.org/TR/2010/REC-xpath20-20101214/
#           http://www.w3.org/TR/2010/REC-xpath-functions-20101214/
#           https://www.w3.org/Consortium/Legal/2015/doc-license
#           https://www.w3.org/TR/charmod-norm/
#
import unittest

if __name__ == '__main__':
    try:
        from tests.test_exceptions import ExceptionsTest
        from tests.test_namespaces import NamespacesTest
        from tests.test_datatypes import UntypedAtomicTest, DateTimeTypesTest, DurationTypesTest, TimezoneTypeTest
        from tests.test_tdop_parser import TdopParserTest
        from tests.test_xpath_nodes import XPathNodesTest
        from tests.test_xpath_token import XPathTokenTest
        from tests.test_xpath_context import XPathContextTest
        from tests.test_xpath1_parser import XPath1ParserTest, LxmlXPath1ParserTest
        from tests.test_xpath2_parser import XPath2ParserTest, LxmlXPath2ParserTest
        from tests.test_schema_proxy import XPath2ParserXMLSchemaTest, LxmlXPath2ParserXMLSchemaTest
        from tests.test_selectors import XPathSelectorsTest
        from tests.test_package import PackageTest
    except ImportError:
        # Python 2 fallback
        from test_exceptions import ExceptionsTest
        from test_namespaces import NamespacesTest
        from test_datatypes import UntypedAtomicTest, DateTimeTypesTest, DurationTypesTest, TimezoneTypeTest
        from test_tdop_parser import TdopParserTest
        from test_xpath_nodes import XPathNodesTest
        from test_xpath_token import XPathTokenTest
        from test_xpath_context import XPathContextTest
        from test_xpath1_parser import XPath1ParserTest, LxmlXPath1ParserTest
        from test_xpath2_parser import XPath2ParserTest, LxmlXPath2ParserTest
        from test_schema_proxy import XPath2ParserXMLSchemaTest, LxmlXPath2ParserXMLSchemaTest
        from test_selectors import XPathSelectorsTest
        from test_package import PackageTest

    unittest.main()
