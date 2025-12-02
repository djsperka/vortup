from abc import ABC, abstractmethod
from VtxEngine import VtxEngine
from PyQt5.QtWidgets import QWidget

class ScanDisplayWidget(QWidget, ABC): 

    def __init__(self, parent: QWidget=None):
        super(QWidget).__init__(parent)

    def 
