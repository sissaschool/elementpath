# -*- coding: utf-8 -*-
#
# Copyright (c), 2018, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""
XPathToken and helper functions for XPath nodes. XPath error messages and node helper functions
are embedded in XPathToken class, in order to raise errors related to token instances.

In XPath there are 7 kinds of nodes:

    element, attribute, text, namespace, processing-instruction, comment, document

Element-like objects are used for representing elements and comments, ElementTree-like objects
for documents. Generic tuples are used for representing attributes and named-tuples for namespaces.
"""
from .compat import string_base_type
from .exceptions import ElementPathError, ElementPathNameError, ElementPathTypeError, \
    ElementPathValueError, ElementPathMissingContextError, ElementPathKeyError
from .namespaces import XQT_ERRORS_NAMESPACE
from .xpath_helpers import is_etree_element, is_document_node, boolean_value, data_value
from .datatypes import DateTime
from .tdop_parser import Token


###
# XPathToken
class XPathToken(Token):

    comment = None  # for XPath 2.0 comments

    def evaluate(self, context=None):
        """
        Evaluate default method for XPath tokens.

        :param context: The XPath dynamic context.
        """
        return list(self.select(context))

    def select(self, context=None):
        """
        Select operator that generates XPath results.

        :param context: The XPath dynamic context.
        """
        item = self.evaluate(context)
        if item is not None:
            if isinstance(item, list):
                for _item in item:
                    yield _item
            else:
                if context is not None:
                    context.item = item
                yield item

    def __str__(self):
        symbol, label = self.symbol, self.label
        if symbol == '$':
            return '$%s variable reference' % (self[0].value if self else '')
        elif symbol == ',':
            return 'comma operator'
        elif label == 'function':
            return '%r function' % symbol
        elif label == 'axis':
            return '%r axis' % symbol
        return super(XPathToken, self).__str__()

    @property
    def source(self):
        symbol, label = self.symbol, self.label
        if label == 'axis':
            return u'%s::%s' % (self.symbol, self[0].source)
        elif label in ('function', 'constructor'):
            return u'%s(%s)' % (self.symbol, ', '.join(item.source for item in self))
        elif symbol == ':':
            return u'%s:%s' % (self[0].source, self[1].source)
        elif symbol == '(':
            return '()' if not self else u'(%s)' % self[0].source
        elif symbol == ',':
            return u'%s, %s' % (self[0].source, self[1].source)
        elif symbol == '$':
            return u'$%s' % self[0].source
        elif symbol == '{':
            return u'{%s}%s' % (self.value, self[0].source)
        elif symbol == 'instance':
            return u'%s instance of %s' % (self[0].source, ''.join(t.source for t in self[1:]))
        elif symbol == 'treat':
            return u'%s treat as %s' % (self[0].source, ''.join(t.source for t in self[1:]))
        return super(XPathToken, self).source

    def get_argument(self, context=None, index=0, default_to_context=False):
        """
        Get the first argument of a function token. A zero length sequence is converted to
        a `None` value. If the function has no argument returns the context's item if the
        dynamic context is not `None`.

        :param context: The dynamic context.
        :param index: An index for select the argument to be got, the first for default.
        :param default_to_context: If set to `True` and the argument is missing the item \
        of the dynamic context is returned.
        """
        try:
            selector = self[index].select
        except IndexError:
            if default_to_context:
                if context is not None:
                    return context.item
                else:
                    self.missing_context()
        else:
            item = None
            for k, result in enumerate(selector(context)):
                if k == 0:
                    item = result
                elif self.parser.version > '1.0':
                    self.wrong_context_type("a sequence of more than one item is not allowed as argument")
                else:
                    break
            return item

    def get_comparison_data(self, context=None):
        """
        Get comparison data couples for the general comparison. Different sequences
        maybe generated with an XPath 2.0 parser, depending on compatibility mode setting.

        Ref: https://www.w3.org/TR/xpath20/#id-general-comparisons

        :param context: The XPath dynamic context.
        :returns: A list.
        """
        if context is None:
            operand1, operand2 = list(self[0].select(None)), list(self[1].select(None))
        else:
            operand1 = list(self[0].select(context.copy()))
            operand2 = list(self[1].select(context.copy()))

        if self.parser.compatibility_mode:
            # Boolean comparison if one of the results is a single boolean value (1.)
            try:
                if isinstance(operand1[0], bool):
                    if len(operand1) == 1:
                        return [(operand1[0], boolean_value(operand2))]
                if isinstance(operand2[0], bool):
                    if len(operand2) == 1:
                        return [(boolean_value(operand1), operand2[0])]
            except IndexError:
                return []

            # Converts to float for lesser-greater operators (3.)
            if self.symbol in ('<', '<=', '>', '>='):
                return [
                    (float(data_value(value1)), float(data_value(value2)))
                    for value1 in operand1 for value2 in operand2
                ]

        return [(data_value(value1), data_value(value2)) for value1 in operand1 for value2 in operand2]

    def get_results(self, context):
        """
        Returns formatted XPath results.

        :param context: The XPath dynamic context.
        :return : A list or a simple datatype when the result is a single simple type \
        generated by a literal or function token.
        """
        results = list(self.select(context))
        if len(results) == 1:
            res = results[0]
            if isinstance(res, tuple) or is_etree_element(res) or is_document_node(res):
                return results
            elif self.symbol in ('text', 'node'):
                return results
            elif self.label in ('function', 'literal'):
                return res
            elif isinstance(res, bool):  # Tests and comparisons
                return res
            else:
                return results
        else:
            return results

    def integer(self, value, lower_bound=None, higher_bound=None):
        """
        Decode a value to an integer.

        :param value: a string or another basic numeric type instance.
        :param lower_bound: if not `None` the result must be higher or equal than its value.
        :param higher_bound: if not `None` the result must be lesser than its value.
        :return: an `int` instance.
        :raise: an `ElementPathValueError` if the value is not decodable to an integer or if \
        the value is out of bounds.
        """
        if isinstance(value, string_base_type):
            try:
                result = int(float(value))
            except ValueError:
                raise self.error('FORG0001', 'could not convert string to integer: %r' % value)
        else:
            try:
                result = int(value)
            except ValueError as err:
                raise self.error('FORG0001', str(err))
            except TypeError as err:
                raise self.error('FORG0006', str(err))

        if lower_bound is not None and result < lower_bound:
            raise self.error('FORG0001', "value %d is too low" % result)
        elif higher_bound is not None and result >= higher_bound:
            raise self.error('FORG0001', "value %d is too high" % result)
        return result

    ###
    # XQuery, XSLT, and XPath Error Codes (https://www.w3.org/2005/xqt-errors/)
    def error(self, code, message=None):
        """
        Returns an error instance related with a code. An XPath/XQuery/XSLT error code is an
        alphanumeric token starting with four uppercase letters and ending with four digits.

        :param code: the error code.
        :param message: an optional custom additional message.
        """
        for prefix, ns in self.parser.namespaces.items():
            if ns == XQT_ERRORS_NAMESPACE:
                break
        else:
            prefix = 'err'

        if ':' not in code:
            pcode = '%s:%s' % (prefix, code) if prefix else code
        elif not prefix or not code.startswith(prefix + ':'):
            raise ElementPathValueError('%r is not an XPath error code' % code)
        else:
            pcode = code
            code = code[len(prefix) + 1:]

        # XPath 2.0 parser error (https://www.w3.org/TR/xpath20/#id-errors)
        if code == 'XPST0001':
            return ElementPathValueError(message or 'Parser not bound to a schema', self, pcode)
        elif code == 'XPDY0002':
            return ElementPathMissingContextError(message or 'Dynamic context required for evaluate', self, pcode)
        elif code == 'XPTY0004':
            return ElementPathTypeError(message or 'Type is not appropriate for the context', self, pcode)
        elif code == 'XPST0005':
            return ElementPathValueError(message or 'A not empty sequence required', self, pcode)
        elif code == 'XPST0008':
            return ElementPathNameError(message or 'Name not found', self, pcode)
        elif code == 'XPST0010':
            return ElementPathNameError(message or 'Axis not found', self, pcode)
        elif code == 'XPST0017':
            return ElementPathValueError(message or 'Wrong number of arguments', self, pcode)
        elif code == 'XPTY0018':
            return ElementPathTypeError(message or 'Step result contains both nodes and atomic values', self, pcode)
        elif code == 'XPTY0019':
            return ElementPathTypeError(message or 'Intermediate step contains an atomic value', self, pcode)
        elif code == 'XPTY0020':
            return ElementPathTypeError(message or 'Context item is not a node', self, pcode)
        elif code == 'XPDY0050':
            return ElementPathTypeError(message or 'Type does not match sequence type', self, pcode)
        elif code == 'XPST0051':
            return ElementPathNameError(message or 'Unknown atomic type', self, pcode)
        elif code == 'XPST0080':
            return ElementPathNameError(message or 'Target type cannot be xs:NOTATION or xs:anyAtomicType', self, pcode)
        elif code == 'XPST0081':
            return ElementPathNameError(message or 'Unknown namespace', self, pcode)

        # XPath data types and function errors
        elif code == 'FOER0000':
            return ElementPathError(message or 'Unidentified error', self, pcode)
        elif code == 'FOAR0001':
            return ElementPathValueError(message or 'Division by zero', self, pcode)
        elif code == 'FOAR0002':
            return ElementPathValueError(message or 'Numeric operation overflow/underflow', self, pcode)
        elif code == 'FOCA0001':
            return ElementPathValueError(message or 'Input value too large for decimal', self, pcode)
        elif code == 'FOCA0002':
            return ElementPathValueError(message or 'Invalid lexical value', self, pcode)
        elif code == 'FOCA0003':
            return ElementPathValueError(message or 'Input value too large for integer', self, pcode)
        elif code == 'FOCA0005':
            return ElementPathValueError(message or 'NaN supplied as float/double value', self, pcode)
        elif code == 'FOCA0006':
            return ElementPathValueError(
                message or 'String to be cast to decimal has too many digits of precision', self, pcode
            )
        elif code == 'FOCH0001':
            return ElementPathValueError(message or 'Code point not valid', self, pcode)
        elif code == 'FOCH0002':
            return ElementPathValueError(message or 'Unsupported collation', self, pcode)
        elif code == 'FOCH0003':
            return ElementPathValueError(message or 'Unsupported normalization form', self, pcode)
        elif code == 'FOCH0004':
            return ElementPathValueError(message or 'Collation does not support collation units', self, pcode)
        elif code == 'FODC0001':
            return ElementPathValueError(message or 'No context document', self, pcode)
        elif code == 'FODC0002':
            return ElementPathValueError(message or 'Error retrieving resource', self, pcode)
        elif code == 'FODC0003':
            return ElementPathValueError(message or 'Function stability not defined', self, pcode)
        elif code == 'FODC0004':
            return ElementPathValueError(message or 'Invalid argument to fn:collection', self, pcode)
        elif code == 'FODC0005':
            return ElementPathValueError(message or 'Invalid argument to fn:doc or fn:doc-available', self, pcode)
        elif code == 'FODT0001':
            return ElementPathValueError(message or 'Overflow/underflow in date/time operation', self, pcode)
        elif code == 'FODT0002':
            return ElementPathValueError(message or 'Overflow/underflow in duration operation', self, pcode)
        elif code == 'FODT0003':
            return ElementPathValueError(message or 'Invalid timezone value', self, pcode)
        elif code == 'FONS0004':
            return ElementPathKeyError(message or 'No namespace found for prefix', self, pcode)
        elif code == 'FONS0005':
            return ElementPathValueError(message or 'Base-uri not defined in the static context', self, pcode)
        elif code == 'FORG0001':
            return ElementPathValueError(message or 'Invalid value for cast/constructor', self, pcode)
        elif code == 'FORG0002':
            return ElementPathValueError(message or 'Invalid argument to fn:resolve-uri()', self, pcode)
        elif code == 'FORG0003':
            return ElementPathValueError(
                message or 'fn:zero-or-one called with a sequence containing more than one item', self, pcode
            )
        elif code == 'FORG0004':
            return ElementPathValueError(
                message or 'fn:one-or-more called with a sequence containing no items', self, pcode
            )
        elif code == 'FORG0005':
            return ElementPathValueError(
                message or 'fn:exactly-one called with a sequence containing zero or more than one item', self, pcode
            )
        elif code == 'FORG0006':
            return ElementPathTypeError(message or 'Invalid argument type', self, pcode)
        elif code == 'FORG0008':
            return ElementPathValueError(
                message or 'The two arguments to fn:dateTime have inconsistent timezones', self, pcode
            )
        elif code == 'FORG0009':
            return ElementPathValueError(
                message or 'Error in resolving a relative URI against a base URI in fn:resolve-uri', self, pcode
            )
        elif code == 'FORX0001':
            return ElementPathValueError(message or 'Invalid regular expression flags', self, pcode)
        elif code == 'FORX0002':
            return ElementPathValueError(message or 'Invalid regular expression', self, pcode)
        elif code == 'FORX0003':
            return ElementPathValueError(message or 'Regular expression matches zero-length string', self, pcode)
        elif code == 'FORX0004':
            return ElementPathValueError(message or 'Invalid replacement string', self, pcode)
        elif code == 'FOTY0012':
            return ElementPathValueError(message or 'Argument node does not have a typed value', self, pcode)
        elif code == '':
            return ElementPathValueError(message or '', self, pcode)

        else:
            raise ElementPathValueError('Unknown XPath error code %r.' % code)

    # Shortcuts for XPath errors
    def missing_schema(self, message=None):
        raise self.error('XPST0001', message)

    def missing_context(self, message=None):
        raise self.error('XPDY0002', message)

    def wrong_context_type(self, message=None):
        raise self.error('XPTY0004', message)

    def missing_sequence(self, message=None):
        raise self.error('XPST0005', message)

    def missing_name(self, message=None):
        raise self.error('XPST0008', message)

    def missing_axis(self, message=None):
        raise self.error('XPST0010', message)

    def wrong_nargs(self, message=None):
        raise self.error('XPST0017', message)

    def wrong_step_result(self, message=None):
        raise self.error('XPTY0018', message)

    def wrong_intermediate_step_result(self, message=None):
        raise self.error('XPTY0019', message)

    def wrong_axis_argument(self, message=None):
        raise self.error('XPTY0020', message)

    def wrong_sequence_type(self, message=None):
        raise self.error('XPDY0050', message)

    def unknown_atomic_type(self, message=None):
        raise self.error('XPST0051', message)

    def wrong_target_type(self, message=None):
        raise self.error('XPST0080', message)

    def unknown_namespace(self, message=None):
        raise self.error('XPST0081', message)
