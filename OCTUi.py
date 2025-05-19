from PyQt5.QtWidgets import QDialog
from PyQt5 import uic
from PyQt5.QtCore import QState, QFinalState, QStateMachine, QEvent, QEventTransition, QSignalTransition, pyqtSignal
from myengine import DEFAULT_ENGINE_PARAMS, StandardEngineParams
from StandardEngineParamsDialog import StandardEngineParamsDialog

class OCTUi(QDialog):
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
        self._cfg = DEFAULT_ENGINE_PARAMS
        self._cfgDialog = None

        uic.loadUi('OCTDialog.ui', self) # Load the .ui file
        self._machine = self.setupStateMachine()
        self._machine.start()
        self.show()

    def acceptedStandardEngineParams(self):
        self._cfg = self._cfgDialog.getEngineParameters()
        # initiate a transition to Ready
        self._readySignal.emit()

    def enteredStateReady(self):
        print("Entered state ready")

    def enteredStateConfig(self):
        print("entered state config")
        self._cfgDialog = StandardEngineParamsDialog(self._cfg)
        self._cfgDialog.accepted.connect(self.acceptedStandardEngineParams)
        self._cfgDialog.rejected.connect(self.rejectedStandardEngineParams)
        self._cfgDialog.show()

    def setupStateMachine(self) -> QStateMachine: 
        machine = QStateMachine(self)
        self._stateConfig = QState()
        self._stateDone = QFinalState()
        self._stateReady = QState()
        stateDone = QFinalState()
        machine.addState(self._stateConfig)
        machine.addState(self._stateReady)
        machine.setInitialState(self._stateConfig)
        self._stateConfig.entered.connect(self.enteredStateConfig)
        self._stateReady.entered.connect(self.enteredStateReady)

        self._readySignal = pyqtSignal(name="ready")
        self._cancelSignal = pyqtSignal(name="cancel")
        self._stateConfig.addTransition(self._readySignal, self._stateReady)
        self._stateConfig.addTransition()


        return machine

    class _ReadyEvent(QEvent):
        EventType = QEvent.User + 1  # Custom event type
        def __init__(self, data=None):
            super().__init__(_ReadyEvent.EventType)
            self.data = data

    class _CancelEvent(QEvent):
        EventType = QEvent.User + 2  # Custom event type
        def __init__(self, data=None):
            super().__init__(_CancelEvent.EventType)
            self.data = data
