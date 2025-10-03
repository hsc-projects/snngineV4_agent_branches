from __future__ import annotations

from typing import ClassVar, TYPE_CHECKING

from pyqtgraph.parametertree.parameterTypes import (
    ListParameter,
    WidgetParameterItem
)

from snngine_v4.gui.parameter_trees.linker_tree.controls_map import \
    ControllerAction
from snngine_v4.gui.parameter_trees.linker_tree.linker_widget import \
    ShortCutWidget
from snngine_v4.gui.parameters.common.action_mixins import (
    ActionItemMixin,
    ActionParameterMixin
)
from snngine_v4.gui.parameters.common.engine_group_parameter import \
    EngineGroupParameter
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


if TYPE_CHECKING:
    from snngine_v4.gui.parameter_trees.linker_tree.linker_tree import \
        LinkerTree


class AddLinkerActionParameter(EngineGroupParameter):

    def __init__(self, **opts):
        super().__init__(**opts)


# class LinkerParameterItem(ListParameterItem, ActionItemMixin):
class LinkerParameterItem(WidgetParameterItem, ActionItemMixin):

    def __init__(self, param, depth):
        super().__init__(param=param, depth=depth)
        self.add_actions()

    def makeWidget(self):
        linker_tree: LinkerTree = self.treeWidget()
        self.asSubItem = True
        self.hideWidget = False
        wdg = ShortCutWidget(
            parameter=None,
            linker_tree=linker_tree,
        )
        wdg.sigChanged = None

        def setValue(value):
            if value not in [None, '']:
                wdg.load_controller(value)
            else:
                wdg.disconnect_parameter()

        def value():
            return wdg._controller

        wdg.setValue = setValue
        wdg.value = value
        return wdg
        # self.defaultBtn.setVisible(True)


# class LinkerParameter(ListParameter, ActionParameterMixin):
#
#     REGISTER_KW: ClassVar[str] = "linker"
#
#     itemClass = LinkerParameterItem
#
#     # noinspection PyPep8Naming
#     def __init__(self, name='Key0',
#                  autoIncrementName=True,
#                  default='',
#                  **opts):
#
#         if opts.get(ParamOpts.KW.TYPE, None) is None:
#             opts[ParamOpts.KW.TYPE] = self.REGISTER_KW
#         super().__init__(name=name,
#                          default=default,
#                          autoIncrementName=autoIncrementName,
#                          **opts)
#         self.sub_parameters = []
#         self.add_action(name='on_press', func=self.on_press)
#         # self.sigValueChanged.connect(self.on_value_changed)
#
#     # def add_subparameter(self):
#     #     name='sub_list' + str(len(self.sub_parameters))
#     #     self.add_list_action(name, self.on_value_changed)
#     #     self.sub_parameters.append(self.list_map.list_parameters[name])
#     #
#     # def on_value_changed(self, par, value):
#     #     main_par = self.value()
#     #     parent_par = main_par
#     #     depth = 0
#     #     if isinstance(main_par, Parameter):
#     #         while (c_count := len(main_par.children())) > 0:
#     #             if len(self.sub_parameters) < (depth + 1):
#     #                 self.add_subparameter()
#     #             sub_list_par = self.sub_parameters[depth]
#     #             sub_list_par.set
#
#
#     def on_press(self):
#         print('on_press')


class LinkerParameter(ListParameter, ActionParameterMixin):

    REGISTER_KW: ClassVar[str] = "linker"

    itemClass = LinkerParameterItem

    # noinspection PyPep8Naming
    def __init__(self, name='Key0',
                 autoIncrementName=True,
                 default='',
                 **opts):

        if opts.get(ParamOpts.KW.TYPE, None) is None:
            opts[ParamOpts.KW.TYPE] = self.REGISTER_KW
        super().__init__(name=name,
                         default=default,
                         autoIncrementName=autoIncrementName,
                         **opts)

    def setValue(self, value, blockSignal=None):
        new_value = super().setValue(value, blockSignal=blockSignal)
        if isinstance(new_value, ControllerAction):
            self.setName(new_value, )
