from myengine import setup_logging, StandardEngineParams, DEFAULT_ENGINE_PARAMS, BaseEngine
from vortex.scan import RasterScan, RasterScanConfig
from vortex import get_console_logger as gcl, Range
from vortex.process import NullProcessor, NullProcessorConfig
from vortex.format import FormatPlanner, FormatPlannerConfig, StackFormatExecutor, StackFormatExecutorConfig
from vortex.engine import SpectraStackHostTensorEndpointUInt16
from vortex.engine import Engine, EngineConfig, source
from vortex.acquire import alazar

import sys
from PyQt5.QtCore import Qt, QEventLoop
from PyQt5.QtWidgets import QApplication

from vortex_tools.ui.display import RasterEnFaceWidget #, RadialEnFaceWidget, SpiralEnFaceWidget, CrossSectionImageWidget


class OCTEngine(BaseEngine):
    def __init__(self, cfg: StandardEngineParams):
        super().__init__(cfg)

        # BaseEngine only creates AlazarAcquisitrion, processor, io_out(if requested), and strobe (same)
        # Must still add scan, format

        # create a repeated A-scan
        rsc = RasterScanConfig()
        rsc.bscans_per_volume = cfg.bscans_per_volume
        rsc.ascans_per_bscan = cfg.ascans_per_bscan
        rsc.bscan_extent = Range(0, 0)
        rsc.volume_extent = Range(0, 0)

        # complete only a single volume
        rsc.loop = True

        raster_scan = RasterScan()
        raster_scan.initialize(rsc)
        self._raster_scan = raster_scan

        # configure standard formatting
        fc = FormatPlannerConfig()
        fc.segments_per_volume = cfg.bscans_per_volume
        fc.records_per_segment = cfg.ascans_per_bscan
        fc.adapt_shape = False

        format = FormatPlanner(gcl('format', cfg.log_level))
        format.initialize(fc)

        # store raw spectra in a volume
        sfec = StackFormatExecutorConfig()
        sfe  = StackFormatExecutor()
        sfe.initialize(sfec)

        endpoint = SpectraStackHostTensorEndpointUInt16(sfe, [cfg.bscans_per_volume, cfg.ascans_per_bscan, cfg.samples_per_ascan], gcl('endpoint', cfg.log_level))
        self._stack_tensor_endpoint = endpoint

        #
        # engine setup
        #

        # configure the engine
        ec = EngineConfig()

        ec.add_acquisition(self._acquire, [self._process])
        ec.add_processor(self._process, [format])
        ec.add_formatter(format, [endpoint])

        # reasonable default parameters
        ec.preload_count = 32
        ec.records_per_block = cfg.ascans_per_block
        ec.blocks_to_allocate = ec.preload_count * 2
        ec.blocks_to_acquire = 1000 # 0 means inifinite acquisition

        engine = Engine(gcl('engine', cfg.log_level))
        engine.initialize(ec)
        engine.prepare()
        self._engine = engine

    def run(self):
        app = QApplication(sys.argv)

        import traceback
        def handler(cls, ex, trace):
            traceback.print_exception(cls, ex, trace)
            app.closeAllWindows()
        sys.excepthook = handler

        self._engine.scan_queue.append(self._raster_scan)

        self._stack_widget = RasterEnFaceWidget(self._stack_tensor_endpoint)
        # self._radial_widget = RadialEnFaceWidget(self._radial_tensor_endpoint)
        # self._spiral_widget = SpiralEnFaceWidget(self._spiral_tensor_endpoint)
        # self._cross_widget = CrossSectionImageWidget(self._stack_tensor_endpoint)

        self._stack_tensor_endpoint.aggregate_segment_callback = self._stack_widget.notify_segments
        # self._radial_tensor_endpoint.aggregate_segment_callback = self._radial_widget.notify_segments
        # self._spiral_tensor_endpoint.update_callback = lambda: self._spiral_widget.notify_segments([0])

        def cb(v):
            self._stack_widget.notify_segments(v)
            # self._cross_widget.notify_segments(v)
        self._stack_tensor_endpoint.aggregate_segment_callback = cb
        # def cb(v):
        #     self._radial_widget.notify_segments(v)
        # self._radial_tensor_endpoint.aggregate_segment_callback = cb
        # def cb(v):
        #     self._spiral_widget.notify_segments(v)
        # self._spiral_tensor_endpoint.aggregate_segment_callback = cb

        # self._stack_widget.keyPressEvent = self._handle_keypress
        # self._radial_widget.keyPressEvent = self._handle_keypress
        # self._spiral_widget.keyPressEvent = self._handle_keypress
        # self._cross_widget.keyPressEvent = self._handle_keypress

        self._stack_widget.show()
        # self._radial_widget.show()
        # self._spiral_widget.show()
        # self._cross_widget.show()

        self._stack_widget.setWindowTitle('Raster Scan')
        # self._radial_widget.setWindowTitle('Radial Scan (Press 2)')
        # self._spiral_widget.setWindowTitle('Spiral Scan (Press 3)')

        self._engine.start()

        try:
            while self._stack_widget.isVisible():
                if self._engine.wait_for(0.01):
                    break

                self._stack_widget.update()

                app.processEvents(QEventLoop.AllEvents, 10)

        except KeyboardInterrupt:
            pass
        finally:
            self._engine.stop()








