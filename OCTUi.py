import sys
from VtxEngineParams import DEFAULT_VTX_ENGINE_PARAMS, VtxEngineParams
from VtxEngineParamsDialog import VtxEngineParamsDialog
from VtxEngine import VtxEngine
from OCTDialog import OCTDialog
from PyQt5.QtWidgets import QApplication
from vortex_tools.ui.display import RasterEnFaceWidget, CrossSectionImageWidget
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

        if v == 1:
            self._cfg = self._cfgDialog.getEngineParameters()
            try:
                # get oct engine ready
                self._engine = VtxEngine(self._cfg)

            except RuntimeError as e:
                print("RuntimeError:")
                print(e)
                self.showParamsDialog()
            else:    
                self._octDialog = OCTDialog()
                self._octDialog.pbStart.clicked.connect(self.startClicked)
                self._octDialog.pbStop.clicked.connect(self.stopClicked)
                self._octDialog.pbStart.enabled = False
                
                # set up plots
                stack_widget = RasterEnFaceWidget(self._engine._stack_tensor_endpoint)
                self._octDialog.tabWidgetPlots.addTab(stack_widget, "Raster")
                cross_widget = CrossSectionImageWidget(self._engine._stack_tensor_endpoint)
                self._octDialog.tabWidgetPlots.addTab(cross_widget, "cross")

                # argument (v) here is a number - index pointing to a segment in allocated segments.
                def cb(v):
                    stack_widget.notify_segments(v)
                    cross_widget.notify_segments(v)
                self._engine._stack_tensor_endpoint.aggregate_segment_callback = cb
                self._octDialog.show()
        else:
            sys.exit()

    def startClicked(self):
        print("startClicked")
        self._octDialog.pbStart.enabled = False
        self._octDialog.pbStop.enabled = True
        self._engine.start()

    def stopClicked(self):
        print("stopClicked")
        self._octDialog.pbStart.enabled = True
        self._octDialog.pbStop.enabled = False
        self._engine.stop()



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
