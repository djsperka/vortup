import sys
from typing import Tuple
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtGui import QDoubleValidator
from Ui_DispersionWidget import Ui_DispersionWidget

class DispersionWidget(QWidget, Ui_DispersionWidget):
    def __init__(self, parent: QWidget=None, dsp: Tuple[float, float] = (0,0)):
        super().__init__(parent)
        self.setupUi(self)


        # initialize values
        self.dsbDispersion0.setMinimum(-10e-5)
        self.dsbDispersion0.setMaximum(10e-5)
        self.dsbDispersion1.setMinimum(-10e-5)
        self.dsbDispersion1.setMaximum(10e-5)
        self.dsbDispersion0.setValue(dsp[0])
        self.dsbDispersion1.setValue(dsp[1])

    def getDispersion(self) -> Tuple[float, float]:
        return (self.dsbDispersion0.value(), self.dsbDispersion1.value())
    
    def setDispersion(self, d: Tuple[float, float]):
        self.dsbDispersion0.setValue(d[0])
        self.dsbDispersion1.setValue(d[1])
    
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = DispersionWidget(None, (1.0e-5, 0.0))
    w.show()
    sys.exit(app.exec_())
