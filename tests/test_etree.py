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
import sys
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
    SafeXMLParser, defuse_xml, etree_tostring, is_etree_document, \
    is_lxml_etree_element, is_lxml_etree_document, etree_deep_equal, \
    etree_iter_paths


XML_WITH_NAMESPACES = '<pfa:root xmlns:pfa="http://xpath.test/nsa">\n' \
                      '  <pfb:elem xmlns:pfb="http://xpath.test/nsb"/>\n' \
                      '</pfa:root>'


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

        elem.text = '\t'
        self.assertEqual(etree_tostring(elem), '<element>    </element>')
        self.assertEqual(etree_tostring(elem, spaces_for_tab=2), '<element>  </element>')
        self.assertEqual(etree_tostring(elem, spaces_for_tab=0), '<element></element>')
        self.assertEqual(etree_tostring(elem, spaces_for_tab=None), '<element>\t</element>')

        elem.text = '\n\n'
        self.assertEqual(etree_tostring(elem), '<element>\n\n</element>')
        self.assertEqual(etree_tostring(elem, indent='  '), '  <element>\n\n  </element>')

        elem.text = '\nfoo\n'
        self.assertEqual(etree_tostring(elem), '<element>\nfoo\n</element>')
        self.assertEqual(etree_tostring(elem, indent=' '), ' <element>\n foo\n </element>')

        elem.text = None

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
        self.assertEqual(etree_tostring(root, max_lines=1), '<root>\n  ...\n  ...\n</root>')

        root = ElementTree.XML(XML_WITH_NAMESPACES)
        result = etree_tostring(root)
        self.assertNotEqual(result, XML_WITH_NAMESPACES)
        self.assertNotIn('pxa', result)
        self.assertNotIn('pxa', result)
        self.assertRegex(result, r'xmlns:ns\d="http://xpath.test/nsa')
        self.assertRegex(result, r'xmlns:ns\d="http://xpath.test/nsb')

        namespaces = {
            'pxa': "http://xpath.test/nsa",
            'pxb': "http://xpath.test/nsb"
        }
        expected = '<pxa:root xmlns:pxa="http://xpath.test/nsa" ' \
                   'xmlns:pxb="http://xpath.test/nsb">\n' \
                   '  <pxb:elem />\n' \
                   '</pxa:root>'
        self.assertEqual(etree_tostring(root, namespaces), expected)

        namespaces = {
            '': "http://xpath.test/nsa",
            'pxa': "http://xpath.test/nsa",
            'pxb': "http://xpath.test/nsb"
        }
        self.assertEqual(etree_tostring(root, namespaces), expected)

        namespaces = {
            '': "http://xpath.test/nsa",
            'pxb': "http://xpath.test/nsb"
        }
        expected = '<root xmlns="http://xpath.test/nsa" ' \
                   'xmlns:pxb="http://xpath.test/nsb">\n' \
                   '  <pxb:elem />\n' \
                   '</root>'
        self.assertEqual(etree_tostring(root, namespaces), expected)

    def test_py_element_string_serialization(self):
        elem = PyElementTree.Element('element')
        self.assertEqual(etree_tostring(elem), '<element />')
        self.assertEqual(etree_tostring(elem, xml_declaration=True), '<element />')

        self.assertEqual(etree_tostring(elem, encoding='us-ascii'), b'<element />')
        self.assertEqual(etree_tostring(elem, encoding='us-ascii', indent='    '),
                         b'    <element />')

        elem.text = '\t'
        self.assertEqual(etree_tostring(elem), '<element>    </element>')
        self.assertEqual(etree_tostring(elem, spaces_for_tab=2), '<element>  </element>')
        self.assertEqual(etree_tostring(elem, spaces_for_tab=0), '<element></element>')
        self.assertEqual(etree_tostring(elem, spaces_for_tab=None), '<element>\t</element>')
        elem.text = None

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

        root = PyElementTree.XML(XML_WITH_NAMESPACES)
        result = etree_tostring(root)
        self.assertNotEqual(result, XML_WITH_NAMESPACES)
        self.assertNotIn('pxa', result)
        self.assertNotIn('pxa', result)
        self.assertRegex(result, r'xmlns:ns\d="http://xpath.test/nsa')
        self.assertRegex(result, r'xmlns:ns\d="http://xpath.test/nsb')

        namespaces = {
            'pxa': "http://xpath.test/nsa",
            'pxb': "http://xpath.test/nsb"
        }
        expected = '<pxa:root xmlns:pxa="http://xpath.test/nsa" ' \
                   'xmlns:pxb="http://xpath.test/nsb">\n' \
                   '  <pxb:elem />\n' \
                   '</pxa:root>'
        self.assertEqual(etree_tostring(root, namespaces), expected)

    @unittest.skipIf(lxml_etree is None, 'lxml is not installed ...')
    def test_lxml_element_string_serialization(self):
        elem = lxml_etree.Element('element')
        self.assertEqual(etree_tostring(elem), '<element/>')
        self.assertEqual(etree_tostring(elem, xml_declaration=True), '<element/>')

        self.assertEqual(etree_tostring(elem, encoding='us-ascii'), b'<element/>')
        self.assertEqual(etree_tostring(elem, encoding='us-ascii', indent='    '),
                         b'    <element/>')

        elem.text = '\t'
        self.assertEqual(etree_tostring(elem), '<element>    </element>')
        self.assertEqual(etree_tostring(elem, spaces_for_tab=2), '<element>  </element>')
        self.assertEqual(etree_tostring(elem, spaces_for_tab=0), '<element></element>')
        self.assertEqual(etree_tostring(elem, spaces_for_tab=None), '<element>\t</element>')
        elem.text = None

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

        root = lxml_etree.XML(XML_WITH_NAMESPACES)
        self.assertEqual(etree_tostring(root), XML_WITH_NAMESPACES)

        namespaces = {
            'tns0': "http://xpath.test/nsa",
            'tns1': "http://xpath.test/nsb"
        }
        self.assertEqual(etree_tostring(root, namespaces), XML_WITH_NAMESPACES)

        for prefix, uri in namespaces.items():
            lxml_etree.register_namespace(prefix, uri)
        self.assertEqual(etree_tostring(root), XML_WITH_NAMESPACES)

    def test_defuse_xml_entities(self):
        xml_file = Path(__file__).parent.joinpath('resources/with_entity.xml')

        elem = ElementTree.parse(str(xml_file)).getroot()
        self.assertEqual(elem.text, 'abc')

        parser = SafeXMLParser(target=PyElementTree.TreeBuilder())
        with self.assertRaises(PyElementTree.ParseError) as ctx:
            ElementTree.parse(xml_file, parser=parser)
        self.assertEqual("Entities are forbidden (entity_name='e')", str(ctx.exception))

        with self.assertRaises(PyElementTree.ParseError) as ctx:
            with xml_file.open() as fp:
                defuse_xml(fp.read())
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

        with self.assertRaises(PyElementTree.ParseError) as ctx:
            with xml_file.open() as fp:
                defuse_xml(fp.read())
        self.assertEqual("Entities are forbidden (entity_name='ee')", str(ctx.exception))

    def test_defuse_xml_unused_external_entities(self):
        xml_file = str(Path(__file__).parent.joinpath('resources/unused_external_entity.xml'))

        elem = ElementTree.parse(xml_file).getroot()
        self.assertEqual(elem.text, 'abc')

        parser = SafeXMLParser(target=PyElementTree.TreeBuilder())
        with self.assertRaises(PyElementTree.ParseError) as ctx:
            ElementTree.parse(xml_file, parser=parser)
        self.assertEqual("Entities are forbidden (entity_name='ee')", str(ctx.exception))

        with self.assertRaises(PyElementTree.ParseError) as ctx:
            with open(xml_file) as fp:
                defuse_xml(fp.read())
        self.assertEqual("Entities are forbidden (entity_name='ee')", str(ctx.exception))

    def test_defuse_xml_unparsed_entities(self):
        xml_file = Path(__file__).parent.joinpath('resources/unparsed_entity.xml')

        parser = SafeXMLParser(target=PyElementTree.TreeBuilder())
        with self.assertRaises(PyElementTree.ParseError) as ctx:
            ElementTree.parse(str(xml_file), parser=parser)
        self.assertEqual("Unparsed entities are forbidden (entity_name='logo_file')",
                         str(ctx.exception))

        with self.assertRaises(PyElementTree.ParseError) as ctx:
            with xml_file.open() as fp:
                defuse_xml(fp.read())
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

        with self.assertRaises(PyElementTree.ParseError) as ctx:
            with xml_file.open() as fp:
                defuse_xml(fp.read())
        self.assertEqual("Unparsed entities are forbidden (entity_name='logo_file')",
                         str(ctx.exception))

    def test_is_etree_document_function(self):
        document = ElementTree.parse(io.StringIO('<A/>'))
        self.assertTrue(is_etree_document(document))
        self.assertFalse(is_etree_document(ElementTree.XML('<A/>')))

    def test_is_lxml_etree_document_function(self):
        document = ElementTree.parse(io.StringIO('<A/>'))
        self.assertFalse(is_lxml_etree_document(document))
        if lxml_etree is not None:
            document = lxml_etree.parse(io.StringIO('<A/>'))
            self.assertTrue(is_lxml_etree_document(document))
            self.assertFalse(is_lxml_etree_document(lxml_etree.XML('<A/>')))

    def test_is_lxml_etree_element_function(self):
        self.assertFalse(is_lxml_etree_element(ElementTree.XML('<A/>')))
        if lxml_etree is not None:
            self.assertTrue(is_lxml_etree_element(lxml_etree.XML('<A/>')))

    def test_etree_deep_equal_function(self):
        e1 = ElementTree.XML('<root a="foo"/>')
        e2 = ElementTree.XML('<root a="foo"/>')
        self.assertTrue(etree_deep_equal(e1, e2))

        e2 = ElementTree.XML('<ROOT a="foo"/>')
        self.assertFalse(etree_deep_equal(e1, e2))

        e2 = ElementTree.XML('<root a="bar"/>')
        self.assertFalse(etree_deep_equal(e1, e2))

        e2 = ElementTree.XML('<root a="foo">bar</root>')
        self.assertFalse(etree_deep_equal(e1, e2))

    def test_etree_iter_paths_function(self):
        root = ElementTree.XML('<root><child/></root>')
        result = list(etree_iter_paths(root))
        self.assertListEqual(
            result, [(root, '.'), (root[0], './Q{}child[1]')]
        )

        root = ElementTree.XML('<root><tns:child xmlns:tns="http://xpath.test/ns"/></root>')
        result = list(etree_iter_paths(root))
        self.assertListEqual(
            result, [(root, '.'), (root[0], './Q{http://xpath.test/ns}child[1]')]
        )

        if sys.version_info >= (3, 8):
            parser = ElementTree.XMLParser(
                target=ElementTree.TreeBuilder(insert_comments=True)
            )
            root = ElementTree.XML('<root><!-- comment --></root>', parser)
            result = list(etree_iter_paths(root))
            self.assertListEqual(
                result, [(root, '.'), (root[0], './comment()[1]')]
            )
            parser = ElementTree.XMLParser(
                target=ElementTree.TreeBuilder(insert_pis=True)
            )
            root = ElementTree.XML(
                '<root><?xml-stylesheet type="text/xsl" href="style.xsl"?></root>', parser
            )
            result = list(etree_iter_paths(root))
            self.assertListEqual(
                result, [(root, '.'), (root[0], './processing-instruction(xml-stylesheet)[1]')]
            )

        if lxml_etree is not None:
            root = lxml_etree.XML('<root><!-- comment --></root>')
            result = list(etree_iter_paths(root))
            self.assertListEqual(
                result, [(root, '.'), (root[0], './comment()[1]')]
            )

            root = lxml_etree.XML(
                '<root><?xml-stylesheet type="text/xsl" href="style.xsl"?></root>'
            )
            result = list(etree_iter_paths(root))
            self.assertListEqual(
                result, [(root, '.'), (root[0], './processing-instruction(xml-stylesheet)[1]')]
            )


if __name__ == '__main__':
    header_template = "ElementTree tests for elementpath with Python {} on {}"
    header = header_template.format(platform.python_version(), platform.platform())
    print('{0}\n{1}\n{0}'.format("*" * len(header), header))

    unittest.main()
