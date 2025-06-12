from VtxBaseEngine import VtxBaseEngine
from vortex import Range, get_console_logger as get_logger
from vortex.marker import Flags
from vortex.engine import Engine, EngineConfig, Block, dispersion_phasor, StackDeviceTensorEndpointInt8 as StackDeviceTensorEndpoint
from vortex.acquire import AlazarConfig, AlazarAcquisition, alazar, FileAcquisitionConfig, FileAcquisition
from vortex.process import CUDAProcessor, CUDAProcessorConfig
from vortex.io import DAQmxIO, DAQmxConfig, daqmx
from VtxEngineParams import VtxEngineParams, AcquisitionType
from vortex.scan import RasterScanConfig, RasterScan
from vortex.format import FormatPlanner, FormatPlannerConfig, StackFormatExecutorConfig, StackFormatExecutor, SimpleSlice
import numpy as np
from AcqParams import AcqParams, DEFAULT_ACQ_PARAMS
class VtxEngine(VtxBaseEngine):
    def __init__(self, cfg: VtxEngineParams, acq: AcqParams=DEFAULT_ACQ_PARAMS, scfg: RasterScanConfig=RasterScanConfig()):

        # base class 
        super().__init__(cfg)


        #
        # scan
        #

        raster_scan = RasterScan()
        raster_scan.initialize(scfg)
        self._raster_scan = raster_scan

        #
        # format planners
        #

        fc = FormatPlannerConfig()
        fc.segments_per_volume = scfg.bscans_per_volume
        fc.records_per_segment = scfg.ascans_per_bscan
        fc.adapt_shape = False

        fc.mask = scfg.flags
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
        stack_tensor_endpoint = StackDeviceTensorEndpoint(cfe, (scfg.bscans_per_volume, scfg.ascans_per_bscan, samples_to_save), get_logger('stack', cfg.log_level))
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
            print("there are {0:d} galvo channels".format(ec.galvo_output_channels))
        if cfg.doStrobe:
            ec.add_io(self._strobe)

        ec.preload_count = cfg.preload_count
        ec.records_per_block = acq.ascans_per_block
        ec.blocks_to_allocate = cfg.blocks_to_allocate
        ec.blocks_to_acquire = acq.blocks_to_acquire
        print("blocks to acquire {0:d}".format(ec.blocks_to_acquire))


        engine = Engine(get_logger('engine', cfg.log_level))
        engine.initialize(ec)
        engine.prepare()
        self._engine = engine

