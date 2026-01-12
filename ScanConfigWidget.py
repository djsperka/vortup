import sys
import math
from ScanParams import ScanParams, RasterScanParams, AimingScanParams, LineScanParams
from vortex.scan import RasterScanConfig, RasterScan, Limits
from vortex import Range
from PyQt5.QtWidgets import QGroupBox, QApplication, QWidget
from PyQt5.QtGui import QDoubleValidator, QIntValidator, QRegExpValidator
from PyQt5.QtCore import QRegExp, pyqtSignal
from Ui_ScanConfigWidget import Ui_ScanConfigWidget
from Ui_RasterScanConfigWidget import Ui_RasterScanConfigWidget
from Ui_AimingScanConfigWidget import Ui_AimingScanConfigWidget
from Ui_LineScanConfigWidget import Ui_LineScanConfigWidget
from vortex_tools.scan import plot_annotated_waveforms_time, plot_annotated_waveforms_space
from matplotlib import pyplot
import traceback


f_sFloat = "([+-]?([0-9]*[.])?[0-9]+)"
RegexForExtents = QRegExp("({0:s}[\s,]{1:s})|{2:s}".format(f_sFloat, f_sFloat, f_sFloat))

def getRangeFromTextEntry(txt) -> Range:
    # match regex. Validator should ensure that there is ALWAYS a match, but throw exception if not.
    if RegexForExtents.exactMatch(txt):
        if RegexForExtents.cap(6) == '':
            iLow = float(RegexForExtents.cap(2))
            iHigh = float(RegexForExtents.cap(4))
            r = Range(iLow, iHigh)
        else:
            iVal = float(RegexForExtents.cap(6))
            r = Range(-iVal, iVal)
    else:
        raise RuntimeError("Cannot parse extents: {0:s}".format(txt))
    return r




class ScanConfigWidget(QGroupBox, Ui_ScanConfigWidget):
    scanTypeChanged = pyqtSignal(object)

    def __init__(self, parent: QWidget=None):
        """Instantiate class

        Args:
        """
        super().__init__(parent)
        self.setupUi(self)

        # callback for radio buttons
        self.cbScanTypes.currentIndexChanged.connect(self.setCurrentIndex)

        # # validators

        # # This regular expression matches a comma-separated range with or without floating-point numbers.
        # # It also matches a single number (float or not). 
        # # The capture [1] is for the former, and capture[6] is for the single number.
        # sFloat = "([+-]?([0-9]*[.])?[0-9]+)"
        # self._regexForExtents = QRegExp("({0:s}[\s,]{1:s})|{2:s}".format(sFloat, sFloat, sFloat))
        # #self._regexForExtents = QRegExp("((-?\d+)[\s,]+(-?\d+))|(-?\d+)")
        # self.leAperB.setValidator(QIntValidator(1,5000))
        # self.leBperV.setValidator(QIntValidator(1,5000))
        # self.leXextent.setValidator(QRegExpValidator(self._regexForExtents))
        # self.leYextent.setValidator(QRegExpValidator(self._regexForExtents))
        # self.pushButtonShowPattern.clicked.connect(self.showPatternClicked)

    def getScanParams(self) -> ScanParams:
        params = ScanParams()
        params.current_index = self.cbScanTypes.currentIndex()
        for i in range(self.cbScanTypes.count()):
            params.scans[self.cbScanTypes.itemText(i)] = self.cbScanTypes.itemData(i).getParams()
        return params

    def addScanType(self, name, w):
        # add item to drop-down
        self.cbScanTypes.addItem(name, w)

        # add page to stacked widget
        self.stackScanTypes.addWidget(w)

    def setCurrentIndex(self, index):
        self.stackScanTypes.setCurrentIndex(index)
        self.scanTypeChanged.emit(index)

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


from abc import ABC, ABCMeta,  abstractmethod
QWidgetMeta = type(QWidget)
class _ABCQWidgetMeta(QWidgetMeta, ABCMeta): pass

class ScanTypeConfigWidget(ABC):

    @abstractmethod
    def setParams(self, params):
        """Initialize widget with the given parameters"""
        pass

    @abstractmethod
    def getParams(self):
        """Return the parameters currently specified in the widget"""
        pass

class RasterScanConfigWidget(QWidget, Ui_RasterScanConfigWidget, ScanTypeConfigWidget, metaclass=_ABCQWidgetMeta):
    def __init__(self, parent: QWidget=None):
        """Instantiate class

        Args:
        """
        super().__init__(parent)
        self.setupUi(self)

        # validators
        self.leAperB.setValidator(QIntValidator(1,5000))
        self.leBperV.setValidator(QIntValidator(1,5000))
        self.leXextent.setValidator(QRegExpValidator(RegexForExtents))
        self.leYextent.setValidator(QRegExpValidator(RegexForExtents))


    def getParams(self):
        return self.getRasterScanParams()
    
    def setParams(self, params):
        self.setRasterScanParams(params)

    def getRasterScanParams(self) -> RasterScanParams:
        params = RasterScanParams()
        params.ascans_per_bscan = int(self.leAperB.text())
        params.bscans_per_volume = int(self.leBperV.text())
        params.bidirectional_segments = self.cbBidirectional.isChecked()
        params.segment_extent = getRangeFromTextEntry(self.leXextent.text())
        params.volume_extent = getRangeFromTextEntry(self.leYextent.text())
        params.angle = self.dsbAngle.value()
        return params

    def setRasterScanParams(self, params: RasterScanParams):
        self.leAperB.setText("{0:d}".format(params.ascans_per_bscan))
        self.leBperV.setText("{0:d}".format(params.bscans_per_volume))
        self.cbBidirectional.setChecked(params.bidirectional_segments)
        self.leXextent.setText("{0:.2f},{1:.2f}".format(params.segment_extent.min, params.segment_extent.max))
        self.leYextent.setText("{0:.2f},{1:.2f}".format(params.volume_extent.min, params.volume_extent.max))
        self.dsbAngle.setValue(params.angle)



