from __future__ import annotations

import numpy as np
from pydantic import BaseModel
from vispy.scene import TurntableCamera, VisualNode, XYZAxis
from vispy.util.event import Event
from vispy.visuals import BoxVisual, CompoundVisual, LineVisual, MeshVisual

from snngine_v4.data.validation.array_annotation import ArrayInterfaces
from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.geometry.spatial_pars import Ax3D
from snngine_v4.gui.parameter_tree.connectors.model_parameter_links import (
    ModelParameterLinks, ObjectParameterLink,
)
from snngine_v4.gui.parameter_tree.connectors.model_signals_register import \
    ModelSignalsRegister
from snngine_v4.gui.parameter_tree.connectors.object2object_links import (
    LinkStateType, Object2ObjectLinks,
)
from snngine_v4.utils.containers.mappings import Model2ObjectMap
from snngine_v4.utils.field_utils import Undefined
# from snngine_v4.utils.settings.ui_parameter_options import update_param_opts
from snngine_v4.visualization.buffer_utils import adapt_dim
from snngine_v4.visualization.config_models.vispy_camera_configs import (
    CameraCenter, TurnTableCameraParameters,
)
from snngine_v4.visualization.config_models.visuals.box_configs import \
    BoxVisualInitConfig

from snngine_v4.visualization.config_models.visuals.line_configs import \
    XYZAxisVisualConfig
from snngine_v4.visualization.config_models.visuals.mesh_visual_config import \
    MeshVisualConfig
from snngine_v4.visualization.config_models.visuals.visual_parameters import \
    RGBAColor
from snngine_v4.visualization.scenes.event_camera import EventCameraMixin
from snngine_v4.visualization.scenes.setattribute_event import (
    MeshDataChangedEvent, Set3DAttributeEvent, SetAttributeEvent,
)
from snngine_v4.visualization.visual_builder import (
    VispyVisualBuilder,
    VisualMixin,
)


type VispyObject = (VisualNode | VisualMixin | LineVisual | BoxVisual
                    | EventCameraMixin | TurntableCamera)


type VispyObjectConfig = TurnTableCameraParameters


