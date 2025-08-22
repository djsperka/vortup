import sys
from PyQt5.QtGui import QDoubleValidator, QIntValidator
from PyQt5.QtWidgets import QDialog
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


        # assign id to each radio button. then assign buttonClicked signal to a slot here. 
        # That signal is called once when a radio button is clicked. Use checkedId() in slot.
        self.buttonGroupSource.setId(self.rbAxsun100k, 1)
        self.buttonGroupSource.setId(self.rbCustom, 2)

        self.buttonGroupSource.buttonClicked.connect(self.rbClicked)
        self.initializeDialog(cfg)        # takes whatever is in cfg and inits dlg

        # slots for accept and cancel
        self.buttonBoxMain.accepted.connect(self.accepted)
        self.buttonBoxMain.rejected.connect(self.reject)

    def accepted(self):
        self._cfg = self.getEngineParameters()
        self.accept()

    def rbClicked(self):
        # if checked is one of the preset sources, assign those values. 
        match self.buttonGroupSource.checkedId():
            case 1:
                self.setClockSourceWidgetValues(source.Axsun100k)
            case 2:
                # When changing to "Custom", do not change values in widgets. 
                pass

    def setClockSourceRadioButton(self, sscfg: Source):
        if sscfg == source.Axsun100k:
            self.rbAxsun100k.setChecked(True)
        else:
            self.rbCustom.setChecked(True)
        
    def setClockSourceWidgetValues(self, sscfg: Source):
        self.lineEditTriggersPerSecond.setText(str(sscfg.triggers_per_second))
        self.lineEditClockRisingEdgesPerTrigger.setText(str(sscfg.clock_rising_edges_per_trigger))
        self.lineEditDutyCycle.setText(str(sscfg.duty_cycle))
        self.lineEditImagingDepth.setText(str(sscfg.imaging_depth_meters))

    def getClockSourceValues(self) -> Source:
        if self.rbAxsun100k.isChecked():
            return source.Axsun100k
        else:
            return Source(int(self.lineEditTriggersPerSecond.text()), int(self.lineEditClockRisingEdgesPerTrigger.text()), float(self.lineEditDutyCycle.text()), float(self.lineEditImagingDepth.text()))
        
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

        # Handle swept_source separately because of source types
        self.setClockSourceRadioButton(cfg.swept_source)
        self.setClockSourceWidgetValues(cfg.swept_source)

        self.checkBoxInternalClock.setChecked(cfg.internal_clock)
        self.lineEditInternalClockRate.setText(str(cfg.clock_samples_per_second))
        self.lineEditExternalClockLevelPct.setText(str(cfg.external_clock_level_pct))
        # input channel and clock channel ignored for now - we cannot load vortex.acquire.alazar....
        self.lineEditTriggerRange.setText(str(cfg.trigger_range_millivolts))
        self.lineEditTriggerLevelFraction.setText(str(cfg.trigger_level_fraction))

        self.lineEditBlocksToAllocate.setText(str(cfg.blocks_to_allocate))
        self.lineEditPreloadCount.setText(str(cfg.preload_count))
        self.lineEditProcessSlots.setText(str(cfg.process_slots))
        # self.lineEditDispersion0.setText(str(cfg.dispersion[0]))
        # self.lineEditDispersion1.setText(str(cfg.dispersion[1]))
        self.lineEditLogLevel.setText(str(cfg.log_level))
        self.cbSaveProfilerData.setChecked(cfg.save_profiler_data)

    def getEngineParameters(self) -> VtxEngineParams:
        s = self._cfg
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
        s.swept_source = self.getClockSourceValues()
        s.internal_clock = bool(self.checkBoxInternalClock.isChecked())
        s.external_clock_level_pct = int(self.lineEditExternalClockLevelPct.text())
        s.trigger_range_millivolts = int(self.lineEditTriggerRange.text())
        s.trigger_level_fraction = float(self.lineEditTriggerLevelFraction.text())
        s.blocks_to_allocate = int(self.lineEditBlocksToAllocate.text())
        s.preload_count = int(self.lineEditPreloadCount.text())
        s.process_slots = int(self.lineEditProcessSlots.text())
        #s.dispersion = (float(self.lineEditDispersion0.text()), float(self.lineEditDispersion1.text()))
        s.log_level = int(self.lineEditLogLevel.text())
        s.save_profiler_data = self.cbSaveProfilerData.isChecked()
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

