import os.path as op
# noinspection PyProtectedMember
from pyqtgraph.icons import getGraphIcon, GraphIcon, getGraphPixmap
# noinspection PyProtectedMember
from pyqtgraph.icons import _ICON_REGISTRY
from qtpy import QtGui


__all__ = ['EngineGraphIcon',
           'getEngineGraphIcon',
           'getEngineGraphPixmap']


class EngineGraphIcon(GraphIcon):

    # # noinspection PyMissingConstructor
    # def __init__(self, path, name=None):
    #     self._path = path
    #     self._name = name or path.split('.')[0]
    #     _ICON_REGISTRY[self._name] = self
    #     self._icon = None

    def _build_qicon(self):
        icon = QtGui.QIcon(op.join(op.dirname(__file__), self._path))
        name = self._path.split('.')[0]
        _ICON_REGISTRY[name] = icon
        # _ICON_REGISTRY[self._name] = icon
        self._icon = icon


# noinspection PyPep8Naming
def getEngineGraphIcon(name):
    try:
        return getGraphIcon(name)
    except KeyError:
        return getGraphIcon("kamiyamane/" + name.replace('.png', ''))


# noinspection PyPep8Naming
def getEngineGraphPixmap(name):
    try:
        return getGraphPixmap(name)
    except KeyError:
        return getGraphPixmap("kamiyamane/" + name.replace('.png', ''))


# Note: List all here icons here ...
ky_arrow_circle = EngineGraphIcon("kamiyamane/arrow-circle.png")
ky_control = EngineGraphIcon("kamiyamane/control.png")
ky_control_pause = EngineGraphIcon("kamiyamane/control-pause.png")
ky_eye = EngineGraphIcon("kamiyamane/eye.png")
ky_eye_clos_grey = EngineGraphIcon("kamiyamane/eye-close-grey.png")
ky_eye_exclamation = EngineGraphIcon("kamiyamane/eye--exclamation.png")
ky_disk_black = EngineGraphIcon("kamiyamane/disk-black.png")
ky_drive_upload = EngineGraphIcon("kamiyamane/drive-upload.png")
ky_default = EngineGraphIcon("kamiyamane/default.png")
ky_plus = EngineGraphIcon("kamiyamane/plus.png")
