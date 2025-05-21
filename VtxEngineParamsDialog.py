import sys
from PyQt5.QtWidgets import QDialog, QApplication
from PyQt5.QtGui import QDoubleValidator, QIntValidator
from PyQt5 import uic
from VtxEngineParams import VtxEngineParams, DEFAULT_VTX_ENGINE_PARAMS
from Ui_VtxEngineParamsDialog import Ui_VtxEngineParamsDialog
from vortex.engine import source, Source

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
        v = QDoubleValidator()
        v.setNotation(QDoubleValidator.Notation.ScientificNotation)
        self.lineEditTriggerDelay.setValidator(v)

        # plain double validators
        v = QDoubleValidator()
        v.setNotation(QDoubleValidator.Notation.ScientificNotation)
        self.lineEditDispersion0.setValidator(v)
        v = QDoubleValidator()
        v.setNotation(QDoubleValidator.Notation.ScientificNotation)
        self.lineEditDispersion1.setValidator(v)

        # int validators
        v = QIntValidator(0,10)
        self.lineEditScanDimension.setValidator(v)
        v = QIntValidator(1,1000000)
        self.lineEditAscansPerBscan.setValidator(v)
        v = QIntValidator(1,1000000)
        self.lineEditBscansPerVolume.setValidator(v)
        v = QIntValidator(0,1000000)
        self.lineEditBlocksToAcquire.setValidator(v)
        v = QIntValidator(1,1000000)
        self.lineEditAscansPerBlock.setValidator(v)
        v = QIntValidator(1,100000)
        self.lineEditSamplesPerAscan.setValidator(v)
        v = QIntValidator(1,1000)
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
        self.buttonGroupSource.setId(self.rbAxsun200k, 2)
        self.buttonGroupSource.setId(self.rbThorlabs400k, 3)
        self.buttonGroupSource.setId(self.rbCustom, 4)

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
                self.setClockSourceWidgetValues(source.Axsun200k)
            case 3:
                self.setClockSourceWidgetValues(source.ThorlabsVCSEL400k)
            case 4:
                # When changing to "Custom", do not change values in widgets. 
                pass

    def setClockSourceRadioButton(self, sscfg: Source):
        if sscfg == source.Axsun100k:
            self.rbAxsun100k.setChecked(True)
        elif sscfg == source.Axsun200k:
            self.rbAxsun200k.setChecked(True)
        elif sscfg == source.ThorlabsVCSEL400k:
            self.rbThorlabs400k.setChecked(True)
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
        elif self.rbAxsun200k.isChecked():
            return source.Axsun200k
        elif self.rbThorlabs400k.isChecked():
            return source.ThorlabsVCSEL400k
        else:
            return Source(int(self.lineEditTriggersPerSecond.text()), int(self.lineEditClockRisingEdgesPerTrigger.text()), float(self.lineEditDutyCycle.text()), float(self.lineEditImagingDepth.text()))
        
    def initializeDialog(self, cfg):
        self._cfg = cfg
        self.lineEditScanDimension.setText(str(cfg.scan_dimension))
        self.checkBoxBidirectional.setChecked(cfg.bidirectional)
        self.lineEditAscansPerBscan.setText(str(cfg.ascans_per_bscan))
        self.lineEditBscansPerVolume.setText(str(cfg.bscans_per_volume))
        self.lineEditGalvoDelay.setText(str(cfg.galvo_delay))

        self.lineEditBlocksToAcquire.setText(str(cfg.blocks_to_acquire))
        self.lineEditAscansPerBlock.setText(str(cfg.ascans_per_block))
        self.lineEditSamplesPerAscan.setText(str(cfg.samples_per_ascan))
        self.lineEditTriggerDelay.setText(str(cfg.trigger_delay_seconds))

        # Handle swept_source separately because of source types
        self.setClockSourceRadioButton(cfg.swept_source)
        self.setClockSourceWidgetValues(cfg.swept_source)

        self.checkBoxInternalClock.setChecked(cfg.internal_clock)
        self.lineEditInternalClockRate.setText(str(cfg.clock_samples_per_second))
        self.lineEditExternalClockLevelPct.setText(str(cfg.external_clock_level_pct))
        # input channel and clock channel ignored for now - we cannot load vortex.acquire.alazar....
        self.checkBoxDoIO.setChecked(cfg.doIO)
        self.checkBoxDoStrobe.setChecked(cfg.doStrobe)
        self.lineEditTriggerRange.setText(str(cfg.trigger_range_millivolts))
        self.lineEditTriggerLevelFraction.setText(str(cfg.trigger_level_fraction))

        self.lineEditBlocksToAllocate.setText(str(cfg.blocks_to_allocate))
        self.lineEditPreloadCount.setText(str(cfg.preload_count))
        self.lineEditProcessSlots.setText(str(cfg.process_slots))
        self.lineEditDispersion0.setText(str(cfg.dispersion[0]))
        self.lineEditDispersion1.setText(str(cfg.dispersion[1]))
        self.lineEditLogLevel.setText(str(cfg.log_level))

    def getEngineParameters(self) -> VtxEngineParams:
        s = DEFAULT_VTX_ENGINE_PARAMS   # TODO: would be nice to have an empty obj
        s.scan_dimension = float(self.lineEditScanDimension.text())
        s.bidirectional = self.checkBoxBidirectional.isChecked()
        s.ascans_per_bscan = int(self.lineEditAscansPerBscan.text())
        s.bscans_per_volume = int(self.lineEditBscansPerVolume.text())
        s.galvo_delay = float(self.lineEditGalvoDelay.text())
        s.clock_samples_per_second = int(self.lineEditBlocksToAcquire.text())
        s.blocks_to_acquire = int(self.lineEditBlocksToAcquire.text())
        s.ascans_per_block = int(self.lineEditAscansPerBlock.text())
        s.samples_per_ascan = int(self.lineEditSamplesPerAscan.text())
        s.trigger_delay_seconds = float(self.lineEditTriggerDelay.text())
        s.swept_source = self.getClockSourceValues()
        s.internal_clock = bool(self.checkBoxInternalClock.isChecked())
        s.external_clock_level_pct = int(self.lineEditExternalClockLevelPct.text())
        #s.clock_channel = 
        #s.input_channel = 
        s.doIO = bool(self.checkBoxDoIO.isChecked())
        s.doStrobe = bool(self.checkBoxDoStrobe.isChecked())
        s.trigger_range_millivolts = int(self.lineEditTriggerRange.text())
        s.trigger_level_fraction = float(self.lineEditTriggerLevelFraction.text())
        s.blocks_to_allocate = int(self.lineEditBlocksToAllocate.text())
        s.preload_count = int(self.lineEditPreloadCount.text())
        s.process_slots = int(self.lineEditProcessSlots.text())
        s.dispersion = (float(self.lineEditDispersion0.text()), float(self.lineEditDispersion1.text()))
        s.log_level = int(self.lineEditLogLevel.text())
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

