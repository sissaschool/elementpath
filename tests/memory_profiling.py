#!/usr/bin/env python
#
# Copyright (c), 2018-2020, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
#

from memory_profiler import profile


# noinspection PyUnresolvedReferences
@profile(precision=3)
def elementpath_memory_usage():
    # Memory relevant standard library imports
    import pathlib
    import decimal
    import calendar
    import xml.etree.ElementTree
    import unicodedata

    # elementpath imports
    #
    # Note: comments out all subpackages imports in elementpath/__init__.py
    # to put in evidence the memory consumption of each subpackage.
    #
    import elementpath

    import elementpath.regex
    import elementpath.datatypes
    import elementpath.xpath_nodes
    import elementpath.xpath_context
    import elementpath.xpath_token
    import elementpath.xpath1
    import elementpath.xpath2

    # Optional elementpath imports
    import elementpath.xpath30
    import elementpath.xpath31


if __name__ == '__main__':
    elementpath_memory_usage()
