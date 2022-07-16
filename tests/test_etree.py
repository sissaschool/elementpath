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
import platform
import importlib
import io
from pathlib import Path

try:
    import lxml.etree as lxml_etree
except ImportError:
    lxml_etree = None

from elementpath.etree import ElementTree, PyElementTree, \
    SafeXMLParser, etree_tostring, is_etree_document


class TestElementTree(unittest.TestCase):

    @unittest.skipUnless(platform.python_implementation() == 'CPython', "requires CPython")
    def test_imported_modules(self):
        self.assertIs(importlib.import_module('xml.etree.ElementTree'), ElementTree)
        self.assertIs(importlib.import_module('xml.etree').ElementTree, ElementTree)
        self.assertIsNot(ElementTree.Element, ElementTree._Element_Py,
                         msg="cElementTree is not available!")

    def test_element_string_serialization(self):
        self.assertRaises(TypeError, etree_tostring, '<element/>')

        elem = ElementTree.Element('element')
        self.assertEqual(etree_tostring(elem), '<element />')
        self.assertEqual(etree_tostring(elem, xml_declaration=True), '<element />')

        self.assertEqual(etree_tostring(elem, encoding='us-ascii'), b'<element />')
        self.assertEqual(etree_tostring(elem, encoding='us-ascii', indent='    '),
                         b'    <element />')
        self.assertEqual(etree_tostring(elem, encoding='us-ascii', xml_declaration=True),
                         b'<?xml version="1.0" encoding="us-ascii"?>\n<element />')

        self.assertEqual(etree_tostring(elem, encoding='ascii'),
                         b"<?xml version='1.0' encoding='ascii'?>\n<element />")
        self.assertEqual(etree_tostring(elem, encoding='ascii', xml_declaration=False),
                         b'<element />')
        self.assertEqual(etree_tostring(elem, encoding='utf-8'), b'<element />')
        self.assertEqual(etree_tostring(elem, encoding='utf-8', xml_declaration=True),
                         b'<?xml version="1.0" encoding="utf-8"?>\n<element />')

        self.assertEqual(etree_tostring(elem, encoding='iso-8859-1'),
                         b"<?xml version='1.0' encoding='iso-8859-1'?>\n<element />")
        self.assertEqual(etree_tostring(elem, encoding='iso-8859-1', xml_declaration=False),
                         b"<element />")

        self.assertEqual(etree_tostring(elem, method='html'), '<element></element>')
        self.assertEqual(etree_tostring(elem, method='text'), '')

        root = ElementTree.XML('<root>\n'
                               '  text1\n'
                               '  <elem>text2</elem>\n'
                               '</root>')
        self.assertEqual(etree_tostring(root, method='text'), '\n  text1\n  text2')

    def test_py_element_string_serialization(self):
        elem = PyElementTree.Element('element')
        self.assertEqual(etree_tostring(elem), '<element />')
        self.assertEqual(etree_tostring(elem, xml_declaration=True), '<element />')

        self.assertEqual(etree_tostring(elem, encoding='us-ascii'), b'<element />')
        self.assertEqual(etree_tostring(elem, encoding='us-ascii', xml_declaration=True),
                         b'<?xml version="1.0" encoding="us-ascii"?>\n<element />')

        self.assertEqual(etree_tostring(elem, encoding='ascii'),
                         b"<?xml version='1.0' encoding='ascii'?>\n<element />")
        self.assertEqual(etree_tostring(elem, encoding='ascii', xml_declaration=False),
                         b'<element />')
        self.assertEqual(etree_tostring(elem, encoding='utf-8'), b'<element />')
        self.assertEqual(etree_tostring(elem, encoding='utf-8', xml_declaration=True),
                         b'<?xml version="1.0" encoding="utf-8"?>\n<element />')

        self.assertEqual(etree_tostring(elem, encoding='iso-8859-1'),
                         b"<?xml version='1.0' encoding='iso-8859-1'?>\n<element />")
        self.assertEqual(etree_tostring(elem, encoding='iso-8859-1', xml_declaration=False),
                         b"<element />")

        self.assertEqual(etree_tostring(elem, method='html'), '<element></element>')
        self.assertEqual(etree_tostring(elem, method='text'), '')

        root = PyElementTree.XML('<root>\n'
                                 '  text1\n'
                                 '  <elem>text2</elem>\n'
                                 '</root>')
        self.assertEqual(etree_tostring(root, method='text'), '\n  text1\n  text2')

    @unittest.skipIf(lxml_etree is None, 'lxml is not installed ...')
    def test_lxml_element_string_serialization(self):
        elem = lxml_etree.Element('element')
        self.assertEqual(etree_tostring(elem), '<element/>')
        self.assertEqual(etree_tostring(elem, xml_declaration=True), '<element/>')

        self.assertEqual(etree_tostring(elem, encoding='us-ascii'), b'<element/>')
        self.assertEqual(etree_tostring(elem, encoding='us-ascii', xml_declaration=True),
                         b'<?xml version="1.0" encoding="us-ascii"?>\n<element/>')

        self.assertEqual(etree_tostring(elem, encoding='ascii'), b'<element/>')
        self.assertEqual(etree_tostring(elem, encoding='ascii', xml_declaration=True),
                         b'<?xml version="1.0" encoding="ascii"?>\n<element/>')

        self.assertEqual(etree_tostring(elem, encoding='utf-8'), b'<element/>')
        self.assertEqual(etree_tostring(elem, encoding='utf-8', xml_declaration=True),
                         b'<?xml version="1.0" encoding="utf-8"?>\n<element/>')

        self.assertEqual(etree_tostring(elem, encoding='iso-8859-1'),
                         b"<?xml version='1.0' encoding='iso-8859-1'?>\n<element/>")
        self.assertEqual(etree_tostring(elem, encoding='iso-8859-1', xml_declaration=False),
                         b"<element/>")

        self.assertEqual(etree_tostring(elem, method='html'), '<element></element>')
        self.assertEqual(etree_tostring(elem, method='text'), '')

        root = lxml_etree.XML('<root>\n'
                              '  text1\n'
                              '  <elem>text2</elem>\n'
                              '</root>')
        self.assertEqual(etree_tostring(root, method='text'), '\n  text1\n  text2')

    def test_defuse_xml_entities(self):
        xml_file = Path(__file__).parent.joinpath('resources/with_entity.xml')

        elem = ElementTree.parse(str(xml_file)).getroot()
        self.assertEqual(elem.text, 'abc')

        parser = SafeXMLParser(target=PyElementTree.TreeBuilder())
        with self.assertRaises(PyElementTree.ParseError) as ctx:
            ElementTree.parse(xml_file, parser=parser)
        self.assertEqual("Entities are forbidden (entity_name='e')", str(ctx.exception))

    def test_defuse_xml_external_entities(self):
        xml_file = Path(__file__).parent.joinpath('resources/external_entity.xml')

        with self.assertRaises(ElementTree.ParseError) as ctx:
            ElementTree.parse(str(xml_file))
        self.assertIn("undefined entity &ee", str(ctx.exception))

        parser = SafeXMLParser(target=PyElementTree.TreeBuilder())
        with self.assertRaises(PyElementTree.ParseError) as ctx:
            ElementTree.parse(str(xml_file), parser=parser)
        self.assertEqual("Entities are forbidden (entity_name='ee')", str(ctx.exception))

    def test_defuse_xml_unused_external_entities(self):
        xml_file = str(Path(__file__).parent.joinpath('resources/unused_external_entity.xml'))

        elem = ElementTree.parse(xml_file).getroot()
        self.assertEqual(elem.text, 'abc')

        parser = SafeXMLParser(target=PyElementTree.TreeBuilder())
        with self.assertRaises(PyElementTree.ParseError) as ctx:
            ElementTree.parse(xml_file, parser=parser)
        self.assertEqual("Entities are forbidden (entity_name='ee')", str(ctx.exception))

    def test_defuse_xml_unparsed_entities(self):
        xml_file = Path(__file__).parent.joinpath('resources/unparsed_entity.xml')

        parser = SafeXMLParser(target=PyElementTree.TreeBuilder())
        with self.assertRaises(PyElementTree.ParseError) as ctx:
            ElementTree.parse(str(xml_file), parser=parser)
        self.assertEqual("Unparsed entities are forbidden (entity_name='logo_file')",
                         str(ctx.exception))

    def test_defuse_xml_unused_unparsed_entities(self):
        xml_file = Path(__file__).parent.joinpath('resources/unused_unparsed_entity.xml')

        elem = ElementTree.parse(str(xml_file)).getroot()
        self.assertIsNone(elem.text)

        parser = SafeXMLParser(target=PyElementTree.TreeBuilder())
        with self.assertRaises(PyElementTree.ParseError) as ctx:
            ElementTree.parse(str(xml_file), parser=parser)
        self.assertEqual("Unparsed entities are forbidden (entity_name='logo_file')",
                         str(ctx.exception))

    def test_is_etree_document_function(self):
        document = ElementTree.parse(io.StringIO('<A/>'))
        self.assertTrue(is_etree_document(document))
        self.assertFalse(is_etree_document(ElementTree.XML('<A/>')))


if __name__ == '__main__':
    header_template = "ElementTree tests for elementpath with Python {} on {}"
    header = header_template.format(platform.python_version(), platform.platform())
    print('{0}\n{1}\n{0}'.format("*" * len(header), header))

    unittest.main()
