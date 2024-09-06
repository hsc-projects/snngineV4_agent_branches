from __future__ import annotations

from collections import UserDict

from snngine_v4.utils.containers.typed_container import (
    ConfigurableContainerBase, ContainerConfig,
)


class ConfigurableDict(ConfigurableContainerBase, UserDict):

    def __init__(
            self, initdict=None,
            container_conf: ContainerConfig | None = None):

        UserDict.__init__(self, initdict)
        ConfigurableContainerBase.__init__(
            self, container_conf=container_conf)

    @classmethod
    def from_type(cls, type_: type,
                  initdict=None, **kwargs):
        return cls(
            initdict=initdict,
            container_conf=ContainerConfig(allowed_types=type_, **kwargs))

    def update(self, m, **kwargs) -> None:
        values = list(m.values()) + list(kwargs.values())
        self.validate_items(values)
        super().update(m, **kwargs)

    def __setitem__(self, key, item):
        if self._container_conf.b_replace_allowed is False:
            if key in self.keys():
                raise KeyError(f"Key {key} already exists.")
        super().__setitem__(key, self.validate_item(item))

    # def filtered_set_item(self, key, value, sink_dict=None):
    #     if sink_dict is None:
    #         sink_dict = {}
    #     if self.check_type(value) is True:
    #         self[key] = value
    #     else:
    #         sink_dict[key] = value
    #     return sink_dict
