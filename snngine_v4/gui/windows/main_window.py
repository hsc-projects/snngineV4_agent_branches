from typing import ClassVar

from qtpy import QtCore, QtWidgets

from snngine_v4.gui.common.qobject_dicts import QWidgetDict

from snngine_v4.gui.parameter_tree.vispy_connector import \
    VispyConnector
from snngine_v4.gui.parameter_tree.parameters.widgets.table \
    .array_editor import ArrayEditorDockWidget
from snngine_v4.gui.windows.settings_window import SettingsWindow

from snngine_v4.snngine import SNNgine
from snngine_v4.gui.windows.main_window_base import (
    MainEngineWindowBase,
    WindowTypes,
)
from snngine_v4.gui.parameter_tree.engine_parameter_tree import (
    EngineTreeDockWidget,
)
from snngine_v4.gui.parameter_tree.cuda_connector import (
    CudaConnector,
    CudaVispyConnector,
)


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
        new_visuals = self.engine.build_network()
        self.update_connections()

        # marker_visual = new_visuals[
        #     self.engine.conf.current.network.elements[1]].built
        # marker_visual.visible = False

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

        current_model = self.engine.network_manager.container_model

        self.network_tree.clear()
        self.network_tree.set_parameters_from_model(
            model=current_model,
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

        model2buffers = CudaVispyConnector.cls_connect_tree(
            tree=self.network_tree, scene_manager=self.engine.scene_manager,
            device=current_model.network.device)

        model2tensors = CudaConnector.cls_connect_tree(
            tree=self.network_tree,
            network_manager=self.engine.network_manager,)

        # reservoir_model: NetworkReservoirConfig = (
        #     self.engine.conf.current.network.elements)[1]
        # reservoir_p = sr.get_group(reservoir_model)
        #
        # spnn = self.engine.network_manager[current_model.network]
        #
        # reservoir = spnn[reservoir_model]
        #
        # # marker_buffers = buffers[reservoir_model]
        # flag_slot = NetworkReservoirConfig.Slots.L_GROUP_FLAGS
        # g_flag_model = reservoir_model.L_Group2Group_flags
        #
        # g_flag_p = sr[reservoir_model].sink.child(flag_slot)
        #
        # for c in reservoir_p.childs:
        #     if isinstance(c, TensorParameter):
        #         c.tensor = reservoir.tensor_dict[c.name()]
        #     elif isinstance(c, TensorDictParameter):
        #         c.set_tensor(reservoir.tensor_dict[c.name()])
        return
