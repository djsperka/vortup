import sys
from myengine import setup_logging, DEFAULT_ENGINE_PARAMS
from OCTUi import OCTUi
from StandardEngineParamsDialog import StandardEngineParamsDialog

#from PyQt5.QtCore import oop, QTimer, QState, QStateMachine
from PyQt5.QtWidgets import QApplication
#from PyQt5 import uic

cfg = DEFAULT_ENGINE_PARAMS

setup_logging()

# gui and exception handler
app = QApplication(sys.argv)

import traceback
def handler(cls, ex, trace):
    traceback.print_exception(cls, ex, trace)
    app.closeAllWindows()
sys.excepthook = handler

cfgDialog = StandardEngineParamsDialog(cfg)

cfgDialog.accepted.connect(cfgAccepted)
cfgDialog.show()


    # octui = OCTUi()
    # octui.show()


sys.exit(app.exec_())


def cfgAccepted():
    cfg =  cfgDialog.getEngineParameters()
    