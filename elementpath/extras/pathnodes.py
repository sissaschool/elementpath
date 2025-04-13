#
# Copyright (c), 2025, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""Experimental use of XDM on pathlib.Path objects."""

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Optional

from elementpath.protocols import XsdElementProtocol
from elementpath.xpath_nodes import ParentNodeType, ChildNodeType, \
    XPathNodeTree, AttributeNode, DocumentNode, ElementNode
from elementpath.helpers import match_wildcard
from elementpath.namespaces import XSD_NAMESPACE
from elementpath.datatypes import DateTime, AtomicType


class PathElementNode(ElementNode):
    name: str
    obj: Path
    xsd_element: Optional[XsdElementProtocol]

    __slots__ = ('stat',)

    def __init__(self,
                 path: Path,
                 parent: Optional[ParentNodeType] = None) -> None:

        self.name = path.name
        self.obj = path
        self.stat = path.stat()
        self.parent = parent
        self.position = self.stat.st_ino
        self.children = []
        self.xsd_type = None
        self._nsmap = None

        if parent is not None:
            self.tree = parent.tree
        else:
            self.tree = XPathNodeTree(self, uri=path.as_uri())

        self.tree.elements[path] = self

    @property
    def content(self) -> Path:
        return self.obj

    elem = value = content

    @property
    def attributes(self) -> list[AttributeNode]:
        if not hasattr(self, '_attributes'):
            self._attributes = [

            ]
        return self._attributes

    @property
    def string_value(self) -> str:
        if self.obj.is_dir():
            return ''
        if self.obj.is_file():
            return self.obj.read_text()
        else:
            return ''

    @property
    def iter_typed_values(self) -> Iterator[AtomicType]:
        yield from ()

    @property
    def is_typed(self) -> bool:
        return False

    def match_name(self, name: str, default_namespace: Optional[str] = None) -> bool:
        if '*' in name:
            return match_wildcard(self.name, name)
        elif name[0] == '{' or not default_namespace:
            return self.name == name
        else:
            return self.name == f'{{{default_namespace}}}{name}'

    def get_document_node(self, replace: bool = True, as_parent: bool = True) -> 'DocumentNode':
        return PathDocumentNode(Path(self.obj.absolute().root))

    def __iter__(self) -> Iterator[ChildNodeType]:
        if not self.children:
            if self.obj.is_dir():
                for path in self.obj.iterdir():
                    if path in self.tree.elements:
                        self.children.append(self.tree.elements[path])
                    else:
                        self.children.append(PathElementNode(path, self))

        yield from self.children

    def iter_descendants(self, with_self: bool = True) -> Iterator[ChildNodeType]:
        if with_self:
            yield self

        for child in self:
            if isinstance(child, PathElementNode):
                yield from child.iter_descendants()
            else:
                yield child


class PathDocumentNode(DocumentNode):
    obj: Path

    __slots__ = ('stat',)

    def __init__(self, document: Path,
                 uri: Optional[str] = None,
                 position: int = 1) -> None:

        assert document.is_dir()
        self.obj = document
        self.name = None
        self.parent = None
        self.position = position
        self.children = []
        self.tree = XPathNodeTree(self, uri=uri)

    @property
    def document(self) -> Path:
        return self.obj

    @property
    def string_value(self) -> str:
        return self.obj.read_text()

    def __iter__(self) -> Iterator[ChildNodeType]:
        if not self.children:
            for path in self.obj.iterdir():
                if path in self.tree.elements:
                    self.children.append(self.tree.elements[path])
                else:
                    self.children.append(PathElementNode(path, self))

        yield from self.children


class IntAttributeNode(AttributeNode):
    name: str
    obj: int
    parent: Optional['PathElementNode']

    __slots__ = ()

    def __init__(self,
                 name: str,
                 value: int,
                 parent: Optional['PathElementNode'] = None) -> None:

        self.name = name
        self.obj = value
        self.parent = parent
        self.position = parent.position if parent is not None else 1
        self.xsd_type = None

    @property
    def value(self) -> int:
        return self.obj

    @property
    def string_value(self) -> str:
        return str(self.obj)

    @property
    def iter_typed_values(self) -> Iterator[AtomicType]:
        yield self.obj

    @property
    def type_name(self) -> Optional[str]:
        return f'{{{XSD_NAMESPACE}}}int'


class DatetimeAttributeNode(AttributeNode):
    name: str
    obj: datetime
    parent: Optional['PathElementNode']

    __slots__ = ()

    def __init__(self,
                 name: str,
                 value: datetime,
                 parent: Optional['PathElementNode'] = None) -> None:

        self.name = name
        self.obj = value
        self.parent = parent
        self.position = parent.position if parent is not None else 1
        self.xsd_type = None

    @property
    def value(self) -> datetime:
        return self.obj

    @property
    def string_value(self) -> str:
        return str(self.obj)

    @property
    def iter_typed_values(self) -> Iterator[AtomicType]:
        yield DateTime.fromdatetime(self.obj)

    @property
    def type_name(self) -> Optional[str]:
        return f'{{{XSD_NAMESPACE}}}dateTime'


def build_path_node_tree(path: Path, fragment: Optional[bool] = None) -> ParentNodeType:
    path = path.resolve(strict=True)

    if fragment:
        # Explicitly requested a fragment: create only one parentless element node
        return PathElementNode(path)

    parents = [p for p in reversed(path.parents)]
    parent: ParentNodeType = PathDocumentNode(parents[0], uri=path.as_uri())
    for p in parents:
        parent = PathElementNode(p, parent)
    return PathElementNode(path, parent)
