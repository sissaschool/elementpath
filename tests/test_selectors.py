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
        self.assertListEqual(select(self.root, 'text()'), ['Dickens'])
        self.assertEqual(select(self.root, '$a', variables={'a': 1}), 1)

        self.assertEqual(
            select(self.root, '$a', variables={'a': 1}, variable_types={'a': 'xs:decimal'}), 1
        )

    def test_iter_select_function(self):
        self.assertListEqual(list(iter_select(self.root, 'text()')), ['Dickens'])
        self.assertListEqual(list(iter_select(self.root, '$a', variables={'a': True})), [True])

    def test_selector_class(self):
        selector = Selector('/A')
        self.assertEqual(repr(selector), "Selector(path='/A', parser=XPath2Parser)")
        self.assertEqual(selector.namespaces, XPath2Parser.DEFAULT_NAMESPACES)

        selector = Selector('text()')
        self.assertListEqual(selector.select(self.root), ['Dickens'])
        self.assertListEqual(list(selector.iter_select(self.root)), ['Dickens'])

        selector = Selector('$a', variables={'a': 1})
        self.assertEqual(selector.select(self.root), 1)
        self.assertListEqual(list(selector.iter_select(self.root)), [1])

    def test_issue_001(self):
        selector = Selector("//FullPath[ends-with(., 'Temp')]")
        self.assertListEqual(selector.select(self.etree.XML('<A/>')), [])
        self.assertListEqual(selector.select(self.etree.XML('<FullPath/>')), [])
        root = self.etree.XML('<FullPath>High Temp</FullPath>')
        self.assertListEqual(selector.select(root), [root])

    def test_issue_042(self):
        selector1 = Selector('text()')
        selector2 = Selector('sup[last()]/preceding-sibling::text()')
        root = self.etree.XML('<root>a<sup>1</sup>b<sup>2</sup>c<sup>3</sup></root>')
        self.assertListEqual(selector1.select(root), selector2.select(root))

        selector2 = Selector('sup[1]/following-sibling::text()')
        root = self.etree.XML('<root><sup>1</sup>b<sup>2</sup>c<sup>3</sup>d</root>')
        self.assertListEqual(selector1.select(root), selector2.select(root))


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
        k = None
        for k, p in enumerate(select(doc, '//pb'), start=1):
            self.assertEqual(p.attrib['n'], f'page{k}')
            self.assertListEqual(p.xpath('./@n'), [f'page{k}'])
            self.assertListEqual(select(doc, './@n'), [])
            self.assertListEqual(select(p, './@n'), [f'page{k}'])
            self.assertListEqual(select(doc, './@n', item=p), [f'page{k}'])
        else:
            self.assertEqual(k, 2)


if __name__ == '__main__':
    unittest.main()
