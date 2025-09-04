import sys
import math
from ScanParams import ScanParams
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
    def __init__(self, parent: QWidget=None):
        """Instantiate class

        Args:
        """
        super().__init__(parent)
        self.setupUi(self)

        # callback for radio buttons
        self.cbScanTypes.currentIndexChanged.connect(self.stackScanTypes.setCurrentIndex)

        # validators

        # This regular expression matches a comma-separated range with or without floating-point numbers.
        # It also matches a single number (float or not). 
        # The capture [1] is for the former, and capture[6] is for the single number.
        sFloat = "([+-]?([0-9]*[.])?[0-9]+)"
        self._regexForExtents = QRegExp("({0:s}[\s,]{1:s})|{2:s}".format(sFloat, sFloat, sFloat))
        #self._regexForExtents = QRegExp("((-?\d+)[\s,]+(-?\d+))|(-?\d+)")
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
            if self._regexForExtents.cap(6) == '':
                iLow = float(self._regexForExtents.cap(2))
                iHigh = float(self._regexForExtents.cap(4))
                r = Range(iLow, iHigh)
            else:
                iVal = float(self._regexForExtents.cap(6))
                r = Range(-iVal, iVal)
        else:
            raise RuntimeError("Cannot parse extents: {0:s}".format(txt))
        return r

    def getScanParams(self) -> ScanParams:
        params = ScanParams()
        params.current_index = self.cbScanTypes.currentIndex()
        if self.cbScanTypes.currentIndex() == 0:
            params.ascans_per_bscan = int(self.leAperB.text())
            params.bscans_per_volume = int(self.leBperV.text())
            params.bidirectional_segments = self.cbBidirectional.isChecked()
            params.segment_extent = self.getRangeFromTextEntry(self.leXextent.text())
            params.volume_extent = self.getRangeFromTextEntry(self.leYextent.text())
        elif self.cbScanTypes.currentIndex() == 1:
            # line scan
            degrees = float(self.leLAngle.text())
            params.angle = degrees * math.pi / 180.0
            params.ascans_per_bscan = int(self.leLAperB.text())
            params.bscans_per_volume = 1
            params.bidirectional_segments = self.cbLBidirectional.isChecked()
            params.segment_extent = self.getRangeFromTextEntry(self.leLextent.text())
            params.volume_extent = Range(0, 0)
        else:
            raise RuntimeError("Scan type not handled by getScanConfig()")
        return params

    def setScanParams(self, params: ScanParams):
        self.cbScanTypes.setCurrentIndex(params.current_index)
        if params.current_index == 0:
            self.leAperB.setText("{0:d}".format(params.ascans_per_bscan))
            self.leBperV.setText("{0:d}".format(params.bscans_per_volume))
            self.cbBidirectional.setChecked(params.bidirectional_segments)
            self.leXextent.setText("{0:.2f},{1:.2f}".format(params.segment_extent.min, params.segment_extent.max))
            self.leYextent.setText("{0:.2f},{1:.2f}".format(params.volume_extent.min, params.volume_extent.max))
        elif params.current_index == 1:
            # line scan
            degrees = params.angle * 180.0 / math.pi
            self.leLAngle.setText("{0:f}".format(degrees))
            self.leLAperB.setText("{0:d}".format(params.ascans_per_bscan))
            self.cbLBidirectional.setChecked(params.bidirectional_segments)
            self.leLextent.setText("{0:.2f},{1:.2f}".format(params.segment_extent.min, params.segment_extent.max))
        else:
            raise RuntimeError("Scan type not handled by getScanConfig()")
        return params


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = ScanConfigWidget()
    ui = Ui_ScanConfigWidget()
    w.show()
    sys.exit(app.exec_())
