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
    .. automethod:: atomization
    .. automethod:: get_atomized_operand
    .. automethod:: iter_comparison_data
    .. automethod:: get_operands
    .. automethod:: get_results
    .. automethod:: select_results
    .. automethod:: adjust_datetime
    .. automethod:: use_locale

    Schema context methods
    .. automethod:: select_xsd_nodes
    .. automethod:: add_xsd_type
    .. automethod:: get_xsd_type
    .. automethod:: get_typed_node

    Data accessor helpers
    .. automethod:: data_value
    .. automethod:: boolean_value
    .. automethod:: string_value
    .. automethod:: number_value
    .. automethod:: schema_node_value

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

.. autoclass:: elementpath.AbstractSchemaProxy

    .. automethod:: bind_parser
    .. automethod:: get_context
    .. automethod:: find
    .. automethod:: get_type
    .. automethod:: get_attribute
    .. automethod:: get_element
    .. automethod:: is_instance
    .. automethod:: cast_as
    .. automethod:: iter_atomic_types
    .. automethod:: get_primitive_type


XPath nodes
===========

XPath nodes are processed using a set of classes derived from :class:`XPathNode`:

.. autoclass:: elementpath.AttributeNode
.. autoclass:: elementpath.TextNode
.. autoclass:: elementpath.TypedAttribute
.. autoclass:: elementpath.TypedElement
.. autoclass:: elementpath.NamespaceNode


XPath regular expressions
=========================

.. autofunction:: elementpath.translate_pattern


Exception classes
=================

.. autoexception:: elementpath.ElementPathError
.. autoexception:: elementpath.MissingContextError
.. autoexception:: elementpath.RegexError

There are also other exceptions, multiple derived from the base exception
:class:`ElementPathError` and Python built-in exceptions:

.. autoexception:: elementpath.ElementPathKeyError
.. autoexception:: elementpath.ElementPathLocaleError
.. autoexception:: elementpath.ElementPathNameError
.. autoexception:: elementpath.ElementPathOverflowError
.. autoexception:: elementpath.ElementPathSyntaxError
.. autoexception:: elementpath.ElementPathTypeError
.. autoexception:: elementpath.ElementPathValueError
.. autoexception:: elementpath.ElementPathZeroDivisionError
