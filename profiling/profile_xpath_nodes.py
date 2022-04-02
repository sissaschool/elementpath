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
from xml.etree import ElementTree

from elementpath.xpath_nodes import ElementType, is_element_node


def run_timeit(stmt='pass', setup='pass', number=1000):
    seconds = timeit(stmt, setup=setup, number=number)
    print("{}: {}s".format(stmt, seconds))


@profile
def element_nodes_objects():
    elem = ElementTree.XML(xml_source)
    nodes = [ElementType(e) for e in elem.iter()]
    return nodes


if __name__ == '__main__':
    print('*' * 62)
    print("*** Memory and timing profile of ElementNode class         ***")
    print('*' * 62)
    print()

    xml_source = '<a>' + '<b/>' * 2000 + '</a>'
    element_nodes_objects()

    root = ElementTree.XML(xml_source)
    setup = 'from __main__ import ElementNode, root, node, is_element_node'
    node = ElementType(root)

    NUMBER = 10000

    run_timeit('for e in root.iter(): e', setup, NUMBER)
    run_timeit('for e in root.iter(): ElementNode(e)', setup, NUMBER)
    run_timeit('for e in map(ElementNode, root.iter()): e', setup, NUMBER)

    run_timeit('for e in root: e', setup, NUMBER)
    run_timeit('for e in root: ElementNode(e)', setup, NUMBER)
    run_timeit('for e in map(ElementNode, root): e', setup, NUMBER)

    run_timeit('isinstance(node, ElementNode)', setup, NUMBER)
    run_timeit('is_element_node(root)', setup, NUMBER)
