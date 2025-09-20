from pydantic import BaseModel
from pyqtgraph.parametertree.parameterTypes import (ActionParameter,
                                                    GroupParameter,
                                                    SimpleParameter)

from snngine_v4.gui.parameter_tree.connectors.model_signals_register import \
    ExtendedModelSignalsRegister
from snngine_v4.gui.parameter_tree.engine_parameter_tree import \
    EngineParameterTree
from snngine_v4.gui.parameter_tree.parameter_builder.parameter_builder import \
    ParameterBuilder
from snngine_v4.gui.selector_tree.selector_model import SelectorModel


class SelectorGroupParameter(GroupParameter):

    # noinspection PyPep8Naming
    def __init__(self,
                 signal_register: ExtendedModelSignalsRegister,
                 name="Selector",
                 removable=True,
                 autoIncrementName=True,
                 **kwargs):

        super().__init__(name=name,
                         removable=removable,
                         autoIncrementName=autoIncrementName,
                         **kwargs)

        self.signal_register = signal_register
        self.b_use_prefix = "Use "

        self.p_use_selector = SimpleParameter(
            name=self.use_par_name(),
            type='bool')

        self.sigNameChanged.connect(self.on_name_change)
        self.sigRemoved.connect(self.p_use_selector.remove)

        self.model = SelectorModel()
        pars = ParameterBuilder.make_pars_from_model(
            self.model, signal_register=signal_register)
        self.addChildren(pars)

    def use_par_name(self):
        return self.b_use_prefix + self.name()

    def on_name_change(self, par, name):
        self.p_use_selector.setName(
            self.use_par_name())


class EngineSelectorTree(EngineParameterTree):

    def __init__(self, name: str = 'Selections', model: BaseModel = None,
                 **kwargs):
        super().__init__(name=name, model=model, **kwargs)

        self.p_selectors = GroupParameter(
            name="Selectors")
        self.p_add_selector_action = ActionParameter(
            name="  Add Selector  ")
        self.p_selectors.addChild(self.p_add_selector_action)
        self.p_add_selector_action.sigActivated.connect(
            self.add_selector)

        self.p_selections = GroupParameter(
            name="Selections")
        self.p_add_selection_action = ActionParameter(
            name="  Add Selection  ")
        self.p_add_selection_action.sigActivated.connect(
            self.add_selection)
        self.p_selections.addChild(self.p_add_selection_action)

        self.addParameters(self.p_selectors)
        self.addParameters(self.p_selections)

    def add_selector(self):
        p_new_selector = SelectorGroupParameter(
            signal_register=self.signal_register
        )

        count = len(self.p_selectors.children())
        self.p_selectors.insertChild(
            count-1, p_new_selector)

        self.p_selections.insertChild(
            count - 1, p_new_selector.p_use_selector)

    def add_selection(self):
        p_new_selector = GroupParameter(
            name="Selection",
            removable=True,
            autoIncrementName=True)
        count = len(self.p_selections.children())
        self.p_selections.insertChild(
            count-1, p_new_selector)
