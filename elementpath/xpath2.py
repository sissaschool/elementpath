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
from .xpath1 import XPath1Parser


class XPath2Parser(XPath1Parser):
    """
    XPath 2.0 expression parser class.
    """
    symbol_table = {k: v for k, v in XPath1Parser.symbol_table.items()}
    SYMBOLS = XPath1Parser.SYMBOLS + (
        'union', 'intersect', 'instance of', 'castable as', 'if', 'then', 'else', '$', 'for',
        'some', 'every', 'in', 'satisfies', 'validate', 'type', 'item', 'satisfies', 'context',
        'cast as', 'treat as', 'as', 'of', 'return', 'except', 'is', 'isnot', '<<', '>>', '?',
        'untyped'
    )
    RELATIVE_PATH_SYMBOLS = XPath1Parser.RELATIVE_PATH_SYMBOLS | {s for s in SYMBOLS if s.endswith("::")}

    @property
    def version(self):
        return '2.0'
