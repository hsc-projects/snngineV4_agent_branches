from pyqtgraph.parametertree.parameterTypes import (
    SimpleParameter,
    StrParameterItem,
)

from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


class NoneTypeParameter(SimpleParameter):

    def __init__(self, **opts):
        opts[ParamOpts.KW.DEFAULT] = None
        opts[ParamOpts.KW.VALUE] = None
        opts[ParamOpts.KW.READONLY] = True
        opts[ParamOpts.KW.REMOVABLE] = True
        super().__init__(**opts)
    
    @property
    def itemClass(self):
        return StrParameterItem

    # noinspection PyPep8Naming
    def setValue(self, value, blockSignal=None):
        return super().setValue(None, blockSignal=None)
