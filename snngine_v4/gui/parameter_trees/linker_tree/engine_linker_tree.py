from enum import IntEnum, auto
from functools import cached_property
from typing import ClassVar

from pydantic import BaseModel
from pyqtgraph.parametertree.parameterTypes import ActionParameter

from snngine_v4.gui.parameter_trees.linker_tree.linker_tree import LinkerTree
from snngine_v4.gui.parameter_trees.linker_tree.linker_window import \
    ShortCutWindow
from snngine_v4.gui.parameters.preset_parameter import PresetGroupParameter
from snngine_v4.snngine import SNNgine


class DeviceTypes(IntEnum):
    KEYBOARD = 0
    X_TOUCH_MINI = auto()


class KeyBoardLinks(PresetGroupParameter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # self.addChild(SimpleParameter(name='K0', type='bool'))


class XTouchMiniLinks(PresetGroupParameter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # self.addChild(SimpleParameter(name='B0', type='bool'))


class EngineLinkerTree(LinkerTree):

    X_TOUCH_MINI_KW: ClassVar[str] = 'xtm'

    def __init__(self, name: str = 'Selections',
                 model: BaseModel = None,
                 engine: SNNgine = None,
                 parameter_type_dict=None,
                 default_context=None,
                 trees=None,
                 **kwargs):
        if parameter_type_dict is None:
            parameter_type_dict = {
                DeviceTypes.KEYBOARD: KeyBoardLinks,
                DeviceTypes.X_TOUCH_MINI: XTouchMiniLinks,
            }
        self.parameter_type_dict = parameter_type_dict

        self.trees = trees

        if default_context is None:
            default_context = {
                self.SHORTCUT_KW: 'Edit Shortcut(s)',
                self.X_TOUCH_MINI_KW: 'Edit X-Touch Mini Controller(s)'}

        super().__init__(name=name, model=model,
                         default_context=default_context,
                         preset_types=DeviceTypes,
                         presets_name='Devices',
                         parameter_type_dict=parameter_type_dict,
                         **kwargs)

        def update():
            for tree in self.trees:
                self.read_tree(tree)

        self.update_action_p = ActionParameter(name='update',)
        self.update_action_p.sigActivated.connect(update)
        self.addParameters(self.update_action_p)

    @cached_property
    def x_touch_mini_window(self):
        return ShortCutWindow()

    def on_sig_context_menu_changed(self, param, data):
        match data:
            case self.X_TOUCH_MINI_KW:
                pass
            case _:
                super().on_sig_context_menu_changed(param, data)


if __name__ == '__main__':

    from qtpy import QtCore, QtWidgets
    from snngine_v4.config.template import SpatialNetworkConfig
    from snngine_v4.gui.parameter_trees.engine_parameter_tree import \
        EngineParameterTree

    app = QtWidgets.QApplication([])

    wdg = QtWidgets.QWidget()
    wdg.setLayout(QtWidgets.QVBoxLayout())
    splitter = QtWidgets.QSplitter()
    wdg.layout().addWidget(splitter)


    model0_ = SpatialNetworkConfig()

    tree2_ = EngineParameterTree(model=model0_)
    tree_ = EngineLinkerTree(trees=[tree2_])
    splitter.addWidget(tree_)
    splitter.addWidget(tree2_)

    wdg.show()
    app.exec()
