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
from __future__ import unicode_literals

from .xpath_context import XPathContext
from .xpath2_parser import XPath2Parser as XPath2Parser


def select(root, path, namespaces=None, parser=None, **kwargs):
    """
    XPath selector function that apply a *path* expression on *root* Element.

    :param root: An Element or ElementTree instance.
    :param path: The XPath expression.
    :param namespaces: A dictionary with mapping from namespace prefixes into URIs.
    :param parser: The parser class to use, that is :class:`XPath2Parser` for default.
    :param kwargs: Other optional parameters for the XPath parser instance.
    :return: A list with XPath nodes or a basic type for expressions based \
    on a function or literal.
    """
    parser = (parser or XPath2Parser)(namespaces, **kwargs)
    root_token = parser.parse(path)
    context = XPathContext(root)
    return root_token.get_results(context)


def iter_select(root, path, namespaces=None, parser=None, **kwargs):
    """
    A function that creates an XPath selector generator for apply a *path* expression
    on *root* Element.

    :param root: An Element or ElementTree instance.
    :param path: The XPath expression.
    :param namespaces: A dictionary with mapping from namespace prefixes into URIs.
    :param parser: The parser class to use, that is :class:`XPath2Parser` for default.
    :param kwargs: Other optional parameters for the XPath parser instance.
    :return: A generator of the XPath expression results.
    """
    parser = (parser or XPath2Parser)(namespaces, **kwargs)
    root_token = parser.parse(path)
    context = XPathContext(root)
    return root_token.select_results(context)


class Selector(object):
    """
    XPath selector class. Create an instance of this class if you want to apply an XPath
    selector to several target data.

    :param path: The XPath expression.
    :param namespaces: A dictionary with mapping from namespace prefixes into URIs.
    :param parser: The parser class to use, that is :class:`XPath2Parser` for default.
    :param kwargs: Other optional parameters for the XPath parser instance.

    :ivar path: The XPath expression.
    :vartype path: str
    :ivar parser: The parser instance.
    :vartype parser: XPath1Parser or XPath2Parser
    :ivar root_token: The root of tokens tree compiled from path.
    :vartype root_token: XPathToken
    """
    def __init__(self, path, namespaces=None, parser=None, **kwargs):
        self.path = path
        self.parser = (parser or XPath2Parser)(namespaces, **kwargs)
        self.root_token = self.parser.parse(path)

    def __repr__(self):
        return u'%s(path=%r, parser=%s)' % (self.__class__.__name__, self.path, self.parser.__class__.__name__)

    @property
    def namespaces(self):
        """A dictionary with mapping from namespace prefixes into URIs."""
        return self.parser.namespaces

    def select(self, root):
        """
        Applies the instance's XPath expression on *root* Element.

        :param root: An Element or ElementTree instance.
        :return: A list with XPath nodes or a basic type for expressions based on \
        a function or literal.
        """
        context = XPathContext(root)
        return self.root_token.get_results(context)

    def iter_select(self, root):
        """
        Creates an XPath selector generator for apply the instance's XPath expression
        on *root* Element.

        :param root: An Element or ElementTree instance.
        :return: A generator of the XPath expression results.
        """
        context = XPathContext(root)
        return self.root_token.select_results(context)
