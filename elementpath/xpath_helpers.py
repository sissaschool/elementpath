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
from .exceptions import xpath_error
from .xpath_nodes import is_element_node


def boolean_value(obj, token=None):
    """
    The effective boolean value, as computed by fn:boolean().
    Moved to token class but kept for backward compatibility.
    """
    if isinstance(obj, list):
        if not obj:
            return False
        elif isinstance(obj[0], tuple) or is_element_node(obj[0]):
            return True
        elif len(obj) == 1:
            return bool(obj[0])
        else:
            raise xpath_error(
                code='FORG0006', token=token, prefix=getattr(token, 'error_prefix', 'err'),
                message="Effective boolean value is not defined for a sequence of two or "
                "more items not starting with an XPath node.",
            )
    elif isinstance(obj, tuple) or is_element_node(obj):
        raise xpath_error(
            code='FORG0006', token=token, prefix=getattr(token, 'error_prefix', 'err'),
            message="Effective boolean value is not defined for {}.".format(obj)
        )
    return bool(obj)
