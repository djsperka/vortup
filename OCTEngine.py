from myengine import StandardEngineParams

from vortex.scan import RasterScanConfig, RasterScan
from vortex.engine import EngineConfig, Engine, source, StackDeviceTensorEndpointInt8 as StackDeviceTensorEndpoint, RadialDeviceTensorEndpointInt8 as RadialDeviceTensorEndpoint, AscanSpiralDeviceTensorEndpointInt8 as AscanSpiralDeviceTensorEndpoint
from vortex.acquire import alazar
from vortex.format import FormatPlanner, FormatPlannerConfig, StackFormatExecutorConfig, StackFormatExecutor, RadialFormatExecutorConfig, RadialFormatExecutor, SpiralFormatExecutorConfig, SpiralFormatExecutor, SimpleSlice

from vortex_tools.ui.display import RasterEnFaceWidget, RadialEnFaceWidget, SpiralEnFaceWidget, CrossSectionImageWidget



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
