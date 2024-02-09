#
# Copyright (c), 2018-2022, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from typing import cast, Any, Iterator, List, Optional, Union

from .namespaces import NamespacesType
from .exceptions import ElementPathTypeError
from .protocols import ElementProtocol, LxmlElementProtocol, \
    DocumentProtocol, LxmlDocumentProtocol, XsdElementProtocol
from .etree import is_etree_document, is_etree_element
from .xpath_nodes import SchemaElemType, ChildNodeType, ElementMapType, \
    TextNode, CommentNode, ProcessingInstructionNode, \
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
                  fragment: bool = False) -> Union[DocumentNode, ElementNode]:
    """
    Returns a tree of XPath nodes that wrap the provided root tree.

    :param root: an Element or an ElementTree or a schema or a schema element.
    :param namespaces: an optional mapping from prefixes to namespace URIs, \
    Ignored if root is a lxml etree or a schema structure.
    :param uri: an optional URI associated with the root element or the document.
    :param fragment: if `True` a root element is considered a fragment, otherwise \
    a root element is considered the root of an XML document. If the root is a \
    document node or an ElementTree instance, and fragment is `True` then use the \
    root element and returns an element node.
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
    root_node: Union[DocumentNode, ElementNode]
    parent: Any
    elements: Any
    child: ChildNodeType
    children: Iterator[Any]

    position = 1

    def build_element_node() -> ElementNode:
        nonlocal position

        node = ElementNode(elem, parent, position, namespaces)
        position += 1
        elements[elem] = node

        # Do not generate namespace and attribute nodes, only reserve positions.
        position += len(node.nsmap) + int('xml' not in node.nsmap) + len(elem.attrib)

        if elem.text is not None:
            node.children.append(TextNode(elem.text, node, position))
            position += 1

        return node

    if hasattr(root, 'parse'):
        document = cast(DocumentProtocol, root)
        parent = DocumentNode(document, uri, position)
        root_node = parent
        position += 1
        elements = root_node.elements

        root_elem = document.getroot()
        if root_elem is None:
            return root_node

        elem = root_elem
        child = build_element_node()
        parent.children.append(child)
        parent = child
    else:
        elem = root
        parent = None
        elements = {}
        root_node = parent = build_element_node()
        root_node.elements = elements
        if uri is not None:
            root_node.uri = uri

    children = iter(elem)
    iterators: List[Any] = []
    ancestors: List[Any] = []

    while True:
        for elem in children:
            if not callable(elem.tag):
                child = build_element_node()
            elif elem.tag.__name__ == 'Comment':  # type: ignore[attr-defined]
                child = CommentNode(elem, parent, position)
                position += 1
            else:
                child = ProcessingInstructionNode(elem, parent, position)

            parent.children.append(child)
            if elem.tail is not None:
                parent.children.append(TextNode(elem.tail, parent, position))
                position += 1

            if len(elem):
                ancestors.append(parent)
                parent = child
                iterators.append(children)
                children = iter(elem)
                break
        else:
            try:
                children, parent = iterators.pop(), ancestors.pop()
            except IndexError:
                return root_node


def build_lxml_node_tree(root: LxmlRootType,
                         uri: Optional[str] = None,
                         fragment: bool = False) -> Union[DocumentNode, ElementNode]:
    """
    Returns a tree of XPath nodes that wrap the provided lxml root tree.

    :param root: a lxml Element or a lxml ElementTree.
    :param uri: an optional URI associated with the document or the root element.
    :param fragment: if `True` a root element is considered a fragment, otherwise \
    a root element is considered the root of an XML document.
    """
    root_node: Union[DocumentNode, ElementNode]
    parent: Any
    elements: Any
    child: ChildNodeType
    children: Iterator[Any]

    position = 1

    def build_lxml_element_node() -> ElementNode:
        nonlocal position

        node = ElementNode(elem, parent, position, elem.nsmap)
        position += 1
        elements[elem] = node

        # Do not generate namespace and attribute nodes, only reserve positions.
        position += len(elem.nsmap) + int('xml' not in elem.nsmap) + len(elem.attrib)

        if elem.text is not None:
            node.children.append(TextNode(elem.text, node, position))
            position += 1

        return node

    def build_document_node() -> ElementNode:
        nonlocal position
        nonlocal child

        # Add root siblings (comments and processing instructions)
        for e in reversed([x for x in elem.itersiblings(preceding=True)]):
            if e.tag.__name__ == 'Comment':  # type: ignore[attr-defined]
                parent.children.append(CommentNode(e, parent, position))
            else:
                parent.children.append(ProcessingInstructionNode(e, parent, position))
            position += 1

        node = build_lxml_element_node()
        parent.children.append(node)

        for e in elem.itersiblings():
            if e.tag.__name__ == 'Comment':  # type: ignore[attr-defined]
                parent.children.append(CommentNode(e, parent, position))
            else:
                parent.children.append(ProcessingInstructionNode(e, parent, position))
            position += 1

        return node

    if fragment:
        if hasattr(root, 'parse'):
            root_elem = cast(LxmlDocumentProtocol, root).getroot()
            if root_elem is None:
                msg = "requested a fragment of an empty ElementTree document"
                raise ElementPathTypeError(msg)
            elem = root_elem
        else:
            elem = root

        parent = None
        elements = {}
        root_node = parent = build_lxml_element_node()
        root_node.elements = elements

    elif hasattr(root, 'parse'):
        document = cast(LxmlDocumentProtocol, root)
        root_node = parent = DocumentNode(document, position=position)
        position += 1

        root_elem = document.getroot()
        if root_elem is None:
            return root_node

        elem = root_elem
        elements = root_node.elements
        parent = build_document_node()

    elif root.getparent() is None:
        # Creates a root document node for parsing root's siblings.
        document = root.getroottree()
        root_node = parent = DocumentNode(document, position=0)

        root_elem = document.getroot()
        assert root_elem is not None

        elem = root_elem
        elements = root_node.elements
        parent = build_document_node()

        if len(root_node.children) == 1:
            # Remove the document node if root element has no siblings
            parent.elements = root_node.elements
            parent.parent = None
            root_node = parent
    else:
        elem = root
        parent = None
        elements = {}
        root_node = parent = build_lxml_element_node()
        root_node.elements = elements

    children = iter(elem)
    iterators: List[Any] = []
    ancestors: List[Any] = []

    if uri is not None:
        root_node.uri = uri

    while True:
        for elem in children:
            if not callable(elem.tag):
                child = build_lxml_element_node()
            elif elem.tag.__name__ == 'Comment':  # type: ignore[attr-defined]
                child = CommentNode(elem, parent, position)
                position += 1
            else:
                child = ProcessingInstructionNode(elem, parent, position)

            parent.children.append(child)
            if elem.tail is not None:
                parent.children.append(TextNode(elem.tail, parent, position))
                position += 1

            if len(elem):
                ancestors.append(parent)
                parent = child
                iterators.append(children)
                children = iter(elem)
                break
        else:
            try:
                children, parent = iterators.pop(), ancestors.pop()
            except IndexError:
                return root_node


def build_schema_node_tree(root: SchemaElemType,
                           uri: Optional[str] = None,
                           elements: Optional[ElementMapType] = None,
                           global_elements: Optional[List[ChildNodeType]] = None) \
        -> SchemaElementNode:
    """
    Returns a tree of XPath nodes that wrap the provided XSD schema structure.

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

    def build_schema_element_node() -> SchemaElementNode:
        nonlocal position

        node = SchemaElementNode(elem, parent, position, elem.namespaces)
        position += 1
        _elements[elem] = node

        # Do not generate namespace and attribute nodes, only reserve positions.
        position += len(elem.namespaces) + int('xml' not in elem.namespaces) + len(elem.attrib)

        return node

    children = iter(root)
    elem = root
    parent = None
    root_node = parent = build_schema_element_node()
    root_node.elements = _elements
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
    iterators: List[Any] = []
    ancestors: List[Any] = []

    while True:
        for elem in children:
            child = build_schema_element_node()
            child.xsd_type = elem.type
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
                    ref = cast(XsdElementProtocol, element_node.elem).ref
                    assert ref is not None

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
