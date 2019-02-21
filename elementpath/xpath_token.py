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
"""
XPathToken and helper functions for XPath nodes. XPath error messages and node helper functions
are embedded in XPathToken class, in order to raise errors related to token instances.

In XPath there are 7 kinds of nodes:

    element, attribute, text, namespace, processing-instruction, comment, document

Element-like objects are used for representing elements and comments, ElementTree-like objects
for documents. Generic tuples are used for representing attributes and named-tuples for namespaces.
"""
from .compat import string_base_type
from .exceptions import xpath_error
from .namespaces import XQT_ERRORS_NAMESPACE
from .xpath_helpers import AttributeNode, is_etree_element, is_document_node, boolean_value, \
    string_value, data_value, number_value
from .datatypes import UntypedAtomic, Timezone, DayTimeDuration
from .tdop_parser import Token


def ordinal(n):
    least_significant_digit = n % 10
    if least_significant_digit == 1:
        return '%dst' % n
    elif least_significant_digit == 2:
        return '%dnd' % n
    elif least_significant_digit == 3:
        return '%drd' % n
    else:
        return '%dth' % n


class XPathToken(Token):
    """Base class for XPath tokens."""

    comment = None   # for XPath 2.0+ comments
    xsd_type = None  # fox XPath 2.0+ schema types labeling

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

    @property
    def error_prefix(self):
        for prefix, ns in self.parser.namespaces.items():
            if ns == XQT_ERRORS_NAMESPACE:
                return prefix
        else:
            return 'err'

    ###
    # Helper methods
    def get_argument(self, context, index=0, required=False, default_to_context=False, default=None, cls=None):
        """
        Get the argument value of a function of constructor token. A zero length sequence is
        converted to a `None` value. If the function has no argument returns the context's
        item if the dynamic context is not `None`.

        :param context: the dynamic context.
        :param index: an index for select the argument to be got, the first for default.
        :param required: if set to `True` missing or empty sequence arguments are not allowed.
        :param default_to_context: if set to `True` then the item of the dynamic context is \
        returned when the argument is missing.
        :param default: the default value returned in case the argument is an empty sequence. \
        If not provided returns `None`.
        :param cls: if a type is provided performs a type checking on item.
        """
        try:
            selector = self[index].select
        except IndexError:
            if default_to_context:
                if context is None:
                    self.missing_context()
                item = context.item if context.item is not None else context.root
            elif required:
                raise self.error('XPST0017', "Missing %s argument" % ordinal(index + 1))
            else:
                return
        else:
            item = None
            for k, result in enumerate(selector(context)):
                if k == 0:
                    item = result
                elif not self.parser.compatibility_mode:
                    self.wrong_context_type("a sequence of more than one item is not allowed as argument")
                else:
                    break
            else:
                if item is None:
                    if not required:
                        return default
                    ord_arg = ordinal(index + 1)
                    if cls is None:
                        self.missing_sequence("A not empty sequence required for %s argument" % ord_arg)
                    else:
                        self.missing_sequence("A not empty sequence of %r required for %s argument" % (cls, ord_arg))

        # Type checking and conversion (see "function conversion rules" in XPath 2.0 language definition)
        if cls is not None and not isinstance(item, cls):
            if self.parser.compatibility_mode:
                if issubclass(cls, string_base_type):
                    return string_value(item)
                elif issubclass(cls, float):
                    return number_value(item)

            if self.parser.version > '1.0':
                value = data_value(item)
                if isinstance(value, UntypedAtomic):
                    try:
                        return str(value) if issubclass(cls, string_base_type) else cls(value)
                    except (TypeError, ValueError):
                        pass

            code = 'XPTY0004' if self.label == 'function' else 'FORG0006'
            raise self.error(code, "the %s argument %r is not a %r instance" % (ordinal(index + 1), item, cls))

        return item

    def atomization(self, context=None):
        """
        Helper method for value atomization of a sequence.

        Ref: https://www.w3.org/TR/xpath20/#id-atomization

        :param context: the XPath context.
        """
        for item in self.select(context):
            value = data_value(item)
            if value is None:
                raise self.error('FOTY0012', "argument node does not have a typed value: {}".format(item))
            else:
                yield value

    def get_atomized_operand(self, context=None):
        """
        Get the atomized value for an XPath operator.

        :param context: the XPath context.
        :return: the atomized value of a single length sequence or `None` if the sequence is empty.
        """
        selector = iter(self.atomization(context))
        try:
            value = next(selector)
        except StopIteration:
            return
        else:
            try:
                next(selector)
            except StopIteration:
                return str(value) if isinstance(value, UntypedAtomic) else value
            else:
                self.wrong_context_type("atomized operand is a sequence of length greater than one")

    def get_comparison_data(self, context):
        """
        Get comparison data couples for the general comparison of sequences. Different sequences
        maybe generated with an XPath 2.0 parser, depending on compatibility mode setting.

        Ref: https://www.w3.org/TR/xpath20/#id-general-comparisons

        :param context: the XPath dynamic context.
        :returns: a list of data couples.
        """
        if context is None:
            operand1, operand2 = list(self[0].select()), list(self[1].select())
        else:
            operand1 = list(self[0].select(context.copy()))
            operand2 = list(self[1].select(context.copy()))

        if self.parser.compatibility_mode:
            # Boolean comparison if one of the results is a single boolean value (1.)
            try:
                if isinstance(operand1[0], bool):
                    if len(operand1) == 1:
                        return [(operand1[0], boolean_value(operand2, self))]
                if isinstance(operand2[0], bool):
                    if len(operand2) == 1:
                        return [(boolean_value(operand1, self), operand2[0])]
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

        :param context: the XPath dynamic context.
        :return: a list or a simple datatype when the result is a single simple type \
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

    def adjust_datetime(self, context, cls):
        """
        XSD datetime adjust function helper.

        :param context: the XPath dynamic context.
        :param cls: the XSD datetime subclass to use.
        :return: an empty list if there is only one argument that is the empty sequence \
        or the adjusted XSD datetime instance.
        """
        if len(self) == 1:
            item = self.get_argument(context, cls=cls)
            if item is None:
                return []
            timezone = getattr(context, 'timezone', None)
        else:
            item = self.get_argument(context=None, cls=cls)  # don't use implicit timezone
            timezone = self.get_argument(context, 1, cls=DayTimeDuration)
            if timezone is not None:
                timezone = Timezone.fromduration(timezone)

        if item.tzinfo is not None and timezone is not None:
            item += timezone.offset - item.tzinfo.offset
            item.tzinfo = timezone
        elif item.tzinfo is None:
            if timezone is not None:
                item.tzinfo = timezone
        elif timezone is None:
            item.tzinfo = None
        return item

    def match_xsd_type(self, schema_item, name):
        """
        Match a token with a schema type, checking the matching between the provided schema
        item and name. If there is a match and the token is already related with another
        schema type an exception is raised.

        :param schema_item: an XPath item related with a schema instance.
        :param name: a not empty string.
        :returns: the matched XSD type or `None` if there isn't a match.
        """
        if isinstance(schema_item, AttributeNode):
            if not schema_item[1].is_matching(name, self.parser.default_namespace):
                return
            xsd_type = schema_item[1].type
        elif is_etree_element(schema_item):
            if hasattr(schema_item, 'is_matching'):
                if not schema_item.is_matching(name, self.parser.default_namespace):
                    return
            elif schema_item.tag != name:
                return
            xsd_type = schema_item.type
        else:
            return

        if self.xsd_type is None:
            self.xsd_type = xsd_type
        elif self.xsd_type is not xsd_type:
            self.wrong_context_type("Multiple XSD type matching during static analysis")
        return xsd_type

    ###
    # Error handling helpers
    def error(self, code, message=None):
        """
        Returns an XPath error instance related with a code. An XPath/XQuery/XSLT error code is an
        alphanumeric token starting with four uppercase letters and ending with four digits.

        :param code: the error code.
        :param message: an optional custom additional message.
        """
        return xpath_error(code, message, self, self.error_prefix)

    # Shortcuts for XPath errors
    def wrong_value(self, message=None):
        raise self.error('FOCA0002', message)

    def wrong_type(self, message=None):
        raise self.error('FORG0006', message)

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
