import sys
import os
from math import pi

from PyQt5.QtCore import Qt, QEventLoop, QTimer, QState, QStateMachine
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5 import uic

from vortex import Range, get_console_logger as get_logger
from vortex.engine import EngineConfig, Engine, source, StackDeviceTensorEndpointInt8 as StackDeviceTensorEndpoint, RadialDeviceTensorEndpointInt8 as RadialDeviceTensorEndpoint, AscanSpiralDeviceTensorEndpointInt8 as AscanSpiralDeviceTensorEndpoint
from vortex.format import FormatPlanner, FormatPlannerConfig, StackFormatExecutorConfig, StackFormatExecutor, RadialFormatExecutorConfig, RadialFormatExecutor, SpiralFormatExecutorConfig, SpiralFormatExecutor, SimpleSlice

from vortex_tools.ui.display import RasterEnFaceWidget, RadialEnFaceWidget, SpiralEnFaceWidget, CrossSectionImageWidget

from myengine import setup_logging, StandardEngineParams, BaseEngine, DEFAULT_ENGINE_PARAMS
from OCTUi import OCTUi
from OCTEngine import OCTEngine

import StandardEngineParamsDialog



if __name__ == '__main__':
    setup_logging()

    # gui and exception handler
    app = QApplication(sys.argv)

    import traceback
    def handler(cls, ex, trace):
        traceback.print_exception(cls, ex, trace)
        app.closeAllWindows()
    sys.excepthook = handler


    # engine
    myEngineParams = DEFAULT_ENGINE_PARAMS
    engine = OCTEngine(myEngineParams)




    # class Ui(QDialog):
    #     def __init__(self):
    #         super(Ui, self).__init__() # Call the inherited classes __init__ method
    #         uic.loadUi('OCTDialog.ui', self) # Load the .ui file

    # # Now create dialog and configure it with engine
    # ui = Ui()

    octui = OCTUi()

    # set up plots
    stack_widget = RasterEnFaceWidget(engine._stack_tensor_endpoint)
    octui.tabWidgetPlots.addTab(stack_widget, "Raster")
    cross_widget = CrossSectionImageWidget(engine._stack_tensor_endpoint)
    octui.tabWidgetPlots.addTab(cross_widget, "cross")

    # argument (v) here is a number - index pointing to a segment in allocated segments.
    def cb(v):
        stack_widget.notify_segments(v)
        cross_widget.notify_segments(v)
    engine._stack_tensor_endpoint.aggregate_segment_callback = cb

    # set start button callback to start engine
    # set stop button callback to stop it
    def startClicked():
        engine.run()
    
    def stopClicked():
        engine.stop()

    def statusTimerCallback():
        s = engine._engine.status()
        if s.active:
            str = "Status: active, dispatched/in-flight {0:5d}/{1:5d}/{2:.2f}/{3:.2f}".format(s.dispatched_blocks, s.inflight_blocks, s.dispatch_completion, s.block_utilization)
        else:
            str = "Status: idle"
        octui.labelStatus.setText(str)

    timer = QTimer(octui)
    timer.timeout.connect(statusTimerCallback)
    octui.pbStart.clicked.connect(startClicked)
    octui.pbStop.clicked.connect(stopClicked)

    octui.show()
    timer.start(1000)
    sys.exit(app.exec_())
