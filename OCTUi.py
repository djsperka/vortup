import sys
import os
from VtxEngineParams import DEFAULT_VTX_ENGINE_PARAMS, VtxEngineParams
from VtxEngineParamsDialog import VtxEngineParamsDialog
from VtxEngine import VtxEngine
from OCTDialog import OCTDialog
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout, QFileDialog, QMessageBox
from vortex_tools.ui.display import RasterEnFaceWidget, CrossSectionImageWidget
from vortex.scan import RasterScanConfig
from vortex.storage import HDF5StackUInt16, HDF5StackInt8, HDF5StackConfig, HDF5StackHeader, SimpleStackUInt16, SimpleStackInt8, SimpleStackConfig, SimpleStackHeader
from TraceWidget import TraceWidget
from AcqParams import AcqParams, DEFAULT_ACQ_PARAMS
import logging
from rainbow_logging_handler import RainbowLoggingHandler
import cupy
import numpy
import traceback

class OCTUi():
    
    def __init__(self):
        super().__init__() # Call the inherited class' __init__ method
        self._logger = logging.getLogger('OCTUi')
        self._vtxengine = None
        self._cross_widget = None
        self._trace_widget = None
        self._engineParams = DEFAULT_VTX_ENGINE_PARAMS
        self._scanConfig = RasterScanConfig()
        self._acqParams = DEFAULT_ACQ_PARAMS
        self._typeExt = None

        self._octDialog = OCTDialog()
        self._octDialog.pbSelectFile.setEnabled(False)
        self._octDialog.cbSaveToDisk.toggled.connect(self._octDialog.pbSelectFile.setEnabled)
        self._octDialog.pbSelectFile.clicked.connect(self.selectFileClicked)
        self._octDialog.pbEtc.clicked.connect(self.etcClicked)
        self._octDialog.pbStart.clicked.connect(self.startClicked)
        self._octDialog.pbStop.clicked.connect(self.stopClicked)
        self._octDialog.pbStart.enabled = True  
        self._octDialog.pbStop.enabled = False  
        #self.addPlotsToDialog()
        self._octDialog.resize(1000,800)              
        self._octDialog.show()

    def selectFileClicked(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog


        # When the user hits Cancel, the filename returned is empty.
        bTryAgain = True
        self._typeExt = None
        self._saveFilename = None
        while bTryAgain:
            fileName, _ = QFileDialog.getSaveFileName(self._octDialog,"Filename for OCT data","","MATLAB (*.mat);;HD5 (*.h5);;Numpy (*.npy)", options=options)
            if fileName:
                d = os.path.dirname(fileName)
                b = os.path.basename(fileName)
                n,ext = os.path.splitext(b)
                print("dir: {0:s} base: {1:s} n: {2:s} ext: {3:s}".format(d,b,n,ext))
                if ext:
                    match ext.lower():
                        case '.mat':
                            self._typeExt = 'mat'
                            bTryAgain = False
                        case 'h5':
                            self._typeExt = '.h5'
                            bTryAgain = False
                        case 'npy':
                            self._typeExt = '.npy'
                            bTryAgain = False
                else:
                    bTryAgain = True
            else:
                bTryAgain = False
            if bTryAgain:
               QMessageBox.information(self._octDialog, "Oops", "Cannot determine file type. Please choose a file with extension \".mat\", \".h5\", or \".npy\".")
            else:
                self._saveFilename = fileName
                print("Got output filename: {0:s}".format(self._saveFilename))

    def etcClicked(self):
        self._cfgDialog = VtxEngineParamsDialog(self._engineParams)
        self._cfgDialog.finished.connect(self.etcFinished)
        self._cfgDialog.show()

    def etcFinished(self, v):
        if v == 1:
            self._engineParams = self._cfgDialog.getEngineParameters()

    def addPlotsToDialog(self):

        # We need access to both the engine (the endpoints) and the gui (display widgets). 
        if not self._cross_widget:
            self._raster_widget = RasterEnFaceWidget(self._vtxengine._stack_tensor_endpoint)
            self._cross_widget = CrossSectionImageWidget(self._vtxengine._stack_tensor_endpoint)
            self._trace_widget = TraceWidget(self._vtxengine._stack_tensor_endpoint)

            # 
            vbox = QVBoxLayout()
            hbox = QHBoxLayout()
            hbox.addWidget(self._raster_widget)
            hbox.addWidget(self._cross_widget)
            vbox.addLayout(hbox)
            vbox.addWidget(self._trace_widget)
            self._octDialog.widgetDummy.setLayout(vbox)
            self._octDialog.widgetDummy.show()

        else:
            self._cross_widget._endpoint = self._vtxengine._stack_tensor_endpoint
            self._trace_widget._endpoint = self._vtxengine._stack_tensor_endpoint

        self._vtxengine._stack_tensor_endpoint.aggregate_segment_callback = self.cb_segments
        self._vtxengine._stack_tensor_endpoint.volume_callback = self.cb_volume

    def cb_segments(self, v):
        # argument (v) here is a number - index pointing to a segment in allocated segments.
        self._raster_widget.notify_segments(v)
        self._cross_widget.notify_segments(v)

    def cb_volume(self, sample_idx, scan_idx, volume_idx):
        self._trace_widget.update_trace()


    def startClicked(self):
        self._octDialog.pbEtc.setEnabled(False)
        self._octDialog.pbStart.setEnabled(False)
        self._octDialog.pbStop.setEnabled(True)

        try:
            # fetch current configuration for acq and scan params. The items 
            # in the engineConfig are updated when that dlg is accepted, so no 
            # fetch here.
            self._acqParams = self._octDialog.acqParamsWidget.getAcqParams()
            self._scanConfig = self._octDialog.scanConfigWidget.getScanConfig()

            # get oct engine ready
            if self._vtxengine:
                if not self._vtxengine._engine.done:
                    self._logger.warning('engine is not stopped')
                    return
                del self._vtxengine
            self._vtxengine = None

            # create engine

            self._vtxengine = VtxEngine(self._engineParams, self._acqParams, self._scanConfig)

            # put something into the scan queue
            self._vtxengine._engine.scan_queue.clear()
            self._vtxengine._engine.scan_queue.append(self._vtxengine._raster_scan)

            # setup plots
            self.addPlotsToDialog()

            # now start the actual engine
            self._vtxengine._engine.start()

        except RuntimeError as e:
            print("RuntimeError:")
            traceback.print_exception(e)
            sys.exit(-1)


    def stopClicked(self):
        self._octDialog.pbEtc.setEnabled(True)
        self._octDialog.pbStart.setEnabled(True)
        self._octDialog.pbStop.setEnabled(False)
        self._vtxengine._engine.stop()



def setup_logging():
    # configure the root logger to accept all records
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.NOTSET)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("OCTUi").setLevel(logging.WARNING)

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
