from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.visualization.config_models.vispy_canvas_config import (
    SceneViews, SceneVisuals, VispyCanvasConfig,
    VispyCanvasConfigOptions, VispyViewBoxConfig,
)
from snngine_v4.visualization.config_models.visual_configs import \
    XYZAxisVisualConfig


class SceneSettings(XMLSettingsModel):

    main: VispyCanvasConfig = VispyCanvasConfig(
        options=VispyCanvasConfigOptions(title='NetworkView'),
        views=SceneViews(main=VispyViewBoxConfig()),
        visuals=SceneVisuals(axis=XYZAxisVisualConfig()))
