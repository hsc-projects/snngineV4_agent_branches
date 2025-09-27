from __future__ import annotations

from functools import cached_property
from typing import Callable, TYPE_CHECKING, Type

from pydantic import BaseModel
from pyqtgraph.parametertree.parameterTypes import (ActionParameter,
                                                    GroupParameter,
                                                    QtEnumParameter,
                                                    SimpleParameter)
from vispy.visuals import BoxVisual

from snngine_v4.gui.parameter_tree.connectors.model_signals_register import \
    ExtendedModelSignalsRegister
from snngine_v4.gui.parameter_tree.engine_parameter_tree import \
    EngineParameterTree
from snngine_v4.gui.parameter_tree.parameter_builder.parameter_builder import \
    ParameterBuilder
from snngine_v4.gui.parameter_tree.parameters.common \
    .engine_group_parameter import EngineGroupParameter
from snngine_v4.gui.parameter_tree.vispy_connector import VispyConnector
from snngine_v4.gui.selector_tree.selector_model import (SelectorModel,
                                                         SelectorType,
                                                         SourceSinkType)
from snngine_v4.utils.containers.mappings import (Object2ObjectMap,
                                                  ObjectMapConfig)
from snngine_v4.visualization.config_models.visuals.boxes import \
    BoxVisualInitConfig


if TYPE_CHECKING:
    from snngine_v4.snngine import SNNgine


class ParameterToVisualMap(Object2ObjectMap):

    __getitem__: Callable[[EngineGroupParameter], BoxVisual]

    class ContainerConfigClass(ObjectMapConfig, frozen=True):
        allowed_types: Type[EngineGroupParameter]
        b_clear_allowed: bool = True
        b_pop_allowed: bool = True


class SelectorParameter(EngineGroupParameter):

    COUNT: int = 0

    # noinspection PyPep8Naming
    def __init__(self,
                 signal_register: ExtendedModelSignalsRegister,
                 name="Selector",
                 removable=True,
                 expanded=False,
                 autoIncrementName=True,
                 selector_type=None,
                 source_sink_type=None,
                 **kwargs):

        name += str(self.__class__.COUNT)
        self.__class__.COUNT += 1

        self.init_name = name

        if selector_type is None:
            selector_type = SelectorType.NEURON

        if source_sink_type is None:
            source_sink_type = SourceSinkType.SOURCE

        super().__init__(name=name,
                         removable=removable,
                         expanded=expanded,
                         autoIncrementName=autoIncrementName,
                         **kwargs)

        self.signal_register = signal_register
        self.b_use_prefix = "Use "

        self.p_use_selector = SimpleParameter(
            name=self.use_par_name(),
            default=True,
            type='bool')

        self.sigNameChanged.connect(self.on_name_change)
        self.sigRemoved.connect(self.p_use_selector.remove)

        self.model = SelectorModel(
            selector_type=selector_type,
            source_sink_type=source_sink_type)

        pars = ParameterBuilder.make_pars_from_model(
            self.model,
            group=self,
            b_raise_if_missing_heritable_opts=False,
            signal_register=signal_register)

        self.selector_type_p.sigValueChanged.connect(self.rename)
        self.source_sink_type_p.sigValueChanged.connect(self.rename)
        self.rename()

    def on_name_change(self, par, name):
        self.p_use_selector.setName(
            self.use_par_name())

    def remove(self):
        super().remove()
        if self.signal_register is not None:
            self.signal_register.disconnect_model(self.model)

    @cached_property
    def selector_type_p(self) -> QtEnumParameter:
        return self.signal_register.get_parameter(
            self.model, SelectorModel.Slots.selector_type)

    @cached_property
    def source_sink_type_p(self) -> QtEnumParameter:
        return self.signal_register.get_parameter(
            self.model, SelectorModel.Slots.source_sink_type)

    def rename(self):
        self.setName(self.init_name +
                     f" ({self.selector_type_p.value().name}, "
                     f"{self.source_sink_type_p.value().name})")

    def use_par_name(self):
        return self.b_use_prefix + self.name()