if __name__ == '__main__':
    setup_logging()

    myEngineParams = StandardEngineParams(
        # scan parameters
        scan_dimension=5,
        bidirectional=False,
        ascans_per_bscan=500,
        bscans_per_volume=500,
        galvo_delay=95e-6,

        # acquisition parameters
        clock_samples_per_second=int(500e6),    # ATS 9350
        blocks_to_acquire=100,
        ascans_per_block=500,
        samples_per_ascan=1376,     # Axsun 100k
        trigger_delay_seconds=0,

        # These are probably rig-specific? Hasn't been an issue to use these. 
        blocks_to_allocate=128,
        preload_count=32,

        # hardware configuration
        swept_source=source.Axsun100k,
        internal_clock=False,
        clock_channel=alazar.Channel.B,     # only relevant if internal_clock = True
        input_channel=alazar.Channel.A,
        doIO=False,
        doStrobe=False,

        # engine memory parameters
        process_slots=2,                    # I think this is for in-stream processing?
        dispersion=(2.8e-5, 0),             # no idea

        # logging
        log_level=1,                        # 1 is normal, 0 is debug-level
    )


    engine = OCTEngine(myEngineParams)
    engine.run()

""" from vortex.acquire import AlazarAcquisition, AlazarConfig, alazar



# configure standard formatting
fc = FormatPlannerConfig()
fc.segments_per_volume = myEngineParameters.bscans_per_volume
fc.records_per_segment = myEngineParameters.ascans_per_bscan
fc.adapt_shape = False

format = FormatPlanner(gcl('format', myEngineParameters.log_level))
format.initialize(fc)

# store raw spectra in a volume
sfec = StackFormatExecutorConfig()
sfe  = StackFormatExecutor()
sfe.initialize(sfec)

endpoint = SpectraStackHostTensorEndpointUInt16(sfe, [myEngineParameters.bscans_per_volume, myEngineParameters.ascans_per_bscan, myEngineParameters.samples_per_ascan], gcl('endpoint', myEngineParameters.log_level))

# configure the engine
ec = EngineConfig()

ec.add_acquisition(acquire, [process])
ec.add_processor(process, [format])
ec.add_formatter(format, [endpoint])

# reasonable default parameters
ec.preload_count = 32
ec.records_per_block = myEngineParameters.ascans_per_block
ec.blocks_to_allocate = ec.preload_count * 2
ec.blocks_to_acquire = 1000 # 0 means inifinite acquisition

engine = Engine(gcl('engine', myEngineParameters.log_level))
engine.initialize(ec)
engine.prepare()

# load the scan
engine.scan_queue.append(scan)

# start the engine and wait for the scan to complete
# NOTE: since loop is false above, only one scan is executed
engine.start()
try:
    engine.wait()
finally:
    engine.stop()

# retrieve the collected data
# data is ordered by B-scan (segment), A-scan, and sample
with endpoint.tensor as volume:
    # combine all the B-scans (if there are multiple) and average all the spectra together
    average_spectrum = volume.reshape((-1,  myEngineParameters.samples_per_ascan)).mean(axis=0)

# show the average spectrum
from matplotlib import pyplot as plt
plt.plot(average_spectrum)

plt.xlabel('sample number')
plt.ylabel('intensity (unscaled)')
plt.title('Average Spectrum')
plt.show()
 """