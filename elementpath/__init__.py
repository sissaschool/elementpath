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


from .exceptions import ElementPathError, ElementPathSyntaxError, ElementPathValueError
from .todp_parser import Token, Parser
from .xpath1 import XPathToken, XPath1Parser
from .xpath2 import XPath2Parser


###
# XPath selectors
#
def relative_path(path, levels, namespaces=None, parser=XPath2Parser):
    """
    Return a relative XPath expression.

    :param path: An XPath expression.
    :param levels: Number of path levels to remove.
    :param namespaces: Is an optional mapping from namespace prefix \
    to full qualified name.
    :param parser: Is an optional XPath parser class. If not given the XPath2Parser is used.
    :return: A string with a relative XPath expression.
    """
    token_tree = parser(namespaces).parse(path)
    path_parts = [t.value for t in token_tree.iter()]
    i = 0
    if path_parts[0] == '.':
        i += 1
    if path_parts[i] == '/':
        i += 1
    for value in path_parts[i:]:
        if levels <= 0:
            break
        if value == '/':
            levels -= 1
        i += 1
    return ''.join(path_parts[i:])


class XPathSelector(object):
    """

    """
    def __init__(self, path, namespaces=None, parser=XPath2Parser):
        self.path = path
        self.parser = parser(namespaces)
        self._selector = self.parser.parse(path)

    def __repr__(self):
        return u'%s(path=%r, namespaces=%r, parser=%s)' % (
            self.__class__.__name__, self.path, self.namespaces, self.parser.__class__.__name__
        )

    @property
    def namespaces(self):
        return self.parser.namespaces

    def iter_select(self, context):
        return self._selector.iter_select(context)


_selector_cache = {}


def element_path_iterfind(context, path, namespaces=None):
    if path[:1] == "/":
        path = "." + path

    path_key = (id(context), path)
    try:
        return _selector_cache[path_key].iter_select(context)
    except KeyError:
        pass

    parser = XPath1Parser(namespaces)
    selector = parser.parse(path)
    if len(_selector_cache) > 100:
        _selector_cache.clear()
    _selector_cache[path] = selector
    return selector.iter_select(context)


class ElementPathMixin(object):
    """
    Mixin class that defines the ElementPath API.
    """
    @property
    def tag(self):
        return getattr(self, 'name')

    @property
    def attrib(self):
        return getattr(self, 'attributes')

    def iterfind(self, path, namespaces=None):
        """
        Generates all matching XSD/XML element declarations by path.

        :param path: is an XPath expression that considers the schema as the root element \
        with global elements as its children.
        :param namespaces: is an optional mapping from namespace prefix to full name.
        :return: an iterable yielding all matching declarations in the XSD/XML order.
        """
        return element_path_iterfind(self, path, namespaces or self.xpath_namespaces)

    def find(self, path, namespaces=None):
        """
        Finds the first XSD/XML element or attribute matching the path.

        :param path: is an XPath expression that considers the schema as the root element \
        with global elements as its children.
        :param namespaces: an optional mapping from namespace prefix to full name.
        :return: The first matching XSD/XML element or attribute or ``None`` if there is not match.
        """
        return next(element_path_iterfind(self, path, namespaces or self.xpath_namespaces), None)

    def findall(self, path, namespaces=None):
        """
        Finds all matching XSD/XML elements or attributes.

        :param path: is an XPath expression that considers the schema as the root element \
        with global elements as its children.
        :param namespaces: an optional mapping from namespace prefix to full name.
        :return: a list containing all matching XSD/XML elements or attributes. An empty list \
        is returned if there is no match.
        """
        return list(element_path_iterfind(self, path, namespaces or self.xpath_namespaces))

    @property
    def xpath_namespaces(self):
        if hasattr(self, 'namespaces'):
            namespaces = {k: v for k, v in self.namespaces.items() if k}
            if hasattr(self, 'xpath_default_namespace'):
                namespaces[''] = self.xpath_default_namespace
            return namespaces

    def iter(self, name=None):
        raise NotImplementedError

    def iterchildren(self, name=None):
        raise NotImplementedError
