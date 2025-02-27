#
# Copyright (c), 2018-2022, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from typing import cast, Any, List, Optional, TYPE_CHECKING, Union

from elementpath._typing import Iterator
from elementpath.aliases import NamespacesType, NsmapType
from elementpath.exceptions import ElementPathTypeError
from elementpath.protocols import LxmlElementProtocol, DocumentProtocol, \
    LxmlDocumentProtocol, XsdElementProtocol, DocumentType, ElementType, \
    SchemaElemType
from elementpath.etree import is_etree_document, is_etree_element, is_etree_element_instance
from elementpath.xpath_nodes import ChildNodeType, ElementMapType, TextNode, \
    ElementNode, SchemaElementNode, DocumentNode, RootNodeType, RootArgType, \
    EtreeElementNode, EtreeDocumentNode, CommentNode, ProcessingInstructionNode

if TYPE_CHECKING:
    from elementpath.schema_proxy import AbstractSchemaProxy

__all__ = ['get_node_tree', 'build_node_tree', 'build_lxml_node_tree', 'build_schema_node_tree']

ElementTreeRootType = Union[DocumentType, ElementType]
LxmlRootType = Union[LxmlDocumentProtocol, LxmlElementProtocol]


def is_schema(obj: Any) -> bool:
    return hasattr(obj, 'xsd_version') and hasattr(obj, 'maps') and not hasattr(obj, 'parent')


def get_node_tree(root: RootArgType,
                  namespaces: Optional[NamespacesType] = None,
                  uri: Optional[str] = None,
                  fragment: Optional[bool] = None) -> RootNodeType:
    """
    Returns a tree of XPath nodes that wrap the provided root tree.

    :param root: an Element or an ElementTree or a schema or a schema element.
    :param namespaces: an optional mapping from prefixes to namespace URIs, \
    Ignored if root is a lxml etree or a schema structure.
    :param uri: an optional URI associated with the root element or the document.
    :param fragment: if `True` is provided the root is considered a fragment. In this \
    case if `root` is an ElementTree instance skips it and use the root Element. If \
    `False` is provided creates a dummy document when the root is an Element instance. \
    For default the root node kind is preserved.
    """
    root_node: RootNodeType

    if isinstance(root, (DocumentNode, ElementNode)):
        if uri is not None and root.uri is None:
            root.uri = uri

        if fragment:
            if isinstance(root, DocumentNode):
                root_node = root.getroot()
                if root_node.uri is None:
                    root_node.uri = root.uri
                return root_node
        elif fragment is False and \
                isinstance(root, ElementNode) and \
                is_etree_element_instance(root.obj):
            return root.get_document_node(replace=False)

        return root

    if not is_etree_document(root) and \
            (not is_etree_element(root) or callable(cast(ElementType, root).tag)):
        msg = "invalid root {!r}, an Element or an ElementTree or a schema node required"
        raise ElementPathTypeError(msg.format(root))
    elif hasattr(root, 'xpath'):
        # a lxml element tree data
        return build_lxml_node_tree(
            cast(LxmlRootType, root), uri, fragment
        )
    elif hasattr(root, 'xsd_version') and hasattr(root, 'maps'):
        # a schema or a schema node
        return build_schema_node_tree(
            cast(SchemaElemType, root), uri
        )
    else:
        return build_node_tree(
            cast(ElementTreeRootType, root), namespaces, uri, fragment
        )


