from __future__ import annotations

from typing import Any, Callable, ClassVar, Set, Type

import numpy as np
from pydantic import BaseModel
from vispy.scene import (
    Box, Line, Markers, VisualNode,
    XYZAxis,
)
from vispy.scene.visuals import create_visual_node
from vispy.util.event import EmitterGroup
from vispy.visuals import (
    BaseVisual, CompoundVisual, LineVisual, MeshVisual,
    Visual,
)
from vispy.visuals.transforms import NullTransform, STTransform

from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.geometry.spatial_pars import (
    AxDir3D, Directions3DBoolPars, EnginePos3D, FloatShape3D,
    Segmentation3D,
)
from snngine_v4.nn.construction.config_models.reservoir.nn_reservoir_config \
    import NetworkReservoirConfig
from snngine_v4.utils.containers.configurable_dict import (
    ConfigurableDict,
    DictContainerConfig,
)
from snngine_v4.utils.class_mixer import ClassMixer
from snngine_v4.utils.core_utils import filter_dict_keys
from snngine_v4.utils.field_utils import Undefined
from snngine_v4.utils.object_builder.object_builder_dict import BuilderDict
from snngine_v4.utils.settings.settings_keywords import (
    BaseModelSlots,
    InternalOpts,
)

from snngine_v4.visualization.config_models.visuals.markers import \
    MarkersVisualConfig

from snngine_v4.visualization.config_models.visuals.parameters import (
    OpenGLState, OpenGlStateType,
    RGBAColor, VispyKeyWords, WDHKw,
    WDHSegKw,
)
from snngine_v4.visualization.config_models.visuals.lines import (
    LineVisualConfig, XYZAxisVisualConfig,
)
from snngine_v4.visualization.config_models.visuals.boxes import (
    BoxVisualInitConfig, OuterGridVisualInitConfig,
)
from snngine_v4.visualization.config_models.plotting.multi_line_plot import (
    MultiPlotConfig, SepLineData,
)
from snngine_v4.visualization.scenes.setattribute_event import (
    MeshDataChangedEvent, SetAttributeEvent,
)
from snngine_v4.visualization.visuals.grid_lines import (
    FiniteGridLinesVisual, MultiBoxLinesVisual,
)


class EmitterMap(ConfigurableDict):

    class ContainerConfigClass(DictContainerConfig):
        allowed_types: Any = Callable | ConfigurableDict
        allowed_key_types: Any = str | int
        b_duplicates_allowed: bool = True

    def __init__(self, events: EmitterGroup, keys, **kwargs):
        self.events = events
        super().__init__(**kwargs)
        self.set_items(*keys)

    def __call__(self, key, value):
        try:
            if key == 'visible':
                pass
            elif key == '_visible':
                return
            self[key](key=key, value=value)
            return
        except KeyError:
            pass

    def set_items(self, *keys):
        for key in keys:
            self[key] = self.events.attr_changed


