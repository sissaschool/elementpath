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
from elementpath.xpath_nodes import get_node_tree


def run_timeit(stmt='pass', setup='pass', number=1000):
    seconds = timeit(stmt, setup=setup, number=number)
    print("{}: {}s ({} times, about {}s each)".format(stmt, seconds, number, seconds/number))


@profile
def create_element_tree(source):
    doc = etree.XML(source)
    return doc


@profile
def create_py_element_tree(source):
    doc = PyElementTree.XML(source)
    return doc


@profile
def create_xpath_tree(root_):
    node_tree = get_node_tree(root_)
    return node_tree


if __name__ == '__main__':
    print('*' * 60)
    print("*** Memory and timing profile of XPath node trees        ***")
    print('*' * 60)
    print()

    XML_DEPTH = 7
    XML_CHILDREN = 3
    SETUP = 'from __main__ import root, xpath_tree, get_node_tree'
    NUMBER = 5000

    chunk = 'lorem ipsum'
    for k in range(XML_DEPTH - 1, 0, -1):
        chunk = f'<a{k}>{chunk}</a{k}>' * XML_CHILDREN
    xml_source = f'<a0>{chunk}</a0>'

    root = create_element_tree(xml_source)
    create_py_element_tree(xml_source)
    xpath_tree = create_xpath_tree(root)

    run_timeit('get_node_tree(root)', SETUP, 100)
    run_timeit('for e in root.iter(): e', SETUP, NUMBER)
    run_timeit('for e in xpath_tree.iter(): e', SETUP, NUMBER)
