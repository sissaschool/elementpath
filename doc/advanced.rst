***************
Advanced topics
***************

.. testsetup::

    from xml.etree import ElementTree
    from elementpath import XPath2Parser, XPathToken, XPathContext, get_node_tree


Parsing expressions
===================

An XPath expression (the *path*) is analyzed using a parser instance,
having as result a tree of tokens:

.. doctest::

    >>> from elementpath import XPath2Parser, XPathToken
    >>>
    >>> parser = XPath2Parser()
    >>> token = parser.parse('/root/(: comment :) child[@attr]')
    >>> isinstance(token, XPathToken)
    True
    >>> token
    _SolidusOperator(...)
    >>> str(token)
    "'/' operator"
    >>> token.tree
    '(/ (/ (root)) ([ (child) (@ (attr))))'
    >>> token.source
    '/root/child[@attr]'

Providing a wrong expression an error is raised:

.. doctest::

    >>> token = parser.parse('/root/#child2/@attr')
    Traceback (most recent call last):
      .........
    elementpath.exceptions.ElementPathSyntaxError: '#' unknown at line 1, column 7: [err:XPST0003] unknown symbol '#'

The result tree is also checked with a static evaluation, that uses only the information
provided by the parser instance (e.g. statically known namespaces).
In *elementpath* a parser instance represents the
`XPath static context <https://www.w3.org/TR/xpath-3/#static_context>`_.
Static evaluation is not based on any XML input data but permits to found many errors
related with operators and function arguments:

.. doctest::

    >>> token = parser.parse('1 + "1"')
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File ".../elementpath/xpath2/xpath2_parser.py", ..., in parse
        root_token.evaluate()  # Static context evaluation
      .........
    elementpath.exceptions.ElementPathTypeError: '+' operator at line 1, column 3: [err:XPTY0004] ...


Dynamic evaluation
==================

Evaluation on XML data is performed using the
`XPath dynamic context <https://www.w3.org/TR/xpath-3/#eval_context>`_,
represented by *XPathContext* objects.

.. doctest::

    >>> from xml.etree import ElementTree
    >>> from elementpath import XPathContext
    >>>
    >>> root = ElementTree.XML('<root><child/><child attr="10"/></root>')
    >>> context = XPathContext(root)
    >>> token.evaluate(context)
    [ElementNode(elem=<Element 'child' at ...)]

In this case an error is raised if you don't provide a context:

.. doctest::

    >>> token.evaluate()
    Traceback (most recent call last):
      .........
    elementpath.exceptions.MissingContextError: '/' operator at line 1, column 6: [err:XPDY0002] Dynamic context required for evaluate

Expressions that not depend on XML data can be evaluated also without a context:

.. doctest::

    >>> token = parser.parse('concat("foo", " ", "bar")')
    >>> token.evaluate()
    'foo bar'

For more details on parsing and evaluation of XPath expressions see the
`XPath processing model <https://www.w3.org/TR/xpath-3/#id-processing-model>`_.


Node trees
==========

In the `XPath Data Model <https://www.w3.org/TR/xpath-datamodel/>`_
there are `seven kinds of nodes <https://www.w3.org/TR/xpath-datamodel/#Nodehave>`_:
document, element, attribute, text, namespace, processing instruction, and comment.

For a fully compliant XPath processing all the seven node kinds have to be represented
and processed, considering theirs properties (called accessors) and their position in
the belonging document.

But the ElementTree components don’t implement all the necessary characteristics,
forcing to use workaround tricks, that make the code more complex.
So since version v3.0 the data processing is based on XPath node types, that act
as wrappers of elements of the input ElementTree structures.
Node trees building requires more time and memory for handling dynamic context and
for iterating the trees, but is overall fast because simplify the rest of the code.

Node trees are automatically created at dynamic context initialization:

.. doctest::

    >>> from xml.etree import ElementTree
    >>> from elementpath import XPathContext, get_node_tree
    >>>
    >>> root = ElementTree.XML('<root><child/><child attr="10"/></root>')
    >>> context = XPathContext(root)
    >>> context.root
    ElementNode(elem=<Element 'root' at ...>)
    >>> context.root.children
    [ElementNode(elem=<Element 'child' at ...>), ElementNode(elem=<Element 'child' at ...>)]

If the same XML data is applied several times for dynamic evaluation it maybe
convenient to build the node tree before, in the way to create it only once:

.. doctest::

    >>> root_node = get_node_tree(root)
    >>> context = XPathContext(root_node)
    >>> context.root is root_node
    True


The context root and the context item
=====================================

Selector functions and class simplify the XML data processing. Often you only
have to provide the root element and the path expression.

But other keyword arguments, related to parser or context initialization, can
be provided. Of these arguments the item has a particular relevance, because it
defines the initial context item for performing dynamic evaluation.

If you have this XML data:

.. doctest::

    >>> from xml.etree import ElementTree
    >>> from elementpath import select
    >>>
    >>> root = ElementTree.XML('<root><child1/><child2/><child3/></root>')

using a select on it with the self-shortcut expression, gives back the root
element:

.. doctest::

    >>> select(root, '.')
    [<Element 'root' at ...>]

But if you want to use a specific child as the initial context item you have
to provide the extra argument *item*:

.. doctest::

    >>> select(root, '.', item=root[1])
    [<Element 'child2' at ...>]

The same result can be obtained providing the same child element as argument *root*:

.. doctest::

    >>> select(root[1], '.')
    [<Element 'child2' at ...>]

But this is not always true, because in the latter case the evaluation is
done using a subtree of nodes:

.. doctest::

    >>> select(root, 'root()', item=root[1])
    [<Element 'root' at ...>]
    >>> select(root[1], 'root()')
    [<Element 'child2' at ...>]

Both choices can be useful, depends if you need to keep the whole tree or
to restrict the scope to a subtree.


The root document and the root element
======================================

Canonically the dynamic evaluation is performed on an XML document, created
from an ElementTree instance:

.. doctest::

    >>> from xml.etree import ElementTree
    >>> from io import StringIO
    >>> from elementpath import select, XPathContext
    >>>
    >>> doc = ElementTree.parse(StringIO('<root><child1/><child2/><child3/></root>'))
    >>> doc
    <xml.etree.ElementTree.ElementTree object at ...>

In this case a document node is created at context initialization and the
context item is not set:

.. doctest::

    >>> context = XPathContext(doc)
    >>> context.root
    DocumentNode(document=<xml.etree.ElementTree.ElementTree object at ...>)
    >>> context.item is None
    True

Providing a root element the document is not created and the context item is
set to root element node:

.. doctest::

    >>> root = ElementTree.XML('<root><child1/><child2/><child3/></root>')
    >>> context = XPathContext(root)
    >>> context.root
    ElementNode(elem=<Element 'root' at ...>)
    >>> context.item is context.root
    True

Exception to this is if XML data root has siblings and if you process
the data with lxml:

.. doctest::

    >>> import lxml.etree as etree
    >>> root = etree.XML('<!-- comment --><root><child/></root>')
    >>> context = XPathContext(root)
    >>> context.root
    DocumentNode(document=<lxml.etree._ElementTree object at ...>)
    >>> context.item
    ElementNode(elem=<Element root at ...>)

