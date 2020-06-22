#
# Copyright (c), 2018-2020, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from .xpath_context import XPathContext
from .xpath2_parser import XPath2Parser as XPath2Parser


def create_xpath_contexts(root, namespaces, parser, **kwargs):
    """Helper method that returns the static context and the dynamic context."""
    context_kwargs = {
        'item': kwargs.pop('item', None),
        'position': kwargs.pop('position', 1),
        'size': kwargs.pop('size', 1),
        'axis': kwargs.pop('axis', None),
        'current_dt': kwargs.pop('current_dt', None),
        'timezone': kwargs.pop('timezone', None),
    }
    variable_values = kwargs.pop('variable_values', None)
    variables = kwargs.pop('variables', variable_values)

    parser = (parser or XPath2Parser)(namespaces, variables=variables, **kwargs)
    if not variable_values and variables and parser.variables != variables:
        context = XPathContext(root, variable_values=variables, **context_kwargs)
    else:
        context = XPathContext(root, variable_values=variable_values, **context_kwargs)

    return parser, context


def select(root, path, namespaces=None, parser=None, **kwargs):
    """
    XPath selector function that apply a *path* expression on *root* Element.

    :param root: an Element or ElementTree instance.
    :param path: the XPath expression.
    :param namespaces: a dictionary with mapping from namespace prefixes into URIs.
    :param parser: the parser class to use, that is :class:`XPath2Parser` for default.
    :param kwargs: other optional parameters for the parser instance or the dynamic \
    context. Common parameters are passed to the parser instance.
    :return: a list with XPath nodes or a basic type for expressions based \
    on a function or literal.
    """
    parser, context = create_xpath_contexts(root, namespaces, parser, **kwargs)
    root_token = parser.parse(path)
    return root_token.get_results(context)


def iter_select(root, path, namespaces=None, parser=None, **kwargs):
    """
    A function that creates an XPath selector generator for apply a *path* expression
    on *root* Element.

    :param root: an Element or ElementTree instance.
    :param path: the XPath expression.
    :param namespaces: a dictionary with mapping from namespace prefixes into URIs.
    :param parser: the parser class to use, that is :class:`XPath2Parser` for default.
    :param kwargs: other optional parameters for the parser instance or the dynamic \
    context. Common parameters are passed to the parser instance.
    :return: a generator of the XPath expression results.
    """
    parser, context = create_xpath_contexts(root, namespaces, parser, **kwargs)
    root_token = parser.parse(path)
    return root_token.select_results(context)


class Selector(object):
    """
    XPath selector class. Create an instance of this class if you want to apply an XPath
    selector to several target data.

    :param path: the XPath expression.
    :param namespaces: a dictionary with mapping from namespace prefixes into URIs.
    :param parser: the parser class to use, that is :class:`XPath2Parser` for default.
    :param kwargs: other optional parameters for the XPath parser instance.

    :ivar path: the XPath expression.
    :vartype path: str
    :ivar parser: the parser instance.
    :vartype parser: XPath1Parser or XPath2Parser
    :ivar root_token: the root of tokens tree compiled from path.
    :vartype root_token: XPathToken
    """
    _variable_values = None  # For backward compatibility

    def __init__(self, path, namespaces=None, parser=None, **kwargs):
        self.parser = (parser or XPath2Parser)(namespaces, **kwargs)
        if self.parser.variables and kwargs['variables'] != self.parser.variables:
            self._variable_values = kwargs['variables']

        self.path = path
        self.root_token = self.parser.parse(path)

    def __repr__(self):
        return u'%s(path=%r, parser=%s)' % (
            self.__class__.__name__, self.path, self.parser.__class__.__name__
        )

    @property
    def namespaces(self):
        """A dictionary with mapping from namespace prefixes into URIs."""
        return self.parser.namespaces

    def select(self, root, **kwargs):
        """
        Applies the instance's XPath expression on *root* Element.

        :param root: an Element or ElementTree instance.
        :param kwargs: other optional parameters for the XPath dynamic context.
        :return: a list with XPath nodes or a basic type for expressions based on \
        a function or literal.
        """
        if 'variable_values' not in kwargs and self._variable_values:
            kwargs['variable_values'] = self._variable_values

        context = XPathContext(root, **kwargs)
        return self.root_token.get_results(context)

    def iter_select(self, root, **kwargs):
        """
        Creates an XPath selector generator for apply the instance's XPath expression
        on *root* Element.

        :param root: an Element or ElementTree instance.
        :param kwargs: other optional parameters for the XPath dynamic context.
        :return: a generator of the XPath expression results.
        """
        if 'variable_values' not in kwargs and self._variable_values:
            kwargs['variable_values'] = self._variable_values

        context = XPathContext(root, **kwargs)
        return self.root_token.select_results(context)
