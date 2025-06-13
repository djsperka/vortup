import sys
from vortex.scan import RasterScanConfig, RasterScan, Limits
from vortex import Range
from PyQt5.QtWidgets import QGroupBox, QApplication, QWidget
from PyQt5.QtGui import QDoubleValidator, QIntValidator, QRegExpValidator
from PyQt5.QtCore import QRegExp
from Ui_ScanConfigWidget import Ui_ScanConfigWidget
from vortex_tools.scan import plot_annotated_waveforms_time, plot_annotated_waveforms_space
from matplotlib import pyplot
import traceback

class ScanConfigWidget(QGroupBox, Ui_ScanConfigWidget):
    def __init__(self, parent: QWidget=None, cfg: RasterScanConfig=RasterScanConfig()):
        """Instantiate class

        Args:
            cfg (RasterScanConfig, optional): _description_. Defaults to RasterScanConfig().
        """
        super().__init__(parent)
        self.setupUi(self)

        # callback for radio buttons
        self.cbScanTypes.currentIndexChanged.connect(self.stackScanTypes.setCurrentIndex)

        # validators
        self._regexForExtents = QRegExp("((-?\d+)[\s,]+(-?\d+))|(-?\d+)")
        self.leAperB.setValidator(QIntValidator(1,5000))
        self.leBperV.setValidator(QIntValidator(1,5000))
        self.leXextent.setValidator(QRegExpValidator(self._regexForExtents))
        self.leYextent.setValidator(QRegExpValidator(self._regexForExtents))
        self.pushButtonShowPattern.clicked.connect(self.showPatternClicked)

    def showPatternClicked(self):
        try:
            cfg = self.getScanConfig()
            scan = RasterScan()
            scan.initialize(cfg)
            name = "scan pattern"
            fig, _ = plot_annotated_waveforms_time(cfg.sampling_interval, scan.scan_buffer(), scan.scan_markers())
            fig.suptitle(name)
            fig.show()
            fig, _ = plot_annotated_waveforms_space(scan.scan_buffer(), scan.scan_markers())
            fig.suptitle(name)
            fig.show()
            pyplot.show()
        except RuntimeError as e:
            print("RuntimeError:")
            traceback.print_exception(e)

    def getRangeFromTextEntry(self, txt) -> Range:
        # match regex. Validator should ensure that there is ALWAYS a match, but throw exception if not.
        if self._regexForExtents.exactMatch(txt):
            if self._regexForExtents.cap(4) == '':
                iLow = int(self._regexForExtents.cap(2))
                iHigh = int(self._regexForExtents.cap(3))
                r = Range(iLow, iHigh)
            else:
                iVal = int(self._regexForExtents.cap(4))
                r = Range(-iVal, iVal)
        else:
            raise RuntimeError("Cannot parse X extents: ", )
        return r

    def getScanConfig(self) -> RasterScanConfig:
        cfg = RasterScanConfig()

        # which type of scan is preferred?
        if self.cbScanTypes.currentIndex() == 0:
            # raster scan
            cfg.ascans_per_bscan = int(self.leAperB.text())
            cfg.bscans_per_volume = int(self.leBperV.text())
            cfg.bidirectional_segments = self.cbBidirectional.isChecked()
            cfg.segment_extent = self.getRangeFromTextEntry(self.leXextent.text())
            cfg.bscan_extent = self.getRangeFromTextEntry(self.leYextent.text())
        elif self.cbScanTypes.currentIndex() == 1:
            # line scan
            cfg.angle = float(self.leLAngle.text())
            cfg.ascans_per_bscan = int(self.leLAperB.text())
            cfg.bscans_per_volume = 1
            cfg.bidirectional_segments = self.cbLBidirectional.isChecked()
            cfg.segment_extent = self.getRangeFromTextEntry(self.leLextent.text())
            cfg.bscan_extent = Range(0, 0)
        else:
            raise RuntimeError("Scan type not handled by getScanConfig()")
        return cfg

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = ScanConfigWidget()
    ui = Ui_ScanConfigWidget()
    w.show()
    sys.exit(app.exec_())
