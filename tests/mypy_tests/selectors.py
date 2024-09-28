#!/usr/bin/env python

def main() -> None:
    from xml.etree.ElementTree import XML
    import elementpath
    from elementpath import get_node_tree
    from elementpath.xpath3 import XPath3Parser

    root = XML('<a><b1/><b2><c1/><c2/></b2><b3/></a>')

    result = elementpath.select(root, '*')
    print(result)

    result = list(elementpath.iter_select(root, '*'))
    print(result)

    selector = elementpath.Selector('*')
    result = selector.select(root)
    print(result)

    result = list(selector.iter_select(root))
    print(result)

    result = elementpath.select(root, 'math:atan(1.0e0)', parser=XPath3Parser)
    print(result)

    root_node = get_node_tree(root)
    result = elementpath.select(root_node, '*')
    print(result)
    assert result == elementpath.select(root, '*')

    try:
        elementpath.select(1, '*')  # type: ignore[arg-type]
    except TypeError:
        pass


if __name__ == '__main__':
    main()
