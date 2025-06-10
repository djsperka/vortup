import sys
from vortex.scan import RasterScanConfig
from PyQt5.QtWidgets import QGroupBox, QApplication, QRadioButton
from PyQt5.QtGui import QDoubleValidator, QIntValidator, QRegExpValidator
from PyQt5.QtCore import QRegExp
from Ui_ScanConfigWidget import Ui_ScanConfigWidget

class ScanConfigWidget(QGroupBox, Ui_ScanConfigWidget):
    def __init__(self, cfg: RasterScanConfig=RasterScanConfig()):
        """Instantiate class

        Args:
            cfg (RasterScanConfig, optional): _description_. Defaults to RasterScanConfig().
        """
        super().__init__()
        self.setupUi(self)

        # callback for radio buttons
        self.cbScanTypes.currentIndexChanged.connect(self.stackScanTypes.setCurrentIndex)

        # validators
        self.leAperB.setValidator(QIntValidator(1,5000))
        self.leBperV.setValidator(QIntValidator(1,5000))
        self.leXextent.setValidator(QRegExpValidator(QRegExp("(-?\d+[\s,]+-?\d+)|(-?\d+)")))
        self.leYextent.setValidator(QRegExpValidator(QRegExp("(-?\d+[\s,]+-?\d+)|(-?\d+)")))


#    def getScanConfig(self) -> RasterScanConfig:


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = ScanConfigWidget()
    ui = Ui_ScanConfigWidget()
    w.show()
    sys.exit(app.exec_())
