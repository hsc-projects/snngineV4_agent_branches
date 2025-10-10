from __future__ import annotations

from typing import Callable, ClassVar

from pyqtgraph.parametertree import Parameter, ParameterItem
from pyqtgraph.parametertree.parameterTypes import (
    GroupParameter,
    GroupParameterItem, NumericParameterItem,
)
from qtpy import QtCore, QtWidgets

from snngine_v4.gui.icons import getEngineGraphIcon
from snngine_v4.gui.parameter_trees.parameter_builder.options_builder import \
    OptionsBuilder
from snngine_v4.gui.parameters.common.action_mixins import (
    ActionItemMixin, ActionParameterMixin,
)
from snngine_v4.utils.field_utils import is_equal
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


# noinspection PyPep8Naming
class EngineGroupParameterItem(GroupParameterItem, ActionItemMixin):

    param: EngineGroupParameter

    def __init__(self, param, depth):

        self._widgets = []

        self._size_set = False

        GroupParameterItem.__init__(self, param, depth)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addStretch(0)

        self.layoutWidget = QtWidgets.QWidget()
        self.layoutWidget.setLayout(layout)

        if param.opts.get(ParamOpts.KW.C_B_GROUP_DEFAULT_BUTTON, False) is True:
            pass
            self.defaultBtn = self.makeDefaultButton()
            self.updateDefaultBtn()
        else:
            self.defaultBtn = None

        self.add_actions()

    def add_engine_slider_parameter_widgets(self, item):
        if ParamOpts.KW.C_NUMERIC_GROUP not in self.param.opts:
            raise PermissionError
        from snngine_v4.gui.parameters.spin_box_slider_parameter import \
            SpinBoxSliderParameterItem
        item: SpinBoxSliderParameterItem
        idx = len(self._widgets)

        if idx == 0:
            w = self.layoutWidget.layout().takeAt(0)
            if not isinstance(w, QtWidgets.QSpacerItem):
                raise TypeError
            self.layoutWidget.layout().removeItem(w)

        self.layoutWidget.layout().insertWidget(idx * 2, item.widget)
        self.layoutWidget.layout().insertWidget(idx * 2, item.displayLabel)

        if isinstance(item, SpinBoxSliderParameterItem):
            item.layoutWidget.layout().insertWidget(
                0, item.slider_layout_widget)
        self._widgets.append(item.widget)
    
    def addChild(self, child):
        super().addChild(child)
        from snngine_v4.gui.parameters.spin_box_slider_parameter import \
            SpinBoxSliderParameterItem

        if isinstance(child, (SpinBoxSliderParameterItem,
                              NumericParameterItem)):
            b_add_to_header = self.param.opts.get(
                ParamOpts.KW.C_NUMERIC_GROUP, False)
            if b_add_to_header:
                self.add_engine_slider_parameter_widgets(child)

        if (self.param.opts.get(ParamOpts.KW.C_COLLAPSED_CHILDREN, False)
                is True):
            child.param.setOpts(expanded=False)
        elif ParamOpts.auto_expand_condition(
                e := self.param.opts[ParamOpts.KW.EXPANDED], self.param.opts):
            if child.param.opts.get(ParamOpts.KW.EXPANDED, True) != e:
                child.param.setOpts(expanded=e)

        if self.defaultBtn:

            from snngine_v4.gui.parameters import IndexParameter
            if isinstance(self.param, IndexParameter):
                pass

            child.param.sigValueChanged.connect(self.updateDefaultBtn)

    def apply_clicked(self):
        self.param.sigApply.emit(self.param)

    def defaultClicked(self):
        print(self.layoutWidget.width())
        for i in range(self.childCount()):
            c = self.child(i)
            if isinstance(c, ParameterItem):
                c.defaultClicked()
                c.param._modifiedSinceReset = False
            else:
                pass
        self.updateDefaultBtn()

    def makeDefaultButton(self):
        defaultBtn = QtWidgets.QPushButton()
        defaultBtn.setAutoDefault(False)
        defaultBtn.setFixedWidth(20)
        defaultBtn.setFixedHeight(20)
        defaultBtn.setIcon(getEngineGraphIcon('kamiyamane/default'))
        defaultBtn.clicked.connect(self.defaultClicked)
        self.layoutWidget.layout().addWidget(defaultBtn)
        self.param.sigChildAdded.connect(self.updateDefaultBtn)
        self.param.sigChildRemoved.connect(self.updateDefaultBtn)
        self.widget_dict['default'] = defaultBtn
        return defaultBtn

    def treeWidgetChanged(self):
        super().treeWidgetChanged()
        tree = self.treeWidget()
        if tree:
            if ParamOpts.KW.C_NUMERIC_GROUP in self.param.opts:
                self.setFirstColumnSpanned(False)
                tree.setItemWidget(self, 1, self.layoutWidget)
            # elif self.widget_dict.get('apply', None) is not None:
            #     self.setFirstColumnSpanned(False)
            #     tree.setItemWidget(self, 1, self.layoutWidget)
            elif (len(self.param.action_map)
                  + len(self.param.list_map)) > 0:
                self.setFirstColumnSpanned(False)
                tree.setItemWidget(self, 1, self.layoutWidget)

    # def setFocus(self):
    #     super().setFocus()

    def selected(self, sel):
        super().selected(sel)
        self.param.sigSelected.emit(self, sel)
    
    def set_sizes(self):
        if self._size_set is False:
            n_widget = len(self._widgets)
            if n_widget >= len(self.param.opts[ParamOpts.KW.C_GROUP_PREFIXES]):
                sb: QtCore.QSize = self.defaultBtn.sizeHint()
                sb.setHeight(int(sb.height() * 0.9))
                h = sb.height()
                w = sb.width()
                for wdg in self._widgets:
                    sw: QtCore.QSize = wdg.sizeHint()
                    sw.setHeight(int(sw.height() * 0.9))

                    w += wdg.minimumWidth() + 2
                    h = max(sw.height(), h)
                self.layoutWidget.setMinimumWidth(w)
                self.setSizeHint(1, QtCore.QSize(w, h))
                self._size_set = True

    def expandedChangedEvent(self, expanded):
        super().expandedChangedEvent(expanded)
        opts = self.param.opts
        if not opts[ParamOpts.KW.SYNC_EXPANDED]:
            e = bool(expanded)
            if ParamOpts.auto_expand_condition(e, opts):
                for i in range(self.childCount()):
                    self.child(i).setExpanded(e)

    def updateDefaultBtn(self):

        from snngine_v4.gui.parameters import IndexParameter
        if isinstance(self.param, IndexParameter):
            pass

        for i in range(self.childCount()):
            c = self.child(i)
            if c.param.valueModifiedSinceResetToDefault() is True:
                self.defaultBtn.setEnabled(True)
                return
        self.defaultBtn.setEnabled(False)


