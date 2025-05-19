import sys
from PyQt5 import QtWidgets
from PyQt5 import uic
from PyQt5.QtCore import QStateMachine, QState
from PyQt5.QtCore import QEventTransition, QPropertyAnimation
from PyQt5.QtCore import QSize, QEasingCurve, QEvent


class MyUI(QtWidgets.QMainWindow):
    
    def __init__(self, root):
        super(MyUI, self).__init__()
        uic.loadUi("statex.ui", self)
        
        # add and configure states and transitions
        self.handle_states()
        
        self.show()
    
    def handle_states(self):
        # create state machine
        machine = QStateMachine(self)
        
        # create states
        s1 = QState()
        s2 = QState()
        s3 = QState()
        
        # assign properties to states
        # State 1
        s1.assignProperty(self.lbl, "text", "1")
        s1.assignProperty(self.frame1, "styleSheet", "background-color: rgb(16, 128, 128);")
        s1.assignProperty(self.frame1, "maximumSize", QSize(500, 200))
        # State 2
        s2.assignProperty(self.lbl, "text", "2")
        s2.assignProperty(self.frame1, "styleSheet", "background-color: rgb(255, 255, 10);")
        s2.assignProperty(self.frame1, "maximumSize", QSize(600, 150))
        # State 3
        s3.assignProperty(self.lbl, "text", "3")
        s3.assignProperty(self.frame1, "styleSheet", "background-color: rgb(102, 102, 255);")
        s3.assignProperty(self.frame1, "maximumSize", QSize(300, 300))
        
        # create animation
        animation = QPropertyAnimation(self.frame1, b"maximumSize")
        animation.setEasingCurve(QEasingCurve.InOutCubic)
        animation.setDuration(500)
        
        # add event transitions
        t1 = QEventTransition(self.but, QEvent.MouseButtonPress)
        t1.setTargetState(s2)
        t1.addAnimation(animation)
        s1.addTransition(t1)
        
        t2 = QEventTransition(self.but, QEvent.MouseButtonPress)
        t2.setTargetState(s3)
        t2.addAnimation(animation)
        s2.addTransition(t2)
        
        t3 = QEventTransition(self.but, QEvent.MouseButtonPress)
        t3.setTargetState(s1)
        t3.addAnimation(animation)
        s3.addTransition(t3)
        
        machine.addState(s1)
        machine.addState(s2)
        machine.addState(s3)
        machine.setInitialState(s1)
        machine.start()


def main():
    app = QtWidgets.QApplication(sys.argv)
    window =  MyUI(app)
    sys.exit(app.exec())

if __name__ == '__main__':
    main()