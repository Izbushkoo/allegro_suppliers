import io
import json
import os
import xml.etree.ElementTree as ET
import re

from lxml import etree

from app.loggers import ToLog

import os
import xmltodict


def parse_xml_to_json_test(supplier_name):
    xml_file_path = os.path.join(os.getcwd(), 'xml', f'{supplier_name}.xml')

    with open(xml_file_path, 'r', encoding='utf-8') as file:
        xml_content = file.read()

    cleaned_xml_content = clean_xml_string(xml_content)

    options = {
        'attr_prefix': '',
        'cdata_key': 'text'
    }

    json_from_xml = xmltodict.parse(cleaned_xml_content, **options)

    return json_from_xml


def parse_xml_to_json_sync(content):

    try:
        # tree = ET.parse(io.StringIO(content))
        # root_element = tree.getroot()
        root_element = ET.fromstring(content)

        def element_to_dict(element):
            element_dict = {element.tag: {} if element.attrib else None}
            child_elements = list(element)
            if child_elements:
                children_dict = {}
                for child_dict in map(element_to_dict, child_elements):
                    for key, value in child_dict.items():
                        if key in children_dict:
                            if not isinstance(children_dict[key], list):
                                children_dict[key] = [children_dict[key]]
                            children_dict[key].append(value)
                        else:
                            children_dict[key] = value
                element_dict = {element.tag: children_dict}
            if element.attrib:
                element_dict[element.tag].update(
                    ('@' + attr_key, attr_value) for attr_key, attr_value in element.attrib.items()
                )
            if element.text:
                text = element.text.strip()
                if child_elements or element.attrib:
                    if text:
                        element_dict[element.tag]['#text'] = text
                else:
                    element_dict[element.tag] = text
            return element_dict

        json_from_xml = element_to_dict(root_element)
        return json_from_xml
    except Exception as error:
        ToLog.write_error(f"Error parsing XML content: {error}")
        return None


def clean_xml_string(xml_string):
    # Удаление неподходящих символов
    invalid_xml_re = re.compile(r'[^\x09\x0A\x0D\x20-\x7F]')
    return invalid_xml_re.sub('', xml_string)


def element_to_dict_(element):
    """Преобразование элемента XML в словарь"""
    element_dict = {element.tag: {} if element.attrib else None}
    child_elements = list(element)
    if child_elements:
        children_dict = {}
        for child_dict in map(element_to_dict_, child_elements):
            for key, value in child_dict.items():
                if key in children_dict:
                    if not isinstance(children_dict[key], list):
                        children_dict[key] = [children_dict[key]]
                    children_dict[key].append(value)
                else:
                    children_dict[key] = value
        element_dict = {element.tag: children_dict}
    if element.attrib:
        element_dict[element.tag].update(
            ('@' + attr_key, attr_value) for attr_key, attr_value in element.attrib.items()
        )
    if element.text and element.text.strip():
        text = element.text.strip()
        if child_elements or element.attrib:
            if text:
                element_dict[element.tag]['#text'] = text
        else:
            element_dict[element.tag] = text
    return element_dict




