#!/usr/bin/env python

def main() -> None:
    from io import StringIO
    from xml.etree import ElementTree
    from elementpath import XPath2Parser, XPathContext, DocumentNode
    from elementpath import XPathToken

    parser = XPath2Parser()
    token = parser.parse('/root/(: comment :) child[@attr]')
    assert isinstance(token, XPathToken)
    assert token.tree == '(/ (/ (root)) ([ (child) (@ (attr))))'
    assert token.source == '/root/child[@attr]'

    root = ElementTree.XML('<root><child/><child attr="10"/></root>')
    context = XPathContext(root)
    value = token.evaluate(context)
    print(value)

    token = parser.parse('concat("foo", " ", "bar")')
    assert context.root is not None and token.evaluate() == 'foo bar'

    doc = ElementTree.parse(StringIO('<root><child1/><child2/><child3/></root>'))
    context = XPathContext(doc)  # error?
    assert isinstance(context.root, DocumentNode)
    assert context.document is context.root
    assert context.item is context.root


if __name__ == '__main__':
    main()
