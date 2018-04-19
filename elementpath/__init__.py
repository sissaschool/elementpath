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
__version__ = '1.0.6'
__author__ = "Davide Brunato"
__contact__ = "brunato@sissa.it"
__copyright__ = "Copyright 2018, SISSA"
__license__ = "MIT"
__status__ = "Production/Stable"


from .exceptions import *
from .tdop_parser import Token, Parser
from .xpath_helpers import AttributeNode, NamespaceNode, UntypedAtomic
from .xpath_token import XPathToken
from .xpath_context import XPathContext
from .xpath1_parser import XPath1Parser
from .xpath2_parser import XPath2Parser
from .schema_proxy import AbstractSchemaProxy, XMLSchemaProxy


def select(root, path, namespaces=None, parser=XPath2Parser, **kwargs):
    """
    XPath selector function.

    :param root: An Element or ElementTree instance.
    :param path: The XPath expression.
    :param namespaces: A dictionary with mapping from namespace prefixes into URIs.
    :param parser: The parser class to use, that is the XPath 2.0 class for default.
    :param kwargs: Other optional parameters for XPath parser class.
    """
    parser = parser(namespaces, **kwargs)
    root_token = parser.parse(path)
    context = XPathContext(root)
    return root_token.get_results(context)


def iter_select(root, path, namespaces=None, parser=XPath2Parser, **kwargs):
    """
    XPath selector generator function.

    :param root: An Element or ElementTree instance.
    :param path: The XPath expression.
    :param namespaces: A dictionary with mapping from namespace prefixes into URIs.
    :param parser: The parser class to use, that is the XPath 2.0 class for default.
    :param kwargs: Other optional parameters for XPath parser class.
    """

    parser = parser(namespaces, **kwargs)
    root_token = parser.parse(path)
    context = XPathContext(root)
    return root_token.select(context)


class Selector(object):
    """
    XPath selector class.

    :param path: The XPath expression.
    :param namespaces: A dictionary with mapping from namespace prefixes into URIs.
    :param parser: The parser class to use, that is the XPath 2.0 class for default.
    :param kwargs: Other optional parameters for XPath parser class.
    """
    def __init__(self, path, namespaces=None, parser=XPath2Parser, **kwargs):
        self.path = path
        self.parser = parser(namespaces, **kwargs)
        self.root_token = self.parser.parse(path)

    def __repr__(self):
        return u'%s(path=%r, namespaces=%r, parser=%s)' % (
            self.__class__.__name__, self.path, self.namespaces, self.parser.__class__.__name__
        )

    @property
    def namespaces(self):
        return self.parser.namespaces

    def select(self, root):
        context = XPathContext(root)
        return self.root_token.get_results(context)

    def iter_select(self, root):
        context = XPathContext(root)
        return self.root_token.select(context)
