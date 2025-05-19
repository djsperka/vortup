from PyQt5.QtCore import QState, QFinalState, QStateMachine
from PyQt5.QtWidgets import QApplication

from myengine import DEFAULT_ENGINE_PARAMS, StandardEngineParams
from StandardEngineParamsDialog import StandardEngineParamsDialog

import sys

def enteredConfig():
    print("entered config")
    dlg = StandardEngineParamsDialog(f_cfg)
    value = dlg.exec()
    if value==1:
        # user hit OK
    else:
        # user hit CANCEL
    print("entered config - done " + str(value))



f_cfg = DEFAULT_ENGINE_PARAMS

app = QApplication(sys.argv)

machine = QStateMachine()
stateConfig = QState(machine)
stateConfig.entered.connect(enteredConfig)
stateFinal = QFinalState(machine)
machine.setInitialState(stateConfig)

print("call machine.start()")
machine.start()
print("machine.start() returned")

app.exec_()

