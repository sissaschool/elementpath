#
# Copyright (c), 2018-2021, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
import datetime
import importlib
from copy import copy
from functools import lru_cache
from itertools import chain
from types import ModuleType
from typing import TYPE_CHECKING, cast, Dict, Any, List, Iterable, Iterator, Optional, Union

from .exceptions import ElementPathTypeError
from .datatypes import AnyAtomicType, Timezone
from .xpath_nodes import TypedElement, AttributeNode, TextNode, TypedAttribute, \
    etree_iter_nodes, is_etree_element, is_element_node, is_document_node, \
    is_schema_node, is_lxml_etree_element, is_lxml_document_node, XPathNode, \
    ElementNode, DocumentNode

if TYPE_CHECKING:
    from .xpath_token import XPathToken, XPathAxis

ContextRootType = Union[ElementNode, DocumentNode]
ContextItemType = Optional[Union[ElementNode, DocumentNode, XPathNode, AnyAtomicType]]


class XPathContext:
    """
    The XPath dynamic context. The static context is provided by the parser.

    Usually the dynamic context instances are created providing only the root element.
    Variable values argument is needed if the XPath expression refers to in-scope variables.
    The other optional arguments are needed only if a specific position on the context is
    required, but have to be used with the knowledge of what is their meaning.

    :param root: the root of the XML document, can be a ElementTree instance or an Element.
    :param namespaces: a dictionary with mapping from namespace prefixes into URIs, \
    used when namespace information is not available within document and element nodes. \
    This can be useful when the dynamic context has additional namespaces and root \
    is an Element or an ElementTree instance of the standard library.
    :param item: the context item. A `None` value means that the context is positioned on \
    the document node.
    :param position: the current position of the node within the input sequence.
    :param size: the number of items in the input sequence.
    :param axis: the active axis. Used to choose when apply the default axis ('child' axis).
    :param variables: dictionary of context variables that maps a QName to a value.
    :param current_dt: current dateTime of the implementation, including explicit timezone.
    :param timezone: implicit timezone to be used when a date, time, or dateTime value does \
    not have a timezone.
    :param documents: available documents. This is a mapping of absolute URI \
    strings onto document nodes. Used by the function fn:doc.
    :param collections: available collections. This is a mapping of absolute URI \
    strings onto sequences of nodes. Used by the XPath 2.0+ function fn:collection.
    :param default_collection: this is the sequence of nodes used when fn:collection \
    is called with no arguments.
    :param resource_collections: available URI collections. This is a mapping of absolute \
    URI strings to sequences of URIs. Used by the XPath 3.0+ function fn:uri-collection.
    :param default_resource_collection: this is the sequence of URIs used when \
    fn:uri-collection is called with no arguments.
    :param allow_environment: defines if the access to system environment is allowed, \
    for default is `False`. Used by the XPath 3.0+ functions fn:environment-variable \
    and fn:available-environment-variables.
    """
    _iter_nodes = staticmethod(etree_iter_nodes)
    _parent_map: Optional[Dict[ElementNode, ContextRootType]] = None
    _etree: Optional[ModuleType] = None
    root: ContextRootType
    item: Optional[ContextItemType]

    def __init__(self,
                 root: ContextRootType,
                 namespaces: Optional[Dict[str, str]] = None,
                 item: Optional[ContextItemType] = None,
                 position: int = 1,
                 size: int = 1,
                 axis: Optional[str] = None,
                 variables: Optional[Dict[str, Any]] = None,
                 current_dt: Optional[datetime.datetime] = None,
                 timezone: Optional[Timezone] = None,
                 documents: Optional[DocumentNode] = None,
                 collections: Optional[ElementNode] = None,
                 default_collection: Optional[str] = None,
                 resource_collections: Optional[Dict[str, List[str]]] = None,
                 default_resource_collection: Optional[str] = None,
                 allow_environment: bool = False,
                 default_language: Optional[str] = None,
                 default_calendar: Optional[str] = None,
                 default_place=None):

        self.root = root
        self.namespaces = namespaces

        if is_element_node(root):
            self.item = root if item is None else item
        elif is_document_node(root):
            self.item = item
        else:
            msg = "invalid root {!r}, an Element or an ElementTree instance required"
            raise ElementPathTypeError(msg.format(root))

        self.position = position
        self.size = size
        self.axis = axis

        if variables is None:
            self.variables = {}
        else:
            self.variables = {k: v for k, v in variables.items()}

        if timezone is None or isinstance(timezone, Timezone):
            self.timezone = timezone
        else:
            self.timezone = Timezone.fromstring(timezone)
        self.current_dt = current_dt or datetime.datetime.now(tz=self.timezone)

        self.documents = documents
        self.collections = collections
        self.default_collection = default_collection
        self.resource_collections = resource_collections
        self.default_resource_collection = default_resource_collection
        self.allow_environment = allow_environment
        self.default_language = default_language
        self.default_calendar = default_calendar
        self.default_place = default_place

    def __repr__(self):
        return '%s(root=%r, item=%r)' % (self.__class__.__name__, self.root, self.item)

    def __copy__(self):
        obj = object.__new__(self.__class__)
        obj.__dict__.update(self.__dict__)
        obj.axis = None
        obj.variables = {k: v for k, v in self.variables.items()}
        return obj

    def copy(self, clear_axis=True):
        # Unused, so it could be deprecated in the future.
        obj = object.__new__(self.__class__)
        obj.__dict__.update(self.__dict__)
        if clear_axis:
            obj.axis = None
        obj.variables = {k: v for k, v in self.variables.items()}
        return obj

    @property
    def parent_map(self) -> Dict[ElementNode, ContextRootType]:
        if self._parent_map is None:
            self._parent_map: Dict[ElementNode, ContextRootType]
            self._parent_map = {child: elem for elem in self.root.iter() for child in elem}
            if is_document_node(self.root):
                self._parent_map[cast(DocumentNode, self.root).getroot()] = self.root

        return self._parent_map

    @property
    def etree(self) -> ModuleType:
        if self._etree is None:
            self._etree: ModuleType
            if is_lxml_etree_element(self.root) or is_lxml_document_node(self.root):
                self._etree = importlib.import_module('lxml.etree')
            else:
                self._etree = importlib.import_module('xml.etree.ElementTree')
        return self._etree

    @lru_cache(maxsize=1024)
    def get_parent(self, elem: Union[ElementNode, TypedElement]):
        """
        Returns the parent element or `None` for root element and for elements
        that are not included in the tree. Uses a LRU cache to minimize parent
        map rebuilding for trees processed with an incremental parser.
        """
        if isinstance(elem, TypedElement):
            elem = elem.elem
        if elem is self.root:
            return None

        try:
            return self.parent_map[elem]
        except KeyError:
            return None

    def get_path(self, item: Any) -> str:
        """Cached path resolver for elements and attributes. Returns absolute paths."""
        path = []
        if isinstance(item, AttributeNode):
            path.append(f'@{item.name}')
            item = item.parent
        elif isinstance(item, TypedAttribute):
            path.append(f'@{item.attribute.name}')
            item = item.attribute.parent

        if item is None:
            return '' if not path else path[0]
        elif isinstance(item, TypedElement):
            item = item.elem

        while True:
            try:
                path.append(item.tag)
            except AttributeError:
                pass  # is a document node

            parent = self.get_parent(item)
            if parent is None:
                return '/{}'.format('/'.join(reversed(path)))
            item = parent

    def is_principal_node_kind(self):
        if self.axis == 'attribute':
            return isinstance(self.item, (AttributeNode, TypedAttribute))
        else:
            return is_element_node(self.item)

    def iter(self) -> Iterator[Union[ElementNode, DocumentNode, AttributeNode, TextNode]]:
        """Iterates context nodes, including text and attribute nodes."""
        root = self.root
        if is_document_node(root):
            yield root
            root = cast(DocumentNode, root).getroot()
        yield from self._iter_nodes(root, with_attributes=True)

    def iter_results(self, results: Iterable) -> Iterator[ContextItemType]:
        """
        Iterates results in document order.

        :param results: a container with selection results.
        """
        status = self.item

        for self.item in self._iter_nodes(self.root, with_attributes=True):
            if self.item in results:
                yield self.item

            elif isinstance(self.item, AttributeNode):
                # Match XSD decoded attributes
                for typed_attribute in filter(lambda x: isinstance(x, TypedAttribute), results):
                    if typed_attribute.attribute == self.item:
                        yield typed_attribute

            elif is_etree_element(self.item):
                # Match XSD decoded elements
                for typed_element in filter(lambda x: isinstance(x, TypedElement), results):
                    if typed_element.elem is self.item:
                        yield typed_element

        self.item = status

    def inner_focus_select(self, token: Union['XPathToken', 'XPathAxis']):
        """Apply the token's selector with an inner focus."""
        status = self.item, self.size, self.position
        results = [x for x in token.select(copy(self))]

        if token.label == 'axis' and cast('XPathAxis', token).reverse_axis:
            self.size = self.position = len(results)
            for self.item in results:
                yield self.item
                self.position -= 1
        else:
            self.size = len(results)
            for self.position, self.item in enumerate(results, start=1):
                yield self.item

        self.item, self.size, self.position = status

    def iter_product(self, selectors, varnames=None):
        """
        Iterator for cartesian products of selectors.

        :param selectors: a sequence of selector generator functions.
        :param varnames: a sequence of variables for storing the generated values.
        """
        iterators = [x(self) for x in selectors]
        dimension = len(iterators)
        prod = [None] * dimension
        max_index = dimension - 1

        k = 0
        while True:
            try:
                value = next(iterators[k])
            except StopIteration:
                if not k:
                    return
                iterators[k] = selectors[k](self)
                k -= 1
            else:
                try:
                    self.variables[varnames[k]] = value
                except (TypeError, IndexError):
                    pass

                prod[k] = value
                if k == max_index:
                    yield tuple(prod)
                else:
                    k += 1

    ##
    # Context item iterators for axis

    def iter_self(self):
        """Iterator for 'self' axis and '.' shortcut."""
        status = self.axis
        self.axis = 'self'
        yield self.item
        self.axis = status

    def iter_attributes(self) -> Iterator[Union[AttributeNode, TypedAttribute]]:
        """Iterator for 'attribute' axis and '@' shortcut."""
        status: Any

        if isinstance(self.item, (AttributeNode, TypedAttribute)):
            status = self.axis
            self.axis = 'attribute'
            yield self.item
            self.axis = status
            return
        elif not is_element_node(self.item):
            return

        status = self.item, self.axis
        self.axis = 'attribute'

        if isinstance(self.item, TypedElement):
            self.item = self.item.elem

        elem = cast(ElementNode, self.item)
        if is_schema_node(elem):
            # TODO: for backward compatibility, to be removed in release 3.0.
            for self.item in (AttributeNode(*x) for x in elem.attrib.items()):
                yield self.item
        else:
            for self.item in (AttributeNode(x[0], x[1], parent=elem) for x in elem.attrib.items()):
                yield self.item

        self.item, self.axis = status

    def iter_children_or_self(self):
        """Iterator for 'child' forward axis and '/' step."""
        if self.axis is not None:
            yield self.item
            return

        status = self.item, self.axis
        self.axis = 'child'

        if isinstance(self.item, TypedElement):
            self.item = self.item.elem

        if self.item is None:
            self.item = self.root.getroot() if is_document_node(self.root) else self.root
            yield self.item
        elif is_etree_element(self.item):
            elem = self.item
            if elem.text is not None:
                self.item = TextNode(elem.text, elem)
                yield self.item

            for child in elem:
                self.item = child
                yield child

                if child.tail is not None:
                    self.item = TextNode(child.tail, child, True)
                    yield self.item

        elif is_document_node(self.item):
            self.item = self.item.getroot()
            yield self.item

        self.item, self.axis = status

    def iter_parent(self):
        """Iterator for 'parent' reverse axis and '..' shortcut."""
        if isinstance(self.item, TypedElement):
            parent = self.get_parent(self.item.elem)
        else:
            parent = self.get_parent(self.item)

        if parent is not None:
            status = self.item, self.axis
            self.axis = 'parent'

            self.item = parent
            yield self.item

            self.item, self.axis = status

    def iter_siblings(self, axis=None):
        """
        Iterator for 'following-sibling' forward axis and 'preceding-sibling' reverse axis.

        :param axis: the context axis, default is 'following-sibling'.
        """
        if isinstance(self.item, TypedElement):
            item = self.item.elem
        elif not is_etree_element(self.item) or callable(self.item.tag):
            return
        else:
            item = self.item

        parent = self.get_parent(item)
        if parent is None:
            return

        status = self.item, self.axis
        self.axis = axis or 'following-sibling'

        if axis == 'preceding-sibling':
            for child in parent:  # pragma: no cover
                if child is item:
                    break
                self.item = child
                yield child
        else:
            follows = False
            for child in parent:
                if follows:
                    self.item = child
                    yield child
                elif child is item:
                    follows = True

        self.item, self.axis = status

    def iter_descendants(self, axis=None, inner_focus=False):
        """
        Iterator for 'descendant' and 'descendant-or-self' forward axes and '//' shortcut.

        :param axis: the context axis, for default has no explicit axis.
        :param inner_focus: if `True` splits between outer focus and inner focus. \
        In this case set the context size at start and change both position and \
        item at each iteration. For default only context item is changed.
        """
        with_self = axis != 'descendant'

        if self.item is None:
            if is_document_node(self.root):
                descendants = self._iter_nodes(self.root, with_root=with_self)
            elif with_self:
                # Yields None in order to emulate position on document
                # FIXME replacing the self.root with ElementTree(self.root)?
                descendants = chain((None,), self._iter_nodes(self.root))
            else:
                descendants = self._iter_nodes(self.root)
        elif is_element_node(self.item) or is_document_node(self.item):
            descendants = self._iter_nodes(self.item, with_root=with_self)
        elif with_self:
            descendants = self.item,
        else:
            return

        if inner_focus:
            status = self.item, self.position, self.size, self.axis
            self.axis = axis
            results = [e for e in descendants]

            self.size = len(results)
            for self.position, self.item in enumerate(results, start=1):
                yield self.item

            self.item, self.position, self.size, self.axis = status
        else:
            status = self.item, self.axis
            self.axis = axis
            for self.item in descendants:
                yield self.item
            self.item, self.axis = status

    def iter_ancestors(self, axis=None):
        """
        Iterator for 'ancestor' and 'ancestor-or-self' reverse axes.

        :param axis: the context axis, default is 'ancestor'.
        """
        status = self.item, self.axis
        self.axis = axis or 'ancestor'

        if isinstance(self.item, TypedElement):
            self.item = self.item.elem

        ancestors = [self.item] if self.axis == 'ancestor-or-self' else []
        parent = self.get_parent(self.item)
        while parent is not None:
            ancestors.append(parent)
            parent = self.get_parent(parent)

        for self.item in reversed(ancestors):
            yield self.item

        self.item, self.axis = status

    def iter_preceding(self):
        """Iterator for 'preceding' reverse axis."""
        item = self.item.elem if isinstance(self.item, TypedElement) else self.item
        if not is_etree_element(item) or item is self.root or callable(item.tag):
            return

        status = self.item, self.axis
        self.axis = 'preceding'

        ancestors = []
        elem = item
        while True:
            parent = self.get_parent(elem)
            if parent is None:
                break
            else:
                ancestors.append(parent)
                elem = parent

        for elem in self.root.iter():  # pragma: no cover
            if elem is item:
                break
            elif elem not in ancestors:
                self.item = elem
                yield elem

        self.item, self.axis = status

    def iter_followings(self):
        """Iterator for 'following' forward axis."""
        status = self.item, self.axis
        self.axis = 'following'

        if self.item is None or self.item is self.root:
            return
        elif isinstance(self.item, TypedElement):
            self.item = self.item.elem
        elif not is_etree_element(self.item) or callable(self.item.tag):
            return

        descendants = set(self._iter_nodes(self.item))
        follows = False
        for elem in self._iter_nodes(self.root):
            if follows:
                if elem not in descendants:
                    self.item = elem
                    yield elem
            elif self.item is elem:
                follows = True

        self.item, self.axis = status


class XPathSchemaContext(XPathContext):
    """
    The XPath dynamic context base class for schema bounded parsers. Use this class
    as dynamic context for schema instances in order to perform a schema-based type
    checking during the static analysis phase. Don't use this as dynamic context on
    XML instances.
    """
