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

from abc import ABC, abstractmethod


class AbstractSchemaProxy(ABC):

    @abstractmethod
    def cast_as(self, unary_expr, type_qname, required=True):
        pass

    @abstractmethod
    def is_instance(self, treat_expr, type_qname, occurs=None):
        pass


class XMLSchemaProxy(AbstractSchemaProxy):

    def cast_as(self, unary_expr, type_qname, required=True):
        pass

    def is_instance(self, treat_expr, type_qname, occurs=None):
        pass
