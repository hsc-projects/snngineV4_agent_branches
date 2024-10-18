from pyqtgraph.parametertree import Parameter
from vispy.scene import TurntableCamera, XYZAxis
from vispy.visuals import BoxVisual, CompoundVisual, MeshVisual

from snngine_v4.geometry.grid_config import FiniteGridConfig

from snngine_v4.gui.parameter_tree.connectors.model_parameter_links import (
    ModelParameterLinks, ObjectParameterLink,
)
from snngine_v4.gui.parameter_tree.connectors.model_signals_register import \
    ModelSignalsRegister
from snngine_v4.gui.parameter_tree.connectors.object2vispy_object_link import \
    VispyLinks
from snngine_v4.gui.parameter_tree.connectors.parameter_connector import \
    ParameterConnector
from snngine_v4.gui.parameter_tree.engine_parameter_tree import \
    EngineParameterTree
from snngine_v4.utils.containers.mappings import (
    Int2ObjectMapConfig, Model2ObjectMap,
    Object2ObjectMap,
)
from snngine_v4.utils.field_utils import model_keys, Undefined
from snngine_v4.visualization.config_models.visuals.box_configs import \
    BoxVisualInitConfig
from snngine_v4.visualization.visual_builder import (
    VispyVisualBuilder,
)


class VispyConnector(ParameterConnector):

    class ContainerConfigClass(Int2ObjectMapConfig, frozen=True):
        b_pop_allowed: bool = True

    @classmethod
    def cls_connect_map(cls, **kwargs):
        container: Model2ObjectMap = super().cls_connect_map(**kwargs)
        pop_keys = []
        for k, v in container.items():
            if isinstance(v, VispyLinks) and (v.source != container.inv[v]):
                pop_keys.append(k)
        for k in pop_keys:
            v = container.pop(k)
            container[v.source] = v
        return container

    @classmethod
    def connect_object(cls, model, obj,
                       signal_register: ModelSignalsRegister):
        vispy_links = VispyLinks(model, obj, signal_register)
        return vispy_links

    @classmethod
    def cls_connect_tree(cls, tree: EngineParameterTree, scene_manager,
                         container=None):
        sr: ModelSignalsRegister = tree.signal_register

        extra_models = list(sr.model2model_map.values())
        container = super().cls_connect_tree(
            tree=tree, scene_manager=scene_manager,
            container=container)
        new_models = [x for x in sr.model2model_map.values() if x not in
                      extra_models]
        new_model_node_trees = sr.model2nodetree_map.get_unique_values(
            *new_models)

        for node_tree in new_model_node_trees:
            # new_model = CompoundVisualNodeConfig(
            #     initialization=node_tree.root)
            model = node_tree.root
            new_pars = tree.add_parameters_from_model(
                model=model, root=sr.get_group(model),
                name='Visual', signal_register=sr,
                exclude_keys=model_keys(sr.model2model_map.inv[model])
            )
            if isinstance(model, BoxVisualInitConfig):
                new_pars.setName(name=BoxVisual.__name__)
                sv: Parameter = new_pars.param(VispyVisualBuilder.SUBVISUALS_KW)
                vispy_links: VispyLinks = container[sr.group_map.inv[new_pars]]
                for i, (name, param) in enumerate(sv.names.items()):
                    subvisual_model = sr.group_map.inv[param]
                    subvisual = vispy_links.sub_visual_map[subvisual_model]
                    new_links = VispyLinks(subvisual_model, subvisual,
                                           signal_register=sr)
                    # model_links: list[ObjectParameterLink] = (
                    #     sr[subvisual_model][ObjectParameterLink].refs)
                    # vispy_links.add_links(
                    #     func=vispy_links.update_object, links=model_links)


        return
