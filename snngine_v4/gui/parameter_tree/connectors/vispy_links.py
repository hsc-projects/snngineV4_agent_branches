from __future__ import annotations

import numpy as np
from pydantic import BaseModel
from vispy.scene import TurntableCamera, VisualNode, XYZAxis
from vispy.util.event import Event
from vispy.visuals import (
    BoxVisual, CompoundVisual, LineVisual, MarkersVisual,
    MeshVisual, Visual,
)
from vispy.visuals.transforms import STTransform

from snngine_v4.utils.data_utils.validation.array_annotation \
    import ArrayInterfaces
from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.geometry.spatial_pars import Ax3D, EnginePos3D
from snngine_v4.gui.parameter_tree.connectors.model_parameter_links import (
    ModelParameterLinks, ObjectParameterLink,
)
from snngine_v4.gui.parameter_tree.connectors.model_signals_register import \
    ExtendedModelSignalsRegister
from snngine_v4.gui.parameter_tree.connectors.object2object_links import (
    LinkStateType, Object2ObjectLinks,
)
from snngine_v4.nn.config_models.reservoir.nn_reservoir_config import \
    NetworkReservoirConfig
from snngine_v4.utils.containers.mappings import Model2ObjectMap
from snngine_v4.utils.field_utils import Undefined
# from snngine_v4.utils.settings.ui_parameter_options import update_param_opts
from snngine_v4.visualization.buffer_utils import adapt_dim
from snngine_v4.visualization.config_models.vispy_camera_configs import (
    CameraCenter, TurnTableCameraParameters,
)
from snngine_v4.visualization.config_models.visuals.boxes import \
    BoxVisualInitConfig
from snngine_v4.visualization.config_models.visuals.lines import (
    MultiBoxLinesVisualConfig, XYZAxisVisualConfig,
)
from snngine_v4.visualization.config_models.visuals.mesh import \
    MeshVisualConfig
from snngine_v4.visualization.config_models.visuals.parameters import (
    RGBAColor, VispyKeyWords,
)
from snngine_v4.visualization.scenes.event_camera import EventCameraMixin
from snngine_v4.visualization.scenes.setattribute_event import (
    MeshDataChangedEvent, Set3DAttributeEvent, SetAttributeEvent,
)
from snngine_v4.visualization.visual_builder import (
    VispyVisualBuilder,
    VisualMixin,
)
from snngine_v4.visualization.visuals.grid_lines import (
    GSGLLineVisual, FiniteGridLines,
    MultiBoxLinesVisual,
)

type VispyObject = (VisualNode | VisualMixin | LineVisual | BoxVisual
                    | Visual | MarkersVisual
                    | EventCameraMixin | TurntableCamera)


type VispyObjectConfig = TurnTableCameraParameters


