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
from .namespaces import prefixed_to_qname

class AbstractSchemaProxy(ABC):

    def __init__(self, schema):
        self._schema = schema

    @abstractmethod
    def cast_as(self, unary_expr, type_qname, required=True):
        pass

    @abstractmethod
    def is_instance(self, treat_expr, type_qname, occurs=None):
        pass

    @abstractmethod
    def get_attribute(self, qname):
        pass

    @abstractmethod
    def get_element(self, qname):
        """
        Get the XSD element from the schema's scope.

        :param qname: The QName of the element to retrieve.
        :returns: The XSD Element or `None` if it isn't found.
        """

    @abstractmethod
    def get_type(self, qname):
        pass


class XMLSchemaProxy(AbstractSchemaProxy):
    """
    XML Schema proxy for schemas created with the 'xmlschema' library.

    Library ref:https://github.com/brunato/xmlschema
    """
    def cast_as(self, unary_expr, type_qname, required=True):
        pass

    def is_instance(self, treat_expr, type_qname, occurs=None):
        pass

    def get_type(self, qname):
        try:
            return self._schema.maps.types[qname]
        except KeyError:
            return None

    def get_attribute(self, qname):
        try:
            return self._schema.maps.attributes[qname]
        except KeyError:
            return None

    def get_element(self, qname):
        try:
            return self._schema.maps.elements[qname]
        except KeyError:
            return None

    def get_substitution_group(self, qname):
        try:
            return self._schema.maps.substitution_groups[qname]
        except KeyError:
            return None
