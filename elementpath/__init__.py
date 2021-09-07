#
# Copyright (c), 2018-2021, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
__version__ = '2.3.1'
__author__ = "Davide Brunato"
__contact__ = "brunato@sissa.it"
__copyright__ = "Copyright 2018-2021, SISSA"
__license__ = "MIT"
__status__ = "Production/Stable"


from .exceptions import ElementPathError, MissingContextError, \
    ElementPathSyntaxError, ElementPathNameError, ElementPathKeyError, \
    ElementPathTypeError, ElementPathLocaleError, ElementPathValueError, \
    ElementPathOverflowError, ElementPathZeroDivisionError

from .xpath_context import XPathContext, XPathSchemaContext
from .xpath_nodes import XPathNode, AttributeNode, TextNode, \
    NamespaceNode, TypedElement, TypedAttribute
from .xpath_token import XPathToken, XPathFunction
from .xpath1 import XPath1Parser
from .xpath2 import XPath2Parser
from .xpath_selectors import select, iter_select, Selector
from .schema_proxy import AbstractSchemaProxy
from .regex import RegexError, translate_pattern


__all__ = ['ElementPathError', 'MissingContextError', 'ElementPathSyntaxError',
           'ElementPathKeyError', 'ElementPathLocaleError', 'ElementPathNameError',
           'ElementPathOverflowError', 'ElementPathValueError', 'ElementPathTypeError',
           'ElementPathZeroDivisionError', 'datatypes', 'XPathContext', 'XPathSchemaContext',
           'XPathNode', 'AttributeNode', 'TextNode', 'NamespaceNode', 'TypedAttribute',
           'TypedElement', 'XPathToken', 'XPathFunction', 'XPath1Parser', 'XPath2Parser',
           'select', 'iter_select', 'Selector', 'AbstractSchemaProxy',
           'RegexError', 'translate_pattern']
