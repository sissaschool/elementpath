#!/usr/bin/env python
#
# Copyright (c), 2022, SISSA (International School for Advanced Studies).
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

from elementpath.validators import validate_analyzed_string, validate_json_to_xml


class ValidatorsTest(unittest.TestCase):
    etree = ElementTree

    def test_validate_analyzed_string(self):
        xml_source = dedent("""\
        <analyze-string-result xmlns="http://www.w3.org/2005/xpath-functions">
            <match>The</match>
            <non-match> </non-match>
            <match>cat</match>
            <non-match> </non-match>
            <match>sat</match>
            <non-match> </non-match>
            <match>on</match>
            <non-match> </non-match>
            <match>the</match>
            <non-match> </non-match>
            <match>mat</match>
            <non-match>.</non-match>
        </analyze-string-result>
        """)

        root = self.etree.XML(xml_source)
        self.assertIsNone(validate_analyzed_string(root))

        with self.assertRaises(ValueError):
            validate_analyzed_string(self.etree.XML('<invalid/>'))

    def test_validate_json_to_xml(self):
        xml_source = """\
        <fn:array xmlns:fn="http://www.w3.org/2005/xpath-functions">
           <fn:number>1</fn:number>
        </fn:array>"""

        root = self.etree.XML(xml_source)
        self.assertIsNone(validate_json_to_xml(root))

        with self.assertRaises(ValueError):
            validate_json_to_xml(self.etree.XML('<invalid/>'))


@unittest.skipIf(lxml_etree is None, "lxml library is not installed")
class ValidatorsTest(ValidatorsTest):
    etree = lxml_etree


if __name__ == '__main__':
    unittest.main()
