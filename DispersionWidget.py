import sys
from typing import Tuple
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5 import QtCore
from Ui_DispersionWidget import Ui_DispersionWidget

class DispersionWidget(QWidget, Ui_DispersionWidget):

    valueChanged = QtCore.pyqtSignal(object)
    c2multiplier = 1e-6
    c3multiplier = 1e-9

    def __init__(self, parent: QWidget=None, dsp: Tuple[float, float] = (0,0)):
        super().__init__(parent)
        self.setupUi(self)


        # initialize values
        self.dsbDispersion0.setMinimum(-1000)
        self.dsbDispersion0.setMaximum(1000)
        self.dsbDispersion1.setMinimum(-1000)
        self.dsbDispersion1.setMaximum(1000)
        self.dsbDispersion0.setValue(dsp[0]/self.c2multiplier)
        self.dsbDispersion1.setValue(dsp[1]/self.c3multiplier)
        self.dsbDispersion0.valueChanged.connect(self.dispersionChanged)
        self.dsbDispersion1.valueChanged.connect(self.dispersionChanged)

    def dispersionChanged(self, value):
        self.valueChanged.emit(self.getDispersion())

    def getDispersion(self) -> Tuple[float, float]:
        return (float(self.dsbDispersion0.value) * self.c2multiplier, float(self.dsbDispersion1.value) * self.c3multiplier)
    
    def setDispersion(self, d: Tuple[float, float]):
        self.dsbDispersion0.setValue(d[0]/self.c2multiplier)
        self.dsbDispersion1.setValue(d[1]/self.c3multiplier)
    
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = DispersionWidget(None, (1.0e-5, 0.0))
    w.show()
    sys.exit(app.exec_())
