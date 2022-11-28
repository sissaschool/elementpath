#
# Copyright (c), 2022, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
from typing import Any, Dict, Optional, Union

from .exceptions import xpath_error
from .namespaces import XSLT_XQUERY_SERIALIZATION_NAMESPACE
from .xpath_nodes import ElementNode, AttributeNode, DocumentNode, NamespaceNode, TextNode
from .xpath_token import XPathToken, XPathMap, XPathArray

# XSLT and XQuery Serialization parameters
SERIALIZATION_PARAMS = '{%s}serialization-parameters' % XSLT_XQUERY_SERIALIZATION_NAMESPACE
SER_PARAM_OMIT_XML_DECLARATION = '{%s}omit-xml-declaration' % XSLT_XQUERY_SERIALIZATION_NAMESPACE
SER_PARAM_USE_CHARACTER_MAPS = '{%s}use-character-maps' % XSLT_XQUERY_SERIALIZATION_NAMESPACE
SER_PARAM_CHARACTER_MAP = '{%s}character-map' % XSLT_XQUERY_SERIALIZATION_NAMESPACE
SER_PARAM_METHOD = '{%s}method' % XSLT_XQUERY_SERIALIZATION_NAMESPACE
SER_PARAM_INDENT = '{%s}indent' % XSLT_XQUERY_SERIALIZATION_NAMESPACE
SER_PARAM_VERSION = '{%s}version' % XSLT_XQUERY_SERIALIZATION_NAMESPACE
SER_PARAM_CDATA = '{%s}cdata-section-elements' % XSLT_XQUERY_SERIALIZATION_NAMESPACE
SER_PARAM_NO_INDENT = '{%s}suppress-indentation' % XSLT_XQUERY_SERIALIZATION_NAMESPACE
SER_PARAM_STANDALONE = '{%s}standalone' % XSLT_XQUERY_SERIALIZATION_NAMESPACE
SER_PARAM_ITEM_SEPARATOR = '{%s}item-separator' % XSLT_XQUERY_SERIALIZATION_NAMESPACE


def get_serialization_params(params: Union[None, ElementNode, XPathMap] = None,
                             token: Optional[XPathToken] = None) -> Dict['str', Any]:

    kwargs = {}
    if isinstance(params, XPathMap):
        if len(params[:]) > len(params.keys()):
            raise xpath_error('SEPM0019', token=token)

        for key, value in params.items():
            if not isinstance(key, str):
                raise xpath_error('XPTY0004', token=token)

            if key == 'omit-xml-declaration':
                if not isinstance(value, bool):
                    raise xpath_error('XPTY0004', token=token)
                kwargs['xml_declaration'] = not value

            elif key == 'cdata-section-elements':
                pass

            elif key == 'method':
                if value not in ('html', 'xml', 'xhtml', 'text', 'adaptive', 'json'):
                    raise xpath_error('SEPM0017', token=token)
                kwargs['method'] = value if value != 'xhtml' else 'html'

            elif key == 'indent':
                if not isinstance(value, bool):
                    raise xpath_error('XPTY0004', token=token)
                kwargs['indent'] = value
                
            elif key == 'item-separator':
                if not isinstance(value, str):
                    raise xpath_error('XPTY0004', token=token)
                kwargs['item_separator'] = value
            
            elif key == 'use-character-maps':
                pass  # TODO param
            elif key == 'suppress-indentation':
                pass  # TODO param
            elif key == 'standalone':
                if value not in ('yes', 'no', 'omit'):
                    raise xpath_error('SEPM0017', token=token)
                if value != 'omit':
                    kwargs['standalone'] = value == 'yes'

            elif key.startswith(f'{{{XSLT_XQUERY_SERIALIZATION_NAMESPACE}'):
                raise xpath_error('SEPM0017')
            elif not key.startswith('{'):  # no-namespace not allowed
                raise xpath_error('SEPM0017')

    elif isinstance(params, ElementNode):
        root = params.value
        if root.tag != SERIALIZATION_PARAMS:
            raise token.error('XPTY0004', 'output:serialization-parameters tag expected')

        if len(root) > len({e.tag for e in root}):
            raise xpath_error('SEPM0019', token=token)

        for child in root:
            if child.tag == SER_PARAM_OMIT_XML_DECLARATION:
                value = child.get('value')
                if value not in ('yes', 'no') or len(child.attrib) > 1:
                    raise xpath_error('SEPM0017', token=token)
                elif value == 'no':
                    kwargs['xml_declaration'] = True

            elif child.tag == SER_PARAM_USE_CHARACTER_MAPS:
                if len(child.attrib):
                    raise xpath_error('SEPM0017', token=token)

                kwargs['character_map'] = character_map = {}
                for e in child:
                    if e.tag != SER_PARAM_CHARACTER_MAP:
                        raise xpath_error('SEPM0017', token=token)

                    try:
                        character = e.attrib['character']
                        if character in character_map:
                            msg = 'duplicate character {!r} in character map'
                            raise xpath_error('SEPM0018', msg.format(character), token)
                        elif len(character) != 1:
                            msg = 'invalid character {!r} in character map'
                            raise xpath_error('SEPM0017', msg.format(character), token)

                        character_map[character] = e.attrib['map-string']
                    except KeyError as key:
                        msg = "missing {} in character map"
                        raise xpath_error('SEPM0017', msg.format(key)) from None
                    else:
                        if len(e.attrib) > 2:
                            msg = "invalid attribute in character map"
                            raise xpath_error('SEPM0017', msg)

            elif child.tag == SER_PARAM_METHOD:
                value = child.get('value')
                if value not in ('html', 'xml', 'xhtml', 'text') or len(child.attrib) > 1:
                    raise xpath_error('SEPM0017', token=token)
                kwargs['method'] = value if value != 'xhtml' else 'html'

            elif child.tag == SER_PARAM_INDENT:
                value = child.attrib.get('value', '').strip()
                if value not in ('yes', 'no') or len(child.attrib) > 1:
                    raise xpath_error('SEPM0017', token=token)

            elif child.tag == SER_PARAM_ITEM_SEPARATOR:
                try:
                    kwargs['item_separator'] = child.attrib['value']
                except KeyError:
                    raise xpath_error('SEPM0017', token=token) from None

            elif child.tag == SER_PARAM_CDATA:
                pass  # TODO param
            elif child.tag == SER_PARAM_NO_INDENT:
                pass  # TODO param
            elif child.tag == SER_PARAM_STANDALONE:
                value = child.attrib.get('value', '').strip()
                if value not in ('yes', 'no', 'omit') or len(child.attrib) > 1:
                    raise xpath_error('SEPM0017', token=token)
                if value != 'omit':
                    kwargs['standalone'] = value == 'yes'

            elif child.tag.startswith(f'{{{XSLT_XQUERY_SERIALIZATION_NAMESPACE}'):
                raise xpath_error('SEPM0017', token=token)
            elif not child.tag.startswith('{'):  # no-namespace not allowed
                raise xpath_error('SEPM0017', token=token)

    return kwargs


