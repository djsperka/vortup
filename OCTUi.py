import sys
from VtxEngineParams import DEFAULT_VTX_ENGINE_PARAMS, VtxEngineParams
from VtxEngineParamsDialog import VtxEngineParamsDialog
from VtxEngine import VtxEngine
from OCTDialog import OCTDialog
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout
from vortex_tools.ui.display import RasterEnFaceWidget, CrossSectionImageWidget
from TraceWidget import TraceWidget
import logging
from rainbow_logging_handler import RainbowLoggingHandler
import cupy
import numpy


class OCTUi():
    
    def __init__(self):
        super().__init__() # Call the inherited class' __init__ method

        #self._app = QApplication(sys.argv)
        self._cross_widget = None
        self._trace_widget = None
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
                self._vtxengine = VtxEngine(self._cfg)

            except RuntimeError as e:
                print("RuntimeError:")
                print(e)
                self.showParamsDialog()
            else:    
                self._octDialog = OCTDialog()
                self._octDialog.pbStart.clicked.connect(self.startClicked)
                self._octDialog.pbStop.clicked.connect(self.stopClicked)
                self._octDialog.pbStart.enabled = False  
                self.addPlotsToDialog()
                self._octDialog.resize(1000,800)              
                self._octDialog.show()
        else:
            sys.exit()

    def addPlotsToDialog(self):
        # set up plots
        # We need access to both the engine (the endpoints) and the gui (display widgets). 
        if not self._cross_widget:
            self._cross_widget = CrossSectionImageWidget(self._vtxengine._stack_tensor_endpoint)
            self._trace_widget = TraceWidget(self._vtxengine._stack_tensor_endpoint)

            # make horizontal layout and add the plots, then set it as layout for widgetDummy
            hbox = QHBoxLayout()
            hbox.addWidget(self._cross_widget)
            hbox.addWidget(self._trace_widget)
            self._octDialog.widgetDummy.setLayout(hbox)
            self._octDialog.widgetDummy.show()

            # argument (v) here is a number - index pointing to a segment in allocated segments.
            def cb(v):
                #stack_widget.notify_segments(v)
                self._cross_widget.notify_segments(v)
            self._vtxengine._stack_tensor_endpoint.aggregate_segment_callback = cb

            # 
            def cb_volume(sample_idx, scan_idx, volume_idx):
                self._trace_widget.update_trace()
            self._vtxengine._stack_tensor_endpoint.volume_callback = cb_volume


    def startClicked(self):
        self._octDialog.pbStart.enabled = False
        self._octDialog.pbStop.enabled = True

        # # set up plots
        # # We need access to both the engine (the endpoints) and the gui (display widgets). 
        # if not self._cross_widget:
        #     self._cross_widget = CrossSectionImageWidget(self._vtxengine._stack_tensor_endpoint)
        #     self._trace_widget = TraceWidget(self._vtxengine._stack_tensor_endpoint)

        #     # make horizontal layout and add the plots, then set it as layout for widgetDummy
        #     hbox = QHBoxLayout()
        #     hbox.addWidget(self._cross_widget)
        #     hbox.addWidget(self._trace_widget)
        #     self._octDialog.widgetDummy.setLayout(hbox)
        #     self._octDialog.widgetDummy.show()

        #     # argument (v) here is a number - index pointing to a segment in allocated segments.
        #     def cb(v):
        #         #stack_widget.notify_segments(v)
        #         self._cross_widget.notify_segments(v)
        #     self._vtxengine._stack_tensor_endpoint.aggregate_segment_callback = cb

        #     # 
        #     def cb_volume(sample_idx, scan_idx, volume_idx):
        #         self._trace_widget.update_trace()
        #     self._vtxengine._stack_tensor_endpoint.volume_callback = cb_volume
        # else:
        #     # clear axes
        #     #self._cross_widget.notify_segments()
        #     self._trace_widget.clear()

        # put something into the scan queue
        self._vtxengine._engine.scan_queue.clear()
        self._vtxengine._engine.scan_queue.append(self._vtxengine._raster_scan)

        # now start the actual engine
        self._vtxengine._engine.start()

    def stopClicked(self):
        self._octDialog.pbStart.enabled = True
        self._octDialog.pbStop.enabled = False
        self._vtxengine._engine.stop()



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
