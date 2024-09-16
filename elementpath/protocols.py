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
from typing import overload, Any, Dict, Iterator, Iterable, Optional, Sequence, ItemsView, \
    Protocol, Sized, Hashable, Union, TypeVar, Mapping, Tuple, Set

from elementpath._typing import MutableMapping
from elementpath.aliases import NamespacesType, NsmapType

_T = TypeVar("_T")
_AnyStr = Union[str, bytes]


class LxmlQNameProtocol(Protocol):
    localname: _AnyStr
    namespace: _AnyStr
    text: _AnyStr


LxmlKeyType = Union[str, bytes, LxmlQNameProtocol]


class LxmlAttribProtocol(Protocol):
    """A minimal protocol for attributes of lxml Element objects."""
    def get(self, *args: Any, **kwargs: Any) -> Optional[str]: ...

    def items(self) -> Sequence[Tuple[Any, Any]]: ...

    def __contains__(self, key: Any) -> bool: ...

    def __getitem__(self, key: Any) -> Any: ...

    def __iter__(self) -> Iterator[Any]: ...

    def __len__(self) -> int: ...


AttribType = Union[
    MutableMapping[str, Any],
    MutableMapping[Optional[str], Any],
    LxmlAttribProtocol,
    'XsdAttributeGroupProtocol'
]


class ElementProtocol(Sized, Hashable, Protocol):
    """A protocol for generic ElementTree elements."""

    def __iter__(self) -> Iterator['ElementProtocol']: ...

    def find(
            self, path: str, namespaces: Optional[Dict[str, str]] = ...
    ) -> Optional['ElementProtocol']: ...
    def iter(self, tag: Optional[str] = ...) -> Iterator['ElementProtocol']: ...

    @overload
    def get(self, key: str) -> Optional[str]: ...

    @overload
    def get(self, key: str, default: _T) -> Union[str, _T]: ...

    def get(self, key: str, default: Optional[_T] = None) -> Union[str, _T, None]: ...

    @property
    def tag(self) -> str: ...

    @property
    def text(self) -> Optional[str]: ...

    @property
    def tail(self) -> Optional[str]: ...

    @property
    def attrib(self) -> AttribType: ...


class EtreeElementProtocol(ElementProtocol, Protocol):
    """A protocol for xml.etree.ElementTree elements."""
    def __iter__(self) -> Iterator['EtreeElementProtocol']: ...

    def find(
            self, path: str, namespaces: Optional[Dict[str, str]] = ...
    ) -> Optional['EtreeElementProtocol']: ...
    def iter(self, tag: Optional[str] = ...) -> Iterator['EtreeElementProtocol']: ...

    @property
    def attrib(self) -> Dict[str, str]: ...


class LxmlElementProtocol(ElementProtocol, Protocol):
    """A protocol for lxml.etree elements."""
    def __iter__(self) -> Iterator['LxmlElementProtocol']: ...

    def find(
            self, path: str, namespaces: Optional[MutableMapping[str, str]] = ...
    ) -> Optional['LxmlElementProtocol']: ...
    def iter(self, tag: Optional[str] = ...) -> Iterator['LxmlElementProtocol']: ...

    def getroottree(self) -> 'LxmlDocumentProtocol': ...
    def getnext(self) -> Optional['LxmlElementProtocol']: ...
    def getparent(self) -> Optional['LxmlElementProtocol']: ...
    def getprevious(self) -> Optional['LxmlElementProtocol']: ...
    def itersiblings(self, tag: Optional[str] = ..., *tags: str,
                     preceding: bool = False) -> Iterable['LxmlElementProtocol']: ...

    @property
    def nsmap(self) -> NsmapType: ...

    @property
    def attrib(self) -> LxmlAttribProtocol: ...


class DocumentProtocol(Hashable, Protocol):
    def getroot(self) -> Optional[ElementProtocol]: ...
    def parse(self, source: Any, *args: Any, **kwargs: Any) -> ElementProtocol: ...
    def iter(self, tag: Optional[str] = ...) -> Iterator[ElementProtocol]: ...


class LxmlDocumentProtocol(Hashable, Protocol):
    def getroot(self) -> Optional[LxmlElementProtocol]: ...
    def parse(self, source: Any, *args: Any, **kwargs: Any) -> LxmlElementProtocol: ...
    def iter(self, tag: Optional[str] = ...) -> Iterator[LxmlElementProtocol]: ...


