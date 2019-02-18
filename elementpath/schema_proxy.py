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
from abc import ABCMeta, abstractmethod
from .compat import add_metaclass
from .exceptions import ElementPathTypeError, ElementPathValueError
from .namespaces import XSD_NAMESPACE
from .xpath_helpers import AttributeNode, is_etree_element
from .xpath_context import XPathContext


@add_metaclass(ABCMeta)
class AbstractSchemaContext(XPathContext):
    """
    Abstract context class for implement a concrete schema context to be used during static
    analysis phase for type checking. A concrete implementation must implement a method for
    matching type of elements and attributes.
    """

    @abstractmethod
    def match_schema_type(self, name=None):
        """
        Match the XSD type of the context item. Returns an *XSD type instance* and a *sample value*
        if the context item is a matching attribute or element, or `None` otherwise. The returned
        XSD type objects must implement a *decode* method for decoding XML strings into values.
        For simple or simple content XSD types the sample value is an instance in the value-space
        of the primitive type. For complex content types the sample value is an empty string.

        :param name: An optional name to filter named nodes (eg. attributes or elements).
        :returns: A couple with XSD type instance and a value, or `None`.
        """


@add_metaclass(ABCMeta)
class AbstractSchemaProxy(object):
    """
    Abstract class for defining schema proxies. The schema elements must implement
    a compatible ElementTree API with the `XPathContext` and a *decode* method to
    apply to XML values.

    :param schema: the schema instance.
    :param base_element: the schema element used as base item for static analysis.
    """
    def __init__(self, schema, base_element=None):
        self._schema = schema
        self._base_element = base_element

    @abstractmethod
    def get_context(self):
        """
        Get a static context instance for static analysis phase. The provided context must
        be an instance of `XPathSchemaContext` or of an its subclass.

        :returns: An `XPathSchemaContext` instance or `None`.
        """

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
        """Iterate over not builtin atomic types defined in the schema's scope."""


class XMLSchemaContext(AbstractSchemaContext):
    """
    Schema context for the *xmlschema* library.
    """
    def match_schema_type(self, name=None):
        if isinstance(self.item, AttributeNode):
            if name is not None and not self.item[1].is_matching(name):
                return
            xsd_type = self.item[1].type
            return xsd_type, xsd_type.primitive_type.value

        elif is_etree_element(self.item):
            if name is not None:
                try:
                    if not self.item.is_matching(name):
                        return
                except AttributeError:
                    if self.item.tag != name:
                        return
            xsd_type = self.item.type
            if xsd_type.has_simple_content():
                return xsd_type, xsd_type.content_type.primitive_type.value
            else:
                return xsd_type, ''


class XMLSchemaProxy(AbstractSchemaProxy):
    """
    Schema proxy for the *xmlschema* library.
    """
    def __init__(self, schema=None, base_element=None):
        if schema is None:
            from xmlschema import XMLSchema
            schema = XMLSchema.meta_schema

        if base_element is not None:
            try:
                if base_element.schema is not schema:
                    raise ElementPathValueError("%r is not an element of %r" % (base_element, schema))
            except AttributeError:
                raise ElementPathTypeError("%r is not an XsdElement" % base_element)

        super(XMLSchemaProxy, self).__init__(schema, base_element)

    def get_context(self):
        return XMLSchemaContext(root=self._schema, item=self._base_element)

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
        try:
            xsd_type.encode(obj)
        except ValueError:
            return False
        else:
            return True

    def cast_as(self, obj, type_qname):
        xsd_type = self._schema.maps.types[type_qname]
        return xsd_type.decode(obj)

    def iter_atomic_types(self):
        for xsd_type in self._schema.maps.types.values():
            if xsd_type.target_namespace != XSD_NAMESPACE and hasattr(xsd_type, 'primitive_type'):
                yield xsd_type
