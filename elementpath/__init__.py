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
__version__ = '1.1.7'
__author__ = "Davide Brunato"
__contact__ = "brunato@sissa.it"
__copyright__ = "Copyright 2018-2019, SISSA"
__license__ = "MIT"
__status__ = "Production/Stable"


from .exceptions import *
from . import datatypes
from .tdop_parser import Token, Parser
from .xpath_context import XPathContext, XPathSchemaContext
from .xpath_helpers import AttributeNode, NamespaceNode
from .xpath_token import XPathToken
from .xpath1_parser import XPath1Parser
from .xpath2_constructors import XPath2Parser
from .xpath_selectors import select, iter_select, Selector
from .schema_proxy import AbstractSchemaProxy, XMLSchemaProxy
