from __future__ import annotations

from typing import ClassVar, TYPE_CHECKING

from qtpy.QtGui import QKeySequence
from pyqtgraph.parametertree.parameterTypes import (
    ListParameter,
    WidgetParameterItem
)

from snngine_v4.gui.parameter_trees.linker_tree.controls_map import \
    ControllerAction
from snngine_v4.gui.parameter_trees.linker_tree.linker_widget import \
    (LinkerWidget, ShortCutWidget)
from snngine_v4.gui.parameter_trees.linker_tree.linker_window import \
    LinkerWindow
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

    widget: ShortCutWidget

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
            if wdg.linker_tree is None:
                wdg.linker_tree = self.treeWidget()
            if value not in [None, '']:
                wdg.load_controller(value)
            else:
                wdg.disconnect_parameter(b_block_signal=False)

        def value():
            return wdg.controller

        wdg.setValue = setValue
        wdg.value = value

        wdg.sigLinkDeleted.connect(self.on_clear)
        wdg.sigWidgetDelete.connect(self.on_remove)

        wdg.clear_btn.setVisible(False)
        wdg.save_btn.setVisible(False)

        return wdg
        # self.defaultBtn.setVisible(True)

    def get_window_widget(
            self, b_raise: bool) -> tuple[LinkerWindow, LinkerWidget] | None:
        ctrl: ControllerAction = self.param.value()
        if isinstance(ctrl, ControllerAction):
            # noinspection PyTypeChecker
            tree: LinkerTree = self.widget.linker_tree
            if tree is not None:
                if isinstance(ctrl.input_obj, QKeySequence):
                    window = tree.short_cut_window
                else:
                    raise NotImplementedError
                if window.parameter is ctrl.parameter:
                    try:
                        window_widget: LinkerWidget = (
                            window.ctrl_widget_map)[ctrl]
                    except KeyError:
                        if b_raise:
                            raise
                        return None
                    return window, window_widget
        return None

    def on_clear(self):
        window_window_widget = self.get_window_widget(b_raise=True)
        if window_window_widget is not None:
            window_widget = window_window_widget[1]
            window_widget.disconnect_parameter(
                b_block_signal=False, b_raise=False)

    def on_remove(self):
        if ((window_window_widget := self.get_window_widget(b_raise=False))
                is not None):
            window, window_widget = window_window_widget
            window.remove_linker_widget(
                window_widget, b_disconnect=False)

    def requestRemove(self):
        self.widget.disconnect_parameter(b_block_signal=False)


class LinkerParameter(ListParameter, ActionParameterMixin):

    REGISTER_KW: ClassVar[str] = "linker"

    itemClass = LinkerParameterItem

    # noinspection PyPep8Naming
    def __init__(self, name='Key0',
                 autoIncrementName=True,
                 default='',
                 removable=True,
                 **opts):

        if opts.get(ParamOpts.KW.TYPE, None) is None:
            opts[ParamOpts.KW.TYPE] = self.REGISTER_KW
        self.init_name = name
        super().__init__(name=name,
                         default=default,
                         removable=removable,
                         autoIncrementName=autoIncrementName,
                         **opts)

    # noinspection PyPep8Naming
    def setValue(self, value, blockSignal=None):
        new_value = super().setValue(value, blockSignal=blockSignal)
        if isinstance(new_value, ControllerAction):
            new_name = (
                LinkerWidget.parameter_label_text(new_value.parameter)
                + f" ({new_value.input_object_string}"
                + f": {new_value.action_type.name}) "
            )
            self.setName(new_name)
        else:
            self.setName(self.init_name)
