import sys
from PyQt5.QtWidgets import QGroupBox, QWidget
from PyQt5.QtGui import QDoubleValidator, QIntValidator, QRegExpValidator
from AcqParams import AcqParams, DEFAULT_ACQ_PARAMS
from Ui_AcqParamsWidget import Ui_AcqParamsWidget

class AcqParamsWidget(QGroupBox, Ui_AcqParamsWidget):
    def __init__(self, parent: QWidget=None, cfg: AcqParams=DEFAULT_ACQ_PARAMS):
        super().__init__(parent)
        self.setupUi(self)

        # validators
        self.leAperBlock.setValidator(QIntValidator(1,5000))
        self.leSperA.setValidator(QIntValidator(1,5000))
        self.leNBlocks.setValidator(QIntValidator(0, 10000))
        v = QDoubleValidator(0.0, 1.0, 3)
        v.setNotation(QDoubleValidator.Notation.ScientificNotation)
        self.leTriggerDelay.setValidator(v)

        # initialize values
        self.leAperBlock.setText(str(cfg.ascans_per_block))
        self.leSperA.setText(str(cfg.samples_per_ascan))
        self.leNBlocks.setText(str(cfg.blocks_to_acquire))
        self.leTriggerDelay.setText(str(cfg.trigger_delay_seconds))

    def getAcqParams(self) -> AcqParams: 
        cfg = AcqParams()
        cfg.ascans_per_block = int(self.leAperBlock.text())
        cfg.samples_per_ascan = int(self.leSperA.text())
        cfg.blocks_to_acquire = int(self.leNBlocks.text())
        cfg.trigger_delay_seconds = float(self.leTriggerDelay.text())
        return cfg
    
    def setAcqParams(self, cfg: AcqParams):
        self.leAperBlock.setText(str(cfg.ascans_per_block))
        self.leSperA.setText(str(cfg.samples_per_ascan))
        self.leNBlocks.setText(str(cfg.blocks_to_acquire))
        self.leTriggerDelay.setText(str(cfg.trigger_delay_seconds))
