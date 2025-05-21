from PyQt5.QtWidgets import QDialog
from PyQt5 import uic
from myengine import DEFAULT_ENGINE_PARAMS, StandardEngineParams
from StandardEngineParamsDialog import StandardEngineParamsDialog
from Ui_OCTDialog import Ui_OCTDialog

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
        # uic.loadUi('OCTDialog.ui', self) # Load the .ui file

