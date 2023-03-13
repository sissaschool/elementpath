#!/usr/bin/env python3
#
# Copyright (c), 2018-2021, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Jelte Jansen <github@tjeb.nl>
# @author Davide Brunato <brunato@sissa.it>
#
"""
Test script for running W3C XPath tests on elementpath. This is a
reworking of https://github.com/tjeb/elementpath_w3c_tests project
that uses ElementTree for default and collapses the essential parts
into only one module.
"""
import argparse
import contextlib
import datetime
import decimal
import re
import json
import html
import math
import os
import sys
import traceback

from collections import OrderedDict
from itertools import zip_longest
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree
import lxml.etree

import elementpath
import xmlschema

from elementpath import ElementPathError, XPath2Parser, XPathContext, XPathNode, \
    CommentNode, ProcessingInstructionNode, get_node_tree
from elementpath.namespaces import XML_NAMESPACE, XPATH_FUNCTIONS_NAMESPACE, get_expanded_name
from elementpath.xpath_tokens import XPathFunction, XPathMap, XPathArray
from elementpath.datatypes import AnyAtomicType
from elementpath.sequence_types import is_sequence_type, match_sequence_type
from elementpath.xpath31 import XPath31Parser


PY38_PLUS = sys.version_info > (3, 8)

XML_EXPANDED_PREFIX = f'{{{XML_NAMESPACE}}}'

DEPENDENCY_TYPES = {'spec', 'feature', 'calendar', 'default-language',
                    'format-integer-sequence', 'language', 'limits',
                    'xml-version', 'xsd-version', 'unicode-version',
                    'unicode-normalization-form'}

SKIP_TESTS = {
    'fn-subsequence__cbcl-subsequence-010',
    'fn-subsequence__cbcl-subsequence-011',
    'fn-subsequence__cbcl-subsequence-012',
    'fn-subsequence__cbcl-subsequence-013',
    'fn-subsequence__cbcl-subsequence-014',
    'prod-NameTest__NodeTest004',

    # Unsupported collations
    'fn-compare__compare-010',
    'fn-substring-after__fn-substring-after-24',
    'fn-substring-before__fn-substring-before-24',
    'fn-deep-equal__K-SeqDeepEqualFunc-57',
    'fn-deep-equal__K-SeqDeepEqualFunc-56',

    # Unsupported language
    'fn-format-integer__format-integer-032',
    'fn-format-integer__format-integer-032-fr',
    'fn-format-integer__format-integer-052',
    'fn-format-integer__format-integer-065',

    # Processing-instructions (tests on env "auction")
    'fn-local-name__fn-local-name-78',
    'fn-name__fn-name-28',
    'fn-string__fn-string-28',

    # Require XML 1.1
    'fn-codepoints-to-string__K-CodepointToStringFunc-8a',
    'fn-codepoints-to-string__K-CodepointToStringFunc-11b',
    'fn-codepoints-to-string__K-CodepointToStringFunc-12b',

    # Require unicode version "7.0"
    'fn-lower-case__fn-lower-case-19',
    'fn-upper-case__fn-upper-case-19',
    'fn-matches.re__re00506',
    'fn-matches.re__re00984',

    # Very large number fault (interpreter crashes or float rounding)
    'op-to__RangeExpr-409d',
    'fn-format-number__numberformat60a',
    'fn-format-number__cbcl-fn-format-number-035',

    # For XQuery??
    'fn-deep-equal__K2-SeqDeepEqualFunc-43',  # includes a '!' symbol

    # For XP30+
    'fn-root__K-NodeRootFunc-2',  # includes a XPath 3.0 fn:generate-id()
    'fn-codepoints-to-string__cbcl-codepoints-to-string-021',  # Too long ...
    'fn-unparsed-text__fn-unparsed-text-038',  # Typo in filename
    'fn-unparsed-text-lines__fn-unparsed-text-lines-038',  # Typo in filename
    'fn-serialize__serialize-xml-015b',  # Do not raise, attribute is good
    'fn-parse-xml-fragment__parse-xml-fragment-022-st',  # conflict with parse-xml-fragment-022
    'fn-for-each-pair__fn-for-each-pair-017',  # Requires PI and comments parsing
    'fn-function-lookup__fn-function-lookup-522',  # xs:dateTimeStamp for XSD 1.1 only

    # Unsupported language (German)
    'fn-format-date__format-date-de101',
    'fn-format-date__format-date-de102',
    'fn-format-date__format-date-de103',
    'fn-format-date__format-date-de104',
    'fn-format-date__format-date-de105',
    'fn-format-date__format-date-de106',
    'fn-format-date__format-date-de111',
    'fn-format-date__format-date-de112',
    'fn-format-date__format-date-de113',
    'fn-format-date__format-date-de114',
    'fn-format-date__format-date-de115',
    'fn-format-date__format-date-de116',

    # Unicode FULLY-NORMALIZATION not supported in Python's unicodedata
    'fn-normalize-unicode__cbcl-fn-normalize-unicode-001',
    'fn-normalize-unicode__cbcl-fn-normalize-unicode-006',

    # 'เจมส์' does not match xs:NCName (maybe due to Python re module limitation)
    'prod-CastExpr__K2-SeqExprCast-488',
    'prod-CastExpr__K2-SeqExprCast-504',

    # TODO: unsupported for serialization
    'fn-serialize__serialize-xml-110',    # TODO: ElementNode serialization with params
    'fn-serialize__serialize-html-001b',  # HTML 5
    'fn-serialize__serialize-html-002b',  # HTML 5

    # IMHO incorrect tests
    'fn-resolve-uri__fn-resolve-uri-9',  # URI scheme names are lowercase
    'fn-apply__fn-apply-13',  # Error code should be err:FOAP0001
    'fn-json-doc__json-doc-032',  # 0 is not an instance of xs:double
    'fn-json-doc__json-doc-033',  # 0 (should be -0) is not an instance of xs:double
    'fn-function-lookup__fn-function-lookup-764',  # Error code should be FOQM0001
}

