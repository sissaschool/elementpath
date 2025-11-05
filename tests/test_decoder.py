#!/usr/bin/env python
#
# Copyright (c), 2022-2025, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import unittest
from textwrap import dedent
from xml.etree import ElementTree

try:
    import lxml.etree as lxml_etree
except ImportError:
    lxml_etree = None

try:
    import xmlschema
except ImportError:
    xmlschema = None

try:
    from tests import xpath_test_class
except ImportError:
    import xpath_test_class

from elementpath import XPathContext
# from elementpath.decoder import get_atomic_sequence
from elementpath.datatypes import DateTime


# noinspection PyUnresolvedReferences
@unittest.skipIf(xmlschema is None, "xmlschema library is not installed")
class DecoderTest(xpath_test_class.XPathTestCase):
    etree = ElementTree

    def test_decode_union(self):
        schema = xmlschema.XMLSchema(dedent('''\
            <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
                <xs:element name="value" type="dateUnion" />
                <xs:simpleType name="dateUnion">
                    <xs:union memberTypes="xs:date xs:dateTime " />
                </xs:simpleType>
            </xs:schema>'''))

        root = self.etree.XML('<value>2007-12-31T12:30:40</value>')
        context = XPathContext(root, schema=schema.xpath_proxy)
        self.check_value('fn:data(.)', [DateTime(2007, 12, 31, 12, 30, 40)], context=context)


@unittest.skipIf(xmlschema is None, "xmlschema library is not installed")
@unittest.skipIf(lxml_etree is None, "lxml library is not installed")
class DecoderLxmlTest(DecoderTest):
    etree = lxml_etree


if __name__ == '__main__':
    unittest.main()
