from enum import IntEnum, auto
from typing import Type

from pydantic import BaseModel
from vispy.gloo import get_current_canvas
from vispy.visuals import LineVisual, MarkersVisual, Visual
from vispy.visuals.line.line import _GLLineVisual

from snngine_v4.gui.parameter_tree.connectors.model_signals_register import \
    ExtendedModelSignalsRegister
from snngine_v4.gui.parameter_tree.connectors.parameter_connector import \
    ParameterConnector
from snngine_v4.gui.parameter_tree.engine_parameter_tree import \
    EngineParameterTree
from snngine_v4.gui.parameter_tree.parameters.array.tensor_parameter import (
    TensorDictParameter,
)
from snngine_v4.utils.containers.mappings import (
    ObjectMapConfig, Many2OneObjectMap,
)
from snngine_v4.visualization.config_models.plotting.multi_line_plot import \
    MultiLinePlotConfig
from snngine_v4.visualization.cuda.gl_interop.gl_tensor import (
    GLBufferTensor, GLVBOTensor,
)
from snngine_v4.visualization.cuda.gl_interop.gl_tensor_dict import (
    GLTensorDict)
from snngine_v4.visualization.scenes.main_network_scene import (
    EngineSceneCanvas)
from snngine_v4.visualization.scenes.scene_manager import (
    SceneManager)
from snngine_v4.visualization.visuals.compound_markers import \
    CompoundMarkersVisual


class GLBufferTypes(IntEnum):
    VBO = 0
    IBO = auto()
    POS_VBO = auto()
    CONNECT_IBO = auto()


class CudaVispyConnector(ParameterConnector):
    """

    """

    class ContainerConfigClass(ObjectMapConfig, frozen=True):
        allowed_types: Type[GLTensorDict] = GLTensorDict

    @classmethod
    def to_gl_buffer(cls,
                     buffer_type: GLBufferTypes,
                     device,
                     obj: Visual,
                     model: BaseModel,
                     **kwargs) -> GLBufferTensor:
        match buffer_type:
            case GLBufferTypes.POS_VBO:
                if isinstance(obj, (MarkersVisual,
                                    CompoundMarkersVisual)):
                    # noinspection PyProtectedMember
                    if isinstance(obj, CompoundMarkersVisual):
                        return cls.to_gl_buffer(
                            buffer_type=GLBufferTypes.POS_VBO,
                            device=device, obj=obj.markers_visual, model=model,
                            **kwargs
                        )
                    gl_id = cls.gl_buffer_id(obj._vbo.id)
                    # noinspection PyProtectedMember
                    return GLVBOTensor(
                        opengl_id=gl_id,
                        shape=(len(model.pos), obj._data.dtype.itemsize // 4),
                        device=device, **kwargs)
                    # print(gl_tensor)
                elif isinstance(obj, LineVisual):
                    if isinstance(model, MultiLinePlotConfig):
                        line_sub_visual: _GLLineVisual = obj._line_visual
                        pos_vbo_id = cls.gl_buffer_id(
                            line_sub_visual._pos_vbo.id)
                        return GLVBOTensor(
                            opengl_id=pos_vbo_id,
                            shape=(len(obj.pos), obj.pos.dtype.itemsize // 4),
                            device=device, **kwargs)
                    else:
                        raise NotImplementedError(
                            f"{obj.__class__.__name__}, "
                            f"{model.__class__.__name__}")
                else:
                    raise NotImplementedError(f"{obj.__class__.__name__}")
            case _:
                raise NotImplementedError(f"{buffer_type.name}")

    @classmethod
    def connect_object(cls, model: BaseModel, obj: Visual,
                       signal_register: ExtendedModelSignalsRegister,
                       **kwargs):
        device = kwargs.pop('device')
        res = GLTensorDict()

        if (isinstance(obj, (MarkersVisual, CompoundMarkersVisual))
                or (isinstance(obj, LineVisual)
                    and isinstance(model, MultiLinePlotConfig))):

            # noinspection PyProtectedMember
            gl_tensor = cls.to_gl_buffer(
                buffer_type=GLBufferTypes.POS_VBO,
                device=device, obj=obj, model=model, **kwargs)
            res[GLBufferTypes.POS_VBO.name] = gl_tensor
            # print(gl_tensor)
        # elif
        #         gl_tensor = cls.to_gl_buffer(
        #             buffer_type=GLBufferTypes.POS_VBO,
        #             device=device, obj=obj, model=model, **kwargs)
        #         res[GLBufferTypes.POS_VBO.name] = gl_tensor
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

        t_dict2scene_map = Many2OneObjectMap()

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
