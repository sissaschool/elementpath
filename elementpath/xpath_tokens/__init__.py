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
from typing import Any

from .base import XPathToken
from .axes import XPathAxis
from .wrappers import ValueToken, ProxyToken
from .functions import XPathFunction
from .contructors import XPathConstructor
from .maps import XPathMap
from .arrays import XPathArray
from .sequences import XPathSequence

__all__ = ['XPathToken', 'XPathAxis', 'XPathFunction', 'XPathConstructor',
           'ValueToken', 'ProxyToken', 'XPathMap', 'XPathArray', 'XPathSequence',
           'TokenBaseClasses']


@dataclass(frozen=True, slots=True)
class TokenBaseClasses:
    """A register of available XPath token base classes."""
    base: type[XPathToken] = XPathToken
    function: type[XPathFunction] = XPathFunction
    axis: type[XPathAxis] = XPathAxis
    value: type[ValueToken] = ValueToken
    proxy: type[ProxyToken] = ProxyToken
    constructor: type[XPathConstructor] = XPathConstructor
    array: type[XPathArray] = XPathArray
    map: type[XPathMap] = XPathMap
    sequence: type[XPathSequence] = XPathSequence

    class __Name:
        name: str | None = None

    def __set_name__(self, owner, name):
        self.__Name.name = name

    def __set__(self, instance: Any, value: Any) -> None:
        raise AttributeError("Can't set attribute {!r}".format(self.__Name.name))

    def __delete__(self, instance: Any) -> None:
        raise AttributeError("Can't delete attribute {!r}".format(self.__Name.name))


XPathToken.token_types = TokenBaseClasses()
