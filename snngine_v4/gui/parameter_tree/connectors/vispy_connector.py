from typing import Callable

import numpy as np
from pydantic import BaseModel

from vispy.scene import Box, TurntableCamera, XYZAxis
from vispy.visuals import BaseVisual, CompoundVisual, MeshVisual

from snngine_v4.data.validation.array_annotation import ArrayInterfaces
from snngine_v4.geometry.grid.finite_grid import FiniteGrid
from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.geometry.spatial_pars import Ax3D
from snngine_v4.gui.parameter_tree.connectors.basemodel_signal_register import (
    ModelSignalRegister,
)
from snngine_v4.gui.parameter_tree.connectors.model_parameter_links import (
    ModelParameterLinks, ObjectParameterLink,
)
from snngine_v4.gui.parameter_tree.connectors.object2object_links import \
    LinkStateType

from snngine_v4.gui.parameter_tree.connectors.parameter_connector import \
    ParameterConnector
from snngine_v4.gui.parameter_tree.engine_parameter_tree import \
    EngineParameterTree
from snngine_v4.visualization.buffer_utils import adapt_dim

from snngine_v4.visualization.config_models.vispy_camera_configs import \
    TurnTableCameraParameters
from snngine_v4.visualization.config_models.vispy_visual_parameters import \
    RGBAColor
from snngine_v4.visualization.config_models.visual_configs import (
    BoxVisualConfig, XYZAxisVisualConfig,
)

from snngine_v4.visualization.scenes.event_camera import (
    EventCameraMixin,
)
from snngine_v4.visualization.scenes.setattribute_event import (
    Set3DAttributeEvent, SetAttributeEvent,
)
from snngine_v4.visualization.visual_builder import (
    VispyVisualBuilder,
    VisualMixins,
)


