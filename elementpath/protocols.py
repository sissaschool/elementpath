#
# Copyright (c), 2021, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""
Define type hints protocols for XPath related objects.
"""
from typing import overload, Any, Dict, Iterator, Iterable, Optional, \
    Protocol, Sized, Hashable, Union, TypeVar, Mapping, Tuple, Set

ET_co = TypeVar("ET_co", covariant=True)
_T = TypeVar("_T")


class GenericElement(Iterable[ET_co], Sized, Hashable, Protocol[ET_co]):
    def find(
            self, path: str, namespaces: Optional[Dict[str, str]] = ...
    ) -> Optional[ET_co]: ...
    def iter(self, tag: Optional[str] = ...) -> Iterator[ET_co]: ...

    @overload
    def get(self, key: str) -> Optional[str]: ...

    @overload
    def get(self, key: str, default: _T) -> Union[str, _T]: ...

    @property
    def tag(self) -> str: ...

    @property
    def text(self) -> Optional[str]: ...

    @property
    def tail(self) -> Optional[str]: ...


class ElementProtocol(GenericElement['ElementProtocol'], Protocol):
    """A protocol for ElementTree elements."""
    @property
    def attrib(self) -> Dict[str, str]: ...


class LxmlElementProtocol(GenericElement['LxmlElementProtocol'], Protocol):
    """A protocol for lxml.etree elements."""
    def getroottree(self) -> 'LxmlDocumentProtocol': ...
    def getnext(self) -> Optional['LxmlElementProtocol']: ...
    def getparent(self) -> Optional['LxmlElementProtocol']: ...
    def getprevious(self) -> Optional['LxmlElementProtocol']: ...
    def itersiblings(self, tag: Optional[str] = ..., *tags: str,
                     preceding: bool = False) -> Iterable['LxmlElementProtocol']: ...

    @property
    def nsmap(self) -> Dict[Optional[str], str]: ...

    @property
    def attrib(self) -> Any: ...


class DocumentProtocol(Hashable, Protocol):
    def getroot(self) -> Optional[ElementProtocol]: ...
    def parse(self, source: Any, *args: Any, **kwargs: Any) -> ElementProtocol: ...
    def iter(self, tag: Optional[str] = ...) -> Iterator[ElementProtocol]: ...


class LxmlDocumentProtocol(Hashable, Protocol):
    def getroot(self) -> Optional[LxmlElementProtocol]: ...
    def parse(self, source: Any, *args: Any, **kwargs: Any) -> LxmlElementProtocol: ...
    def iter(self, tag: Optional[str] = ...) -> Iterator[LxmlElementProtocol]: ...


class XsdValidatorProtocol(Protocol):
    def is_matching(self, name: Optional[str],
                    default_namespace: Optional[str] = None) -> bool: ...

    @property
    def name(self) -> Optional[str]: ...

    @property
    def xsd_version(self) -> str: ...

    @property
    def maps(self) -> 'GlobalMapsProtocol': ...


class XsdComponentProtocol(XsdValidatorProtocol, Protocol):

    @property
    def ref(self) -> Optional[Any]: ...

    @property
    def parent(self) -> Optional['XsdComponentProtocol']: ...


class XsdTypeProtocol(XsdComponentProtocol, Protocol):

    def is_simple(self) -> bool:
        """Returns `True` if it's a simpleType instance, `False` if it's a complexType."""
        ...

    def is_empty(self) -> bool:
        """
        Returns `True` if it's a simpleType instance or a complexType with empty content,
        `False` otherwise.
        """
        ...

    def has_simple_content(self) -> bool:
        """
        Returns `True` if it's a simpleType instance or a complexType with simple content,
        `False` otherwise.
        """
        ...

    def has_mixed_content(self) -> bool:
        """
        Returns `True` if it's a complexType with mixed content, `False` otherwise.
        """
        ...

    def is_element_only(self) -> bool:
        """
        Returns `True` if it's a complexType with element-only content, `False` otherwise.
        """
        ...

    def is_key(self) -> bool:
        """Returns `True` if it's a simpleType derived from xs:ID, `False` otherwise."""
        ...

    def is_qname(self) -> bool:
        """Returns `True` if it's a simpleType derived from xs:QName, `False` otherwise."""
        ...

    def is_notation(self) -> bool:
        """Returns `True` if it's a simpleType derived from xs:NOTATION, `False` otherwise."""
        ...

    def is_valid(self, obj: Any, *args: Any, **kwargs: Any) -> bool:
        """
        Validates an XML object node using the XSD type. The argument *obj* is an element
        for complex type nodes or a text value for simple type nodes. Returns `True` if
        the argument is valid, `False` otherwise.
        """
        ...

    def validate(self, obj: Any, *args: Any, **kwargs: Any) -> None:
        """
        Validates an XML object node using the XSD type. The argument *obj* is an element
        for complex type nodes or a text value for simple type nodes. Raises a `ValueError`
        compatible exception (a `ValueError` or a subclass of it) if the argument is not valid.
        """
        ...

    def decode(self, obj: Any, *args: Any, **kwargs: Any) -> Any:
        """
        Decodes an XML object node using the XSD type. The argument *obj* is an element
        for complex type nodes or a text value for simple type nodes. Raises a `ValueError`
        or a `TypeError` compatible exception if the argument it's not valid.
        """
        ...

    @property
    def root_type(self) -> 'XsdTypeProtocol':
        """
        The type at base of the definition of the XSD type. For a special type is the type
        itself. For an atomic type is the primitive type. For a list is the primitive type
        of the item. For a union is the base union type. For a complex type is xs:anyType.
        """
        ...


class XsdAttributeProtocol(XsdComponentProtocol, Protocol):

    @property
    def type(self) -> Optional[XsdTypeProtocol]: ...


XsdElementType = Union['XsdElementProtocol', 'XsdAnyElementProtocol']


class XsdAnyElementProtocol(XsdComponentProtocol, GenericElement[XsdElementType], Protocol):

    @property
    def type(self) -> None: ...


class XsdElementProtocol(XsdComponentProtocol, GenericElement[XsdElementType], Protocol):

    @property
    def name(self) -> str: ...

    @property
    def type(self) -> XsdTypeProtocol: ...

    @property
    def attrib(self) -> Dict[str, XsdAttributeProtocol]: ...


GT = TypeVar("GT")
XsdGlobalValue = Union[GT, Tuple[ElementProtocol, Any]]


class GlobalMapsProtocol(Protocol):
    @property
    def types(self) -> Mapping[str, XsdGlobalValue[XsdTypeProtocol]]: ...

    @property
    def attributes(self) -> Mapping[str, XsdGlobalValue[XsdAttributeProtocol]]: ...

    @property
    def elements(self) -> Mapping[str, XsdGlobalValue[XsdElementProtocol]]: ...

    @property
    def substitution_groups(self) -> Mapping[str, Set[Any]]: ...


XsdSchemaType = Union['XsdSchemaProtocol', 'XsdElementProtocol']


class XsdSchemaProtocol(XsdValidatorProtocol, GenericElement[XsdSchemaType], Protocol):

    @property
    def tag(self) -> str: ...

    @property
    def attrib(self) -> Dict[str, 'XsdAttributeProtocol']: ...


__allx__ = ['ElementProtocol', 'LxmlElementProtocol',
            'DocumentProtocol', 'LxmlDocumentProtocol',
            'XsdValidatorProtocol', 'XsdSchemaProtocol',
            'XsdComponentProtocol', 'XsdTypeProtocol',
            'XsdElementProtocol', 'XsdAttributeProtocol',
            'XsdAnyElementProtocol', 'GlobalMapsProtocol']
