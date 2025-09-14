from enum import auto, IntEnum
from typing import ClassVar

import numpy as np
from pydantic import Field, NonNegativeFloat, NonNegativeInt

from snngine_v4.utils.core_utils import filter_dict_keys
from snngine_v4.utils.data_utils.dataframe_config import SeriesI32
from snngine_v4.utils.data_utils.validation.array_annotation import (
    Bool1D,
)
from snngine_v4.geometry.spatial_pars import Pos2DVBO
from snngine_v4.utils.settings.config_model import ConfigModel
from snngine_v4.utils.settings.ui_parameter_options import p_field
from snngine_v4.visualization.config_models.visuals import (
    LineVisualConfig, MarkersVisualConfig,
)
from snngine_v4.visualization.config_models.visuals.parameters import (
    ColorVBO, RGBAColorType,
)


class PlotViewMode(IntEnum):
    DOCKED = 0
    WINDOWED = auto()
    SCENE = auto()
    NONE = auto()


class PlotConfigMixin:

    @property
    def data_size(self) -> NonNegativeInt:
        return self.size_x

    def make_connect(self, size=None):
        if size is None:
            size = self.data_size
        connect = np.ones(size).astype(bool)
        connect[-1] = False
        return connect

    def make_color(self):
        color = np.ones((self.data_size, 4), dtype=np.float32)
        color[:, 0] = np.linspace(0, 1, self.data_size)
        color[:, 1] = color[::-1, 0]
        return color

    def make_pos(self):
        pos = np.zeros((self.data_size, 2), dtype=np.float32)
        pos[:, 0] = np.linspace(0, self.data_size - 1, self.data_size),
        return pos


class LinePlotConfigBase(LineVisualConfig):
    size_x: NonNegativeInt = 1
    max_size_x: int = 10000

    # noinspection Pydantic
    connect: Bool1D = Field(
        default_factory=lambda: np.array([True, True, False],
                                         dtype=np.bool),
        repr=False)

    pos: Pos2DVBO = Field(
        default_factory=lambda: np.array([
            [0, 0],
            [0, 0],
            [0, 0],], dtype=np.float32),
        repr=False)
    color: ColorVBO = Field(
        default_factory=lambda: np.array(
            [[0, 0, 0, 0]], dtype=np.float32), repr=False)
    view_mode: PlotViewMode = PlotViewMode.SCENE

    def model_post_init(self, __context):
        super().model_post_init(__context)
        if self.pos.shape != (self.data_size, 2):
            self.pos = self.make_pos()
        if self.connect.shape != self.data_size:
            self.connect = self.make_connect()
        if self.color.shape != (self.data_size, 4):
            self.color = self.make_color()


class PlotConfig(LinePlotConfigBase, PlotConfigMixin):
    pass


class SepLineData(LineVisualConfig):

    n_sep_lines: NonNegativeInt = 10
    sep_line_offset: float = 2
    pos: Pos2DVBO = Field(
        default_factory=lambda: np.array([[0, 0]], dtype=np.float32),
        repr=False)
    color: ColorVBO = Field(
        default_factory=lambda: np.array(
            [[0, 0, 0, 0]], dtype=np.float32), repr=False)
    connect: str = p_field(default='segments',  readonly=True, repr=False)

    def init_sep_line_data(self, size_x, n_plots, sep_line_offset=None):
        if sep_line_offset is not None:
            self.sep_line_offset = sep_line_offset
        self.pos, self.color = self.make_sep_line_arrays(size_x, n_plots)

    def make_sep_line_arrays(self, size_x, n_plots):
        pos = np.zeros((self.n_sep_lines * 2, 2), dtype=np.float32)
        color = np.ones((self.n_sep_lines * 2, 4), dtype=np.float32)
        color[:, 3] = 0
        pos[:, 0] = (
            np.expand_dims(
                np.array([-self.sep_line_offset, size_x]), 0)
            .repeat(self.n_sep_lines, 0)).flatten()
        pos[:, 1] = np.linspace(0, n_plots, self.n_sep_lines).repeat(2)
        return pos, color

    @classmethod
    def keep_object_init_kwargs(cls, kwargs):
        line_keys = set(LineVisualConfig.cls_model_keys())
        plot_keys0 = set(SepLineData.cls_model_keys())
        exclude = plot_keys0 - line_keys
        kwargs_ = filter_dict_keys(dct=kwargs, exclude=exclude)
        return kwargs_


