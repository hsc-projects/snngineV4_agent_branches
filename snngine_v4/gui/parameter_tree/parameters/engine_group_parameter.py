from pyqtgraph.parametertree import Parameter, ParameterItem, ParameterTree
from pyqtgraph.parametertree.parameterTypes import (
    GroupParameter,
    GroupParameterItem, NumericParameterItem, WidgetParameterItem,
)
from qtpy import QtCore, QtWidgets

from snngine_v4.gui.icons import getEngineGraphIcon
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


class EngineGroupParameterItem(GroupParameterItem):

    def __init__(self, param, depth):

        self._widgets = []

        self._size_set = False

        GroupParameterItem.__init__(self, param, depth)

        self.defaultBtn = self.makeDefaultButton()
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addStretch(0)

        self.layoutWidget = QtWidgets.QWidget()
        self.layoutWidget.setLayout(layout)

        if ParamOpts.KW.C_NUMERIC_GROUP in param.opts:
            pass

        layout.addWidget(self.defaultBtn)
        param.sigChildAdded.connect(self.updateDefaultBtn)
        param.sigChildRemoved.connect(self.updateDefaultBtn)
        self.updateDefaultBtn()

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

    # noinspection PyPep8Naming
    def defaultClicked(self):
        print(self.layoutWidget.width())
        for i in range(self.childCount()):
            c = self.child(i)
            if isinstance(c, ParameterItem):
                c.defaultClicked()
        self.updateDefaultBtn()

    # noinspection PyPep8Naming
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

    # noinspection PyPep8Naming
    def updateDefaultBtn(self):
        enabled = False
        for i in range(self.childCount()):
            c = self.child(i)
            if isinstance(c, WidgetParameterItem):
                enabled = c.defaultBtn.isEnabled()
                if enabled:
                    break
        self.defaultBtn.setEnabled(enabled)


class EngineGroupParameter(GroupParameter):

    itemClass = EngineGroupParameterItem

    @classmethod
    def from_model(cls, model, name):
        return cls(**ParamOpts.from_model(model=model, name_=name))

    def makeTreeItem(self, depth) -> EngineGroupParameterItem:
        return super().makeTreeItem(depth=depth)

    def setToDefault(self):
        for param in self.children():
            param: Parameter
            param.setToDefault()