# Tests that can be run only with lxml.etree
LXML_ONLY = {
    # parse of comments or PIs required
    'fn-string__fn-string-30',
    'prod-AxisStep__Axes003-4',
    'prod-AxisStep__Axes006-4',
    'prod-AxisStep__Axes033-4',
    'prod-AxisStep__Axes037-2',
    'prod-AxisStep__Axes046-2',
    'prod-AxisStep__Axes049-2',
    'prod-AxisStep__Axes058-2',
    'prod-AxisStep__Axes058-3',
    'prod-AxisStep__Axes061-1',
    'prod-AxisStep__Axes061-2',
    'prod-AxisStep__Axes064-2',
    'prod-AxisStep__Axes064-3',
    'prod-AxisStep__Axes067-2',
    'prod-AxisStep__Axes067-3',
    'prod-AxisStep__Axes073-1',
    'prod-AxisStep__Axes073-2',
    'prod-AxisStep__Axes076-4',
    'prod-AxisStep__Axes079-4',
    'fn-path__path007',
    'fn-path__path009',
    'fn-generate-id__generate-id-005',
    'fn-parse-xml-fragment__parse-xml-fragment-010',

    # in-scope namespaces required
    'prod-AxisStep__Axes118',
    'prod-AxisStep__Axes120',
    'prod-AxisStep__Axes126',
    'fn-resolve-QName__fn-resolve-qname-26',
    'fn-in-scope-prefixes__fn-in-scope-prefixes-21',
    'fn-in-scope-prefixes__fn-in-scope-prefixes-22',
    'fn-in-scope-prefixes__fn-in-scope-prefixes-24',
    'fn-in-scope-prefixes__fn-in-scope-prefixes-25',
    'fn-in-scope-prefixes__fn-in-scope-prefixes-26',
    'fn-innermost__fn-innermost-017',
    'fn-innermost__fn-innermost-018',
    'fn-innermost__fn-innermost-019',
    'fn-innermost__fn-innermost-020',
    'fn-innermost__fn-innermost-021',
    'fn-outermost__fn-outermost-017',
    'fn-outermost__fn-outermost-018',
    'fn-outermost__fn-outermost-019',
    'fn-outermost__fn-outermost-020',
    'fn-outermost__fn-outermost-021',
    'fn-outermost__fn-outermost-046',
    'fn-local-name__fn-local-name-77',
    'fn-local-name__fn-local-name-79',
    'fn-name__fn-name-27',
    'fn-name__fn-name-29',
    'fn-string__fn-string-27',
    'fn-format-number__numberformat87',
    'fn-format-number__numberformat88',
    'fn-path__path010',
    'fn-path__path011',
    'fn-path__path012',
    'fn-path__path013',
    'fn-function-lookup__fn-function-lookup-262',
    'fn-generate-id__generate-id-007',
    'fn-serialize__serialize-xml-012',
    'prod-EQName__eqname-018',
    'prod-EQName__eqname-023',
    'prod-NamedFunctionRef__function-literal-262',

    # XML declaration
    'fn-serialize__serialize-xml-029b',
    'fn-serialize__serialize-xml-030b',

    # require external ENTITY parsing
    'fn-parse-xml__parse-xml-010',
}

USE_SCHEMA_FOR_JSON = {
    'fn-json-to-xml__json-to-xml-016',
    'fn-json-to-xml__json-to-xml-017',
    'fn-json-to-xml__json-to-xml-037',
    'fn-json-to-xml__json-to-xml-038',
}

xpath_parser = XPath2Parser

ignore_specs = {'XQ10', 'XQ10+', 'XP30', 'XP30+', 'XQ30', 'XQ30+',
                'XP31', 'XP31+', 'XQ31', 'XQ31+', 'XT30+'}

QT3_NAMESPACE = "http://www.w3.org/2010/09/qt-fots-catalog"

namespaces = {'': QT3_NAMESPACE}


@contextlib.contextmanager
def working_directory(dirpath):
    orig_wd = os.getcwd()
    os.chdir(dirpath)
    try:
        yield
    finally:
        os.chdir(orig_wd)


def get_context_result(item):
    if isinstance(item, XPathNode):
        raise TypeError("Unexpected XPath node in external results")
    elif isinstance(item, (list, tuple)):
        return [get_context_result(x) for x in item]
    elif hasattr(item, 'tag'):
        if callable(item.tag):
            if item.tag.__name__ == 'Comment':
                return CommentNode(item)
            else:
                return ProcessingInstructionNode(item)
    elif not hasattr(item, 'getroot'):
        return item

    return get_node_tree(root=item)


def is_equivalent(t1, t2):
    if t1 == t2 or html.unescape(t1) == html.unescape(t2):
        return True

    try:
        if decimal.Decimal(t1) != decimal.Decimal(t2):
            return False
    except (ValueError, decimal.DecimalException):
        return False
    else:
        return True


def etree_is_equal(root1, root2, strict=True):

    for e1, e2 in zip_longest(root1.iter(), root2.iter()):
        if e1 is None or e2 is None:
            return False

        if e1.tail != e2.tail:
            if strict or e1.tail is None or e2.tail is None:
                return False
            if e1.tail.strip() != e2.tail.strip():
                return False

        if callable(e1.tag) ^ callable(e2.tag):
            return False
        elif not callable(e1.tag):
            if e1.tag != e2.tag:
                return False
            if e1.attrib != e2.attrib:
                if strict:
                    return False

                attrib1 = e1.attrib
                attrib2 = e2.attrib
                if len(attrib1) != len(attrib2):
                    attrib1 = {k: v for k, v in attrib1.items()
                               if not k.startswith(XML_EXPANDED_PREFIX)}
                    attrib2 = {k: v for k, v in attrib2.items()
                               if not k.startswith(XML_EXPANDED_PREFIX)}
                    if len(attrib1) != len(attrib2):
                        return False

                for (k1, v1), (k2, v2) in zip(attrib1.items(), attrib2.items()):
                    if not is_equivalent(k1, k2) or not is_equivalent(v1, v2):
                        return False

        if e1.text != e2.text:
            if strict or e1.text is None or e2.text is None:
                return False
            if e1.text.strip() != e2.text.strip():
                if not is_equivalent(e1.text, e2.text):
                    return False
    else:
        return True


class ExecutionError(Exception):
    """Common class for W3C XPath tests execution script."""


class ParseError(ExecutionError):
    """Other error generated by XPath expression parsing and static evaluation."""


class EvaluateError(ExecutionError):
    """Other error generated by XPath token evaluation with dynamic context."""


class Schema(object):
    """Represents an XSD schema used in XML environment settings."""

    def __init__(self, elem):
        assert elem.tag == '{%s}schema' % QT3_NAMESPACE
        self.uri = elem.attrib.get('uri')
        self.file = elem.attrib.get('file')
        try:
            self.description = elem.find('description', namespaces).text
        except AttributeError:
            self.description = ''

        self.filepath = self.file and os.path.abspath(self.file)

    def __repr__(self):
        return '%s(uri=%r, file=%s)' % (self.__class__.__name__, self.uri, self.file)


