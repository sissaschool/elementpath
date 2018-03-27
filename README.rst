###########
elementpath
###########

The proposal of this package is to provides XPath 1.0 and 2.0 selectors for Python's ElementTree XML
data structures, both for the standard ElementTree library and for the
`lxml.etree <http://lxml.de>`_ library.

For `lxml.etree <http://lxml.de>`_ this package could be useful for providing XPath 2.0 selectors,
because `lxml.etree <http://lxml.de>`_ already has it's own implementation of XPath 1.0.

The XPath 2.0 functions implementation is partial, due to wide number of functions that this language
provides. If you want you can contribute to add an unimplemented function see the section below.


Installation and usage
======================

You can install the package with *pip* in a Python 2.7 or Python 3.3+ environment::

    pip install elementpath

For using import the package and apply the selectors on ElementTree nodes:

.. code-block:: pycon

    >>> import elementpath
    >>> from xml.etree import ElementTree
    >>> xt = ElementTree.XML('<A><B1/><B2><C1/><C2/><C3/></B2></A>')
    >>> elementpath.select(xt, '/A/B2/*')
    ...


Public API
==========

The package includes some classes and functions for XPath parsers and selectors.

XPath1Parser
------------

.. code-block:: python

    class XPath1Parser(namespaces=None, variables=None, strict=True)

The XPath 1.0 parser. Provide a *namespaces* dictionary argument for mapping namespace prefixes to URI
inside expressions. With *variables* you can pass a dictionary with the static context's in-scope variables.
If *strict* is set to `False` the parser enables parsing of QNames, like the ElementPath library.

XPath2Parser
------------

.. code-block:: python

    XPath2Parser(namespaces=None, variables=None, strict=True, default_namespace='', function_namespace=None,
    schema=None,
    build_constructors=False, compatibility_mode=False)

The XPath 2.0 parser, that is the default parser. It has additional arguments compared to the parent class.
 *default_namespace* is the namespace to apply to unprefixed names. For default no namespace is applied
(the empty namespace '').
*function_namespace* is the default namespace to apply to unprefixed function names (the
"http://www.w3.org/2005/xpath-functions" namespace for default).
*schema* is an optional instance of an XML Schema interface as defined by the abstract class
`AbstractSchemaProxy`.
*build_constructors* indicates when to define constructor functions for the in-scope XSD atomic types.
The *compatibility_mode* flag indicates if the XPath 2.0 parser has to work in compatibility
with XPath 1.0.

XPath selectors
---------------

.. code-block:: python

   select(root, path, namespaces=None, schema=None, parser=XPath2Parser)

Apply *path* expression on *root* Element. The *root* argument can be an ElementTree instance
or an Element instance.
Returns a list with XPath nodes or a basic type for expressions based on a function or literal.

.. code-block:: python 

    iter_select(root, path, namespaces=None, schema=None, parser=XPath2Parser)

Iterator version of *select*, if you want to process each result one by one.

.. code-block:: python

    Selector(path, namespaces=None, schema=None, parser=XPath2Parser)

Create an instance of this class if you want to apply an XPath selector to several target data.
An instance provides *select* and *iter_select* methods with a *root* argument that has the
same meaning that as for the *select* API.


Contributing
============

You can contribute to this package reporting bugs, using the issue tracker or by a pull request.
In case you open an issue please try to provide a test or test data for reproducing the wrong
behaviour. The provided testing code shall be added to the tests of the package.

The XPath parsers are based on an implementation of the Pratt's Top Down Operator Precedence parser.
The implemented parser includes some lookup-ahead features, helpers for registering tokens and for
extending language implementations. Also the token class has been generalized using a `MutableSequence`
as base class. See *todp_parser.py* for the basic internal classes and *xpath1_parser.py* for extensions
and for a basic usage of the parser.

If you like you can use the basic parser and tokens provided by the *todp_parser.py* module to
implement other types of parsers (I think it could be also a funny exercise!).


License
=======
This software is distributed under the terms of the MIT License.
See the file 'LICENSE' in the root directory of the present
distribution, or http://opensource.org/licenses/MIT.
