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
from abc import ABCMeta, abstractmethod
from .compat import add_metaclass


@add_metaclass(ABCMeta)
class AbstractSchemaProxy(object):

    def __init__(self, schema):
        self._schema = schema

    @abstractmethod
    def get_type(self, type_qname):
        """
        Get the XSD global type from the schema's scope.

        :param type_qname: The QName of the type to retrieve.
        :returns: The XSD Element or `None` if it isn't found.
        """

    @abstractmethod
    def get_attribute(self, attribute_qname):
        """
        Get the XSD global attribute from the schema's scope.

        :param attribute_qname: The QName of the attribute to retrieve.
        :returns: The XSD Element or `None` if it isn't found.
        """

    @abstractmethod
    def get_element(self, element_qname):
        """
        Get the XSD global element from the schema's scope.

        :param element_qname: The QName of the element to retrieve.
        :returns: The XSD Element or `None` if it isn't found.
        """

    @abstractmethod
    def is_instance(self, obj, type_qname):
        """
        Returns `True` if *obj* is an instance of the XSD global type, `False` if not.

        :param obj: The instance to be tested.
        :param type_qname: The QName of the type to test the instance.
        """

    @abstractmethod
    def cast_as(self, obj, type_qname):
        """
        Cast *obj* to the base type defined by XSD global type. Raise a ValueError or TypeError if the .

        :param obj: The instance to be casted.
        :param type_qname: The QName of the type to cast the instance.
        """

    @abstractmethod
    def iter_atomic_types(self):
        """Iterate over the XSD atomic types defined in the schema's scope."""


class XMLSchemaProxy(AbstractSchemaProxy):
    """
    XML Schema proxy for schemas created with the 'xmlschema' library.

    Library ref:https://github.com/brunato/xmlschema
    """
    def get_type(self, type_qname):
        try:
            return self._schema.maps.types[type_qname]
        except KeyError:
            return None

    def get_attribute(self, attribute_qname):
        try:
            return self._schema.maps.attributes[attribute_qname]
        except KeyError:
            return None

    def get_element(self, element_qname):
        try:
            return self._schema.maps.elements[element_qname]
        except KeyError:
            return None

    def get_substitution_group(self, element_qname):
        try:
            return self._schema.maps.substitution_groups[element_qname]
        except KeyError:
            return None

    def is_instance(self, obj, type_qname):
        xsd_type = self._schema.maps.types[type_qname]
        return xsd_type.is_valid(obj)

    def cast_as(self, obj, type_qname):
        xsd_type = self._schema.maps.types[type_qname]
        return xsd_type.decode(obj)

    def iter_atomic_types(self):
        for xsd_type in self._schema.maps.types.values():
            if xsd_type.is_simple() and not hasattr(xsd_type, 'item_type') and \
                    not hasattr(xsd_type, 'member_type'):
                yield xsd_type
