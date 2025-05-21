import sys
from VtxEngineParams import DEFAULT_VTX_ENGINE_PARAMS, VtxEngineParams
from VtxEngineParamsDialog import VtxEngineParamsDialog
from VtxEngine import VtxEngine
from OCTDialog import OCTDialog
from PyQt5.QtWidgets import QApplication

import logging
from rainbow_logging_handler import RainbowLoggingHandler


class OCTUi():
    
    def __init__(self):
        super().__init__() # Call the inherited class' __init__ method

        #self._app = QApplication(sys.argv)
        self._cfg = DEFAULT_VTX_ENGINE_PARAMS
        self.showParamsDialog()

    def showParamsDialog(self):
        self._cfgDialog = VtxEngineParamsDialog(self._cfg)
        self._cfgDialog.finished.connect(self.cfgFinished)
        self._cfgDialog.show()

    def cfgFinished(self, v):

        self._octDialog = OCTDialog()
        self._octDialog.show()
        # if v == 1:
        #     self._cfg = self._cfgDialog.getEngineParameters()
        #     try:
        #         # get oct engine ready
        #         self._engine = VtxEngine(self._cfg)
        #     except RuntimeError as e:
        #         print("RuntimeError:")
        #         print(e)
        #         self.showParamsDialog()
        #     else:    
        #         self._octDialog = OCTDialog()
        #         self._octDialog.show()
        # else:
        #     sys.exit()


def setup_logging():
    # configure the root logger to accept all records
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.NOTSET)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)

    formatter = logging.Formatter('%(asctime)s.%(msecs)03d [%(name)s] %(filename)s:%(lineno)d\t%(levelname)s:\t%(message)s')

    # set up colored logging to console
    console_handler = RainbowLoggingHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)



if __name__ == '__main__':
    setup_logging()
    app = QApplication(sys.argv)
    octui = OCTUi()
    app.exec_()
