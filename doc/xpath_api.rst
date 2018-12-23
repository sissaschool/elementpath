****************
Public XPath API
****************

The package includes some classes and functions that implement XPath parsers, tokens, context and selectors.

XPath parsers
=============

.. autoclass:: elementpath.XPath1Parser

    .. autoattribute:: DEFAULT_NAMESPACES
    .. autoattribute:: version
    .. autoattribute:: default_namespace

    Helper methods for defining token classes:

    .. automethod:: axis
    .. automethod:: function


.. autoclass:: elementpath.XPath2Parser


XPath tokens
============

.. autoclass:: elementpath.XPathToken

    .. automethod:: evaluate
    .. automethod:: select

    Context manipulation helpers:

    .. automethod:: get_argument
    .. automethod:: get_comparison_data
    .. automethod:: get_results
    .. automethod:: adjust_datetime

    Error management helper:

    .. automethod:: error


XPath dynamic context
=====================

.. autoclass:: elementpath.XPathContext


XPath selectors
===============

.. autofunction:: elementpath.select

.. autofunction:: elementpath.iter_select

.. autoclass:: elementpath.Selector

    .. autoattribute:: namespaces
    .. automethod:: select
    .. automethod:: iter_select
