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
"""Python 2/3 compatibility imports and definitions."""
import sys

PY3 = sys.version_info >= (3,)

if PY3:
    from urllib.parse import uses_relative, urlparse, urljoin, quote as urllib_quote
    from urllib.error import URLError
    string_base_type = str
    unicode_type = str
    unicode_chr = chr
    from collections.abc import MutableSequence
    from functools import lru_cache
else:
    # noinspection PyCompatibility
    from urllib2 import URLError, quote as urllib_quote
    from urlparse import urlparse, urljoin, uses_relative
    string_base_type = basestring
    unicode_type = unicode
    unicode_chr = unichr
    from collections import MutableSequence
    from functools import wraps

    def lru_cache(maxsize=128, typed=False):
        """
        A fake lru_cache decorator function for Python 2.7 compatibility until support ends.
        """
        def lru_cache_decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                return f(*args, **kwargs)
            return wrapper
        return lru_cache_decorator


def add_metaclass(metaclass):
    """
    Class decorator for creating a class with a metaclass.
    From `six` package source code: https://bitbucket.org/gutworth/six/overview.
    """
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper
