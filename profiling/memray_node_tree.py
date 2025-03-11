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
if __name__ == '__main__':
    import argparse
    import pathlib
    import memray
    import xml.etree.ElementTree as ElementTree

    from elementpath import DocumentNode, ElementNode, \
        CommentNode, ProcessingInstructionNode, TextNode

    def get_element_tree(source):
        return ElementTree.XML(source)

    parser = argparse.ArgumentParser()
    parser.add_argument('--depth', type=int, default=7,
                        help="the depth of the test XML tree (7 for default)")
    parser.add_argument('--children', type=int, default=3,
                        help="the number of children for each element (3 for default)")
    params = parser.parse_args()

    print('*' * 64)
    print("*** Memory usage estimation of XPath node trees using memray ***")
    print('*' * 64)
    print()

    chunk = 'lorem ipsum'
    for k in range(params.depth - 1, 0, -1):
        chunk = f'<a{k} b{k}="k">{chunk}</a{k}>' * params.children
    xml_source = f'<a0>{chunk}</a0>'

    label = f'{params.depth}x{params.children}'

    outdir = pathlib.Path(__file__).parent.joinpath('out/')
    et_file = outdir.joinpath(f'memray-element-tree-{label}.bin')
    nt_file = outdir.joinpath(f'memray-node-tree-{label}.bin')

    if et_file.is_file():
        et_file.unlink()

    with memray.Tracker(et_file, memory_interval_ms=1, follow_fork=True):
        root = get_element_tree(xml_source)

    if nt_file.is_file():
        nt_file.unlink()

    with memray.Tracker(nt_file, follow_fork=True):
        namespaces = None
        position = 1

        def build_element_node() -> ElementNode:
            global position

            node = ElementNode(elem, parent, position)
            position += 1

            position += len(nsmap) if 'xml' in nsmap else len(nsmap) + 1
            position += len(elem.attrib)
            
            if elem.text is not None:
                node.children.append(TextNode(elem.text, node, position))
                position += 1

            return node

        # Common nsmap
        nsmap = {} if namespaces is None else dict(namespaces)

        if hasattr(root, 'parse'):
            root_node = parent = DocumentNode(root, position)
            position += 1

            elem = root.getroot()
            child = build_element_node()
            parent.children.append(child)
            parent = child
        else:
            elem = root
            parent = None
            root_node = parent = build_element_node()

        root_node.tree.namespaces = nsmap
        children = iter(elem)
        iterators = []
        ancestors = []

        while True:
            for elem in children:
                if not callable(elem.tag):
                    child = build_element_node()
                elif elem.tag.__name__ == 'Comment':  # type: ignore[attr-defined]
                    child = CommentNode(elem, parent, position)
                    position += 1
                else:
                    child = ProcessingInstructionNode(elem, parent, position)

                parent.children.append(child)
                if elem.tail is not None:
                    parent.children.append(TextNode(elem.tail, parent, position))
                    position += 1

                if len(elem):
                    ancestors.append(parent)
                    parent = child
                    iterators.append(children)
                    children = iter(elem)
                    break
            else:
                try:
                    children, parent = iterators.pop(), ancestors.pop()
                except IndexError:
                    break

    print(f"Number of elements: {sum(1 for _ in root.iter())}")
    print(f"Number of nodes: {sum(1 for _ in root_node.iter())}")

    element_nodes = list(x for x in root_node.iter() if isinstance(x, ElementNode))
    print(f"Number of element nodes: {len(element_nodes)}")