class Source(object):
    """Represents an XML source file as used in environment settings."""

    namespaces = None

    def __init__(self, elem, use_lxml=False):
        assert elem.tag == '{%s}source' % QT3_NAMESPACE
        self.file = elem.attrib['file']
        self.role = elem.attrib.get('role', '')
        self.uri = elem.attrib.get('uri', self.file)
        if not urlsplit(self.uri).scheme:
            self.uri = Path(self.uri).absolute().as_uri()

        self.key = self.role or self.file

        try:
            self.description = elem.find('description', namespaces).text
        except AttributeError:
            self.description = ''

        if use_lxml:
            iterparse = lxml.etree.iterparse
            parser = lxml.etree.XMLParser(collect_ids=False)
            try:
                self.xml = lxml.etree.parse(self.file, parser=parser)
            except lxml.etree.XMLSyntaxError:
                self.xml = None
        else:
            iterparse = ElementTree.iterparse
            if PY38_PLUS:
                tree_builder = ElementTree.TreeBuilder(insert_comments=True, insert_pis=True)
                parser = ElementTree.XMLParser(target=tree_builder)
            else:
                parser = None

            try:
                self.xml = ElementTree.parse(self.file, parser=parser)
            except ElementTree.ParseError:
                self.xml = None

        try:
            self.namespaces = {}
            dup_index = 1

            for _, (prefix, uri) in iterparse(self.file, events=('start-ns',)):
                if prefix not in self.namespaces:
                    self.namespaces[prefix] = uri
                elif prefix:
                    self.namespaces[f'{prefix}{dup_index}'] = uri
                    dup_index += 1
                else:
                    self.namespaces[f'default{dup_index}'] = uri
                    dup_index += 1
        except (ElementTree.ParseError, lxml.etree.XMLSyntaxError):
            pass

    def __repr__(self):
        return '%s(file=%r)' % (self.__class__.__name__, self.file)


class Resource(object):
    """Represents a remote resource used in environment settings."""

    def __init__(self, elem, use_lxml=False):
        assert elem.tag == '{%s}resource' % QT3_NAMESPACE
        self.uri = elem.attrib['uri']
        self.file = elem.attrib['file']
        self.file_uri = f'file://{os.getcwd()}/{self.file}'
        self.media_type = elem.get('media-type')
        self.encoding = elem.get('encoding')


class Collection(object):
    """Represents a collection of source files as used in XML environment settings."""

    def __init__(self, elem, use_lxml=False):
        assert elem.tag == '{%s}collection' % QT3_NAMESPACE
        self.uri = elem.attrib.get('uri')
        self.query = elem.find('query', namespaces)  # Not used (for XQuery)
        self.sources = [Source(e, use_lxml) for e in elem.iterfind('source', namespaces)]

    def __repr__(self):
        return '%s(uri=%r)' % (self.__class__.__name__, self.uri)


class Environment(object):
    """
    The XML environment definition for a test case.

    :param elem: the XML Element that contains the environment definition.
    :param use_lxml: use lxml.etree for loading XML sources.
    """
    collation = None
    default_collation = False
    collection = None
    schema = None
    static_base_uri = None
    decimal_formats = None

    def __init__(self, elem, use_lxml=False):
        assert elem.tag == '{%s}environment' % QT3_NAMESPACE
        self.name = elem.get('name', 'anonymous')
        self.namespaces = {
            namespace.attrib['prefix']: namespace.attrib['uri']
            for namespace in elem.iterfind('namespace', namespaces)
        }

        self.decimal_formats = {}
        for child in elem.iterfind('decimal-format', namespaces):
            name = child.get('name')
            if name is not None and ':' in name:
                if use_lxml:
                    name = get_expanded_name(name, child.nsmap)
                else:
                    try:
                        name = get_expanded_name(name, self.namespaces)
                    except KeyError:
                        pass

            self.decimal_formats[name] = child.attrib

        child = elem.find('collation', namespaces)
        if child is not None:
            self.collation = child.get('uri')
            self.default_collation = child.get('default') == 'true'

        child = elem.find('collection', namespaces)
        if child is not None:
            self.collection = Collection(child, use_lxml)

        child = elem.find('schema', namespaces)
        if child is not None:
            self.schema = Schema(child)

        child = elem.find('static-base-uri', namespaces)
        if child is not None:
            self.static_base_uri = child.get('uri')

        self.params = [e.attrib for e in elem.iterfind('param', namespaces)]

        self.sources = {}
        for child in elem.iterfind('source', namespaces):
            source = Source(child, use_lxml)
            self.sources[source.key] = source

        self.resources = {}
        for child in elem.iterfind('resource', namespaces):
            resource = Resource(child, use_lxml)
            self.resources[resource.uri] = resource

    def __repr__(self):
        return '%s(name=%r)' % (self.__class__.__name__, self.name)

    def __str__(self):
        children = []
        for prefix, uri in self.namespaces.items():
            children.append('<namespace prefix="{}" uri="{}"/>'.format(prefix, uri))
        if self.schema is not None:
            children.append('<schema uri="{}" file="{}"/>'.format(
                self.schema.uri or '', self.schema.file or ''
            ))
        for role, source in self.sources.items():
            children.append('<source role="{}" uri="{}" file="{}"/>'.format(
                role, source.uri or '', source.file
            ))
        return '<environment name="{}">\n   {}\n</environment>'.format(
            self.name, '\n   '.join(children)
        )

    def get_namespaces(self):
        namespaces_ = self.namespaces.copy()
        for source in self.sources.values():
            if source.namespaces:
                for pfx, uri in source.namespaces.items():
                    if pfx not in namespaces_:
                        namespaces_[pfx] = uri

        return namespaces_


class TestSet(object):
    """
    Represents a test-set as read from the catalog file and the test-set XML file itself.

    :param elem: the XML Element that contains the test-set definitions.
    :param pattern: the regex pattern for selecting test-cases to load.
    :param use_lxml: use lxml.etree for loading environment XML sources.
    :param environments: the global environments.
    """
    def __init__(self, elem, pattern, use_lxml=False, environments=None):
        assert elem.tag == '{%s}test-set' % QT3_NAMESPACE
        self.name = elem.attrib['name']
        self.file = elem.attrib['file']
        self.environments = {} if environments is None else environments.copy()
        self.test_cases = []

        self.specs = []
        self.features = []
        self.xsd_version = None
        self.use_lxml = use_lxml
        self.etree = lxml.etree if use_lxml else ElementTree

        full_path = os.path.abspath(self.file)
        filename = os.path.basename(full_path)
        self.workdir = os.path.dirname(full_path)

        with working_directory(self.workdir):
            xml_root = self.etree.parse(filename).getroot()

            self.description = xml_root.find('description', namespaces).text

            for child in xml_root.findall('dependency', namespaces):
                dep_type = child.attrib['type']
                value = child.attrib['value']
                if dep_type == 'spec':
                    self.specs.extend(value.split(' '))
                elif dep_type == 'feature':
                    if child.get('satisfied', 'true') in ('true', '1'):
                        self.features.append(value)
                elif dep_type == 'xsd-version':
                    self.xsd_version = value
                else:
                    print("unexpected dependency type %s for test-set %r" % (dep_type, self.name))

            for child in xml_root.findall('environment', namespaces):
                environment = Environment(child, use_lxml)
                self.environments[environment.name] = environment

            test_case_template = self.name + '__%s'
            for child in xml_root.findall('test-case', namespaces):
                if pattern.search(test_case_template % child.attrib['name']) is not None:
                    self.test_cases.append(TestCase(child, self, use_lxml))

    def __repr__(self):
        return '%s(name=%r)' % (self.__class__.__name__, self.name)


