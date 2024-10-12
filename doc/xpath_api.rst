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

    Helper methods for defining token classes:

    .. automethod:: axis
    .. automethod:: function


.. autoclass:: elementpath.XPath2Parser
.. autoclass:: elementpath.xpath3.XPath30Parser
.. autoclass:: elementpath.xpath3.XPath31Parser


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
This class is based on an abstract class :class:`elementpath.AbstractSchemaProxy`, that can be used for
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


XPath nodes
===========

XPath nodes are processed using a set of classes derived from
:class:`elementpath.XPathNode`. This class hierarchy is as simple
as possible, with a focus on speed a low memory consumption.

.. autoclass:: elementpath.XPathNode

The seven XPath node types:

.. autoclass:: elementpath.AttributeNode
.. autoclass:: elementpath.NamespaceNode
.. autoclass:: elementpath.TextNode
.. autoclass:: elementpath.CommentNode
.. autoclass:: elementpath.ProcessingInstructionNode
.. autoclass:: elementpath.ElementNode
.. autoclass:: elementpath.DocumentNode

There are also other two specialized versions of ElementNode
usable on specific cases:

.. autoclass:: elementpath.LazyElementNode
.. autoclass:: elementpath.SchemaElementNode


Node tree builders
==================

Node trees are automatically created during the initialization of an
:class:`elementpath.XPathContext`. But if you need to process the same XML data
more times there is an helper API for creating document or element based node trees:

.. autofunction:: elementpath.get_node_tree
.. autofunction:: elementpath.build_node_tree
.. autofunction:: elementpath.build_lxml_node_tree
.. autofunction:: elementpath.build_schema_node_tree


XPath regular expressions
=========================

.. autofunction:: elementpath.translate_pattern
.. autofunction:: elementpath.install_unicode_data
.. autofunction:: elementpath.unicode_version


Exception classes
=================

.. autoexception:: elementpath.ElementPathError
.. autoexception:: elementpath.MissingContextError
.. autoexception:: elementpath.UnsupportedFeatureError
.. autoexception:: elementpath.RegexError
.. autoexception:: elementpath.ElementPathLocaleError

There are also other exceptions, multiple derived from the base exception
:class:`elementpath.ElementPathError` and Python built-in exceptions:

.. autoexception:: elementpath.ElementPathKeyError
.. autoexception:: elementpath.ElementPathNameError
.. autoexception:: elementpath.ElementPathOverflowError
.. autoexception:: elementpath.ElementPathRuntimeError
.. autoexception:: elementpath.ElementPathSyntaxError
.. autoexception:: elementpath.ElementPathTypeError
.. autoexception:: elementpath.ElementPathValueError
.. autoexception:: elementpath.ElementPathZeroDivisionError
