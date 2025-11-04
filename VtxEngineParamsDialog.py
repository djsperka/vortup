import sys
from PyQt5.QtGui import QDoubleValidator, QIntValidator
from PyQt5.QtWidgets import QDialog, QApplication
from DAQConst import ATS9350InputRange
from VtxEngineParams import VtxEngineParams, DEFAULT_VTX_ENGINE_PARAMS, AcquisitionType
from Ui_VtxEngineParamsDialog import Ui_VtxEngineParamsDialog
from vortex.engine import source, Source
from vortex import Range

class VtxEngineParamsDialog(QDialog, Ui_VtxEngineParamsDialog):
    """Dialog for setting VtxEngineParameters.     

    """
    def __init__(self, cfg: VtxEngineParams=DEFAULT_VTX_ENGINE_PARAMS):
        """Instantiate dialog for editing params in cfg.

        Args:
            cfg (StandardEngineParams, optional): Configuration to edit. Defaults to DEFAULT_ENGINE_PARAMS.

        """
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("OCT Engine Parameters")
        # uic.loadUi("VtxEngineParamsDialog.ui", self)

        # Set validators for some values

        # scientific notation for some
        v = QDoubleValidator()
        v.setNotation(QDoubleValidator.Notation.ScientificNotation)
        self.lineEditGalvoDelay.setValidator(v)

        # plain double validators
        v = QDoubleValidator(-10,10,3)
        self.lineEditGalvoXmin.setValidator(v)
        v = QDoubleValidator(-10,10,3)
        self.lineEditGalvoXmax.setValidator(v)
        v = QDoubleValidator(-10,10,3)
        self.lineEditGalvoYmin.setValidator(v)
        v = QDoubleValidator(-10,10,3)
        self.lineEditGalvoYmax.setValidator(v)
        
        v = QDoubleValidator(0,2,3)
        self.lineEditXUnitsPerVolt.setValidator(v)
        v = QDoubleValidator(0,2,3)
        self.lineEditYUnitsPerVolt.setValidator(v)

        self.lineEditBlocksToAllocate.setValidator(v)
        v = QIntValidator(1, 1000)
        self.lineEditPreloadCount.setValidator(v)
        v = QIntValidator(0, 16)
        self.lineEditProcessSlots.setValidator(v)

        v = QIntValidator(1000,1000000)
        self.lineEditInternalClockRate.setValidator(v)
        v = QIntValidator(1,100)
        self.lineEditExternalClockLevelPct.setValidator(v)
        v = QIntValidator(1,10000)
        self.lineEditTriggerRange.setValidator(v)
        v = QDoubleValidator()
        self.lineEditTriggerLevelFraction.setValidator(v)

        self.initializeDialog(cfg)        # takes whatever is in cfg and inits dlg

        # slots for accept and cancel
        self.buttonBoxMain.accepted.connect(self.accepted)
        self.buttonBoxMain.rejected.connect(self.reject)

    def accepted(self):
        self._cfg = self.getEngineParameters()        
        self.accept()
        
    def initializeDialog(self, cfg: VtxEngineParams):
        self._cfg = cfg
        if self._cfg.acquisition_type==AcquisitionType.ALAZAR_ACQUISITION:
            self.radioButtonAlazarAcquisition.setChecked(True)
        elif self._cfg.acquisition_type==AcquisitionType.FILE_ACQUISITION:
            self.radioButtonFileAcquisition.setChecked(True)

        self.lineEditGalvoDelay.setText(str(cfg.galvo_delay))

        self.lineEditGalvoXmin.setText(str(cfg.galvo_x_voltage_range.min))
        self.lineEditGalvoXmax.setText(str(cfg.galvo_x_voltage_range.max))
        self.lineEditGalvoYmin.setText(str(cfg.galvo_y_voltage_range.min))
        self.lineEditGalvoYmax.setText(str(cfg.galvo_y_voltage_range.max))
        self.lineEditXUnitsPerVolt.setText(str(cfg.galvo_x_units_per_volt))
        self.lineEditYUnitsPerVolt.setText(str(cfg.galvo_y_units_per_volt))

        self.lineEditTriggersPerSecond.setText(str(cfg.ssrc_triggers_per_second))
        self.lineEditClockRisingEdgesPerTrigger.setText(str(cfg.ssrc_clock_rising_edges_per_trigger))

        self.checkBoxInternalClock.setChecked(cfg.internal_clock)
        self.lineEditInternalClockRate.setText(str(cfg.clock_samples_per_second))
        self.lineEditExternalClockLevelPct.setText(str(cfg.external_clock_level_pct))

        self.comboBoxInputChannel.setCurrentText(cfg.input_channel)
        self.comboBoxClockChannel.setCurrentText(cfg.clock_channel)
        self.lineEditTriggerRange.setText(str(cfg.trigger_range_millivolts))
        self.lineEditTriggerLevelFraction.setText(str(cfg.trigger_level_fraction))

        self.lineEditBlocksToAllocate.setText(str(cfg.blocks_to_allocate))
        self.lineEditPreloadCount.setText(str(cfg.preload_count))
        self.lineEditProcessSlots.setText(str(cfg.process_slots))
        self.lineEditLogLevel.setText(str(cfg.log_level))
        self.cbSaveProfilerData.setChecked(cfg.save_profiler_data)

        # enum-using combo boxes....
        self.comboBoxInputRange.initialize(ATS9350InputRange, cfg.input_channel_range_millivolts)

        # clock and device sources
        self.lineEditGalvoClockSource.setText(cfg.galvo_clock_source)
        self.lineEditGalvoXDevice.setText(cfg.galvo_x_device_channel)
        self.lineEditGalvoYDevice.setText(cfg.galvo_y_device_channel)
        self.lineEditStrobeClockSource.setText(cfg.strobe_clock_source)
        self.lineEditStrobeDevice.setText(cfg.strobe_device_channel)

        # enable/disable
        self.groupBoxGalvo.setChecked(cfg.galvo_enabled)
        self.groupBoxStrobe.setChecked(cfg.strobe_enabled)


    def getEngineParameters(self) -> VtxEngineParams:
        s = VtxEngineParams()
        if self.radioButtonAlazarAcquisition.isChecked():
            s.acquisition_type = AcquisitionType.ALAZAR_ACQUISITION
        elif self.radioButtonFileAcquisition.isChecked():
            s.acquisition_type = AcquisitionType.FILE_ACQUISITION

        s.galvo_delay = float(self.lineEditGalvoDelay.text())
        s.galvo_x_voltage_range = Range(float(self.lineEditGalvoXmin.text()), float(self.lineEditGalvoXmax.text()))
        s.galvo_y_voltage_range = Range(float(self.lineEditGalvoYmin.text()), float(self.lineEditGalvoYmax.text()))
        s.galvo_x_units_per_volt = float(self.lineEditXUnitsPerVolt.text())
        s.galvo_y_units_per_volt = float(self.lineEditYUnitsPerVolt.text())

        s.clock_samples_per_second = int(self.lineEditInternalClockRate.text())
        s.ssrc_triggers_per_second = int(self.lineEditTriggersPerSecond.text())
        s.ssrc_clock_rising_edges_per_trigger = int(self.lineEditClockRisingEdgesPerTrigger.text())

        s.internal_clock = bool(self.checkBoxInternalClock.isChecked())
        s.external_clock_level_pct = int(self.lineEditExternalClockLevelPct.text())
        s.input_channel = self.comboBoxInputChannel.currentText()
        s.clock_channel = self.comboBoxClockChannel.currentText()
        s.trigger_range_millivolts = int(self.lineEditTriggerRange.text())
        s.trigger_level_fraction = float(self.lineEditTriggerLevelFraction.text())
        s.input_channel_range_millivolts = self.comboBoxInputRange.itemData(self.comboBoxInputRange.currentIndex())
        s.blocks_to_allocate = int(self.lineEditBlocksToAllocate.text())
        s.preload_count = int(self.lineEditPreloadCount.text())
        s.process_slots = int(self.lineEditProcessSlots.text())
        #s.dispersion = (float(self.lineEditDispersion0.text()), float(self.lineEditDispersion1.text()))
        s.log_level = int(self.lineEditLogLevel.text())
        s.save_profiler_data = self.cbSaveProfilerData.isChecked()

        # enable/disable
        s.galvo_enabled = self.groupBoxGalvo.isChecked()
        s.strobe_enabled = self.groupBoxStrobe.isChecked()

        # clock source stuff added
        s.galvo_clock_source = self.lineEditGalvoClockSource.text()
        s.galvo_x_device_channel = self.lineEditGalvoXDevice.text()
        s.galvo_y_device_channel = self.lineEditGalvoYDevice.text()
        s.strobe_clock_source = self.lineEditStrobeClockSource.text()
        s.strobe_device_channel = self.lineEditStrobeDevice.text()
        return s


if __name__ == '__main__':

    app = QApplication(sys.argv)
    dlg = VtxEngineParamsDialog(DEFAULT_VTX_ENGINE_PARAMS)
    dlg.show()
    app.exec_()
    print("exec() done")
    params = dlg._cfg
    dlg2 = VtxEngineParamsDialog(params)
    dlg2.exec()
    # app.exec_()

