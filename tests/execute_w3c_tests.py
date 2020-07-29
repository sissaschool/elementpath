#!/usr/bin/env python3
#
# Copyright (c), 2018-2020, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Jelte Jansen <github@tjeb.nl>
# @author Davide Brunato <brunato@sissa.it>
#
"""
Tests script for running W3C XPath tests on elementpath. This is a
reworking of https://github.com/tjeb/elementpath_w3c_tests project
that uses ElementTree for default and collapses the essential parts
into only one module.
"""
import argparse
import contextlib
import decimal
import re
import json
import os
import sys
import traceback

from collections import OrderedDict
from xml.etree import ElementTree
import lxml.etree

from elementpath import ElementPathError, XPath2Parser, XPathContext
import elementpath
import xmlschema


DEPENDENCY_TYPES = {'spec', 'feature', 'calendar', 'default-language',
                    'format-integer-sequence', 'language', 'limits',
                    'xml-version', 'xsd-version', 'unicode-version',
                    'unicode-normalization-form'}

IGNORE_SPECS = {'XQ10', 'XQ10+', 'XP30', 'XP30+', 'XQ30',
                'XQ30+', 'XP31', 'XP31+', 'XQ31', 'XQ31+'}

SKIP_TESTS = [
    'fn-subsequence__cbcl-subsequence-010',
    'fn-subsequence__cbcl-subsequence-011',
    'fn-subsequence__cbcl-subsequence-012',
    'fn-subsequence__cbcl-subsequence-013',
    'fn-subsequence__cbcl-subsequence-014',
    'prod-NameTest__NodeTest004',

    # Maybe tested with lxml
    'fn-string__fn-string-30',  # parse of comments required

    # Unsupported collations
    'fn-compare__compare-010',

    # Processing-instructions (tests on env "auction")
    'fn-local-name__fn-local-name-78',
    'fn-name__fn-name-28',
    'fn-string__fn-string-28',
]


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
    """Represents a source file as used in XML environment settings."""

    namespaces = None

    def __init__(self, elem, use_lxml=False):
        assert elem.tag == '{%s}source' % QT3_NAMESPACE
        self.file = elem.attrib['file']
        self.role = elem.attrib.get('role', '')
        self.uri = elem.attrib.get('uri')
        try:
            self.description = elem.find('description', namespaces).text
        except AttributeError:
            self.description = ''

        try:
            if use_lxml:
                self.xml = lxml.etree.parse(self.file)
            else:
                self.xml = ElementTree.parse(self.file)
                self.namespaces = {
                    k: v for _, (k, v) in ElementTree.iterparse(self.file, events=('start-ns',))
                }

        except (ElementTree.ParseError, lxml.etree.XMLSyntaxError):
            self.xml = None

    def __repr__(self):
        return '%s(file=%r)' % (self.__class__.__name__, self.file)


