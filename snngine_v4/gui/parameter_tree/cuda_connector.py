from typing import Type

from pydantic import BaseModel
from pyqtgraph.parametertree.parameterTypes import GroupParameter
from vispy.gloo import get_current_canvas
from vispy.visuals import MarkersVisual, Visual

from snngine_v4.gui.parameter_tree.connectors.model_signals_register import \
    ExtendedModelSignalsRegister
from snngine_v4.gui.parameter_tree.connectors.parameter_connector import \
    ParameterConnector
from snngine_v4.gui.parameter_tree.engine_parameter_tree import \
    EngineParameterTree
from snngine_v4.gui.parameter_tree.parameters.tensor_parameter import (
    TensorDictParameter, TensorParameter,
)
from snngine_v4.nn.engine_element import EngineElement
from snngine_v4.nn.nn_builder import NetworkManager
from snngine_v4.utils.containers.mappings import (
    Int2ObjectMapConfig, Object2ObjectMap, SurjectiveMap,
)
from snngine_v4.visualization.cuda.gl_interop.gl_tensor import (
    GLVBOTensor,
)
from snngine_v4.visualization.cuda.gl_interop.gl_tensor_dict import (
    GLTensorDict)
from snngine_v4.visualization.scenes.main_network_scene import (
    EngineSceneCanvas)
from snngine_v4.visualization.scenes.scene_manager import (
    SceneManager)


class CudaConnector(ParameterConnector):
    @classmethod
    def connect_object(cls, model: EngineElement,
                       obj: GroupParameter,
                       signal_register: ExtendedModelSignalsRegister,
                       **kwargs):
        res = {}
        for c in obj.childs:
            if isinstance(c, (TensorParameter, TensorDictParameter)):
                name = c.name()
                tensor = model.tensor_dict[c.name()]
                if isinstance(c, TensorParameter):
                    c.tensor = tensor
                elif isinstance(c, TensorDictParameter):
                    c.set_tensor(tensor)
                else:
                    raise TypeError
                res[name] = tensor
        return res

    @classmethod
    def cls_connect_tree(cls, tree: EngineParameterTree,
                         network_manager: NetworkManager,
                         container=None,
                         **kwargs):
        sr = tree.signal_register
        network_model = network_manager.container_model.network
        network = network_manager[network_model]
        mapping = cls.make_container()
        for m in network_model.elements:
            mapping[network[m]] = sr.get_group(m)
        return super().cls_connect_tree(tree, mapping, container, **kwargs)

    @classmethod
    def make_container(cls):
        return Object2ObjectMap(container_conf=cls.cls_make_container_conf())


class CudaVispyConnector(ParameterConnector):

    class ContainerConfigClass(Int2ObjectMapConfig, frozen=True):
        allowed_types: Type[GLTensorDict] = GLTensorDict

    @classmethod
    def connect_object(cls, model: BaseModel, obj: Visual,
                       signal_register: ExtendedModelSignalsRegister,
                       **kwargs):
        device = kwargs.pop('device')
        res = GLTensorDict()
        if isinstance(obj, MarkersVisual):
            # noinspection PyProtectedMember
            gl_id = cls.gl_buffer_id(obj._vbo.id)
            # noinspection PyProtectedMember
            gl_tensor = GLVBOTensor(
                opengl_id=gl_id,
                shape=(len(model.pos), obj._data.dtype.itemsize // 4),
                device=device, **kwargs)
            res['vbo'] = gl_tensor
            print(gl_tensor)
        else:
            pass
            # raise NotImplementedError
        return res

    @classmethod
    def cls_connect_map(cls, scene: EngineSceneCanvas,
                        signal_register: ExtendedModelSignalsRegister,
                        container=None, **kwargs):
        device = kwargs.pop('device')
        if container is None:
            container = cls.make_container()
        if isinstance(scene, EngineSceneCanvas):
            scene.set_current()
            # noinspection PyProtectedMember
            # scene._draw_scene()
            scene.on_draw(None)
            mapping = scene.visual_node_dict
        else:
            raise NotImplementedError
        container = super().cls_connect_map(
            mapping=mapping, signal_register=signal_register,
            container=container,
            device=device, **kwargs)
        return container

    @classmethod
    def cls_connect_tree(cls, tree: EngineParameterTree,
                         scene_manager: SceneManager,
                         container=None, **kwargs):
        device = kwargs.pop('device')
        if container is None:
            container = cls.make_container()

        sr = tree.signal_register

        t_dict2scene_map = SurjectiveMap()

        for scene in scene_manager.values():
            scene_container = cls.cls_connect_map(
                scene=scene, signal_register=sr, device=device, **kwargs)
            for model, t_dct in scene_container.pairs():
                t_dict2scene_map[t_dct] = scene
            container.update(scene_container)

        for model, t_dct in container.pairs():

            if model in sr:
                p = TensorDictParameter(value=t_dct, signal_register=sr)
                tree.addParameters(root=sr.get_group(model), param=p)
                scene: EngineSceneCanvas = t_dict2scene_map[t_dct]

                def update_scene(*arg, **kwargs_):
                    scene.update()

                p.sigValueChanged.connect(update_scene)

        return container

    @staticmethod
    def gl_buffer_id(glir_id):
        # noinspection PyProtectedMember
        return int(get_current_canvas().context.shared.parser._objects[glir_id]
                   .handle)
