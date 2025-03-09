from vispy.scene import Line
from vispy.visuals import CompoundVisual, LineVisual

from snngine_v4.utils.core_utils import filter_dict
from snngine_v4.visualization.config_models.plotting.multi_line_plot import \
    MultiPlotConfig
from snngine_v4.visualization.config_models.visuals import LineVisualConfig


class PlotLine(LineVisual):

    def __init__(self, **kwargs):

        line_keys = LineVisualConfig.cls_model_keys()
        line_keys_kwargs = LineVisualConfig.cls_filter_dict_keys(
            kwargs, keys=line_keys)

        sep_lines = kwargs.pop(MultiPlotConfig.SEP_LINES_KW)
        if sep_lines is None:
            sep_line_kwargs = {}
        else:
            sep_line_kwargs = LineVisualConfig.cls_filter_dict_keys(
                sep_lines, keys=line_keys)

        self.sep_line_visual = LineVisual(**sep_line_kwargs)

        super().__init__(**line_keys_kwargs)
        self.add_subvisual(self.sep_line_visual)
