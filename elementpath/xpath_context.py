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
    Optional, Sequence, Union, Callable, Tuple

from .exceptions import ElementPathTypeError, ElementPathValueError
from .datatypes import AnyAtomicType, Timezone
from .protocols import XsdElementProtocol, XMLSchemaProtocol
from .etree import ElementType, DocumentType, is_etree_element, is_etree_document, etree_iter_root
from .xpath_nodes import DocumentNode, ElementNode, CommentNode, ProcessingInstructionNode, \
    AttributeNode, NamespaceNode, TextNode, XPathNode, XPathNodeType, is_schema

if TYPE_CHECKING:
    from .xpath_token import XPathToken, XPathAxis


ContextRootType = Union[ElementType, DocumentType]
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
    _etree: Optional[ModuleType] = None
    root: ContextRootType
    item: Optional[ContextItemType]
    total_nodes: int = 0  # Number of nodes associated to the context

    documents: Optional[Dict[str, DocumentNode]] = None
    collections = None
    default_collection: Optional[List[XPathNode]] = None

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
                 documents: Optional[Dict[str, DocumentType]] = None,
                 collections: Optional[Dict[str, ElementType]] = None,
                 default_collection: Optional[str] = None,
                 text_resources: Optional[Dict[str, str]] = None,
                 resource_collections: Optional[Dict[str, List[str]]] = None,
                 default_resource_collection: Optional[str] = None,
                 allow_environment: bool = False,
                 default_language: Optional[str] = None,
                 default_calendar: Optional[str] = None,
                 default_place: Optional[str] = None) -> None:

        self.namespaces = dict(namespaces) if namespaces else {}

        assert not isinstance(root, XPathNode)
        if is_etree_document(root) or is_etree_element(root):
            self.root = self.build_tree(root)
        else:
            msg = "invalid root {!r}, an Element or an ElementTree or a schema instance required"
            raise ElementPathTypeError(msg.format(root))

        assert not isinstance(item, XPathNode)
        if item is None:
            self.item = self.root if isinstance(self.root, ElementNode) else None
        else:
            self.item = self._get_effective_value(item)

        self.position = position
        self.size = size
        self.axis = axis

        if variables is None:
            self.variables = {}
        else:
            self.variables = {k: self._get_effective_value(v) for k, v in variables.items()}

        if timezone is None or isinstance(timezone, Timezone):
            self.timezone = timezone
        else:
            self.timezone = Timezone.fromstring(timezone)
        self.current_dt = current_dt or datetime.datetime.now(tz=self.timezone)

        if documents is not None:
            self.documents = {k: self.build_tree(v) if v is not None else v
                              for k, v in documents.items()}

        if collections is not None:
            self.collections = {k: self._get_effective_value(v) if v is not None else v
                                for k, v in collections.items()}

        if default_collection is not None:
            self.default_collection = self._get_effective_value(default_collection)

        self.text_resources = text_resources if text_resources is not None else {}
        self.resource_collections = resource_collections
        self.default_resource_collection = default_resource_collection
        self.allow_environment = allow_environment
        self.default_language = default_language
        self.default_calendar = default_calendar
        self.default_place = default_place

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(root={self.root.value})'

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
    def etree(self) -> ModuleType:
        if self._etree is None:
            etree_module_name = self.root.value.__class__.__module__
            self._etree: ModuleType = importlib.import_module(etree_module_name)
        return self._etree

    def get_root(self, node: Any) -> Union[None, ElementType, DocumentType]:
        if any(node == x for x in self.iter()):
            return self.root

        if self.documents is not None:
            try:
                for uri, doc in self.documents.items():
                    doc_context = XPathContext(root=doc.value)
                    if any(node == x for x in doc_context.iter()):
                        return doc
            except AttributeError:
                pass

        return None

    def get_path(self, item: Any) -> str:
        """Cached path resolver for elements and attributes. Returns absolute paths."""
        path = []
        if isinstance(item, AttributeNode):
            path.append(f'@{item.name}')
            item = item.parent

        if item is None:
            return '' if not path else path[0]

        while True:
            try:
                path.append(item.elem.tag)
            except AttributeError:
                pass  # is a document node

            item = item.parent
            if item is None:
                return '/{}'.format('/'.join(reversed(path)))

    def is_principal_node_kind(self) -> bool:
        if self.axis == 'attribute':
            return isinstance(self.item, AttributeNode)
        elif self.axis == 'namespace':
            return isinstance(self.item, NamespaceNode)
        else:
            return isinstance(self.item, ElementNode)

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
            if not isinstance(self.item, AttributeNode):
                return False
            item_name = self.item.name
        elif isinstance(self.item, ElementNode):
            item_name = self.item.elem.tag
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

    def _get_effective_value(self, value):
        if isinstance(value, XPathNode):
            return value
        elif isinstance(value, (list, tuple)):
            return [self._get_effective_value(x) for x in value]
        elif is_etree_document(value):
            if value is self.root.value:
                return self.root
        elif is_etree_element(value):
            for node in self.root.iter():
                if value is node.value:
                    return node
        else:
            return value

        return self.build_tree(value)

    def build_tree(self, root: Union[DocumentType, ElementType, XMLSchemaProtocol]) \
            -> Union[DocumentNode, ElementNode]:

        if hasattr(root, 'getroot'):
            document = cast(DocumentType, root)
            root_node = parent = DocumentNode(self, document)

            _root = document.getroot()
            for e in etree_iter_root(_root):
                if not callable(e.tag):
                    child = ElementNode(self, e, parent)
                    parent.children.append(child)
                elif e.tag.__name__ == 'Comment':
                    parent.children.append(CommentNode(self, e, parent))
                else:
                    parent.children.append(ProcessingInstructionNode(self, e, parent))

            children: Iterator[Any] = iter(_root)
            parent = child

        elif is_schema(root):
            return self._get_schema_tree(root)
        elif not callable(root.tag):
            children: Iterator[Any] = iter(root)
            root_node = parent = ElementNode(self, root)
        elif root.tag.__name__ == 'Comment':
            return CommentNode(self, root)
        else:
            return ProcessingInstructionNode(self, root)

        iterators: List[Any] = []
        ancestors: List[Any] = []

        while True:
            try:
                elem = next(children)
            except StopIteration:
                try:
                    children, parent = iterators.pop(), ancestors.pop()
                except IndexError:
                    return root_node
            else:
                if not callable(elem.tag):
                    child = ElementNode(self, elem, parent)
                elif elem.tag.__name__ == 'Comment':
                    child = CommentNode(self, elem, parent)
                else:
                    child = ProcessingInstructionNode(self, elem, parent)

                parent.children.append(child)
                if elem.tail is not None:
                    parent.children.append(TextNode(self, elem.tail, parent))

                if len(elem):
                    ancestors.append(parent)
                    parent = child
                    iterators.append(children)
                    children = iter(elem)

    def _get_schema_tree(self, root: XMLSchemaProtocol) -> ElementNode:
        children: Iterator[Any] = iter(root)
        root_node = parent = ElementNode(self, root)

        elements = {root}
        iterators: List[Any] = []
        ancestors: List[Any] = []

        while True:
            try:
                elem = next(children)
            except StopIteration:
                try:
                    children, parent = iterators.pop(), ancestors.pop()
                except IndexError:
                    return root_node
            else:
                if elem.parent is not None and elem in elements:
                    continue

                elements.add(elem)
                child = ElementNode(self, elem, parent, xsd_type=elem.type)
                parent.children.append(child)

                if elem.ref is None:
                    ancestors.append(parent)
                    parent = child
                    iterators.append(children)
                    children = iter(elem)
                elif elem.ref not in elements:
                    elements.add(elem.ref)
                    ancestors.append(parent)
                    parent = child
                    iterators.append(children)
                    children = iter(elem.ref)

    def iter(self, namespaces: Optional[Dict[str, str]] = None) \
            -> Iterator[Union[ElementType, DocumentType, TextNode, NamespaceNode, AttributeNode]]:
        """
        Iterates context nodes in document order, including namespace and attribute nodes.

        :param namespaces: a fallback mapping for generating namespaces nodes, \
        used when element nodes do not have a property for in-scope namespaces.
        """
        yield from self.root.iter()

    def inner_focus_select(self, token: Union['XPathToken', 'XPathAxis']) -> Iterator[Any]:
        """Apply the token's selector with an inner focus."""
        status = self.item, self.size, self.position, self.axis
        c1 = self.copy(clear_axis=False)
        results = [x for x in token.select(c1)]
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

    def iter_children_or_self(self) -> Iterator[Any]:
        """Iterator for 'child' forward axis and '/' step."""
        if self.axis is not None:
            yield self.item
        elif isinstance(self.item, (ElementNode, DocumentNode)):
            status = self.item, self.axis
            self.axis = 'child'

            for self.item in self.item.children:
                yield self.item

            self.item, self.axis = status

        elif self.item is None:
            status = self.item, self.axis
            self.axis = 'child'

            if isinstance(self.root, DocumentNode):
                for self.item in self.root.children:
                    yield self.item
            else:
                for self.item in etree_iter_root(self.root):
                    yield self.item

            self.item, self.axis = status

    def iter_parent(self) -> Iterator[ElementType]:
        """Iterator for 'parent' reverse axis and '..' shortcut."""
        if not isinstance(self.item, XPathNode):
            return  # not applicable

        parent = self.item.parent
        if parent is not None:
            status = self.item, self.axis
            self.axis = 'parent'

            self.item = parent
            yield cast(ElementType, self.item)

            self.item, self.axis = status

    def iter_siblings(self, axis: Optional[str] = None) \
            -> Iterator[Union[ElementType, TextNode]]:
        """
        Iterator for 'following-sibling' forward axis and 'preceding-sibling' reverse axis.

        :param axis: the context axis, default is 'following-sibling'.
        """
        if not isinstance(self.item, XPathNode):
            return

        parent = self.item.parent
        if parent is None:
            return

        item = self.item
        status = self.item, self.axis
        self.axis = axis or 'following-sibling'

        if axis == 'preceding-sibling':
            for child in parent.children:  # pragma: no cover
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

        if isinstance(self.item, (ElementNode, DocumentNode)):
            descendants = self.item.iter_descendants(with_self)
        elif self.item is None:
            if isinstance(self.root, DocumentNode):
                descendants = self.root.iter_descendants(with_self)
            elif with_self:
                # Yields None in order to emulate position on document
                # FIXME replacing the self.root with ElementTree(self.root)?
                descendants = chain((None,), self.root.iter_descendants())
            else:
                descendants = self.root.iter_descendants()
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
        if not isinstance(self.item, XPathNode):
            return  # item is not an XPath node or document position without a document root

        status = self.item, self.axis
        self.axis = axis or 'ancestor'

        ancestors: List[Union[ElementType, DocumentType, XPathNode]] = []
        if axis == 'ancestor-or-self':
            ancestors.append(self.item)

        parent = self.item.parent
        while parent is not None:
            ancestors.append(parent)
            parent = parent.parent

        for self.item in reversed(ancestors):
            yield self.item

        self.item, self.axis = status

    def iter_preceding(self) -> Iterator[ElementType]:
        """Iterator for 'preceding' reverse axis."""
        item: Union[ElementType, XPathNode]
        parent: Union[None, ElementType, DocumentType]

        if not isinstance(self.item, XPathNode):
            return

        parent = self.item.parent
        if parent is None:
            return

        status = self.item, self.axis
        self.axis = 'preceding'

        ancestors = set()
        while parent is not None:
            ancestors.add(parent)
            parent = parent.parent

        item = self.item
        for self.item in self.root.iter(with_self=True):
            if self.item is item:
                break
            if isinstance(self.item, (AttributeNode, NamespaceNode)):
                continue
            if self.item not in ancestors:
                yield self.item

        self.item, self.axis = status

    def iter_followings(self) -> Iterator[XPathNodeType]:
        """Iterator for 'following' forward axis."""
        if self.item is None or self.item is self.root:
            return
        elif isinstance(self.item, ElementNode):
            status = self.item, self.axis
            self.axis = 'following'
            item = self.item

            descendants = set(item.iter_descendants())
            for self.item in self.root.iter_descendants():
                if item.position < self.item.position and self.item not in descendants:
                    yield self.item

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