class TestCase(object):
    """
    Represents a test case as read from a test-set file.

    :param elem: the XML Element that contains the test-case definition.
    :param test_set: the test-set that the test-case belongs to.
    :param use_lxml: use lxml.etree for loading environment XML sources.
    """
    # Single value dependencies
    parser = None
    calendar = None
    default_language = None
    format_integer_sequence = None
    language = None
    limits = None
    unicode_version = None
    unicode_normalization_form = None
    xml_version = None

    def __init__(self, elem, test_set, use_lxml=False):
        assert elem.tag == '{%s}test-case' % QT3_NAMESPACE
        self.test_set = test_set
        self.xsd_version = test_set.xsd_version
        self.features = [feature for feature in test_set.features]

        self.use_lxml = use_lxml
        self.etree = lxml.etree if use_lxml else ElementTree

        self.name = test_set.name + "__" + elem.attrib['name']
        self.description = elem.find('description', namespaces).text
        self.test = elem.find('test', namespaces).text

        result_child = elem.find('result', namespaces).find("*")
        self.result = Result(result_child, test_case=self, use_lxml=use_lxml)

        self.environment_ref = None
        self.environment = None
        self.specs = []

        for child in elem.findall('dependency', namespaces):
            dep_type = child.attrib['type']
            value = child.attrib['value']
            if dep_type == 'spec':
                self.specs.extend(value.split(' '))
            elif dep_type == 'feature':
                if child.get('satisfied') == 'false':
                    try:
                        self.features.remove(value)
                    except ValueError:
                        pass
                else:
                    self.features.append(value)

            elif dep_type in DEPENDENCY_TYPES:
                setattr(self, dep_type.replace('-', '_'), value)
            else:
                print("unexpected dependency type %s for test-case %r" % (dep_type, self.name))

        child = elem.find('environment', namespaces)
        if child is not None:
            if 'ref' in child.attrib:
                self.environment_ref = child.attrib['ref']
            else:
                self.environment = Environment(child, use_lxml)

    def __repr__(self):
        return '%s(name=%r)' % (self.__class__.__name__, self.name)

    def __str__(self):
        children = [
            '<description>{}</description>'.format(self.description or ''),
            '<test>{}</test>'.format(self.test) if self.test else '</test>',
            '<result>\n   {}\n</result>'.format(self.result),
        ]
        if self.environment_ref:
            children.append('<environment ref="{}"/>'.format(self.environment_ref))

        for dep_type in sorted(DEPENDENCY_TYPES):
            if dep_type == 'spec':
                if self.specs:
                    children.extend('<spec value="{}"/>'.format(x) for x in self.specs)
            elif dep_type == 'feature':
                if self.features:
                    children.extend('<feature value="{}"/>'.format(x) for x in self.features)
            else:
                value = getattr(self, dep_type.replace('-', '_'))
                if value is not None:
                    children.append('<{} value="{}"/>'.format(dep_type, value))

        return '<test-case name="{}" test_set_file="{}"/>\n   {}\n</test-case>'.format(
            self.name,
            self.test_set_file,
            '\n   '.join('\n'.join(children).split('\n')),
        )

    @property
    def test_set_file(self):
        return self.test_set.file

    def get_environment(self):
        env_ref = self.environment_ref
        if env_ref:
            try:
                return self.test_set.environments[env_ref]
            except KeyError:
                msg = "Unknown environment %s in test case %s"
                raise ExecutionError(msg % (env_ref, self.name)) from None
        elif self.environment:
            return self.environment

    def run(self, verbose=1):
        if verbose > 4:
            print("\n*** Execute test case {!r} ***".format(self.name))
            print(str(self))
            print()
        return self.result.validate(verbose)

    def run_xpath_test(self, verbose=1, with_context=True, with_xpath_nodes=False):
        """
        Helper function to parse and evaluate tests with elementpath.

        If may_fail is true, raise the exception instead of printing and aborting
        """
        environment = self.get_environment()

        # Create the parser instance (static context)
        if environment is None:
            test_namespaces = static_base_uri = schema_proxy = default_collation = None
        else:
            test_namespaces = environment.get_namespaces()
            static_base_uri = environment.static_base_uri

            default_collation = None
            if environment.collation is not None:
                if environment.default_collation:
                    default_collation = environment.collation

            if environment.schema is None or not environment.schema.filepath:
                if self.name in USE_SCHEMA_FOR_JSON:
                    xsd_path = Path(__file__).parent.joinpath('resources/schema-for-json.xsd')
                    schema = xmlschema.XMLSchema(xsd_path)
                    schema_proxy = schema.xpath_proxy
                else:
                    schema_proxy = None
            else:
                if verbose > 2:
                    print("Schema %r required for test %r" % (environment.schema.file, self.name))

                schema = xmlschema.XMLSchema(environment.schema.filepath)
                schema_proxy = schema.xpath_proxy

        if static_base_uri is None:
            if self.name == "fn-parse-xml__parse-xml-007":
                # workaround: static-base-uri() must return AnyURI('') for this case
                static_base_uri = ''
            else:
                base_uri = os.path.dirname(os.path.abspath(self.test_set_file))
                if os.path.isdir(base_uri):
                    static_base_uri = f'{Path(base_uri).as_uri()}/'

        elif environment and static_base_uri in environment.resources:
            static_base_uri = environment.resources[static_base_uri].file_uri
        elif static_base_uri == 'http://www.w3.org/fots/unparsed-text/':
            static_base_uri = f'file://{os.getcwd()}/fn/unparsed-text/'

        kwargs = dict(
            namespaces=test_namespaces,
            xsd_version=self.xsd_version,
            schema=schema_proxy,
            base_uri=static_base_uri,
            compatibility_mode='xpath-1.0-compatibility' in self.features,
            default_collation=default_collation,
        )
        if environment is not None and xpath_parser.version >= '3.0':
            if environment.decimal_formats:
                kwargs['decimal_formats'] = environment.decimal_formats
            kwargs['defuse_xml'] = False

        self.parser = xpath_parser(**kwargs)

        if self.test is None:
            xpath_expression = None
        else:
            xpath_expression = self.test
            if environment:
                for uri, resource in environment.resources.items():
                    if uri in xpath_expression:
                        xpath_expression = xpath_expression.replace(uri, resource.file_uri)

        try:
            root_node = self.parser.parse(xpath_expression)  # static evaluation
        except Exception as err:
            if isinstance(err, ElementPathError):
                raise
            raise ParseError(err)

        # Create the dynamic context
        if not with_context:
            context = None
        elif environment is None:
            context = XPathContext(
                root=self.etree.XML("<empty/>"),
                namespaces=test_namespaces,
                timezone='Z',
                default_language=self.default_language,
                default_calendar=self.calendar
            )
        else:
            kwargs = {'timezone': 'Z'}
            variables = {}
            documents = {}

            if '.' in environment.sources:
                root = environment.sources['.'].xml
            else:
                root = self.etree.XML("<empty/>")

            if any(k.startswith('$') for k in environment.sources):
                variables.update(
                    (k[1:], v.xml) for k, v in environment.sources.items() if k.startswith('$')
                )

            for param in environment.params:
                name = param['name']
                value = xpath_parser().parse(param['select']).evaluate()
                variables[name] = value

            for source in environment.sources.values():
                documents[source.uri] = source.xml

            if environment.collection is not None:
                uri = environment.collection.uri
                collection = [source.xml for source in environment.collection.sources]
                if uri is not None:
                    kwargs['collections'] = {uri: collection}

                if collection:
                    kwargs['default_collection'] = collection

                if 'non_empty_sequence_collection' in self.features:
                    kwargs['default_resource_collection'] = uri

            if test_namespaces:
                kwargs['namespaces'] = test_namespaces
            if variables:
                kwargs['variables'] = variables
            if documents:
                kwargs['documents'] = documents
            if self.default_language:
                kwargs['default_language'] = self.default_language
            if self.calendar:
                kwargs['default_calendar'] = self.calendar

            context = XPathContext(root=root, **kwargs)

        try:
            if with_xpath_nodes:
                result = root_node.evaluate(context)
            else:
                result = root_node.get_results(context)
        except Exception as err:
            if isinstance(err, ElementPathError):
                raise
            raise EvaluateError(err)

        if verbose > 4:
            print("Result of evaluation: {!r}\n".format(result))
        return result


