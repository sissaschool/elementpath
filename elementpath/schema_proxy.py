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
from .exceptions import ElementPathTypeError
from .xpath_nodes import is_etree_element
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
    def validate(self, obj, *args, **kwargs):
        """
        Validates an XML object node using the XSD type. The argument *obj* is an element
        for complex type nodes or a text value for simple type nodes. Raises a `ValueError`
        compatible exception (a `ValueError` or a subclass of it) if the argument is not valid.
        """

    @abstractmethod
    def decode(self, obj, *args, **kwargs):
        """
        Decodes an XML object node using the XSD type. The argument *obj* is an element
        for complex type nodes or a text value for simple type nodes. Raises a `ValueError`
        or a `TypeError` compatible exception if the argument it's not valid.
        """


####
# Schema proxy classes
#

@add_metaclass(ABCMeta)
class AbstractSchemaProxy(object):
    """
    Abstract class for defining schema proxies.

    :param schema: a schema instance that implements the `AbstractEtreeElement` interface.
    :param base_element: the schema element used as base item for static analysis. It must \
    implements the `AbstractXsdElement` interface.
    """
    def __init__(self, schema, base_element=None):
        if not is_etree_element(schema):
            raise ElementPathTypeError("argument {!r} is not a compatible schema instance".format(schema))
        if base_element is not None and not is_etree_element(base_element):
            raise ElementPathTypeError("argument 'base_element' is not a compatible element instance")

        self._schema = schema
        self._base_element = base_element

    def bind_parser(self, parser):
        """
        Binds a parser instance with schema proxy adding the schema's atomic types constructors.
        This method can be redefined in a concrete proxy to optimize schema bindings.

        :param parser: a parser instance.
        """
        if parser.schema is not self:
            parser.schema = self

        parser.symbol_table = parser.__class__.symbol_table.copy()
        for xsd_type in self.iter_atomic_types():
            parser.schema_constructor(xsd_type.name)
        parser.tokenizer = parser.create_tokenizer(parser.symbol_table)

    def get_context(self):
        """
        Get a context instance for static analysis phase.

        :returns: an `XPathSchemaContext` instance.
        """
        return XPathSchemaContext(root=self._schema, item=self._base_element)

    def find(self, path, namespaces=None):
        """
        Find a schema element or attribute using an XPath expression.

        :param path: an XPath expression that selects an element or an attribute node.
        :param namespaces: an optional mapping from namespace prefix to namespace URI.
        :return: The first matching schema component, or ``None`` if there is no match.
        """

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


__all__ = ['AbstractXsdComponent', 'AbstractEtreeElement', 'AbstractXsdType',
           'AbstractXsdAttribute', 'AbstractXsdElement', 'AbstractSchemaProxy']