def build_node_tree(root: ElementTreeRootType,
                    namespaces: Optional[NamespacesType] = None,
                    uri: Optional[str] = None,
                    fragment: Optional[bool] = None,
                    schema: Optional['AbstractSchemaProxy'] = None) -> RootNodeType:
    """
    Returns a tree of XPath nodes that wrap the provided root tree.

    :param root: an Element or an ElementTree.
    :param namespaces: an optional mapping from prefixes to namespace URIs.
    :param uri: an optional URI associated with the document or the root element.
    :param fragment: if `True` is provided the root is considered a fragment. In this \
    case if `root` is an ElementTree instance skips it and use the root Element. If \
    `False` is provided creates a dummy document when the root is an Element instance. \
    For default the root node kind is preserved.
    :param schema: an optional schema proxy instance for applying XSD type annotations \
    on element and attribute nodes.
    """
    elem: ElementType
    parent: Any
    elements: Any
    child: ChildNodeType
    children: Iterator[Any]
    document: Optional[DocumentProtocol]

    position = 1

    nsmap: Optional[NsmapType]
    if namespaces:
        nsmap = {k: v for k, v in namespaces.items()}
        elem_pos_offset = len(namespaces) + int('xml' not in namespaces) + 1
    else:
        nsmap = {}
        elem_pos_offset = 2

    if hasattr(root, 'parse'):
        document = cast(DocumentProtocol, root)
        root_elem = document.getroot()
    else:
        document = None
        root_elem = root

    if fragment and root_elem is not None:
        document = None  # Explicitly requested a fragment: don't create a document node

    if document is not None:
        document_node = EtreeDocumentNode(document, uri, position)
        position += 1

        if root_elem is None:
            return document_node

        elem = root_elem
        root_node = EtreeElementNode(elem, document_node, position, nsmap)
        elements = document_node.elements
        document_node.children.append(root_node)
    else:
        assert root_elem is not None
        document_node = None
        elem = root_elem
        root_node = EtreeElementNode(elem, None, position, nsmap)
        root_node.elements = elements = {}
        if uri is not None:
            root_node.uri = uri

    # Complete the root element node build
    elements[elem] = root_node
    position += elem_pos_offset + len(elem.attrib)
    if elem.text is not None:
        root_node.children.append(TextNode(elem.text, root_node, position))
        position += 1

    children = iter(elem)
    iterators: List[Any] = []
    ancestors: List[Any] = []
    parent = root_node

    while True:
        for elem in children:
            if not callable(elem.tag):
                child = EtreeElementNode(elem, parent, position, nsmap)
                position += elem_pos_offset + len(elem.attrib)

                if elem.text is not None:
                    child.children.append(TextNode(elem.text, child, position))
                    position += 1

            elif elem.tag.__name__ == 'Comment':  # type: ignore[attr-defined]
                child = CommentNode(elem, parent, position)
                position += 1
            else:
                child = ProcessingInstructionNode(elem, None, parent, position)
                position += 1

            elements[elem] = child
            parent.children.append(child)

            if len(elem):
                ancestors.append(parent)
                parent = child
                iterators.append(children)
                children = iter(elem)
                break

            if elem.tail is not None:
                parent.children.append(TextNode(elem.tail, parent, position))
                position += 1
        else:
            try:
                children, parent = iterators.pop(), ancestors.pop()
            except IndexError:
                if document_node is not None:
                    return document_node
                elif fragment is False and \
                        isinstance(root_node, ElementNode) and \
                        is_etree_element_instance(root_node.elem):
                    return root_node.get_document_node(replace=False)
                else:
                    return root_node
            else:
                if (tail := parent.children[-1].elem.tail) is not None:
                    parent.children.append(TextNode(tail, parent, position))
                    position += 1


def build_lxml_node_tree(root: LxmlRootType,
                         uri: Optional[str] = None,
                         fragment: Optional[bool] = None) -> RootNodeType:
    """
    Returns a tree of XPath nodes that wrap the provided lxml root tree.

    :param root: a lxml Element or a lxml ElementTree.
    :param uri: an optional URI associated with the document or the root element.
    :param fragment: if `True` is provided the root is considered a fragment. In this \
    case if `root` is an ElementTree instance skips it and use the root Element. If \
    `False` is provided creates a dummy document when the root is an Element instance. \
    For default the root node kind is preserved.
    """
    root_node: RootNodeType
    document: Optional[LxmlDocumentProtocol]
    parent: Any
    elements: Any
    child: ChildNodeType
    children: Iterator[Any]

    position = 1

    if fragment:
        document = None  # Explicitly requested a fragment: don't create a document node
    elif hasattr(root, 'parse'):
        document = cast(LxmlDocumentProtocol, root)
    elif fragment is False or root.getparent() is None and (
            any(True for _sibling in root.itersiblings(preceding=True)) or
            any(True for _sibling in root.itersiblings())):
        # Despite a document is not explicitly requested create a dummy document
        # because the root element has siblings
        document = root.getroottree()
    else:
        document = None

    if document is not None:
        document_node = EtreeDocumentNode(document, uri, position)
        elements = document_node.elements
        position += 1

        root_elem = document.getroot()
        if root_elem is None:
            return document_node

        # Add root siblings (comments and processing instructions)
        for elem in reversed([x for x in root_elem.itersiblings(preceding=True)]):
            if elem.tag.__name__ == 'Comment':  # type: ignore[attr-defined]
                child = CommentNode(elem, document_node, position)
            else:
                child = ProcessingInstructionNode(elem, None, document_node, position)

            elements[elem] = child
            document_node.children.append(child)
            position += 1

        root_node = EtreeElementNode(root_elem, document_node, position, root_elem.nsmap)
        document_node.children.append(root_node)
    else:
        if hasattr(root, 'parse'):
            root_elem = cast(LxmlDocumentProtocol, root).getroot()
        else:
            root_elem = root

        if root_elem is None:
            if fragment:
                msg = "requested a fragment of an empty ElementTree document"
            else:
                msg = "root argument is neither an lxml ElementTree nor a lxml Element"
            raise ElementPathTypeError(msg)

        document_node = None
        root_node = EtreeElementNode(root_elem, None, position, root_elem.nsmap)
        root_node.elements = elements = {}
        if uri is not None:
            root_node.uri = uri

    # Complete the root element node build
    elements[root_elem] = root_node
    if 'xml' in root_elem.nsmap:
        position += len(root_elem.nsmap) + len(root_elem.attrib) + 1
    else:
        position += len(root_elem.nsmap) + len(root_elem.attrib) + 2

    if root_elem.text is not None:
        root_node.children.append(TextNode(root_elem.text, root_node, position))
        position += 1

    children = iter(root_elem)
    iterators: List[Any] = []
    ancestors: List[Any] = []
    parent = root_node

    while True:
        for elem in children:
            if not callable(elem.tag):
                child = EtreeElementNode(elem, parent, position, elem.nsmap)
                if 'xml' in elem.nsmap:
                    position += len(elem.nsmap) + len(elem.attrib) + 1
                else:
                    position += len(elem.nsmap) + len(elem.attrib) + 2

                if elem.text is not None:
                    child.children.append(TextNode(elem.text, child, position))
                    position += 1

            elif elem.tag.__name__ == 'Comment':  # type: ignore[attr-defined]
                child = CommentNode(elem, parent, position)
                position += 1
            else:
                child = ProcessingInstructionNode(elem, None, parent, position)
                position += 1

            elements[elem] = child
            parent.children.append(child)

            if len(elem):
                ancestors.append(parent)
                parent = child
                iterators.append(children)
                children = iter(elem)
                break

            if elem.tail is not None:
                parent.children.append(TextNode(elem.tail, parent, position))
                position += 1
        else:
            try:
                children, parent = iterators.pop(), ancestors.pop()
            except IndexError:
                if document_node is None:
                    return root_node

                # Add root following siblings (comments and processing instructions)
                for elem in root_elem.itersiblings():
                    if elem.tag.__name__ == 'Comment':  # type: ignore[attr-defined]
                        child = CommentNode(elem, document_node, position)
                    else:
                        child = ProcessingInstructionNode(elem, None, document_node, position)

                    elements[elem] = child
                    document_node.children.append(child)
                    position += 1

                return document_node
            else:
                if (tail := parent.children[-1].elem.tail) is not None:
                    parent.children.append(TextNode(tail, parent, position))
                    position += 1


