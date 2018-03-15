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
from .exceptions import ElementPathNameError, ElementPathKeyError, ElementPathTypeError, ElementPathValueError
from .xpath_nodes import is_xpath_node, is_etree_element
from .todp_parser import Token


###
# XPathToken
class XPathToken(Token):

    comment = None  # for XPath 2.0 comments

    def select(self, context):
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
                context.item = item
                yield item

    def __str__(self):
        symbol, label = self.symbol, self.label
        if symbol == '$':
            return '$%s variable reference' % (self[0].value if self else '')
        elif symbol == ',':
            return 'comma operator'
        elif label == 'function':
            return '%s(%s) function' % (symbol, ', '.join(repr(t.value) for t in self))
        elif label == 'axis':
            return '%s axis' % symbol
        return super(XPathToken, self).__str__()

    def is_path_step_token(self):
        return self.label == 'axis' or self.symbol in {
            '(integer)', '(string)', '(float)',  '(decimal)', '(name)', '*', '@', '..', '.', '(', '/'
        }

    ###
    # XPath errors
    def missing_schema(self, message='parser not bound to a schema'):
        raise ElementPathValueError("%s: %s [err:XPST0001]." % (self, message))

    def missing_context(self, message='dynamic context required for evaluate'):
        raise ElementPathValueError("%s: %s [err:XPDY0002]." % (self, message))

    def wrong_context_type(self, message='type is not appropriate for the context'):
        raise ElementPathTypeError("%s: %s [err:XPTY0004]." % (self, message))

    def missing_sequence(self, message='a not empty sequence required'):
        raise ElementPathValueError("%s: %s [err:XPST0005]." % (self, message))

    def missing_name(self, message='name not found'):
        raise ElementPathNameError("%s: %s [err:XPST0008]." % (self, message))

    def missing_axis(self, message='axis not found'):
        raise ElementPathNameError("%s: %s [err:XPST0010]." % (self, message))

    def wrong_nargs(self, message='wrong number of arguments'):
        raise ElementPathValueError("%s: %s [err:XPST0017]." % (self, message))

    def wrong_step_result(self, message='step result contains both nodes and atomic values'):
        raise ElementPathTypeError("%s: %s [err:XPTY0018]." % (self, message))

    def wrong_intermediate_step_result(self, message='intermediate step contains an atomic value'):
        raise ElementPathTypeError("%s: %s [err:XPTY0019]." % (self, message))

    def wrong_axis_argument(self, message='context item is not a node'):
        raise ElementPathTypeError("%s: %s [err:XPTY0020]." % (self, message))

    def wrong_sequence_type(self, message='type does not match sequence type'):
        raise ElementPathTypeError("%s: %s [err:XPDY0050]." % (self, message))

    def unknown_atomic_type(self, message='unknown atomic type'):
        raise ElementPathNameError("%s: %s [err:XPST0051]." % (self, message))

    def wrong_target_type(self, message='target type cannot be xs:NOTATION or xs:anyAtomicType'):
        raise ElementPathNameError("%s: %s [err:XPST0080]." % (self, message))

    def unknown_namespace(self, message='unknown namespace'):
        raise ElementPathNameError("%s: %s [err:XPST0081]." % (self, message))

    # Helper methods
    def boolean(self, obj):
        """
        The effective boolean value, as computed by fn:boolean().
        """
        if isinstance(obj, list):
            if not obj:
                return False
            elif is_xpath_node(obj[0]):
                return True
            elif len(obj) > 1:
                self.wrong_type("not a test expression")
            else:
                return bool(obj[0])
        elif isinstance(obj, tuple) or is_etree_element(obj):
            self.wrong_type("not a test expression")
        else:
            return bool(obj)

    def get_argument(self, context=None):
        if not self:
            if context is not None:
                return context.item
        elif context is None:
            return self[0].evaluate()
        else:
            item = None
            for k, result in enumerate(self[0].select(context)):
                if k == 0:
                    item = result
                elif self.parser.version > '1.0':
                    self.wrong_context_type("a sequence of more than one item is not allowed as argument")
                else:
                    break
            return item

    def data(self, object):
        """
        The atomic value of an object, as computed by fn:data() on each item.
        """
        pass


