from pyqtgraph.parametertree import Parameter, ParameterItem
from pyqtgraph.parametertree.parameterTypes import (
    GroupParameter,
    GroupParameterItem, NumericParameterItem, WidgetParameterItem,
)
from qtpy import QtCore, QtWidgets

from snngine_v4.gui.icons import getEngineGraphIcon
from snngine_v4.gui.parameter_tree.parameter_builder.options_builder import \
    OptionsBuilder
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


# noinspection PyPep8Naming
class EngineGroupParameterItem(GroupParameterItem):

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

        if param.opts.get(ParamOpts.KW.C_B_GROUP_DEFAULT_BUTTON, False):
            pass
            self.defaultBtn = self.makeDefaultButton()
            layout.addWidget(self.defaultBtn)
            param.sigChildAdded.connect(self.updateDefaultBtn)
            param.sigChildRemoved.connect(self.updateDefaultBtn)
            self.updateDefaultBtn()

    def add_engine_slider_parameter_widgets(self, item):
        if ParamOpts.KW.C_NUMERIC_GROUP not in self.param.opts:
            raise PermissionError
        from snngine_v4.gui.parameter_tree.parameters \
            .spin_box_slider_parameter import \
            SpinBoxSliderParameterItem
        item: SpinBoxSliderParameterItem
        idx = len(self._widgets)

        if idx == 0:
            w = self.layoutWidget.layout().takeAt(0)
            self.layoutWidget.layout().removeItem(w)

        self.layoutWidget.layout().insertWidget(idx * 2, item.widget)
        self.layoutWidget.layout().insertWidget(idx * 2, item.displayLabel)

        item.param.sigValueChanged.connect(self.updateDefaultBtn)

        if isinstance(item, SpinBoxSliderParameterItem):
            item.layoutWidget.layout().insertWidget(
                0, item.slider_layout_widget)
        self._widgets.append(item.widget)

    def addChild(self, child):
        super().addChild(child)
        from snngine_v4.gui.parameter_tree.parameters \
            .spin_box_slider_parameter import \
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

    def defaultClicked(self):
        print(self.layoutWidget.width())
        for i in range(self.childCount()):
            c = self.child(i)
            if isinstance(c, ParameterItem):
                c.defaultClicked()
        self.updateDefaultBtn()

    def makeDefaultButton(self):
        defaultBtn = QtWidgets.QPushButton()
        defaultBtn.setAutoDefault(False)
        defaultBtn.setFixedWidth(20)
        defaultBtn.setFixedHeight(20)
        defaultBtn.setIcon(getEngineGraphIcon('kamiyamane/default'))
        defaultBtn.clicked.connect(self.defaultClicked)
        return defaultBtn

    def treeWidgetChanged(self):
        super().treeWidgetChanged()
        tree = self.treeWidget()
        if tree and (ParamOpts.KW.C_NUMERIC_GROUP in self.param.opts):
            self.setFirstColumnSpanned(False)
            tree.setItemWidget(self, 1, self.layoutWidget)

    def set_sizes(self):
        if self._size_set is False:
            n_widget = len(self._widgets)
            if n_widget >= len(self.param.opts[ParamOpts.KW.C_GROUP_PREFIXES]):
                sb = self.defaultBtn.sizeHint()
                sb.setHeight(int(sb.height() * 0.9))
                h = sb.height()
                w = sb.width()
                for wdg in self._widgets:
                    sw = wdg.sizeHint()
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
        enabled = False
        for i in range(self.childCount()):
            c = self.child(i)
            if isinstance(c, WidgetParameterItem):
                enabled = c.defaultBtn.isEnabled()
                if enabled:
                    break
        self.defaultBtn.setEnabled(enabled)


# noinspection PyPep8Naming
class EngineGroupParameter(GroupParameter):

    itemClass = EngineGroupParameterItem

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
    def from_model(cls, model, **options):
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
        for param in self.children():
            param: Parameter
            param.setToDefault()

    def value(self):
        return {
            x.name(): x.value() for x in self.children()
        }

    def valueChanged(self, child, value):
        return self.sigValueChanged.emit(self, self.value())
