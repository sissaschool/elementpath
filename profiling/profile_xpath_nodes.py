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

from elementpath.etree import PyElementTree
from elementpath.xpath_nodes import build_nodes


@profile
def create_xpath_tree():
    node_tree = build_nodes(root)
    return node_tree


def run_timeit(stmt='pass', setup='pass', number=1000):
    seconds = timeit(stmt, setup=setup, number=number)
    print("{}: {}s ({} times, about {}s each)".format(stmt, seconds, number, seconds/number))


@profile
def create_element_tree():
    doc = etree.XML(xml_source)
    return doc


@profile
def create_py_element_tree():
    doc = PyElementTree.XML(xml_source)
    return doc


if __name__ == '__main__':
    print('*' * 60)
    print("*** Memory and timing profile of XPath node trees        ***")
    print('*' * 60)
    print()

    xml_source = '<a>' + '<b>lorem ipsum</b>' * 1000 + '</a>'
    root = create_element_tree()
    create_py_element_tree()
    xpath_tree = create_xpath_tree()

    setup = 'from __main__ import root, xpath_tree, build_nodes'
    NUMBER = 5000

    run_timeit('build_nodes(root)', setup, 100)
    run_timeit('for e in root.iter(): e', setup, NUMBER)
    run_timeit('for e in xpath_tree.iter(): e', setup, NUMBER)
    run_timeit('for e in xpath_tree.iter2(): e', setup, NUMBER)
