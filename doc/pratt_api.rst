******************
Pratt's parser API
******************

The TDOP (Top Down Operator Precedence) parser implemented within this library is
a variant of the original Pratt's parser based on a class for the parser and
meta-classes for tokens.

The parser base class includes helper functions for registering token classes,
the Pratt's methods and a regexp-based tokenizer builder. There are also additional
methods and attributes to help the developing of new parsers. Parsers can be defined
by class derivation and following a tokens registration procedure. These classes are
not available at package level but only within module `elementpath.tdop`.

Token base class
================

.. autoclass:: elementpath.tdop.Token

    .. autoattribute:: arity
    .. autoattribute:: tree
    .. autoattribute:: source

    .. automethod:: nud
    .. automethod:: led
    .. automethod:: evaluate
    .. automethod:: iter

    Helper methods for checking symbols and for error raising:

    .. automethod:: expected
    .. automethod:: unexpected
    .. automethod:: wrong_syntax
    .. automethod:: wrong_value
    .. automethod:: wrong_type


Parser base class
=================

.. autoclass:: elementpath.tdop.Parser

    .. autoattribute:: position

    Parsing methods:

    .. automethod:: parse
    .. automethod:: advance
    .. automethod:: advance_until
    .. automethod:: expression

    Helper methods for checking parser status:

    .. automethod:: is_source_start
    .. automethod:: is_line_start
    .. automethod:: is_spaced

    Helper methods for building new parsers:

    .. automethod:: register
    .. automethod:: unregister
    .. automethod:: duplicate
    .. automethod:: literal
    .. automethod:: nullary
    .. automethod:: prefix
    .. automethod:: postfix
    .. automethod:: infix
    .. automethod:: infixr
    .. automethod:: method
    .. automethod:: build
    .. automethod:: create_tokenizer

