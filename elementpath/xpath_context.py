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
from itertools import chain
from types import ModuleType
from typing import TYPE_CHECKING, cast, Dict, Any, List, Iterator, \
    Optional, Sequence, Union, Callable, MutableMapping, Set, Tuple

from .exceptions import ElementPathTypeError, ElementPathValueError
from .namespaces import XML_NAMESPACE
from .datatypes import AnyAtomicType, Timezone
from .protocols import ElementProtocol, XsdElementProtocol, XMLSchemaProtocol
from .xpath_nodes import NamespaceNode, AttributeNode, TextNode, TypedElement, \
    TypedAttribute, etree_iter_nodes, is_etree_element, is_element_node, \
    is_document_node, is_lxml_etree_element, is_lxml_document_node, \
    XPathNode, ElementNode, DocumentNode, XPathNodeType, etree_iter_root

if TYPE_CHECKING:
    from .xpath_token import XPathToken, XPathAxis


ContextRootType = Union[ElementNode, DocumentNode]
ContextItemType = Union[XPathNodeType, AnyAtomicType]


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
    :param text_resources: available text resources. This is a mapping of absolute URI strings \
    onto text resources. Used by XPath 3.0+ function fn:unparsed-text/fn:unparsed-text-lines.
    :param resource_collections: available URI collections. This is a mapping of absolute \
    URI strings to sequence of URIs. Used by the XPath 3.0+ function fn:uri-collection.
    :param default_resource_collection: this is the sequence of URIs used when \
    fn:uri-collection is called with no arguments.
    :param allow_environment: defines if the access to system environment is allowed, \
    for default is `False`. Used by the XPath 3.0+ functions fn:environment-variable \
    and fn:available-environment-variables.
    """
    _iter_nodes = staticmethod(etree_iter_nodes)
    _parent_map: Optional[MutableMapping[ElementNode, ContextRootType]] = None
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
                 timezone: Optional[Union[str, Timezone]] = None,
                 documents: Optional[Dict[str, DocumentNode]] = None,
                 collections: Optional[Dict[str, ElementNode]] = None,
                 default_collection: Optional[str] = None,
                 text_resources: Optional[Dict[str, str]] = None,
                 resource_collections: Optional[Dict[str, List[str]]] = None,
                 default_resource_collection: Optional[str] = None,
                 allow_environment: bool = False,
                 default_language: Optional[str] = None,
                 default_calendar: Optional[str] = None,
                 default_place: Optional[str] = None) -> None:

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
        self.text_resources = text_resources if text_resources is not None else {}
        self.resource_collections = resource_collections
        self.default_resource_collection = default_resource_collection
        self.allow_environment = allow_environment
        self.default_language = default_language
        self.default_calendar = default_calendar
        self.default_place = default_place

    def __repr__(self) -> str:
        return '%s(root=%r, item=%r)' % (self.__class__.__name__, self.root, self.item)

    def __copy__(self) -> 'XPathContext':
        obj: XPathContext = object.__new__(self.__class__)
        obj.__dict__.update(self.__dict__)
        obj.axis = None
        obj.variables = {k: v for k, v in self.variables.items()}
        return obj

    def copy(self, clear_axis: bool = True) -> 'XPathContext':
        # Unused, so it could be deprecated in the future.
        obj: XPathContext = object.__new__(self.__class__)
        obj.__dict__.update(self.__dict__)
        if clear_axis:
            obj.axis = None
        obj.variables = {k: v for k, v in self.variables.items()}
        return obj

    @property
    def parent_map(self) -> MutableMapping[ElementNode, ContextRootType]:
        if self._parent_map is None:
            self._parent_map: Dict[ElementNode, ContextRootType]
            self._parent_map = {child: elem for elem in self.root.iter() for child in elem}
            if is_document_node(self.root):
                self._parent_map[cast(DocumentNode, self.root).getroot()] = self.root

            # Add parent mapping for trees bound to dynamic context variables
            for v in self.variables.values():
                if is_document_node(v):
                    doc = cast(DocumentNode, v)
                    self._parent_map.update((c, e) for e in doc.iter() for c in e)
                    self._parent_map[doc.getroot()] = doc
                elif is_element_node(v):
                    if isinstance(v, TypedElement):
                        root = v.elem
                    else:
                        root = cast(ElementNode, v)

                    self._parent_map.update((c, e) for e in root.iter() for c in e)

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

    def get_root(self, node: Any) -> Union[None, ElementNode, DocumentNode]:
        if any(node == x for x in self.iter()):
            return self.root

        if self.documents is not None:
            try:
                for uri, doc in self.documents.items():
                    doc_context = XPathContext(root=doc)
                    if any(node == x for x in doc_context.iter()):
                        return doc
            except AttributeError:
                pass

        return None

    def get_parent(self, elem: Union[ElementNode, TypedElement]) \
            -> Union[None, ElementNode, DocumentNode]:
        """Returns the parent of the element or `None` if it has no parent."""
        _elem = elem.elem if isinstance(elem, TypedElement) else elem

        try:
            return self.parent_map[_elem]
        except KeyError:
            try:
                # fallback for lxml elements
                parent = _elem.getparent()  # type: ignore[attr-defined]
            except AttributeError:
                return None
            else:
                return cast(Optional[ElementNode], parent)

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

    def is_principal_node_kind(self) -> bool:
        if self.axis == 'attribute':
            return isinstance(self.item, (AttributeNode, TypedAttribute))
        elif self.axis == 'namespace':
            return isinstance(self.item, NamespaceNode)
        else:
            return is_element_node(self.item)

    def match_name(self, name: Optional[str] = None,
                   default_namespace: Optional[str] = None) -> bool:
        """
        Returns `True` if the context item is matching the name, `False` otherwise.

        :param name: a fully qualified name, a local name or a wildcard. The accepted \
        wildcard formats are '*', '*:*', '*:local-name' and '{namespace}*'.
        :param default_namespace: the namespace URI associated with unqualified names. \
        Used for matching element names (tag).
        """
        if self.axis == 'attribute':
            if not isinstance(self.item, (AttributeNode, TypedAttribute)):
                return False
            item_name = self.item.name
        elif is_element_node(self.item):
            item_name = cast(ElementProtocol, self.item).tag
        else:
            return False

        if name is None or name == '*' or name == '*:*':
            return True

        if not name:
            return not item_name
        elif name[0] == '*':
            try:
                _, _name = name.split(':')
            except (ValueError, IndexError):
                raise ElementPathValueError("unexpected format %r for argument 'name'" % name)
            else:
                if item_name.startswith('{'):
                    return item_name.split('}')[1] == _name
                else:
                    return item_name == _name

        elif name[-1] == '*':
            if name[0] != '{' or '}' not in name:
                raise ElementPathValueError("unexpected format %r for argument 'name'" % name)
            elif item_name.startswith('{'):
                return item_name.split('}')[0][1:] == name.split('}')[0][1:]
            else:
                return False
        elif name[0] == '{' or not default_namespace:
            return item_name == name
        elif self.axis == 'attribute':
            return item_name == name
        else:
            return item_name == '{%s}%s' % (default_namespace, name)

    def iter(self, namespaces: Optional[Dict[str, str]] = None) \
            -> Iterator[Union[ElementNode, DocumentNode, TextNode, NamespaceNode, AttributeNode]]:
        """
        Iterates context nodes in document order, including namespace and attribute nodes.

        :param namespaces: a fallback mapping for generating namespaces nodes, \
        used when element nodes do not have a property for in-scope namespaces.
        """
        item: Union[ElementNode, DocumentNode, TextNode]

        for item in self._iter_nodes(self.root):
            if not hasattr(item, 'tag'):
                yield item
            else:
                elem = cast(ElementNode, item)
                if callable(elem.tag):
                    yield elem
                    continue

                nsmap: Optional[Dict[str, str]] = getattr(elem, 'nsmap', namespaces)
                if nsmap is not None:
                    for pfx, uri in nsmap.items():
                        yield NamespaceNode(pfx, uri, elem)
                    if 'xml' not in nsmap:
                        yield NamespaceNode('xml', XML_NAMESPACE, elem)

                yield elem

                for name, value in elem.attrib.items():
                    yield AttributeNode(name, value, elem)

    def iter_results(self, results: Set[Any], namespaces: Optional[Dict[str, str]] = None) \
            -> Iterator[Optional[ContextItemType]]:
        """
        Generate results in document order.

        :param results: a container with selection results.
        :param namespaces: a fallback mapping for generating namespaces nodes, \
        used when element nodes do not have a property for in-scope namespaces.
        """
        status = self.root, self.item
        roots: Any
        root: Union[DocumentNode, ElementNode]

        documents = [v for v in results if is_document_node(v)]
        documents.append(self.root)
        documents.extend(v for v in self.variables.values() if is_document_node(v))
        visited_docs = set()

        for doc in documents:
            if doc in visited_docs:
                continue
            visited_docs.add(doc)

            self.root = doc
            for self.item in self.iter(namespaces):
                if self.item in results:
                    yield self.item
                    results.remove(self.item)

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

        self.root, self.item = status

    def inner_focus_select(self, token: Union['XPathToken', 'XPathAxis']) -> Iterator[Any]:
        """Apply the token's selector with an inner focus."""
        status = self.item, self.size, self.position, self.axis
        results = [x for x in token.select(self.copy(clear_axis=False))]
        self.axis = None

        if token.label == 'axis' and cast('XPathAxis', token).reverse_axis:
            self.size = self.position = len(results)
            for self.item in results:
                yield self.item
                self.position -= 1
        else:
            self.size = len(results)
            for self.position, self.item in enumerate(results, start=1):
                yield self.item

        self.item, self.size, self.position, self.axis = status

    def iter_product(self, selectors: Sequence[Callable[[Any], Any]],
                     varnames: Optional[Sequence[str]] = None) -> Iterator[Any]:
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
                if varnames is not None:
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

    def iter_self(self) -> Iterator[Any]:
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
        for self.item in (AttributeNode(x[0], x[1], parent=elem) for x in elem.attrib.items()):
            yield self.item

        self.item, self.axis = status

    def iter_children_or_self(self) -> Iterator[Any]:
        """Iterator for 'child' forward axis and '/' step."""
        if self.axis is not None:
            yield self.item
            return

        status = self.item, self.axis
        self.axis = 'child'

        if isinstance(self.item, TypedElement):
            self.item = self.item.elem

        if self.item is None:
            if is_document_node(self.root):
                document = cast(DocumentNode, self.root)
                root = document.getroot()
            else:
                root = cast(ElementProtocol, self.root)

            for self.item in etree_iter_root(root):
                yield self.item

        elif is_etree_element(self.item):
            elem = cast(ElementNode, self.item)
            if callable(elem.tag):
                return
            elif elem.text is not None:
                self.item = TextNode(elem.text, elem)
                yield self.item

            for child in elem:
                self.item = child
                yield child

                if child.tail is not None:
                    self.item = TextNode(child.tail, child, True)
                    yield self.item

        elif is_document_node(self.item):
            document = cast(DocumentNode, self.item)
            for self.item in etree_iter_root(document.getroot()):
                yield self.item

        self.item, self.axis = status

    def iter_parent(self) -> Iterator[ElementNode]:
        """Iterator for 'parent' reverse axis and '..' shortcut."""
        if isinstance(self.item, TypedElement):
            parent = self.get_parent(self.item.elem)
        elif isinstance(self.item, TextNode):
            parent = self.item.parent
            if parent is not None and (callable(parent.tag) or self.item.is_tail()):
                parent = self.get_parent(parent)
        elif isinstance(self.item, XPathNode):
            parent = self.item.parent
        elif hasattr(self.item, 'tag'):
            parent = self.get_parent(cast(ElementNode, self.item))
        else:
            return  # not applicable

        if parent is not None:
            status = self.item, self.axis
            self.axis = 'parent'

            self.item = parent
            yield cast(ElementNode, self.item)

            self.item, self.axis = status

    def iter_siblings(self, axis: Optional[str] = None) \
            -> Iterator[Union[ElementNode, TextNode]]:
        """
        Iterator for 'following-sibling' forward axis and 'preceding-sibling' reverse axis.

        :param axis: the context axis, default is 'following-sibling'.
        """
        if isinstance(self.item, TypedElement):
            item = self.item.elem
        elif not is_etree_element(self.item) or callable(getattr(self.item, 'tag')):
            return
        else:
            item = cast(ElementNode, self.item)

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
                if child.tail is not None:
                    self.item = TextNode(child.tail, child, True)
                    yield self.item
        else:
            follows = False
            for child in parent:
                if follows:
                    self.item = child
                    yield child
                    if child.tail is not None:
                        self.item = TextNode(child.tail, child, True)
                        yield self.item
                elif child is item:
                    follows = True

        self.item, self.axis = status

    def iter_descendants(self, axis: Optional[str] = None,
                         inner_focus: bool = False) -> Iterator[Any]:
        """
        Iterator for 'descendant' and 'descendant-or-self' forward axes and '//' shortcut.

        :param axis: the context axis, for default has no explicit axis.
        :param inner_focus: if `True` splits between outer focus and inner focus. \
        In this case set the context size at start and change both position and \
        item at each iteration. For default only context item is changed.
        """
        descendants: Union[Iterator[Union[XPathNodeType, None]], Tuple[XPathNode]]
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
        elif with_self and isinstance(self.item, XPathNode):
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
            status_ = self.item, self.axis
            self.axis = axis
            for self.item in descendants:
                yield self.item
            self.item, self.axis = status_

    def iter_ancestors(self, axis: Optional[str] = None) -> Iterator[XPathNodeType]:
        """
        Iterator for 'ancestor' and 'ancestor-or-self' reverse axes.

        :param axis: the context axis, default is 'ancestor'.
        """
        if isinstance(self.item, TypedElement):
            parent = self.get_parent(self.item.elem)
        elif isinstance(self.item, TextNode):
            parent = self.item.parent
            if parent is not None and (callable(parent.tag) or self.item.is_tail()):
                parent = self.get_parent(parent)
        elif isinstance(self.item, XPathNode):
            parent = self.item.parent
        elif isinstance(self.item, AnyAtomicType):
            return
        elif self.item is None:
            return  # document position without a document root
        elif hasattr(self.item, 'tag'):
            parent = self.get_parent(cast(ElementNode, self.item))
        elif is_document_node(self.item):
            parent = None
        else:
            return  # is not an XPath node

        status = self.item, self.axis
        self.axis = axis or 'ancestor'

        ancestors: List[Union[ElementNode, DocumentNode, XPathNode]] = []
        if axis == 'ancestor-or-self':
            ancestors.append(self.item)

        while parent is not None:
            ancestors.append(parent)
            parent = self.get_parent(parent)  # type: ignore[arg-type]

        for self.item in reversed(ancestors):
            yield self.item

        self.item, self.axis = status

    def iter_preceding(self) -> Iterator[ElementNode]:
        """Iterator for 'preceding' reverse axis."""
        item: Union[ElementNode, XPathNode]
        parent: Union[None, ElementNode, DocumentNode]

        if isinstance(self.item, TypedElement):
            item = self.item.elem
            parent = self.get_parent(item)
        elif isinstance(self.item, XPathNode):
            item = self.item
            parent = item.parent
            if parent is None:
                return
            if callable(parent.tag):
                parent = self.get_parent(parent)
        elif is_element_node(self.item):
            item = cast(ElementNode, self.item)
            if item is self.root:
                return
            parent = self.get_parent(item)
        else:
            return

        status = self.item, self.axis
        self.axis = 'preceding'

        ancestors = set()
        while parent is not None:
            ancestors.add(parent)
            parent = self.get_parent(parent)  # type: ignore[arg-type]

        for elem in self._iter_nodes(self.root):  # pragma: no cover
            if elem is item:
                break
            elif elem not in ancestors:
                self.item = cast(ElementNode, elem)
                yield self.item

        self.item, self.axis = status

    def iter_followings(self) -> Iterator[XPathNodeType]:
        """Iterator for 'following' forward axis."""
        status = self.item, self.axis
        self.axis = 'following'

        if self.item is None or self.item is self.root:
            return
        elif isinstance(self.item, TypedElement):
            self.item = self.item.elem
        elif not is_etree_element(self.item) \
                or callable(getattr(self.item, 'tag')):
            return

        descendants = set(self._iter_nodes(self.item))
        follows = False
        for item in self._iter_nodes(self.root):
            if follows:
                if item not in descendants:
                    self.item = item
                    yield item
            elif self.item is item:
                follows = True

        self.item, self.axis = status


class XPathSchemaContext(XPathContext):
    """
    The XPath dynamic context base class for schema bounded parsers. Use this class
    as dynamic context for schema instances in order to perform a schema-based type
    checking during the static analysis phase. Don't use this as dynamic context on
    XML instances.
    """
    iter_children_or_self: Callable[..., Iterator[Union[XsdElementProtocol, XMLSchemaProtocol]]]
    root: XMLSchemaProtocol
