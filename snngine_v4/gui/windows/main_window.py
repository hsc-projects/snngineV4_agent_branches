from copy import copy
from functools import cached_property
from typing import ClassVar

from qtpy import QtCore, QtWidgets

from snngine_v4.gui.common.docks import MainDockWidget
from snngine_v4.gui.common.qobject_dicts import QWidgetDict

from snngine_v4.gui.parameter_tree.vispy_connector import \
    VispyConnector
from snngine_v4.gui.parameter_tree.parameters.widgets.table \
    .array_editor import ArrayEditorDockWidget
from snngine_v4.gui.views.view_area import ViewArea
from snngine_v4.gui.windows.extra_parameters import ParameterArea
from snngine_v4.gui.windows.settings_window import SettingsWindow

from snngine_v4.snngine import SNNgine
from snngine_v4.gui.windows.main_window_base import (
    MainEngineWindowBase,
    WindowTypes,
)
from snngine_v4.gui.parameter_tree.engine_parameter_tree import (
    EngineParameterTree, EngineTreeDockWidget,
)
from snngine_v4.gui.parameter_tree.tensor_connector import TensorConnector


# noinspection PyPep8Naming
class MainEngineWindow(MainEngineWindowBase):

    SETTINGS_DOCK_CLASS: ClassVar = EngineTreeDockWidget

    def __init__(self, engine: SNNgine):

        sec_views = ViewArea(scene_manager=engine.scene_manager)

        windows = QWidgetDict({
            WindowTypes.SETTINGS: SettingsWindow(engine_config=engine.conf),
            WindowTypes.EXTRA_PARAMETERS: ParameterArea(),
            WindowTypes.SECONDARY_VIEWS: sec_views
        })

        # sec_views.show()
        sec_views.resize(QtCore.QSize(640, 480))

        super().__init__(windows, engine=engine)

        self.add_secondary_views()
        # sec_views.show()
        # sec_views: ViewArea = self.windows[WindowTypes.SECONDARY_VIEWS]
        # sec_views.addDock(self.engine.conf.scenes.multiplot_current)
        # sec_views.addDock(self.engine.conf.scenes.multiplot_voltage)

    def add_secondary_views(self):

        sec_views: ViewArea = self.windows[WindowTypes.SECONDARY_VIEWS]
        sec_views.show()

        model_list = copy(self.engine.scene_manager.refs.data)
        model_list.remove(self.engine.conf.scenes.main)
        model_list.reverse()
        for model in model_list:
            sec_views.addDock(model)

    @cached_property
    def b_pycuda_available(self):
        try:
            import pycuda
            return True
        except ModuleNotFoundError:
            return False

    def build(self):
        self.main_network_scene.set_current()
        self.engine.build_network()
        self.update_connections()

    def addRightDockWidget(self, key, widget: MainDockWidget):
        show_dock_action = QtWidgets.QAction(key, self.right_toolbar)
        self.right_toolbar.addAction(show_dock_action)
        self.addDockWidget(
            QtCore.Qt.DockWidgetArea.RightDockWidgetArea, widget)
        # noinspection PyTypeChecker,PydanticTypeChecker
        self.docks.add_widget(widget)
        show_dock_action.triggered.connect(widget.toggleVisibility)
        widget.close()

    def setup_dock_widgets(self):
        super().setup_dock_widgets()

        array_dock = ArrayEditorDockWidget(name=self.ARRAYS_DOCK_NAME)
        self.addRightDockWidget('A', array_dock)

        controls_tree = EngineParameterTree()

        features = (
            QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable)
        controls_dock = EngineTreeDockWidget(
            pars=controls_tree, name=self.CONTROLS_DOCK_NAME,
            features=features)
        self.addRightDockWidget('C', controls_dock)

    def update_connections(self):

        VispyConnector.cls_connect_tree(
            tree=self.scene_tree, scene_manager=self.engine.scene_manager)

        current_model = self.engine.network_manager.container_model

        self.network_tree.clear()
        self.network_tree.set_parameters_from_model(model=current_model,
                                                    showTop=False)

        # network_pos = deepcopy(current_model.network.elements[1].pos_origin)

        sr = self.network_tree.signal_register
        # sync_signal_register = ExtendedModelSignalsRegister()
        model0 = current_model.network.elements[1].pos_origin
        model1 = current_model.network.elements[1].grid.pos_origin
        # sr[model0].add_parameter(sr.get_group(model1))
        # o2o_links = ModelParameterLinks(
        #     model=model0,
        #     group_param=self.network_tree.signal_register.get_group(model1))
        # o2o_links = ModelParameterLinks(
        #     model=model1,
        #     group_param=self.network_tree.signal_register.get_group(model0))
        # o2o_links = Object2ObjectLinks(source=model0, sink=model1)
        # o2o_links.add_attribute('X')
        # sync_signal_register.add_linked_model(
        #     model0=model0,
        #     model1=model1,
        #     group0=self.network_tree.signal_register.get_group(model0),
        # )

        network_connector = VispyConnector()
        # network_connector.connect_tree(
        network_connector.cls_connect_tree(
            tree=self.network_tree,
            scene_manager=self.engine.scene_manager)
        if self.b_pycuda_available:
            from snngine_v4.gui.parameter_tree.cuda_connector import (
                CudaVispyConnector,
            )
            model2buffers = CudaVispyConnector.cls_connect_tree(
                tree=self.network_tree, scene_manager=self.engine.scene_manager,
                device=current_model.network.device)

        model2tensors = TensorConnector.cls_connect_tree(
            tree=self.network_tree,
            network_manager=self.engine.network_manager,)

        # self.show()
        # self.main_network_scene.set_current()
        # sec_views: ViewArea = self.windows[WindowTypes.SECONDARY_VIEWS]
        # sec_views.addDock(self.engine.conf.scenes.multiplot_voltage)
        # sec_views.addDock(self.engine.conf.scenes.current_voltage)
        self.main_network_scene.set_current()
        return
