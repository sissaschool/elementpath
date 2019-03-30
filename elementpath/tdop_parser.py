# -*- coding: utf-8 -*-
#
# Copyright (c), 2018-2019, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""
This module contains classes and helper functions for defining Pratt parsers.
"""
import sys
import re
from unicodedata import name as unicode_name
from decimal import Decimal
from abc import ABCMeta

from .compat import PY3, add_metaclass, MutableSequence
from .exceptions import ElementPathSyntaxError, ElementPathNameError, ElementPathValueError, ElementPathTypeError

###
# Regex based tokenizer
SPECIAL_SYMBOL_PATTERN = re.compile(r'\(\w+\)')
"""Compiled regular expression for matching special symbols, that are names between round brackets."""

SPACE_PATTERN = re.compile(r'\s')


def symbol_to_identifier(symbol):
    """
    Converts a symbol string to an identifier (only alphanumeric and '_').
    """
    def get_id_name(c):
        if c in ('_', '-', ' '):
            return '_'
        elif c.isalnum():
            return c
        elif PY3:
            return unicode_name(c).title().replace(' ', '')
        else:
            return unicode_name(unicode(c)).title().replace(' ', '')

    if symbol.isalnum():
        return symbol
    elif SPECIAL_SYMBOL_PATTERN.match(symbol):
        return symbol[1:-1]
    else:
        return ''.join(get_id_name(c) for c in symbol)


def create_tokenizer(symbol_table, name_pattern='[A-Za-z0-9_]+'):
    """
    Returns a regex based tokenizer built from a symbol table of token classes.
    The returned tokenizer skips extra spaces between symbols.

    A regular expression is created from the symbol table of the parser using a template.
    The symbols are inserted in the template putting the longer symbols first. Symbols and
    their patterns can't contain spaces.

    :param symbol_table: a dictionary containing the token classes of the formal language.
    :param name_pattern: pattern to use to match names.
    """
    tokenizer_pattern_template = r"""
        ('[^']*' | "[^"]*" | (?:\d+|\.\d+)(?:\.\d*)?(?:[Ee][+-]?\d+)?) |  # Literals (string and numbers)
        (%s|[%s]) |                                                       # Symbol's patterns
        (%s) |                                                            # Names
        (\S) |                                                            # Unexpected characters
        \s+                                                               # Skip extra spaces
    """
    patterns = [
        t.pattern for s, t in symbol_table.items()
        if SPECIAL_SYMBOL_PATTERN.match(s) is None
    ]
    string_patterns = []
    character_patterns = []

    for p in patterns:
        if ' ' in p:
            raise ElementPathValueError('pattern %r contains spaces' % p)
        length = len(p)
        if length == 1 or length == 2 and p[0] == '\\':
            character_patterns.append(p)
        else:
            string_patterns.append(p)

    pattern = tokenizer_pattern_template % (
        '|'.join(sorted(string_patterns, key=lambda x: -len(x))),
        ''.join(character_patterns),
        name_pattern
    )
    return re.compile(pattern, re.VERBOSE)


#
# Simple top down parser based on Vaughan Pratt's algorithm (Top Down Operator Precedence).
#
# References:
#
#   https://tdop.github.io/  (Vaughan R. Pratt's "Top Down Operator Precedence" - 1973)
#   http://crockford.com/javascript/tdop/tdop.html  (Douglas Crockford - 2007)
#   http://effbot.org/zone/simple-top-down-parsing.htm (Fredrik Lundh - 2008)
#
# This implementation is based on a base class for tokens and a base class for parsers.
# A real parser is built with a derivation of the base parser class followed by the
# registrations of token classes for the symbols of the language.
#
# A parser can be extended by derivation, copying the reusable token classes and
# defining the additional ones. See the files xpath1_parser.py and xpath2_parser.py
# for a fully implementation example of a real parser.
#

class MultiLabel(object):
    """
    Helper class for defining multi-value label for tokens. Useful when a symbol has more roles.
    A label of this type has equivalence with each of its values.

    Example:
        label = MultiLabel('function', 'operator')
        label == 'symbol'    # False
        label == 'function'  # True
        label == 'operator'  # True
    """
    def __init__(self, *values):
        self.values = values

    def __eq__(self, other):
        return any(other == v for v in self.values)

    def __ne__(self, other):
        return all(other != v for v in self.values)

    def __str__(self):
        return '_'.join(self.values)

    def __unicode__(self):
        return u'_'.join(self.values)

    if PY3:
        __str__ = __unicode__


class Token(MutableSequence):
    """
    Token base class for defining a parser based on Pratt's method.

    Each token instance is a list-like object. The number of token's items is the arity of
    the represented operator, where token's items are the operands. Nullary operators are
    used for symbols, names and literals. Tokens with items represent the other operators
    (unary, binary and so on).

    Each token class has a *symbol*, a lbp (left binding power) value and a rbp (right binding
    power) value, that are used in the sense described by the Pratt's method. This implementation
    of Pratt tokens includes two extra attributes, *pattern* and *label*, that can be used to
    simplify the parsing of symbols in a concrete parser.

    :param parser: The parser instance that creates the token instance.
    :param value: The token value. If not provided defaults to token symbol.

    :cvar symbol: the symbol of the token class.
    :cvar lbp: Pratt's left binding power, defaults to 0.
    :cvar rbp: Pratt's right binding power, defaults to 0.
    :cvar pattern: the regex pattern used for the token class. Defaults to the escaped symbol. \
    Can be customized to match more detailed conditions (eg. a function with its left round bracket), \
    in order to simplify the related code.
    :cvar label: defines the typology of the token class. Its value is used in representations of the \
    token instance and can be used to restrict code choices without more complicated analysis. The label \
    value can be set as needed by the parser implementation (eg. 'function', 'axis', 'constructor' are \
    used by the XPath parsers). In the base parser class defaults to 'symbol' with 'literal' and 'operator' \
    as possible alternatives. If set by a tuple of values the token class label is transformed to a \
    multi-value label, that means the token class can covers multiple roles (eg. as XPath function or axis). \
    In those cases the definitive role is defined at parse time (nud and/or led methods) after the token \
    instance creation.
    """
    symbol = None     # the token identifier, key in the token table.
    lbp = 0           # left binding power
    rbp = 0           # right binding power
    pattern = None    # the token regex pattern, for building the tokenizer.
    label = 'symbol'  # optional label

    def __init__(self, parser, value=None):
        self.parser = parser
        self.value = value if value is not None else self.symbol
        self._operands = []

    def __getitem__(self, i):
        return self._operands[i]

    def __setitem__(self, i, item):
        self._operands[i] = item

    def __delitem__(self, i):
        del self._operands[i]

    def __len__(self):
        return len(self._operands)

    def insert(self, i, item):
        self._operands.insert(i, item)

    def __str__(self):
        symbol = self.symbol
        if SPECIAL_SYMBOL_PATTERN.match(symbol) is not None:
            return '%r %s' % (self.value, symbol[1:-1])
        else:
            return '%r %s' % (symbol, self.label)

    def __repr__(self):
        symbol, value = self.symbol, self.value
        if value != symbol:
            return u'%s(value=%r)' % (self.__class__.__name__, value)
        else:
            return u'%s()' % self.__class__.__name__

    def __cmp__(self, other):
        return self.symbol == other.symbol and self.value == other.value

    @property
    def arity(self):
        return len(self)

    @property
    def tree(self):
        """Returns a tree representation string."""
        symbol, length = self.symbol, len(self)
        if symbol == '(name)':
            return u'(%s)' % self.value
        elif SPECIAL_SYMBOL_PATTERN.match(symbol) is not None:
            return u'(%r)' % self.value
        elif symbol == '(':
            return '()' if not self else self[0].tree
        elif not length:
            return u'(%s)' % symbol
        else:
            return u'(%s %s)' % (symbol, ' '.join(item.tree for item in self))

    @property
    def source(self):
        """Returns the source representation string."""
        symbol = self.symbol
        if symbol == '(name)':
            return self.value
        elif SPECIAL_SYMBOL_PATTERN.match(symbol) is not None:
            return repr(self.value)
        else:
            length = len(self)
            if not length:
                return symbol
            elif length == 1:
                return u'%s %s' % (symbol, self[0].source)
            elif length == 2:
                return u'%s %s %s' % (self[0].source, symbol, self[1].source)
            else:
                return u'%s %s' % (symbol, ' '.join(item.source for item in self))

    def nud(self):
        """Pratt's null denotation method"""
        self.wrong_syntax()

    def led(self, left):
        """Pratt's left denotation method"""
        self.wrong_syntax()

    def evaluate(self, *args, **kwargs):
        """Evaluation method"""

    def iter(self):
        """Returns a generator for iterating the token's tree."""
        for t in self[:1]:
            for token in t.iter():
                yield token
        yield self
        for t in self[1:]:
            for token in t.iter():
                yield token

    def expected(self, *symbols):
        if symbols and self.symbol not in symbols:
            self.wrong_syntax()

    def unexpected(self, *symbols):
        if not symbols or self.symbol in symbols:
            self.wrong_syntax()

    def wrong_syntax(self, message=None):
        symbol = self.value if SPECIAL_SYMBOL_PATTERN.match(self.symbol) is not None else self.symbol
        line_column = 'line %d, column %d' % self.parser.position
        token = self.parser.token
        if token is not None and symbol != token.symbol:
            msg = "symbol %r after %s at %s" % (symbol, token, line_column)
        else:
            msg = "symbol %r at %s" % (symbol, line_column)

        if message:
            raise ElementPathSyntaxError('%s: %s' % (msg, message), self)
        else:
            raise ElementPathSyntaxError('unexpected %s.' % msg, self)

    def wrong_value(self, message='unknown error'):
        raise ElementPathValueError(message, self)

    def wrong_type(self, message='unknown error'):
        raise ElementPathTypeError(message, self)


