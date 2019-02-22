****************
Public XPath API
****************

The package includes some classes and functions that implement XPath selectors, parsers, tokens,
contexts and schema proxy.


XPath selectors
===============

.. autofunction:: elementpath.select

.. autofunction:: elementpath.iter_select

.. autoclass:: elementpath.Selector

    .. autoattribute:: namespaces
    .. automethod:: select
    .. automethod:: iter_select


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


XPath contexts
==============

.. autoclass:: elementpath.XPathContext
.. autoclass:: elementpath.XPathSchemaContext


XML Schema proxy
================

The XPath 2.0 parser can be interfaced with an XML Schema processor through a schema proxy.
An :class:`XMLSchemaProxy` class is defined for interfacing schemas created with the *xmlschema* package.
This class is based on an abstract class :class:`AbstractSchemaProxy`, that can be used for
implementing concrete interfaces to other types of XML Schema processors.

.. autoclass:: elementpath.XMLSchemaProxy

.. autoclass:: elementpath.AbstractSchemaProxy

    .. automethod:: get_context
    .. automethod:: get_type
    .. automethod:: get_attribute
    .. automethod:: get_element
    .. automethod:: get_element
    .. automethod:: is_instance
    .. automethod:: cast_as
    .. automethod:: is_instance
    .. automethod:: iter_atomic_types
    .. automethod:: get_primitive_type
