import sys
import os
from VtxEngineParamsDialog import VtxEngineParamsDialog
from VtxEngine import VtxEngine
from OCTDialog import OCTDialog
from OCTUiParams import OCTUiParams
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout
from PyQt5.QtWidgets import QMessageBox
from vortex import get_console_logger as gcl
from vortex_tools.ui.display import RasterEnFaceWidget, CrossSectionImageWidget
from vortex.scan import RasterScan
from vortex.storage import SimpleStackConfig, SimpleStackHeader
from vortex.engine import Engine
from BScanTraceWidget import BScanTraceWidget
import logging
from typing import Tuple
from rainbow_logging_handler import RainbowLoggingHandler
import traceback
import matplotlib as mpl
from datetime import datetime

class OCTUi():
    
    def __init__(self):
        super().__init__() # Call the inherited class' __init__ method
        self._logger = logging.getLogger('OCTUi')
        self._vtxengine = None
        self._cross_widget = None
        self._trace_widget = None
        self._savingVolumesNow = False
        self._savingVolumesStopNow = False
        self._savingVolumesThisMany = 0
        self._savingVolumesThisManySaved = 0
        self._savingVolumesRequested = False

        # load config file - default file only!
        # TODO - make it configurable, or be able to load a diff't config.
        self._params = OCTUiParams()

        self._octDialog = OCTDialog()

        # initializations
        self._octDialog.widgetDispersion.setDispersion(self._params.dsp)
        self._octDialog.widgetDispersion.valueChanged.connect(self.dispersionChanged)
        self._octDialog.widgetScanConfig.setScanParams(self._params.scn)
        self._octDialog.widgetAcqParams.setAcqParams(self._params.acq)

        # connections. 
        self._octDialog.gbSaveVolumes.saveNVolumes.connect(self.saveNVolumes)
        self._octDialog.gbSaveVolumes.saveContVolumes.connect(self.saveContVolumes)
        self._octDialog.gbSaveVolumes.enableSaving(False)
        self._octDialog.dialogClosing.connect(self.dialogClosing)
        self._octDialog.pbEtc.clicked.connect(self.etcClicked)
        self._octDialog.pbStart.clicked.connect(self.startClicked)
        self._octDialog.pbStop.clicked.connect(self.stopClicked)
        self._octDialog.pbStart.enabled = True  
        self._octDialog.pbStop.enabled = False  
        self._octDialog.resize(1000,800)              
        self._octDialog.show()

    def dispersionChanged(self, dispersion: Tuple[float, float]):
        if self._vtxengine is not None:
            self._vtxengine.update_dispersion(dispersion)   
            print("Updated dispersion ", dispersion)

    def dialogClosing(self):
        self._getAllParams()
        if self._params.isdirty():
            dlg = QMessageBox(self._octDialog)
            dlg.setWindowTitle("OCTUi is exiting...")
            dlg.setText("Save engine parameters?")
            dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            dlg.setIcon(QMessageBox.Question)
            button = dlg.exec()
            if button == QMessageBox.Yes:
                self._logger.info("Saving engine parameters...")
                self._params.save()

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
            self._raster_widget = RasterEnFaceWidget(self._vtxengine._endpoint_ascan_display, cmap=mpl.colormaps['gray'])
            self._cross_widget = CrossSectionImageWidget(self._vtxengine._endpoint_ascan_display, cmap=mpl.colormaps['gray'])
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
            self._raster_widget._endpoint = self._vtxengine._endpoint_ascan_display
            self._cross_widget._endpoint = self._vtxengine._endpoint_ascan_display
            self._ascan_trace_widget._endpoint = self._vtxengine._endpoint_ascan_display
            self._spectra_trace_widget._endpoint = self._vtxengine._endpoint_spectra_display

        def cb_ascan(v):
            self._cross_widget.notify_segments(v)
            self._raster_widget.notify_segments(v)
            self._ascan_trace_widget.update_trace(v)
        self._vtxengine._endpoint_ascan_display.aggregate_segment_callback = cb_ascan

        def cb_spectra(v):
             self._spectra_trace_widget.update_trace(v)
        self._vtxengine._endpoint_spectra_display.aggregate_segment_callback = cb_spectra

    # def cb_segments(self, v):
    #     # argument (v) here is a number - index pointing to a segment in allocated segments.
    #     #print("agg segment cb: v=", v)
    #     self._raster_widget.notify_segments(v)
    #     self._cross_widget.notify_segments(v)
    #     self._ascan_trace_widget.update_trace(v)
    #     self._spectra_trace_widget.update_trace(v)

    def _getAllParams(self):
        # fetch current configuration for acq and scan params. The items 
        # in the engineConfig are updated when that dlg is accepted, so no 
        # fetch here.
        self._params.acq = self._octDialog.widgetAcqParams.getAcqParams()
        self._params.scn = self._octDialog.widgetScanConfig.getScanParams()
        self._params.dsp = self._octDialog.widgetDispersion.getDispersion()


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
            # update params with ui 
            self._getAllParams()

            # get oct engine ready
            if self._vtxengine:
                if not self._vtxengine._engine.done:
                    self._logger.warning('engine is not stopped')
                    return
                del self._vtxengine
            self._vtxengine = None

            # create engine
            self._logger.info('Setting up OCT engine...')
            self._vtxengine = VtxEngine(self._params)
            self._vtxengine._engine.event_callback = self.engineEventCallback
            self._vtxengine._null_endpoint.volume_callback = self.volumeCallback
            self._vtxengine._endpoint_spectra_storage.volume_callback = self.volumeCallback2
            #self._vtxengine._null_endpoint.segment_callback = self.segmentCallback
            #self._vtxengine._null_endpoint.aggregate_segment_callback = self.aggregateSegmentCallback
            #self._vtxengine._null_endpoint.scan_callback = self.scanCallback

            # put something into the scan queue
            self._raster_scan = RasterScan()
            self._raster_scan.initialize(self._params.rsc)
            self._vtxengine._engine.scan_queue.clear()
            self._vtxengine._engine.scan_queue.append(self._raster_scan)

            # setup plots
            self.addPlotsToDialog()

            # now start the actual engine
            self._vtxengine._engine.start()

            # status timer


        except RuntimeError as e:
            print("RuntimeError:")
            traceback.print_exception(e)
            sys.exit(-1)

    def engineEventCallback(self, event, thingy):
        if event == Engine.Event.Start:
            self._octDialog.gbSaveVolumes.enableSaving(True)
        elif event == Engine.Event.Shutdown:
            self._octDialog.gbSaveVolumes.enableSaving(False)
        elif event == Engine.Event.Error:
            self._logger.error("Error event from engine.")
            self.stopClicked()

    def stopClicked(self):
        if self._vtxengine is not None:
            self._octDialog.pbEtc.setEnabled(True)
            self._octDialog.pbStart.setEnabled(True)
            self._octDialog.pbStop.setEnabled(False)
            self._vtxengine.stop()

    def scanCallback(self, arg0, arg1):
        self._logger.info("scanCallback({0:d}, {1:d}, {2:d}, {3:d})".format(arg0, arg1))

    def segmentCallback(self, arg0, arg1, arg2, arg3):
        self._logger.info("segmentCallback({0:d}, {1:d}, {2:d}, {3:d})".format(arg0, arg1, arg2, arg3))

    def aggregateSegmentCallback(self, v):
        self._logger.info("aggregateSegmentCallback({0:s})".format(str(v)))

    def volumeCallback(self, arg0, arg1, arg2):
        """volume callback that is (should be) called prior to other volume callbacks. 
        Because of that arrangement, this callback will open storage. Same storage is closed 
        in volumeCallback2

        Args:
            sample_idx (int): sample index
            scan_idx (int): scan index
            volume_idx (int): volume index
        """

        #self._logger.info("volumeCallback({0:d}, {1:d}, {2:d})".format(arg0, arg1, arg2))
        if self._savingVolumesRequested:
            (bOK, filename) = self.checkFileSaveStuff()
            if bOK:
                # Create SimpleStackConfig to config storage
                npsc = SimpleStackConfig()
                npsc.shape = (self._params.scn.bscans_per_volume, self._params.scn.ascans_per_bscan, self._params.acq.samples_per_ascan, 1)
                npsc.header = SimpleStackHeader.NumPy
                npsc.path = filename
                self._logger.info('Open storage.')
                self._vtxengine._spectra_storage.open(npsc)
                self._savingVolumesNow = True
                self._savingVolumesRequested = False
                #self._savingVolumesThisMany = SHOULD HAVE BEEN SET IN PB CALLBACK WHEN SAVING VOLUMES REQUESTED
                self._savingVolumesThisManySaved = 0
                self._octDialog.gbSaveVolumes.enableSaving(False, self._savingVolumesThisMany==0)
            else:
                self._logger.warning("Cannot open file {0:s} for saving.".format(filename))
                self._savingVolumesRequested = False

    def volumeCallback2(self, arg0, arg1, arg2):
        """This callback will close a file if opened.

        Args:
            arg0 (_type_): _description_
            arg1 (_type_): _description_
            arg2 (_type_): _description_
        """
        if self._savingVolumesNow:

            # this is called after the current volume has been written
            self._savingVolumesThisManySaved = self._savingVolumesThisManySaved + 1

            if self._savingVolumesStopNow or (self._savingVolumesThisMany > 0 and self._savingVolumesThisManySaved == self._savingVolumesThisMany):

                self._logger.info("Saved {0:d} volumes.".format(self._savingVolumesThisManySaved))
                # close file
                self._savingVolumesNow = False
                self._savingVolumesStopNow = False
                self._savingVolumesThisManySaved = 0
                self._savingVolumesThisMany = 0
                self._savingVolumesRequested = False
                self._vtxengine._spectra_storage.close()
                self._octDialog.gbSaveVolumes.enableSaving(True)


    def checkFileSaveStuff(self) -> Tuple[bool, str]:
        """This function will verify that the file save root folder is accessible. If so, 
        a new folder with the name yyyy-MM-dd is created (if it doesn't already exist). A new 
        filename is generated and returned. 
        """

        # Try to create new folder
        now = datetime.now()
        sFolder = now.strftime('%Y-%m-%d')
        sFile = now.strftime('%Y-%m-%d-%H%M%S.npy')
        p = self._octDialog.gbSaveVolumes.pathDataRoot / sFolder
        p.mkdir(parents=True, exist_ok=True)
        return (True, str(p / sFile))

    def saveNVolumes(self, n: int):
        self._savingVolumesRequested = True
        self._savingVolumesThisMany = n
        self._octDialog.gbSaveVolumes.enableSaving(False, False)

    def saveContVolumes(self):
        """This slot is called when the "Save Continuous" button is pushed. If not currently saving, then 
        proceed to open the file and start saving. If already saving, though, this button is a toggle and 
        should stop saving.
        """

        if not self._savingVolumesNow:
            self._savingVolumesRequested = True
            self._savingVolumesThisMany = 0
            self._octDialog.gbSaveVolumes.enableSaving(False, True)
        else:
            self._savingVolumesStopNow = True