class VisualMixin:

    SET_DATA_LineVisual_KWS = [VispyKeyWords.COLOR,
                               VispyKeyWords.POS,
                               VispyKeyWords.CONNECT,
                               'width']

    SET_DATA_KWS = {
        LineVisual: SET_DATA_LineVisual_KWS,
        Line: SET_DATA_LineVisual_KWS,
        XYZAxis: SET_DATA_LineVisual_KWS,
        MultiBoxLinesVisual: SET_DATA_LineVisual_KWS,
        # FiniteGridLines: [],
        FiniteGridLinesVisual: [],
        Box: [VispyKeyWords.COLOR],
        Markers: [VispyKeyWords.POS,
                  VispyKeyWords.EDGE_COLOR,
                  VispyKeyWords.FACE_COLOR,
                  VispyKeyWords.SIZE,
                  VispyKeyWords.EDGE_WIDTH,
                  ],
        MeshVisual: ['vertices', 'faces',
                     VispyKeyWords.VERTEX_COLORS,
                     VispyKeyWords.FACE_COLORS,
                     'vertex_values',
                     'meshdata'],
    }

    attr_changed_keys: ClassVar[Set[str]] = set()

    def __pre_init__(self, *args, **kwargs):
        object.__setattr__(self, "emitter_map", None)
        self._initialized = True
        self._compound_post_init_called = False
        # self.emitter_map = None

    def mesh_data_changed(self: MeshVisual):
        MeshVisual.mesh_data_changed(self)
        print('mesh_data_changed', id(self))
        self.events.mesh_data_changed(instance=self, data=self._meshdata)

    def __post_init__(self: VisualMixin | Visual | CompoundVisual,
                      subvisuals=None):

        b_verbose = False

        self.events.add(auto_connect=False,
                        attr_changed=SetAttributeEvent)
        self.emitter_map = EmitterMap(self.events, keys=self.attr_changed_keys)

        def connect_mesh_data_changed(v_):
            v_.mesh_data_changed = lambda: VisualMixin.mesh_data_changed(v_)

        if subvisuals is not None:
            for s in subvisuals:
                self.add_subvisual(s)

        if isinstance(self, CompoundVisual):
            for i, v in enumerate(self._subvisuals):
                v: Visual
                if not isinstance(v, VisualMixin):
                    if isinstance(v, (MeshVisual, LineVisual)):
                        if isinstance(v, MeshVisual):
                            v.events.add(
                                auto_connect=False,
                                attr_changed=SetAttributeEvent,
                                mesh_data_changed=MeshDataChangedEvent)
                            connect_mesh_data_changed(v)
                        elif isinstance(v, LineVisual):
                            v.events.add(
                                auto_connect=False,
                                attr_changed=SetAttributeEvent,
                                mesh_data_changed=MeshDataChangedEvent)
                        if b_verbose:
                            print('added events:', v.__class__.__name__, id(v))
                    else:
                        pass


class VisualMixins(ClassMixer):
    Mixins: ClassVar = VisualMixin

    @classmethod
    def mix(cls, class_item: Type, name=None, attr_changed_keys=Undefined):

        if issubclass(class_item, (VisualNode, BaseVisual)):

            if class_item in [XYZAxis, Line]:
                attr_changed_keys = LineVisualConfig.cls_model_keys()
            elif class_item in (Box, FiniteGridLinesVisual):
                attr_changed_keys = {'_mesh': ['shading']}
            elif class_item == MeshVisual:
                attr_changed_keys = ['color']
            elif class_item == Markers:
                attr_changed_keys = (
                    ['alpha'] + MarkersVisualConfig.cls_model_keys())
            else:
                raise NotImplementedError()
            if 'visible' not in attr_changed_keys:
                if not isinstance(attr_changed_keys, dict):
                    attr_changed_keys += ['visible']
                else:
                    attr_changed_keys['visible'] = []

            if not issubclass(class_item, VisualNode):
                set_data_kws = VisualMixin.SET_DATA_KWS[class_item]
                class_item = create_visual_node(FiniteGridLinesVisual)
                VisualMixin.SET_DATA_KWS[class_item] = set_data_kws

            def init(self: VisualMixin | Visual, *args, **kwargs_):
                subvisuals = None
                if class_item == Line:
                    subvisuals = kwargs_.pop(
                        VispyVisualBuilder.SUBVISUALS_KW, None)
                    sep_lines = kwargs_.pop(
                        MultiPlotConfig.SEP_LINES_KW, None)
                    if sep_lines is not None:
                        if subvisuals is None:
                            subvisuals = []
                        subvisuals += [sep_lines]

                    line_keys = set(LineVisualConfig.cls_model_keys())
                    plot_keys0 = set(SepLineData.cls_model_keys())
                    plot_keys1 = set(MultiPlotConfig.cls_model_keys())
                    exclude = plot_keys0 - line_keys
                    exclude |= plot_keys1 - line_keys
                    kwargs_ = filter_dict_keys(dct=kwargs_, exclude=exclude)

                visible = kwargs_.pop('visible', True)
                pos_origin = kwargs_.pop(EnginePos3D.Slots.POS_ORIGIN, True)

                self.__pre_init__(*args, **kwargs_)
                class_item.__init__(self, *args, **kwargs_)
                if subvisuals is not None:
                    self.__post_init__(subvisuals)
                else:
                    self.__post_init__()

            def set_attr(self: VisualMixin | Visual, key, value):
                class_item.__setattr__(self, key, value)
                if self._initialized and self.emitter_map:
                    self.emitter_map.__call__(key, value)

            kwargs = dict(__init__=init,
                          __setattr__=set_attr,
                          attr_changed_keys=attr_changed_keys)

            new = super().mix(class_item, name, **kwargs)

            if class_item in VisualMixin.SET_DATA_KWS:
                VisualMixin.SET_DATA_KWS[new] = (
                    VisualMixin.SET_DATA_KWS[class_item])

            return new
        else:
            raise AssertionError
            # return class_item


