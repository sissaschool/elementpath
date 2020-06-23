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

from elementpath.namespaces import XSD_NAMESPACE, get_namespace, get_prefixed_qname, \
    get_extended_qname


class NamespacesTest(unittest.TestCase):
    namespaces = {
        'xs': XSD_NAMESPACE,
        'tst': "http://xpath.test/ns"
    }

    # namespaces.py module
    def test_get_namespace_function(self):
        self.assertEqual(get_namespace('A'), '')
        self.assertEqual(get_namespace('{ns}foo'), 'ns')
        self.assertEqual(get_namespace('{}foo'), '')
        self.assertEqual(get_namespace('{A}B{C}'), 'A')

    def test_qname_to_prefixed_function(self):
        self.assertEqual(get_prefixed_qname('{ns}foo', {'bar': 'ns'}), 'bar:foo')
        self.assertEqual(get_prefixed_qname('{ns}foo', {'': 'ns'}), 'foo')
        self.assertEqual(get_prefixed_qname('foo', {'': 'ns'}), 'foo')
        self.assertEqual(get_prefixed_qname('', {'': 'ns'}), '')
        self.assertEqual(get_prefixed_qname('{ns}foo', {}), '{ns}foo')
        self.assertEqual(get_prefixed_qname('{ns}foo', {'bar': 'other'}), '{ns}foo')

        with self.assertRaises(ValueError):
            get_prefixed_qname('{{ns}}foo', {'bar': 'ns'})

    def test_prefixed_to_qname_function(self):
        self.assertEqual(get_extended_qname('{ns}foo', {'bar': 'ns'}), '{ns}foo')
        self.assertEqual(get_extended_qname('bar:foo', {'bar': 'ns'}), '{ns}foo')
        self.assertEqual(get_extended_qname('foo', {'': 'ns'}), '{ns}foo')
        self.assertEqual(get_extended_qname('', {'': 'ns'}), '')

        with self.assertRaises(ValueError):
            get_extended_qname('bar:foo', self.namespaces)
        with self.assertRaises(ValueError):
            get_extended_qname('bar:foo:bar', {'bar': 'ns'})
        with self.assertRaises(ValueError):
            get_extended_qname(':foo', {'': 'ns'})
        with self.assertRaises(ValueError):
            get_extended_qname('foo:', {'': 'ns'})


if __name__ == '__main__':
    unittest.main()
