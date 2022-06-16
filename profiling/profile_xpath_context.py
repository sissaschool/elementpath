#!/usr/bin/env python
#
# Copyright (c), 2022, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from timeit import timeit
from memory_profiler import profile
import lxml.etree as etree

from elementpath import XPathContext


def run_timeit(stmt='pass', setup='pass', number=1000):
    seconds = timeit(stmt, setup=setup, number=number)
    print("{}: {}s".format(stmt, seconds))


@profile
def create_element_tree():
    doc = etree.XML(xml_source)
    return doc


@profile
def create_dynamic_context():
    ctx = XPathContext(root)
    return ctx


if __name__ == '__main__':
    print('*' * 62)
    print("*** Memory and timing profile of XPathContext         ***")
    print('*' * 62)
    print()

    xml_source = '<a>' + '<b>lorem ipsum</b>' * 1000 + '</a>'
    root = create_element_tree()
    context = create_dynamic_context()

    setup = 'from __main__ import root, context'
    NUMBER = 10000

    run_timeit('for e in root.iter(): e', setup, NUMBER)
    run_timeit('for e in context.root.iter(): e', setup, NUMBER)
    # run_timeit('for e in context.root.iter2(): e', setup, NUMBER)
