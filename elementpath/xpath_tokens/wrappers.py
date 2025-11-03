#
# Copyright (c), 2018-2025, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from typing import Iterator

import elementpath.aliases as ta
from elementpath.namespaces import XPATH_FUNCTIONS_NAMESPACE, XSD_NAMESPACE
from elementpath.datatypes import AnyAtomicType
from .base import XPathToken


class ValueToken(XPathToken):
    """
    A dummy token for encapsulating a value.
    """
    symbol = '(value)'
    value: AnyAtomicType

    @property
    def source(self) -> str:
        return str(self.value)

    def evaluate(self, context: ta.ContextType = None) -> AnyAtomicType:
        return self.value

    def select(self, context: ta.ContextType = None) -> Iterator[AnyAtomicType]:
        if isinstance(self.value, list):
            yield from self.value
        else:
            yield self.value


class ProxyToken(XPathToken):
    """
    A token class for resolving collisions between other tokens that have
    the same symbol but are in different namespaces. It also resolves
    collisions of functions with names.
    """
    symbol = '(proxy)'

    def nud(self) -> XPathToken:
        if self.parser.next_token.symbol not in ('(', '#'):
            # Not a function call or reference, returns a name.
            return self.as_name()

        lookup_name = f'{{{self.namespace or XPATH_FUNCTIONS_NAMESPACE}}}{self.value}'
        try:
            token = self.parser.symbol_table[lookup_name](self.parser)
        except KeyError:
            if self.namespace == XSD_NAMESPACE:
                msg = f'unknown constructor function {self.symbol!r}'
            else:
                msg = f'unknown function {self.symbol!r}'
            raise self.error('XPST0017', msg) from None
        else:
            if self.parser.next_token.symbol == '#':
                return token

            res = token.nud()
            return res
