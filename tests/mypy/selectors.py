#!/usr/bin/env python

def main() -> None:
    from xml.etree.ElementTree import XML
    import elementpath

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


if __name__ == '__main__':
    main()
