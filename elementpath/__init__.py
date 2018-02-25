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

from abc import ABC, abstractmethod

from .exceptions import (
    ElementPathError, ElementPathSyntaxError, ElementPathNameError, ElementPathValueError, ElementPathTypeError
)
from .todp_parser import Token, Parser
from .xpath_base import is_etree_element, XPathToken, XPathContext
from .xpath1_parser import XPath1Parser
from .xpath2_parser import XPath2Parser


###
# XPath selectors
#
class Selector(object):
    """
    XPath selector. For default uses XPath 2.0.

    :ivar path: The path expression string.
    :ivar namespaces:
    """
    def __init__(self, path, namespaces=None, schema=None, parser=XPath2Parser):
        self.path = path
        self.parser = parser(namespaces)
        self.schema = schema
        self.root_token = self.parser.parse(path)

    def __repr__(self):
        return u'%s(path=%r, namespaces=%r, parser=%s)' % (
            self.__class__.__name__, self.path, self.namespaces, self.parser.__class__.__name__
        )

    @property
    def namespaces(self):
        return self.parser.namespaces

    def findall(self, elem):
        context = XPathContext(elem)
        return list(self.root_token.select(context))


def select(elem, path, namespaces=None, schema=None, parser=XPath2Parser):
    parser = parser(namespaces, schema)
    root_token = parser.parse(path)
    context = XPathContext(elem)
    return root_token.select(context)


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
        return select(self, path, namespaces or self.xpath_namespaces)

    def find(self, path, namespaces=None):
        """
        Finds the first XSD/XML element or attribute matching the path.

        :param path: is an XPath expression that considers the schema as the root element \
        with global elements as its children.
        :param namespaces: an optional mapping from namespace prefix to full name.
        :return: The first matching XSD/XML element or attribute or ``None`` if there is not match.
        """
        return next(select(self, path, namespaces or self.xpath_namespaces), None)

    def findall(self, path, namespaces=None):
        """
        Finds all matching XSD/XML elements or attributes.

        :param path: is an XPath expression that considers the schema as the root element \
        with global elements as its children.
        :param namespaces: an optional mapping from namespace prefix to full name.
        :return: a list containing all matching XSD/XML elements or attributes. An empty list \
        is returned if there is no match.
        """
        return list(select(self, path, namespaces or self.xpath_namespaces))

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


class AbstractSchemaProxy(ABC):
    """
    Proxy abstract class for binding a schema infoset to XPath selectors.
    """
    def __init__(self, schema):
        super(AbstractSchemaProxy, self).__init__()
        self._schema = schema

    @property
    @abstractmethod
    def root(self):
        pass

    @property
    @abstractmethod
    def xpath_namespaces(self):
        pass

    @property
    @abstractmethod
    def attributes(self):
        pass

    @property
    @abstractmethod
    def elements(self):
        pass

    @property
    @abstractmethod
    def types(self):
        pass

    @property
    @abstractmethod
    def substitution_groups(self):
        pass