class AimingScanConfigWidget(QWidget, ScanTypeConfigWidget, Ui_AimingScanConfigWidget, metaclass=_ABCQWidgetMeta):
    def __init__(self, parent: QWidget=None):
        """Instantiate class

        Args:
        """
        super().__init__(parent)
        self.setupUi(self)

        # validators
        self.leAperB.setValidator(QIntValidator(1,5000))
        self.leBperV.setValidator(QIntValidator(1,5000))
        self.leAextent.setValidator(QRegExpValidator(RegexForExtents))

    def getParams(self):
        return self.getAimingScanParams()
    
    def setParams(self, params):
        self.setAimingScanParams(params)

    def getAimingScanParams(self) -> AimingScanParams:
        params = AimingScanParams()
        params.ascans_per_bscan = int(self.leAperB.text())
        params.bscans_per_volume = int(self.leBperV.text())
        params.bidirectional_segments = self.cbBidirectional.isChecked()
        params.aim_extent = getRangeFromTextEntry(self.leAextent.text())
        params.angle = self.dsbAngle.value()
        return params

    def setAimingScanParams(self, params: AimingScanParams):
        self.leAperB.setText("{0:d}".format(params.ascans_per_bscan))
        self.leBperV.setText("{0:d}".format(params.bscans_per_volume))
        self.cbBidirectional.setChecked(params.bidirectional_segments)
        self.leAextent.setText("{0:.2f},{1:.2f}".format(params.aim_extent.min, params.aim_extent.max))
        self.dsbAngle.setValue(params.angle)


class LineScanConfigWidget(QWidget, ScanTypeConfigWidget, Ui_LineScanConfigWidget, metaclass=_ABCQWidgetMeta):
    def __init__(self, parent: QWidget=None):
        """Instantiate class

        Args:
        """
        super().__init__(parent)
        self.setupUi(self)

        # validators
        self.leAperB.setValidator(QIntValidator(1,5000))
        self.leXextent.setValidator(QRegExpValidator(RegexForExtents))

    def getParams(self):
        return self.getLineScanParams()
    
    def setParams(self, params):
        self.setLineScanParams(params)

    def getLineScanParams(self) -> LineScanParams:
        params = LineScanParams()
        params.ascans_per_bscan = int(self.leAperB.text())
        params.lines_per_volume = int(self.leLperV.text())
        params.bidirectional_segments = self.cbBidirectional.isChecked()
        params.line_extent = getRangeFromTextEntry(self.leXextent.text())
        params.angle = self.dsbAngle.value()
        return params

    def setLineScanParams(self, params: LineScanParams):
        self.leAperB.setText("{0:d}".format(params.ascans_per_bscan))
        self.cbBidirectional.setChecked(params.bidirectional_segments)
        self.leXextent.setText("{0:.2f},{1:.2f}".format(params.line_extent.min, params.line_extent.max))
        self.leLperV.setText("{0:d}".format(params.lines_per_volume))
        self.dsbAngle.setValue(params.angle)



if __name__ == "__main__":
    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
    parser = ArgumentParser(description='save volume to disk', formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('--type', choices=['raster', 'aim', 'line'], default='raster', help='dlg type')
    args = parser.parse_args()
    app = QApplication([])
    match args.type:
        case 'raster':
            w = RasterScanConfigWidget()

            r = RasterScanParams()
            r.angle=99
            r.segment_extent = Range(-4,4)
            r.volume_extent = Range(-1,3)
            r.bidirectional_segments = False
            r.ascans_per_bscan = 400
            r.bscans_per_volume = 450
            w.setParams(r)

            w.show()
            app.exec()

            r2 = w.getParams()
            print(r)
            print(r2)
        case 'aim':
            w = AimingScanConfigWidget()

            r = AimingScanParams()
            r.angle=99
            r.aim_extent = Range(-2,5)
            r.bidirectional_segments = False
            r.ascans_per_bscan = 400
            w.setAimingScanParams(r)
            w.show()
            app.exec()

            r2 = w.getAimingScanParams()
            print(r)
            print(r2)

        case 'line':
            w = LineScanConfigWidget()

            r = LineScanParams()
            r.angle=99
            r.line_extent = Range(-1,4)
            r.bidirectional_segments = False
            r.ascans_per_bscan = 423
            w.setLineScanParams(r)
            w.show()
            app.exec()

            r2 = w.getLineScanParams()
            print(r)
            print(r2)


