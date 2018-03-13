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
__version__ = '1.0'
__author__ = "Davide Brunato"
__contact__ = "brunato@sissa.it"
__copyright__ = "Copyright 2018, SISSA"
__license__ = "MIT"
__status__ = "Production/Stable"


from .exceptions import (
    ElementPathError, ElementPathSyntaxError, ElementPathNameError, ElementPathValueError, ElementPathTypeError
)
from .todp_parser import Token, Parser
from .xpath_token import is_etree_element, is_xpath_node, XPathToken
from .xpath_context import XPathContext
from .xpath1_parser import XPath1Parser
from .xpath2_parser import XPath2Parser


def select(elem, path, namespaces=None, parser=XPath2Parser, **kwargs):
    parser = parser(namespaces, **kwargs)
    root_token = parser.parse(path)
    context = XPathContext(elem)
    results = list(root_token.select(context))
    if len(results) == 1 and root_token.label in ('function', 'literal'):
        return results[0]
    else:
        return results


def iter_select(elem, path, namespaces=None, parser=XPath2Parser, **kwargs):
    parser = parser(namespaces, **kwargs)
    root_token = parser.parse(path)
    context = XPathContext(elem, variables=kwargs.get('variables'))
    return root_token.select(context)


class Selector(object):
    """
    XPath selector. For default uses XPath 2.0.

    :ivar path: The path expression string.
    :ivar namespaces:
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

    def select(self, elem):
        context = XPathContext(elem)
        results = list(self.root_token.select(context))
        if len(results) == 1 and self.root_token.label in ('function', 'literal'):
            return results[0]
        else:
            return results

    def iter_select(self, elem):
        context = XPathContext(elem)
        return self.root_token.select(context)
