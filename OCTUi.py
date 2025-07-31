import sys
import os
from VtxEngineParams import DEFAULT_VTX_ENGINE_PARAMS, FileSaveConfig
from VtxEngineParamsDialog import VtxEngineParamsDialog
from VtxEngine import VtxEngine
from OCTDialog import OCTDialog
from OCTUiParams import OCTUiParams
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout
from vortex import get_console_logger as gcl
from vortex_tools.ui.display import RasterEnFaceWidget, CrossSectionImageWidget
from vortex.scan import RasterScanConfig, RasterScan
from vortex.storage import HDF5StackUInt16, HDF5StackInt8, HDF5StackConfig, HDF5StackHeader, SimpleStackUInt16, SimpleStackInt8, SimpleStackConfig, SimpleStackHeader
#from TraceWidget import TraceWidget
from BScanTraceWidget import BScanTraceWidget
from AcqParams import AcqParams, DEFAULT_ACQ_PARAMS
import logging
from rainbow_logging_handler import RainbowLoggingHandler
import cupy
import numpy
import traceback
import matplotlib as mpl

class OCTUi():
    
    def __init__(self):
        super().__init__() # Call the inherited class' __init__ method
        self._logger = logging.getLogger('OCTUi')
        self._vtxengine = None
        self._cross_widget = None
        self._trace_widget = None
        self._saveFilenameAscans = ''
        self._typeExtAscans = ''
        self._saveFilenameSpectra = ''
        self._typeExtSpectra = ''

        # load config file - default file only!
        # TODO - make it configurable, or be able to load a diff't config.
        self._params = OCTUiParams()

        self._octDialog = OCTDialog()

        # connections. 
        self._octDialog.pbEtc.clicked.connect(self.etcClicked)
        self._octDialog.pbStart.clicked.connect(self.startClicked)
        self._octDialog.pbStop.clicked.connect(self.stopClicked)
        self._octDialog.pbStart.enabled = True  
        self._octDialog.pbStop.enabled = False  
        self._octDialog.resize(1000,800)              
        self._octDialog.show()

    def etcClicked(self):
        self._cfgDialog = VtxEngineParamsDialog(self._params.vtx)
        self._cfgDialog.finished.connect(self.etcFinished)
        self._cfgDialog.show()

    def etcFinished(self, v):
        if v == 1:
            self._params.vtx = self._cfgDialog.getEngineParameters()

    def addPlotsToDialog(self):

        # We need access to both the engine (the endpoints) and the gui (display widgets). 
        if not self._cross_widget:
            self._raster_widget = RasterEnFaceWidget(self._vtxengine._endpoint_ascan_display)
            self._cross_widget = CrossSectionImageWidget(self._vtxengine._endpoint_ascan_display)
            self._ascan_trace_widget = BScanTraceWidget(self._vtxengine._endpoint_ascan_display, title="ascan")

            self._spectra_trace_widget = BScanTraceWidget(self._vtxengine._endpoint_spectra_display, title="raw spectra")

            # 
            vbox = QVBoxLayout()
            hbox_upper = QHBoxLayout()
            hbox_upper.addWidget(self._raster_widget)
            hbox_upper.addWidget(self._cross_widget)
            hbox_lower = QHBoxLayout()
            hbox_lower.addWidget(self._spectra_trace_widget)
            hbox_lower.addWidget(self._ascan_trace_widget)
            vbox.addLayout(hbox_upper)
            vbox.addLayout(hbox_lower)
            self._octDialog.widgetDummy.setLayout(vbox)
            self._octDialog.widgetDummy.show()

        else:
            self._raster_widget._endpoint = self._vtxengine._endpoint_spectra_display
            self._cross_widget._endpoint = self._vtxengine._endpoint_ascan_display
            self._ascan_trace_widget._endpoint = self._vtxengine._endpoint_ascan_display
            self._spectra_trace_widget._endpoint = self._vtxengine._endpoint_spectra_display

        def cb_ascan(v):
            self._cross_widget.notify_segments(v)
            self._ascan_trace_widget.update_trace(v)
        self._vtxengine._endpoint_ascan_display.aggregate_segment_callback = cb_ascan

        def cb_spectra(v):
            self._raster_widget.notify_segments(v)
            self._spectra_trace_widget.update_trace(v)
        self._vtxengine._endpoint_spectra_display.aggregate_segment_callback = cb_spectra


        #self._vtxengine._endpoint_ascan_display.volume_callback = self.cb_volume

    def cb_segments(self, v):
        # argument (v) here is a number - index pointing to a segment in allocated segments.
        #print("agg segment cb: v=", v)
        self._raster_widget.notify_segments(v)
        self._cross_widget.notify_segments(v)
        self._ascan_trace_widget.update_trace(v)
        self._spectra_trace_widget.update_trace(v)

    def cb_volume(self, sample_idx, scan_idx, volume_idx):
        print("volume cb: sample_idx=",sample_idx, "scan_idx=", scan_idx, "volume_idx=", volume_idx)
        self._trace_widget.update_trace()


    def startClicked(self):
        self._octDialog.pbEtc.setEnabled(False)
        self._octDialog.pbStart.setEnabled(False)
        self._octDialog.pbStop.setEnabled(True)

        # check if profiling was requested
        if self._params.vtx.save_profiler_data:
            os.environ['VORTEX_PROFILER_LOG'] = 'profiler.log'
        elif os.environ.get('VORTEX_PROFILER_LOG') is not None:
            os.environ['VORTEX_PROFILER_LOG'] = ''

        # now build engine
        try:
            # fetch current configuration for acq and scan params. The items 
            # in the engineConfig are updated when that dlg is accepted, so no 
            # fetch here.
            self.acq = self._octDialog.widgetAcqParams.getAcqParams()
            self.scn = self._octDialog.widgetScanConfig.getScanConfig()
            self._filesaveAscans = self._octDialog.widgetAscansFileSave.getFileSaveConfig()
            self._filesaveSpectra = self._octDialog.widgetSpectraFileSave.getFileSaveConfig()

            # get oct engine ready
            if self._vtxengine:
                if not self._vtxengine._engine.done:
                    self._logger.warning('engine is not stopped')
                    return
                del self._vtxengine
            self._vtxengine = None

            # create engine

            self._vtxengine = VtxEngine(self._params.vtx, self._params.acq, self._params.scn, self._filesaveAscans, self._filesaveSpectra)

            # put something into the scan queue
            self._raster_scan = RasterScan()
            self._raster_scan.initialize(self._params.scn)
            self._vtxengine._engine.scan_queue.clear()
            self._vtxengine._engine.scan_queue.append(self._raster_scan)

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
        self._vtxengine.stop()



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


def setup_plotting():
    mpl.rcParams['axes.facecolor'] = 'k'
    mpl.rcParams['lines.linewidth'] = 1


if __name__ == '__main__':
    setup_logging()
    setup_plotting()
    app = QApplication(sys.argv)
    octui = OCTUi()
    app.exec_()
