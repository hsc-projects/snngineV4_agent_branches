from vispy.app import Application
from vispy.scene import SceneCanvas, Widget

from snngine_v4.utils.settings.settings_keywords import ParameterUIOpts
from snngine_v4.config.graphics.scene_config import VispyCanvasOptions


class EngineSceneCanvas(SceneCanvas):

    def __init__(self, conf: VispyCanvasOptions,
                 app: Application):

        conf = conf or VispyCanvasOptions()
        kwargs = conf.model_dump(mode='python')
        wdg_opts = kwargs.pop(
            VispyCanvasOptions.Slots.CENTRAL_WIDGET_OPTIONS, {})

        kwargs.pop(ParameterUIOpts.UI_OPTIONS_KEYWORD, {})
        wdg_opts.pop(ParameterUIOpts.UI_OPTIONS_KEYWORD, {})
        if 'config' in kwargs:
            kwargs['config'].pop(ParameterUIOpts.UI_OPTIONS_KEYWORD, {})

        super().__init__(app=app, **kwargs)
        for k, v in wdg_opts.items():
            if k == 'border_width':
                k = '_border_width'
            setattr(self.central_widget, k, v)
        self.unfreeze()

    @property
    def name(self):
        return self.title
