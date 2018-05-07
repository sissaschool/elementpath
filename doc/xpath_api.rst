Public XPath API
================

The package includes some classes and functions that implement XPath parsers and selectors.

XPath parsers
-------------

.. autoclass:: elementpath.XPath1Parser

.. autoclass:: elementpath.XPath2Parser


XPath selectors
---------------

.. autofunction:: elementpath.select

.. autofunction:: elementpath.iter_select

.. autoclass:: elementpath.Selector

    .. autoattribute:: namespaces
    .. automethod:: select
    .. automethod:: iter_select


XPath dynamic context
---------------------

.. autoclass:: elementpath.XPathContext

