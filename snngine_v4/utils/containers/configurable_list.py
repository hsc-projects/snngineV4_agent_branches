from collections import UserList
from typing import ClassVar, Type

from pydantic import BaseModel

from snngine_v4.utils.containers.configurable_container import (
    ConfigurableContainerBase, ContainerConfig,
)


class ConfigurableListConfig(ContainerConfig, frozen=True):

    b_append_allowed: bool = True
    b_clear_allowed: bool = True
    b_extend_allowed: bool = True
    b_insert_allowed: bool = True
    b_remove_allowed: bool = True


class ConfigurableList(ConfigurableContainerBase, UserList):

    ContainerConfigClass: ClassVar[Type[ConfigurableListConfig]] = (
        ConfigurableListConfig)

    def __init__(self, initlist=None,
                 container_conf: ConfigurableListConfig = None):

        self._container_conf: ConfigurableListConfig | None = None

        ConfigurableContainerBase.__init__(self, container_conf=container_conf)
        UserList.__init__(self)

        if initlist is not None:
            if isinstance(initlist, (list, UserList)):
                self.validate_items(initlist)
            else:
                self.validate_item(initlist)
                initlist = [initlist]
            self.extend(initlist)

    def append(self, item, b_ignore_non_matching_types: bool = False) -> None:
        if self._container_conf.b_append_allowed is False:
            raise AttributeError("Appending not allowed.")
        if ((b_ignore_non_matching_types is True)
                and (self.b_valid_item_type(item) is False)):
            return
        super().append(self.validate_item(item))

    def apply(self, func, *args, **kwargs):
        return [func(x, *args, **kwargs) for x in self]

    @classmethod
    def class_from_type(cls, type_: Type, **kwargs):
        class GeneratedConfigurableList(ConfigurableList):
            def __init__(
                    self, initlist=None,
                    container_conf: ConfigurableListConfig = None):
                container_conf = container_conf or ConfigurableListConfig(
                    allowed_types=type_, **kwargs)
                ConfigurableList.__init__(
                    self, initlist=initlist, container_conf=container_conf)
                # print(id(self))
                pass

        return GeneratedConfigurableList

    def clear(self, b_force: bool = False) -> None:
        if ((self._container_conf.b_clear_allowed is False)
                and (b_force is False)):
            raise AttributeError("Clearing not allowed.")
        super().clear()

    def b_duplicated_item(self, item):

        b_duplicate_check = not self._container_conf.b_duplicates_allowed

        return ((b_duplicate_check is True) and hasattr(self, "data")
                and (item in self))

    @property
    def empty(self) -> bool:
        return len(self) == 0

    def extend(self, other) -> None:
        if self._container_conf.b_extend_allowed is False:
            raise AttributeError("Extending not allowed.")
        super().extend(other)
        self.validate_items(self.data)

    def filtered_extend(self, list_: list, b_pop=False) -> None:
        list_ = self.cls_filter_list(
            list_=list_, type_=self._container_conf.allowed_types,
            result_list=[], b_pop=b_pop)
        self.extend(list_)

    @classmethod
    def from_type(cls, type_: Type, initlist=None, **kwargs):
        return cls(
            initlist=initlist,
            container_conf=ConfigurableListConfig(
                allowed_types=type_, **kwargs))

    def insert(self, i: int, item) -> None:
        if self._container_conf.b_insert_allowed is False:
            raise PermissionError("Inserting not allowed.")
        super().insert(i, self.validate_item(item))

    def pop(self, i=-1):
        if self._container_conf.b_pop_allowed is False:
            raise PermissionError("Popping not allowed.")
        return super().pop(i)

    def remove(self, item):
        if self._container_conf.b_remove_allowed is False:
            raise PermissionError("Remove not allowed.")
        try:
            super().remove(item)
        except ValueError:
            if (isinstance(item, int)
                and self._container_conf.b_remove_by_id_allowed
                and (item in self.data_ids)
            ):
                idx = self.data_ids.index(item)
                item_ = self[idx]
                if id(item_) != item:
                    raise ValueError("Item not found.")
                super().remove(item_)

    def replace(self, old, new):
        if self._container_conf.b_replace_allowed is False:
            raise PermissionError("Replacing not allowed.")
        idx = self.index(old)
        self.pop(idx)
        self.insert(idx, new)

    def __setitem__(self, i, value):
        if self._container_conf.b_replace_allowed is False:
            raise KeyError(f"Replacing elements is not allowed.")
        super().__setitem__(i, self.validate_item(value))


class ConfigurableModelListConfig(ConfigurableListConfig, frozen=True):
    allowed_types: Type[BaseModel] = BaseModel
    b_duplicate_check_by_id: bool = True
