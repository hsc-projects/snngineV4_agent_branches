from typing import ClassVar

from qtpy import QtCore, QtWidgets

from snngine_v4.gui.common.qobject_dicts import QWidgetDict
from snngine_v4.gui.parameter_tree.vispy_connector import \
    VispyConnector
from snngine_v4.gui.parameter_tree.parameters.widgets.array_editor import \
    ArrayEditorDockWidget
from snngine_v4.gui.windows.settings_window import SettingsWindow
from snngine_v4.nn.config_models.nn_reservoir_config import NetworkReservoir
from snngine_v4.snngine import SNNgine
from snngine_v4.gui.windows.main_window_base import (
    MainEngineWindowBase,
    WindowTypes,
)
from snngine_v4.gui.parameter_tree.engine_parameter_tree import (
    EngineTreeDockWidget,
)
from snngine_v4.gui.parameter_tree.cuda_connector import CudaVispyConnector


# noinspection PyPep8Naming
class MainEngineWindow(MainEngineWindowBase):

    SETTINGS_DOCK_CLASS: ClassVar = EngineTreeDockWidget

    def __init__(self, engine: SNNgine):

        windows = QWidgetDict({
            WindowTypes.SETTINGS: SettingsWindow(engine_config=engine.conf)
        })

        super().__init__(windows, engine=engine)

        # self.build()

    def build(self):
        self.engine.build()
        self.update_connections()

    def setup_dock_widgets(self):
        docks = super().setup_dock_widgets()
        array_dock = ArrayEditorDockWidget(name=self.ARRAYS_DOCK_NAME)
        self.addDockWidget(
            QtCore.Qt.DockWidgetArea.RightDockWidgetArea, array_dock)
        array_dock.close()
        docks.add_widgets(array_dock)

        show_array_editor_action = QtWidgets.QAction('A', self.right_toolbar)
        self.right_toolbar.addAction(show_array_editor_action)
        show_array_editor_action.triggered.connect(
            docks[self.ARRAYS_DOCK_NAME].toggleVisibility)

        return docks

    def update_connections(self):

        VispyConnector.cls_connect_tree(
            tree=self.scene_tree,
            scene_manager=self.engine.scene_manager)

        self.network_tree.clear()
        self.network_tree.add_parameters_from_model(
            self.engine.network_manager.container_model,
            showTop=False)
        network_connector = VispyConnector()
        # network_connector.connect_tree(
        network_connector.cls_connect_tree(
            tree=self.network_tree,
            scene_manager=self.engine.scene_manager)

        buffers = CudaVispyConnector.cls_connect_tree(
            tree=self.network_tree,
            scene_manager=self.engine.scene_manager)

        marker_model: NetworkReservoir = (
            self.engine.conf.current.network.elements)[1]

        marker_buffers = buffers[marker_model]

        # from snngine_v4.visualization.cuda.gl_interop.gl_tensor import \
        #     GLVBOTensor
        # tensor = GLVBOTensor(
        #     opengl_id=marker_buffers['vbo'],
        #     shape=(len(marker_model.pos), 14
        #            # self._config.technical.vispy_scatter_plot_stride
        #            ),
        #     device=0)
        # a = tensor.tensor
        # data = self.conf.current.model_dump(mode=ModelDumpTypes.only_arrays)

        return