class VispyLinks(Object2ObjectLinks):

    def __init__(self, model, vispy_obj,
                 signal_register: ExtendedModelSignalsRegister,
                 model_signals=None,
                 **kwargs):

        self.data: dict[int | BaseModel, VispyObject] | None = None
        self.source: VispyObjectConfig | None = None
        self.sink: VispyObject | None = None

        self.sub_visual_map = Model2ObjectMap()

        node_tree = None
        if isinstance(vispy_obj, (BoxVisual, FiniteGridLines,
                                  MultiBoxLinesVisual, MarkersVisual)):
            exp_model = VispyVisualBuilder.get_model(model)
            if model.__class__ != exp_model.__class__:
                assert isinstance(model, (FiniteGridConfig,
                                          NetworkReservoirConfig))
                node_tree = signal_register.add_linked_model(
                    model, exp_model)
                model = exp_model
                # model.__setattr__(model, 'seg', (1, 2, 3))
            else:
                node_tree = signal_register.model2nodetree_map[model]

        super().__init__(source=model, sink=vispy_obj, **kwargs)

        self.model_signals: ModelParameterLinks = (
            model_signals) if model_signals else signal_register[self.source]
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
        else:
            if (isinstance(vispy_obj, VisualNode)
                    and type(vispy_obj) not in VisualMixin.SET_DATA_KWS):
                raise AssertionError
            if isinstance(self.sink, XYZAxis):

                assert isinstance(self.source, XYZAxisVisualConfig)
                self.sink.events.attr_changed.connect(self.update_model)
                self.add_links(self.update_object)
                # self.sink.__setattr__('antialias', True)
                # self.sink.antialias = True

            elif isinstance(self.sink, MarkersVisual):
                self.sink.events.attr_changed.connect(self.update_model)
                self.add_links(self.update_object)

            elif isinstance(self.sink, MultiBoxLinesVisual):
                self.sink.events.attr_changed.connect(self.update_model)
                self.add_links(self.update_object)
                # model_links: list[ObjectParameterLink] = (
                #     signal_register[self.source][ObjectParameterLink].refs)
                # self.add_links(self.update_object, links=model_links)

            elif isinstance(self.sink, CompoundVisual):
                if isinstance(self.source, BoxVisualInitConfig):
                    assert isinstance(self.sink, BoxVisual)
                elif isinstance(self.source, MultiBoxLinesVisualConfig):
                    assert isinstance(self.sink, MultiBoxLinesVisual)
                else:
                    raise NotImplementedError
                # noinspection PyProtectedMember
                if len(self.sink._subvisuals) > 0:
                    self.source.subvisuals = []
                    # noinspection PyProtectedMember
                    for sub_visual in self.sink._subvisuals:
                        if isinstance(sub_visual, MeshVisual):
                            # noinspection PyArgumentList
                            sub_visual_model = MeshVisualConfig()
                        elif isinstance(sub_visual, MultiBoxLinesVisual):
                            sub_visual_model = MultiBoxLinesVisualConfig(
                                pos=sub_visual.pos,
                                connect=sub_visual.connect,
                                width=sub_visual.width,
                                color=sub_visual.color,
                            )
                        elif isinstance(sub_visual, GSGLLineVisual):
                            sub_visual_model = None
                        else:
                            raise NotImplementedError
                        if sub_visual_model is not None:
                            self.sub_visual_map[sub_visual_model] = sub_visual
                            self.source.subvisuals.append(
                                sub_visual_model)
                node_tree.read_model(self.source, b_ignore_existing=True)

            elif isinstance(self.sink, MeshVisual):
                self.connect_mesh_visual(self.sink, self.source,
                                         # sr=signal_register
                                         )
                self.add_links(self.update_object)

            self.transform_signals: ModelParameterLinks | None = None
            self.connect_transform(signal_register, model_signals)

            return

    def add_links(self, func, links=None,
                  b_validate_kw: bool = True,
                  b_verbose: bool = True):
        if links is None:
            links = self.model_links

        new_keys = []
        for link in links:
            if ((b_validate_kw is False)
                    or self.b_valid_keyword(link.source_key, func)):
                link[LinkStateType.SOURCE2SINK].connect(func)
                self[link.source_key] = link
                new_keys.append(link.source_key)
        if b_verbose:
            print(self.source.__class__.__name__, new_keys)

    @classmethod
    def adapt_condition(cls, arr0, arr1):
        if ((not ArrayInterfaces().D2.b_is_valid_np(arr0))
                or (not ArrayInterfaces().D2.b_is_valid_np(arr1))):
            return False
        return arr0.shape[0] != arr1.shape[0]

    def connect_mesh_visual(self, obj, model,
                            # sr: ExtendedModelSignalsRegister = None
                            ):
        if type(obj) not in VisualMixin.SET_DATA_KWS:
            VisualMixin.SET_DATA_KWS[type(obj)] = (
                VisualMixin.SET_DATA_KWS)[MeshVisual]
        assert isinstance(model, MeshVisualConfig)
        # obj.events.attr_changed.connect(update_model)
        # print('connect MeshVisual', id(obj))
        obj.events.mesh_data_changed.connect(self.update_model)
        # if sr is not None:
        #     model_links: list[ObjectParameterLink] = (
        #         sr[model][ObjectParameterLink].refs)
        #     self.add_links(func=self.update_object, links=model_links)

    def connect_transform(self, signal_register, model_signals):
        if hasattr(self.source, EnginePos3D.Slots.POS_ORIGIN):
            if isinstance(self.sink.transform, STTransform):
                pos_origin_model = self.source.pos_origin
                if ((model_signals is None)
                        or (model_signals is self.model_signals)):
                    transform_signals = signal_register[pos_origin_model]
                elif (model_signals is
                      signal_register.extensions_map[self.source]):
                    return
                    # signals = signal_register.extensions_map[pos_origin_model]
                else:
                    raise AssertionError
                self.transform_signals: ModelParameterLinks = transform_signals
                print(
                    '\nconnect_transform',
                    self.source.__class__.__name__,
                    f"<{id(self.source)}>\n",
                    # src.__class__.__name__,
                    # f"<{id(src)}>\n",
                    self.sink.__class__.__name__,
                    f"<{id(self.sink)}>\n"
                    # f"signals <{id(signals)}>\n"
                    f"signals <{id(self.transform_signals)}>\n"
                )

                links = self.transform_signals[ObjectParameterLink].refs
                for link in links:
                    link[LinkStateType.SOURCE2SINK].connect(
                        self.update_object_transform)
                    if link.source_key not in self[str]:
                        self[link.source_key] = link

                self.sink.transform.changed.connect(self.update_model)
                self.sink.transform.changed()

    @classmethod
    def cls_update_model(
            cls, event: Event,
            model_signals: ModelParameterLinks, block):
        if isinstance(event, Set3DAttributeEvent):
            for ax in Ax3D:
                try:
                    link = model_signals[str][ax.name]
                    cls.cls_update_model_attribute(
                        link, ax.name, event.value[ax.value], block)
                except KeyError:
                    raise
        elif isinstance(event, SetAttributeEvent):
            try:
                link = model_signals[str][event.key]
            except KeyError:
                if event.key == 'visible':
                    return
                raise
            cls.cls_update_model_attribute(link, event.key, event.value, block)
        elif isinstance(event, MeshDataChangedEvent):
            pass

        elif event.type == 'transform_changed':
            tr: STTransform = event.source
            # pos_origin_model = model_signals.source
            for ax in Ax3D:
                link = model_signals[str][ax.name]
                cls.cls_update_model_attribute(
                    link, ax.name, float(tr.translate[ax.value]), block)
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

    @classmethod
    def cls_update_model_attribute(
            cls, link: ObjectParameterLink, key, value, block):
        if block:
            link[LinkStateType.SOURCE2SINK].disconnect(block)
        link[LinkStateType.SOURCE2SINK](
            link.source, key, value, b_block=False)
        if block:
            link[LinkStateType.SOURCE2SINK].connect(block)

    @property
    def model_links(self):
        return self.model_signals[ObjectParameterLink].refs

    @classmethod
    def handle_set_data_kwargs(cls, obj, key, value):
        kwargs = {key: value}

        if key.endswith(VispyKeyWords.COLOR):
            if isinstance(kwargs[key], (tuple, dict)):
                kwargs[key] = RGBAColor.to_vispy(kwargs[key])

        if isinstance(obj, XYZAxis):
            if ((key == 'width')
                    or ((key == VispyKeyWords.CONNECT)
                        and isinstance(value, str))):
                return kwargs
            if key == VispyKeyWords.COLOR:
                other_key = VispyKeyWords.POS
            else:
                other_key = VispyKeyWords.COLOR
            if cls.adapt_condition(
                    kwargs[key], other := getattr(obj, other_key)):
                kwargs[other_key] = adapt_dim(other, ref=kwargs[key])
        elif isinstance(obj, MarkersVisual):
            kw_to_rec = {
                'pos': 'a_position',
                'edge_color': 'a_fg_color',
                'face_color': 'a_bg_color',
                'size': 'a_size',
                'edge_width': 'a_edgewidth',
                # 'symbol': 'a_symbol',
            }
            if key in [VispyKeyWords.SIZE, VispyKeyWords.EDGE_WIDTH]:
                pass
            else:
                if key == VispyKeyWords.COLOR:
                    other_key = VispyKeyWords.POS
                else:
                    other_key = VispyKeyWords.FACE_COLOR
                if cls.adapt_condition(
                        kwargs[key], other := obj._data[kw_to_rec[other_key]]):
                    kwargs[other_key] = adapt_dim(other, ref=kwargs[key])
            for k in kw_to_rec:
                if k not in kwargs:
                    kwargs[k] = obj._data[kw_to_rec[k]]
        return kwargs

    def prepare_object(self, obj, link_type: LinkStateType,
                       debug_catch=BaseException):
        raise NotImplementedError

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
        elif event.type == 'transform_changed':
            signals_ = self.transform_signals
            if block is Undefined:
                block = self.update_object_transform
        else:
            signals_ = self.model_signals
            if block is Undefined:
                block = self.update_object

        if (isinstance(event, SetAttributeEvent)
                and (not isinstance(event, Set3DAttributeEvent))
                and (event.key not in self[str].refs.data)):
            return

        self.cls_update_model(
            event=event, model_signals=signals_, block=block)

    def b_valid_keyword(self, key, func):
        if func == self.update_object:
            if hasattr(self.sink, key):
                return True
            elif ((type(self.sink) in VisualMixin.SET_DATA_KWS)
                    and (key in VisualMixin.SET_DATA_KWS[type(self.sink)])):
                return True
            return False
        elif func == self.update_camera_object:
            return True
        else:
            raise NotImplementedError

    def update_object(self, model, key, value,
                      event_block=Undefined,
                      block=Undefined):

        if not self.b_valid_keyword(key, self.update_object):
            raise RuntimeError

        if event_block is Undefined:
            event_block = self.sink.events.attr_changed
        if block is Undefined:
            block = self.update_model
        event_block.disconnect(block)
        # new_kwargs = {}
        if ((type(self.sink) in VisualMixin.SET_DATA_KWS)
                and (key in VisualMixin.SET_DATA_KWS[type(self.sink)])):
            new_kwargs = self.handle_set_data_kwargs(self.sink, key, value)
            self.sink.set_data(**new_kwargs)
        else:
            if key == 'color':
                if isinstance(value, (tuple, dict)):
                    value = RGBAColor.to_vispy(value)
            if hasattr(self.sink, key):
                setattr(self.sink, key, value)
            else:
                pass

        event_block.connect(block)
        # if len(new_kwargs) > 1:
        #     for k, v in new_kwargs.items():
        #         if k != key:
        #             event_block(key=k, value=v)

    def update_object_transform(
            self, model, key, value, event_block=Undefined, block=Undefined):

        if event_block is Undefined:
            # event_block = self.sink.events.attr_changed
            event_block = self.sink.transform.changed
        if block is Undefined:
            block = self.update_model
            pass
        else:
            event_block.disconnect(block)

        arr = self.sink.transform.translate
        arr[Ax3D[key].value] = value
        self.sink.transform.translate = arr

        if block is Undefined:
            pass
        else:
            event_block.connect(block)
