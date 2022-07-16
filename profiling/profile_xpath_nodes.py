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
import sys
from timeit import timeit
from memory_profiler import profile
import lxml.etree as etree

from elementpath import XPathNode, build_node_tree
from elementpath.etree import PyElementTree


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
def create_xpath_tree(et_root):
    node_tree = build_node_tree(et_root)
    return node_tree


# ep2.5 node checking function
def is_xpath_node(obj):
    return isinstance(obj, XPathNode) or \
        hasattr(obj, 'tag') and hasattr(obj, 'attrib') and hasattr(obj, 'text') or \
        hasattr(obj, 'local_name') and hasattr(obj, 'type') and hasattr(obj, 'name') or \
        hasattr(obj, 'getroot') and hasattr(obj, 'parse') and hasattr(obj, 'iter')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--depth', type=int, default=7,
                        help="the depth of the test XML tree (7 for default)")
    parser.add_argument('--children', type=int, default=3,
                        help="the number of children for each element (3 for default)")
    parser.add_argument('--speed', action='store_true', default=False,
                        help="run also speed tests (disabled for default)")
    params = parser.parse_args()

    print('*' * 60)
    print("*** Memory and timing profile of XPath node trees        ***")
    print('*' * 60)
    print()

    SETUP = 'from __main__ import root, xpath_tree, build_node_tree, is_xpath_node, XPathNode'
    NUMBER = 5000

    chunk = 'lorem ipsum'
    for k in range(params.depth - 1, 0, -1):
        chunk = f'<a{k} b{k}="k">{chunk}</a{k}>' * params.children
    xml_source = f'<a0>{chunk}</a0>'

    root = create_element_tree(xml_source)
    create_py_element_tree(xml_source)
    xpath_tree = create_xpath_tree(root)

    if not params.speed:
        print('Speed tests skipped ... exit')
        sys.exit()

    run_timeit('build_node_tree(root)', SETUP, 100)
    print()

    run_timeit('is_xpath_node(root)', SETUP, NUMBER)
    run_timeit('is_xpath_node(xpath_tree)', SETUP, NUMBER)
    run_timeit('isinstance(xpath_tree, XPathNode)', SETUP, NUMBER)
    print()

    run_timeit('for e in root.iter(): e', SETUP, NUMBER)
    run_timeit('for e in xpath_tree.iter(): e', SETUP, NUMBER)
    print()

    run_timeit('for e in root.iter(): is_xpath_node(e)', SETUP, NUMBER)
    run_timeit('for e in xpath_tree.iter(): isinstance(e, XPathNode)', SETUP, NUMBER)
