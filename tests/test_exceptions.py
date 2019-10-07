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
from __future__ import unicode_literals
import unittest

from elementpath.exceptions import ElementPathError, xpath_error
from elementpath.namespaces import XSD_NAMESPACE
from elementpath.xpath1_parser import XPath1Parser


class ExceptionsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.parser = XPath1Parser(namespaces={'xs': XSD_NAMESPACE, 'tst': "http://xpath.test/ns"})

    def test_exception_repr(self):
        err = ElementPathError("unknown error")
        self.assertEqual(str(err), 'unknown error')
        err = ElementPathError("unknown error", code='XPST0001')
        self.assertEqual(str(err), '[XPST0001] unknown error.')
        token = self.parser.symbol_table['true'](self.parser)
        err = ElementPathError("unknown error", code='XPST0001', token=token)
        self.assertEqual(str(err), "'true' function: [XPST0001] unknown error.")

    def test_xpath_error(self):
        self.assertEqual(str(xpath_error('XPST0001')), '[err:XPST0001] Parser not bound to a schema.')
        self.assertEqual(str(xpath_error('err:XPDY0002', "test message")), '[err:XPDY0002] test message.')
        self.assertRaises(ValueError, xpath_error, '')
        self.assertRaises(ValueError, xpath_error, 'error:XPDY0002')


if __name__ == '__main__':
    unittest.main()