class Result(object):
    """
    Class for validating the result of a test case. Result instances can
    be nested for multiple validation options. There are several types
    of result validators available:

      * all-of
      * any-of
      * assert
      * assert-count
      * assert-deep-eq
      * assert-empty
      * assert-eq
      * assert-false
      * assert-permutation
      * assert-serialization-error
      * assert-string-value
      * assert-true
      * assert-type
      * assert-xml
      * error
      * not
      * serialization-matches

    :param elem: the XML Element that contains the test-case definition.
    :param test_case: the test-case that the result validator belongs to.
    """
    # Validation helper tokens
    string_token = XPath31Parser().parse('fn:string($result)')
    string_join_token = XPath31Parser().parse('fn:string-join($result, " ")')

    def __init__(self, elem, test_case, use_lxml=False):
        self.test_case = test_case
        self.use_lxml = use_lxml
        self.etree = lxml.etree if use_lxml else ElementTree

        self.type = elem.tag.split('}')[1]
        self.value = elem.text
        self.attrib = {k: v for k, v in elem.attrib.items()}

        if self.value is None and self.type == 'assert-xml':
            self.attrib['file'] = os.path.abspath(self.attrib['file'])
        self.children = [Result(child, test_case) for child in elem.findall('*')]
        self.validate = getattr(self, '%s_validator' % self.type.replace("-", "_"))

    def __repr__(self):
        return '%s(type=%r)' % (self.__class__.__name__, self.type)

    def __str__(self):
        attrib = ' '.join('{}="{}"'.format(k, v) for k, v in self.attrib.items())
        if self.children:
            return '<{0} {1}>{2}{3}\n</{0}>'.format(
                self.type,
                attrib,
                self.value if self.value is not None else '',
                '\n   '.join(str(child) for child in self.children),
            )
        elif self.value is not None:
            return '<{0} {1}>{2}</{0}>'.format(self.type, attrib, self.value)
        else:
            return '<{} {}/>'.format(self.type, attrib)

    def report_failure(self, verbose=1, **results):
        if verbose <= 1:
            return

        print(f'Fail for test case {self.test_case.name!r}')
        print(f'Result failed: {self}')

        if verbose < 4:
            print(f'XPath expression: {self.test_case.test.strip()}')
        else:
            print()
            print(self.test_case)

        if results:
            print()
            print_traceback = False
            max_key = max(len(k) for k in results)
            for k, v in results.items():
                if isinstance(v, Exception):
                    v = "Unexpected {!r}: {}".format(type(v), v)
                    if verbose >= 3:
                        print_traceback = True

                print('  {}: {}{!r}'.format(k, ' ' * (max_key - len(k)), v))

            if print_traceback:
                print()
                traceback.print_exc()

        print()

    def all_of_validator(self, verbose=1):
        """Valid if all child result validators are valid."""
        assert self.children
        result = True
        for child in self.children:
            if not child.validate(verbose):
                result = False
        return result

    def any_of_validator(self, verbose=1):
        """Valid if any child result validator is valid."""
        assert self.children
        result = False
        for child in self.children:
            if child.validate():
                result = True

        if not result and verbose > 1:
            for child in self.children:
                child.validate(verbose)
        return result

    def not_validator(self, verbose=1):
        """Valid if the child result validator is not valid."""
        assert len(self.children) == 1
        result = not self.children[0].validate()
        if not result and verbose > 1:
            self.children[0].validate(verbose)

        if not result:
            self.report_failure(verbose, expected=False, result=True)
        return result

    def assert_eq_validator(self, verbose=1):
        try:
            result = self.test_case.run_xpath_test(verbose)
        except (ElementPathError, ParseError, EvaluateError) as err:
            self.report_failure(verbose, error=err)
            return False

        if isinstance(result, list) and len(result) == 1:
            result = result[0]

        parser = xpath_parser(xsd_version=self.test_case.xsd_version)
        root_node = parser.parse(self.value)
        context = XPathContext(root=self.etree.XML("<empty/>"))
        expected_result = root_node.evaluate(context)

        try:
            if expected_result == result:
                return True
            elif isinstance(expected_result, decimal.Decimal) and isinstance(result, float):
                if float(expected_result) == result:
                    return True
            elif decimal.Decimal(expected_result) == decimal.Decimal(result):
                return True
        except (TypeError, ValueError, decimal.DecimalException):
            pass

        self.report_failure(verbose, expected=expected_result, result=result)
        return False

    def assert_type_validator(self, verbose=1):
        try:
            result = self.test_case.run_xpath_test(verbose)
        except (ElementPathError, ParseError, EvaluateError) as err:
            self.report_failure(verbose, error=err)
            return False

        if isinstance(result, list) and len(result) == 1:
            result = result[0]

        parser = xpath_parser(namespaces={'j': XPATH_FUNCTIONS_NAMESPACE})
        if self.value == 'function(*)':
            type_check = isinstance(result, XPathFunction)
        elif self.value == 'array(*)':
            type_check = isinstance(result, XPathArray)
        elif self.value == 'map(*)':
            type_check = isinstance(result, XPathMap)
        elif not is_sequence_type(self.value, parser):
            msg = " test-case {}: {!r} is not a valid sequence type"
            print(msg.format(self.test_case.name, self.value))
            type_check = False
        else:
            context_result = get_context_result(result)
            type_check = match_sequence_type(context_result, self.value, parser)

        if not type_check:
            self.report_failure(
                verbose, expected=self.value, result=result, result_type=type(result)
            )
        return type_check

    def assert_string_value_validator(self, verbose=1):
        try:
            result = self.test_case.run_xpath_test(verbose)
        except (ElementPathError, ParseError, EvaluateError) as err:
            self.report_failure(verbose, error=err)
            return False

        context = XPathContext(self.etree.XML("<empty/>"), variables={'result': result})
        if isinstance(result, list):
            value = self.string_join_token.evaluate(context)
        else:
            value = self.string_token.evaluate(context)

        if self.attrib.get('normalize-space'):
            expected = re.sub(r'\s+', ' ', self.value).strip()
            value = ' '.join(x.strip() for x in value.split('\n')).strip()
        else:
            expected = self.value

        if not value:
            if expected is None:
                return True
        elif value == expected:
            return True
        elif isinstance(expected, str):
            # workaround for typos in some expected values
            if expected.strip() == value:
                return True
            elif expected.replace('v ;', 'v;') == value:
                return True

        if value and ' ' not in value:
            try:
                dv = decimal.Decimal(value)
                if math.isclose(dv, decimal.Decimal(expected), rel_tol=1E-7, abs_tol=0.0):
                    return True
            except decimal.DecimalException:
                pass

        self.report_failure(
            verbose, expected=expected, string_value=value, xpath_result=result
        )
        return False

    def error_validator(self, verbose=1):
        code = self.attrib.get('code', '*').strip()
        err_traceback = ''

        try:
            self.test_case.run_xpath_test(verbose, with_context=code != 'XPDY0002')
        except ElementPathError as err:
            if code == '*' or code in str(err):
                return True

            if verbose > 3:
                err_traceback = ''.join(traceback.format_exception(None, err, err.__traceback__))
            reason = "Unexpected error {!r}: {}".format(type(err), str(err))

        except (ParseError, EvaluateError) as err:
            if verbose > 3:
                err_traceback = ''.join(traceback.format_exception(None, err, err.__traceback__))
            reason = "Not an elementpath error {!r}: {}".format(type(err), str(err))
        else:
            reason = "Error not raised"

        self.report_failure(verbose, reason=reason, expected_code=code)
        if err_traceback:
            print(err_traceback)
        return False

    def assert_true_validator(self, verbose=1):
        """Valid if the result is `True`."""
        try:
            result = self.test_case.run_xpath_test(verbose)
        except (ElementPathError, ParseError, EvaluateError) as err:
            self.report_failure(verbose, error=err)
            return False
        else:
            if result is True or isinstance(result, list) and result and result[0] is True:
                return True

            self.report_failure(verbose)
            return False

    def assert_false_validator(self, verbose=1):
        """Valid if the result is `False`."""
        try:
            result = self.test_case.run_xpath_test(verbose)
        except (ElementPathError, ParseError, EvaluateError) as err:
            self.report_failure(verbose, error=err)
            return False
        else:
            if result is False or isinstance(result, list) and result and result[0] is False:
                return True

            self.report_failure(verbose)
            return False

    def assert_count_validator(self, verbose=1):
        """Valid if the number of items of the result matches."""
        try:
            result = self.test_case.run_xpath_test(verbose)
        except (ElementPathError, ParseError, EvaluateError) as err:
            self.report_failure(verbose, error=err)
            return False

        if isinstance(result, (AnyAtomicType, XPathArray, XPathMap)):
            length = 1
        else:
            try:
                length = len(result)
            except TypeError as err:
                self.report_failure(verbose, error=err)
                return False

        if int(self.value) == length:
            return True

        self.report_failure(
            verbose, expected=int(self.value), value=length, xpath_result=result
        )
        return False

    def assert_validator(self, verbose=1):
        """
        Assert validator contains an XPath expression whose value must be true.
        The expression may use the variable $result, which is the result of
        the original test.
        """
        try:
            result = self.test_case.run_xpath_test(verbose, with_xpath_nodes=True)
        except (ElementPathError, ParseError, EvaluateError) as err:
            self.report_failure(verbose, error=err)
            return False

        variables = {'result': result}
        root_node = self.test_case.parser.parse(self.value)
        context = XPathContext(
            root=self.etree.XML("<empty/>"),
            variables=variables
        )
        if root_node.boolean_value(root_node.evaluate(context)) is True:
            return True

        self.report_failure(verbose)
        return False

    def assert_deep_eq_validator(self, verbose=1):
        try:
            result = self.test_case.run_xpath_test(verbose)
        except (ElementPathError, ParseError, EvaluateError) as err:
            self.report_failure(verbose, error=err)
            return False

        if isinstance(result, list) and len(result) == 1:
            result = result[0]

        expression = "fn:deep-equal($result, (%s))" % self.value
        variables = {'result': result}

        parser = XPath31Parser(xsd_version=self.test_case.xsd_version)
        root_node = parser.parse(expression)
        context = XPathContext(root=self.etree.XML("<empty/>"), variables=variables)
        if root_node.evaluate(context) is True:
            return True

        self.report_failure(verbose, expected=self.value, result=result)
        return False

    def assert_empty_validator(self, verbose=1):
        """Valid if the result is empty."""
        try:
            result = self.test_case.run_xpath_test(verbose)
        except (ElementPathError, ParseError, EvaluateError) as err:
            self.report_failure(verbose, error=err)
            return False
        else:
            if result is None or result == '' or result == [] or result == ['']:
                return True

            self.report_failure(verbose, result=result)
            return False

    def assert_permutation_validator(self, verbose=1):
        try:
            result = self.test_case.run_xpath_test(verbose)
        except (ElementPathError, ParseError, EvaluateError) as err:
            self.report_failure(verbose, error=err)
            return False

        if not isinstance(result, list):
            result = [result]

        expected = xpath_parser().parse(self.value).evaluate()
        if not isinstance(expected, list):
            expected = [expected]

        if set(expected) == set(result):
            return True

        if len(expected) == len(result):
            _expected = set(expected)

            for value in result:
                if value in _expected:
                    _expected.remove(value)
                    continue
                elif not isinstance(value, (float, decimal.Decimal)):
                    self.report_failure(verbose, result=result, expected=expected)
                    return False

                dv = decimal.Decimal(value)
                for ev in _expected:
                    if not isinstance(ev, (float, decimal.Decimal)):
                        continue
                    elif math.isnan(ev) and math.isnan(dv):
                        _expected.remove(ev)
                        break
                    elif math.isclose(dv, decimal.Decimal(ev), rel_tol=1E-7, abs_tol=0.0):
                        _expected.remove(ev)
                        break
                else:
                    self.report_failure(verbose, result=result, expected=expected)
                    return False

            return True

        self.report_failure(verbose, result=result, expected=expected)
        return False

    def assert_serialization_error_validator(self, verbose=1):
        # TODO: this currently succeeds on any error
        try:
            self.test_case.run_xpath_test(verbose)
        except (ElementPathError, ParseError, EvaluateError):
            return True
        else:
            return False

    def assert_xml_validator(self, verbose=1):
        try:
            if self.test_case.test_set.name == 'fn-parse-xml':
                with working_directory(self.test_case.test_set.workdir):
                    result = self.test_case.run_xpath_test(verbose)
            else:
                result = self.test_case.run_xpath_test(verbose)

        except (ElementPathError, ParseError, EvaluateError) as err:
            self.report_failure(verbose, error=err)
            return False

        if result is None:
            return False

        if self.use_lxml:
            fromstring = lxml.etree.fromstring
            tostring = lxml.etree.tostring
        else:
            fromstring = ElementTree.fromstring
            tostring = ElementTree.tostring

            environment = self.test_case.get_environment()
            if environment is not None:
                for source in environment.sources.values():
                    if source.namespaces:
                        for prefix, uri in source.namespaces.items():
                            ElementTree.register_namespace(prefix, uri)

                for prefix, uri in environment.namespaces.items():
                    ElementTree.register_namespace(prefix, uri)
            else:
                for prefix, uri in xpath_parser.DEFAULT_NAMESPACES.items():
                    ElementTree.register_namespace(prefix, uri)

        if self.value is not None:
            expected = self.value
        else:
            with open(self.attrib['file']) as fp:
                expected = fp.read()

        if type(result) == list:
            parts = []
            for item in result:
                if isinstance(item, elementpath.ElementNode):
                    tail, item.elem.tail = item.elem.tail, None
                    parts.append(tostring(item.elem).decode('utf-8').strip())
                    item.elem.tail = tail
                elif isinstance(item, XPathNode):
                    parts.append(str(item.value))
                elif hasattr(item, 'tag'):
                    tail, item.tail = item.tail, None
                    parts.append(tostring(item).decode('utf-8').strip())
                    item.tail = tail
                elif hasattr(item, 'getroot'):
                    parts.append(tostring(item.getroot()).decode('utf-8').strip())
                else:
                    parts.append(str(item))
            xml_str = ''.join(parts)
        else:
            try:
                root = result.getroot()
            except AttributeError:
                root = result

            xml_str = tostring(root).decode('utf-8').strip()

        # Remove character data from result if expected result is serialized
        if '\n' not in expected:
            xml_str = '>'.join(s.lstrip() for s in xml_str.split('>\n'))

        # Strip the tail from serialized result
        if '>' in xml_str:
            tail_pos = xml_str.rindex('>') + 1
            if tail_pos < len(xml_str):
                xml_str = xml_str[:tail_pos]

        if xml_str == expected or xml_str.replace(' />', '/>') == expected:
            return True

        # 2nd tentative (expected result from a serialization or comparing trees)
        try:
            if xml_str == tostring(fromstring(expected)).decode('utf-8').strip():
                return True
            if etree_is_equal(fromstring(xml_str), fromstring(expected), strict=False):
                return True
        except (ElementTree.ParseError, lxml.etree.ParseError):
            # invalid XML data (maybe empty or concatenation of XML elements)

            # Last try removing xmlns registrations
            xmlns_pattern = re.compile(r'\sxmlns[^"]+"[^"]+"')
            expected_xmlns = xmlns_pattern.findall(expected)

            if any(xmlns not in expected_xmlns for xmlns in xmlns_pattern.findall(xml_str)):
                pass
            elif xmlns_pattern.sub('', xml_str) == xmlns_pattern.sub('', expected):
                return True

        self.report_failure(verbose, result=xml_str, expected=self.value or self.attrib['file'])
        return False

    def serialization_matches_validator(self, verbose=1):
        try:
            result = self.test_case.run_xpath_test(verbose)
        except (ElementPathError, ParseError, EvaluateError):
            return False

        regex = re.compile(self.value)
        return regex.match(result)


