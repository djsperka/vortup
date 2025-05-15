import sys
from typing import Tuple
from PyQt5.QtWidgets import QDialog, QApplication
from PyQt5 import uic
from myengine import StandardEngineParams, DEFAULT_ENGINE_PARAMS
from vortex.engine import source, Source

class StandardEngineParamsDialog(QDialog):
    def __init__(self, cfg: StandardEngineParams):
        super().__init__()
        self.setWindowTitle("OCT Engine Parameters")
        uic.loadUi("StandardEngineParams.ui", self)
        self.initializeDialog(cfg)        # takes whatever is in cfg and inits dlg

    def setClockSourceValues(self, sscfg: Source):
        # For the sources, must check values since we do not save the source type, just the parameters.
        if sscfg == source.Axsun100k:
            self.rbAxsun100k.setDown(True)
        elif sscfg == source.Axsun200k:
            self.rbAxsun200k.setDown(True)
        elif sscfg == source.ThorlabsVCSEL400k:
            self.rbThorlabs400k.setDown(True)
        else:
            self.rbCustom.setDown(True)

        self.spinBoxTriggersPerSecond.setValue(sscfg.triggers_per_second)
        self.spinBoxClockRisingEdgesPerTrigger.setValue(sscfg.clock_rising_edges_per_trigger)
        self.doubleSpinBoxDutyCycle.setValue(sscfg.duty_cycle)
        self.doubleSpinBoxImagingDepth.setValue(sscfg.imaging_depth_meters)

    def getClockSourceValues(self) -> Source:
        if self.rbAxsun100k.isDown():
            return source.Axsun100k
        elif self.rbAxsun200k.isDown():
            return source.Axsun200k
        elif self.rbThorlabs400k.isDown():
            return source.ThorlabsVCSEL400k
        else:
            return Source(self.spinBoxTriggersPerSecond.value(), self.spinBoxClockRisingEdgesPerTrigger.value(), self.doubleSpinBoxDutyCycle.value(), self.doubleSpinBoxImagingDepth.value())
        
    def initializeDialog(self, cfg):
        self._cfg = cfg
        self.doubleSpinBoxScanDimension.setValue(cfg.scan_dimension)
        self.checkBoxBidirectional.setChecked(cfg.bidirectional)
        self.spinBoxAscansPerBscan.setValue(cfg.ascans_per_bscan)
        self.spinBoxBscansPerVolume.setValue(cfg.bscans_per_volume)
        self.doubleSpinBoxGalvoDelay.setValue(cfg.galvo_delay)

        self.spinBoxBlocksToAcquire.setValue(cfg.blocks_to_acquire)
        self.spinBoxAscansPerBlock.setValue(cfg.ascans_per_block)
        self.spinBoxSamplesPerAscan.setValue(cfg.samples_per_ascan)
        self.doubleSpinBoxTriggerDelay.setValue(cfg.trigger_delay_seconds)

        # Handle swept_source separately because of source types
        self.setClockSourceValues(cfg.swept_source)

        self.checkBoxInternalClock.setChecked(cfg.internal_clock)
        self.spinBoxInternalClockRate.setValue(cfg.clock_samples_per_second)
        self.doubleSpinBoxExternalClockLevelPct.setValue(cfg.external_clock_level_pct)
        # input channel and clock channel ignored for now - we cannot load vortex.acquire.alazar....
        self.checkBoxDoIO.setChecked(cfg.doIO)
        self.checkBoxDoStrobe.setChecked(cfg.doStrobe)
        self.spinBoxTriggerRange.setValue(cfg.trigger_range_millivolts)
        self.doubleSpinBoxTriggerLevelFraction.setValue(cfg.trigger_level_fraction)

        self.spinBoxBlocksToAllocate.setValue(cfg.blocks_to_allocate)
        self.spinBoxPreloadCount.setValue(cfg.preload_count)
        self.spinBoxProcessSlots.setValue(cfg.process_slots)
        self.doubleSpinBoxDispersion0.setValue(cfg.dispersion[0])
        self.doubleSpinBoxDispersion1.setValue(cfg.dispersion[1])





if __name__ == '__main__':

    app = QApplication(sys.argv)
    dlg = StandardEngineParamsDialog(DEFAULT_ENGINE_PARAMS)
    dlg.show()
    app.exec_()


