#
# Copyright (c), 2018-2022, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
__version__ = '4.7.0'
__author__ = "Davide Brunato"
__contact__ = "brunato@sissa.it"
__copyright__ = "Copyright 2018-2024, SISSA"
__license__ = "MIT"
__status__ = "Production/Stable"

# Imports here are considered as stable API, other internal calls may change.

from . import datatypes  # XSD datatypes
from . import etree      # Safe parser and helper functions for ElementTree
from . import protocols  # Protocols for type annotations

from .exceptions import ElementPathError, MissingContextError, ElementPathKeyError, \
    ElementPathZeroDivisionError, ElementPathNameError, ElementPathOverflowError, \
    ElementPathRuntimeError, ElementPathSyntaxError, ElementPathTypeError, \
    ElementPathValueError, ElementPathLocaleError, UnsupportedFeatureError

from .xpath_context import XPathContext, XPathSchemaContext
from .xpath_nodes import XPathNode, DocumentNode, ElementNode, AttributeNode, \
    NamespaceNode,  CommentNode, ProcessingInstructionNode, TextNode, \
    LazyElementNode, SchemaElementNode
from .tree_builders import get_node_tree, build_node_tree, build_lxml_node_tree, \
    build_schema_node_tree
from .xpath_tokens import XPathToken, XPathFunction
from .xpath1 import XPath1Parser
from .xpath2 import XPath2Parser
from .xpath_selectors import select, iter_select, Selector
from .schema_proxy import AbstractSchemaProxy
from .regex import RegexError, translate_pattern, install_unicode_data, unicode_version

__all__ = ['datatypes', 'protocols', 'etree', 'ElementPathError', 'MissingContextError',
           'UnsupportedFeatureError', 'ElementPathKeyError',
           'ElementPathZeroDivisionError', 'ElementPathNameError',
           'ElementPathOverflowError', 'ElementPathRuntimeError', 'ElementPathSyntaxError',
           'ElementPathTypeError', 'ElementPathValueError', 'ElementPathLocaleError',
           'XPathContext', 'XPathSchemaContext', 'XPathNode', 'DocumentNode',
           'ElementNode', 'AttributeNode', 'NamespaceNode', 'CommentNode',
           'ProcessingInstructionNode', 'TextNode', 'LazyElementNode',
           'SchemaElementNode', 'get_node_tree', 'build_node_tree',
           'build_lxml_node_tree', 'build_schema_node_tree', 'XPathToken',
           'XPathFunction', 'XPath1Parser', 'XPath2Parser', 'select', 'iter_select',
           'Selector', 'AbstractSchemaProxy', 'RegexError', 'translate_pattern',
           'install_unicode_data', 'unicode_version']
