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
"""Python 2/3 compatibility imports and definitions."""
import sys

PY3 = sys.version_info >= (3,)

if PY3:
    # noinspection PyCompatibility
    from urllib.parse import quote as urllib_quote

    unicode_chr = chr
else:
    # noinspection PyCompatibility
    from urllib2 import quote as urllib_quote

    unicode_chr = unichr
