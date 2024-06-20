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

    options = {
        'attr_prefix': '',
        'cdata_key': 'text'
    }

    json_from_xml = xmltodict.parse(xml_content, **options)

    return json_from_xml


def parse_xml_to_json(supplier_name):
    xml_file_path = os.path.join(os.getcwd(), 'xml', f'{supplier_name}.xml')

    try:
        tree = ET.parse(xml_file_path)
        root_element = tree.getroot()

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
        ToLog.write_error(f"Error parsing XML file {xml_file_path}: {error}")
        return None


def clean_xml_string(xml_string):
    # Удаление неподходящих символов
    invalid_xml_re = re.compile('[^\x09\x0A\x0D\x20-\x7F]')
    return invalid_xml_re.sub('', xml_string)


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


def parse_large_xml_to_json_stream(supplier_name):
    xml_file_path = os.path.join(os.getcwd(), 'xml', f'{supplier_name}.xml')
    json_data = []

    try:
        context = etree.iterparse(xml_file_path, events=("end",))

        for event, elem in context:
            # Преобразование элемента в строку XML
            xml_str = etree.tostring(elem, encoding='utf-8').decode('utf-8')

            # Очистка строки от неподходящих символов
            cleaned_xml_str = clean_xml_string(xml_str)

            # Преобразование очищенной строки XML в словарь
            elem_tree = etree.fromstring(cleaned_xml_str)
            json_elem = element_to_dict(elem_tree)
            json_data.append(json_elem)

            # Очистка элемента из памяти после обработки
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]

        return json_data

    except Exception as error:
        ToLog.write_error(f"Error parsing XML file {xml_file_path}: {error}")
        return None


# def parse_xml_to_json(supplier_name):
#     xml_file_path = os.path.join(os.getcwd(), 'xml', f'{supplier_name}.xml')
#
#     try:
#         tree = ET.parse(xml_file_path)
#         root = tree.getroot()
#
#         def elem_to_dict(elem):
#             d = {elem.tag: {} if elem.attrib else None}
#             children = list(elem)
#             if children:
#                 dd = dict()
#                 for dc in map(elem_to_dict, children):
#                     for k, v in dc.items():
#                         if k in dd:
#                             dd[k].append(v)
#                         else:
#                             dd[k] = [v]
#                 d = {elem.tag: dd}
#             if elem.attrib:
#                 d[elem.tag].update(('@' + k, v) for k, v in elem.attrib.items())
#             if elem.text:
#                 text = elem.text.strip()
#                 if children or elem.attrib:
#                     if text:
#                         d[elem.tag]['#text'] = text
#                 else:
#                     d[elem.tag] = text
#             return d
#
#         json_from_xml = elem_to_dict(root)
#         return json_from_xml
#     except Exception as e:
#         print(f"Error parsing XML file {xml_file_path}: {e}")
#         return None

# Example usage:
# json_data = parse_xml_to_json('pgn')
# print(json_data)
