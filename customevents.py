from PyQt5.QtCore import QObject, QEvent, pyqtSignal, QTimer

class CustomEvent(QEvent):
    EventType = QEvent.User + 1  # Custom event type
# w   w w    .  bo    o k   2  s .   c  o  m
    def __init__(self, data):
        super().__init__(CustomEvent.EventType)
        self.data = data

class EventProducer(QObject):
    customEventTriggered = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def startProducingEvents(self):
        timer = QTimer(self)
        timer.timeout.connect(self.emitCustomEvent)
        timer.start(1000)

    def emitCustomEvent(self):
        print("emitCustomEvent")
        data = "Custom event data"
        event = CustomEvent(data)
        self.customEvent(event)

class EventConsumer(QObject):
    def __init__(self):
        super().__init__()

    def event(self, event):
        if event.type() == CustomEvent.EventType:
            print("Custom event received with data:", event.data)
            return True
        return super().event(event)

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    producer = EventProducer()
    consumer = EventConsumer()

    producer.customEventTriggered.connect(consumer.customEvent)

    producer.startProducingEvents()

    sys.exit(app.exec_())
