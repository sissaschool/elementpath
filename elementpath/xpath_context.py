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
from types import ModuleType
from typing import TYPE_CHECKING, cast, Any, Dict, List, Optional, Set, Union

from elementpath._typing import Iterator, Sequence, Callable
from elementpath.aliases import NamespacesType, SequenceType, InputType
from elementpath.protocols import ElementProtocol, DocumentProtocol
from elementpath.exceptions import ElementPathTypeError
from elementpath.tdop import Token
from elementpath.datatypes import AnyAtomicType, AtomicType, Timezone, Language
from elementpath.etree import is_etree_element, is_etree_element_instance, is_etree_document
from elementpath.xpath_nodes import ChildNodeType, XPathNode, AttributeNode, NamespaceNode, \
    CommentNode, ProcessingInstructionNode, ElementNode, DocumentNode
from elementpath.tree_builders import RootArgType, get_node_tree

if TYPE_CHECKING:
    from .xpath_tokens import XPathToken, XPathAxis, XPathFunction  # noqa: F401

__all__ = ['XPathContext', 'XPathSchemaContext', 'ContextType', 'ItemType',
           'ValueType', 'ItemArgType', 'FunctionArgType']

###
# Type annotations aliases for context and tokens classes
ContextType = Union['XPathContext', 'XPathSchemaContext', None]
ItemType = Union[XPathNode, AtomicType, 'XPathFunction']
ValueType = SequenceType[ItemType]
ItemArgType = Union[ItemType, ElementProtocol, DocumentProtocol]
FunctionArgType = Union[InputType[ItemArgType], ValueType]

NodeArgType = Union[XPathNode, ElementProtocol, DocumentProtocol]
CollectionArgType = Optional[InputType[NodeArgType]]


