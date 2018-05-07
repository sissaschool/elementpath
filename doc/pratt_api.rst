Pratt's parser API
==================

The TDOP (Top Down Operator Precedence) parser implemented within this library is variant of the original
Pratt's parser based on a class for the parser and metaclasses for tokens.

The parser base class includes helper functions for registering token classes,
the Pratt's methods and a regexp-based tokenizer builder. There are also additional
methods and attributes to help the developing of new parsers. Parsers can be defined
by class derivation and following a tokens registration procedure.

Token Base Class
----------------

.. autoclass:: elementpath.Token


Parser Base Class
-----------------

.. autoclass:: elementpath.Parser

    .. automethod:: build_tokenizer
    .. automethod:: parse
    .. automethod:: advance
    .. automethod:: expression







