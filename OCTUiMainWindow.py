import sys
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QApplication, QStyle
from Ui_OCTUiMainWindow import Ui_OCTUiMainWindow

class OCTUiMainWindow(QMainWindow, Ui_OCTUiMainWindow):
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

    # signal emitted with dialog is closing
    dialogClosing = pyqtSignal()

    def __init__(self):
        super().__init__() # Call the inherited class' __init__ method
        self.setupUi(self)  # Use Ui_OCTDialog.py- WARNING! pyuic5 -o Ui_OCTDialog.py OCTDialog.ui

        # icons. Cannot seem to do this easily from QtDesigner!
        self.pbStart.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.pbStop.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))


    def closeEvent(self, event):
        self.dialogClosing.emit()
        event.accept()

if __name__ == '__main__':

    app = QApplication(sys.argv)
    dlg = OCTUiMainWindow()
    dlg.show()
    app.exec_()
