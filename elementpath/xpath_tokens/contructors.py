#
# Copyright (c), 2018-2025, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from typing import Any, Optional, Union

import elementpath.aliases as ta
import elementpath.datatypes as dt

from elementpath.exceptions import ElementPathError
from elementpath.xpath_context import XPathContext, XPathSchemaContext
from .functions import XPathFunction


class XPathConstructor(XPathFunction):
    """
    A token for processing XPath 2.0+ constructors.
    """
    type_class: type[dt.AnyAtomicType | dt.ListType]

    @staticmethod
    def cast(value: Any) -> ta.AtomicType:
        raise NotImplementedError()

    def nud(self) -> 'XPathConstructor':
        if not self.parser.parse_arguments:
            return self

        try:
            self.parser.advance('(')
            self[0:] = self.parser.expression(5),
            if self.parser.next_token.symbol == ',':
                msg = 'Too many arguments: expected at most 1 argument'
                raise self.error('XPST0017', msg)
            self.parser.advance(')')
        except SyntaxError:
            raise self.error('XPST0017') from None
        else:
            if self[0].symbol == '?':
                self.to_partial_function()
            return self

    def evaluate(self, context: Optional[XPathContext] = None) \
            -> Union[list[None], ta.AtomicType]:
        if self.context is not None:
            context = self.context

        arg = self.data_value(self.get_argument(context))
        if arg is None:
            return dt.empty_sequence
        elif arg == '?' and self[0].symbol == '?':
            raise self.error('XPTY0004', "cannot evaluate a partial function")

        try:
            if isinstance(arg, dt.UntypedAtomic):
                return self.cast(arg.value)
            return self.cast(arg)
        except ElementPathError:
            raise
        except (TypeError, ValueError) as err:
            if isinstance(context, XPathSchemaContext):
                return dt.empty_sequence
            raise self.error('FORG0001', err) from None
