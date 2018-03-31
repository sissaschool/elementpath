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

class ElementPathError(Exception):
    pass


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
