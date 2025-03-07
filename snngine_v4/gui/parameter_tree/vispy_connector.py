from pyqtgraph.parametertree import Parameter
from vispy.visuals import BoxVisual, MarkersVisual

from snngine_v4.geometry.spatial_pars import EnginePos3D
from snngine_v4.gui.parameter_tree.connectors.model_signals_register import \
    ExtendedModelSignalsRegister
from snngine_v4.gui.parameter_tree.connectors.vispy_links import \
    VispyLinks
from snngine_v4.gui.parameter_tree.connectors.parameter_connector import \
    ParameterConnector
from snngine_v4.gui.parameter_tree.engine_parameter_tree import \
    EngineParameterTree
from snngine_v4.utils.containers.mappings import (
    ObjectMapConfig, Model2ObjectMap,
)
from snngine_v4.utils.field_utils import model_keys
from snngine_v4.visualization.config_models.visuals import MarkersVisualConfig
from snngine_v4.visualization.config_models.visuals.boxes import (
    BoxVisualInitConfig, OuterGridVisualInitConfig,
)
from snngine_v4.visualization.config_models.visuals.parameters import \
    VispyKeyWords
from snngine_v4.visualization.visual_builder import (
    VispyVisualBuilder,
)


class VispyConnector(ParameterConnector):

    class ContainerConfigClass(ObjectMapConfig, frozen=True):
        b_pop_allowed: bool = True

    @classmethod
    def cls_connect_map(cls, **kwargs):

        container: Model2ObjectMap = super().cls_connect_map(**kwargs)
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
                       model_signals=None):
        return VispyLinks(
            model=model, vispy_obj=obj, signal_register=signal_register,
            model_signals=model_signals)

    @classmethod
    def cls_connect_tree(cls, tree: EngineParameterTree, scene_manager,
                         container=None, **kwargs):
        sr: ExtendedModelSignalsRegister = tree.signal_register

        extra_models = list(sr.model2model_map.values())
        models = tree.signal_register.connected_models
        mapping = scene_manager.get_built_objects(*models)
        # mapping = scene_manager.get_visual_nodes()
        container = super().cls_connect_tree(
            tree=tree, mapping=mapping, container=container)

        new_models = [x for x in sr.model2model_map.values() if x not in
                      extra_models]
        if len(new_models) > 0:
            new_model_node_trees = sr.model2nodetree_map.values(
                *new_models, b_unique=True)

            for node_tree in new_model_node_trees:
                # new_model = CompoundVisualNodeConfig(
                #     initialization=node_tree.root)
                model = node_tree.root
                exclude_keys = []
                if isinstance(model, BoxVisualInitConfig):
                    exclude_keys += model_keys(sr.model2model_map.inv[model])
                    exclude_keys += [VispyKeyWords.COLOR,
                                     VispyKeyWords.VERTEX_COLORS,
                                     VispyKeyWords.FACE_COLORS,
                                     VispyKeyWords.EDGE_COLOR,
                                     EnginePos3D.Slots.POS_ORIGIN]
                elif isinstance(model, MarkersVisualConfig):
                    exclude_keys += [VispyKeyWords.POS,
                                     EnginePos3D.Slots.POS_ORIGIN
                                     ]

                new_pars = tree.add_parameters_from_model(
                    model=model,
                    root=sr.get_group(sr.model2model_map.inv[model]),
                    name='Visual', signal_register=sr,
                    exclude_keys=exclude_keys
                )

                new_names = {}
                visual_conf = sr.get_model(new_pars)
                vispy_links: VispyLinks = container[visual_conf]
                if isinstance(model, BoxVisualInitConfig):
                    if isinstance(model, OuterGridVisualInitConfig):
                        new_pars.setName(name='Visual')
                    else:
                        new_pars.setName(name=BoxVisual.__name__)
                    sv: Parameter = new_pars.param(
                        VispyVisualBuilder.SUBVISUALS_KW)

                    for i, (name, param) in enumerate(sv.names.items()):
                        subvisual_model = sr.get_model(param)
                        subvisual = vispy_links.sub_visual_map[subvisual_model]
                        if subvisual == vispy_links.sink.mesh:
                            new_names[VispyKeyWords.MESH] = param
                        elif subvisual == vispy_links.sink.border:
                            new_names[VispyKeyWords.BORDER] = param
                        # elif subvisual == vispy_links.sink.border:
                        #     new_names[VispyKeyWords.BORDER] = param
                        new_links = VispyLinks(subvisual_model, subvisual,
                                               signal_register=sr)
                elif isinstance(model, MarkersVisualConfig):
                    new_pars.setName(name=MarkersVisual.__name__)
                    visual_model = sr.get_model(new_pars)
                    visual = vispy_links.sink
                    new_links = VispyLinks(
                        visual_model, visual,
                        model_signals=sr.extensions_map[visual_model],
                        signal_register=sr)
                for k, v in new_names.items():
                    v.setName(name=k)
            return
