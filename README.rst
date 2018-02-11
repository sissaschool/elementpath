***********
elementpath
***********

The library provides XPath selectors for Python's ElementTree XML libraries. Includes
a parser for XPath 1.0 and for XPath 2.0 and a mixin class for adding XPath selection
to other tree of elements.

Originally included into the `xmlschema <https://github.com/brunato/xmlschema>`_ library
this has been forked to a different package in order to provide an indipendent usage.

Installation and usage
======================

You can install the library with *pip* in a Python 2.7 or Python 3.3+ environment::

    pip install elementpath

Then import the selector from the library and apply XPath selection to ElementTree structures:

.. code-block:: pycon

    >>> from elementpath import XPathSelector
    >>> ....


License
-------
This software is distributed under the terms of the MIT License.
See the file 'LICENSE' in the root directory of the present
distribution, or http://opensource.org/licenses/MIT.
