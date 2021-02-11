***********
elementpath
***********

.. image:: https://img.shields.io/pypi/v/elementpath.svg
   :target: https://pypi.python.org/pypi/elementpath/
.. image:: https://img.shields.io/pypi/pyversions/elementpath.svg
   :target: https://pypi.python.org/pypi/elementpath/
.. image:: https://img.shields.io/pypi/implementation/elementpath.svg
   :target: https://pypi.python.org/pypi/elementpath/
.. image:: https://img.shields.io/badge/License-MIT-blue.svg
   :alt: MIT License
   :target: https://lbesson.mit-license.org/
.. image:: https://travis-ci.org/sissaschool/elementpath.svg?branch=master
   :target: https://travis-ci.org/sissaschool/elementpath
.. image:: https://img.shields.io/pypi/dm/elementpath.svg
   :target: https://pypi.python.org/pypi/elementpath/
.. image:: https://img.shields.io/badge/Maintained%3F-yes-green.svg
   :target: https://GitHub.com/Naereen/StrapDown.js/graphs/commit-activity

.. elementpath-introduction

The proposal of this package is to provide XPath 1.0 and 2.0 selectors for Python's ElementTree XML
data structures, both for the standard ElementTree library and for the
`lxml.etree <http://lxml.de>`_ library.

For `lxml.etree <http://lxml.de>`_ this package can be useful for providing XPath 2.0 selectors,
because `lxml.etree <http://lxml.de>`_ already has it's own implementation of XPath 1.0.


Installation and usage
======================

You can install the package with *pip* in a Python 3.6+ environment::

    pip install elementpath

For using it import the package and apply the selectors on ElementTree nodes:

>>> import elementpath
>>> from xml.etree import ElementTree
>>> root = ElementTree.XML('<A><B1/><B2><C1/><C2/><C3/></B2></A>')
>>> elementpath.select(root, '/A/B2/*')
[<Element 'C1' at ...>, <Element 'C2' at ...>, <Element 'C3' at ...>]

The *select* API provides the standard XPath result format that is a list or an elementary
datatype's value. If you want only to iterate over results you can use the generator function
*iter_select* that accepts the same arguments of *select*.

The selectors API works also using XML data trees based on the `lxml.etree <http://lxml.de>`_
library:

>>> import elementpath
>>> import lxml.etree as etree
>>> root = etree.XML('<A><B1/><B2><C1/><C2/><C3/></B2></A>')
>>> elementpath.select(root, '/A/B2/*')
[<Element C1 at ...>, <Element C2 at ...>, <Element C3 at ...>]

When you need to apply the same XPath expression to several XML data you can also use the
*Selector* class, creating an instance and then using it to apply the path on distinct XML
data:

>>> import elementpath
>>> import lxml.etree as etree
>>> selector = elementpath.Selector('/A/*/*')
>>> root = etree.XML('<A><B1/><B2><C1/><C2/><C3/></B2></A>')
>>> selector.select(root)
[<Element C1 at ...>, <Element C2 at ...>, <Element C3 at ...>]
>>> root = etree.XML('<A><B1><C0/></B1><B2><C1/><C2/><C3/></B2></A>')
>>> selector.select(root)
[<Element C0 at ...>, <Element C1 at ...>, <Element C2 at ...>, <Element C3 at ...>]

Public API classes and functions are described into the
`elementpath manual on the "Read the Docs" site <http://elementpath.readthedocs.io/en/latest/>`_.

Contributing
============

You can contribute to this package reporting bugs, using the issue tracker or by a pull request.
In case you open an issue please try to provide a test or test data for reproducing the wrong
behaviour. The provided testing code shall be added to the tests of the package.

The XPath parsers are based on an implementation of the Pratt's Top Down Operator Precedence parser.
The implemented parser includes some lookup-ahead features, helpers for registering tokens and for
extending language implementations. Also the token class has been generalized using a `MutableSequence`
as base class. See *tdop_parser.py* for the basic internal classes and *xpath1_parser.py* for extensions
and for a basic usage of the parser.

If you like you can use the basic parser and tokens provided by the *tdop_parser.py* module to
implement other types of parsers (I think it could be also a funny exercise!).


License
=======

This software is distributed under the terms of the MIT License.
See the file 'LICENSE' in the root directory of the present
distribution, or http://opensource.org/licenses/MIT.