class Environment(object):
    """
    The XML environment definition for a test case.

    :param elem: the XML Element that contains the environment definition.
    :param use_lxml: use lxml.etree for loading XML sources.
    """
    def __init__(self, elem, use_lxml=False):
        assert elem.tag == '{%s}environment' % QT3_NAMESPACE
        self.name = elem.get('name', 'anonymous')
        self.namespaces = {
            namespace.attrib['prefix']: namespace.attrib['uri']
            for namespace in elem.iterfind('namespace', namespaces)
        }

        child = elem.find('schema', namespaces)
        if child is not None:
            self.schema = Schema(child)
        else:
            self.schema = None

        self.sources = {}
        for child in elem.iterfind('source', namespaces):
            source = Source(child, use_lxml)
            self.sources[source.role] = source

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

        full_path = os.path.abspath(self.file)
        directory = os.path.dirname(full_path)
        filename = os.path.basename(full_path)
        with working_directory(directory):
            xml_root = ElementTree.parse(filename).getroot()

            self.description = xml_root.find('description', namespaces).text

            for child in xml_root.findall('dependency', namespaces):
                dep_type = child.attrib['type']
                value = child.attrib['value']
                if dep_type == 'spec':
                    self.specs.extend(value.split(' '))
                elif dep_type == 'feature':
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
    calendar = None
    default_language = None
    format_integer_sequence = None
    language = None
    limits = None
    unicode_version = None
    unicode_normalization_form = None
    xml_version = None
    xsd_version = None

    def __init__(self, elem, test_set, use_lxml=False):
        assert elem.tag == '{%s}test-case' % QT3_NAMESPACE
        self.test_set = test_set
        self.name = test_set.name + "__" + elem.attrib['name']
        self.description = elem.find('description', namespaces).text
        self.test = elem.find('test', namespaces).text

        result_child = elem.find('result', namespaces).find("*")
        self.result = Result(result_child, test_case=self, use_lxml=use_lxml)

        self.environment_ref = None
        self.environment = None
        self.specs = []
        self.features = []

        for child in elem.findall('dependency', namespaces):
            dep_type = child.attrib['type']
            value = child.attrib['value']
            if dep_type == 'spec':
                self.specs.extend(value.split(' '))
            elif dep_type == 'feature':
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
                    children.extend('<spec value="{}"/>'.format(x) for x in self.features)
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

    def get_xpath_context(self):
        kwargs = {
            'timezone': 'Z',
        }

        environment = self.get_environment()
        if environment is None:
            return XPathContext(root=ElementTree.XML("<empty/>"), **kwargs)

        if '.' in environment.sources:
            root = environment.sources['.'].xml
        else:
            root = ElementTree.XML("<empty/>")

        if any(k.startswith('$') for k in environment.sources):
            kwargs['variable_values'] = {
                k[1:]: v.xml for k, v in environment.sources.items() if k.startswith('$')
            }

        return XPathContext(root=root, **kwargs)

    def run(self, verbose=1):
        if verbose > 4:
            print("\n*** Execute test case {!r} ***".format(self.name))
            print(str(self))
            print()
        return self.result.validate(verbose)

    def run_xpath_test(self, verbose=1, with_context=True):
        """
        Helper function to parse and evaluate tests with elementpath.

        If may_fail is true, raise the exception instead of printing and aborting
        """
        environment = self.get_environment()
        if environment is None:
            test_namespaces = schema_proxy = None
        else:
            test_namespaces = environment.namespaces.copy()

            if environment.schema is None or not environment.schema.filepath:
                schema_proxy = None
            else:
                if verbose > 2:
                    print("Schema %r required for test %r" % (environment.schema.file, self.name))

                schema = xmlschema.XMLSchema(environment.schema.filepath)
                schema_proxy = schema.xpath_proxy

        try:
            parser = XPath2Parser(
                namespaces=test_namespaces,
                xsd_version=self.xsd_version,
                schema=schema_proxy,
            )
            root_node = parser.parse(self.test)
        except Exception as err:
            if isinstance(err, ElementPathError):
                raise
            raise ParseError(err)

        context = self.get_xpath_context() if with_context else None
        try:
            result = root_node.evaluate(context)
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
    parser = XPath2Parser()
    string_token = parser.parse('fn:string($result)')
    string_join_token = parser.parse('fn:string-join($result, " ")')

    def __init__(self, elem, test_case, use_lxml=False):
        self.test_case = test_case
        self.use_lxml = use_lxml
        self.type = elem.tag.split('}')[1]
        self.value = elem.text
        self.attrib = {k: v for k, v in elem.attrib.items()}
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

        if verbose < 4:
            print('Result <{}> failed for test case {!r}'.format(self.type, self.test_case.name))
            print('XPath expression: {}'.format(self.test_case.test))
        else:
            print('Result <{}> failed\n'.format(self.type))
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
        return result

    def assert_eq_validator(self, verbose=1):
        try:
            result = self.test_case.run_xpath_test(verbose)
        except (ElementPathError, ParseError, EvaluateError) as err:
            self.report_failure(verbose, error=err)
            return False

        if isinstance(result, list) and len(result) == 1:
            result = result[0]

        parser = XPath2Parser()
        root_node = parser.parse(self.value)
        context = XPathContext(root=ElementTree.XML("<empty/>"))
        expected_result = root_node.evaluate(context)
        if expected_result == result:
            return True
        elif isinstance(expected_result, decimal.Decimal) and isinstance(result, float):
            if float(expected_result) == result:
                return True

        self.report_failure(verbose, expected=expected_result, result=result)
        return False

    def assert_type_validator(self, verbose=1):
        try:
            result = self.test_case.run_xpath_test(verbose)
        except (ElementPathError, ParseError, EvaluateError) as err:
            self.report_failure(verbose, error=err)
            return False

        if self.value == 'xs:anyURI':
            type_check = isinstance(result, str)
        elif self.value == 'xs:boolean':
            type_check = isinstance(result, bool)
        elif self.value == 'xs:date':
            type_check = isinstance(result, elementpath.datatypes.Date10)
        elif self.value == 'xs:double':
            type_check = isinstance(result, float)
        elif self.value == 'xs:dateTime':
            type_check = isinstance(result, elementpath.datatypes.DateTime10)
        elif self.value == 'xs:dayTimeDuration':
            type_check = isinstance(result, elementpath.datatypes.DayTimeDuration)
        elif self.value == 'xs:decimal':
            type_check = isinstance(result, (int, decimal.Decimal)) and not isinstance(result, bool)
        elif self.value == 'xs:float':
            type_check = isinstance(result, float)
        elif self.value == 'xs:integer':
            type_check = isinstance(result, int) and not isinstance(result, bool)
        elif self.value == 'xs:NCName':
            type_check = isinstance(result, str)
        elif self.value == 'xs:nonNegativeInteger':
            type_check = isinstance(result, int) and not isinstance(result, bool)
        elif self.value == 'xs:positiveInteger':
            type_check = isinstance(result, int) and not isinstance(result, bool)
        elif self.value == 'xs:string':
            type_check = isinstance(result, str)
        elif self.value == 'xs:time':
            type_check = isinstance(result, elementpath.datatypes.Time)
        elif self.value == 'xs:token':
            type_check = isinstance(result, str)
        elif self.value == 'xs:unsignedShort':
            type_check = isinstance(result, int) and not isinstance(result, bool)
        elif self.value.startswith('document-node') or self.value.startswith('element'):
            type_check = isinstance(result, list)
        else:
            msg = "unknown type in assert_type: %s (result type is %s), test-case %s"
            print(msg % (self.value, str(type(result)), self.test_case.name))
            sys.exit(1)

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

        context = XPathContext(ElementTree.XML("<empty/>"), variable_values={'result': result})
        if isinstance(result, list):
            value = self.string_join_token.evaluate(context)
        else:
            value = self.string_token.evaluate(context)

        if self.attrib.get('normalize-space'):
            expected = ' '.join(x.strip() for x in self.value.split('\n')).strip()
        else:
            expected = self.value

        if not value:
            if expected is None:
                return True
        elif value == expected:
            return True

        if value and ' ' not in value:
            try:
                dv = decimal.Decimal(value)
                if dv == decimal.Decimal(expected):
                    return True
            except decimal.DecimalException:
                pass
            else:
                if abs(dv) > 10**3 and round(dv) == decimal.Decimal(expected):
                    return True

        self.report_failure(
            verbose, expected=expected, string_value=value, xpath_result=result
        )
        return False

    def error_validator(self, verbose=1):
        code = self.attrib.get('code', '*').strip()
        try:
            self.test_case.run_xpath_test(verbose, with_context=code != 'XPDY0002')
        except ElementPathError as err:
            if code == '*' or code in str(err):
                return True
            reason = "Unexpected error {!r}: {}".format(type(err), str(err))
        except (ParseError, EvaluateError) as err:
            reason = "Not an elementpath error {!r}: {}".format(type(err), str(err))
        else:
            reason = "Error not raised"

        self.report_failure(verbose, reason=reason, expected_code=code)
        return False

    def assert_true_validator(self, verbose=1):
        """Valid if the result is `True`."""
        try:
            if self.test_case.run_xpath_test(verbose) is True:
                return True
        except (ElementPathError, ParseError, EvaluateError) as err:
            self.report_failure(verbose, error=err)
            return False
        else:
            self.report_failure(verbose)
            return False

    def assert_false_validator(self, verbose=1):
        """Valid if the result is `False`."""
        try:
            if self.test_case.run_xpath_test(verbose) is False:
                return True
        except (ElementPathError, ParseError, EvaluateError) as err:
            self.report_failure(verbose, error=err)
            return False
        else:
            self.report_failure(verbose)
            return False

    def assert_count_validator(self, verbose=1):
        """Valid if the number of items of the result matches."""
        try:
            result = self.test_case.run_xpath_test(verbose)
        except (ElementPathError, ParseError, EvaluateError) as err:
            self.report_failure(verbose, error=err)
            return False

        try:
            length = 1 if isinstance(result, (str, bytes)) else len(result)
        except TypeError as err:
            self.report_failure(verbose, error=err)
            return False
        else:
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
            result = self.test_case.run_xpath_test(verbose)
        except (ElementPathError, ParseError, EvaluateError) as err:
            self.report_failure(verbose, error=err)
            return False

        variables = {'result': result}
        parser = XPath2Parser(variables=variables)
        root_node = parser.parse(self.value)
        context = XPathContext(root=ElementTree.XML("<empty/>"), variable_values=variables)
        if root_node.evaluate(context) is True:
            return True

        self.report_failure(verbose)
        return False

    def assert_deep_eq_validator(self, verbose=1):
        try:
            result = self.test_case.run_xpath_test(verbose)
        except (ElementPathError, ParseError, EvaluateError) as err:
            self.report_failure(verbose, error=err)
            return False

        expression = "fn:deep-equal($result, (%s))" % self.value
        variables = {'result': result}

        parser = XPath2Parser(variables=variables)
        root_node = parser.parse(expression)
        context = XPathContext(root=ElementTree.XML("<empty/>"), variable_values=variables)
        if root_node.evaluate(context) is True:
            return True

        self.report_failure(verbose)
        return False

    def assert_empty_validator(self, verbose=1):
        """Valid if the result is empty."""
        try:
            result = self.test_case.run_xpath_test(verbose)
        except (ElementPathError, ParseError, EvaluateError) as err:
            self.report_failure(verbose, error=err)
            return False
        else:
            if result is None or result == []:
                return True

            self.report_failure(verbose, result=result)
            return False

    def assert_permutation_validator(self, verbose=1):
        """ TODO """

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
            result = self.test_case.run_xpath_test(verbose)
        except (ElementPathError, ParseError, EvaluateError):
            return False

        if result is None:
            return False

        if self.use_lxml:
            tostring = lxml.etree.tostring
        else:
            tostring = ElementTree.tostring

            environment = self.test_case.get_environment()
            if environment is not None:
                for source in environment.sources.values():
                    if source.namespaces:
                        for prefix, uri in source.namespaces.items():
                            ElementTree.register_namespace(prefix, uri)

                for prefix, uri in environment.namespaces.items():
                    ElementTree.register_namespace(prefix, uri)

        if type(result) == list:
            parts = []
            for item in result:
                if isinstance(item, elementpath.TypedElement):
                    parts.append(tostring(item[0]).decode('utf-8').strip())
                elif isinstance(item, tuple):
                    parts.append(str(item[-1]))
                elif hasattr(item, 'tag'):
                    parts.append(tostring(item).decode('utf-8').strip())
                else:
                    parts.append(str(item))
            xml_str = ''.join(parts)
        else:
            xml_str = tostring(result.getroot()).decode('utf-8').strip()

        if xml_str == self.value:
            return True

        diff = set(re.split('[> ]', self.value)) - set(re.split('[> ]', xml_str))
        if not diff or all(x.startswith('xmlns:') for x in diff):
            return True

        self.report_failure(verbose, result=xml_str, expected=self.value)
        return False

    def serialization_matches_validator(self, verbose=1):
        try:
            result = self.test_case.run_xpath_test(verbose)
        except (ElementPathError, ParseError, EvaluateError):
            return False

        regex = re.compile(self.value)
        return regex.match(result)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('catalog', metavar='CATALOG_FILE',
                        help='the path to the main index file of test suite (catalog.xml)')
    parser.add_argument('pattern', nargs='?', default='.*', metavar='PATTERN',
                        help='run only test cases which name matches a regex pattern')
    parser.add_argument('-i', dest='ignore_case', action='store_true', default=False,
                        help="ignore character case for regex pattern matching")
    parser.add_argument('-l', '--lxml', dest='use_lxml', action='store_true', default=False,
                        help="use lxml.etree for environment sources (default is ElementTree)")
    parser.add_argument('-v', dest='verbose', action='count', default=1,
                        help='increase verbosity: one option to show unexpected errors, '
                             'two for show also unmatched error codes, three for debug')
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

    if not os.path.isfile(catalog_file):
        print("Error: catalog file %s does not exist" % args.catalog)
        sys.exit(1)

    with working_directory(dirpath=os.path.dirname(catalog_file)):
        catalog_xml = ElementTree.parse(catalog_file)

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
            # ignore test cases for XQuery, and 3.0
            ignore_all_in_test_set = any(
                dep in IGNORE_SPECS for dep in test_set.specs
            )

            for test_case in test_set.test_cases:
                count_read += 1

                if ignore_all_in_test_set:
                    count_skip += 1
                    continue

                # ignore test cases for XQuery, and 3.0
                if any(dep in IGNORE_SPECS for dep in test_case.specs):
                    count_skip += 1
                    continue

                # ignore tests that rely on higher-order function such as array:sort()
                if 'higherOrderFunctions' in test_case.features:
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

                count_run += 1
                try:
                    case_result = test_case.run(verbose=args.verbose)
                    if case_result is True:
                        if args.report:
                            report['success'].append(test_case.name)
                        count_success += 1
                    elif case_result is False:
                        if args.report:
                            report['failed'].append(test_case.name)
                        count_failed += 1
                    else:
                        if args.report:
                            report['unknown'].append(test_case.name)
                        count_unknown += 1
                except Exception as err:
                    print("\nUnexpected failure for test %r" % test_case.name)
                    print(type(err), str(err))

                    if args.verbose >= 4:
                        traceback.print_exc()
                    if args.report:
                        report['other_failures'].append(test_case.name)
                    count_other_failures += 1

        print("\n*** Totals of W3C XPath tests execution ***\n")
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