def build_schema_node_tree(root: SchemaElemType,
                           uri: Optional[str] = None,
                           elements: Optional[ElementMapType] = None,
                           global_elements: Optional[List[ChildNodeType]] = None) \
        -> SchemaElementNode:
    """
    Returns a graph of XPath nodes that wrap the provided XSD schema structure.
    The elements dictionary is shared between all nodes to keep all of them,
    globals and local, linked in a single structure.

    :param root: a schema or a schema element.
    :param uri: an optional URI associated with the root element.
    :param elements: a shared map from XSD elements to tree nodes. Provided for \
    linking together parts of the same schema or other schemas.
    :param global_elements: a list for schema global elements, used for linking \
    the elements declared by reference.
    """
    parent: Any
    elem: Any
    child: SchemaElementNode
    children: Iterator[Any]

    position = 1
    _elements = {} if elements is None else elements

    nsmap: Optional[NsmapType] = getattr(root, 'namespaces', None)
    if nsmap:
        elem_pos_offset = len(nsmap) + int('xml' not in nsmap) + 1
    else:
        elem_pos_offset = 2

    root_node = SchemaElementNode(root, None, position, nsmap)
    _elements[root] = root_node
    root_node.elements = _elements
    position += elem_pos_offset + len(root.attrib)
    if uri is not None:
        root_node.uri = uri

    if global_elements is not None:
        global_elements.append(root_node)
    elif is_schema(root):
        global_elements = root_node.children
    else:
        # Track global elements even if the initial root is not a schema to avoid circularity
        global_elements = []

    local_nodes = {root: root_node}  # Irrelevant even if it's the schema
    ref_nodes: List[SchemaElementNode] = []

    children = iter(root)
    iterators: List[Any] = []
    ancestors: List[Any] = []
    parent = root_node

    while True:
        for elem in children:
            child = SchemaElementNode(elem, parent, position, elem.namespaces)
            position += elem_pos_offset + len(elem.attrib)

            _elements[elem] = child
            child.elements = _elements
            parent.children.append(child)

            if elem in local_nodes:
                if elem.ref is None:
                    child.children = local_nodes[elem].children
                else:
                    ref_nodes.append(child)
            else:
                local_nodes[elem] = child
                if elem.ref is None:
                    ancestors.append(parent)
                    parent = child
                    iterators.append(children)
                    children = iter(elem)
                    break
                else:
                    ref_nodes.append(child)
        else:
            try:
                children, parent = iterators.pop(), ancestors.pop()
            except IndexError:
                # connect references to proper nodes
                for element_node in ref_nodes:
                    elem = element_node.elem
                    ref = cast(XsdElementProtocol, elem.ref)

                    other: Any
                    for other in global_elements:
                        if other.elem is ref:
                            element_node.ref = other
                            break
                    else:
                        # Extend node tree with other globals
                        element_node.ref = build_schema_node_tree(
                            ref, elements=_elements, global_elements=global_elements
                        )

                return root_node
