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
import unittest
import xml.etree.ElementTree as ElementTree

from elementpath import *


class XPathContextTest(unittest.TestCase):
    root = ElementTree.XML('<author>Dickens</author>')

    def test_initialization(self):
        self.assertRaises(TypeError, XPathContext, None)

    def test_repr(self):
        self.assertEqual(
            repr(XPathContext(self.root)),
            "XPathContext(root={0}, item={0}, position=0, size=1, axis=None)".format(self.root)
        )

    def test_parent_map(self):
        root = ElementTree.XML('<A><B1/><B2/></A>')
        context = XPathContext(root)
        self.assertEqual(context.parent_map, {root[0]: root, root[1]: root})

        root = ElementTree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2/></B3></A>')
        context = XPathContext(root)
        self.assertEqual(context.parent_map, {
            root[0]: root, root[0][0]: root[0], root[1]: root,
            root[2]: root, root[2][0]: root[2], root[2][1]: root[2]
        })

    def test_iter_attributes(self):
        root = ElementTree.XML('<A a1="10" a2="20"/>')
        context = XPathContext(root)
        self.assertListEqual(
            sorted(list(context.iter_attributes()), key=lambda x: x[0]),
            [AttributeNode(name='a1', value='10'), AttributeNode(name='a2', value='20')]
        )

        context.item = None
        self.assertListEqual(list(context.iter_attributes()), [])

    def test_iter_parent(self):
        root = ElementTree.XML('<A a1="10" a2="20"/>')
        context = XPathContext(root, item=None)
        self.assertListEqual(list(context.iter_parent()), [])

    def test_iter_descendants(self):
        root = ElementTree.XML('<A a1="10" a2="20"><B1/><B2/></A>')
        attr = AttributeNode('a1', '10')
        self.assertListEqual(list(XPathContext(root).iter_descendants()), [root, root[0], root[1]])
        self.assertListEqual(list(XPathContext(root, item=attr).iter_descendants()), [])

    def test_iter_ancestors(self):
        root = ElementTree.XML('<A a1="10" a2="20"><B1/><B2/></A>')
        attr = AttributeNode('a1', '10')
        self.assertListEqual(list(XPathContext(root).iter_ancestors()), [])
        self.assertListEqual(list(XPathContext(root, item=root[1]).iter_ancestors()), [root])
        self.assertListEqual(list(XPathContext(root).iter_ancestors(item=root[1])), [root])
        self.assertListEqual(list(XPathContext(root, item=attr).iter_ancestors()), [])

    def test_iter(self):
        root = ElementTree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2/></B3></A>')
        context = XPathContext(root)
        self.assertListEqual(list(context.iter()), list(root.iter()))
        context.item = None
        self.assertListEqual(list(context.iter()), [root] + list(root.iter()))
        context.item = AttributeNode('a1', '10')
        self.assertListEqual(list(context.iter()), [])


if __name__ == '__main__':
    unittest.main()
