from snngine_v4.utils.settings.config_model import ConfigModel
from snngine_v4.visualization.config_models.vispy_camera_configs import \
    PanZoomCameraParameters
from snngine_v4.visualization.config_models.vispy_canvas_config import (
    SceneViews, SceneVisuals, VispyCanvasConfig,
    VispyCanvasConfigOptions, VispyViewBoxConfig,
)
from snngine_v4.visualization.config_models.visuals.lines import \
    XYZAxisVisualConfig


# noinspection PyArgumentList
class SceneSettings(ConfigModel):

    main: VispyCanvasConfig = VispyCanvasConfig(
        Options=VispyCanvasConfigOptions(title='NetworkView'),
        Views=SceneViews(
            main=VispyViewBoxConfig(),
            # second=VispyViewBoxConfig(),
        ),
        Visuals=SceneVisuals(axis=XYZAxisVisualConfig()))

    multiplot_voltage: VispyCanvasConfig = VispyCanvasConfig(
        Options=VispyCanvasConfigOptions(title='Potential'),
        Views=SceneViews(
            main=VispyViewBoxConfig(),
        ),
        Visuals=SceneVisuals(axis=XYZAxisVisualConfig()))

    multiplot_current: VispyCanvasConfig = VispyCanvasConfig(
        Options=VispyCanvasConfigOptions(title='Current'),
        Views=SceneViews(
            main=VispyViewBoxConfig(
                camera=PanZoomCameraParameters()
            ),
        ),
        Visuals=SceneVisuals(
            axis=XYZAxisVisualConfig()
        ))
