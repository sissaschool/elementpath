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
# flake8: noqa

def profile_memory(func):
    def wrapper(*a, **kw):
        mem = this_process.memory_info().rss
        result = func(*a, **kw)
        mem = this_process.memory_info().rss - mem
        print("Memory usage by %s(): %.2f MB (%d)" % (func.__name__, mem / 1024 ** 2, mem))
        return result

    return wrapper


# noinspection PyUnresolvedReferences
@profile_memory
def elementpath_deps_memory_usage():
    # Memory relevant standard library imports
    import pathlib
    import decimal
    import calendar
    import xml.etree.ElementTree
    import unicodedata


@profile_memory
def elementpath_memory_usage():
    # elementpath imports
    #
    # Note: comments out all subpackages imports in elementpath/__init__.py
    # to put in evidence the memory consumption of each subpackage.
    #
    import elementpath

@profile_memory
def elementpath_subpackages_memory_usage():
    import elementpath.regex
    import elementpath.datatypes
    import elementpath.xpath_nodes
    import elementpath.xpath_context
    import elementpath.xpath_tokens
    import elementpath.xpath1
    import elementpath.xpath2


@profile_memory
def elementpath_optional_memory_usage():
    # Optional elementpath imports
    import elementpath.xpath30
    import elementpath.xpath31


if __name__ == '__main__':
    import os
    import psutil

    this_process = psutil.Process(os.getpid())

    elementpath_deps_memory_usage()
    elementpath_memory_usage()
    elementpath_subpackages_memory_usage()
    elementpath_optional_memory_usage()