def setup_logging():

    # format
    DATE_FORMAT = "%d-%b-%Y %H:%M:%S"
    #FORMAT = '%(asctime)s.%(msecs)03d [%(name)s] %(filename)s:%(lineno)d\t%(levelname)s:\t%(message)s'
    FORMAT = '[%(asctime)s.%(msecs)d] %(name)s\t(%(levelname).1s) %(message)s'
    logging.basicConfig(format=FORMAT, datefmt=DATE_FORMAT, level=logging.DEBUG)

    # This was in  the examples, not sure why.
    logging.getLogger("matplotlib").setLevel(logging.WARNING)


    # # set up colored logging to console
    # formatter = logging.Formatter('%(asctime)s.%(msecs)03d [%(name)s] %(filename)s:%(lineno)d\t%(levelname)s:\t%(message)s')
    # console_handler = RainbowLoggingHandler(sys.stderr)
    # console_handler.setFormatter(formatter)
    # root_logger.addHandler(console_handler)


def setup_plotting():
    mpl.rcParams['axes.facecolor'] = 'k'
    mpl.rcParams['lines.linewidth'] = 1


if __name__ == '__main__':
    setup_logging()
    setup_plotting()
    app = QApplication(sys.argv)
    octui = OCTUi()
    app.exec_()
