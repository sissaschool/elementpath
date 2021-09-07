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
import sys
from typing import TYPE_CHECKING, Any


if not TYPE_CHECKING or sys.version_info < (3, 8):
    # For runtime or for Python < 3.8 fallback to typing.Any

    ElementProtocol = Any
    LxmlElementProtocol: Any
    DocumentProtocol = Any
    XsdComponentProtocol = Any
    XsdTypeProtocol = Any
    XsdElementProtocol = Any
    XsdAttributeProtocol = Any
    GlobalMapsProtocol = Any
    XsdSchemaProtocol = Any
else:
    from typing import Dict, Iterator, Iterable, List, Literal, \
        NoReturn, Optional, Protocol, Sized

    class ElementProtocol(Iterable['ElementProtocol'], Sized, Protocol):
        def find(
            self, path: str, namespaces: Optional[Dict[str, str]] = ...
        ) -> Optional['ElementProtocol']: ...
        def iter(self, tag: Optional[str] = ...) -> Iterator['ElementProtocol']: ...
        tag: str
        attrib: Dict[str, str]
        text: Optional[str]
        tail: Optional[str]

    class LxmlElementProtocol(ElementProtocol, Protocol):
        def getparent(self) -> Optional['LxmlElementProtocol']: ...
        nsmap: Dict[Optional[str], str]

    class DocumentProtocol(Iterable[ElementProtocol], Protocol):
        def getroot(self) -> ElementProtocol: ...
        def parse(self, source: Any, *args: Any, **kwargs: Any) -> ElementProtocol: ...
        def iter(self, tag: Optional[str] = ...) -> Iterator[ElementProtocol]: ...

    class XsdComponentProtocol(Protocol):
        def is_matching(self, name: Optional[str],
                        default_namespace: Optional[str] = None) -> bool: ...
        name: Optional[str]
        local_name:  Optional[str]

    class XsdTypeProtocol(XsdComponentProtocol, Protocol):
        def is_simple(self) -> bool:
            """Returns `True` if it's a simpleType instance, `False` if it's a complexType."""
        def is_empty(self) -> bool:
            """
            Returns `True` if it's a simpleType instance or a complexType with empty content,
            `False` otherwise.
            """
        def has_simple_content(self) -> bool:
            """
            Returns `True` if it's a simpleType instance or a complexType with simple content,
            `False` otherwise.
            """
        def has_mixed_content(self) -> bool:
            """
            Returns `True` if it's a complexType with mixed content, `False` otherwise.
            """
        def is_element_only(self) -> bool:
            """
            Returns `True` if it's a complexType with element-only content, `False` otherwise.
            """
        def is_key(self) -> bool:
            """Returns `True` if it's a simpleType derived from xs:ID, `False` otherwise."""
        def is_qname(self) -> bool:
            """Returns `True` if it's a simpleType derived from xs:QName, `False` otherwise."""
        def is_notation(self) -> bool:
            """Returns `True` if it's a simpleType derived from xs:NOTATION, `False` otherwise."""
        def validate(self, obj, *args, **kwargs) -> NoReturn:
            """
            Validates an XML object node using the XSD type. The argument *obj* is an element
            for complex type nodes or a text value for simple type nodes. Raises a `ValueError`
            compatible exception (a `ValueError` or a subclass of it) if the argument is not valid.
            """
        def decode(self, obj, *args, **kwargs) -> Any:
            """
            Decodes an XML object node using the XSD type. The argument *obj* is an element
            for complex type nodes or a text value for simple type nodes. Raises a `ValueError`
            or a `TypeError` compatible exception if the argument it's not valid.
            """

    class XsdElementProtocol(XsdComponentProtocol, ElementProtocol, Protocol):
        type: XsdTypeProtocol

    class XsdAttributeProtocol(XsdComponentProtocol, Protocol):
        type: XsdTypeProtocol

    class GlobalMapsProtocol(Protocol):
        types: Dict[str, XsdTypeProtocol]
        attributes: Dict[str, XsdAttributeProtocol]
        elements: Dict[str, XsdElementProtocol]
        substitution_groups: Dict[str, List[XsdElementProtocol]]

    class XsdSchemaProtocol(ElementProtocol, Protocol):
        xsd_version: Literal['1.0', '1.1']
        tag: Literal['{http://www.w3.org/2001/XMLSchema}schema']
        attrib: Dict[str, Any]
        text: None
        maps: GlobalMapsProtocol


__all__ = ['ElementProtocol', 'LxmlElementProtocol', 'DocumentProtocol',
           'XsdComponentProtocol', 'XsdTypeProtocol', 'XsdElementProtocol',
           'XsdAttributeProtocol', 'GlobalMapsProtocol', 'XsdSchemaProtocol']
