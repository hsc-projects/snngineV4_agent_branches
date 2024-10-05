from __future__ import annotations

from typing import Callable, Type

from pydantic import BaseModel
from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.parameterTypes import GroupParameter

from snngine_v4.gui.parameter_tree.connectors.model_parameter_links import \
    ModelParameterLinks
from snngine_v4.utils.containers.mappings import (
    Int2ObjectMapConfig, Model2ObjectMap,
)


class ModelSignalRegister(Model2ObjectMap):

    class ContainerConfigClass(Int2ObjectMapConfig, frozen=True):
        allowed_types: Type[ModelParameterLinks]
        b_clear_allowed: bool = True

    values: Callable[[], list[ModelParameterLinks]]

    def __init__(self, **kwargs):
        self.data: dict[BaseModel, ModelParameterLinks] | None = None
        self.group_map: dict[BaseModel, GroupParameter] | Model2ObjectMap = (
            Model2ObjectMap.from_type(GroupParameter))
        self.model2model_map = Model2ObjectMap.from_type(BaseModel)
        super().__init__(**kwargs)

    def clear(self, b_force: bool = False, b_clear_inv: bool = True):
        for v in self.values():
            v.clear(b_force=self.container_conf.b_clear_allowed)
        super().clear(b_force=b_force, b_clear_inv=b_clear_inv)
        self.group_map.clear(b_force=True)

    def connect_group_parameter(self, model, parameter: GroupParameter):
        if model not in self:
            self[model] = ModelParameterLinks(model=model)
            self.group_map[model] = parameter
        self[model].add_group_parameter(model=model, parameter=parameter)

    @property
    def connected_models(self):
        return self.refs

    def connect_parameter(self, model, parameter: Parameter):
        if model not in self:
            self[model] = ModelParameterLinks(model=model)
        self[model].add_parameter(parameter=parameter, obj=model)

    def link_model(self, model0, model1):
        self.model2model_map[model0] = model1
