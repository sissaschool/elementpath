# -*- coding: utf-8 -*-
#
# Copyright (c), 2018, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from .exceptions import ElementPathTypeError, ElementPathValueError
from .xpath_helpers import AttributeNode, is_etree_element, is_element_node, is_document_node, is_attribute_node


class XPathContext(object):
    """
    The XPath dynamic context. The static context is provided by the parser.

    :param root: The root of the XML document, must be a ElementTree's Element.
    :param item: The context item. A `None` value means that the context is positioned on \
    the document node.
    :param position: The current position of the node within the input sequence.
    :param size: The number of items in the input sequence.
    :param axis: The active axis. Used to choose when apply the default axis ('child' axis).
    :param variables: Dictionary of context variables that maps a QName to a value.
    """
    def __init__(self, root, item=None, position=0, size=1, axis=None, variables=None):
        if not is_element_node(root) and not is_document_node(root):
            raise ElementPathTypeError("argument 'root' must be an Element: %r" % root)
        self.root = root
        if item is not None:
            self.item = item
        elif is_element_node(root):
            self.item = root
        else:
            self.item = None

        self.position = position
        self.size = size
        self.axis = axis
        self.variables = {} if variables is None else dict(variables)
        self._parent_map = None

    def __repr__(self):
        return '%s(root=%r, item=%r, position=%r, size=%r, axis=%r)' % (
            self.__class__.__name__, self.root, self.item, self.position, self.size, self.axis
        )

    def copy(self, clear_axis=True):
        obj = XPathContext(
            root=self.root,
            item=self.item,
            position=self.position,
            size=self.size,
            axis=None if clear_axis else self.axis,
            variables=self.variables.copy()
        )
        obj._parent_map = self._parent_map
        return obj

    @property
    def parent_map(self):
        if self._parent_map is None:
            self._parent_map = {child: elem for elem in self.root.iter() for child in elem}
        return self._parent_map

    def is_principal_node_kind(self):
        if self.axis == 'attribute':
            return is_attribute_node(self.item)
        else:
            return is_element_node(self.item)

    # Context item iterators
    def iter_self(self):
        status = self.item, self.size, self.position, self.axis
        self.axis = 'self'
        yield self.item
        self.item, self.size, self.position, self.axis = status

    def iter_attributes(self):
        if not is_element_node(self.item):
            return

        status = self.item, self.size, self.position, self.axis
        self.axis = 'attribute'

        for item in self.item.attrib.items():
            self.item = AttributeNode(*item)
            yield self.item

        self.item, self.size, self.position, self.axis = status

    def iter_children_or_self(self, item=None, child_axis=False):
        status = self.item, self.size, self.position, self.axis
        if not child_axis and self.axis is not None:
            yield self.item
            self.item, self.size, self.position, self.axis = status
            return

        self.axis = 'child'
        if item is not None:
            self.item = item

        if self.item is None:
            self.size, self.position = 1, 0
            self.item = self.root.getroot() if is_document_node(self.root) else self.root
            yield self.item
        elif is_element_node(self.item):
            elem = self.item
            if elem.text is not None:
                self.item = elem.text
                yield self.item
            self.size = len(elem)
            for self.position, self.item in enumerate(elem):
                yield self.item

        self.item, self.size, self.position, self.axis = status

    def iter_parent(self, axis=None):
        status = self.item, self.size, self.position, self.axis
        self.axis = axis
        try:
            self.item = self.parent_map[self.item]
        except KeyError:
            pass
        else:
            yield self.item
        self.item, self.size, self.position, self.axis = status

    def iter_descendants(self, item=None, axis=None):
        def _iter_descendants():
            elem = self.item
            yield self.item
            if elem.text is not None:
                self.item = elem.text
                yield self.item
            if len(elem):
                self.size = len(elem)
                for self.position, self.item in enumerate(elem):
                    for _descendant in _iter_descendants():
                        yield _descendant

        status = self.item, self.size, self.position, self.axis
        self.axis = axis

        if item is not None:
            self.item = item

        if self.item is None:
            self.size, self.position = 1, 0
            yield self.root
            self.item = self.root.getroot() if is_document_node(self.root) else self.root
        elif not is_etree_element(self.item):
            return

        for descendant in _iter_descendants():
            yield descendant

        self.item, self.size, self.position, self.axis = status

    def iter_ancestors(self, item=None, axis=None):
        status = self.item, self.size, self.position, self.axis
        self.axis = axis

        if item is not None:
            self.item = item

        if not is_etree_element(self.item):
            return
        elem = self.item
        parent_map = self.parent_map
        while True:
            try:
                parent = parent_map[self.item]
            except KeyError:
                break
            else:
                if parent is elem:
                    raise ElementPathValueError("not an Element tree, circularity found for %r." % elem)
                self.item = parent
                yield self.item

        self.item, self.size, self.position, self.axis = status

    def iter(self, axis=None):
        def _iter():
            elem = self.item
            yield self.item
            if elem.text is not None:
                self.item = elem.text
                yield self.item

            for _item in sorted(elem.attrib.items()):
                self.item = _item
                yield _item

            if len(elem):
                self.size = len(elem)
                for self.position, self.item in enumerate(elem):
                    for _item in _iter():
                        yield _item

        status = self.item, self.size, self.position, self.axis
        self.axis = axis

        if self.item is None:
            self.size, self.position = 1, 0
            yield self.root
            self.item = self.root.getroot() if is_document_node(self.root) else self.root
        elif not is_etree_element(self.item):
            return

        for item in _iter():
            yield item

        self.item, self.size, self.position, self.axis = status
