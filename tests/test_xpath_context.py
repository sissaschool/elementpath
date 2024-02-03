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

from elementpath import XPathContext, DocumentNode, ElementNode, datatypes, \
    select, get_node_tree, TextNode


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

    def test_invalid_initialization(self):
        self.assertRaises(TypeError, XPathContext, None)

        with self.assertRaises(TypeError):
            XPathContext(item=[1])

    def test_timezone_argument(self):
        context = XPathContext(self.root)
        self.assertIsNone(context.timezone)
        context = XPathContext(self.root, timezone='Z')
        self.assertIsInstance(context.timezone, datatypes.Timezone)

    def test_repr(self):
        self.assertEqual(repr(XPathContext(self.root)), f"XPathContext(root={self.root})")
        self.assertEqual(repr(XPathContext(item=self.root)), f"XPathContext(item={self.root})")
        self.assertEqual(repr(XPathContext(item=9.0)), "XPathContext(item=9.0)")

    def test_copy(self):
        root = ElementTree.XML('<A><B1><C1/></B1><B2/><B3><C1/><C2/></B3></A>')
        context = XPathContext(root)
        self.assertIsInstance(copy(context), XPathContext)
        self.assertIsNot(copy(context), context)

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

    def test_context_root_type(self):
        root = ElementTree.XML('<root/>')
        context = XPathContext(root)
        self.assertTrue(context.is_document())
        self.assertIsInstance(context.root, ElementNode)
        self.assertIsInstance(context.document, DocumentNode)
        self.assertFalse(context.is_fragment())
        self.assertFalse(context.is_rooted_subtree())

        root = ElementTree.XML('<root/>')
        context = XPathContext(root, fragment=True)
        self.assertFalse(context.is_document())
        self.assertIsInstance(context.root, ElementNode)
        self.assertIsNone(context.document)
        self.assertIsNone(context.root.parent)
        self.assertTrue(context.is_fragment())
        self.assertFalse(context.is_rooted_subtree())

        root = ElementTree.XML('<root><child/></root>')
        context = XPathContext(root[0], fragment=True)

        self.assertFalse(context.is_document())
        self.assertIsInstance(context.root, ElementNode)
        self.assertIsNone(context.root.parent)
        self.assertIsNone(context.document)
        self.assertTrue(context.is_fragment())
        self.assertFalse(context.is_rooted_subtree())

    def test_no_root(self):
        with self.assertRaises(TypeError) as ctx:
            XPathContext()
        self.assertEqual(str(ctx.exception),
                         "Missing both the root node and the context item!")

        context = XPathContext(item=7)
        self.assertIsNone(context.root)
        self.assertEqual(context.item, 7)

        self.assertListEqual(list(context.iter_self()), [7])
        self.assertListEqual(list(context.iter_children_or_self()), [])
        self.assertListEqual(list(context.iter_attributes()), [])
        self.assertListEqual(list(context.iter_descendants()), [])
        self.assertListEqual(list(context.iter_parent()), [])
        self.assertListEqual(list(context.iter_preceding()), [])
        self.assertListEqual(list(context.iter_followings()), [])
        self.assertListEqual(list(context.iter_ancestors()), [])
        self.assertEqual(context.item, 7)

        root = ElementTree.XML('<root><child1/><child2/></root>')
        root_node = get_node_tree(root)
        context = XPathContext(item=root_node)
        self.assertEqual(context.item, root_node)

        self.assertListEqual(list(context.iter_self()), [root_node])
        self.assertListEqual(list(context.iter_children_or_self()), root_node[:])
        self.assertListEqual(list(context.iter_attributes()), [])
        self.assertListEqual(list(context.iter_descendants()),
                             [root_node, root_node[0], root_node[1]])
        self.assertListEqual(list(context.iter_parent()), [])
        self.assertListEqual(list(context.iter_preceding()), [])
        self.assertListEqual(list(context.iter_followings()), [])
        self.assertListEqual(list(context.iter_ancestors()), [])
        self.assertEqual(context.item, root_node)

        context = XPathContext(item=root_node[0])
        self.assertEqual(context.item, root_node[0])

        self.assertListEqual(list(context.iter_self()), [root_node[0]])
        self.assertListEqual(list(context.iter_children_or_self()), [])
        self.assertListEqual(list(context.iter_attributes()), [])
        self.assertListEqual(list(context.iter_descendants()), [root_node[0]])
        self.assertListEqual(list(context.iter_parent()), [root_node])
        self.assertListEqual(list(context.iter_preceding()), [])
        self.assertListEqual(list(context.iter_followings()), [root_node[1]])
        self.assertListEqual(list(context.iter_ancestors()), [root_node])
        self.assertEqual(context.item, root_node[0])

        context = XPathContext(item=root_node[1])
        self.assertEqual(context.item, root_node[1])

        self.assertListEqual(list(context.iter_self()), [root_node[1]])
        self.assertListEqual(list(context.iter_children_or_self()), [])
        self.assertListEqual(list(context.iter_attributes()), [])
        self.assertListEqual(list(context.iter_descendants()), [root_node[1]])
        self.assertListEqual(list(context.iter_parent()), [root_node])
        self.assertListEqual(list(context.iter_preceding()), [root_node[0]])
        self.assertListEqual(list(context.iter_followings()), [])
        self.assertListEqual(list(context.iter_ancestors()), [root_node])
        self.assertEqual(context.item, root_node[1])

    def test_default_collection(self):
        node = TextNode('hello world!')

        context = XPathContext(self.root, default_collection=1)
        self.assertListEqual(context.default_collection, [1])
        context = XPathContext(self.root, default_collection=[node])
        self.assertListEqual(context.default_collection, [node])

    def test_is_principal_node_kind(self):
        root = ElementTree.XML('<A a1="10" a2="20"/>')
        context = XPathContext(root)
        self.assertTrue(hasattr(context.item.elem, 'tag'))
        self.assertTrue(context.is_principal_node_kind())
        context.item = context.root.attributes[0]
        self.assertFalse(context.is_principal_node_kind())
        context.axis = 'attribute'
        self.assertTrue(context.is_principal_node_kind())

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

        self.assertListEqual(list(e.elem for e in context.iter_children_or_self()), [self.root])

        context.item = context.root[0]  # root element
        self.assertListEqual(list(context.iter_children_or_self()),
                             [context.root[0].children[0]])

        context.item = context.root  # document node
        self.assertListEqual(list(e.elem for e in context.iter_children_or_self()), [self.root])

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
        self.assertListEqual(list(e.elem for e in context.iter_parent()), [root[2]])

        with patch.object(DummyXsdType(), 'is_empty', return_value=True) as xsd_type:
            context = XPathContext(root, item=root[2][0])
            context.root[2][0].xsd_type = xsd_type
            self.assertListEqual(list(e.elem for e in context.iter_parent()), [root[2]])

    def test_iter_siblings(self):
        root = ElementTree.XML('<A><B1><C1/></B1><B2/><B3><C1/></B3><B4/><B5/></A>')

        context = XPathContext(root)
        self.assertListEqual(list(context.iter_siblings()), [])

        context = XPathContext(root, item=root[2])
        self.assertListEqual(list(e.elem for e in context.iter_siblings()), list(root[3:]))

        with patch.object(DummyXsdType(), 'is_element_only', return_value=True) as xsd_type:
            context = XPathContext(root, item=root[2])
            context.root[2].xsd_type = xsd_type
            self.assertListEqual(list(e.elem for e in context.iter_siblings()), list(root[3:]))

        context = XPathContext(root, item=root[2])
        self.assertListEqual(
            list(e.elem for e in context.iter_siblings('preceding-sibling')), list(root[:2])
        )

        with patch.object(DummyXsdType(), 'is_element_only', return_value=True) as xsd_type:
            context = XPathContext(root, item=root[2])
            context.root[2].xsd_type = xsd_type
            self.assertListEqual(
                list(e.elem for e in context.iter_siblings('preceding-sibling')), list(root[:2])
            )

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

        self.assertListEqual(list(e.elem for e in context.iter_descendants()),
                             [root, root[0], root[1]])

        context.item = attr
        self.assertListEqual(list(context.iter_descendants(axis='descendant')), [])

        context.item = attr
        self.assertListEqual(list(context.iter_descendants()), [attr])

        with patch.object(DummyXsdType(), 'has_mixed_content', return_value=True) as xsd_type:
            context = XPathContext(root, item=root)
            context.root.xsd_type = xsd_type
            self.assertListEqual(
                list(e.elem for e in context.iter_descendants()), [root, root[0], root[1]]
            )

    def test_iter_ancestors(self):
        root = ElementTree.XML('<A a1="10" a2="20"><B1/><B2/></A>')
        context = XPathContext(root)
        attr = context.root.attributes[0]

        self.assertListEqual(list(context.iter_ancestors()), [])

        context.item = attr
        self.assertListEqual(list(context.iter_ancestors()), [context.root])

        result = list(e.elem for e in XPathContext(root, item=root[1]).iter_ancestors())
        self.assertListEqual(result, [root])
        with patch.object(DummyXsdType(), 'has_mixed_content', return_value=True) as xsd_type:
            context = XPathContext(root, item=root[1])
            context.root[1].xsd_type = xsd_type
            self.assertListEqual(list(context.iter_ancestors()), [context.root])

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
        self.assertListEqual(list(e.elem for e in context.iter_preceding()),
                             [root[0], root[0][0], root[1], root[2][0]])

    def test_iter_following(self):
        root = ElementTree.XML('<A a="1"><B1><C1/></B1><B2/><B3><C1/></B3><B4/><B5/></A>')

        context = XPathContext(root)
        self.assertListEqual(list(context.iter_followings()), [])

        context = XPathContext(root)
        context.item = context.root.attributes[0]
        self.assertListEqual(list(context.iter_followings()), [])

        context = XPathContext(root, item=root[2])
        self.assertListEqual(list(e.elem for e in context.iter_followings()), list(root[3:]))

        context = XPathContext(root, item=root[1])
        result = [root[2], root[2][0], root[3], root[4]]
        self.assertListEqual(list(e.elem for e in context.iter_followings()), result)

        with patch.object(DummyXsdType(), 'has_mixed_content', return_value=True) as xsd_type:
            context = XPathContext(root, item=root[1])
            context.root[1].xsd_type = xsd_type
            self.assertListEqual(list(e.elem for e in context.iter_followings()), result)


if __name__ == '__main__':
    unittest.main()