class MultiPlotConfigMixin(PlotConfigMixin):

    SEP_LINES_KW: ClassVar[str] = 'sep_lines'
    MAP_KW: ClassVar[str] = 'map'

    @property
    def data_size(self) -> NonNegativeInt:
        return self.n_plots * self.size_x

    def make_connect(self, size=None):
        if size is None:
            size = self.size_x
        connect = super().make_connect(size=size)
        connect = connect.reshape(1, size).repeat(
            self.n_plots, axis=0).flatten()
        return connect

    def make_mesh(self):
        return np.meshgrid(
            np.linspace(0, self.size_x - 1, self.size_x,
                        dtype=np.float32),
            np.linspace(0.5, self.n_plots - 0.5, self.n_plots,
                        dtype=np.float32)
        )

    def make_pos(self):
        mesh = self.make_mesh()
        return np.vstack([
            mesh[0].ravel(),
            mesh[1].ravel(),
        ]).T

    @classmethod
    def _keep_object_init_kwargs(
            cls: ConfigModel,
            kwargs, core_class: type[ConfigModel]):
        line_keys = set(core_class.cls_model_keys())
        # plot_keys0 = set(SepLineData.cls_model_keys())
        plot_keys1 = set(cls.cls_model_keys())
        # exclude = plot_keys0 - line_keys
        exclude = plot_keys1 - line_keys
        kwargs_ = filter_dict_keys(dct=kwargs, exclude=exclude)
        return kwargs_

    @property
    def shape(self) -> NonNegativeInt:
        return self.size_x, self.n_plots


class MultiLinePlotConfigBase(LinePlotConfigBase):

    n_plots: NonNegativeInt = 10
    sep_lines: SepLineData | None = Field(
        default_factory=lambda: SepLineData())
    max_n_plots: int = 1000
    map: SeriesI32


class MultiLinePlotConfig(MultiLinePlotConfigBase, MultiPlotConfigMixin):

    @classmethod
    def keep_object_init_kwargs(cls, kwargs):
        return cls._keep_object_init_kwargs(kwargs, LineVisualConfig)


class MultiScatterPlotConfigBase(MarkersVisualConfig):

    size_x: NonNegativeInt = 1
    max_size_x: int = 10000

    # connect: Bool1D = Field(
    #     default_factory=lambda: np.array([True, True, False],
    #                                      dtype=np.bool),
    #     repr=False)

    pos: Pos2DVBO = Field(
        default_factory=lambda: np.array([
            [0, 0],
            [0, 0],
            [0, 0],], dtype=np.float32),
        repr=False)
    face_color: ColorVBO = Field(
        default_factory=lambda: np.array(
            [[0, 0, 0, 0]], dtype=np.float32), repr=False)
    view_mode: PlotViewMode = PlotViewMode.SCENE

    n_plots: NonNegativeInt = 10
    sep_lines: SepLineData | None = Field(
        default_factory=lambda: SepLineData())
    max_n_plots: int = 1000
    map: SeriesI32

    size: NonNegativeFloat | None = Field(default=3, le=50)
    edge_width: float | None = Field(default=0, ge=0, le=20)
    edge_color: RGBAColorType = 'black'

    def model_post_init(self, __context):
        super().model_post_init(__context)
        if self.pos.shape != (self.data_size, 2):
            self.pos = self.make_pos()
        # if self.connect.shape != self.data_size:
        #     self.connect = self.make_connect()
        if self.face_color.shape != (self.data_size, 4):
            self.face_color = self.make_color()


class MultiScatterPlotConfig(MultiScatterPlotConfigBase,
                             MultiPlotConfigMixin):
    def make_color(self):
        color = super().make_color()
        # color[:, 3] = 0
        return color

    @classmethod
    def keep_object_init_kwargs(cls, kwargs):
        return cls._keep_object_init_kwargs(kwargs, MarkersVisualConfig)