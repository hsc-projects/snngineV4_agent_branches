import os
from pathlib import Path
import sys


# print('\n', os.environ.get('LD_LIBRARY_PATH'),'\n')


if str(dir_ := Path(os.path.dirname(__file__)).parent) not in sys.path:
    sys.path.append(str(dir_))

from snngine_v4.gui.app.engine_app import EngineApp


if __name__ == '__main__':
    print()
    app = EngineApp()
    app.run()