def serialize_to_xml(elements, etree_module=None, token=None, **params):
    if etree_module is None:
        from xml.etree import ElementTree
        etree_module = ElementTree

    item_separator = params.get('item_separator', ' ')
    character_map = params.get('character_map')

    kwargs = {}
    if 'xml_declaration' in params:
        kwargs['xml_declaration'] = params['xml_declaration']
    if 'standalone' in params:
        kwargs['standalone'] = params['standalone']

    method = kwargs.get('method', 'xml')
    if method == 'xhtml':
        method = 'html'

    chunks = []
    for item in elements:
        if isinstance(item, DocumentNode):
            item = item.document.getroot()
        elif isinstance(item, ElementNode):
            item = item.elem
        elif isinstance(item, (AttributeNode, NamespaceNode)):
            raise xpath_error('SENR0001', token=token)
        elif isinstance(item, TextNode):
            chunks.append(item.value)
            continue
        elif isinstance(item, bool):
            chunks.append('true' if item else 'false')
            continue
        else:
            chunks.append(str(item))
            continue

        try:
            ck = etree_module.tostringlist(
                item, encoding='utf-8', method=method, **kwargs
            )
        except TypeError:
            chunks.append(etree_module.tostring(
                item, encoding='utf-8', method=method,
            ).decode('utf-8'))
        else:
            if ck and ck[0].startswith(b'<?'):
                ck[0] = ck[0].replace(b'\'', b'"')
            chunks.append(b'\n'.join(ck).decode('utf-8'))

    if not character_map:
        return item_separator.join(chunks)

    result = item_separator.join(chunks)
    for character, map_string in character_map.items():
        result = result.replace(character, map_string)
    return result


def serialize_to_json(elements, etree_module=None, token=None, **kwargs):
    if etree_module is None:
        from xml.etree import ElementTree
        etree_module = ElementTree

    try:
        iterator = iter(elements)
    except TypeError:
        iterator = iter((elements,))

    chunks = []
    for item in iterator:
        if isinstance(item, DocumentNode):
            item = item.document.getroot()
        elif isinstance(item, ElementNode):
            item = item.elem
        elif isinstance(item, (AttributeNode, NamespaceNode)):
            # if self.parser.version < '3.1':
            #    raise self.error('SENR0001')
            chunks.append(f'{item.name}="{item.string_value}"')
            continue
        elif isinstance(item, TextNode):
            chunks.append(item.value)
            continue
        elif isinstance(item, XPathMap):
            ck = []
            for k, v in item.items():
                sk = serialize_to_json(k, token=token, **kwargs)
                sv = serialize_to_json(v, token=token, **kwargs)
                ck.append(f'"{sk}": "{sv}"')
            chunks.append(f'{{{", ".join(ck)}}}')
            continue
        elif isinstance(item, XPathArray):
            continue
        elif isinstance(item, bool):
            chunks.append('true' if item else 'false')
            continue
        else:
            chunks.append(str(item))
            continue

        try:
            ck = etree_module.tostringlist(item, encoding='utf-8')
        except TypeError:
            chunks.append(etree_module.tostring(item, encoding='utf-8').decode('utf-8'))
        else:
            if ck and ck[0].startswith(b'<?'):
                ck[0] = ck[0].replace(b'\'', b'"')
            chunks.append(b'\n'.join(ck).decode('utf-8').replace('/', '\\/'))

    if len(chunks) > 1:
        raise xpath_error('SERE0023', token=token)

    return chunks[0]

