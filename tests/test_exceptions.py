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

from elementpath.exceptions import ElementPathError, xpath_error
from elementpath.namespaces import XSD_NAMESPACE
from elementpath.xpath1 import XPath1Parser


class ExceptionsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.parser = XPath1Parser(namespaces={'xs': XSD_NAMESPACE, 'tst': "http://xpath.test/ns"})

    def test_string_conversion(self):
        err = ElementPathError("unknown error")
        self.assertEqual(str(err), 'unknown error')
        err = ElementPathError("unknown error", code='XPST0001')
        self.assertEqual(str(err), '[XPST0001] unknown error')
        token = self.parser.symbol_table['true'](self.parser)
        err = ElementPathError("unknown error", token=token)
        self.assertEqual(str(err), "'true' function at line 1, column 1: unknown error")
        err = ElementPathError("unknown error", code='XPST0001', token=token)
        self.assertEqual(str(err), "'true' function at line 1, column 1: [XPST0001] unknown error")

    def test_xpath_error(self):
        self.assertEqual(str(xpath_error('XPST0001')),
                         '[err:XPST0001] Parser not bound to a schema')
        self.assertEqual(str(xpath_error('err:XPDY0002', "test message")),
                         '[err:XPDY0002] test message')

        self.assertRaises(ValueError, xpath_error, '')
        self.assertRaises(ValueError, xpath_error, 'error:XPDY0002')

        self.assertEqual(str(xpath_error('{http://www.w3.org/2005/xqt-errors}XPST0001')),
                         '[err:XPST0001] Parser not bound to a schema')

        with self.assertRaises(ValueError) as err:
            xpath_error('{http://www.w3.org/2005/xpath-functions}XPST0001')
        self.assertEqual(str(err.exception), "[err:XPTY0004] invalid namespace "
                                             "'http://www.w3.org/2005/xpath-functions'")

        with self.assertRaises(ValueError) as err:
            xpath_error('{http://www.w3.org/2005/xpath-functions}}XPST0001')
        self.assertEqual(str(err.exception), "[err:XPTY0004] '{http://www.w3.org/2005/xpath-"
                                             "functions}}XPST0001' is not an xs:QName",)


if __name__ == '__main__':
    unittest.main()
