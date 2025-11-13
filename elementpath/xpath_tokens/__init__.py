#
# Copyright (c), 2018-2025, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""
XPathToken class and derived classes for other XPath objects (functions, constructors,
axes, maps, arrays). XPath's error creation and node helper functions are embedded in
XPathToken class, in order to raise errors related to token instances.
"""
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any

import elementpath.aliases as ta
import elementpath.datatypes as dt

from .base import XPathToken
from .axes import XPathAxis
from .functions import XPathFunction
from .contructors import XPathConstructor
from .maps import XPathMap
from .arrays import XPathArray
from .tokens import ValueToken, ProxyToken, NameToken, \
    PrefixedReferenceToken, ExpandedNameToken

__all__ = ['XPathToken', 'XPathAxis', 'XPathFunction', 'XPathConstructor',
           'XPathMap', 'XPathArray', 'ValueToken', 'ProxyToken', 'NameToken',
           'PrefixedReferenceToken', 'ExpandedNameToken', 'TokenRegistry']

MakeSequenceType = Callable[[ta.SequenceArgType[Any]], dt.XPathSequence[Any]]


@dataclass(frozen=True, slots=True)
class TokenRegistry:
    """A registry of classes, helpers and instances used commonly by XPath tokens."""

    # Token base classes
    base_token: type[XPathToken] = XPathToken
    axis_token: type[XPathAxis] = XPathAxis
    function_token: type[XPathFunction] = XPathFunction
    constructor_token: type[XPathConstructor] = XPathConstructor
    array_token: type[XPathArray] = XPathArray
    map_token: type[XPathMap] = XPathMap
    value_token: type[ValueToken] = ValueToken
    proxy_token: type[ProxyToken] = ProxyToken
    name_token: type[NameToken] = NameToken
    prefixed_ref_token: type[PrefixedReferenceToken] = PrefixedReferenceToken
    expanded_name_token: type[ExpandedNameToken] = ExpandedNameToken

    # XPath sequences (formally introduced with XPath 4.0)
    empty_sequence: dt.EmptySequence = dt.empty_sequence
    sequence_class: type[dt.XPathSequence] = dt.XPathSequence

    class __Name:
        name: str | None = None

    def __set_name__(self, owner, name):
        self.__Name.name = name

    def __set__(self, instance: Any, value: Any) -> None:
        raise AttributeError("Can't set attribute {!r}".format(self.__Name.name))

    def __delete__(self, instance: Any) -> None:
        raise AttributeError("Can't delete attribute {!r}".format(self.__Name.name))


XPathToken.registry = TokenRegistry()
