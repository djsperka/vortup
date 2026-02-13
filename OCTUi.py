import sys
import os
from VtxEngineParamsDialog import VtxEngineParamsDialog
from VtxEngine import VtxEngine
from OCTUiMainWindow import OCTUiMainWindow
from OCTUiParams import OCTUiParams
from PyQt5.QtWidgets import QApplication, QMessageBox, QLabel
from PyQt5.QtCore import QTimer,QDateTime
from vortex.engine import Engine, EngineConfig, EngineStatus
from vortex import get_console_logger as gcl
from vortex.storage import SimpleStackConfig, SimpleStackHeader
from ScanGUIHelper import ScanGUIHelper
from scanGUIHelperFactory import scanGUIHelperFactory
import logging
from typing import Tuple
import traceback
import matplotlib as mpl
from datetime import datetime
from json import dumps

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
        self._timer=QTimer()
        self._timer.timeout.connect(self.showTime)
        self._guihelpers = []

        # load config file - default file only!
        # TODO - make it configurable, or be able to load a diff't config.
        self._params = OCTUiParams()

        self._octDialog = OCTUiMainWindow()

        # add a permanent status widget to the status bar
        self._labelEngineStatus = QLabel("Not started...")
        self._octDialog.statusBar().addPermanentWidget(self._labelEngineStatus)

        # remove this now. By default the stacked widget comes with a single page.
        self._octDialog.stackedWidgetDummy.removeWidget(self._octDialog.stackedWidgetDummyPage1)


        # Create and initialize GUI Helpers
        for number,(name,cfg) in enumerate(self._params.scn.scans.items()):
            flag = 1<<number
            self._logger.info("Found scan config {0:s},{1:x}".format(name,flag))
            # are there settings for this scan config? 
            if name in self._params.settings:
                s = self._params.settings[name]
                self._logger.debug("Found settings: {0:s}".format(dumps(s)))
            else:
                s = {}

            self._guihelpers.append(scanGUIHelperFactory(name, flag, cfg, s))
            self._octDialog.widgetScanConfig.addScanType(name, self._guihelpers[-1].edit_widget)
            #self._octDialog.stackedWidgetDummy.addWidget(self._guihelpers[-1].plot_widget)

        self._octDialog.widgetScanConfig.setCurrentIndex(self._params.scn.current_index)
        #self._octDialog.stackedWidgetDummy.setCurrentIndex(self._params.scn.current_index)

        # connections. 
        #self._octDialog.widgetDispersion.valueChanged.connect(self.dispersionChanged)
        self._octDialog.widgetScanConfig.scanTypeChanged.connect(self.scanTypeChanged)
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

    def scanTypeChanged(self, index: int):
        self._params.scn.current_index = index
        # only do this if the engine exists. 
        # This isn't a clean way to test, as the existence of the engine might
        # not be the best test here. 
        if self._vtxengine:        
            self._octDialog.stackedWidgetDummy.setCurrentIndex(index)
        helper = self._guihelpers[index]
        self.connectCurrentScan(helper)

    def dispersionChanged(self, dispersion: Tuple[float, float]):
        if self._vtxengine is not None:
            self._vtxengine.update_dispersion(dispersion)   
            print("Updated dispersion ", dispersion)

    def dialogClosing(self):
        self.stopClicked()
        self._getAllParams()
        self._getPlotSettings()
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

    def _getAllParams(self):
        # fetch current configuration for acq and scan params. The items 
        # in the engineConfig are updated when that dlg is accepted, so no 
        # fetch here.
        self._params.scn = self._octDialog.widgetScanConfig.getScanParams()

    def _getPlotSettings(self):

        # get settings if components have been created. 
        # If one of the helpers has no components, then they all probably do not. 
        if all(helper.has_components() for helper in self._guihelpers):
            settings = {}
            for helper in self._guihelpers:
                settings[helper.name] = helper.getSettings()
            self._params.settings = settings

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

            # # HACK 
            # from VtxEngineParams import AcquisitionType
            # self._params.vtx.acquisition_type = AcquisitionType.FILE_ACQUISITION
            # self._logger.warning('USING FILE ACQUISITION')

            # get oct engine ready
            if self._vtxengine:
                if not self._vtxengine._engine.done:
                    self._logger.warning('engine is not stopped')
                    return
                del self._vtxengine
            self._vtxengine = None

            # create engine
            self._logger.info('Setting up OCT engine...')
            self._vtxengine = VtxEngine(self._params, self._guihelpers)
            self._vtxengine._engine.event_callback = self.engineEventCallback

            # Clear out widgets previously located in the stacked widget, then add
            # newly-created plots. 
            for i in range(self._octDialog.stackedWidgetDummy.count()):
                self._octDialog.stackedWidgetDummy.removeWidget(self._octDialog.stackedWidgetDummy.widget(0))
                
            for helper in self._guihelpers:
                self._octDialog.stackedWidgetDummy.addWidget(helper.components.plot_widget)

            # make plots visible
            self._octDialog.stackedWidgetDummy.setCurrentIndex(self._params.scn.current_index)


            self._vtxengine._engine.scan_queue.clear()
            self.connectCurrentScan(self._guihelpers[self._params.scn.current_index])


            # now start the actual engine
            self._vtxengine._engine.start()

            # status timer
            self._timer.start(1000)


        except RuntimeError as e:
            print("RuntimeError:")
            traceback.print_exception(e)
            sys.exit(-1)

    def connectCurrentScan(self, helper: ScanGUIHelper): 

        if helper.has_components():

            helper.components.null_endpoint.volume_callback = self.volumeCallback
            helper.components.storage_endpoint.volume_callback = self.volumeCallback2

            # the engine might not yet be created, if this is initialization
            if self._vtxengine:
                self._logger.info('Connect scan \'{0:s}\' to engine.'.format(helper.name))
                self._vtxengine._engine.scan_queue.interrupt(helper.getScan())
            else:
                self._logger.info('Cannot connect scan \'{0:s}\' to engine yet...'.format(helper.name))

        else:
            self._logger.info('Cannot connect scan \'{0:s}\' to engine (no components yet)...'.format(helper.name))


        
    def showTime(self):
        current_time=QDateTime.currentDateTime()
        formatted_time=current_time.toString('yyyy-MM-dd hh:mm:ss dddd')
        #self._logger.info(formatted_time)
        self._octDialog.statusBar().showMessage(formatted_time)
        status = self._vtxengine._engine.status()
        if status.active:
            self._labelEngineStatus.setText("Active: blk_util {0:f} disp_blks {2:d}".format(status.block_utilization, status.dispatched_blocks, status.inflight_blocks))
        else:
            self._labelEngineStatus.setText("Not running.")


    def engineEventCallback(self, event, thingy):
        if event == Engine.Event.Start:
            self._octDialog.gbSaveVolumes.enableSaving(True)
        elif event == Engine.Event.Shutdown:
            self._octDialog.gbSaveVolumes.enableSaving(False)
        elif event == Engine.Event.Error:
            self._logger.error("Error event from engine.")
            #self.stopClicked()

    def printStatus(self, s):
        if self._vtxengine is not None:
            status = self._vtxengine._engine.status()
            self._logger.info(s + "\nactive? {0:d}\nblock_utilization {1:f}\ndispatch_completion {2:f}\ndispatched_blocks {3:d}\ninflight_blocks {4:d}\n".format(status.active, status.block_utilization, status.dispatch_completion, status.dispatched_blocks, status.inflight_blocks))

    def stopClicked(self):
        self._timer.stop()
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


        # shape for raster is (BperV, AperB, depth)
        # For an aiming scan, each "cross" consists of 2 b-scans

        helper = self._guihelpers[self._params.scn.current_index]
        shape = helper.components.spectra_endpoint.tensor.shape
        #self._logger.info("volumeCallback({0:d}, {1:d}, {2:d}),helper={3:s},shape=({4:d},{5:d},{6:d})".format(arg0, arg1, arg2, helper.name,shape[0], shape[1], shape[2]))
        if self._savingVolumesRequested:
            (bOK, filename) = self.checkFileSaveStuff()
            if bOK:
                # Create SimpleStackConfig to config storage
                npsc = SimpleStackConfig()

                # shape is a mystery. Let's just copy what the endpoint is. 
                # TODO Must figure out why this volume doesn't match acq params (see esp. non-raster scan)
                #npsc.shape = (self._params.scn.bscans_per_volume, self._params.scn.ascans_per_bscan, self._params.acq.samples_per_ascan, 1)
                self._logger.info("volumeCallback:({0:d}, {1:d}, {2:d}),helper={3:s},shape=({4:d},{5:d},{6:d})".format(arg0, arg1, arg2, helper.name,shape[0], shape[1], shape[2]))
                npsc.shape = (shape[0], shape[1], shape[2], 1)
                npsc.header = SimpleStackHeader.NumPy
                npsc.path = filename
                self._logger.info('Open storage.')
                helper.components.storage.open(npsc)
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
                helper = self._guihelpers[self._params.scn.current_index]
                helper.components.storage.close()
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