def main():
    global xpath_parser

    parser = argparse.ArgumentParser()
    parser.add_argument('catalog', metavar='CATALOG_FILE',
                        help='the path to the main index file of test suite (catalog.xml)')
    parser.add_argument('pattern', nargs='?', default='.*', metavar='PATTERN',
                        help='run only test cases which name matches a regex pattern')
    parser.add_argument('--xpath', metavar='XPATH_EXPR',
                        help="run only test cases that have a specific XPath expression")
    parser.add_argument('-i', dest='ignore_case', action='store_true', default=False,
                        help="ignore character case for regex pattern matching")
    parser.add_argument('--xp30', action='store_true', default=False,
                        help="test XPath 3.0 parser")
    parser.add_argument('--xp31', action='store_true', default=False,
                        help="test XPath 3.0 parser")
    parser.add_argument('-l', '--lxml', dest='use_lxml', action='store_true', default=False,
                        help="use lxml.etree for environment sources (default is ElementTree)")
    parser.add_argument('-c', dest='show_test_case', action='store_true', default=False,
                        help="show test case information before execution")
    parser.add_argument('-v', dest='verbose', action='count', default=1,
                        help='increase verbosity: one option to show unexpected errors, '
                             'two for show also unmatched error codes, three for debug')
    parser.add_argument('-q', '--quiet', action='store_true', default=False,
                        help="run without printing steps or errors")
    parser.add_argument('-r', dest='report', metavar='REPORT_FILE',
                        help="write a report (JSON format) to the given file")
    args = parser.parse_args()

    report = OrderedDict()
    report["summary"] = OrderedDict()
    report['other_failures'] = []
    report['unknown'] = []
    report['failed'] = []
    report['success'] = []

    catalog_file = os.path.abspath(args.catalog)
    pattern = re.compile(args.pattern, flags=re.IGNORECASE if args.ignore_case else 0)
    etree = lxml.etree if args.use_lxml else ElementTree

    if not args.quiet:
        verbose = args.verbose
    elif args.verbose > 1:
        print("Error: quiet and verbose options are mutually exclusive")
        sys.exit(1)
    else:
        verbose = 0

    if not os.path.isfile(catalog_file):
        print("Error: catalog file %s does not exist" % args.catalog)
        sys.exit(1)

    start_time = datetime.datetime.now()

    if args.xp31:
        from elementpath.xpath31 import XPath31Parser

        xpath_parser = XPath31Parser
        Result.parser = xpath_parser()
        ignore_specs.remove('XP30+')
        ignore_specs.remove('XP31')
        ignore_specs.remove('XP31+')
        ignore_specs.add('XP20')

    elif args.xp30:
        from elementpath.xpath30 import XPath30Parser

        xpath_parser = XPath30Parser
        Result.parser = xpath_parser()
        ignore_specs.remove('XP30')
        ignore_specs.remove('XP30+')
        ignore_specs.add('XP20')

    with working_directory(dirpath=os.path.dirname(catalog_file)):
        catalog_xml = etree.parse(catalog_file)

        environments = {}
        for child in catalog_xml.getroot().iterfind("environment", namespaces):
            environment = Environment(child, args.use_lxml)
            environments[environment.name] = environment

        test_sets = {}
        for child in catalog_xml.getroot().iterfind("test-set", namespaces):
            test_set = TestSet(child, pattern, args.use_lxml, environments)
            test_sets[test_set.name] = test_set

        count_read = 0
        count_skip = 0
        count_run = 0
        count_success = 0
        count_failed = 0
        count_unknown = 0
        count_other_failures = 0

        for test_set in test_sets.values():
            # ignore by specs of test_set
            ignore_all_in_test_set = test_set.specs and all(
                dep in ignore_specs for dep in test_set.specs
            )

            for test_case in test_set.test_cases:
                count_read += 1

                if ignore_all_in_test_set:
                    count_skip += 1
                    continue

                # ignore test cases for XML version 1.1 (not yet supported by Python's libraries)
                if test_case.xml_version == '1.1':
                    count_skip += 1
                    continue

                # ignore by specs of test_case
                if test_case.specs and all(dep in ignore_specs for dep in test_case.specs):
                    count_skip += 1
                    continue

                # ignore tests that rely on high level of support for uca collation semantics
                if 'advanced-uca-fallback' in test_case.features:
                    count_skip += 1
                    continue

                # ignore tests that require an XQuery processor available
                if 'fn-load-xquery-module' in test_case.features:
                    count_skip += 1
                    continue

                # ignore tests that require an XSLT processor available
                if 'fn-transform-XSLT' in test_case.features:
                    count_skip += 1
                    continue

                # ignore tests that require an XSLT 3.0 processor available
                if 'fn-transform-XSLT30' in test_case.features:
                    count_skip += 1
                    continue

                # ignore tests that rely on DTD parsing (TODO with lxml or a custom parser)
                if 'infoset-dtd' in test_case.features \
                        or test_case.environment_ref == 'id-idref-dtd':
                    count_skip += 1
                    continue

                # ignore cases where a directory is used as collection uri (not supported
                # feature, only the case fn-collection__collection-010)
                if 'directory-as-collection-uri' in test_case.features:
                    count_skip += 1
                    continue

                # ignore tests that rely on XQuery 1.0/XPath 2.0 static-typing enforcement
                if 'staticTyping' in test_case.test_set.features \
                        or 'staticTyping' in test_case.features:
                    count_skip += 1
                    continue

                # ignore tests that rely on processing-instructions and comments
                if test_case.environment_ref == 'bib2':
                    count_skip += 1
                    continue

                # Other test cases to skip for technical limitations
                if test_case.name in SKIP_TESTS:
                    count_skip += 1
                    continue

                if not args.use_lxml and test_case.name in LXML_ONLY:
                    count_skip += 1
                    continue

                if args.xpath and test_case.test != args.xpath:
                    count_skip += 1
                    continue

                if args.xp30 and not args.xp31 and test_case.test:
                    if 'parse-json' in test_case.test:
                        count_skip += 1
                        continue
                    elif 'map {' in test_case.test:
                        count_skip += 1
                        continue

                count_run += 1
                if args.show_test_case:
                    print(f"Run test case {test_case.name!r}", flush=True)
                elif verbose == 1:
                    print('.', end='', flush=True)

                try:
                    case_result = test_case.run(verbose)
                    if case_result is True:
                        if args.report:
                            report['success'].append(test_case.name)
                        count_success += 1
                    elif case_result is False:
                        if args.report:
                            report['failed'].append(test_case.name)
                        count_failed += 1
                        if verbose == 1:
                            print('F', end='', flush=True)
                    else:
                        if args.report:
                            report['unknown'].append(test_case.name)
                        count_unknown += 1
                        if verbose == 1:
                            print('U', end='', flush=True)
                except Exception as err:
                    if verbose == 1:
                        print('E', end='', flush=True)
                    elif verbose:
                        print("\nUnexpected failure for test %r" % test_case.name)
                        print(type(err), str(err), flush=True)
                        if verbose >= 4:
                            traceback.print_exc()

                    if args.report:
                        report['other_failures'].append(test_case.name)
                    count_other_failures += 1

        elapsed_time = (datetime.datetime.now() - start_time).seconds

        print("\n*** Totals of W3C XPath tests execution ***\n")

        print(f"Total elapsed time: {elapsed_time}s\n")
        print("%d test cases read" % count_read)
        print("%d test cases skipped" % count_skip)
        print("%d test cases run\n" % count_run)
        print("  %d success" % count_success)
        print("  %d failed" % count_failed)
        print("  %d unknown" % count_unknown)
        print("  %d other failures" % count_other_failures)

        if args.report:
            report['summary']['read'] = count_read
            report['summary']['skipped'] = count_skip
            report['summary']['run'] = count_run
            report['summary']['success'] = count_success
            report['summary']['failed'] = count_failed
            report['summary']['unknown'] = count_unknown
            report['summary']['other_failures'] = count_other_failures
            with open(args.report, 'w') as outfile:
                outfile.write(json.dumps(report, indent=2))


if __name__ == '__main__':
    sys.exit(main())
