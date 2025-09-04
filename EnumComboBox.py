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

    
