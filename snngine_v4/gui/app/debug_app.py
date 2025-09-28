import qdarktheme
from pydantic import BaseModel
from qtpy import QtWidgets

from snngine_v4.gui.parameter_trees.engine_parameter_tree import \
    EngineParameterTree


def make_app(content, theme='dark'):

    app = QtWidgets.QApplication([''])
    qdarktheme.setup_theme(
        theme=theme,
    )
    if isinstance(content, BaseModel):
        widget = EngineParameterTree(model=content)
    else:
        widget = content()
        if isinstance(widget, BaseModel):
            widget = EngineParameterTree(model=widget)
    widget.show()
    app.exec_()
