import sys
from myengine import setup_logging
from myengine import setup_logging, StandardEngineParams, BaseEngine, DEFAULT_ENGINE_PARAMS
from OCTUi import OCTUi

#from PyQt5.QtCore import oop, QTimer, QState, QStateMachine
from PyQt5.QtWidgets import QApplication
#from PyQt5 import uic



if __name__ == '__main__':
    setup_logging()

    # gui and exception handler
    app = QApplication(sys.argv)

    import traceback
    def handler(cls, ex, trace):
        traceback.print_exception(cls, ex, trace)
        app.closeAllWindows()
    sys.excepthook = handler

    octui = OCTUi()

    octui.show()
    #timer.start(1000)
    sys.exit(app.exec_())
