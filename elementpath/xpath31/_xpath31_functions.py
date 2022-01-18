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
XPath 3.1 implementation - part 3 (functions)
"""
from .xpath31_parser import XPath31Parser

method = XPath31Parser.method
function = XPath31Parser.function

XPath31Parser.unregister('string-join')


@method(function('string-join', nargs=(1, 2),
                 sequence_types=('xs:anyAtomicType*', 'xs:string', 'xs:string')))
def evaluate_string_join_function(self, context=None):
    items = [self.string_value(s) for s in self[0].select(context)]

    if len(self) == 1:
        return ''.join(items)
    return self.get_argument(context, 1, required=True, cls=str).join(items)
