from PyQt5.QtWidgets import QWidget, QComboBox
from enum import Enum

class EnumComboBox(QComboBox):
    def __init__(self, parent: QWidget=None):
        super().__init__(parent)
        self._E = None

    def initialize(self, e: Enum, v: int = 0):
        if not isinstance(e, type):
            raise RuntimeError("Expecting a type (e.g. an Enum class name).")
        self._E = e
        setToThisIndex=-1
        for t in list(self._E):
            if v == t.value:
                setToThisIndex = self.count()
            self.addItem(t.name, t.value)
        if setToThisIndex < 0:
            setToThisIndex = 0
        self.setCurrentIndex(setToThisIndex)

    
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    from DAQConst import ATS9350InputRange
    from vortex.acquire import alazar
    app = QApplication(sys.argv)
    w = EnumComboBox()
    w.initialize(ATS9350InputRange, 1)
    w.show()
    app.exec()
    print("w.currentIndex {0:d} text {1:d}".format(w.currentIndex(), w.itemData(w.currentIndex())))
    sys.exit()