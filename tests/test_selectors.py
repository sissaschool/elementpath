#!/usr/bin/env python
#
# Copyright (c), 2018-2025, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import unittest
import warnings
import xml.etree.ElementTree as ElementTree

from elementpath import select, iter_select, Selector, XPath2Parser

try:
    import lxml.etree as lxml_etree
except ImportError:
    lxml_etree = None


class XPathSelectorsTest(unittest.TestCase):
    etree = ElementTree

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = cls.etree.XML('<author>Dickens</author>')

    def test_select_function(self):
        self.assertEqual(select(self.root, 'text()'), ['Dickens'])
        self.assertEqual(select(self.root, '$a', variables={'a': 1}), 1)

        self.assertEqual(
            select(self.root, '$a', variables={'a': 1}, variable_types={'a': 'xs:decimal'}), 1
        )

    def test_iter_select_function(self):
        self.assertEqual(list(iter_select(self.root, 'text()')), ['Dickens'])
        self.assertEqual(list(iter_select(self.root, '$a', variables={'a': True})), [True])

    def test_selector_class(self):
        selector = Selector('/A')
        self.assertEqual(repr(selector), "Selector(path='/A', parser=XPath2Parser)")
        self.assertEqual(selector.namespaces, XPath2Parser.DEFAULT_NAMESPACES)

        selector = Selector('text()')
        self.assertEqual(selector.select(self.root), ['Dickens'])
        self.assertEqual(list(selector.iter_select(self.root)), ['Dickens'])

        selector = Selector('$a')
        self.assertEqual(selector.select(self.root, variables={'a': 1}), 1)
        self.assertEqual(list(selector.iter_select(self.root, variables={'a': 1})), [1])

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            selector = Selector('$a', variables={'a': 1})
            self.assertEqual(len(w), 1)
            self.assertEqual(w[0].category, DeprecationWarning)

        self.assertEqual(selector.select(self.root), 1)
        self.assertEqual(list(selector.iter_select(self.root)), [1])

    def test_issue_001(self):
        selector = Selector("//FullPath[ends-with(., 'Temp')]")
        self.assertEqual(selector.select(self.etree.XML('<A/>')), [])
        self.assertEqual(selector.select(self.etree.XML('<FullPath/>')), [])
        root = self.etree.XML('<FullPath>High Temp</FullPath>')
        self.assertEqual(selector.select(root), [root])

    def test_issue_042(self):
        selector1 = Selector('text()')
        selector2 = Selector('sup[last()]/preceding-sibling::text()')
        root = self.etree.XML('<root>a<sup>1</sup>b<sup>2</sup>c<sup>3</sup></root>')
        self.assertEqual(selector1.select(root), selector2.select(root))

        selector2 = Selector('sup[1]/following-sibling::text()')
        root = self.etree.XML('<root><sup>1</sup>b<sup>2</sup>c<sup>3</sup>d</root>')
        self.assertEqual(selector1.select(root), selector2.select(root))

    def test_fragment_argument__issue_081(self):
        # xml1 contains the xml-stylesheet tag
        xml1 = b"""<?xml version="1.0" encoding="UTF-8"?>
        <?xml-stylesheet type='text/xsl' href='test.xsl'?>
        <root>
            <first>
                <second>
                    value
                </second>
            </first>
        </root>
        """

        # the same as xml1, but without the xml-stylesheet tag
        xml2 = b"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <root>
            <first>
                <second>
                    value
                </second>
            </first>
        </root>
        """

        root1 = self.etree.XML(xml1)
        root2 = self.etree.XML(xml2)
        query = "first/second"

        if hasattr(root1, 'xpath'):
            self.assertEqual(select(root1, query), [])
        else:
            self.assertEqual(select(root1, query), root1[0][:])

        self.assertEqual(select(root1, query, fragment=True), root1[0][:])
        self.assertEqual(select(root2, query), root2[0][:])

        self.assertEqual(select(root1, query, fragment=False), [])
        self.assertEqual(select(root2, query, fragment=False), [])

        query = "root/first/second"

        self.assertEqual(select(root1, query, fragment=False), root1[0][:])
        self.assertEqual(select(root2, query, fragment=False), root2[0][:])


@unittest.skipIf(lxml_etree is None, "The lxml library is not installed")
class LxmlXPathSelectorsTest(XPathSelectorsTest):
    etree = lxml_etree

    def test_issue_058(self):
        tei = """<?xml version='1.0' encoding='UTF8'?>
        <?xml-model type="application/xml"?>
        <TEI xmlns="http://www.tei-c.org/ns/1.0">
          <text>
                <pb n="page1"/>
                <pb n="page2"/>
          </text>
        </TEI>
        """

        doc = self.etree.XML(tei.encode())
        namespaces = {'': "http://www.tei-c.org/ns/1.0"}
        k = None
        for k, p in enumerate(select(doc, '//pb', namespaces), start=1):
            self.assertEqual(p.attrib['n'], f'page{k}')
            self.assertEqual(p.xpath('./@n'), [f'page{k}'])
            self.assertEqual(select(doc, './@n'), [])
            self.assertEqual(select(p, './@n'), [f'page{k}'])
            self.assertEqual(select(doc, './@n', item=p), [f'page{k}'])
        else:
            self.assertEqual(k, 2)

    def test_issue_074(self):
        root = lxml_etree.XML("<root><trunk><branch></branch></trunk></root>")

        result = select(root, "trunk")
        self.assertEqual(result, [root[0]])  # [<Element trunk at 0x...>]

        result = select(root, "/root/trunk")
        self.assertEqual(result, [root[0]])  # [<Element trunk at 0x...>]

        root = lxml_etree.XML("<!--comment--><root><trunk><branch></branch></trunk></root>")

        result = select(root, "trunk")
        self.assertEqual(result, [])

        result = select(root, "root/trunk")
        self.assertEqual(result, [root[0]])  # [<Element trunk at 0x...>]

        result = select(root, "/root/trunk")
        self.assertEqual(result, [root[0]])  # [<Element trunk at 0x...>]


if __name__ == '__main__':
    unittest.main()
