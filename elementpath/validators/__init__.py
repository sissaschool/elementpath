#
# Copyright (c), 2018-2022, SISSA (International School for Advanced Studies).
# All rights reserved.
# This file is distributed under the terms of the MIT License.
# See the file 'LICENSE' in the root directory of the present
# distribution, or http://opensource.org/licenses/MIT.
#
# @author Davide Brunato <brunato@sissa.it>
#
"""
Subpackage for validating against XPath standard schemas.
"""
import pathlib
from typing import Optional

import xmlschema
from ..namespaces import XPATH_FUNCTIONS_NAMESPACE

analyzed_string_schema: Optional[xmlschema.XMLSchemaBase] = None
json_to_xml_schema: Optional[xmlschema.XMLSchemaBase] = None

__all__ = ['validate_analyzed_string', 'validate_json_to_xml']


def validate_analyzed_string(xml_data: str) -> None:
    global analyzed_string_schema

    if analyzed_string_schema is None:
        xsd_file = pathlib.Path(__file__).parent.joinpath('analyze-string.xsd')
        analyzed_string_schema = xmlschema.XMLSchema(xsd_file)

    analyzed_string_schema.validate(xml_data)


def validate_json_to_xml(xml_data: str) -> None:
    global json_to_xml_schema

    if json_to_xml_schema is None:
        xsd_file = pathlib.Path(__file__).parent.joinpath('schema-for-json.xsd')
        json_to_xml_schema = xmlschema.XMLSchema(xsd_file)

    json_to_xml_schema.validate(xml_data, namespaces={'j': XPATH_FUNCTIONS_NAMESPACE})
