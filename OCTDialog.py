import sys
from PyQt5.QtWidgets import QDialog, QApplication, QStyle, QVBoxLayout
from PyQt5.QtWidgets import QDialog, QStyle
from PyQt5 import uic
from myengine import DEFAULT_ENGINE_PARAMS, StandardEngineParams
from StandardEngineParamsDialog import StandardEngineParamsDialog
from Ui_OCTDialog import Ui_OCTDialog
from ScanConfigWidget import ScanConfigWidget
from AcqParamsWidget import AcqParamsWidget
from CbFileSaveWidget import CbFileSaveWidget

class OCTDialog(QDialog, Ui_OCTDialog):
    """Wrapper class around designer-generated user interface. 
    
    The user interface file is created and updated using designer, which 
    is found somewhere in the qt5-tools package in your python installation
    (find site-packages inside your venv, as a starting point). The whole thing
    is done here (instead of inside the application file itself) to suppress a
    deprecation warning that comes up:

    sipPyTypeDict() is deprecated, the extension module should use sipPyTypeDictRef() instead

    I'm not sure what that means, but by moving the loading process (uic.loadUi) to a separate 
    file, it goes away. 

    Args:
        QDialog (_type_): Parent dialog that the UI is placed inside of
    """    
    
    def __init__(self):
        super().__init__() # Call the inherited class' __init__ method
        self.setupUi(self)  # Use Ui_OCTDialog.py- WARNING! pyuic5 -o Ui_OCTDialog.py OCTDialog.ui

        # replace placeholder with scan type widget
        self.scanConfigWidget = ScanConfigWidget(self)
        self.verticalLayoutSidebar.insertWidget(0, self.scanConfigWidget)
        self.acqParamsWidget = AcqParamsWidget(self)
        self.verticalLayoutSidebar.insertWidget(1, self.acqParamsWidget)
        self.verticalLayoutSidebar.insertStretch(2)

        # icons
        self.pbStart.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.pbStop.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))

        self.saveAscans = CbFileSaveWidget('ascans', self)
        self.saveSpectra = CbFileSaveWidget('spectra', self)
        layout = QVBoxLayout()
        layout.addWidget(self.saveAscans)
        layout.addWidget(self.saveSpectra)
        self.horizontalLayoutStartStop.addLayout(layout)


if __name__ == '__main__':

    app = QApplication(sys.argv)
    dlg = OCTDialog()
    dlg.show()
    app.exec_()
    print("exec() done")