# noinspection PyPep8Naming
class EngineGroupParameter(GroupParameter, ActionParameterMixin):

    itemClass = EngineGroupParameterItem

    children: Callable[[], list[Parameter]]

    sigApply = QtCore.Signal(object)
    sigSelected = QtCore.Signal(object, bool)
    # sigValueChanged = QtCore.Signal(object, object)
    APPLY_KW: ClassVar[str] = "apply"

    def __init__(self, **opts):

        if ParamOpts.KW.C_INIT_VALUE not in opts:
            init_value = opts[ParamOpts.KW.C_INIT_VALUE] \
                = opts.pop(ParamOpts.KW.VALUE, None)
            init_default = opts[ParamOpts.KW.C_INIT_DEFAULT] \
                = opts.pop(ParamOpts.KW.DEFAULT, None)
            if not is_equal(init_value, init_default):
                pass

        super().__init__(**opts)
        if opts.get(ParamOpts.KW.C_B_GROUP_APPLY_BUTTON, False) is True:
            self.add_apply_action()

    def add_apply_action(self, func=None):
        if self.APPLY_KW not in self.action_map:
            self.add_action(self.APPLY_KW, self.emit_apply, ' Apply ')
        if func:
            self.sigApply.connect(func)

    def emit_apply(self):
        self.sigApply.emit(self)

    def connect_sigValueChanged(self, recursive: int = 0):
        for child in self.children():
            if isinstance(child, Parameter):
                child.sigValueChanged.connect(self.valueChanged)
                if (((recursive > 0) or (recursive == -1)) and
                        isinstance(child, EngineGroupParameter)):
                    child.connect_sigValueChanged(
                        recursive=(recursive - 1) if (recursive > 0)
                        else recursive)

    @classmethod
    def from_model(cls, model, **options) -> EngineGroupParameter:
        return cls(**OptionsBuilder
                   .from_model(model=model, **options))

    def makeTreeItem(self, depth) -> EngineGroupParameterItem:
        return super().makeTreeItem(depth=depth)

    def setOpts(self, **opts):
        super().setOpts(**opts)
        if ((ParamOpts.KW.EXPANDED in opts)
                and (self.opts.get(ParamOpts.KW.SYNC_EXPANDED, False) is True)):
            e = bool(opts[ParamOpts.KW.EXPANDED])
            if ParamOpts.auto_expand_condition(e, self.opts):
                for c in self.children():
                    c.setOpts(expanded=e)

    def setToDefault(self):
        with self.treeChangeBlocker():
            for param in self.children():
                param: Parameter
                param.setToDefault()
            self._modifiedSinceReset = False

    def setValue(self, value, blockSignal=None):
        return super().setValue(value, blockSignal=blockSignal)

    def value(self):
        if self.type() == 'list':
            return [x.value() for x in self.children()]
        # value = self.opts['value']
        # if value is None:
        value = {
            x.name(): x.value() for x in self.children()
        }
        # return values_dct
        return value

    def valueChanged(self, child: Parameter, value):
        if child.valueModifiedSinceResetToDefault() is True:
            self._modifiedSinceReset = True
        value_ = self.value()
        self.sigValueChanged.emit(self, value_)
        # self.sigValueChanged.emit(self, )
