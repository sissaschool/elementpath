#
# Copyright (c), 2018-2022, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from typing import cast, Any, List, Optional, Union

from elementpath._typing import Iterator
from elementpath.aliases import NamespacesType
from elementpath.exceptions import ElementPathTypeError
from elementpath.protocols import ElementProtocol, LxmlElementProtocol, \
    DocumentProtocol, LxmlDocumentProtocol, XsdElementProtocol
from elementpath.etree import is_etree_document, is_etree_element
from elementpath.xpath_nodes import SchemaElemType, ChildNodeType, \
    ElementMapType, TextNode, CommentNode, ProcessingInstructionNode, \
    ElementNode, SchemaElementNode, DocumentNode

__all__ = ['RootArgType', 'get_node_tree', 'build_node_tree',
           'build_lxml_node_tree', 'build_schema_node_tree']

RootArgType = Union[DocumentProtocol, ElementProtocol, SchemaElemType,
                    'DocumentNode', 'ElementNode']

ElementTreeRootType = Union[DocumentProtocol, ElementProtocol]
LxmlRootType = Union[LxmlDocumentProtocol, LxmlElementProtocol]


def is_schema(obj: Any) -> bool:
    return hasattr(obj, 'xsd_version') and hasattr(obj, 'maps') and not hasattr(obj, 'parent')


def get_node_tree(root: RootArgType,
                  namespaces: Optional[NamespacesType] = None,
                  uri: Optional[str] = None,
                  fragment: Optional[bool] = False) -> Union[DocumentNode, ElementNode]:
    """
    Returns a tree of XPath nodes that wrap the provided root tree.

    :param root: an Element or an ElementTree or a schema or a schema element.
    :param namespaces: an optional mapping from prefixes to namespace URIs, \
    Ignored if root is a lxml etree or a schema structure.
    :param uri: an optional URI associated with the root element or the document.
    :param fragment: if `True` a root element is considered a fragment, if `False` \
    a root element is considered the root of an XML document. If the root is a \
    document node or an ElementTree instance, and fragment is `True` then use the \
    root element and returns an element node. If `None` is provided, the root node \
    kind is preserved.
    """
    if isinstance(root, (DocumentNode, ElementNode)):
        if uri is not None and root.uri is None:
            root.uri = uri

        if fragment and isinstance(root, DocumentNode):
            root_node = root.getroot()
            if root_node.uri is None:
                root_node.uri = root.uri
            return root_node

        return root

    # If a fragment is requested remove the ElementTree instance
    if is_etree_document(root):
        _root = cast(DocumentProtocol, root).getroot() if fragment else root
    elif is_etree_element(root) and not callable(cast(ElementProtocol, root).tag):
        _root = root
    else:
        msg = "invalid root {!r}, an Element or an ElementTree or a schema node required"
        raise ElementPathTypeError(msg.format(root))

    if hasattr(_root, 'xpath'):
        # a lxml element tree data
        return build_lxml_node_tree(
            cast(LxmlRootType, _root), uri, fragment
        )
    elif hasattr(_root, 'xsd_version') and hasattr(_root, 'maps'):
        # a schema or a schema node
        return build_schema_node_tree(
            cast(SchemaElemType, root), uri
        )
    else:
        return build_node_tree(
            cast(ElementTreeRootType, root), namespaces, uri
        )


def build_node_tree(root: ElementTreeRootType,
                    namespaces: Optional[NamespacesType] = None,
                    uri: Optional[str] = None) -> Union[DocumentNode, ElementNode]:
    """
    Returns a tree of XPath nodes that wrap the provided root tree.

    :param root: an Element or an ElementTree.
    :param namespaces: an optional mapping from prefixes to namespace URIs.
    :param uri: an optional URI associated with the document or the root element.
    """
    elem: ElementProtocol
    parent: Any
    elements: Any
    child: ChildNodeType
    children: Iterator[Any]

    position = 1
    if namespaces:
        elem_pos_offset = len(namespaces) + int('xml' not in namespaces) + 1
    else:
        elem_pos_offset = 2

    if hasattr(root, 'parse'):
        document = cast(DocumentProtocol, root)
        document_node = DocumentNode(document, uri, position)
        position += 1

        root_elem = document.getroot()
        if root_elem is None:
            return document_node

        elem = root_elem
        root_node = ElementNode(elem, document_node, position, namespaces)
        elements = document_node.elements
        document_node.children.append(root_node)
    else:
        document_node = None
        elem = root
        root_node = ElementNode(elem, None, position, namespaces)
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
                child = ElementNode(elem, parent, position, namespaces)
                position += elem_pos_offset + len(elem.attrib)

                if elem.text is not None:
                    child.children.append(TextNode(elem.text, child, position))
                    position += 1

            elif elem.tag.__name__ == 'Comment':  # type: ignore[attr-defined]
                child = CommentNode(elem, parent, position)
                position += 1
            else:
                child = ProcessingInstructionNode(elem, parent, position)
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
                return root_node if document_node is None else document_node
            else:
                if (tail := parent.children[-1].elem.tail) is not None:
                    parent.children.append(TextNode(tail, parent, position))
                    position += 1


def build_lxml_node_tree(root: LxmlRootType,
                         uri: Optional[str] = None,
                         fragment: Optional[bool] = False) -> Union[DocumentNode, ElementNode]:
    """
    Returns a tree of XPath nodes that wrap the provided lxml root tree.

    :param root: a lxml Element or a lxml ElementTree.
    :param uri: an optional URI associated with the document or the root element.
    :param fragment: if `True` a root element is considered a fragment, if `False` \
    a root element is considered the root of an XML document. If `None` is provided, \
    the root node kind is preserved.
    """
    root_node: Union[DocumentNode, ElementNode]
    parent: Any
    elements: Any
    child: ChildNodeType
    children: Iterator[Any]

    position = 1

    if fragment:
        # Explicitly requested a fragment: don't create a document node.
        document = None
    elif hasattr(root, 'parse'):
        # A document (ElementTree instance)
        document = cast(LxmlDocumentProtocol, root)
    elif root.getparent() is None and (
            any(True for _sibling in root.itersiblings(preceding=True)) or
            any(True for _sibling in root.itersiblings())):
        # A root element with siblings, create a document for them.
        document = root.getroottree()
    else:
        # Explicitly provided a non-root element: do not parse root's siblings.
        document = None

    if document is not None:
        document_node = DocumentNode(document, uri, position)
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
                child = ProcessingInstructionNode(elem, document_node, position)

            elements[elem] = child
            document_node.children.append(child)
            position += 1

        root_node = ElementNode(root_elem, document_node, position, root_elem.nsmap)
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
        root_node = ElementNode(root_elem, None, position, root_elem.nsmap)
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
                child = ElementNode(elem, parent, position, elem.nsmap)
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
                child = ProcessingInstructionNode(elem, parent, position)
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
                        child = ProcessingInstructionNode(elem, document_node, position)

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

    namespaces: Optional[NamespacesType] = getattr(root, 'namespaces', None)
    if namespaces:
        elem_pos_offset = len(namespaces) + int('xml' not in namespaces) + 1
    else:
        elem_pos_offset = 2

    root_node = SchemaElementNode(root, None, position, namespaces)
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
            child.xsd_type = elem.type
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