class XPathContext:
    """
    The XPath dynamic context. The static context is provided by the parser.

    Usually the dynamic context instances are created providing only the root element.
    Variable values argument is needed if the XPath expression refers to in-scope variables.
    The other optional arguments are needed only if a specific position on the context is
    required, but have to be used with the knowledge of what is their meaning.

    :param root: the root of the XML document, usually an ElementTree instance or an \
    Element. A schema or a schema element can also be provided, or an already built \
    node tree. For default is `None`, in which case no XML root is set, and you have \
    to provide an *item* argument.
    :param namespaces: a dictionary with mapping from namespace prefixes into URIs, \
    used when namespace information is not available within document and element nodes. \
    This can be useful when the dynamic context has additional namespaces and root \
    is an Element or an ElementTree instance of the standard library.
    :param uri: an optional URI associated with the root element or the document.
    :param fragment: if `True` is provided the root is considered a fragment. In this \
    case if `root` is an ElementTree instance skips it and use the root Element. If \
    `False` is provided creates a dummy document when the root is an Element instance. \
    In this case the dummy document value is not included in results. For default the \
    root node kind is preserved.
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
    strings into document nodes. Used by the function fn:doc.
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
    _etree: Optional[ModuleType] = None
    root: Union[DocumentNode, ElementNode, None] = None
    document: Optional[DocumentNode] = None
    item: ItemType
    total_nodes: int = 0  # Number of nodes associated to the context

    variables: Dict[str, ValueType]
    documents: Optional[Dict[str, DocumentNode]] = None
    collections = None
    default_collection = None

    def __init__(self,
                 root: Optional[RootArgType] = None,
                 namespaces: Optional[NamespacesType] = None,
                 uri: Optional[str] = None,
                 fragment: Optional[bool] = None,
                 item: Optional[ItemArgType] = None,
                 position: int = 1,
                 size: int = 1,
                 axis: Optional[str] = None,
                 variables: Optional[Dict[str, InputType[ItemArgType]]] = None,
                 current_dt: Optional[datetime.datetime] = None,
                 timezone: Optional[Union[str, Timezone]] = None,
                 documents: Optional[Dict[str, RootArgType]] = None,
                 collections: Optional[Dict[str, CollectionArgType]] = None,
                 default_collection: CollectionArgType = None,
                 text_resources: Optional[Dict[str, str]] = None,
                 resource_collections: Optional[Dict[str, List[str]]] = None,
                 default_resource_collection: Optional[str] = None,
                 allow_environment: bool = False,
                 default_language: Optional[str] = None,
                 default_calendar: Optional[str] = None,
                 default_place: Optional[str] = None) -> None:

        if namespaces:
            self.namespaces = {k: v for k, v in namespaces.items()}
        else:
            self.namespaces = {}

        if root is not None:
            self.root = get_node_tree(root, self.namespaces, uri, fragment)
            if item is not None:
                self.item = self.get_context_item(item, self.namespaces)
            else:
                self.item = self.root

        elif item is not None:
            self.item = self.get_context_item(item, self.namespaces, uri, fragment)
        else:
            raise ElementPathTypeError("Missing both the root node and the context item!")

        if isinstance(self.root, DocumentNode):
            self.document = self.root
        elif fragment is None and \
                isinstance(self.root, ElementNode) and \
                is_etree_element_instance(self.root.elem):
            # Creates a dummy document that will be not included in results
            self.document = self.root.get_document_node(replace=False, as_parent=False)

        self.position = position
        self.size = size
        self.axis = axis

        if timezone is None or isinstance(timezone, Timezone):
            self.timezone = timezone
        else:
            self.timezone = Timezone.fromstring(timezone)
        self.current_dt = current_dt or datetime.datetime.now(tz=self.timezone)

        if documents is not None:
            # Assume that are all documents because type checking is done by fn:doc().
            self.documents = {
                k: cast(DocumentNode, get_node_tree(v, self.namespaces, k))
                if v is not None else v for k, v in documents.items()
            }

        self.variables = {}
        if variables is not None:
            for varname, value in variables.items():
                self.variables[varname] = self.get_value(value, self.namespaces)

        if collections is not None:
            self.collections = {k: self.get_collection(v) for k, v in collections.items()}

        if default_collection is not None:
            self.default_collection = self.get_collection(default_collection)

        self.text_resources = text_resources if text_resources is not None else {}
        self.resource_collections = resource_collections
        self.default_resource_collection = default_resource_collection
        self.allow_environment = allow_environment
        self.default_language = None if default_language is None else Language(default_language)
        self.default_calendar = default_calendar
        self.default_place = default_place

    def __repr__(self) -> str:
        if self.root is not None:
            return f'{self.__class__.__name__}(root={self.root.value})'
        elif isinstance(self.item, XPathNode):
            return f'{self.__class__.__name__}(item={self.item.value})'
        else:
            return f'{self.__class__.__name__}(item={self.item!r})'

    def __copy__(self) -> 'XPathContext':
        obj: XPathContext = object.__new__(self.__class__)
        obj.__dict__.update(self.__dict__)
        obj.axis = None
        obj.variables = {k: v for k, v in self.variables.items()}
        return obj

    @property
    def etree(self) -> ModuleType:
        if self._etree is None:
            if isinstance(self.root, (DocumentNode, ElementNode)):
                module_name = self.root.value.__class__.__module__
            elif isinstance(self.item, (DocumentNode, ElementNode, CommentNode,
                                        ProcessingInstructionNode)):
                module_name = self.item.value.__class__.__module__
            else:
                module_name = 'xml.etree.ElementTree'

            if module_name in ('lxml.etree', 'lxml.html'):
                self._etree: ModuleType = importlib.import_module('lxml.etree')
            else:
                self._etree = importlib.import_module('xml.etree.ElementTree')

        return self._etree

    def get_root(self, node: Any) -> Union[None, ElementNode, DocumentNode]:
        if isinstance(self.root, (DocumentNode, ElementNode)):
            if any(node is x for x in self.root.iter_lazy()):
                return self.root

        if self.documents is not None:
            for uri, doc in self.documents.items():
                if doc is not None and any(node is x for x in doc.iter_lazy()):
                    return doc

        return None

    def is_document(self) -> bool:
        return isinstance(self.document, DocumentNode)

    def is_fragment(self) -> bool:
        return self.document is None and self.root is not None

    def is_rooted_subtree(self) -> bool:
        return self.root is not None and isinstance(self.root.parent, ElementNode)

    def is_principal_node_kind(self) -> bool:
        if self.axis == 'attribute':
            return isinstance(self.item, AttributeNode)
        elif self.axis == 'namespace':
            return isinstance(self.item, NamespaceNode)
        else:
            return isinstance(self.item, ElementNode)

    def get_context_item(self, item: ItemArgType,
                         namespaces: Optional[NamespacesType] = None,
                         uri: Optional[str] = None,
                         fragment: Optional[bool] = None) -> ItemType:
        """
        Checks the item and returns an item suitable for XPath processing.
        For XML trees and elements try a match with an existing node in the
        context. If it fails then builds a new node using also the provided
        optional arguments.
        """
        if isinstance(item, (XPathNode, AnyAtomicType)):
            return item
        elif is_etree_document(item):
            if self.root is not None and item is self.root.value:
                return self.root

            if self.documents:
                for doc in self.documents.values():
                    if doc is not None and item is doc.value:
                        return doc

        elif is_etree_element(item):
            try:
                return self.root.elements[item]  # type: ignore[index,union-attr]
            except (TypeError, KeyError, AttributeError):
                pass

            if self.documents:
                for doc in self.documents.values():
                    if doc is not None and doc.elements is not None and item in doc.elements:
                        return doc.elements[item]  # type: ignore[index]

            if callable(item.tag):  # type: ignore[union-attr]
                if item.tag.__name__ == 'Comment':  # type: ignore[union-attr]
                    return CommentNode(cast(ElementProtocol, item))
                else:
                    return ProcessingInstructionNode(cast(ElementProtocol, item))
        elif not isinstance(item, Token) or not callable(item):
            msg = f"Unexpected type {type(item)} for context item"
            raise ElementPathTypeError(msg)
        else:
            return item

        return get_node_tree(
            root=cast(Union[ElementProtocol, DocumentProtocol], item),
            namespaces=namespaces,
            uri=uri,
            fragment=fragment
        )

    def get_value(self, item: FunctionArgType, *args: Any, **kwargs: Any) -> ValueType:
        if item is None:
            return []
        elif not isinstance(item, (list, tuple)):
            return self.get_context_item(item, *args, **kwargs)
        return [self.get_context_item(x, *args, **kwargs) for x in item]

    def get_collection(self, items: CollectionArgType) -> List[XPathNode]:
        if items is None:
            return []
        elif isinstance(items, (list, tuple)):
            return [x for x in map(self.get_context_item, items) if isinstance(x, XPathNode)]
        else:
            item = self.get_context_item(items)
            return [item] if isinstance(item, XPathNode) else []

    def inner_focus_select(self, token: Union['XPathToken', 'XPathAxis'], predicate: bool = False) \
            -> Iterator[ItemType]:
        """Apply the token's selector with an inner focus."""
        status = self.item, self.size, self.position, self.axis
        if predicate:
            results: list[ItemType] = []
            for item in token.select(copy(self)):
                # With predicate select nodes that have not single list value
                # must be replaced by value.
                if isinstance(item, (AttributeNode, ElementNode)) and item.is_list:
                    value = item.typed_value
                    if isinstance(value, list):
                        results.extend(value)
                        continue

                results.append(item)
        else:
             results = [x for x in token.select(copy(self))]

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
        if varnames is None:
            varnames = []
        iterators = [x(self) for x in selectors]
        dimension = len(iterators)
        prod = [None] * dimension
        max_index = dimension - 1

        k = 0
        while True:
            for value in iterators[k]:
                try:
                    self.variables[varnames[k]] = value
                except IndexError:
                    pass

                prod[k] = value
                if k == max_index:
                    yield tuple(prod)
                else:
                    k += 1
                break
            else:
                if not k:
                    return
                iterators[k] = selectors[k](self)
                k -= 1

    ##
    # Context item iterators for axis

    def iter_self(self) -> Iterator[ItemType]:
        """Iterator for 'self' axis and '.' shortcut."""
        if self.item is not None:
            status = self.axis
            self.axis = 'self'
            yield self.item
            self.axis = status

    def iter_attributes(self) -> Iterator[AttributeNode]:
        """Iterator for 'attribute' axis and '@' shortcut."""
        status: Any

        if isinstance(self.item, AttributeNode):
            status = self.axis
            self.axis = 'attribute'
            yield self.item
            self.axis = status
            return
        elif isinstance(self.item, ElementNode):
            status = self.item, self.axis
            self.axis = 'attribute'

            for self.item in self.item.attributes:
                yield self.item

            self.item, self.axis = status

    def iter_children_or_self(self) -> Iterator[ItemType]:
        """Iterator for 'child' forward axis and '/' step."""
        if self.item is not None:
            if self.axis is not None:
                yield self.item
            elif isinstance(self.item, (ElementNode, DocumentNode)):
                _status = self.item, self.axis
                self.axis = 'child'

                if self.item is self.document and self.root is not self.document:
                    if self.root is not None:
                        yield self.root
                else:
                    for self.item in self.item:
                        yield self.item

                self.item, self.axis = _status

    def iter_matching_nodes(self, name: str, default_namespace: Optional[str] = None) \
            -> Iterator[Union[AttributeNode, ElementNode]]:
        """
        Iterator for matching elements or attributes. For default uses 'child'
        forward axis if no axis is active, otherwise tests the current item.
        """
        if self.axis is not None:
            if isinstance(self.item, (AttributeNode, ElementNode)):
                if self.item.match_name(name, default_namespace):
                    yield self.item
        elif isinstance(self.item, (ElementNode, DocumentNode)):
            _status = self.item, self.axis
            self.axis = 'child'

            if self.item is self.document and isinstance(self.root, ElementNode):
                if self.root.match_name(name, default_namespace):
                    yield self.root
            else:
                for self.item in self.item:
                    if self.item.match_name(name, default_namespace):
                        assert isinstance(self.item, ElementNode)
                        yield self.item

            self.item, self.axis = _status

    def iter_parent(self) -> Iterator[Union[ElementNode, DocumentNode]]:
        """Iterator for 'parent' reverse axis and '..' shortcut."""
        if isinstance(self.item, XPathNode):

            # A stop rule for non-rooted fragments (e.g. root is a schema elements)
            if self.document is not None or self.item is not self.root:
                if self.item.parent is not None:
                    status = self.item, self.axis
                    self.axis = 'parent'

                    self.item = self.item.parent
                    yield self.item

                    self.item, self.axis = status

    def iter_siblings(self, axis: Optional[str] = None) -> Iterator[ChildNodeType]:
        """
        Iterator for 'following-sibling' forward axis and 'preceding-sibling' reverse axis.

        :param axis: the context axis, default is 'following-sibling'.
        """
        if isinstance(self.item, XPathNode):
            if self.document is not None or self.item is not self.root:
                item = self.item

                if item.parent is not None:
                    status = self.item, self.axis
                    self.axis = axis or 'following-sibling'

                    if axis == 'preceding-sibling':
                        for child in item.parent:  # pragma: no cover
                            if child is item:
                                break
                            self.item = child
                            yield child
                    else:
                        follows = False
                        for child in item.parent:
                            if follows:
                                self.item = child
                                yield child
                            elif child is item:
                                follows = True

                    self.item, self.axis = status

    def iter_descendants(self, axis: Optional[str] = None) -> Iterator[Union[None, XPathNode]]:
        """
        Iterator for 'descendant' and 'descendant-or-self' forward axes and '//' shortcut.

        :param axis: the context axis, for default has no explicit axis.
        """
        if isinstance(self.item, (DocumentNode, ElementNode)):
            status = self.item, self.axis
            self.axis = axis

            for self.item in self.item.iter_descendants(with_self=axis != 'descendant'):
                yield self.item

            self.item, self.axis = status

        elif axis != 'descendant' and isinstance(self.item, XPathNode):
            self.axis, axis = axis, self.axis
            yield self.item
            self.axis = axis

    def iter_ancestors(self, axis: Optional[str] = None) -> Iterator[XPathNode]:
        """
        Iterator for 'ancestor' and 'ancestor-or-self' reverse axes.

        :param axis: the context axis, default is 'ancestor'.
        """
        if isinstance(self.item, XPathNode):
            status = self.item, self.axis
            self.axis = axis or 'ancestor'

            ancestors: List[XPathNode] = []
            if axis == 'ancestor-or-self':
                ancestors.append(self.item)

            if self.document is not None or self.item is not self.root:
                parent = self.item.parent
                while parent is not None:
                    ancestors.append(parent)
                    if parent is self.root and self.document is None:
                        break
                    parent = parent.parent

            for self.item in reversed(ancestors):
                yield self.item

            self.item, self.axis = status

    def iter_preceding(self) -> Iterator[Union[DocumentNode, ChildNodeType]]:
        """Iterator for 'preceding' reverse axis."""
        ancestors: Set[Union[ElementNode, DocumentNode]]
        item: XPathNode

        if isinstance(self.item, XPathNode):
            if self.document is not None or self.item is not self.root:
                item = self.item

                if (root := item.parent) is not None:
                    status = self.item, self.axis
                    self.axis = 'preceding'
                    ancestors = {root}

                    while root.parent is not None:
                        if root is self.root and self.document is None:
                            break
                        root = root.parent
                        ancestors.add(root)

                    for self.item in root.iter_descendants():
                        if self.item is item:
                            break
                        if self.item not in ancestors:
                            yield self.item

                    self.item, self.axis = status

    def iter_followings(self) -> Iterator[ChildNodeType]:
        """Iterator for 'following' forward axis."""
        if isinstance(self.item, ElementNode):
            status = self.item, self.axis
            self.axis = 'following'

            descendants = set(self.item.iter_descendants())
            position = self.item.position

            root = self.item
            while isinstance(root.parent, ElementNode) and root is not self.root:
                root = root.parent

            for item in root.iter_descendants(with_self=False):
                if position < item.position and item not in descendants:
                    self.item = item
                    yield cast(ChildNodeType, self.item)

            self.item, self.axis = status


class XPathSchemaContext(XPathContext):
    """
    The XPath dynamic context base class for schema bounded parsers. Use this class
    as dynamic context for schema instances in order to perform a schema-based type
    checking during the static analysis phase. Don't use this as dynamic context on
    XML instances.
    """
    root: ElementNode
