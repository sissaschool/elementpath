#!/usr/bin/env python
#
# Copyright (c), 2018-2021, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import unittest
from copy import copy
from unittest.mock import patch
import xml.etree.ElementTree as ElementTree

try:
    import lxml.etree as lxml_etree
except ImportError:
    lxml_etree = None

from elementpath import *


class DummyXsdType:
    name = local_name = None

    def is_matching(self, name, default_namespace): pass
    def is_empty(self): pass
    def is_simple(self): pass
    def has_simple_content(self): pass
    def has_mixed_content(self): pass
    def is_element_only(self): pass
    def is_key(self): pass
    def is_qname(self): pass
    def is_notation(self): pass
    def decode(self, obj, *args, **kwargs): pass
    def validate(self, obj, *args, **kwargs): pass


class XPathContextTest(unittest.TestCase):
    root = ElementTree.XML('<author>Dickens</author>')

    def test_basic_initialization(self):
        self.assertRaises(TypeError, XPathContext, None)

    def test_timezone_argument(self):
        context = XPathContext(self.root)
        self.assertIsNone(context.timezone)
        context = XPathContext(self.root, timezone='Z')
        self.assertIsInstance(context.timezone, datatypes.Timezone)

    def test_repr(self):
        self.assertEqual(repr(XPathContext(self.root)), f"XPathContext(root={self.root})")

    def test_copy(self):
        root = ElementTree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2/></B3></A>')
        context = XPathContext(root)
        self.assertIsInstance(copy(context), XPathContext)
        self.assertIsNot(copy(context), context)

        context = XPathContext(root, axis='children')
        self.assertIsNone(context.copy().axis)
        self.assertEqual(context.copy(clear_axis=False).axis, 'children')

    @unittest.skipIf(lxml_etree is None, 'lxml library is not installed')
    def test_etree_property(self):
        root = ElementTree.XML('<root/>')
        context = XPathContext(root)
        self.assertEqual(context.etree.__name__, 'xml.etree.ElementTree')
        self.assertEqual(context.etree.__name__, 'xml.etree.ElementTree')  # property caching

        root = lxml_etree.XML('<root/>')
        context = XPathContext(root)
        self.assertEqual(context.etree.__name__, 'lxml.etree')
        self.assertEqual(context.etree.__name__, 'lxml.etree')

    def test_parent_map(self):
        root = ElementTree.XML('<A><B1/><B2/></A>')
        context = XPathContext(root)
        self.assertEqual(context.parent_map, {root[0]: root, root[1]: root})

        with patch.object(DummyXsdType(), 'is_element_only', return_value=True) as xsd_type:
            context = XPathContext(root, item=root)
            context.root.xsd_type = xsd_type
            self.assertEqual(context.parent_map, {root[0]: root, root[1]: root})

        root = ElementTree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2/></B3></A>')

        context = XPathContext(root)
        result = {
            root[0]: root, root[0][0]: root[0], root[1]: root,
            root[2]: root, root[2][0]: root[2], root[2][1]: root[2]
        }
        self.assertEqual(context.parent_map, result)
        self.assertEqual(context.parent_map, result)  # Test property caching

        with patch.object(DummyXsdType(), 'is_element_only', return_value=True) as xsd_type:
            context = XPathContext(root, item=root)
            context.root.xsd_type = xsd_type
            self.assertEqual(context.parent_map, result)

    def test_get_parent(self):
        root = ElementTree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2 max="10"/></B3></A>')

        context = XPathContext(root)

        self.assertIsNone(context._parent_map)
        self.assertIsNone(context.get_parent(root))

        self.assertIsInstance(context._parent_map, dict)
        self.assertEqual(context.get_parent(root[0]), root)
        parent_map_id = id(context._parent_map)

        self.assertEqual(context.get_parent(root[1]), root)
        self.assertEqual(context.get_parent(root[2]), root)
        self.assertEqual(context.get_parent(root[2][1]), root[2])

        with patch.object(DummyXsdType(), 'is_empty', return_value=True) as xsd_type:
            elem_node = context.root[2][1]
            elem_node.xsd_type = xsd_type
            self.assertEqual(context.get_parent(elem_node), context.root[2])
            self.assertEqual(id(context._parent_map), parent_map_id)

        # self.assertIsNone(context.get_parent(AttributeNode('max', '10')))
        self.assertEqual(id(context._parent_map), parent_map_id)

        parent_map_id = id(context._parent_map)
        # self.assertIsNone(context.get_parent(AttributeNode('max', '10')))
        self.assertEqual(
            id(context._parent_map), parent_map_id  # LRU cache prevents parent map rebuild
        )

        document = ElementTree.ElementTree(root)
        context = XPathContext(root=document)

        self.assertEqual(context.get_parent(root[1]), root)
        self.assertEqual(context.get_parent(root[2]), root)
        self.assertEqual(context.get_parent(root[2][1]), root[2])

    def test_get_path(self):
        root = ElementTree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2 max="10"/></B3></A>')

        context = XPathContext(root)

        self.assertEqual(context.get_path(None), '')
        self.assertEqual(context.get_path(context.root), '/A')
        self.assertEqual(context.get_path(context.root[0]), '/A/B1')
        self.assertEqual(context.get_path(context.root[0][0]), '/A/B1/C1')
        self.assertEqual(context.get_path(context.root[1]), '/A/B2')
        self.assertEqual(context.get_path(context.root[2]), '/A/B3')
        self.assertEqual(context.get_path(context.root[2][0]), '/A/B3/C1')
        self.assertEqual(context.get_path(context.root[2][1]), '/A/B3/C2')

        # self.assertEqual(context.get_path(AttributeNode('max', '10')), '@max')
        attr = context.root[2][1].attributes[0]
        self.assertEqual(context.get_path(attr), '/A/B3/C2/@max')

        document = ElementTree.ElementTree(root)
        context = XPathContext(root=document)
        self.assertEqual(context.get_path(context.root[0][2][0]), '/A/B3/C1')

        root = ElementTree.XML('<A><B1>10</B1><B2 min="1"/><B3/></A>')
        context = XPathContext(root)
        with patch.object(DummyXsdType(), 'is_simple', return_value=True) as xsd_type:
            elem = context.root[0]
            elem.xsd_type = xsd_type
            self.assertEqual(context.get_path(elem), '/A/B1')

        with patch.object(DummyXsdType(), 'is_simple', return_value=True) as xsd_type:
            context = XPathContext(root)
            attr = context.root[1].attributes[0]
            attr.xsd_type = xsd_type
            self.assertEqual(context.get_path(attr), '/A/B2/@min')

    def test_is_principal_node_kind(self):
        root = ElementTree.XML('<A a1="10" a2="20"/>')
        context = XPathContext(root)
        self.assertTrue(hasattr(context.item, 'tag'))
        self.assertTrue(context.is_principal_node_kind())
        context.item = context.root.attributes[0]
        self.assertFalse(context.is_principal_node_kind())
        context.axis = 'attribute'
        self.assertTrue(context.is_principal_node_kind())

    @unittest.SkipTest
    def test__iter_nodes_static_method(self):
        root = ElementTree.XML('<A>text1\n<B1 a="10">text2</B1><B2/><B3><C1>text3</C1></B3></A>')

        result = [root, TextNode('text1\n', root),
                  root[0], TextNode('text2', root[0]), root[1],
                  root[2], root[2][0], TextNode('text3', root[2][0])]

        self.assertListEqual(list(XPathContext._iter_nodes(root)), result)
        self.assertListEqual(list(XPathContext._iter_nodes(root, with_root=False)), result[1:])

        with patch.multiple(DummyXsdType, has_mixed_content=lambda x: True):
            xsd_type = DummyXsdType()
            typed_root = ElementNode(root, xsd_type=xsd_type)
            self.assertListEqual(list(XPathContext._iter_nodes(typed_root)), result)

        comment = ElementTree.Comment('foo')
        root[1].append(comment)
        self.assertListEqual(list(XPathContext._iter_nodes(root)),
                             result[:5] + [comment] + result[5:])

    def test_iter_product(self):
        context = XPathContext(self.root)

        def sel1(_context):
            yield from range(2)

        def sel2(_context):
            yield from range(3)

        expected = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)]

        self.assertListEqual(list(context.iter_product([sel1, sel2])), expected)
        self.assertEqual(context.variables, {})

        self.assertListEqual(list(context.iter_product([sel1, sel2], [])), expected)
        self.assertEqual(context.variables, {})

        self.assertListEqual(list(context.iter_product([sel1, sel2], ['a', 'b'])), expected)
        self.assertEqual(context.variables, {'a': 1, 'b': 2})

        context.variables = {'a': 0, 'b': 0}
        self.assertListEqual(list(context.iter_product([sel1, sel2], ['a', 'b'])), expected)
        self.assertEqual(context.variables, {'a': 1, 'b': 2})

        context.variables = {'a': 0, 'b': 0}
        self.assertListEqual(list(context.iter_product([sel1, sel2], ['a'])), expected)
        self.assertEqual(context.variables, {'a': 1, 'b': 0})

        context.variables = {'a': 0, 'b': 0}
        self.assertListEqual(list(context.iter_product([sel1, sel2], ['c', 'b'])), expected)
        self.assertEqual(context.variables, {'a': 0, 'b': 2, 'c': 1})

        context.variables = {'a': 0, 'b': 0}
        self.assertListEqual(list(context.iter_product([sel1, sel2], ['b'])), expected)
        self.assertEqual(context.variables, {'a': 0, 'b': 1})

    def test_iter_attributes(self):
        root = ElementTree.XML('<A a1="10" a2="20"/>')
        context = XPathContext(root)
        attributes = context.root.attributes

        self.assertEqual(len(attributes), 2)
        self.assertListEqual(list(context.iter_attributes()), attributes)

        context.item = attributes[0]
        self.assertListEqual(list(context.iter_attributes()), attributes[:1])

        with patch.object(DummyXsdType(), 'has_simple_content', return_value=True) as xsd_type:
            context = XPathContext(root)
            context.root.xsd_type = xsd_type
            self.assertListEqual(list(context.iter_attributes()), context.root.attributes)
            self.assertNotEqual(attributes, context.root.attributes)

        context.item = None
        self.assertListEqual(list(context.iter_attributes()), [])

    def test_iter_children_or_self(self):
        doc = ElementTree.ElementTree(self.root)
        context = XPathContext(doc)
        self.assertIsInstance(context.root, DocumentNode)
        self.assertIsInstance(context.root[0], ElementNode)

        self.assertListEqual(list(context.iter_children_or_self()), [self.root])

        context.item = context.root[0]  # root element
        self.assertListEqual(list(context.iter_children_or_self()),
                             [context.root[0].children[0]])

        context.item = context.root  # document node
        self.assertListEqual(list(context.iter_children_or_self()), [self.root])

    def test_iter_parent(self):
        root = ElementTree.XML('<A a1="10" a2="20"/>')
        context = XPathContext(root, item=None)
        self.assertListEqual(list(context.iter_parent()), [])

        context = XPathContext(root)
        self.assertListEqual(list(context.iter_parent()), [])

        with patch.object(DummyXsdType(), 'has_simple_content', return_value=True) as xsd_type:
            context = XPathContext(root, item=root)
            context.root.xsd_type = xsd_type
            self.assertListEqual(list(context.iter_parent()), [])

        root = ElementTree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2/></B3></A>')
        context = XPathContext(root, item=None)
        self.assertListEqual(list(context.iter_parent()), [])

        context = XPathContext(root, item=root[2][0])
        self.assertListEqual(list(context.iter_parent()), [root[2]])

        with patch.object(DummyXsdType(), 'is_empty', return_value=True) as xsd_type:
            context = XPathContext(root, item=root[2][0])
            context.root[2][0].xsd_type = xsd_type
            self.assertListEqual(list(context.iter_parent()), [root[2]])

    def test_iter_siblings(self):
        root = ElementTree.XML('<A><B1><C1/></B1><B2/><B3><C1/></B3><B4/><B5/></A>')

        context = XPathContext(root)
        self.assertListEqual(list(context.iter_siblings()), [])

        context = XPathContext(root, item=root[2])
        self.assertListEqual(list(context.iter_siblings()), list(root[3:]))

        with patch.object(DummyXsdType(), 'is_element_only', return_value=True) as xsd_type:
            context = XPathContext(root, item=root[2])
            context.root[2].xsd_type = xsd_type
            self.assertListEqual(list(context.iter_siblings()), list(root[3:]))

        context = XPathContext(root, item=root[2])
        self.assertListEqual(list(context.iter_siblings('preceding-sibling')), list(root[:2]))

        with patch.object(DummyXsdType(), 'is_element_only', return_value=True) as xsd_type:
            context = XPathContext(root, item=root[2])
            context.root[2].xsd_type = xsd_type
            self.assertListEqual(list(context.iter_siblings('preceding-sibling')), list(root[:2]))

    @unittest.skipIf(lxml_etree is None, 'lxml library is not installed')
    def test_iter_siblings__issue_44(self):
        root = lxml_etree.XML('<root>text 1<!-- comment -->text 2<!-- comment --> text 3</root>')
        result = select(root, 'node()[1]/following-sibling::node()')
        self.assertListEqual(result, [root[0], 'text 2', root[1], ' text 3'])
        self.assertListEqual(result, root.xpath('node()[1]/following-sibling::node()'))

    def test_iter_descendants(self):
        root = ElementTree.XML('<A a1="10" a2="20"><B1/><B2/></A>')
        context = XPathContext(root)
        attr = context.root.attributes[0]

        self.assertListEqual(list(context.iter_descendants()), [root, root[0], root[1]])

        context.item = attr
        self.assertListEqual(list(context.iter_descendants(axis='descendant')), [])

        context.item = attr
        self.assertListEqual(list(context.iter_descendants()), [attr])

        with patch.object(DummyXsdType(), 'has_mixed_content', return_value=True) as xsd_type:
            context = XPathContext(root, item=root)
            context.root.xsd_type = xsd_type
            self.assertListEqual(list(context.iter_descendants()), [root, root[0], root[1]])

    def test_iter_ancestors(self):
        root = ElementTree.XML('<A a1="10" a2="20"><B1/><B2/></A>')
        context = XPathContext(root)
        attr = context.root.attributes[0]

        self.assertListEqual(list(context.iter_ancestors()), [])

        context.item = attr
        self.assertListEqual(list(context.iter_ancestors()), [context.root])

        self.assertListEqual(list(XPathContext(root, item=root[1]).iter_ancestors()), [root])
        with patch.object(DummyXsdType(), 'has_mixed_content', return_value=True) as xsd_type:
            context = XPathContext(root, item=root[1])
            context.root[1].xsd_type = xsd_type
            self.assertListEqual(list(context.iter_ancestors()), [context.root])

    def test_iter(self):
        root = ElementTree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2/></B3></A>')
        context = XPathContext(root)

        # iter includes also xml namespace nodes
        self.assertListEqual(
            list(e.elem for e in context.iter() if isinstance(e, ElementNode)),
            list(root.iter())
        )

        doc = ElementTree.ElementTree(root)
        context = XPathContext(doc)
        expected = [node for node in context.root.iter()]
        self.assertListEqual(list(context.iter()), expected)

    def test_iter_preceding(self):
        root = ElementTree.XML('<A a1="10" a2="20"/>')
        context = XPathContext(root, item=None)
        self.assertListEqual(list(context.iter_preceding()), [])

        context = XPathContext(root)
        self.assertListEqual(list(context.iter_preceding()), [])

        with patch.object(DummyXsdType(), 'has_simple_content', return_value=True) as xsd_type:
            context = XPathContext(root, item=root)
            context.root.xsd_type = xsd_type
            self.assertListEqual(list(context.iter_preceding()), [])

        context = XPathContext(root, item='text')
        self.assertListEqual(list(context.iter_preceding()), [])

        root = ElementTree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2/></B3></A>')
        context = XPathContext(root, item=root[2][1])
        self.assertListEqual(list(context.iter_preceding()),
                             [root[0], root[0][0], root[1], root[2][0]])

    def test_iter_following(self):
        root = ElementTree.XML('<A a="1"><B1><C1/></B1><B2/><B3><C1/></B3><B4/><B5/></A>')

        context = XPathContext(root)
        self.assertListEqual(list(context.iter_followings()), [])

        context = XPathContext(root)
        context.item = context.root.attributes[0]
        self.assertListEqual(list(context.iter_followings()), [])

        context = XPathContext(root, item=root[2])
        self.assertListEqual(list(context.iter_followings()), list(root[3:]))

        context = XPathContext(root, item=root[1])
        result = [root[2], root[2][0], root[3], root[4]]
        self.assertListEqual(list(context.iter_followings()), result)

        with patch.object(DummyXsdType(), 'has_mixed_content', return_value=True) as xsd_type:
            context = XPathContext(root, item=root[1])
            context.root[1].xsd_type = xsd_type
            self.assertListEqual(list(context.iter_followings()), result)

    def test_iter_results(self):
        root = ElementTree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2 max="10"/></B3></A>')

        results = [root[2], root[0][0]]
        context = XPathContext(root)
        self.assertListEqual(list(context.iter_results(results)), [root[0][0], root[2]])

        with patch.object(DummyXsdType(), 'is_empty', return_value=True) as xsd_type:
            context = XPathContext(root, item=root)
            context.root.xsd_type = xsd_type
            results = [root[2], root[0][0]]
            self.assertListEqual(list(context.iter_results(results)), [root[0][0], root[2]])

            results = [root[2], context.root[0][0]]
            context = XPathContext(root)
            self.assertListEqual(list(context.iter_results(results)),
                                 [context.root[0][0], root[2]])

            context = XPathContext(root, item=root)
            context.root.xsd_type = xsd_type
            results = [root[2], context.root[0][0]]
            self.assertListEqual(list(context.iter_results(results)),
                                 [context.root[0][0], root[2]])

        with patch.object(DummyXsdType(), 'is_simple', return_value=True) as xsd_type:
            context = XPathContext(root)
            attribute = context.root[2][1].attributes[0]
            attribute.xsd_type = xsd_type
            results = [attribute, root[0]]
            self.assertListEqual(list(context.iter_results(results.copy())), results[::-1])

            context = XPathContext(root)
            results = [
                AttributeNode(context, 'max', '11', xsd_type=xsd_type),
                root[0]
            ]
            self.assertListEqual(list(context.iter_results(results.copy())), results[1:])


if __name__ == '__main__':
    unittest.main()
