import sys
import os
from math import pi

from PyQt5.QtCore import Qt, QEventLoop, QTimer
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5 import uic

from vortex import Range, get_console_logger as get_logger
from vortex.marker import Flags
from vortex.scan import RasterScanConfig, RasterScan, RadialScanConfig, RadialScan, SpiralScanConfig, SpiralScan
from vortex.engine import EngineConfig, Engine, source, StackDeviceTensorEndpointInt8 as StackDeviceTensorEndpoint, RadialDeviceTensorEndpointInt8 as RadialDeviceTensorEndpoint, AscanSpiralDeviceTensorEndpointInt8 as AscanSpiralDeviceTensorEndpoint
from vortex.acquire import alazar
from vortex.format import FormatPlanner, FormatPlannerConfig, StackFormatExecutorConfig, StackFormatExecutor, RadialFormatExecutorConfig, RadialFormatExecutor, SpiralFormatExecutorConfig, SpiralFormatExecutor, SimpleSlice

from vortex_tools.ui.display import RasterEnFaceWidget, RadialEnFaceWidget, SpiralEnFaceWidget, CrossSectionImageWidget

from myengine import setup_logging, StandardEngineParams, BaseEngine, DEFAULT_ENGINE_PARAMS


class OCTEngine(BaseEngine):
    def __init__(self, cfg: StandardEngineParams):
        super().__init__(cfg)

        #
        # scan
        #

        raster_sc = RasterScanConfig()
        raster_sc.bscans_per_volume = cfg.bscans_per_volume
        raster_sc.ascans_per_bscan = cfg.ascans_per_bscan
        raster_sc.bscan_extent = Range(-cfg.scan_dimension, cfg.scan_dimension)
        raster_sc.volume_extent = Range(-cfg.scan_dimension, cfg.scan_dimension)
        raster_sc.bidirectional_segments = cfg.bidirectional
        raster_sc.bidirectional_volumes = cfg.bidirectional
        raster_sc.samples_per_second = cfg.swept_source.triggers_per_second
        raster_sc.loop = True
        raster_sc.flags = Flags(0x1)

        raster_scan = RasterScan()
        raster_scan.initialize(raster_sc)
        self._raster_scan = raster_scan

        #
        # output setup
        #

        # format planners
        fc = FormatPlannerConfig()
        fc.segments_per_volume = cfg.bscans_per_volume
        fc.records_per_segment = cfg.ascans_per_bscan
        fc.adapt_shape = False

        fc.mask = raster_sc.flags
        stack_format = FormatPlanner(get_logger('raster format', cfg.log_level))
        stack_format.initialize(fc)
        self._stack_format = stack_format

        # format executors
        cfec = StackFormatExecutorConfig()
        # only keep half of the spectrum
        cfec.sample_slice = SimpleSlice(self._process.config.samples_per_ascan // 2)
        samples_to_save = cfec.sample_slice.count()


        cfe = StackFormatExecutor()
        cfe.initialize(cfec)
        stack_tensor_endpoint = StackDeviceTensorEndpoint(cfe, (raster_sc.bscans_per_volume, raster_sc.ascans_per_bscan, samples_to_save), get_logger('stack', cfg.log_level))
        self._stack_tensor_endpoint = stack_tensor_endpoint


        #
        # engine setup
        #

        ec = EngineConfig()
        ec.add_acquisition(self._acquire, [self._process])
        ec.add_processor(self._process, [stack_format])
        ec.add_formatter(stack_format, [stack_tensor_endpoint])
        if cfg.doIO:
            ec.add_io(self._io_out, lead_samples=round(cfg.galvo_delay * self._io_out.config.samples_per_second))
            ec.galvo_output_channels = len(self._io_out.config.channels)
        if cfg.doStrobe:
            ec.add_io(self._strobe)

        ec.preload_count = cfg.preload_count
        ec.records_per_block = cfg.ascans_per_block
        ec.blocks_to_allocate = cfg.blocks_to_allocate
        ec.blocks_to_acquire = cfg.blocks_to_acquire

    
        engine = Engine(get_logger('engine', cfg.log_level))
        self._engine = engine

        engine.initialize(ec)
        engine.prepare()

    def _handle_keypress(self, e):
        if e.key() == Qt.Key.Key_Q:
            self._engine.stop()

    def stop(self):
        self._engine.stop()

    def run(self):
        cpcfg = self._process.config
        print("CUDA config:\naverage_window: {0}\nresampling_samples: {1}\nenable_ifft: {2}\n".format(cpcfg.average_window, cpcfg.resampling_samples, cpcfg.enable_ifft))

        # add scan pattern
        self._engine.scan_queue.append(self._raster_scan)
        self._engine.start()

        # app = QApplication(sys.argv)

        # import traceback
        # def handler(cls, ex, trace):
        #     traceback.print_exception(cls, ex, trace)
        #     app.closeAllWindows()
        # sys.excepthook = handler

        # self._engine.scan_queue.append(self._raster_scan)

        # self._stack_widget = RasterEnFaceWidget(self._stack_tensor_endpoint)
        # self._cross_widget = CrossSectionImageWidget(self._stack_tensor_endpoint)

        # self._stack_tensor_endpoint.aggregate_segment_callback = self._stack_widget.notify_segments

        # def cb(v):
        #     self._stack_widget.notify_segments(v)
        #     self._cross_widget.notify_segments(v)
        # self._stack_tensor_endpoint.aggregate_segment_callback = cb

        # self._stack_widget.keyPressEvent = self._handle_keypress
        # self._cross_widget.keyPressEvent = self._handle_keypress

        # self._stack_widget.show()
        # self._cross_widget.show()

        # self._stack_widget.setWindowTitle('Raster Scan (Press 1)')
        # self._radial_widget.setWindowTitle('Radial Scan (Press 2)')
        # self._spiral_widget.setWindowTitle('Spiral Scan (Press 3)')

        # self._engine.start()

        # try:
        #     while (self._stack_widget.isVisible() or self._radial_widget.isVisible() or self._spiral_widget.isVisible()) and self._cross_widget.isVisible():
        #         if self._engine.wait_for(0.01):
        #             break

        #         self._stack_widget.update()
        #         self._radial_widget.update()
        #         self._spiral_widget.update()
        #         self._cross_widget.update()

        #         app.processEvents(QEventLoop.AllEvents, 10)

        # except KeyboardInterrupt:
        #     pass
        # finally:
        #     self._engine.stop()

if __name__ == '__main__':
    setup_logging()

    # engine
    myEngineParams = DEFAULT_ENGINE_PARAMS
    engine = OCTEngine(myEngineParams)

    # gui and exception handler
    app = QApplication(sys.argv)

    import traceback
    def handler(cls, ex, trace):
        traceback.print_exception(cls, ex, trace)
        app.closeAllWindows()
    sys.excepthook = handler



    class Ui(QDialog):
        def __init__(self):
            super(Ui, self).__init__() # Call the inherited classes __init__ method
            uic.loadUi('OCTDialog.ui', self) # Load the .ui file

    # Now create dialog and configure it with engine
    ui = Ui()
    

    # set up plots
    stack_widget = RasterEnFaceWidget(engine._stack_tensor_endpoint)
    ui.tabWidgetPlots.addTab(stack_widget, "Raster")
    cross_widget = CrossSectionImageWidget(engine._stack_tensor_endpoint)
    ui.tabWidgetPlots.addTab(cross_widget, "cross")

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
        ui.labelStatus.setText(str)

    timer = QTimer(ui)
    timer.timeout.connect(statusTimerCallback)
    ui.pbStart.clicked.connect(startClicked)
    ui.pbStop.clicked.connect(stopClicked)

    ui.show()
    timer.start(1000)
    sys.exit(app.exec_())
