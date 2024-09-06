from __future__ import annotations

from enum import IntEnum
from pprint import pprint
from types import NoneType
from xml.dom import minidom
from xml.etree.ElementTree import Element, ElementTree, SubElement, tostring

from deepdiff import DeepDiff
from pydantic import BaseModel


class XMLHandler:

    base_types = (int, float, str, bool, NoneType)
    base_type_dct = {str(t): t for t in base_types}

    TYPE_ATTRIBUTE = "type"
    ENUM_ATTRIBUTE = "Enum"
    SEQUENCE_ELEMENT_TAG_SUFFIX = "Element"
    SEQUENCE_ELEMENT_TYPES = [x.__name__.capitalize() + "Element"
                              for x in [list, tuple]]
    DICT_KEY_ATTR = "key"
    DICT_ITEM_TAG = "DictItem"

    @classmethod
    def convert_to_xml(cls, parent, tag, v, ref=None,
                       b_enum_as_names: bool = True):

        v_xml = SubElement(parent, tag)
        if hasattr(ref, tag):
            child_ref = getattr(ref, tag)
            v_xml.set(cls.TYPE_ATTRIBUTE, type(child_ref).__name__)
        else:
            v_xml.set(cls.TYPE_ATTRIBUTE, type(v).__name__)
            child_ref = None

        if isinstance(child_ref, IntEnum):
            v_xml.set(cls.ENUM_ATTRIBUTE, type(child_ref).__name__)
            v_xml.text = str(v)

        elif isinstance(v, cls.base_types):
            if type(v) in cls.base_types:
                v_xml.text = str(v)
            else:
                raise NotImplementedError(
                    f'Type {type(v)} is not supported')
        elif isinstance(v, (tuple, list)):
            if child_ref:
                tag = f'{type(child_ref).__name__.capitalize()}'
            else:
                tag = f'{type(v).__name__.capitalize()}'
            tag += cls.SEQUENCE_ELEMENT_TAG_SUFFIX
            for i, item in enumerate(v):
                cls.convert_to_xml(v_xml, tag=tag, v=item, ref=child_ref)

        elif isinstance(v, dict):
            for key, value in v.items():
                if not hasattr(child_ref, key):
                    tag = cls.DICT_ITEM_TAG
                else:
                    tag = key
                value_xml = cls.convert_to_xml(v_xml, tag, value,
                                               ref=child_ref)
                if not hasattr(child_ref, key):
                    value_xml.set(cls.DICT_KEY_ATTR, key)

        else:
            raise NotImplementedError(
                f'Type {type(v)} is not supported')
        return v_xml

    @classmethod
    def to_xml(cls, data: BaseModel | dict, parent: Element | None = None):

        parent = parent or Element(data.__class__.__name__)

        # print(data.model_rebuild())

        if isinstance(data, BaseModel):
            dct = data.model_dump(mode='json')
        else:
            dct = data
        if not isinstance(dct, dict):
            raise TypeError

        for k, v in dct.items():
            v_xml = cls.convert_to_xml(parent, k, v, ref=data)
        return parent

    @classmethod
    def convert_from_xml(cls, element: ElementTree | Element,
                         # conversion_dict: dict | None = None
                         ):
        attrib = element.attrib

        match attrib[XMLHandler.TYPE_ATTRIBUTE]:
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
                return [cls.convert_from_xml(x) for x in element]
            case 'dict':
                return {x.attrib['key']: cls.convert_from_xml(x) for x in
                        element}
            case 'tuple':
                return tuple([cls.convert_from_xml(x) for x in element])
            case 'set':
                return set([cls.convert_from_xml(x) for x in element])
            case 'frozenset':
                return frozenset([cls.convert_from_xml(x) for x in element])
            case _:
                if cls.ENUM_ATTRIBUTE in attrib:
                    return int(element.text)
                return element.text
                # raise NotImplementedError(attrib['type'])

    @classmethod
    def from_xml(cls, element: ElementTree | Element,
                 values=None,
                 b_collect_attrib: bool = True):
        """
        NOTE: parent_map = {c:p for p in element.iter() for c in p}
        """
        res = {}
        values = values or element.findall('*')
        for v in values:
            values_ = v.findall('*')
            if v.tag in res:
                raise KeyError(f'Key {v.tag} already exists')
            if ((len(values_) > 0)
                    and (values_[0].tag not in (cls.SEQUENCE_ELEMENT_TYPES
                         + [cls.DICT_ITEM_TAG]))):
                sub_res = cls.from_xml(
                    v, values=values_, b_collect_attrib=b_collect_attrib)
                if b_collect_attrib is True:
                    res[v.tag] = {}
                    res[v.tag]['attrib'] = v.attrib
                    res[v.tag]['value'] = sub_res
                else:
                    res[v.tag] = sub_res
            else:
                res[v.tag] = cls.convert_from_xml(v)
        return res

    @classmethod
    def to_xml_str(cls, data: BaseModel | dict, use_pretty_print: bool = True,
                   encoding='unicode', method='xml',
                   indent="  ",
                   **kwargs):

        res = tostring(cls.to_xml(data=data),
                       encoding=encoding, method=method, **kwargs)
        if use_pretty_print is True:
            res = minidom.parseString(res).toprettyxml(indent=indent)
        return res

    @classmethod
    def test_conversion(cls, model: BaseModel):

        model_dict = model.model_dump(mode='json')
        model_xml_data = cls.to_xml(model_dict)
        model_xml_data_dict = cls.from_xml(model_xml_data)
        model_xml = model.__class__(**model_xml_data_dict)
        model_xml_dict = model_xml.model_dump(mode='json')

        result = DeepDiff(model_dict, model_xml_dict,
                          ignore_private_variables=False)
        if 'unprocessed' in result:
            print('\nunprocessed:')
            pprint([x[: x.index(':')] for x in result['unprocessed']])
        if 'type_changes' in result:
            print('\ntype_changes:')
            pprint(result['type_changes'])
        return result
