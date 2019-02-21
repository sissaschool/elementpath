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
from .xpath_helpers import is_etree_element
from .xpath_context import XPathSchemaContext


####
# Interfaces for XSD components
#
# Following interfaces can be used for defining XSD components into alternative
# schema proxies. Anyway no type-checking is done on XSD components returned by
# schema proxy instances, so one could decide to implement XSD components without
# the usage of these interfaces.
#

@add_metaclass(ABCMeta)
class AbstractXsdComponent(object):
    """Interface for XSD components."""

    @property
    @abstractmethod
    def name(self):
        """The XSD component's name. It's `None` for a local type definition."""

    @property
    @abstractmethod
    def local_name(self):
        """The local part of the XSD component's name. It's `None` for a local type definition."""

    @abstractmethod
    def is_matching(self, name, default_namespace):
        """
        Returns `True` if the component name is matching the name provided as argument, `False` otherwise.

        :param name: a local or fully-qualified name.
        :param default_namespace: used if it's not None and not empty for completing the name \
        argument in case it's a local name.
        """


@add_metaclass(ABCMeta)
class AbstractEtreeElement(object):
    """Interface for ElementTree compatible elements."""

    @property
    @abstractmethod
    def tag(self):
        """The element tag."""

    @property
    @abstractmethod
    def attrib(self):
        """The element's attributes dictionary."""

    @property
    @abstractmethod
    def text(self):
        """The element text."""

    @abstractmethod
    def __iter__(self):
        """Iterate over element's children."""


class AbstractXsdElement(AbstractXsdComponent, AbstractEtreeElement):
    """Interface for XSD attribute."""

    @property
    @abstractmethod
    def type(self):
        """The element's XSD type."""


class AbstractXsdAttribute(AbstractXsdComponent):
    """Interface for XSD attribute."""

    @property
    @abstractmethod
    def type(self):
        """The attribute's XSD type."""


class AbstractXsdType(AbstractXsdComponent):
    """Interface for XSD types."""

    @abstractmethod
    def is_simple(self):
        """Returns `True` if it's a simpleType instance, `False` if it's a complexType."""

    @abstractmethod
    def has_simple_content(self):
        """
        Returns `True` if it's a simpleType instance or a complexType with simple content,
        `False` otherwise.
        """

    @abstractmethod
    def decode(self, obj, *args, **kwargs):
        """
        Decodes XML data using the XSD type.
        """


####
# Schema proxy classes
#

@add_metaclass(ABCMeta)
class AbstractSchemaProxy(object):
    """
    Abstract class for defining schema proxies.

    :param schema: the schema instance.
    :param base_element: the schema element used as base item for static analysis.
    """
    def __init__(self, schema, base_element=None):
        if not is_etree_element(schema):
            raise ElementPathTypeError("argument {!r} is not a compatible schema".format(schema))
        if base_element is not None and not is_etree_element(base_element):
            raise ElementPathTypeError("argument 'base_element' is not a compatible element")

        self._schema = schema
        self._base_element = base_element

    def get_context(self):
        """
        Get a context instance for static analysis phase.

        :returns: an `XPathSchemaContext` instance.
        """
        return XPathSchemaContext(root=self._schema, item=self._base_element)

    @abstractmethod
    def get_type(self, qname):
        """
        Get the XSD global type from the schema's scope. A concrete implementation must
        returns an object that implements the `AbstractXsdType` interface, or `None` if
        the global type is not found.

        :param qname: the fully qualified name of the type to retrieve.
        :returns: an object that represents an XSD type or `None`.
        """

    @abstractmethod
    def get_attribute(self, qname):
        """
        Get the XSD global attribute from the schema's scope. A concrete implementation must
        returns an object that implements the `AbstractXsdAttribute` interface, or `None` if
        the global attribute is not found.

        :param qname: the fully qualified name of the attribute to retrieve.
        :returns: an object that represents an XSD attribute or `None`.
        """

    @abstractmethod
    def get_element(self, qname):
        """
        Get the XSD global element from the schema's scope. A concrete implementation must
        returns an object that implements the `AbstractXsdElement` interface or `None` if
        the global element is not found.

        :param qname: the fully qualified name of the element to retrieve.
        :returns: an object that represents an XSD element or `None`.
        """

    @abstractmethod
    def get_substitution_group(self, qname):
        """
        Get a substitution group. A concrete implementation must returns a list containing
        substitution elements or `None` if the substitution group is not found. Moreover each item
        of the returned list must be an object that implements the `AbstractXsdElement` interface.

        :param qname: the fully qualified name of the substitution group to retrieve.
        :returns: a list containing substitution elements or `None`.
        """

    @abstractmethod
    def is_instance(self, obj, type_qname):
        """
        Returns `True` if *obj* is an instance of the XSD global type, `False` if not.

        :param obj: the instance to be tested.
        :param type_qname: the fully qualified name of the type used to test the instance.
        """

    @abstractmethod
    def cast_as(self, obj, type_qname):
        """
        Converts *obj* to the Python type associated with an XSD global type. A concrete
        implementation must raises a `ValueError` or `TypeError` in case of a decoding
        error or a `KeyError` if the type is not bound to the schema's scope.

        :param obj: the instance to be casted.
        :param type_qname: the fully qualified name of the type used to convert the instance.
        """

    @abstractmethod
    def iter_atomic_types(self):
        """
        Returns an iterator for not builtin atomic types defined in the schema's scope. A concrete
        implementation must yields objects that implement the `AbstractXsdType` interface.
        """

    @abstractmethod
    def get_primitive_type(self, xsd_type):
        """
        Returns the primitive type of an XSD type.

        :param xsd_type: an XSD type instance.
        :return: an XSD builtin primitive type.
        """


class XMLSchemaProxy(AbstractSchemaProxy):
    """
    Schema proxy for the *xmlschema* library.
    """
    def __init__(self, schema=None, base_element=None):
        if schema is None:
            from xmlschema import XMLSchema
            schema = XMLSchema.meta_schema
        super(XMLSchemaProxy, self).__init__(schema, base_element)

        if base_element is not None:
            try:
                if base_element.schema is not schema:
                    raise ElementPathValueError("%r is not an element of %r" % (base_element, schema))
            except AttributeError:
                raise ElementPathTypeError("%r is not an XsdElement" % base_element)

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

    def get_primitive_type(self, xsd_type):
        if not xsd_type.is_simple():
            return self._schema.maps.types['{%s}anyType']
        elif not hasattr(xsd_type, 'primitive_type'):
            return self.get_primitive_type(xsd_type.base_type)
        elif xsd_type.primitive_type is not xsd_type:
            return self.get_primitive_type(xsd_type.primitive_type)
        else:
            return xsd_type


__all__ = ['AbstractXsdComponent', 'AbstractEtreeElement', 'AbstractXsdType', 'AbstractXsdAttribute',
           'AbstractXsdElement', 'AbstractSchemaProxy', 'XMLSchemaProxy']