class VispyConnector(ParameterConnector):

    SET_DATA_KWS = {
        XYZAxis: ['color', 'pos', 'connect', 'width'],
        MeshVisual: ['vertices', 'faces', 'vertex_colors',
                     'face_colors', 'color', 'vertex_values',
                     'meshdata']
    }

    @classmethod
    def adapt_condition(cls, arr0, arr1):
        if ((not ArrayInterfaces().D2.b_is_valid_np(arr0))
                or (not ArrayInterfaces().D2.b_is_valid_np(arr1))):
            return False
        return arr0.shape[0] != arr1.shape[0]

    @classmethod
    def connect_object(cls, model, obj,
                       signal_register: ModelSignalRegister):

        model_signals: ModelParameterLinks = signal_register[model]
        links: list[ObjectParameterLink] = model_signals[
            ObjectParameterLink].refs

        def update_object(link_, key, value):
            cls.update_object(obj, key, value, update_model)

        def update_model(event: SetAttributeEvent):
            cls.update_model(event=event, model_signals=model_signals,
                             block=update_object)

        if isinstance(obj, (EventCameraMixin, TurntableCamera)):
            assert isinstance(model, TurnTableCameraParameters)

            center_signals: ModelParameterLinks = signal_register[
                model.center]

            center_parameters = {
                x.name: center_signals[str][x.name].sink
                for x in Ax3D
            }

            def update_camera_object(model_: BaseModel, key, value):
                if model_ == model.center:
                    key = 'center'
                    value = (
                        center_parameters[Ax3D.X.name].value(),
                        center_parameters[Ax3D.Y.name].value(),
                        center_parameters[Ax3D.Z.name].value(),
                    )
                block = update_camera_model
                if key == EventCameraMixin.Slots.CENTER:
                    obj.events.center_changed.disconnect(block)
                else:
                    obj.events.attr_changed.disconnect(block)
                try:
                    setattr(obj, key, value)
                except TypeError:
                    if value is None:
                        setattr(obj, key, np.nan)
                    else:
                        raise
                if key == EventCameraMixin.Slots.CENTER:
                    obj.events.center_changed.connect(block)
                else:
                    obj.events.attr_changed.connect(block)

            def update_camera_model(
                    event: SetAttributeEvent,
                    block: Callable | None = update_camera_object):
                if event.key == EventCameraMixin.Slots.CENTER:
                    signals_ = center_signals
                else:
                    signals_ = model_signals
                cls.update_model(
                    event=event, model_signals=signals_,
                    block=block)

            obj.events.attr_changed.connect(update_camera_model)
            obj.events.center_changed.connect(update_camera_model)

            for link in links:

                ev = SetAttributeEvent(
                    key=link.key, value=getattr(obj, link.key))
                update_camera_model(ev, None)

                link[LinkStateType.SOURCE2SINK].set_connect(
                    value=True, func=update_camera_object)

            center_links: list[ObjectParameterLink] = (
                center_signals[ObjectParameterLink].refs)

            for link in center_links:
                link[LinkStateType.SOURCE2SINK].connect(
                    func=update_camera_object)

        elif isinstance(obj, XYZAxis):
            assert isinstance(model, XYZAxisVisualConfig)
            obj.events.attr_changed.connect(update_model)
            for link in links:
                link[LinkStateType.SOURCE2SINK].connect(update_object)
            obj.__setattr__('antialias', True)
            obj.antialias = True
            pass

        elif isinstance(obj, CompoundVisual):
            exp_model = VispyVisualBuilder.get_model(model)
            if model.__class__ != exp_model.__class__:
                assert isinstance(model, FiniteGridConfig)
                new_model = exp_model
                signal_register.make_model2model_links(model, new_model)
                # model.__setattr__(model, 'seg', (1, 2, 3))
                pass
            # assert isinstance(model, BoxVisualConfig)
            # for sub_visual in obj._subvisuals:
            #     cls.connect_object(
            #         model, sub_visual,
            #         signal_register)

        elif isinstance(obj, MeshVisual):
            assert isinstance(model, BoxVisualConfig)
            obj.events.attr_changed.connect(update_model)
            for link in links:
                link[LinkStateType.SOURCE2SINK].connect(update_object)

        return

    @classmethod
    def connect_tree(cls, tree: EngineParameterTree, scene_manager):
        model2model_map = tree.signal_register.model2model_map
        extra_models = list(model2model_map.values())
        super().connect_tree(tree=tree, scene_manager=scene_manager)
        new_models = [x for x in model2model_map.values() if x not in
                      extra_models]
        new_trees = tree.signal_register.model2nodetree_map.get_unique_values(
            *new_models
        )

        return

    @classmethod
    def handle_set_data_kwargs(cls, obj, key, value):
        kwargs = {key: value}
        if isinstance(obj, XYZAxis):
            if ((key == 'width')
                    or ((key == 'connect') and isinstance(value, str))):
                return kwargs
            if key == 'color':
                if isinstance(kwargs[key], (tuple, dict)):
                    kwargs[key] = RGBAColor.to_vispy(kwargs[key])
                other_key = 'pos'
            else:
                other_key = 'color'
            if cls.adapt_condition(
                    kwargs[key], other := getattr(obj, other_key)):
                kwargs[other_key] = adapt_dim(other, ref=kwargs[key])
                # cls.update_model()
        return kwargs

    @classmethod
    def update_model(cls, event: SetAttributeEvent,
                     model_signals: ModelParameterLinks, block):
        if isinstance(event, Set3DAttributeEvent):
            for ax in Ax3D:
                try:
                    link = model_signals[str][ax.name]
                    cls.update_model_attribute(
                        link, ax.name, event.value[ax.value], block)
                except KeyError:
                    raise

        elif isinstance(event, SetAttributeEvent):
            try:
                link = model_signals[str][event.key]
            except KeyError:
                raise
            cls.update_model_attribute(link, event.key, event.value, block)
        # elif event.type == 'update':
        #
        #     source: BaseVisual = event.source
        #     if isinstance(source, TurntableCamera):
        #         model: BaseModel = model_signals.model
        #         for link, p in model_signals.pairs():
        #             value = getattr(source, link.key)
        #             if not isinstance(value, np.ndarray):
        #                 if getattr(model, link.key) != value:
        #                     cls.update_model_attribute(
        #                         link, link.key, value, block)

    @classmethod
    def update_model_attribute(
            cls, link: ObjectParameterLink, key, value, block):
        if block:
            link[LinkStateType.SOURCE2SINK].disconnect(block)
        link[LinkStateType.SOURCE2SINK](
            link.source, key, value, b_block=False)
        if block:
            link[LinkStateType.SOURCE2SINK].connect(block)

    @classmethod
    def update_object(cls,  obj: XYZAxis, key, value, block):
        obj.events.update.disconnect(block)
        new_kwargs = {}
        if ((type(obj) in cls.SET_DATA_KWS)
                and (key in cls.SET_DATA_KWS[type(obj)])):
            new_kwargs = cls.handle_set_data_kwargs(obj, key, value)
            obj.set_data(**new_kwargs)
        else:
            setattr(obj, key, value)
        obj.events.update.connect(block)
        if len(new_kwargs) > 1:
            for k, v in new_kwargs.items():
                if k != key:
                    obj.events.attr_changed(key=k, value=v)
