from pydantic import BaseModel
from pyqtgraph.parametertree import Parameter
from vispy.visuals import BoxVisual, CompoundVisual, MarkersVisual

from snngine_v4.geometry.spatial_pars import EnginePos3D
from snngine_v4.gui.parameter_trees.connectors.model_signals_register import \
    ExtendedModelSignalsRegister
from snngine_v4.gui.parameter_trees.connectors.vispy_links import \
    VispyLinks
from snngine_v4.gui.parameter_trees.connectors.parameter_connector import \
    ParameterConnector
from snngine_v4.gui.parameter_trees.engine_parameter_tree import \
    EngineParameterTree
from snngine_v4.utils.containers.mappings import (
    Object2ObjectMap, ObjectMapConfig, Model2ObjectMap,
)
from snngine_v4.utils.field_utils import model_keys
from snngine_v4.visualization.config_models.visuals import MarkersVisualConfig
from snngine_v4.visualization.config_models.visuals.boxes import (
    BoxVisualInitConfig, OuterGridVisualInitConfig,
)
from snngine_v4.visualization.config_models.visuals.parameters import \
    VispyKeyWords
from snngine_v4.visualization.scenes.scene_manager import SceneManager, VispyMap


class VispyConnector(ParameterConnector):

    class ContainerConfigClass(ObjectMapConfig, frozen=True):
        b_pop_allowed: bool = True

    @classmethod
    def cls_connect_map(cls, mapping: Object2ObjectMap, **kwargs):

        container: Model2ObjectMap = super().cls_connect_map(
            mapping=mapping, **kwargs)

        # Handle linked models:
        # Replace linked model keys by the generated models
        replace_source_keys = []
        for k, v in container.items():
            if isinstance(v, VispyLinks) and (v.source != container.inv[v]):
                replace_source_keys.append(k)
        for k in replace_source_keys:
            v = container.pop(k)
            container[v.source] = v

        return container

    @classmethod
    def connect_object(cls, model, obj,
                       signal_register: ExtendedModelSignalsRegister,
                       sub_visual_super_map=None,
                       model_signals=None):

        if model in signal_register.model2model_map:
            model = signal_register.model2model_map[model]
        if isinstance(obj, CompoundVisual):
            sub_visual_map = sub_visual_super_map[model]
        else:
            sub_visual_map = None

        new_links = VispyLinks(
            model=model, vispy_obj=obj, signal_register=signal_register,
            sub_visual_map=sub_visual_map,
            model_signals=model_signals)

        return new_links

    @classmethod
    def _add_linked_model_parameters(
            cls, tree: EngineParameterTree,
            model0: BaseModel, model1: BaseModel):

        # sr: ExtendedModelSignalsRegister = tree.signal_register
        # sr.add_linked_model(model0=model0, model1=model1)
        if isinstance(model1, BoxVisualInitConfig):
            if isinstance(model1, OuterGridVisualInitConfig):
                name = 'OuterGridVisual'
            else:
                name = BoxVisual.__name__
            exclude_keys = model_keys(model0)
            exclude_keys += [VispyKeyWords.COLOR,
                             VispyKeyWords.VERTEX_COLORS,
                             VispyKeyWords.FACE_COLORS,
                             VispyKeyWords.EDGE_COLOR,
                             EnginePos3D.Slots.POS_ORIGIN]
        elif isinstance(model1, MarkersVisualConfig):
            name = MarkersVisual.__name__
            exclude_keys = [VispyKeyWords.POS,
                            EnginePos3D.Slots.POS_ORIGIN]
        else:
            exclude_keys = []
            name = 'Visual'

        new_pars = tree.add_parameters_from_linked_model(
            model0=model0, model1=model1,
            name=name, exclude_keys=exclude_keys
        )

        # visual_conf = sr.get_model(new_pars)
        # # vispy_links: VispyLinks = container[model1]
        #
        #     # cls._connect_subvisuals(
        #     #     model=model1, links=vispy_links, signal_register=sr)
        #     # # sv: Parameter = new_pars.param(
        #     # #     VispyVisualBuilder.SUBVISUALS_KW)
        #     # # for i, (name, param) in enumerate(sv.names.items()):
        #     # #     subvisual_model = sr.get_model(param)
        #     # #     subvisual = vispy_links.sub_visual_map[subvisual_model]
        #     # #     if subvisual == vispy_links.sink.mesh:
        #     # #         new_names[VispyKeyWords.MESH] = param
        #     # #     elif subvisual == vispy_links.sink.border:
        #     # #         new_names[VispyKeyWords.BORDER] = param
        #     # #     # elif subvisual == vispy_links.sink.border:
        #     # #     #     new_names[VispyKeyWords.BORDER] = param
        #     # #     new_links = VispyLinks(subvisual_model, subvisual,
        #     # #                            signal_register=sr)
        # elif isinstance(model1, MarkersVisualConfig):
        #     new_pars.setName()
        #     # visual_model = sr.get_model(new_pars)
        #     # # visual = vispy_links.sink
        #     # new_links = VispyLinks(
        #     #     visual_model, visual,
        #     #     model_signals=sr.extensions_map[visual_model],
        #     #     signal_register=sr)
        return new_pars

    @classmethod
    def cls_connect_tree(cls, tree: EngineParameterTree,
                         scene_manager: SceneManager,
                         container=None, **kwargs):
        sr: ExtendedModelSignalsRegister = tree.signal_register

        # extra_models = list(sr.model2model_map.values())
        models = tree.signal_register.connected_models
        mapping: VispyMap = scene_manager.get_built_objects(*models)

        for m in mapping.model2model_map.refs:
            cls._add_linked_model_parameters(
                tree, model0=m,
                model1=mapping.model2model_map[m])

        container = super().cls_connect_tree(
            tree=tree, mapping=mapping,
            sub_visual_super_map=mapping.sub_visual_super_map,
            container=container)

        # for m in mapping.sub_visual_super_map.refs:
        #     if m in mapping.model2model_map.values():
        #         cls._connect_subvisuals(
        #             model=m, links=None, signal_register=sr)

        # new_models = [x for x in sr.model2model_map.values() if x not in
        #               extra_models]
        # if len(new_models) > 0:
        #     new_model_node_trees = sr.model2nodetree_map.values(
        #         *new_models, b_unique=True)
        #
        #     for node_tree in new_model_node_trees:
        #         model = node_tree.root
        #         cls._add_linked_model_parameters(tree, container, model)
        #
        return container
