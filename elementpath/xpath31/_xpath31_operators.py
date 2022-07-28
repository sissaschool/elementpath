#
# Copyright (c), 2018-2021, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
# type: ignore
"""
XPath 3.1 implementation - part 2 (operators and constructors)
"""
from ..xpath_token import XPathMap, XPathArray
from .xpath31_parser import XPath31Parser

register = XPath31Parser.register
method = XPath31Parser.method

register('map', bp=90, label='map', bases=(XPathMap,))
register('array', bp=90, label='array', bases=(XPathArray,))


###
# Square array constructor (pushed lazy)
@method('[')
def nud_array_constructor(self):
    if self.parser.version < '3.1':
        raise self.wrong_syntax()

    # Constructs an XPathArray token and returns it instead of the predicate
    token = XPathArray(self.parser)
    if token.parser.next_token.symbol not in (']', '(end)'):
        while True:
            token.append(self.parser.expression(5))
            if token.parser.next_token.symbol != ',':
                break
            token.parser.advance()

    token.parser.advance(']')
    return token
