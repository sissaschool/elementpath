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
from .exceptions import (
    ElementPathNameError, ElementPathTypeError, ElementPathValueError, ElementPathMissingContextError
)
from .namespaces import XQT_ERRORS_NAMESPACE
from .xpath_helpers import is_etree_element, is_document_node, boolean_value, data_value
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
            return '%s() function' % symbol
        elif label == 'axis':
            return '%s axis' % symbol
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

    ###
    # XQuery, XSLT, and XPath Error Codes (https://www.w3.org/2005/xqt-errors/)
    def error(self, code, message=None):
        """
        Raises an error instance related with a code. An XPath/XQuery/XSLT error code is an
        alphanumeric token starting with four uppercase letters and ending with four digits.

        :param code: the error code.
        :param message: an optional custom message.
        """
        for p, v in self.parser.namespaces.items():
            if v == XQT_ERRORS_NAMESPACE:
                pcode = '%s:%s' % (p, code) if p else code
                break
        else:
            pcode = 'err:' + code

        if code == 'XPST0001':
            raise ElementPathValueError(message or 'parser not bound to a schema', self, pcode)
        elif code == 'XPDY0002':
            raise ElementPathMissingContextError(message or 'dynamic context required for evaluate', self, pcode)
        elif code == 'XPTY0004':
            raise ElementPathTypeError(message or 'type is not appropriate for the context', self, pcode)
        elif code == 'XPST0005':
            raise ElementPathValueError(message or 'a not empty sequence required', self, pcode)
        elif code == 'XPST0008':
            raise ElementPathNameError(message or 'name not found', self, pcode)
        elif code == 'XPST0010':
            raise ElementPathNameError(message or 'axis not found', self, pcode)
        elif code == 'XPST0017':
            raise ElementPathValueError(message or 'wrong number of arguments', self, pcode)
        elif code == 'XPTY0018':
            raise ElementPathTypeError(message or 'step result contains both nodes and atomic values', self, pcode)
        elif code == 'XPTY0019':
            raise ElementPathTypeError(message or 'intermediate step contains an atomic value', self, pcode)
        elif code == 'XPTY0020':
            raise ElementPathTypeError(message or 'context item is not a node', self, pcode)
        elif code == 'XPDY0050':
            raise ElementPathTypeError(message or 'type does not match sequence type', self, pcode)
        elif code == 'XPST0051':
            raise ElementPathNameError(message or 'unknown atomic type', self, pcode)
        elif code == 'XPST0080':
            raise ElementPathNameError(message or 'target type cannot be xs:NOTATION or xs:anyAtomicType', self, pcode)
        elif code == 'XPST0081':
            raise ElementPathNameError(message or 'unknown namespace', self, pcode)
        else:
            raise ElementPathValueError('unknown XPath error code %r.' % code)

    # Shortcuts for XPath errors (https://www.w3.org/TR/xpath20/#id-errors)
    def missing_schema(self, message=None):
        self.error('XPST0001', message)

    def missing_context(self, message=None):
        self.error('XPDY0002', message)

    def wrong_context_type(self, message=None):
        self.error('XPTY0004', message)

    def missing_sequence(self, message=None):
        self.error('XPST0005', message)

    def missing_name(self, message=None):
        self.error('XPST0008', message)

    def missing_axis(self, message=None):
        self.error('XPST0010', message)

    def wrong_nargs(self, message=None):
        self.error('XPST0017', message)

    def wrong_step_result(self, message=None):
        self.error('XPTY0018', message)

    def wrong_intermediate_step_result(self, message=None):
        self.error('XPTY0019', message)

    def wrong_axis_argument(self, message=None):
        self.error('XPTY0020', message)

    def wrong_sequence_type(self, message=None):
        self.error('XPDY0050', message)

    def unknown_atomic_type(self, message=None):
        self.error('XPST0051', message)

    def wrong_target_type(self, message=None):
        self.error('XPST0080', message)

    def unknown_namespace(self, message=None):
        self.error('XPST0081', message)