class ParserMeta(type):

    def __new__(mcs, name, bases, namespace):
        cls = super(ParserMeta, mcs).__new__(mcs, name, bases, namespace)

        # Avoids more parsers definitions for a single module
        for k, v in sys.modules[cls.__module__].__dict__.items():
            if isinstance(v, ParserMeta) and v.__module__ == cls.__module__:
                raise RuntimeError("Multiple parser class definitions per module are not permitted: %r" % cls)

        # Checks and initializes class attributes
        if not hasattr(cls, 'token_base_class'):
            cls.token_base_class = Token
        if 'tokenizer' not in namespace:
            cls.tokenizer = None
        if 'SYMBOLS' not in namespace:
            cls.SYMBOLS = set()
            for base_class in bases:
                if hasattr(base_class, 'SYMBOLS'):
                    cls.SYMBOLS.update(base_class.SYMBOLS)
                    break
        if 'symbol_table' not in namespace:
            cls.symbol_table = {}
            for base_class in bases:
                if hasattr(base_class, 'symbol_table'):
                    cls.symbol_table.update(base_class.symbol_table)
                    break
        return cls

    def __init__(cls, name, bases, namespace):
        super(ParserMeta, cls).__init__(name, bases, namespace)


@add_metaclass(ParserMeta)
class Parser(object):
    """
    Parser class for implementing a Top Down Operator Precedence parser.

    :cvar SYMBOLS: the symbols of the definable tokens for the parser. In the base class it's an \
    immutable set that contains the symbols for special tokens (literals, names and end-token).\
    Has to be extended in a concrete parser adding all the symbols of the language.
    :cvar symbol_table: a dictionary that stores the token classes defined for the language.
    :type symbol_table: dict
    :cvar token_base_class: the base class for creating language's token classes.
    :type token_base_class: Token
    :cvar tokenizer: the language tokenizer compiled regexp.
    """
    SYMBOLS = frozenset(('(string)', '(float)', '(decimal)', '(integer)', '(name)', '(end)'))
    token_base_class = Token
    tokenizer = None
    symbol_table = {}

    @classmethod
    def build_tokenizer(cls, name_pattern='[A-Za-z0-9_]+'):
        """
        Builds the parser class tokenizer using the symbol related patterns.

        :param name_pattern: Pattern to use to match names.
        """
        if not cls.SYMBOLS.issubset(cls.symbol_table.keys()):
            unregistered = [s for s in cls.SYMBOLS if s not in cls.symbol_table]
            raise ValueError("The parser %r has unregistered symbols: %r" % (cls, unregistered))
        cls.tokenizer = create_tokenizer(cls.symbol_table, name_pattern)

    def __init__(self):
        if self.tokenizer is None:
            raise ValueError("Incomplete parser class %s registration." % self.__class__.__name__)
        self.token = None
        self.match = None
        self.next_token = None
        self.next_match = None
        self.tokens = iter(())
        self.source = ''

    def __eq__(self, other):
        if self.token_base_class != other.token_base_class:
            return False
        elif self.SYMBOLS != other.SYMBOLS:
            return False
        elif self.symbol_table != other.symbol_table:
            return False
        else:
            return True

    def parse(self, source):
        """
        Parses a source code of the formal language. This is the main method that has to be
        called for a parser's instance.

        :param source: The source string.
        :return: The root of the token's tree that parse the source.
        """
        try:
            self.source = source
            self.tokens = iter(self.tokenizer.finditer(source))
            self.advance()
            root_token = self.expression()
            if self.next_token.symbol != '(end)':
                self.next_token.unexpected()
            return root_token
        finally:
            self.tokens = iter(())
            self.token = None
            self.match = None
            self.next_token = None
            self.next_match = None

    def advance(self, *symbols):
        """
        The Pratt's function for advancing to next token.

        :param symbols: Optional arguments tuple. If not empty one of the provided \
        symbols is expected. If the next token's symbol differs the parser raise a \
        parse error.
        :return: The next token instance.
        """
        if getattr(self.next_token, 'symbol', None) == '(end)':
            if self.token is None:
                raise ElementPathSyntaxError("source is empty.")
            else:
                raise ElementPathSyntaxError("unexpected end of source after %s." % self.token)
        elif self.next_token is not None:
            self.next_token.expected(*symbols)

        self.token = self.next_token
        self.match = self.next_match
        while True:
            try:
                self.next_match = next(self.tokens)
            except StopIteration:
                self.next_token = self.symbol_table['(end)'](self)
                break
            else:
                literal, symbol, name, unexpected = self.next_match.groups()
                if symbol is not None:
                    symbol = symbol.strip()
                    try:
                        self.next_token = self.symbol_table[symbol](self)
                    except KeyError:
                        raise ElementPathSyntaxError("unknown symbol %r." % symbol)
                    break
                elif literal is not None:
                    if literal[0] in '\'"':
                        self.next_token = self.symbol_table['(string)'](self, literal.strip("'\""))
                    elif 'e' in literal or 'E' in literal:
                        self.next_token = self.symbol_table['(float)'](self, float(literal))
                    elif '.' in literal:
                        self.next_token = self.symbol_table['(decimal)'](self, Decimal(literal))
                    else:
                        self.next_token = self.symbol_table['(integer)'](self, int(literal))
                    break
                elif name is not None:
                    self.next_token = self.symbol_table['(name)'](self, name)
                    break
                elif unexpected is not None:
                    raise ElementPathSyntaxError(
                        "unexpected symbol %r at %s." % (unexpected, 'line %d, column %d' % self.position)
                    )
                elif str(self.next_match.group()).strip():
                    raise RuntimeError(
                        "Unexpected matching %r: not compatible tokenizer." % self.next_match.group()
                    )
        return self.next_token

    def raw_advance(self, *stop_symbols):
        """
        Advances until one of the symbols is found or the end of source is reached, returning
        the raw source string placed before. Useful for raw parsing of comments and references
        enclosed between specific symbols. This is an extension provided by this implementation.

        :param stop_symbols: The symbols that have to be found for stopping advance.
        :return: The source string chunk enclosed between the initial position and the first stop symbol.
        """
        if not stop_symbols:
            raise ElementPathValueError("at least a stop symbol required!", self.next_token)
        elif getattr(self.next_token, 'symbol', None) == '(end)':
            if self.token is None:
                raise ElementPathSyntaxError("source is empty.", self.next_token)
            else:
                raise ElementPathSyntaxError("unexpected end of source after %s." % self.token, self.next_token)

        self.token = self.next_token
        self.match = self.next_match
        source_chunk = []
        while True:
            try:
                self.next_match = next(self.tokens)
            except StopIteration:
                self.next_token = self.symbol_table['(end)'](self)
                break
            else:
                symbol = self.next_match.group(2)
                if symbol is not None:
                    symbol = symbol.strip()
                    if symbol not in stop_symbols:
                        source_chunk.append(symbol)
                    else:
                        try:
                            self.next_token = self.symbol_table[symbol](self)
                        except KeyError:
                            raise ElementPathSyntaxError("unknown symbol %r." % symbol)
                        break
                else:
                    source_chunk.append(self.next_match.group())
        return ''.join(source_chunk)

    def expression(self, rbp=0):
        """
        Pratt's function for parsing an expression. It calls token.nud() and then advances
        until the right binding power is less the left binding power of the next
        token, invoking the led() method on the following token.

        :param rbp: right binding power for the expression.
        :return: left token.
        """
        token = self.next_token
        self.advance()
        left = token.nud()
        while rbp < self.next_token.lbp:
            token = self.next_token
            self.advance()
            left = token.led(left)
        return left

    @property
    def position(self):
        """Property that returns the current line and column indexes."""
        if self.match is None:
            return 1, 0
        token_index = self.match.span()[0]
        line = self.source[:token_index].count('\n') + 1
        if line == 1:
            return line, token_index + 1
        else:
            return line, token_index - self.source[:token_index].rindex('\n')

    def is_source_start(self):
        """
        Returns `True` if the parser is positioned at the start of the source, ignoring the spaces.
        """
        if self.match is None:
            return True
        return not bool(self.source[0:self.match.span()[0]].strip())

    def is_line_start(self):
        """
        Returns `True` if the parser is positioned at the start of a source line, ignoring the spaces.
        """
        if self.match is None:
            return True
        token_index = self.match.span()[0]
        line_start = self.source[0:token_index].rindex('\n') + 1
        return not bool(self.source[line_start:token_index].strip())

    def is_spaced(self, before=True, after=True):
        """
        Returns `True` if the source has an extra space (whitespace, tab or newline) immediately
        before or after the current position of the parser.

        :param before: if `True` considers also the extra spaces before the current token symbol.
        :param after: if `True` considers also the extra spaces after the current token symbol.
        """
        if self.match is None:
            return False
        start, end = self.match.span()
        if before and start > 0 and self.source[start - 1] in ' \t\n':
            return True
        try:
            return after and self.source[end] in ' \t\n'
        except IndexError:
            return False

    @classmethod
    def register(cls, symbol, **kwargs):
        """
        Register/update a token class in the symbol table.

        :param symbol: The identifier symbol for the or an existent token class.
        :param kwargs: Optional attributes/methods for the token class.
        :return: A token class.
        """
        def symbol_escape(s):
            s = re.escape(s)
            s.replace(r'\ ', r'\s+')

            if s.isalpha():
                s = r'\b%s\b' % s
            elif s[-2:] == r'\(':
                s = r'%s\s*%s' % (s[:-2], s[-2:])
            elif s[-4:] == r'\:\:':
                s = r'%s\s*%s' % (s[:-4], s[-4:])
            return s

        try:
            try:
                if ' ' in symbol:
                    raise ElementPathValueError("%r: a symbol can't contains whitespaces." % symbol)
            except TypeError:
                assert isinstance(symbol, type) and issubclass(symbol, Token), \
                    "A %r subclass requested, not %r." % (Token, symbol)
                symbol, token_class = symbol.symbol, symbol
                assert symbol in cls.symbol_table and cls.symbol_table[symbol] is token_class, \
                    "Token class %r is not registered." % token_class
            else:
                token_class = cls.symbol_table[symbol]

        except KeyError:
            # Register a new symbol and create a new custom class. The new class
            # name is registered at parser class's module level.
            if symbol not in cls.SYMBOLS:
                raise ElementPathNameError('%r is not a symbol of the parser %r.' % (symbol, cls))

            kwargs['symbol'] = symbol
            if 'pattern' not in kwargs:
                pattern = symbol_escape(symbol) if len(symbol) > 1 else re.escape(symbol)
                kwargs['pattern'] = pattern

            label = kwargs.get('label', 'symbol')
            if isinstance(label, tuple):
                label = kwargs['label'] = MultiLabel(*label)

            token_class_name = str("_%s_%s_token" % (symbol_to_identifier(symbol), label))
            kwargs.update({
                '__module__': cls.__module__,
                '__qualname__': token_class_name,
                '__return__': None
            })
            token_class = ABCMeta(token_class_name, (cls.token_base_class,), kwargs)
            cls.symbol_table[symbol] = token_class
            MutableSequence.register(token_class)
            setattr(sys.modules[cls.__module__], token_class_name, token_class)

        else:
            for key, value in kwargs.items():
                if key == 'lbp' and value > token_class.lbp:
                    token_class.lbp = value
                elif key == 'rbp' and value > token_class.rbp:
                    token_class.rbp = value
                elif callable(value):
                    setattr(token_class, key, value)

        return token_class

    @classmethod
    def unregister(cls, symbol):
        """Unregister a token class from the symbol table."""
        del cls.symbol_table[symbol.strip()]

    @classmethod
    def literal(cls, symbol, bp=0):
        """Register a token for a symbol that represents a *literal*."""
        def nud(self):
            return self

        def evaluate(self, *args, **kwargs):
            return self.value

        return cls.register(symbol, label='literal', lbp=bp, evaluate=evaluate, nud=nud)

    @classmethod
    def nullary(cls, symbol, bp=0):
        """Register a token for a symbol that represents a *nullary* operator."""
        def nud(self):
            return self
        return cls.register(symbol, label='operator', lbp=bp, nud=nud)

    @classmethod
    def prefix(cls, symbol, bp=0):
        """Register a token for a symbol that represents a *prefix* unary operator."""
        def nud(self):
            self[:] = self.parser.expression(rbp=bp),
            return self
        return cls.register(symbol, label='operator', lbp=bp, rbp=bp, nud=nud)

    @classmethod
    def postfix(cls, symbol, bp=0):
        """Register a token for a symbol that represents a *postfix* unary operator."""
        def led(self, left):
            self[:] = left,
            return self
        return cls.register(symbol, label='operator', lbp=bp, rbp=bp, led=led)

    @classmethod
    def infix(cls, symbol, bp=0):
        """Register a token for a symbol that represents an *infix* binary operator."""
        def led(self, left):
            self[:] = left, self.parser.expression(rbp=bp)
            return self
        return cls.register(symbol, label='operator', lbp=bp, rbp=bp, led=led)

    @classmethod
    def infixr(cls, symbol, bp=0):
        """Register a token for a symbol that represents an *infixr* binary operator."""
        def led(self, left):
            self[:] = left, self.parser.expression(rbp=bp-1)
            return self
        return cls.register(symbol, label='operator', lbp=bp, rbp=bp-1, led=led)

    @classmethod
    def method(cls, symbol, bp=0):
        """
        Register a token for a symbol that represents a custom operator or redefine
        a method for an existing token.
        """
        token_class = cls.register(symbol, label='operator', lbp=bp, rbp=bp)

        def bind(func):
            assert callable(getattr(token_class, func.__name__, None)), \
                "The name %r does not match with a callable of %r." % (func.__name__, token_class)
            setattr(token_class, func.__name__, func)
            return func
        return bind