class SelectionParameter(EngineGroupParameter):
    pass


class EngineSelectorTree(EngineParameterTree):

    def __init__(self, name: str = 'Selections', model: BaseModel = None,
                 engine: SNNgine = None,
                 **kwargs):
        super().__init__(name=name, model=model, **kwargs)

        self.p_selectors = EngineGroupParameter(name="Selectors")

        for selector_type in SelectorType:
            p_add_selectors = EngineGroupParameter(
                name=f"+ {selector_type.name.capitalize()} Selector")
            self.p_selectors.addChild(p_add_selectors)
            for source_sink_type in SourceSinkType:
                self._append_add_selector_action(
                    p_add_selectors=p_add_selectors,
                    selector_type=selector_type,
                    source_sink_type=source_sink_type)

        self.p_selections = EngineGroupParameter(name="Selections")
        self.p_selections.add_action('add_selection',
                                     self.add_selection,
                                     " + Selection ")

        self.addParameters(self.p_selectors)
        self.addParameters(self.p_selections)

        self._engine: SNNgine | None = None
        if engine is not None:
            self.connect_engine(engine)

    def add_selector_box_visual(
            self, par: SelectorParameter | SelectionParameter):
        if not self.b_engine_connected:
            raise AssertionError("Not connected")

        box_model = BoxVisualInitConfig(
            color=None, edge_color='blue'
        )

        box_visual = self._engine.make_visual(model=box_model)

        new_pars = self.add_parameters_from_model(
            model=box_model,
            root=self.p_selectors,
            name='SelectorBoxVisual',
            # signal_register=self.signal_register,
            # exclude_keys=exclude_keys
        )

        sub_visual_super_map = self._engine.main_scene.sub_visual_super_map

        VispyConnector.connect_object(
            model=box_model, obj=box_visual,
            sub_visual_super_map=sub_visual_super_map,
            signal_register=self.signal_register,)

    def add_selection(self):
        p_new_selection = SelectionParameter(
            name="Selection",
            removable=True,
            autoIncrementName=True)
        self.p_selections.addChild(p_new_selection)
        p_new_selection.sigRemoved.connect(self.on_selection_removed)

    def add_selector(
            self,
            selector_type: SelectorType | None = None,
            source_sink_type: SourceSinkType | None = None):
        # selector_type = self.default_type_p.value()

        p_new_selector = SelectorParameter(
            selector_type=selector_type,
            source_sink_type=source_sink_type,
            signal_register=self.signal_register
        )
        count = len(self.p_selectors.children()) - len(SelectorType)

        p_new_selector.sigRemoved.connect(self.on_selector_removed)

        self.p_selectors.addChild(p_new_selector)
        self.p_selections.insertChild(
            count, p_new_selector.p_use_selector)

    def _append_add_selector_action(
            self, p_add_selectors: EngineGroupParameter,
            selector_type: SelectorType, source_sink_type: SourceSinkType):

        def add_selector():
            self.add_selector(selector_type=selector_type,
                              source_sink_type=source_sink_type)
        name = source_sink_type.name
        p_add_selectors.add_action(
            f'add_{name.lower()}_selector', add_selector,
            f"+ {name.upper()}")

    @property
    def b_engine_connected(self):
        return self._engine is not None

    def connect_engine(self, engine: SNNgine):
        if self.b_engine_connected:
            raise RuntimeError("Already connected")
        self._engine = engine

    def on_selector_removed(self):
        pass

    def on_selection_removed(self):
        pass

    @cached_property
    def visual_map(self) -> ParameterToVisualMap:
        return ParameterToVisualMap()


if __name__ == '__main__':

    from qtpy import QtWidgets
    app = QtWidgets.QApplication([])

    tree_ = EngineSelectorTree()
    tree_.show()
    app.exec()
