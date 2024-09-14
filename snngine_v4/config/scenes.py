from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.visualization.canvas_config import MainNetworkSceneConfig


class SceneSettings(XMLSettingsModel):
    main: MainNetworkSceneConfig = MainNetworkSceneConfig()
