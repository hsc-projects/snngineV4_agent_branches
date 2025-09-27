from __future__ import annotations

import os
from enum import IntEnum
from pprint import pprint
from xml.dom import minidom
from xml.etree.ElementTree import (
    Element,
    ElementTree,
    SubElement,
    tostring
)

from deepdiff import DeepDiff
from pydantic import BaseModel

from pydantic_settings.sources import PathType

from snngine_v4.utils.data_utils.validation.np_interface \
    import ExtendedNumpyJsonDict
from snngine_v4.utils.settings.xml_converter.xml_converter_options import (
    XMLConverterOptions,
    XMLStringOptions,
)


class CustomElementTree(ElementTree):

    def __init__(self, element=None, file=None, parser=None):
        super().__init__(element=element, file=None)
        if file:
            self.parse(file, parser=parser)


class XMLConverter:

    def __init__(self, conf: XMLConverterOptions = None):
        if conf is None:
            conf = XMLConverterOptions()

        self.conf: XMLConverterOptions = conf

    def dict_from_xml(self, element: ElementTree | Element | PathType,
                      values=None,
                      parser=None,
                      b_collect_attrib: bool = True):
        """
        NOTE: parent_map = {c:p for p in element.iter() for c in p}
        """

        if isinstance(element, str):
            element = CustomElementTree(file=element, parser=parser)
        elif isinstance(element, list):
            res = {}
            for elem in element:
                value = self.dict_from_xml(elem, parser=parser,
                                           b_collect_attrib=b_collect_attrib)
                res.update(value)
            return res

        res = {}

        values = values or element.findall('*')

        seq_elm_namings = self.conf.sequence_element_types_naming

        for v in values:
            values_ = v.findall('*')
            if v.tag in res:
                raise KeyError(f'Key {v.tag} already exists')
            if ((len(values_) > 0)
                    and (values_[0].tag not in
                         seq_elm_namings + [self.conf.dict_item_tag])):
                sub_res = self.dict_from_xml(
                    v, values=values_, b_collect_attrib=b_collect_attrib)
                if b_collect_attrib is True:
                    res[v.tag] = {}
                    res[v.tag]['attrib'] = v.attrib
                    res[v.tag]['value'] = sub_res
                else:
                    res[v.tag] = sub_res
            else:
                res[v.tag] = self.value_from_xml(v)
        return res

    def to_xml(self, data: BaseModel | dict,
               parent: Element | None = None, **kwargs):
        parent = parent or Element(data.__class__.__name__)
        if not isinstance(data, dict):
            dct = data.model_dump(mode='json', **kwargs)
        else:
            dct = data

        for k, v in dct.items():
            self.value_to_xml(parent, k, v, ref=dct)
        return parent

    def test_conversion(self, model: BaseModel, **kwargs):

        model_dict = model.model_dump(mode='json', **kwargs)
        model_xml_data = self.to_xml(model_dict)
        model_xml_data_dict = self.dict_from_xml(model_xml_data)
        model_xml = model.__class__(**model_xml_data_dict)
        model_xml_dict = model_xml.model_dump(mode='json', **kwargs)

        result = DeepDiff(model_dict, model_xml_dict,
                          ignore_private_variables=False)
        if 'unprocessed' in result:
            print('\nunprocessed:')
            pprint([x[: x.index(':')] for x in result['unprocessed']])
        if 'type_changes' in result:
            print('\ntype_changes:')
            pprint(result['type_changes'])
        return result

    def to_xml_str(self, data: BaseModel | dict,
                   **kwargs):

        options = self.conf.to_string_options.model_dump()
        options.update(kwargs)

        b_pretty = options.pop(XMLStringOptions.Slots.B_PRETTY)
        indent = options.pop(XMLStringOptions.Slots.INDENT)
        newl = options.pop(XMLStringOptions.Slots.NEWL)
        encoding = options.get(XMLStringOptions.Slots.ENCODING)

        res = tostring(self.to_xml(data=data), **options)
        if b_pretty is True:
            res = minidom.parseString(res).toprettyxml(
                newl=newl, indent=indent, encoding=encoding)
        return res

    def to_xml_file(self, data, fn,
                    b_make_dir: bool = True,
                    b_dir_exist_ok=True, **kwargs):
        if not os.path.isfile(fn):
            directory = os.path.dirname(os.path.abspath(fn))
            if b_make_dir:
                os.makedirs(directory, exist_ok=b_dir_exist_ok)
        content = self.to_xml_str(data=data, **kwargs)
        with open(fn, 'wb') as file:
            file.write(content)

    def value_from_xml(self, element: ElementTree | Element):

        attrib = element.attrib

        match attrib[self.conf.type_attribute]:
            case 'int':
                return int(element.text)
            case 'float':
                return float(element.text)
            case 'str':
                return element.text
            case 'bool':
                return True if element.text == 'True' else False
            case 'NoneType':
                return None
            case 'list':
                return [self.value_from_xml(x) for x in element]
            case 'dict':
                res = {x.attrib[self.conf.dict_key_attribute]:
                       self.value_from_xml(x)
                       for x in element}
                if ((tag_map := self.conf.dict_key_to_tag_attributes)
                        is not None):
                    for k, v in tag_map.items():
                        if (tag_value := attrib.get(v, None)) is not None:
                            if k in res:
                                raise KeyError(f'Key {k} already exists')
                            res[k] = tag_value

                return res

            case 'tuple':
                return tuple([self.value_from_xml(x) for x in element])
            case 'set':
                return set([self.value_from_xml(x) for x in element])
            case 'frozenset':
                return frozenset([self.value_from_xml(x) for x in element])
            case _:
                if self.conf.enum_attribute in attrib:
                    return int(element.text)
                return element.text
                # raise NotImplementedError(attrib['type'])

    def value_to_xml(self, parent, tag, v, ref=None):

        if isinstance(v, dict):
            b_array = ExtendedNumpyJsonDict.is_valid(v)
            if b_array:
                raise RuntimeError

        v_xml = SubElement(parent, tag)
        if hasattr(ref, tag):
            child_ref = getattr(ref, tag)
            v_xml.set(self.conf.type_attribute, type(child_ref).__name__)
        else:
            v_xml.set(self.conf.type_attribute, type(v).__name__)
            if (isinstance(v, dict)
                    and ((tag_map := self.conf.dict_key_to_tag_attributes)
                         is not None)):
                for k in tag_map:
                    if k in v:
                        v_xml.set(tag_map[k], v.pop(k))
            child_ref = None

        if isinstance(child_ref, IntEnum):
            v_xml.set(self.conf.enum_attribute, type(child_ref).__name__)
            v_xml.text = str(v)
        else:
            base_types = self.conf.base_types
            if isinstance(v, base_types):
                if type(v) in base_types:
                    v_xml.text = str(v)
                else:
                    raise NotImplementedError(
                        f'Type {type(v)} is not supported')
            elif isinstance(v, (tuple, list)):
                if child_ref:
                    tag = f'{type(child_ref).__name__.capitalize()}'
                else:
                    tag = self.conf.make_seq_element_name(type(v))
                tag += self.conf.sequence_element_tag_suffix
                for i, item in enumerate(v):
                    self.value_to_xml(v_xml, tag=tag, v=item, ref=child_ref)

            elif isinstance(v, dict):
                for key, value in v.items():
                    b_array_ = False
                    if isinstance(value, dict):
                        b_array_ = ExtendedNumpyJsonDict.is_valid(value)
                    if not b_array_:
                        if not hasattr(child_ref, key):
                            tag = self.conf.dict_item_tag
                        else:
                            tag = key

                        value_xml = self.value_to_xml(v_xml, tag, value,
                                                      ref=child_ref)

                        if not hasattr(child_ref, key):
                            value_xml.set(self.conf.dict_key_attribute, key)

            else:
                raise NotImplementedError(
                    f'Type {type(v)} is not supported')
        return v_xml