class VispyVisualBuilder(BuilderDict):

    VISPY_VISUAL_DUMP_KW: ClassVar[str] = 'vispy'

    POS_KW: ClassVar[str] = 'pos'
    COLOR_KW: ClassVar[str] = 'color'
    SUBVISUALS_KW: ClassVar[str] = 'subvisuals'

    BUILDER_OBJECT_CLASS_MIXER: ClassVar = VisualMixins

    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        BoxVisualInitConfig: Box,
        FiniteGridConfig: FiniteGridLinesVisual,
        OuterGridVisualInitConfig: Box,
        XYZAxisVisualConfig: XYZAxis,
        MarkersVisualConfig: Markers,
        NetworkReservoirConfig: Markers,
        # PlotConfig: Line,
        MultiPlotConfig: Line,
        LineVisualConfig: Line,
        SepLineData: Line,
    }

    # BUILDER_OBJECT_SUPERCLASS_MAP: ClassVar = {}

    @classmethod
    def _convert_to_vispy(cls, dct, model: BaseModel):
        res = ConfigurableDict(
            container_conf=DictContainerConfig(b_duplicates_allowed=True))

        dct.pop(InternalOpts.Slots.TECHNICAL, None)
        subvisuals = dct.pop(cls.SUBVISUALS_KW, None)
        if subvisuals and len(subvisuals) > 0:
            if not isinstance(model, MultiPlotConfig):
                raise AssertionError
            pass
        elif subvisuals is not None:
            pass

        if isinstance(model, MultiPlotConfig):
            if model.sep_lines is not None:
                if cls.SUBVISUALS_KW not in dct:
                    dct[cls.SUBVISUALS_KW] = []
                dct.pop(MultiPlotConfig.SEP_LINES_KW)
                sub_vis = VispyVisualBuilder.cls_build_obj(
                    model.sep_lines).built
                dct[cls.SUBVISUALS_KW] += [sub_vis]

        if isinstance(dct, dict):

            if isinstance(model, XYZAxisVisualConfig):
                if dct.get(cls.POS_KW, None) is None:
                    dct[cls.POS_KW] = np.array([
                        [0, 0, 0],
                        [1, 0, 0],
                        [0, 0, 0],
                        [0, 1, 0],
                        [0, 0, 0],
                        [0, 0, 1]])
                if dct.get(cls.COLOR_KW, None) is None:
                    dct[cls.COLOR_KW] = np.array([
                        [1, 0, 0, 1],
                        [1, 0, 0, 1],
                        [0, 1, 0, 1],
                        [0, 1, 0, 1],
                        [0, 0, 1, 1],
                        [0, 0, 1, 1]])

            up_keys = {}
            for k, dump_value_ in dct.items():
                if k != cls.SUBVISUALS_KW:
                    model_ = getattr(model, k)
                    if isinstance(model_, FloatShape3D):
                        # up_keys[k] = WDHKw.convert_dict(dump_value_)
                        up_keys[k] = WDHKw.convert_model(model_)
                    elif isinstance(model_, Segmentation3D):
                        # up_keys[k] = WDHSegKw.convert_dict(dump_value_)
                        up_keys[k] = WDHSegKw.convert_model(model_)
                    elif isinstance(model_, RGBAColor):
                        dct[k] = RGBAColor.to_vispy(dump_value_)
                    elif isinstance(model_, Directions3DBoolPars):
                        vals = list(dump_value_.keys())
                        vals = [AxDir3D.vispy_name_alias(x) for x in vals]
                        dct[k] = tuple(vals)

            for k in up_keys:
                dct.pop(k)
                res.update(up_keys[k])
            res.update(dct)

        return res.data

    @classmethod
    def get_model(cls, model: BaseModel | None):
        dump = model.model_dump(mode='python',
                                round_trip=True,
                                exclude={BaseModelSlots.CLASS__NAME})
        if isinstance(model, FiniteGridConfig):
            model = OuterGridVisualInitConfig(**dump)
        elif isinstance(model, NetworkReservoirConfig):
            model = MarkersVisualConfig(pos=dump['pos'])
        return super().get_model(model=model)

    @classmethod
    def make_object_kwargs(cls, object_class, model: BaseModel, **kwargs):
        object_kwargs = super().make_object_kwargs(object_class, model)
        object_kwargs = cls._convert_to_vispy(object_kwargs, model=model)
        object_kwargs.update(**kwargs)
        return object_kwargs

    @classmethod
    def make_object(cls, object_class, object_model, **object_kwargs):

        opengl_kwargs = cls._pop_opengl_kwargs(
            dct=object_kwargs, model=object_model)

        visual: VisualNode = super().make_object(
            object_class=object_class, object_model=object_model,
            **object_kwargs,)

        if len(opengl_kwargs) > 0:
            cls.apply_open_gl_kwargs(visual, opengl_kwargs)

        if isinstance(visual.transform, NullTransform):
            visual.transform = STTransform(
                translate=(0, 0, 0), scale=(1, 1, 1))
            if isinstance(visual, FiniteGridLinesVisual):
                visual.transform.move(visual.grid.shape / 2)
                visual.transform.changed()

        return visual

    @classmethod
    def _pop_opengl_kwargs(cls, dct, model: BaseModel):
        res = ConfigurableDict()
        for k, v in dct.items():
            if hasattr(model, k):
                model_ = getattr(model, k)
                if isinstance(model_, OpenGLState):
                    res[k] = v
        for k in res:
            dct.pop(k)
        return res

    @classmethod
    def apply_open_gl_kwargs(
        cls, visual: BaseVisual | VisualNode, opengl_kwargs,
            state_type: OpenGlStateType | None = None
    ):
        if state_type is None:
            cls.apply_open_gl_kwargs(visual, opengl_kwargs,
                                     state_type=OpenGlStateType.SET)
            cls.apply_open_gl_kwargs(visual, opengl_kwargs,
                                     state_type=OpenGlStateType.UPDATE)
        else:
            for k, kwargs in opengl_kwargs.items():
                if kwargs.pop(OpenGLState.Slots.STATE_TYPE, None) == state_type:
                    if ((k_ := kwargs.pop(OpenGLState.Slots.ATTRIBUTE_KEY))
                            is not None):
                        k = k_
                    attr: Visual = getattr(visual, k)

                    match state_type:
                        case OpenGlStateType.SET:
                            attr.set_gl_state(**kwargs)
                        case OpenGlStateType.UPDATE:
                            attr.update_gl_state(**kwargs)
                        case _:
                            raise NotImplementedError(f"{state_type}")
