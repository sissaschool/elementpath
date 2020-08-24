#
# Copyright (c), 2018-2020, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
__version__ = '2.0.2'
__author__ = "Davide Brunato"
__contact__ = "brunato@sissa.it"
__copyright__ = "Copyright 2018-2020, SISSA"
__license__ = "MIT"
__status__ = "Production/Stable"


from .exceptions import ElementPathError, MissingContextError, \
    ElementPathSyntaxError, ElementPathNameError, ElementPathKeyError, \
    ElementPathTypeError, ElementPathLocaleError, ElementPathValueError, \
    ElementPathOverflowError, ElementPathZeroDivisionError

from .xpath_context import XPathContext, XPathSchemaContext
from .xpath_nodes import AttributeNode, TextNode, TypedAttribute, TypedElement, NamespaceNode
from .xpath_token import XPathToken
from .xpath1_parser import XPath1Parser
from .xpath2_parser import XPath2Parser
from .xpath_selectors import select, iter_select, Selector
from .schema_proxy import AbstractSchemaProxy
from .regex import RegexError, translate_pattern


__all__ = ['ElementPathError', 'MissingContextError', 'ElementPathSyntaxError',
           'ElementPathKeyError', 'ElementPathLocaleError', 'ElementPathNameError',
           'ElementPathOverflowError', 'ElementPathValueError', 'ElementPathTypeError',
           'ElementPathZeroDivisionError', 'datatypes', 'XPathContext', 'XPathSchemaContext',
           'AttributeNode', 'TextNode', 'TypedAttribute', 'TypedElement', 'NamespaceNode',
           'XPathToken', 'XPath1Parser', 'XPath2Parser', 'select', 'iter_select', 'Selector',
           'AbstractSchemaProxy', 'RegexError', 'translate_pattern']