class XsdValidatorProtocol(Hashable, Protocol):
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

    def is_atomic(self) -> bool:
        """Returns `True` if the instance is an atomic simpleType, `False` otherwise."""
        ...

    def is_list(self) -> bool:
        """Returns `True` if the instance is a list simpleType, `False` otherwise."""
        ...

    def is_union(self) -> bool:
        """Returns `True` if the instance is a union simpleType, `False` otherwise."""
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

    @overload
    def is_valid(self, obj: Any, use_defaults: bool = True,
                 namespaces: Optional[NamespacesType] = None,
                 *args: Any, **kwargs: Any) -> bool: ...

    @overload
    def is_valid(self, obj: Any, *args: Any, **kwargs: Any) -> bool: ...

    def is_valid(self, obj: Any, *args: Any, **kwargs: Any) -> bool:
        """
        Validates an XML object node using the XSD type. The argument *obj* is an element
        for complex type nodes or a text value for simple type nodes. Returns `True` if
        the argument is valid, `False` otherwise.
        """
        ...

    @overload
    def validate(self, obj: Any, use_defaults: bool = True,
                 namespaces: Optional[NamespacesType] = None,
                 *args: Any, **kwargs: Any) -> None: ...

    @overload
    def validate(self, obj: Any, *args: Any, **kwargs: Any) -> None: ...

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

    @property
    def ref(self) -> Optional[Any]: ...


XsdXPathNodeType = Union['XsdSchemaProtocol', 'XsdElementProtocol']


class XsdAttributeGroupProtocol(XsdComponentProtocol, Protocol):

    @overload
    def get(self, key: Optional[str]) -> Optional[XsdAttributeProtocol]: ...

    @overload
    def get(self, key: Optional[str], default: _T) -> Union[XsdAttributeProtocol, _T]: ...

    def get(self, key: Optional[str], default: Optional[_T] = None) \
        -> Union[XsdAttributeProtocol, _T, None]: ...

    def items(self) -> ItemsView[Optional[str], XsdAttributeProtocol]: ...

    def __contains__(self, key: Optional[str]) -> bool: ...

    def __getitem__(self, key: Optional[str]) -> XsdAttributeProtocol: ...

    def __iter__(self) -> Iterator[Optional[str]]: ...

    def __len__(self) -> int: ...

    def __hash__(self) -> int: ...

    @property
    def ref(self) -> Optional[Any]: ...


class XsdElementProtocol(XsdComponentProtocol, ElementProtocol, Protocol):

    def __iter__(self) -> Iterator['XsdElementProtocol']: ...

    def find(
            self, path: str, namespaces: Optional[NamespacesType] = ...
    ) -> Optional[XsdXPathNodeType]: ...
    def iter(self, tag: Optional[str] = ...) -> Iterator['XsdElementProtocol']: ...

    @property
    def name(self) -> Optional[str]: ...

    @property
    def type(self) -> Optional[XsdTypeProtocol]: ...

    @property
    def ref(self) -> Optional[Any]: ...

    @property
    def attrib(self) -> XsdAttributeGroupProtocol: ...


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


class XsdSchemaProtocol(XsdValidatorProtocol, ElementProtocol, Protocol):

    def __iter__(self) -> Iterator[XsdXPathNodeType]: ...

    def find(
            self, path: str, namespaces: Optional[NamespacesType] = ...
    ) -> Optional[XsdXPathNodeType]: ...
    def iter(self, tag: Optional[str] = ...) -> Iterator[XsdXPathNodeType]: ...

    @property
    def tag(self) -> str: ...

    @property
    def attrib(self) -> MutableMapping[Optional[str], 'XsdAttributeProtocol']: ...


__all__ = ['ElementProtocol', 'EtreeElementProtocol', 'LxmlAttribProtocol',
           'LxmlElementProtocol', 'DocumentProtocol', 'LxmlDocumentProtocol',
           'XsdValidatorProtocol', 'XsdComponentProtocol', 'XsdTypeProtocol',
           'XsdAttributeProtocol', 'XsdAttributeGroupProtocol',
           'XsdElementProtocol', 'GlobalMapsProtocol', 'XsdSchemaProtocol',]
