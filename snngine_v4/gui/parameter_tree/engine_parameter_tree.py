from pydantic import BaseModel
from pyqtgraph.parametertree import ParameterTree
from qtpy import QtCore

from snngine_v4.config.base.ui_options import ParameterUIOpts
from snngine_v4.gui.parameter_tree.parameter_builder import ParameterBuilder
from snngine_v4.gui.parameter_tree.signal_register import SignalMapRegister


class EngineParameterTree(ParameterTree):

    # noinspection PyPep8Naming
    def __init__(self, model: BaseModel,
                 parent=None, showHeader=True):

        super().__init__(parent=parent, showHeader=showHeader)

        self.settings_model = model
        settings_model_dict = self.settings_model.model_dump()
        self.signal_register = SignalMapRegister()
        self.parameters = self.add_parameters_from_model(
            self.settings_model, model_dict=settings_model_dict)

    def add_parameters_from_model(self, model: BaseModel, model_dict=None):
        if model_dict is None:
            model_dict = model.model_dump()
        pars = self.cls_make_parameters(
            model=model, model_dict=model_dict,
            signal_register=self.signal_register)
        self.addParameters(pars)
        return pars

    def sizeHint(self):
        hint = super().sizeHint()
        return QtCore.QSize(hint.width(), hint.height() + 20)

    @classmethod
    def cls_make_parameters(cls, model, model_dict,
                            signal_register: SignalMapRegister | None = None,
                            name=None):
        group = ParameterBuilder.make_group(
            model, name=name, model_dict=model_dict)
        for k, v in model_dict.items():
            if k not in [ParameterUIOpts.UI_OPTIONS_KEYWORD]:
                if isinstance(getattr(model, k), BaseModel):
                    par = cls.cls_make_parameters(
                        model=getattr(model, k), model_dict=v, name=k)
                else:
                    par = ParameterBuilder.make(model=model, key=k, value=v)
                if signal_register is not None:
                    signal_register.connect_parameter(
                        model, key_=name, parameter=par)
                group.addChild(par)
        return group
