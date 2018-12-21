******************
Pratt's parser API
******************

The TDOP (Top Down Operator Precedence) parser implemented within this library is a variant of the
original Pratt's parser based on a class for the parser and metaclasses for tokens.

The parser base class includes helper functions for registering token classes,
the Pratt's methods and a regexp-based tokenizer builder. There are also additional
methods and attributes to help the developing of new parsers. Parsers can be defined
by class derivation and following a tokens registration procedure.

Token base class
================

.. autoclass:: elementpath.Token

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

.. autoclass:: elementpath.Parser

    Parsing methods:

    .. automethod:: build_tokenizer
    .. automethod:: parse
    .. automethod:: advance
    .. automethod:: raw_advance
    .. automethod:: expression

    Helper methods for building effective parser classes:

    .. automethod:: register
    .. automethod:: unregister
    .. automethod:: literal
    .. automethod:: nullary
    .. automethod:: prefix
    .. automethod:: postfix
    .. automethod:: infix
    .. automethod:: infixr
    .. automethod:: method
