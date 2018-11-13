# -*- coding: utf-8 -*-
#
# Copyright (c), 2018, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from __future__ import unicode_literals
from .compat import PY3


class ElementPathError(Exception):
    """
    Base exception class for elementpath package.

    :param message: the message related to the error.
    :param token: an optional token instance related with the error.
    :param code: an optional error code.
    """

    def __init__(self, message, token=None, code=None):
        super(ElementPathError, self).__init__(message)
        self.message = message
        self.token = token
        self.code = code

    def __str__(self):
        return unicode(self).encode("utf-8")

    def __unicode__(self):
        if self.code is None:
            return self.message if self.token is None else '%s: %s.' % (self.token, self.message)
        elif self.token is None:
            return '%s [%s].' % (self.message, self.code)
        else:
            return '%s: %s [%s].' % (self.token, self.message, self.code)

    if PY3:
        __str__ = __unicode__


class ElementPathNameError(ElementPathError, NameError):
    pass


class ElementPathKeyError(ElementPathError, KeyError):
    pass


class ElementPathSyntaxError(ElementPathError, SyntaxError):
    pass


class ElementPathTypeError(ElementPathError, TypeError):
    pass


class ElementPathValueError(ElementPathError, ValueError):
    pass


class ElementPathMissingContextError(ElementPathError):
    pass
