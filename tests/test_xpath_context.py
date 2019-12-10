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
from elementpath.compat import PY3


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

        context = XPathContext(root, item=TypedElement(root, ''))
        self.assertEqual(context.parent_map, {root[0]: root, root[1]: root})

        root = ElementTree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2/></B3></A>')

        context = XPathContext(root)
        result = {
            root[0]: root, root[0][0]: root[0], root[1]: root,
            root[2]: root, root[2][0]: root[2], root[2][1]: root[2]
        }
        self.assertEqual(context.parent_map, result)
        self.assertEqual(context.parent_map, result)  # Test property caching

        context = XPathContext(root, item=TypedElement(root, None))
        self.assertEqual(context.parent_map, result)

    def test_get_parent(self):
        root = ElementTree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2 max="10"/></B3></A>')

        context = XPathContext(root)

        self.assertIsNone(context._parent_map)
        self.assertIsNone(context.get_parent(root))

        self.assertIsNone(context._parent_map)
        self.assertEqual(context.get_parent(root[0]), root)
        self.assertIsInstance(context._parent_map, dict)
        parent_map_id = id(context._parent_map)

        self.assertEqual(context.get_parent(root[1]), root)
        self.assertEqual(context.get_parent(root[2]), root)
        self.assertEqual(context.get_parent(root[2][1]), root[2])

        self.assertEqual(context.get_parent(TypedElement(root[2][1], None)), root[2])
        self.assertEqual(id(context._parent_map), parent_map_id)

        self.assertIsNone(context.get_parent(AttributeNode('max', '10')))
        self.assertNotEqual(id(context._parent_map), parent_map_id)

        parent_map_id = id(context._parent_map)
        self.assertIsNone(context.get_parent(AttributeNode('max', '10')))
        if PY3:
            self.assertEqual(id(context._parent_map), parent_map_id)  # LRU cache prevents parent map rebuild

    def test_get_path(self):
        root = ElementTree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2 max="10"/></B3></A>')

        context = XPathContext(root)

        self.assertEqual(context.get_path(root), '/A')
        self.assertEqual(context.get_path(root[0]), '/A/B1')
        self.assertEqual(context.get_path(root[0][0]), '/A/B1/C1')
        self.assertEqual(context.get_path(root[1]), '/A/B2')
        self.assertEqual(context.get_path(root[2]), '/A/B3')
        self.assertEqual(context.get_path(root[2][0]), '/A/B3/C1')
        self.assertEqual(context.get_path(root[2][1]), '/A/B3/C2')
        context._elem = root[2][1]
        self.assertEqual(context.get_path(AttributeNode('max', '10')), '/A/B3/C2/@max')

        root = ElementTree.XML('<A><B1>10</B1><B2 min="1"/><B3/></A>')
        context = XPathContext(root)
        self.assertEqual(context.get_path(TypedElement(root[0], 10)), '/A/B1')
        attr = TypedAttribute(AttributeNode('min', '1'), 1)
        context = XPathContext(root)
        context._elem = root[1]
        self.assertEqual(context.get_path(attr), '/A/B2/@min')

    def test_iter_attributes(self):
        root = ElementTree.XML('<A a1="10" a2="20"/>')
        context = XPathContext(root)
        self.assertListEqual(
            sorted(list(context.iter_attributes()), key=lambda x: x[0]),
            [AttributeNode(name='a1', value='10'), AttributeNode(name='a2', value='20')]
        )
        context = XPathContext(root, item=TypedElement(root, ''))
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

        context = XPathContext(root)
        self.assertListEqual(list(context.iter_parent()), [])

        context = XPathContext(root, item=TypedElement(root, ''))
        self.assertListEqual(list(context.iter_parent()), [])

        root = ElementTree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2/></B3></A>')
        context = XPathContext(root, item=None)
        self.assertListEqual(list(context.iter_parent()), [])

        context = XPathContext(root, item=root[2][0])
        self.assertListEqual(list(context.iter_parent()), [root[2]])

        context = XPathContext(root, item=TypedElement(root[2][0], None))
        self.assertListEqual(list(context.iter_parent()), [root[2]])

    def test_iter_descendants(self):
        root = ElementTree.XML('<A a1="10" a2="20"><B1/><B2/></A>')
        attr = AttributeNode('a1', '10')
        self.assertListEqual(list(XPathContext(root).iter_descendants()), [root, root[0], root[1]])
        self.assertListEqual(list(XPathContext(root, item=attr).iter_descendants()), [])

        context = XPathContext(root, item=TypedElement(root, ''))
        self.assertListEqual(list(context.iter_descendants()), [root, root[0], root[1]])

    def test_iter_ancestors(self):
        root = ElementTree.XML('<A a1="10" a2="20"><B1/><B2/></A>')
        attr = AttributeNode('a1', '10')
        self.assertListEqual(list(XPathContext(root).iter_ancestors()), [])
        self.assertListEqual(list(XPathContext(root, item=root[1]).iter_ancestors()), [root])
        self.assertListEqual(list(XPathContext(root).iter_ancestors(item=root[1])), [root])
        self.assertListEqual(list(XPathContext(root, item=attr).iter_ancestors()), [])

        context = XPathContext(root, item=TypedElement(root[1], None))
        self.assertListEqual(list(context.iter_ancestors()), [root])

    def test_iter(self):
        root = ElementTree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2/></B3></A>')
        context = XPathContext(root)
        self.assertListEqual(list(context.iter()), list(root.iter()))

        doc = ElementTree.ElementTree(root)
        context = XPathContext(doc)
        self.assertListEqual(list(context.iter()), [doc] + list(root.iter()))

    def test_iter_preceding(self):
        root = ElementTree.XML('<A a1="10" a2="20"/>')
        context = XPathContext(root, item=None)
        self.assertListEqual(list(context.iter_preceding()), [])

        context = XPathContext(root)
        self.assertListEqual(list(context.iter_preceding()), [])

        context = XPathContext(root, item=TypedElement(root, ''))
        self.assertListEqual(list(context.iter_preceding()), [])

        context = XPathContext(root, item='text')
        self.assertListEqual(list(context.iter_preceding()), [])

        root = ElementTree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2/></B3></A>')
        context = XPathContext(root, item=root[2][1])
        self.assertListEqual(list(context.iter_preceding()),
                             [root[0], root[0][0], root[1], root[2][0]])

    def test_iter_results(self):
        root = ElementTree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2 max="10"/></B3></A>')

        results = [root[2], root[0][0]]
        context = XPathContext(root)
        self.assertListEqual(list(context.iter_results(results)), [root[0][0], root[2]])

        context = XPathContext(root, item=TypedElement(root, None))
        self.assertListEqual(list(context.iter_results(results)), [root[0][0], root[2]])

        results = [root[2], TypedElement(root[0][0], None)]
        context = XPathContext(root)
        self.assertListEqual(list(context.iter_results(results)), [TypedElement(root[0][0], None), root[2]])

        context = XPathContext(root, item=TypedElement(root, None))
        self.assertListEqual(list(context.iter_results(results)), [TypedElement(root[0][0], None), root[2]])

        results = [TypedAttribute(AttributeNode('max', '10'), 10), root[0]]
        context = XPathContext(root)
        self.assertListEqual(list(context.iter_results(results)), results[::-1])

        results = [TypedAttribute(AttributeNode('max', '11'), 11), root[0]]
        context = XPathContext(root)
        self.assertListEqual(list(context.iter_results(results)), results[1:])


if __name__ == '__main__':
    unittest.main()
