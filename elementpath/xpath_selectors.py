#
# Copyright (c), 2018, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from typing import TYPE_CHECKING, Any, Dict, Optional

from elementpath._typing import Iterator
from elementpath.aliases import NamespacesType
from elementpath.tree_builders import RootArgType
from elementpath.xpath_context import XPathContext
from elementpath.xpath2 import XPath2Parser

if TYPE_CHECKING:
    from elementpath.xpath_tokens import ParserClassType


def select(root: Optional[RootArgType],
           path: str,
           namespaces: Optional[NamespacesType] = None,
           parser: Optional['ParserClassType'] = None,
           **kwargs: Any) -> Any:
    """
    XPath selector function that apply a *path* expression on *root* Element.

    :param root: the root of the XML document, usually an ElementTree instance or an \
    Element. A schema or a schema element can also be provided, or an already built \
    node tree. You can also provide `None`, in which case no XML root node is set in \
    the dynamic context, and you have to provide the keyword argument *item*.
    :param path: the XPath expression.
    :param namespaces: a dictionary with mapping from namespace prefixes into URIs.
    :param parser: the parser class to use, that is :class:`XPath2Parser` for default.
    :param kwargs: other optional parameters for the parser instance or the dynamic context.
    :return: a list with XPath nodes or a basic type for expressions based \
    on a function or literal.
    """
    context_kwargs = {
        'uri': kwargs.pop('uri', None),
        'fragment': kwargs.pop('fragment', False),
        'item': kwargs.pop('item', None),
        'position': kwargs.pop('position', 1),
        'size': kwargs.pop('size', 1),
        'axis': kwargs.pop('axis', None),
        'variables': kwargs.pop('variables', None),
        'current_dt': kwargs.pop('current_dt', None),
        'timezone': kwargs.pop('timezone', None),
    }
    _parser = (parser or XPath2Parser)(namespaces, **kwargs)
    root_token = _parser.parse(path)
    context = XPathContext(root, namespaces, **context_kwargs)
    return root_token.get_results(context)


def iter_select(root: Optional[RootArgType],
                path: str,
                namespaces: Optional[NamespacesType] = None,
                parser: Optional['ParserClassType'] = None,
                **kwargs: Any) -> Iterator[Any]:
    """
    A function that creates an XPath selector generator for apply a *path* expression
    on *root* Element.

    :param root: the root of the XML document, usually an ElementTree instance or an \
    Element. A schema or a schema element can also be provided, or an already built \
    node tree. You can also provide `None`, in which case no XML root node is set in \
    the dynamic context, and you have to provide the keyword argument *item*.
    :param path: the XPath expression.
    :param namespaces: a dictionary with mapping from namespace prefixes into URIs.
    :param parser: the parser class to use, that is :class:`XPath2Parser` for default.
    :param kwargs: other optional parameters for the parser instance or the dynamic context.
    :return: a generator of the XPath expression results.
    """
    context_kwargs = {
        'uri': kwargs.pop('uri', None),
        'fragment': kwargs.pop('fragment', False),
        'item': kwargs.pop('item', None),
        'position': kwargs.pop('position', 1),
        'size': kwargs.pop('size', 1),
        'axis': kwargs.pop('axis', None),
        'variables': kwargs.pop('variables', None),
        'current_dt': kwargs.pop('current_dt', None),
        'timezone': kwargs.pop('timezone', None),
    }
    _parser = (parser or XPath2Parser)(namespaces, **kwargs)
    root_token = _parser.parse(path)
    context = XPathContext(root, namespaces, **context_kwargs)
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
    def __init__(self, path: str,
                 namespaces: Optional[NamespacesType] = None,
                 parser: Optional['ParserClassType'] = None,
                 **kwargs: Any) -> None:

        self._variables = kwargs.pop('variables', None)  # For backward compatibility
        self.parser = (parser or XPath2Parser)(namespaces, **kwargs)
        self.path = path
        self.root_token = self.parser.parse(path)

    def __repr__(self) -> str:
        return '%s(path=%r, parser=%s)' % (
            self.__class__.__name__, self.path, self.parser.__class__.__name__
        )

    @property
    def namespaces(self) -> Dict[str, str]:
        """A dictionary with mapping from namespace prefixes into URIs."""
        return self.parser.namespaces

    def select(self, root: Optional[RootArgType], **kwargs: Any) -> Any:
        """
        Applies the instance's XPath expression on *root* Element.

        :param root: the root of the XML document, usually an ElementTree instance \
        or an Element.
        :param kwargs: other optional parameters for the XPath dynamic context.
        :return: a list with XPath nodes or a basic type for expressions based on \
        a function or literal.
        """
        if 'variables' not in kwargs and self._variables:
            kwargs['variables'] = self._variables

        context = XPathContext(root, **kwargs)
        return self.root_token.get_results(context)

    def iter_select(self, root: Optional[RootArgType], **kwargs: Any) -> Iterator[Any]:
        """
        Creates an XPath selector generator for apply the instance's XPath expression
        on *root* Element.

        :param root: the root of the XML document, usually an ElementTree instance \
        or an Element.
        :param kwargs: other optional parameters for the XPath dynamic context.
        :return: a generator of the XPath expression results.
        """
        if 'variables' not in kwargs and self._variables:
            kwargs['variables'] = self._variables

        context = XPathContext(root, **kwargs)
        return self.root_token.select_results(context)
