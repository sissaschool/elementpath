*********
CHANGELOG
*********

`v4.6.0`_ (2024-10-27)
======================
* Fix XsdAttributeGroupProtocol
* Improve Unicode support with installable UnicodeData.txt versions
* Extend names disambiguation with a fix for issue #78
* Refactor tree builders to fix document position of tails (issue #79)

`v4.5.0`_ (2024-09-09)
======================
* Fix and clean node trees iteration methods (issue #72)
* Fix missing raw string for '[^\r\n]' (pull request #76)
* Full and more specific type annotations

`v4.4.0`_ (2024-03-11)
======================
* Improve stand-alone XPath functions builder (issue #70)
* Update tokens and parsers __repr__
* Fix static typing protocols to work with etree and XSD elements

`v4.3.0`_ (2024-02-17)
======================
* Change the purpose of the evaluation with a dynamic schema context
* Add a tox.ini testenv with Python 3.13 pre-releases

`v4.2.1`_ (2024-02-10)
======================
* Fix dynamic context initialization with lxml a non-root element (issue #71)
* Fix XP30+ function fn:function-lookup
* Fix XP30+ fn:unparsed-text, fn:unparsed-text-lines and fn:unparsed-text-available

`v4.2.0`_ (2024-02-03)
======================
* Drop support for Python 3.7
* Add *uri* and *fragment* options to dynamic context
* Make context root node not mandatory (issue #63)
* Add function objects constructor (issue #70)

`v4.1.5`_ (2023-07-25)
======================
* Fix typed value of ElementNode() if self.elem.text is None

`v4.1.4`_ (2023-06-26)
======================
* Fix select of prefixed names (issue #68)
* Fix zero length *xs:base64Binary* (pull request #69)

`v4.1.3`_ (2023-06-17)
======================
* Fix XP30+ fn:path (issue #67)
* Fix weak tests (issues #64 and #66)

`v4.1.2`_ (2023-04-28)
======================
* Add support for Python 3.12
* Fix self shortcut operator (adding is_schema_node() to node classes)

`v4.1.1`_ (2023-04-11)
======================
* Simplify type annotations for XSD datatypes
* Full test coverage of sequence type functions with bugfixes

`v4.1.0`_ (2023-03-21)
======================
* Refactor XPath function call (context=None only as keyword argument)
* Add external function support (issue #60)
* Some fixes to string representation and source property of tokens
* Extend documentation and tests
* Clean XSD datatypes hierarchy

`v4.0.1`_ (2023-02-02)
======================
* Fix packaging: include py.typed in package data
* Revert to comparison between xs:QName instances and strings

`v4.0.0`_ (2023-02-01)
======================
* First XPath 3.1 implementation (without UCA collation support)

`v3.0.2`_ (2022-08-12)
======================
* Extend root concept to subtrees used as root (e.g. XSD 1.1 assertions)
* Begin XPath 3.1 implementation adding XPathMap and XPathArray

`v3.0.1`_ (2022-07-23)
======================
* Fix of descendant path operator (issue #51)
* Add support for Python 3.11

`v3.0.0`_ (2022-07-16)
======================
* Transition to full XPath node implementation (more memory usage but
  better control and overall faster)
* Add etree.py module with a safe XML parser (ported from xmlschema)

`v2.5.3`_ (2022-05-30)
======================
* Fix unary path step operator (issue #46)
* Fix sphinx warnings *'reference target not found'* (issue #45)

`v2.5.2`_ (2022-05-17)
======================
* Include PR #43 with fixes for `XPathContext.iter_siblings()` (issues #42 and #44)

`v2.5.1`_ (2022-04-28)
======================
* Fix for failed floats equality tests (issue #41)
* Static typing tested with mypy==0.950

`v2.5.0`_ (2022-03-04)
======================
* Add XPath 3.0 support
* Better use of lxml.etree features
* Full coverage of W3C tests
* Drop support for Python 3.6

`v2.4.0`_ (2021-11-09)
======================
* Fix type annotations and going strict on parsers and other public classes
* Add XPathConstructor token class (subclass of XPathFunction)
* Last release for Python 3.6

`v2.3.2`_ (2021-09-16)
======================
* Make ElementProtocol and LxmlElementProtocol runtime checkable (only for Python 3.8+)
* Type annotations for all package public APIs

`v2.3.1`_ (2021-09-07)
======================
* Add LxmlElementProtocol
* Add pytest env to tox.ini (test issue #39)

`v2.3.0`_ (2021-09-01)
======================
* Add inline type annotations check support
* Add structural Protocol based type checks (effective for Python 3.8+)

`v2.2.3`_ (2021-06-16)
======================
* Add Python 3.10 in Tox and CI tests
* Apply __slots__ to TDOP and regex classes

`v2.2.2`_ (2021-05-03)
======================
* Fix issue sissaschool/xmlschema#243 (assert with xsi:nil usage)
* First implementation of XPath 3.0 fn:format-integer

`v2.2.1`_ (2021-03-24)
======================
* Add function signatures at token registration
* Some fixes to XPath tokens and more XPath 3.0 implementations

`v2.2.0`_ (2021-03-01)
======================
* Optimize TDOP parser's tokenizer
* Resolve ambiguities with operators and statements that are also names
* Merge with XPath 3.0/3.1 develop (to be completed)

`v2.1.4`_ (2021-02-09)
======================
* Add tests and apply small fixes to TDOP parser
* Fix wildcard selection of attributes (issue #35)

`v2.1.3`_ (2021-01-30)
======================
* Extend tests for XPath 2.0 with minor fixes
* Fix fn:round-half-to-even (issue #33)

`v2.1.2`_ (2021-01-22)
======================
* Extend tests for XPath 1.0/2.0 with minor fixes
* Fix for +/- prefix operators
* Fix for regex patterns anchors and binary datatypes

`v2.1.1`_ (2021-01-06)
======================
* Fix for issue #32 (test failure on missing locale setting)
* Extend tests for XPath 1.0 with minor fixes

`v2.1.0`_ (2021-01-05)
======================
* Create custom class hierarchy for XPath nodes that replaces named-tuples
* Bind attribute nodes, text nodes and namespace nodes to parent element (issue #31)

`v2.0.5`_ (2020-12-02)
======================
* Increase the speed of path step selection on large trees
* More tests and small fixes to XSD builtin datatypes

`v2.0.4`_ (2020-10-30)
======================
* Lazy tokenizer for parser classes in order to minimize import time

`v2.0.3`_ (2020-09-13)
======================
* Fix context handling in cycle statements
* Change constructor's label to 'constructor function'

`v2.0.2`_ (2020-09-03)
======================
* Add regex translator to package API
* More than 99% of W3C XPath 2.0 tests pass

`v2.0.1`_ (2020-08-24)
======================
* Add regex transpiler (for XPath/XQuery and XML Schema regular expressions)
* Hotfix for issue #30

`v2.0.0`_ (2020-08-13)
======================
* Extensive testing with W3C XPath 2.0 tests (~98% passed)
* Split context variables from in-scope variables (types)
* Add other XSD builtin atomic types

`v1.4.6`_ (2020-06-15)
======================
* Fix XPathContext to let the subclasses replace the XPath nodes iterator function

`v1.4.5`_ (2020-05-22)
======================
* Fix tokenizer and parsers for ambiguities between symbols and names

`v1.4.4`_ (2020-04-23)
======================
* Improve XPath context and axes processing
* Integrate pull requests and fix bug on predicate selector

`v1.4.3`_ (2020-03-18)
======================
* Fix PyPy 3 tests on xs:base64Binary and xs:hexBinary
* Separated the tests of schema proxy API and other schemas based tests

`v1.4.2`_ (2020-03-13)
======================
* Multiple XSD type associations on a token
* Extend xs:untypedAtomic type usage
* Increase the tests coverage to 95%

`v1.4.1`_ (2020-01-28)
======================
* Fix for node kind tests
* Fix for issue #17
* Update test dependencies
* Add PyPy3 to tests

`v1.4.0`_ (2019-12-31)
======================
* Remove Python 2 support
* Add TextNode node type
* Fix for issue #15 and for errors related to PR #16

`v1.3.3`_ (2019-12-17)
======================
* Fix 'attribute' multi-role token (axis and kind test)
* Fixes for issues #13 and #14

`v1.3.2`_ (2019-12-10)
======================
* Add token labels 'sequence types' and 'kind test' for callables that are not XPath functions
* Add missing XPath 2.0 functions
* Fix for issue #12

`v1.3.1`_ (2019-10-21)
======================
* Add test module for TDOP parser
* Fix for issue #10

`v1.3.0`_ (2019-10-11)
======================
* Improved schema proxy
* Improved XSD type matching using paths
* Cached parent path for XPathContext (only Python 3)
* Improve typed selection with TypedAttribute and TypedElement named-tuples
* Add iter_results to XPathContext
* Remove XMLSchemaProxy from package
* Fix descendant shortcut operator '//'
* Fix text() function
* Fix typed select of '(name)' token
* Fix 24-hour time for DateTime

`v1.2.1`_ (2019-08-30)
======================
* Hashable XSD datatypes classes
* Fix Duration types comparison

`v1.2.0`_ (2019-08-14)
======================
* Added special XSD datatypes
* Better handling of schema contexts
* Added validators for numeric types
* Fixed function conversion rules
* Fixed tests with lxml and XPath 1.0
* Added tests for uncovered code

`v1.1.8`_ (2019-05-20)
======================
* Added code coverage and flake8 checks
* Drop Python 3.4 support
* Use more specific XPath errors for functions and namespace resolving
* Fix for issue #4

`v1.1.7`_ (2019-04-25)
======================
* Added Parser.is_spaced() method for checking if the current token has extra spaces before or after
* Fixes for '/' and ':' tokens
* Fixes for fn:max() and fn:min() functions

`v1.1.6`_ (2019-03-28)
======================
* Fixes for XSD datatypes
* Minor fixes after a first test run with Python v3.8a3

`v1.1.5`_ (2019-02-23)
======================
* Differentiated unordered XPath gregorian types from ordered types for XSD
* Fix issue #2

`v1.1.4`_ (2019-02-21)
======================
* Implementation of a full Static Analysis Phase at parse() level
* Schema-based static analysis for XPath 2.0 parsers using schema contexts
* Added ``XPathSchemaContext`` class for processing schema contexts
* Added atomization() and get_atomized_operand() helpers to XPathToken
* Fix value comparison operators

`v1.1.3`_ (2019-02-06)
======================
* Fix for issue #1
* Added fn:static-base-uri() and fn:resolve-uri()
* Fixes to XPath 1.0 functions for compatibility mode

`v1.1.2`_ (2019-01-30)
======================
* Fixes for XSD datatypes
* Change the default value of *default_namespace* argument of XPath2Parser to ``None``

`v1.1.1`_ (2019-01-19)
======================
* Improvements and fixes for XSD datatypes
* Rewritten AbstractDateTime for supporting years with value > 9999
* Added fn:dateTime()

`v1.1.0`_ (2018-12-23)
======================
* Almost full implementation of XPath 2.0
* Extended XPath errors management
* Add XSD datatypes for data/time builtins
* Add constructors for XSD builtins

`v1.0.12`_ (2018-09-01)
=======================
* Fixed the default namespace use for names without prefix.

`v1.0.11`_ (2018-07-25)
=======================
* Added two recursive protected methods to context class
* Minor fixes for context and helpers

`v1.0.10`_ (2018-06-15)
=======================
* Updated TDOP parser and implemented token classes serialization

`v1.0.8`_ (2018-06-13)
======================
* Fixed token classes creation for parsers serialization

`v1.0.7`_ (2018-05-07)
======================
* Added autodoc based manual with Sphinx

`v1.0.6`_ (2018-05-02)
======================
* Added tox testing
* Improved the parser class with raw_advance method

`v1.0.5`_ (2018-03-31)
======================
* Added n.10 XPath 2.0 functions for strings
* Fix README.rst for right rendering in PyPI
* Added ElementPathMissingContextError exception for a correct handling of static context evaluation

`v1.0.4`_ (2018-03-27)
======================
* Fixed packaging ('packages' argument in setup.py).

`v1.0.3`_ (2018-03-27)
======================
* Fixed the effective boolean value for a list containing an empty string.

`v1.0.2`_ (2018-03-27)
======================
* Add QName parsing like in the ElementPath library (usage regulated by a *strict* flag).

`v1.0.1`_ (2018-03-27)
======================
* Some bug fixes for attributes selection.

`v1.0.0`_ (2018-03-26)
======================
* First stable version.


.. _v1.0.0: https://github.com/sissaschool/elementpath/commit/b28da83
.. _v1.0.1: https://github.com/sissaschool/elementpath/compare/v1.0.0...v1.0.1
.. _v1.0.2: https://github.com/sissaschool/elementpath/compare/v1.0.1...v1.0.2
.. _v1.0.3: https://github.com/sissaschool/elementpath/compare/v1.0.2...v1.0.3
.. _v1.0.4: https://github.com/sissaschool/elementpath/compare/v1.0.3...v1.0.4
.. _v1.0.5: https://github.com/sissaschool/elementpath/compare/v1.0.4...v1.0.5
.. _v1.0.6: https://github.com/sissaschool/elementpath/compare/v1.0.5...v1.0.6
.. _v1.0.7: https://github.com/sissaschool/elementpath/compare/v1.0.6...v1.0.7
.. _v1.0.8: https://github.com/sissaschool/elementpath/compare/v1.0.7...v1.0.8
.. _v1.0.10: https://github.com/sissaschool/elementpath/compare/v1.0.8...v1.0.10
.. _v1.0.11: https://github.com/sissaschool/elementpath/compare/v1.0.10...v1.0.11
.. _v1.0.12: https://github.com/sissaschool/elementpath/compare/v1.0.11...v1.0.12
.. _v1.1.0: https://github.com/sissaschool/elementpath/compare/v1.0.12...v1.1.0
.. _v1.1.1: https://github.com/sissaschool/elementpath/compare/v1.1.0...v1.1.1
.. _v1.1.2: https://github.com/sissaschool/elementpath/compare/v1.1.1...v1.1.2
.. _v1.1.3: https://github.com/sissaschool/elementpath/compare/v1.1.2...v1.1.3
.. _v1.1.4: https://github.com/sissaschool/elementpath/compare/v1.1.3...v1.1.4
.. _v1.1.5: https://github.com/sissaschool/elementpath/compare/v1.1.4...v1.1.5
.. _v1.1.6: https://github.com/sissaschool/elementpath/compare/v1.1.5...v1.1.6
.. _v1.1.7: https://github.com/sissaschool/elementpath/compare/v1.1.6...v1.1.7
.. _v1.1.8: https://github.com/sissaschool/elementpath/compare/v1.1.7...v1.1.8
.. _v1.1.9: https://github.com/sissaschool/elementpath/compare/v1.1.8...v1.1.9
.. _v1.2.0: https://github.com/sissaschool/elementpath/compare/v1.1.9...v1.2.0
.. _v1.2.1: https://github.com/sissaschool/elementpath/compare/v1.2.0...v1.2.1
.. _v1.3.0: https://github.com/sissaschool/elementpath/compare/v1.2.1...v1.3.0
.. _v1.3.1: https://github.com/sissaschool/elementpath/compare/v1.3.0...v1.3.1
.. _v1.3.2: https://github.com/sissaschool/elementpath/compare/v1.3.1...v1.3.2
.. _v1.3.3: https://github.com/sissaschool/elementpath/compare/v1.3.2...v1.3.3
.. _v1.4.0: https://github.com/sissaschool/elementpath/compare/v1.3.3...v1.4.0
.. _v1.4.1: https://github.com/sissaschool/elementpath/compare/v1.4.0...v1.4.1
.. _v1.4.2: https://github.com/sissaschool/elementpath/compare/v1.4.1...v1.4.2
.. _v1.4.3: https://github.com/sissaschool/elementpath/compare/v1.4.2...v1.4.3
.. _v1.4.4: https://github.com/sissaschool/elementpath/compare/v1.4.3...v1.4.4
.. _v1.4.5: https://github.com/sissaschool/elementpath/compare/v1.4.4...v1.4.5
.. _v1.4.6: https://github.com/sissaschool/elementpath/compare/v1.4.5...v1.4.6
.. _v2.0.0: https://github.com/sissaschool/elementpath/compare/v1.4.6...v2.0.0
.. _v2.0.1: https://github.com/sissaschool/elementpath/compare/v2.0.0...v2.0.1
.. _v2.0.2: https://github.com/sissaschool/elementpath/compare/v2.0.1...v2.0.2
.. _v2.0.3: https://github.com/sissaschool/elementpath/compare/v2.0.2...v2.0.3
.. _v2.0.4: https://github.com/sissaschool/elementpath/compare/v2.0.3...v2.0.4
.. _v2.0.5: https://github.com/sissaschool/elementpath/compare/v2.0.4...v2.0.5
.. _v2.1.0: https://github.com/sissaschool/elementpath/compare/v2.0.5...v2.1.0
.. _v2.1.1: https://github.com/sissaschool/elementpath/compare/v2.1.0...v2.1.1
.. _v2.1.2: https://github.com/sissaschool/elementpath/compare/v2.1.1...v2.1.2
.. _v2.1.3: https://github.com/sissaschool/elementpath/compare/v2.1.2...v2.1.3
.. _v2.1.4: https://github.com/sissaschool/elementpath/compare/v2.1.3...v2.1.4
.. _v2.2.0: https://github.com/sissaschool/elementpath/compare/v2.1.4...v2.2.0
.. _v2.2.1: https://github.com/sissaschool/elementpath/compare/v2.2.0...v2.2.1
.. _v2.2.2: https://github.com/sissaschool/elementpath/compare/v2.2.1...v2.2.2
.. _v2.2.3: https://github.com/sissaschool/elementpath/compare/v2.2.2...v2.2.3
.. _v2.3.0: https://github.com/sissaschool/elementpath/compare/v2.2.3...v2.3.0
.. _v2.3.1: https://github.com/sissaschool/elementpath/compare/v2.3.0...v2.3.1
.. _v2.3.2: https://github.com/sissaschool/elementpath/compare/v2.3.1...v2.3.2
.. _v2.4.0: https://github.com/sissaschool/elementpath/compare/v2.3.3...v2.4.0
.. _v2.5.0: https://github.com/sissaschool/elementpath/compare/v2.4.0...v2.5.0
.. _v2.5.1: https://github.com/sissaschool/elementpath/compare/v2.5.0...v2.5.1
.. _v2.5.2: https://github.com/sissaschool/elementpath/compare/v2.5.1...v2.5.2
.. _v2.5.3: https://github.com/sissaschool/elementpath/compare/v2.5.2...v2.5.3
.. _v3.0.0: https://github.com/sissaschool/elementpath/compare/v2.5.3...v3.0.0
.. _v3.0.1: https://github.com/sissaschool/elementpath/compare/v3.0.0...v3.0.1
.. _v3.0.2: https://github.com/sissaschool/elementpath/compare/v3.0.1...v3.0.2
.. _v4.0.0: https://github.com/sissaschool/elementpath/compare/v3.0.2...v4.0.0
.. _v4.0.1: https://github.com/sissaschool/elementpath/compare/v4.0.0...v4.0.1
.. _v4.1.0: https://github.com/sissaschool/elementpath/compare/v4.0.1...v4.1.0
.. _v4.1.1: https://github.com/sissaschool/elementpath/compare/v4.1.0...v4.1.1
.. _v4.1.2: https://github.com/sissaschool/elementpath/compare/v4.1.1...v4.1.2
.. _v4.1.3: https://github.com/sissaschool/elementpath/compare/v4.1.2...v4.1.3
.. _v4.1.4: https://github.com/sissaschool/elementpath/compare/v4.1.3...v4.1.4
.. _v4.1.5: https://github.com/sissaschool/elementpath/compare/v4.1.4...v4.1.5
.. _v4.2.0: https://github.com/sissaschool/elementpath/compare/v4.1.5...v4.2.0
.. _v4.2.1: https://github.com/sissaschool/elementpath/compare/v4.2.0...v4.2.1
.. _v4.3.0: https://github.com/sissaschool/elementpath/compare/v4.2.1...v4.3.0
.. _v4.4.0: https://github.com/sissaschool/elementpath/compare/v4.3.0...v4.4.0
.. _v4.5.0: https://github.com/sissaschool/elementpath/compare/v4.4.0...v4.5.0
.. _v4.6.0: https://github.com/sissaschool/elementpath/compare/v4.5.0...v4.6.0
