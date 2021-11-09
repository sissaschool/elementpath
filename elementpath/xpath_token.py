#
# Copyright (c), 2018-2021, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""
XPathToken and helper functions for XPath nodes. XPath error messages and node helper functions
are embedded in XPathToken class, in order to raise errors related to token instances.

In XPath there are 7 kinds of nodes:

    element, attribute, text, namespace, processing-instruction, comment, document

Element-like objects are used for representing elements and comments, ElementTree-like objects
for documents.
XPathNode subclasses are used for representing other node types and typed elements/attributes.
"""
import locale
import contextlib
import math
from copy import copy
from decimal import Decimal
from itertools import product
from typing import TYPE_CHECKING, cast, Dict, Optional, List, Tuple, Union, \
    Any, Iterator, SupportsFloat, Type
import urllib.parse

from .exceptions import ElementPathError, ElementPathValueError, ElementPathNameError, \
    ElementPathTypeError, ElementPathSyntaxError, MissingContextError, XPATH_ERROR_CODES
from .helpers import ordinal
from .namespaces import XQT_ERRORS_NAMESPACE, XSD_NAMESPACE, XSD_SCHEMA, \
    XPATH_FUNCTIONS_NAMESPACE, XPATH_MATH_FUNCTIONS_NAMESPACE, \
    XSD_ANY_TYPE, XSD_ANY_SIMPLE_TYPE, XSD_ANY_ATOMIC_TYPE, XSI_NIL
from .xpath_nodes import XPathNode, TypedElement, AttributeNode, TextNode, \
    NamespaceNode, TypedAttribute, is_etree_element, etree_iter_strings, \
    is_comment_node, is_processing_instruction_node, is_element_node, \
    is_document_node, is_xpath_node, is_schema_node
from .datatypes import xsd10_atomic_types, xsd11_atomic_types, AbstractDateTime, \
    AnyURI, UntypedAtomic, Timezone, DateTime10, Date10, DayTimeDuration, Duration, \
    Integer, DoubleProxy10, DoubleProxy, QName, DatetimeValueType, AtomicValueType, \
    AnyAtomicType
from .protocols import ElementProtocol, DocumentProtocol, \
    XsdAttributeProtocol, XsdTypeProtocol, XMLSchemaProtocol
from .schema_proxy import AbstractSchemaProxy
from .tdop import Token, MultiLabel
from .xpath_context import XPathContext, XPathSchemaContext

if TYPE_CHECKING:
    from .xpath1 import XPath1Parser
    from .xpath2 import XPath2Parser
    from .xpath30 import XPath30Parser

    XPathParserType = Union[XPath1Parser, XPath2Parser, XPath30Parser]
else:
    XPathParserType = Any

UNICODE_CODEPOINT_COLLATION = "http://www.w3.org/2005/xpath-functions/collation/codepoint"
XSD_SPECIAL_TYPES = {XSD_ANY_TYPE, XSD_ANY_SIMPLE_TYPE, XSD_ANY_ATOMIC_TYPE}

# Type annotations aliases
NargsType = Optional[Union[int, Tuple[int, Optional[int]]]]
ClassCheckType = Union[Type[Any], Tuple[Type[Any], ...]]
PrincipalNodeType = Union[ElementProtocol, AttributeNode, TypedAttribute, TypedElement]
OperandsType = Tuple[Optional[AtomicValueType], Optional[AtomicValueType]]
SelectResultType = Union[AtomicValueType, ElementProtocol, XsdAttributeProtocol, Tuple[str, str]]

XPathTokenType = Union['XPathToken', 'XPathAxis', 'XPathFunction', 'XPathConstructor']


class XPathToken(Token[XPathTokenType]):
    """Base class for XPath tokens."""
    parser: XPathParserType
    xsd_types: Optional[Dict[str, Union[XsdTypeProtocol, List[XsdTypeProtocol]]]]
    namespace: Optional[str]

    xsd_types = None  # for XPath 2.0+ XML Schema types labeling
    namespace = None  # for namespace binding of names and wildcards

    def evaluate(self, context: Optional[XPathContext] = None) -> Any:
        """
        Evaluate default method for XPath tokens.

        :param context: The XPath dynamic context.
        """
        return [x for x in self.select(context)]

    def select(self, context: Optional[XPathContext] = None) -> Iterator[Any]:
        """
        Select operator that generates XPath results.

        :param context: The XPath dynamic context.
        """
        item = self.evaluate(context)
        if item is not None:
            if isinstance(item, list):
                yield from item
            else:
                if context is not None:
                    context.item = item
                yield item

    def __str__(self) -> str:
        symbol, label = self.symbol, self.label
        if symbol == '$':
            return '$%s variable reference' % (self[0].value if self._items else '')
        elif symbol == ',':
            return 'comma operator' if self.parser.version > '1.0' else 'comma symbol'
        elif label.endswith('function') or label in ('axis', 'sequence type', 'kind test'):
            return '%r %s' % (symbol, label)
        return super(XPathToken, self).__str__()

    @property
    def source(self) -> str:
        symbol, label = self.symbol, self.label
        if label == 'axis':
            return '%s::%s' % (self.symbol, self[0].source)
        elif label.endswith('function') or label in ('sequence type', 'kind test'):
            return '%s(%s)' % (self.symbol, ', '.join(item.source for item in self))
        elif symbol == ':':
            return '%s:%s' % (self[0].source, self[1].source)
        elif symbol == '(':
            return '()' if not self else '(%s)' % self[0].source
        elif symbol == '[':
            return '%s[%s]' % (self[0].source, self[1].source)
        elif symbol == ',':
            return '%s, %s' % (self[0].source, self[1].source)
        elif symbol == '$':
            return '$%s' % self[0].source
        elif symbol == '{':
            return '{%s}%s' % (self[0].value, self[1].value)
        elif symbol == 'if':
            return 'if (%s) then %s else %s' % (self[0].source, self[1].source, self[2].source)
        elif symbol == 'instance':
            return '%s instance of %s' % (self[0].source, ''.join(t.source for t in self[1:]))
        elif symbol == 'treat':
            return '%s treat as %s' % (self[0].source, ''.join(t.source for t in self[1:]))
        elif symbol == 'for':
            return 'for %s return %s' % (
                ', '.join('%s in %s' % (self[k].source, self[k + 1].source)
                          for k in range(0, len(self) - 1, 2)),
                self[-1].source
            )
        return super(XPathToken, self).source

    @property
    def child_axis(self) -> bool:
        """Is `True` if the token apply child axis for default, `False` otherwise."""
        if self.symbol not in {'*', 'node', 'child', 'text', '(name)', ':',
                               'document-node', 'element', 'schema-element'}:
            return False
        elif self.symbol != ':':
            return True
        return not self._items[1].label.endswith('function')

    ###
    # Tokens tree analysis methods
    def iter_leaf_elements(self) -> Iterator[str]:
        """
        Iterates through the leaf elements of the token tree if there are any,
        returning QNames in prefixed format. A leaf element is an element
        positioned at last path step. Does not consider kind tests and wildcards.
        """
        if self.symbol in {'(name)', ':'}:
            yield cast(str, self.value)
        elif self.symbol in ('//', '/'):
            if self._items[-1].symbol in {
                '(name)', '*', ':', '..', '.', '[', 'self', 'child',
                'parent', 'following-sibling', 'preceding-sibling',
                'ancestor', 'ancestor-or-self', 'descendant',
                'descendant-or-self', 'following', 'preceding'
            }:
                yield from self._items[-1].iter_leaf_elements()

        elif self.symbol in ('[',):
            yield from self._items[0].iter_leaf_elements()
        else:
            for tk in self._items:
                yield from tk.iter_leaf_elements()

    ###
    # Dynamic context methods
    def get_argument(self, context: Optional[XPathContext],
                     index: int = 0,
                     required: bool = False,
                     default_to_context: bool = False,
                     default: Optional[AtomicValueType] = None,
                     cls: Optional[Type[Any]] = None,
                     promote: Optional[ClassCheckType] = None) -> Any:
        """
        Get the argument value of a function of constructor token. A zero length sequence is
        converted to a `None` value. If the function has no argument returns the context's
        item if the dynamic context is not `None`.

        :param context: the dynamic context.
        :param index: an index for select the argument to be got, the first for default.
        :param required: if set to `True` missing or empty sequence arguments are not allowed.
        :param default_to_context: if set to `True` then the item of the dynamic context is \
        returned when the argument is missing.
        :param default: the default value returned in case the argument is an empty sequence. \
        If not provided returns `None`.
        :param cls: if a type is provided performs a type checking on item.
        :param promote: a class or a tuple of classes that are promoted to `cls` class.
        """
        item: Union[None, ElementProtocol, DocumentProtocol, XPathNode, AnyAtomicType]

        try:
            selector = self._items[index].select
        except IndexError:
            if default_to_context:
                if context is None:
                    raise self.missing_context() from None
                item = context.item if context.item is not None else context.root
            elif required:
                msg = "missing %s argument" % ordinal(index + 1)
                raise self.error('XPST0017', msg) from None
            else:
                return default
        else:
            item = None
            for k, result in enumerate(selector(copy(context))):
                if k == 0:
                    item = result
                elif self.parser.compatibility_mode:
                    break
                elif isinstance(context, XPathSchemaContext):
                    # Multiple schema nodes are ignored but do not raise. The target
                    # of schema context selection is XSD type association and multiple
                    # nodes coherency is already checked at schema level.
                    break
                else:
                    raise self.wrong_context_type(
                        "a sequence of more than one item is not allowed as argument"
                    )
            else:
                if item is None:
                    if not required:
                        return default
                    ord_arg = ordinal(index + 1)
                    msg = "A not empty sequence required for {} argument"
                    raise self.error('XPTY0004', msg.format(ord_arg))

        # Type promotion checking (see "function conversion rules" in XPath 2.0 language definition)
        if cls is not None and not isinstance(item, cls) and not issubclass(cls, XPathToken):
            if promote and isinstance(item, promote):
                return cls(item)

            if self.parser.compatibility_mode:
                if issubclass(cls, str):
                    return self.string_value(item)
                elif issubclass(cls, float) or issubclass(float, cls):
                    return self.number_value(item)

            if self.parser.version == '1.0':
                code = 'XPTY0004'
            else:
                value = self.data_value(item)
                if isinstance(value, cls):
                    return value
                elif isinstance(value, AnyURI) and issubclass(cls, str):
                    return cls(value)
                elif isinstance(value, UntypedAtomic):
                    try:
                        return cls(value)
                    except (TypeError, ValueError):
                        pass

                code = 'FOTY0012' if value is None else 'XPTY0004'

            message = "the type of the {} argument is {!r} instead of {!r}"
            raise self.error(code, message.format(ordinal(index + 1), type(item), cls))

        return item

    def select_data_values(self, context: Optional[XPathContext] = None) \
            -> Iterator[Optional[AtomicValueType]]:
        """
        Yields data value of selected items.

        :param context: the XPath dynamic context.
        """
        for item in self.select(context):
            yield self.data_value(item)

    def atomization(self, context: Optional[XPathContext] = None) \
            -> Iterator[AtomicValueType]:
        """
        Helper method for value atomization of a sequence.

        Ref: https://www.w3.org/TR/xpath20/#id-atomization

        :param context: the XPath dynamic context.
        """
        for item in self.select(context):
            value = self.data_value(item)
            if value is None:
                msg = "argument node {!r} does not have a typed value"
                raise self.error('FOTY0012', msg.format(item))
            else:
                yield value

    def get_atomized_operand(self, context: Optional[XPathContext] = None) \
            -> Optional[AtomicValueType]:
        """
        Get the atomized value for an XPath operator.

        :param context: the XPath dynamic context.
        :return: the atomized value of a single length sequence or `None` if the sequence is empty.
        """
        selector = iter(self.atomization(context))
        try:
            value = next(selector)
        except StopIteration:
            return None
        else:
            item = getattr(context, 'item', None)

            try:
                next(selector)
            except StopIteration:
                if isinstance(value, UntypedAtomic):
                    value = str(value)

                if not isinstance(context, XPathSchemaContext) and \
                        item is not None and \
                        self.xsd_types and \
                        isinstance(value, str):

                    xsd_type = self.get_xsd_type(item)
                    if xsd_type is None or xsd_type.name in XSD_SPECIAL_TYPES:
                        pass
                    else:
                        try:
                            value = xsd_type.decode(value)
                        except (TypeError, ValueError):
                            msg = "Type {!r} is not appropriate for the context"
                            raise self.wrong_context_type(msg.format(type(value)))

                return value
            else:
                msg = "atomized operand is a sequence of length greater than one"
                raise self.wrong_context_type(msg)

    def iter_comparison_data(self, context: XPathContext) -> Iterator[OperandsType]:
        """
        Generates comparison data couples for the general comparison of sequences.
        Different sequences maybe generated with an XPath 2.0 parser, depending on
        compatibility mode setting.

        Ref: https://www.w3.org/TR/xpath20/#id-general-comparisons

        :param context: the XPath dynamic context.
        """
        if self.parser.compatibility_mode:
            operand1 = [x for x in self._items[0].select(copy(context))]
            operand2 = [x for x in self._items[1].select(copy(context))]

            # Boolean comparison if one of the results is a single boolean value (1.)
            try:
                if isinstance(operand1[0], bool):
                    if len(operand1) == 1:
                        yield operand1[0], self.boolean_value(operand2)
                        return
                if isinstance(operand2[0], bool):
                    if len(operand2) == 1:
                        yield self.boolean_value(operand1), operand2[0]
                        return
            except IndexError:
                return

            # Converts to float for lesser-greater operators (3.)
            if self.symbol in ('<', '<=', '>', '>='):
                yield from product(
                    map(float, map(self.data_value, operand1)),  # type: ignore[arg-type]
                    map(float, map(self.data_value, operand2)),  # type: ignore[arg-type]
                )
                return
            elif self.parser.version == '1.0':
                yield from product(map(self.data_value, operand1), map(self.data_value, operand2))
                return

        for values in product(map(self.data_value, self._items[0].select(copy(context))),
                              map(self.data_value, self._items[1].select(copy(context)))):
            if any(isinstance(x, bool) for x in values):
                if any(isinstance(x, (str, Integer)) for x in values):
                    msg = "cannot compare {!r} and {!r}"
                    raise TypeError(msg.format(type(values[0]), type(values[1])))
            elif any(isinstance(x, Integer) for x in values) and \
                    any(isinstance(x, str) for x in values):
                msg = "cannot compare {!r} and {!r}"
                raise TypeError(msg.format(type(values[0]), type(values[1])))
            yield values

    def select_results(self, context: Optional[XPathContext]) -> Iterator[SelectResultType]:
        """
        Generates formatted XPath results.

        :param context: the XPath dynamic context.
        """
        if context is not None:
            self.parser.check_variables(context.variables)

        for result in self.select(context):
            if not isinstance(result, XPathNode):
                yield result
            elif isinstance(result, (TextNode, AttributeNode)):
                yield result.value
            elif isinstance(result, TypedElement):
                yield result.elem
            elif isinstance(result, TypedAttribute):
                if is_schema_node(result.attribute.value):
                    yield result.attribute.value
                else:
                    yield result.value
            elif isinstance(result, NamespaceNode):  # pragma: no cover
                if self.parser.compatibility_mode:
                    yield result.prefix, result.uri
                else:
                    yield result.uri

    def get_results(self, context: XPathContext) \
            -> Union[List[Any], AtomicValueType]:
        """
        Returns formatted XPath results.

        :param context: the XPath dynamic context.
        :return: a list or a simple datatype when the result is a single simple type \
        generated by a literal or function token.
        """
        results = [x for x in self.select_results(context)]
        if len(results) == 1:
            res = results[0]
            if isinstance(res, (bool, int, float, Decimal)):
                return res
            elif is_etree_element(res) or is_document_node(res) or is_schema_node(res):
                return results
            elif self.label in ('function', 'literal'):
                return cast(AtomicValueType, res)
            else:
                return results
        else:
            return results

    def get_operands(self, context: XPathContext, cls: Optional[Type[Any]] = None) \
            -> OperandsType:
        """
        Returns the operands for a binary operator. Float arguments are converted
        to decimal if the other argument is a `Decimal` instance.

        :param context: the XPath dynamic context.
        :param cls: if a type is provided performs a type checking on item.
        :return: a couple of values representing the operands. If any operand \
        is not available returns a `(None, None)` couple.
        """
        op1 = self.get_argument(context, cls=cls)
        if op1 is None:
            return None, None
        elif is_element_node(op1):
            op1 = self._items[0].data_value(op1)

        op2 = self.get_argument(context, index=1, cls=cls)
        if op2 is None:
            return None, None
        elif is_element_node(op2):
            op2 = self._items[1].data_value(op2)

        if isinstance(op1, AbstractDateTime) and isinstance(op2, AbstractDateTime):
            if context is not None and context.timezone is not None:
                if op1.tzinfo is None:
                    op1.tzinfo = context.timezone
                if op2.tzinfo is None:
                    op2.tzinfo = context.timezone
        else:
            if isinstance(op1, UntypedAtomic):
                op1 = self.cast_to_double(op1.value)
                if isinstance(op2, Decimal):
                    return op1, float(op2)
            if isinstance(op2, UntypedAtomic):
                op2 = self.cast_to_double(op2.value)
                if isinstance(op1, Decimal):
                    return float(op1), op2

        if isinstance(op1, float):
            if isinstance(op2, Duration):
                return Decimal(op1), op2
            if isinstance(op2, Decimal):
                return op1, type(op1)(op2)
        if isinstance(op2, float):
            if isinstance(op1, Duration):
                return op1, Decimal(op2)
            if isinstance(op1, Decimal):
                return type(op2)(op1), op2

        return op1, op2

    def get_absolute_uri(self, uri: str,
                         base_uri: Optional[str] = None,
                         as_string: bool = True) -> Union[str, AnyURI]:
        """
        Obtains an absolute URI from the argument and the static context.

        :param uri: a string representing an URI.
        :param base_uri: an alternative base URI, otherwise the base_uri \
        of the static context is used.
        :param as_string: if `True` then returns the URI as a string, otherwise \
        returns the URI as xs:anyURI instance.
        :returns: the argument if it's an absolute URI. Otherwise returns the URI
        obtained by the join o the base_uri of the static context with the
        argument. Returns the argument if the base_uri is `None'.
        """
        if not base_uri:
            base_uri = self.parser.base_uri

        url_parts: Union[urllib.parse.ParseResult, urllib.parse.SplitResult]
        url_parts = urllib.parse.urlparse(uri)
        if url_parts.scheme or url_parts.netloc \
                or url_parts.path.startswith('/') \
                or base_uri is None:
            return uri if as_string else AnyURI(uri)

        url_parts = urllib.parse.urlsplit(base_uri)
        if url_parts.fragment or not url_parts.scheme and \
                not url_parts.netloc and not url_parts.path.startswith('/'):
            raise self.error('FORG0002', '{!r} is not suitable as base URI'.format(base_uri))

        if as_string:
            return urllib.parse.urljoin(base_uri, uri)
        return AnyURI(urllib.parse.urljoin(base_uri, uri))

    def get_namespace(self, prefix: str) -> str:
        """
        Resolves a prefix to a namespace raising an error (FONS0004) if the
        prefix is not found in the namespace map.
        """
        try:
            return self.parser.namespaces[prefix]
        except KeyError as err:
            msg = 'no namespace found for prefix %r' % str(err)
            raise self.error('FONS0004', msg) from None

    def bind_namespace(self, namespace: str) -> None:
        """
        Bind a token with a namespace. The token has to be a name, a name wildcard,
        a function or a constructor, otherwise a syntax error is raised. Functions
        and constructors must be limited to its namespaces.
        """
        if self.symbol in ('(name)', '*'):
            pass
        elif namespace == self.parser.function_namespace:
            if self.label != 'function':
                msg = "a name, a wildcard or a function expected"
                raise self.wrong_syntax(msg, code='XPST0017')
            elif isinstance(self.label, MultiLabel):
                self.label = 'function'
        elif namespace == XSD_NAMESPACE:
            if self.label != 'constructor function':
                msg = "a name, a wildcard or a constructor function expected"
                raise self.wrong_syntax(msg, code='XPST0017')
            elif isinstance(self.label, MultiLabel):
                self.label = 'constructor function'
        elif namespace == XPATH_MATH_FUNCTIONS_NAMESPACE:
            if self.label != 'math function':
                msg = "a name, a wildcard or a math function expected"
                raise self.wrong_syntax(msg, code='XPST0017')
            elif isinstance(self.label, MultiLabel):
                self.label = 'math function'
        else:
            raise self.wrong_syntax("a name, a wildcard or a function expected")

        self.namespace = namespace

    def adjust_datetime(self, context: XPathContext, cls: Type[DatetimeValueType]) \
            -> Optional[Union[DatetimeValueType, DayTimeDuration]]:
        """
        XSD datetime adjust function helper.

        :param context: the XPath dynamic context.
        :param cls: the XSD datetime subclass to use.
        :return: an empty list if there is only one argument that is the empty sequence \
        or the adjusted XSD datetime instance.
        """
        timezone: Optional[Any]
        item: Optional[DatetimeValueType]
        _item: Union[DatetimeValueType, DayTimeDuration]

        if len(self) == 1:
            item = self.get_argument(context, cls=cls)
            if item is None:
                return None
            timezone = getattr(context, 'timezone', None)
        else:
            item = self.get_argument(context, cls=cls)
            timezone = self.get_argument(context, 1, cls=DayTimeDuration)

            if timezone is not None:
                try:
                    timezone = Timezone.fromduration(timezone)
                except ValueError as err:
                    raise self.error('FODT0003', str(err)) from None
            if item is None:
                return None

        _item = item
        _tzinfo = _item.tzinfo
        try:
            if _tzinfo is not None and timezone is not None:
                if isinstance(_item, DateTime10):
                    _item += timezone.offset
                elif not isinstance(item, Date10):
                    _item += timezone.offset - _tzinfo.offset
                elif timezone.offset < _tzinfo.offset:
                    _item -= timezone.offset - _tzinfo.offset
                    _item -= DayTimeDuration.fromstring('P1D')
        except OverflowError as err:
            raise self.error('FODT0001', str(err)) from None

        if not isinstance(_item, DayTimeDuration):
            _item.tzinfo = timezone
        return _item

    @contextlib.contextmanager
    def use_locale(self, collation: str) -> Iterator[None]:
        """A context manager for use a locale setting for string comparison in a code block."""
        loc = locale.getlocale(locale.LC_COLLATE)
        if collation == UNICODE_CODEPOINT_COLLATION:
            collation = 'en_US.UTF-8'
        elif collation is None:
            raise self.error('XPTY0004', 'collation cannot be an empty sequence')

        try:
            locale.setlocale(locale.LC_COLLATE, collation)
        except locale.Error:
            raise self.error('FOCH0002', 'Unsupported collation %r' % collation) from None
        else:
            yield
        finally:
            locale.setlocale(locale.LC_COLLATE, loc)

    ###
    # XSD types related methods
    def select_xsd_nodes(self, schema_context: XPathSchemaContext, name: str) \
            -> Iterator[Union[None, TypedElement, TypedAttribute, XMLSchemaProtocol]]:
        """
        Selector for XSD nodes (elements, attributes and schemas). If there is
        a match with an attribute or an element the node's type is added to
        matching types of the token. For each matching elements or attributes
        yields tuple nodes containing the node, its type and a compatible value
        for doing static evaluation. For matching schemas yields the original
        instance.

        :param schema_context: an XPathSchemaContext instance.
        :param name: a QName in extended format.
        """
        xsd_node: Any
        for xsd_node in schema_context.iter_children_or_self():
            if xsd_node is None:
                if name == XSD_SCHEMA == schema_context.root.tag:
                    yield None
                continue  # pragma: no cover

            try:
                if isinstance(xsd_node, AttributeNode):
                    if isinstance(xsd_node.value, str):
                        if xsd_node.name != name:
                            continue
                        xsd_node = schema_context.root.maps.attributes.get(name)
                        if xsd_node is None:
                            continue
                    elif xsd_node.value.is_matching(name):
                        if xsd_node.name is None:
                            # node is an XSD attribute wildcard
                            xsd_node = schema_context.root.maps.attributes.get(name)
                            if xsd_node is None:
                                continue
                    else:
                        continue

                    xsd_type = self.add_xsd_type(xsd_node)
                    if xsd_type is not None:
                        value = self.parser.get_atomic_value(xsd_type)
                        yield TypedAttribute(xsd_node, xsd_type, value)

                elif name == XSD_SCHEMA == xsd_node.tag:
                    # The element is a schema
                    yield xsd_node

                elif xsd_node.is_matching(name, self.parser.default_namespace):
                    if xsd_node.name is None:
                        # node is an XSD element wildcard
                        xsd_node = schema_context.root.maps.elements.get(name)
                        if xsd_node is None:
                            continue

                    xsd_type = self.add_xsd_type(xsd_node)
                    if xsd_type is not None:
                        value = self.parser.get_atomic_value(xsd_type)
                        yield TypedElement(xsd_node, xsd_type, value)

            except AttributeError:
                pass

    def add_xsd_type(self, item: Any) -> Optional[XsdTypeProtocol]:
        """
        Adds an XSD type association from an item. The association is
        added using the item's name and type.
        """
        if isinstance(item, AttributeNode):
            item = item.value
        elif isinstance(item, TypedAttribute):
            item = item.attribute.value
        elif isinstance(item, TypedElement):
            item = item.elem

        if not is_schema_node(item):
            return None

        name: str = item.name
        xsd_type: XsdTypeProtocol = item.type

        if self.xsd_types is None:
            self.xsd_types = {name: xsd_type}
        else:
            obj = self.xsd_types.get(name)
            if obj is None:
                self.xsd_types[name] = xsd_type
            elif not isinstance(obj, list):
                if obj is not xsd_type:
                    self.xsd_types[name] = [obj, xsd_type]
            elif xsd_type not in obj:
                obj.append(xsd_type)

        return xsd_type

    def get_xsd_type(self, item: Union[str, PrincipalNodeType]) \
            -> Optional[XsdTypeProtocol]:
        """
        Returns the XSD type associated with an item. Match by item's name
        and XSD validity. Returns `None` if no XSD type is matching.

        :param item: a string or an AttributeNode or an element.
        """
        if not self.xsd_types or isinstance(self.xsd_types, AbstractSchemaProxy):
            return None
        elif isinstance(item, str):
            xsd_type = self.xsd_types.get(item)
        elif isinstance(item, AttributeNode):
            xsd_type = self.xsd_types.get(item.name)
        elif isinstance(item, (TypedAttribute, TypedElement)):
            return cast(XsdTypeProtocol, item.xsd_type)
        else:
            xsd_type = self.xsd_types.get(item.tag)

        x: XsdTypeProtocol
        if not xsd_type:
            return None
        elif not isinstance(xsd_type, list):
            return xsd_type
        elif isinstance(item, AttributeNode):
            for x in xsd_type:
                if x.is_valid(item.value):
                    return x
        elif is_etree_element(item):
            for x in xsd_type:
                if x.is_simple():
                    if x.is_valid(item.text):  # type: ignore[union-attr]
                        return x
                elif x.is_valid(item):
                    return x

        return xsd_type[0]

    def get_typed_node(self, item: PrincipalNodeType) -> PrincipalNodeType:
        """
        Returns a typed node if the item is matching an XSD type.

        Ref:
          https://www.w3.org/TR/xpath20/#id-processing-model
          https://www.w3.org/TR/xpath20/#id-static-analysis
          https://www.w3.org/TR/xquery-semantics/

        :param item: an untyped attribute or element.
        :return: a typed AttributeNode/ElementNode if the argument is matching \
        any associated XSD type.
        """
        if isinstance(item, (TypedAttribute, TypedElement)):
            return item

        xsd_type = self.get_xsd_type(item)
        if not xsd_type:
            return item
        elif xsd_type.name in XSD_SPECIAL_TYPES:
            if isinstance(item, AttributeNode):
                if not isinstance(item.value, str):
                    return TypedAttribute(item, xsd_type, UntypedAtomic(''))
                return TypedAttribute(item, xsd_type, UntypedAtomic(item.value))
            return TypedElement(item, xsd_type, UntypedAtomic(item.text or ''))

        elif isinstance(item, AttributeNode):
            pass
        elif xsd_type.has_mixed_content():
            value = UntypedAtomic(item.text or '')
            return TypedElement(item, xsd_type, value)
        elif xsd_type.is_element_only():
            return TypedElement(item, xsd_type, None)
        elif xsd_type.is_empty():
            return TypedElement(item, xsd_type, None)
        elif item.get(XSI_NIL) and getattr(xsd_type.parent, 'nillable', None):
            return TypedElement(item, xsd_type, None)

        if self.parser.xsd_version == '1.0':
            atomic_types = xsd10_atomic_types
        else:
            atomic_types = xsd11_atomic_types

        try:
            builder: Any = atomic_types[xsd_type.name]
        except KeyError:
            pass
        else:
            if issubclass(builder, (AbstractDateTime, Duration)):
                builder = builder.fromstring
            elif issubclass(builder, QName):
                builder = self.cast_to_qname

            try:
                if isinstance(item, AttributeNode):
                    return TypedAttribute(item, xsd_type, builder(item.value))
                else:
                    return TypedElement(item, xsd_type, builder(item.text))
            except (TypeError, ValueError):
                msg = "Type {!r} does not match sequence type of {!r}"
                raise self.wrong_sequence_type(msg.format(xsd_type, item)) from None

        if self.parser.schema is None:
            builder = UntypedAtomic
        else:
            try:
                primitive_type = self.parser.schema.get_primitive_type(xsd_type)
                builder = atomic_types[primitive_type.name]
            except KeyError:
                builder = UntypedAtomic
            else:
                if isinstance(builder, (AbstractDateTime, Duration)):
                    builder = builder.fromstring
                elif issubclass(builder, QName):
                    builder = self.cast_to_qname

        try:
            if isinstance(item, AttributeNode):
                if xsd_type.is_valid(item.value):
                    return TypedAttribute(item, xsd_type, builder(item.value))
            elif xsd_type.is_valid(item.text):
                return TypedElement(item, xsd_type, builder(item.text))
        except (TypeError, ValueError):
            pass

        msg = "Type {!r} does not match sequence type of {!r}"
        raise self.wrong_sequence_type(msg.format(xsd_type, item)) from None

    def cast_to_qname(self, qname: str) -> QName:
        """Cast a prefixed qname string to a QName object."""
        try:
            if ':' not in qname:
                return QName(self.parser.namespaces.get(''), qname.strip())
            pfx, _ = qname.strip().split(':')
            return QName(self.parser.namespaces[pfx], qname)
        except ValueError:
            msg = 'invalid value {!r} for an xs:QName'.format(qname.strip())
            raise self.error('FORG0001', msg)
        except KeyError as err:
            raise self.error('FONS0004', 'no namespace found for prefix {}'.format(err))

    def cast_to_double(self, value: Union[SupportsFloat, str]) -> float:
        """Cast a value to xs:double."""
        try:
            if self.parser.xsd_version == '1.0':
                return cast(float, DoubleProxy10(value))
            return cast(float, DoubleProxy(value))
        except ValueError as err:
            raise self.error('FORG0001', str(err))  # str or UntypedAtomic

    ###
    # XPath data accessors base functions
    def boolean_value(self, obj: Any) -> bool:
        """
        The effective boolean value, as computed by fn:boolean().
        """
        if isinstance(obj, list):
            if not obj:
                return False
            elif is_xpath_node(obj[0]):
                return True
            elif len(obj) > 1:
                message = "effective boolean value is not defined for a sequence " \
                          "of two or more items not starting with an XPath node."
                raise self.error('FORG0006', message)
            else:
                obj = obj[0]

        if isinstance(obj, (int, str, UntypedAtomic, AnyURI)):  # Include bool
            return bool(obj)
        elif isinstance(obj, (float, Decimal)):
            return False if math.isnan(obj) else bool(obj)
        elif obj is None:
            return False
        else:
            message = "effective boolean value is not defined for {!r}.".format(type(obj))
            raise self.error('FORG0006', message)

    def data_value(self, obj: Any) -> Optional[AtomicValueType]:
        """
        The typed value, as computed by fn:data() on each item.
        Returns an instance of UntypedAtomic for untyped data.

        https://www.w3.org/TR/xpath20/#dt-typed-value
        """
        if obj is None:
            return None
        elif isinstance(obj, XPathNode):
            if isinstance(obj, TextNode):
                return UntypedAtomic(obj.value)
            elif isinstance(obj, AttributeNode) and isinstance(obj.value, str):
                return UntypedAtomic(obj.value)
            return cast(Optional[AtomicValueType], obj.value)  # a typed node or a NamespaceNode

        elif is_schema_node(obj):
            return self.parser.get_atomic_value(obj.type)

        elif hasattr(obj, 'tag'):
            if is_comment_node(obj) or is_processing_instruction_node(obj):
                return cast(str, obj.text)
            elif hasattr(obj, 'attrib') and hasattr(obj, 'text'):
                return UntypedAtomic(''.join(etree_iter_strings(obj)))
            else:
                return None
        elif is_document_node(obj):
            value = ''.join(etree_iter_strings(obj.getroot()))
            return UntypedAtomic(value)
        else:
            return cast(AtomicValueType, obj)

    def string_value(self, obj: Any) -> str:
        """
        The string value, as computed by fn:string().
        """
        if obj is None:
            return ''
        elif isinstance(obj, XPathNode):
            if isinstance(obj, TypedElement):
                if obj.value is None:
                    return ''.join(etree_iter_strings(obj))
                return str(obj.value)
            elif isinstance(obj, (AttributeNode, TypedAttribute)):
                return str(obj.value)
            else:
                return cast(str, obj.value)  # TextNode or NamespaceNode
        elif is_schema_node(obj):
            return str(self.parser.get_atomic_value(obj.type))
        elif hasattr(obj, 'tag'):
            if is_comment_node(obj) or is_processing_instruction_node(obj):
                return cast(str, obj.text)
            elif hasattr(obj, 'attrib') and hasattr(obj, 'text'):
                return ''.join(etree_iter_strings(obj))
        elif is_document_node(obj):
            return ''.join(etree_iter_strings(obj.getroot()))
        elif isinstance(obj, bool):
            return 'true' if obj else 'false'
        elif isinstance(obj, Decimal):
            value = format(obj, 'f')
            if '.' in value:
                return value.rstrip('0').rstrip('.')
            return value

        elif isinstance(obj, float):
            if math.isnan(obj):
                return 'NaN'
            elif math.isinf(obj):
                return str(obj).upper()

            value = str(obj)
            if '.' in value:
                value = value.rstrip('0').rstrip('.')
            if '+' in value:
                value = value.replace('+', '')
            if 'e' in value:
                return value.upper()
            return value

        return str(obj)

    def number_value(self, obj: Any) -> float:
        """
        The numeric value, as computed by fn:number() on each item. Returns a float value.
        """
        try:
            return float(self.string_value(obj) if is_xpath_node(obj) else obj)
        except (TypeError, ValueError):
            return float('nan')

    ###
    # Error handling helpers
    def error_code(self, code: str) -> str:
        """Returns a prefixed error code."""
        if self.parser.namespaces.get('err') == XQT_ERRORS_NAMESPACE:
            return 'err:%s' % code

        for pfx, uri in self.parser.namespaces.items():
            if uri == XQT_ERRORS_NAMESPACE:
                return '%s:%s' % (pfx, code) if pfx else code

        return code  # returns an unprefixed code (without prefix the namespace is not checked)

    def error(self, code: Union[str, QName],
              message_or_error: Union[None, str, Exception] = None) -> ElementPathError:
        """
        Returns an XPath error instance related with a code. An XPath/XQuery/XSLT
        error code is an alphanumeric token starting with four uppercase letters
        and ending with four digits.

        :param code: the error code as QName or string.
        :param message_or_error: an optional custom message or an exception.
        """
        namespace: Optional[str]

        if isinstance(code, QName):
            namespace = code.uri
            code = code.local_name
        elif ':' not in code:
            namespace = None
        else:
            try:
                prefix, code = code.split(':')
            except ValueError:
                raise ElementPathValueError(
                    message='%r is not a prefixed name' % code,
                    code=self.error_code('XPTY0004'),
                    token=self,
                )
            else:
                namespace = self.parser.namespaces.get(prefix)

        if namespace and namespace != XQT_ERRORS_NAMESPACE:
            raise ElementPathValueError(
                message='%r namespace is required' % XQT_ERRORS_NAMESPACE,
                code=self.error_code('XPTY0004'),
                token=self,
            )

        try:
            error_class, default_message = XPATH_ERROR_CODES[code]
        except KeyError:
            raise ElementPathValueError(
                message='unknown XPath error code %r' % code,
                code=self.error_code('XPTY0004'),
                token=self,
            )

        if message_or_error is None:
            message = default_message
        elif isinstance(message_or_error, str):
            message = message_or_error
        elif isinstance(message_or_error, ElementPathError):
            message = message_or_error.message
        else:
            message = str(message_or_error)

        return error_class(message, code=self.error_code(code), token=self)

    # Shortcuts for XPath errors, only the wrong_syntax
    def expected(self, *symbols: str,
                 message: Optional[str] = None,
                 code: str = 'XPST0003') -> None:
        if symbols and self.symbol not in symbols:
            raise self.wrong_syntax(message, code)

    def unexpected(self, *symbols: str,
                   message: Optional[str] = None,
                   code: str = 'XPST0003') -> None:
        if not symbols or self.symbol in symbols:
            raise self.wrong_syntax(message, code)

    def wrong_syntax(self, message: Optional[str] = None,  # type: ignore[override]
                     code: str = 'XPST0003') -> ElementPathError:
        if self.label == 'function':
            code = 'XPST0017'

        if message:
            return self.error(code, message)

        error = super(XPathToken, self).wrong_syntax(message)
        return self.error(code, str(error))

    def wrong_value(self, message: Optional[str] = None) -> ElementPathValueError:
        return cast(ElementPathValueError, self.error('FOCA0002', message))

    def wrong_type(self, message: Optional[str] = None) -> ElementPathTypeError:
        return cast(ElementPathTypeError, self.error('FORG0006', message))

    def missing_context(self, message: Optional[str] = None) -> MissingContextError:
        return cast(MissingContextError, self.error('XPDY0002', message))

    def wrong_context_type(self, message: Optional[str] = None) -> ElementPathTypeError:
        return cast(ElementPathTypeError, self.error('XPTY0004', message))

    def missing_name(self, message: Optional[str] = None) -> ElementPathNameError:
        return cast(ElementPathNameError, self.error('XPST0008', message))

    def missing_axis(self, message: Optional[str] = None) \
            -> Union[ElementPathNameError, ElementPathSyntaxError]:
        if self.parser.compatibility_mode:
            return cast(ElementPathNameError, self.error('XPST0010', message))
        return cast(ElementPathSyntaxError, self.error('XPST0003', message))

    def wrong_nargs(self, message: Optional[str] = None) -> ElementPathTypeError:
        return cast(ElementPathTypeError, self.error('XPST0017', message))

    def wrong_sequence_type(self, message: Optional[str] = None) -> ElementPathTypeError:
        return cast(ElementPathTypeError, self.error('XPDY0050', message))

    def unknown_atomic_type(self, message: Optional[str] = None) -> ElementPathNameError:
        return cast(ElementPathNameError, self.error('XPST0051', message))


class XPathAxis(XPathToken):
    pattern = r'\b[^\d\W][\w.\-\xb7\u0300-\u036F\u203F\u2040]*(?=\s*\:\:|\s*\(\:.*\:\)\s*\:\:)'
    label = 'axis'
    reverse_axis: bool = False

    def nud(self) -> 'XPathAxis':
        self.parser.advance('::')
        self.parser.expected_name(
            '(name)', '*', 'text', 'node', 'document-node',
            'comment', 'processing-instruction', 'attribute',
            'schema-attribute', 'element', 'schema-element'
        )
        self._items[:] = self.parser.expression(rbp=self.rbp),
        return self


class ValueToken(XPathToken):
    """
    A dummy token for encapsulating a value.
    """
    symbol = '(value)'

    def evaluate(self, context: Optional[XPathContext] = None) -> Any:
        return self.value

    def select(self, context: Optional[XPathContext] = None) -> Iterator[Any]:
        yield self.value


class XPathFunction(XPathToken):
    """
    A token for processing XPath functions.
    """
    _name: Optional[QName] = None
    pattern = r'\b[^\d\W][\w.\-\xb7\u0300-\u036F\u203F\u2040]*(?=\s*(?:\(\:.*\:\))?\s*\((?!\:))'

    sequence_types: Tuple[str, ...] = ()
    "Sequence types of arguments and of the return value of the function."

    nargs: NargsType = None
    "Number of arguments: a single value or a couple with None that means unbounded."

    def __init__(self, parser: 'XPath1Parser', nargs: Optional[int] = None) -> None:
        super().__init__(parser)
        if isinstance(nargs, int) and nargs != self.nargs:
            if nargs < 0:
                raise self.error('XPST0017', 'number of arguments must be non negative')
            elif self.nargs is None:
                self.nargs = nargs
            elif isinstance(self.nargs, int):
                raise self.error('XPST0017', 'incongruent number of arguments')
            elif self.nargs[0] > nargs or self.nargs[1] is not None and self.nargs[1] < nargs:
                raise self.error('XPST0017', 'incongruent number of arguments')
            else:
                self.nargs = nargs

    def __call__(self, context: Optional[XPathContext] = None,
                 argument_list: Optional[Union[
                     XPathToken,
                     List[Union[XPathToken, AtomicValueType]],
                     Tuple[Union[XPathToken, AtomicValueType], ...]
                 ]] = None) -> Any:

        args: List[Union[Token[XPathTokenType], AtomicValueType]] = []
        if isinstance(argument_list, (list, tuple)):
            args.extend(argument_list)
        elif isinstance(argument_list, XPathToken):
            if argument_list.symbol == '(':
                args.append(argument_list)
            else:
                for token in argument_list.iter():
                    if token.symbol not in ('(', ','):
                        args.append(token)

        context = copy(context)
        if self.symbol == 'function':
            if context is None:
                raise self.missing_context()

            for variable, sequence_type, value in zip(self, self.sequence_types, args):
                if not self.parser.match_sequence_type(value, sequence_type):
                    msg = "invalid type for argument {!r}"
                    raise self.error('XPTY0004', msg.format(variable[0].value))
                varname = cast(str, variable[0].value)
                context.variables[varname] = value
        elif any(tk.symbol == '?' for tk in self):
            for value, tk in zip(args, filter(lambda x: x.symbol == '?', self)):
                if isinstance(value, XPathToken):
                    tk.value = value.evaluate(context)
                else:
                    assert not isinstance(value, Token), "An atomic value or None expected"
                    tk.value = value
        else:
            self.clear()
            for value in args:
                if isinstance(value, XPathToken):
                    self.append(value)
                else:
                    assert not isinstance(value, Token), "An atomic value or None expected"
                    self.append(ValueToken(self.parser, value=value))

        result = self.evaluate(context)
        if not self.parser.match_sequence_type(result, self.sequence_types[-1]):
            msg = "{!r} does not match sequence type {}"
            raise self.error('XPTY0004', msg.format(result, self.sequence_types[-1]))

        return result

    @property
    def name(self) -> Optional[QName]:
        if self.symbol == 'function':
            return None
        elif self._name is None:
            if not self.namespace or self.namespace == XPATH_FUNCTIONS_NAMESPACE:
                self._name = QName(XPATH_FUNCTIONS_NAMESPACE, 'fn:%s' % self.symbol)
            elif self.namespace == XSD_NAMESPACE:
                self._name = QName(XSD_NAMESPACE, 'xs:%s' % self.symbol)
            elif self.namespace == XPATH_MATH_FUNCTIONS_NAMESPACE:
                self._name = QName(XPATH_MATH_FUNCTIONS_NAMESPACE, 'math:%s' % self.symbol)

        return self._name

    @property
    def arity(self) -> int:
        return self.nargs if isinstance(self.nargs, int) else len(self)

    def nud(self) -> 'XPathFunction':
        code = 'XPST0017' if self.label == 'function' else 'XPST0003'
        self.value = None
        self.parser.advance('(')
        if self.nargs is None:
            del self._items[:]
            if self.parser.next_token.symbol in (')', '(end)'):
                raise self.error(code, 'at least an argument is required')
            while True:
                self.append(self.parser.expression(5))
                if self.parser.next_token.symbol != ',':
                    break
                self.parser.advance()
            self.parser.advance(')')
            return self
        elif self.nargs == 0:
            if self.parser.next_token.symbol != ')':
                if self.parser.next_token.symbol != '(end)':
                    raise self.error(code, '%s has no arguments' % str(self))
                raise self.parser.next_token.wrong_syntax()
            self.parser.advance()
            return self
        elif isinstance(self.nargs, (tuple, list)):
            min_args, max_args = self.nargs
        else:
            min_args = max_args = self.nargs

        k = 0
        while k < min_args:
            if self.parser.next_token.symbol in (')', '(end)'):
                msg = 'Too few arguments: expected at least %s arguments' % min_args
                raise self.wrong_nargs(msg if min_args > 1 else msg[:-1])

            self._items[k:] = self.parser.expression(5),
            k += 1
            if k < min_args:
                if self.parser.next_token.symbol == ')':
                    msg = 'Too few arguments: expected at least %s arguments' % min_args
                    raise self.error(code, msg if min_args > 1 else msg[:-1])
                self.parser.advance(',')

        while max_args is None or k < max_args:
            if self.parser.next_token.symbol == ',':
                self.parser.advance(',')
                self._items[k:] = self.parser.expression(5),
            elif k == 0 and self.parser.next_token.symbol != ')':
                self._items[k:] = self.parser.expression(5),
            else:
                break  # pragma: no cover
            k += 1

        if self.parser.next_token.symbol == ',':
            msg = 'Too many arguments: expected at most %s arguments' % max_args
            raise self.error(code, msg if max_args != 1 else msg[:-1])

        self.parser.advance(')')
        return self


class XPathConstructor(XPathFunction):
    """
    A token for processing XPath 2.0+ constructors.
    """
    @staticmethod
    def cast(value: Any) -> AtomicValueType:
        raise NotImplementedError()