class VispyLinks(Object2ObjectLinks):

    SET_DATA_KWS = {
        XYZAxis: ['color', 'pos', 'connect', 'width'],
        MeshVisual: ['vertices', 'faces', 'vertex_colors',
                     'face_colors', 'vertex_values',
                     'meshdata']
    }

    def add_links(self, func, links=None):
        if links is None:
            links = self.model_links
        for link in links:
            link[LinkStateType.SOURCE2SINK].connect(func)
            self[link.source_key] = link

    @property
    def model_links(self):
        return self.model_signals[ObjectParameterLink].refs

    def __init__(self, model, vispy_obj,
                 signal_register: ModelSignalsRegister, **kwargs):
        self.data: dict[int | BaseModel, VispyObject] | None = None
        self.source: VispyObjectConfig | None = None
        self.sink: VispyObject | None = None

        self.sub_visual_map = Model2ObjectMap()

        node_tree = None
        if isinstance(vispy_obj, CompoundVisual):
            exp_model = VispyVisualBuilder.get_model(model)
            if model.__class__ != exp_model.__class__:
                assert isinstance(model, FiniteGridConfig)
                node_tree = signal_register.make_model2model_links(
                    model, exp_model)
                model = exp_model
                # model.__setattr__(model, 'seg', (1, 2, 3))
                pass

        super().__init__(source=model, sink=vispy_obj, **kwargs)

        self.model_signals: ModelParameterLinks = signal_register[self.source]
        self.center_signals = None
        if isinstance(self.source, TurnTableCameraParameters):
            self.center_signals: ModelParameterLinks = signal_register[
                self.source.center]

        if isinstance(self.sink, (EventCameraMixin, TurntableCamera)):
            assert isinstance(self.source, TurnTableCameraParameters)
            self.sink.events.attr_changed.connect(self.update_model)
            self.sink.events.center_changed.connect(self.update_model)
            self.add_links(self.update_camera_object)
            for link in self.model_links:
                ev = SetAttributeEvent(
                    key=link.source_key,
                    value=getattr(self.sink, link.source_key))
                self.update_model(ev)
            center_links: list[ObjectParameterLink] = (
                self.center_signals[ObjectParameterLink].refs)
            self.add_links(self.update_camera_object, center_links)

        elif isinstance(self.sink, XYZAxis):
            if type(self.sink) not in self.SET_DATA_KWS:
                self.SET_DATA_KWS[type(self.sink)] = self.SET_DATA_KWS[XYZAxis]
            assert isinstance(self.source, XYZAxisVisualConfig)
            self.sink.events.attr_changed.connect(self.update_model)
            self.add_links(self.update_object)
            self.sink.__setattr__('antialias', True)
            self.sink.antialias = True
            pass

        elif isinstance(self.sink, CompoundVisual):
            assert isinstance(self.source, BoxVisualInitConfig)
            assert isinstance(self.sink, BoxVisual)
            # if type(self.sink) not in self.SET_DATA_KWS:
            #     if isinstance(self.sink, BoxVisual):
            #         self.SET_DATA_KWS[type(self.sink)] =
            #         self.SET_DATA_KWS[BoxVisual]
            color = 'blue'
            # noinspection PyProtectedMember
            if len(self.sink._subvisuals) > 0:
                # sub_visuals_model = SubVisualsConfig()
                self.source.subvisuals = []
                # noinspection PyProtectedMember
                for sub_visual in self.sink._subvisuals:

                    if isinstance(sub_visual, MeshVisual):
                        sub_visual_model = MeshVisualConfig()
                    else:
                        raise NotImplementedError
                    self.sub_visual_map[sub_visual_model] = sub_visual
                    # if isinstance(self.source, BoxVisualInitConfig):
                    #     if sub_visual == self.sink.mesh:
                    #         update_param_opts(sub_visual_model, name='mesh')
                    #     elif sub_visual == self.sink.border:
                    #         update_param_opts(sub_visual_model, name='border')

                    self.source.subvisuals.append(
                        sub_visual_model)
                    # self.connect_mesh_visual(
                    #     obj=sub_visual, model=sub_visual_model)
                    # sub_visual.color = color
                    color = 'red'
            node_tree.read_model(self.source, b_ignore_existing=True)

        elif isinstance(self.sink, MeshVisual):
            self.connect_mesh_visual(self.sink, self.source,
                                     sr=signal_register)

    @classmethod
    def adapt_condition(cls, arr0, arr1):
        if ((not ArrayInterfaces().D2.b_is_valid_np(arr0))
                or (not ArrayInterfaces().D2.b_is_valid_np(arr1))):
            return False
        return arr0.shape[0] != arr1.shape[0]

    def connect_mesh_visual(self, obj, model, sr: ModelSignalsRegister = None):
        if type(obj) not in self.SET_DATA_KWS:
            self.SET_DATA_KWS[type(obj)] = self.SET_DATA_KWS[MeshVisual]
        assert isinstance(model, MeshVisualConfig)
        # obj.events.attr_changed.connect(update_model)
        print('connect MeshVisual', id(obj))
        obj.events.mesh_data_changed.connect(self.update_model)
        if sr is not None:
            model_links: list[ObjectParameterLink] = (
                sr[model][ObjectParameterLink].refs)
            self.add_links(func=self.update_object, links=model_links)

    @classmethod
    def cls_update_model(
            cls, event: Event,
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
        elif isinstance(event, MeshDataChangedEvent):
            pass
        # elif event.type == 'update':
        #     source: BaseVisual = event.source
        #     if isinstance(source, TurntableCamera):
        #         model: BaseModel = model_signals.model
        #         for link, p in model_signals.pairs():
        #             value = getattr(source, link.key)
        #             if not isinstance(value, np.ndarray):
        #                 if getattr(model, link.key) != value:
        #                     cls.update_model_attribute(
        #                         link, link.key, value, block)

    def prepare_object(self, obj, link_type: LinkStateType,
                       debug_catch=BaseException):
        raise NotImplementedError

    @classmethod
    def handle_set_data_kwargs(cls, obj, key, value):
        kwargs = {key: value}

        if key == 'color':
            if isinstance(kwargs[key], (tuple, dict)):
                kwargs[key] = RGBAColor.to_vispy(kwargs[key])

        if isinstance(obj, XYZAxis):
            if ((key == 'width')
                    or ((key == 'connect') and isinstance(value, str))):
                return kwargs
            if key == 'color':
                other_key = 'pos'
            else:
                other_key = 'color'
            if cls.adapt_condition(
                    kwargs[key], other := getattr(obj, other_key)):
                kwargs[other_key] = adapt_dim(other, ref=kwargs[key])
        return kwargs

    def update_camera_object(
            self, model_: VispyObjectConfig | CameraCenter,
            key, value, block=Undefined):
        if model_ == self.source.center:
            key = 'center'
            value = model_
            event_block = self.sink.events.center_changed
        else:
            event_block = self.sink.events.attr_changed
        try:
            self.update_object(model_, key, value, event_block, block)
        except TypeError:
            if value is None:
                self.update_object(model_, key, np.nan, event_block, block)
            else:
                raise

    def update_model(self, event: Event | SetAttributeEvent, block=Undefined):
        if isinstance(self.sink, EventCameraMixin):
            if block is Undefined:
                block = self.update_camera_object
            if event.key == EventCameraMixin.Slots.CENTER:
                signals_ = self.center_signals
            else:
                signals_ = self.model_signals
        else:
            signals_ = self.model_signals
            if block is Undefined:
                block = self.update_object
        self.cls_update_model(
            event=event, model_signals=signals_,
            block=block)

    @classmethod
    def update_model_attribute(
            cls, link: ObjectParameterLink, key, value, block):
        if block:
            link[LinkStateType.SOURCE2SINK].disconnect(block)
        link[LinkStateType.SOURCE2SINK](
            link.source, key, value, b_block=False)
        if block:
            link[LinkStateType.SOURCE2SINK].connect(block)

    def update_object(self, model, key, value,
                      event_block=Undefined,
                      block=Undefined):
        if event_block is Undefined:
            event_block = self.sink.events.attr_changed
        if block is Undefined:
            block = self.update_model
        event_block.disconnect(block)
        new_kwargs = {}
        if ((type(self.sink) in self.SET_DATA_KWS)
                and (key in self.SET_DATA_KWS[type(self.sink)])):
            new_kwargs = self.handle_set_data_kwargs(self.sink, key, value)
            self.sink.set_data(**new_kwargs)
        else:
            if key == 'color':
                if isinstance(value, (tuple, dict)):
                    value = RGBAColor.to_vispy(value)
            setattr(self.sink, key, value)

        event_block.connect(block)
        if len(new_kwargs) > 1:
            for k, v in new_kwargs.items():
                if k != key:
                    event_block(key=k, value=v)
