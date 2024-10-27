from __future__ import annotations

from pathlib import Path

import numpy as np
from pydantic import BaseModel

from snngine_v4.utils.data.deepdish_pack import deepdish
from snngine_v4.utils.data.validation.np_interface import ExtendedNumpyJsonDict
from snngine_v4.utils.field_utils import model_keys
from snngine_v4.utils.settings.settings_keywords import BaseModelSlots


def is_array_value(item):
    return isinstance(item, np.ndarray) or (
            isinstance(item, dict) and ExtendedNumpyJsonDict.is_valid(item))


class ArrayDictRW:

    @classmethod
    def update_destination(cls, dest: list | dict | BaseModel, k, v):
        if dest is None:
            return
        if isinstance(dest, list):
            dest.append(v)
        elif isinstance(dest, dict):
            dest[k] = v
        else:
            setattr(dest, k, v)

    @classmethod
    def update_destinations(cls, dests: list, k, v):
        for d in dests:
            cls.update_destination(d, k, v)

    @classmethod
    def next_destination(cls, dest: list | dict | BaseModel | None, k,
                         type_=None, container=None):
        if dest is None:
            return dest
        if isinstance(dest, list):
            if container is not None:
                dest.append(container)
                return container
            return dest
        elif isinstance(dest, dict):
            if k in dest:
                return dest[k]
            if type_ is None:
                dest[k] = {}
            else:
                dest[k] = type_()
            return dest[k]
        else:
            return getattr(dest, k)

    @classmethod
    def update_destinations_from_iterable(cls, parent_dests, k, v, b_recursive):

        b_iterable_dest_exists = []
        iterable_dests = []

        for d in parent_dests:
            b_iterable_dest_exists.append(isinstance(d, BaseModel) or (
                    isinstance(d, dict) and (k in d)))
            iterable_dests.append(cls.next_destination(d, k, type_=type(v)))
            if (b_iterable_dest_exists[-1] and (len(v) > 0)
                    and (len(iterable_dests[-1]) != len(v))):
                raise AssertionError

        for idx, item in enumerate(v):
            if is_array_value(item):
                raise RuntimeError
                # update_destinations(dests, k, item)
            elif b_recursive and isinstance(item, BaseModel | dict):
                dests_ = []
                for dest_idx, d in enumerate(iterable_dests):
                    if d is not None:
                        if b_iterable_dest_exists[dest_idx] is False:
                            dests_.append(cls.next_destination(
                                iterable_dests[dest_idx], k,
                                container=dict()
                                if not isinstance(parent_dests[dest_idx], list)
                                else None))
                        else:
                            dests_.append(iterable_dests[dest_idx][idx])
                    else:
                        dests_.append(None)

                cls.extract_arrays(item, b_recursive=True, dests=dests_)

    @classmethod
    def extract_arrays(cls, container: BaseModel | dict | Path | str,
                       dests: tuple | list | None = None,
                       b_recursive: bool = True):

        if dests is None:
            dests = [{}]

        if isinstance(container, (Path, str)):
            container = deepdish.io.load(container)

        if isinstance(container, BaseModel):
            keys = model_keys(container, exclude=BaseModelSlots.CLASS__NAME)
        else:
            keys = container.keys()

        for k in keys:

            if isinstance(container, BaseModel):
                v = getattr(container, k)
            else:
                v = container[k]

            if is_array_value(v):
                cls.update_destinations(dests, k, v)
            elif b_recursive and isinstance(v, BaseModel | dict):
                cls.extract_arrays(v, b_recursive=True,
                                   dests=[cls.next_destination(d, k)
                                          for d in dests])
            elif isinstance(v, (list, tuple)):
                cls.update_destinations_from_iterable(dests, k, v, b_recursive)
        return dests
