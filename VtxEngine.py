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

class VtxEngine():
    def __init__(self, cfg: VtxEngineParams):

        #
        # acquisition
        #

        resampling = []     # may be reassigned in this block, used below this block
        if cfg.acquisition_type == AcquisitionType.ALAZAR_ACQUISITION:

            # configure external clocking from an Alazar card
            # internal clock works for testing with 9350 (doesn't take 800*10**6)
            ac = AlazarConfig()

            if cfg.internal_clock:
                ac.clock = alazar.InternalClock(cfg.clock_samples_per_second)
            else:
                ac.clock = alazar.ExternalClock(level_ratio=cfg.external_clock_level_pct, coupling=alazar.Coupling.AC, edge=alazar.ClockEdge.Rising, dual=False)

            board = alazar.Board(ac.device.system_index, ac.device.board_index)
            ac.samples_per_record = board.info.smallest_aligned_samples_per_record(cfg.swept_source.clock_rising_edges_per_trigger)

            # trigger with range - must be 5000 (2500 will err). TTL will work in config also. Discrepancy with docs
            ac.trigger = alazar.SingleExternalTrigger(range_millivolts=cfg.trigger_range_millivolts, level_ratio=cfg.trigger_level_fraction, delay_samples=0, slope=alazar.TriggerSlope.Positive)

            # only input channel A
            input = alazar.Input(alazar.Channel.A, cfg.input_channel_range_millivolts)
            ac.inputs.append(input)

            # pull in engine params
            ac.records_per_block = cfg.ascans_per_block
            ac.samples_per_record = cfg.samples_per_ascan

            acquire = AlazarAcquisition(get_logger('acquire', cfg.log_level))
            acquire.initialize(ac)
            self._acquire = acquire

        elif cfg.acquisition_type == AcquisitionType.FILE_ACQUISITION:

            # create a temporary file with a pure sinusoid for tutorial purposes only
            spectrum = 2**15 + 2**14 * np.sin(2*np.pi * (cfg.samples_per_ascan / 4) * np.linspace(0, 1, cfg.samples_per_ascan))
            spectra = np.repeat(spectrum[None, ...], cfg.ascans_per_block, axis=0)

            import os
            from tempfile import mkstemp
            (fd, test_file_path) = mkstemp()
            # NOTE: the Python bindings are restricted to the uint16 data type
            open(test_file_path, 'wb').write(spectra.astype(np.uint16).tobytes())
            os.close(fd)


            # produce blocks ready from a file
            ac = FileAcquisitionConfig()
            ac.path = test_file_path
            ac.records_per_block = cfg.ascans_per_block
            ac.samples_per_record = cfg.samples_per_ascan
            ac.loop = True # repeat the file indefinitely

            acquire = FileAcquisition(get_logger('acquire', cfg.log_level))
            acquire.initialize(ac)
            self._acquire = acquire


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
        # OCT processing setup
        #

        pc = CUDAProcessorConfig()

        # match acquisition settings
        pc.samples_per_record = cfg.samples_per_ascan
        pc.ascans_per_block = cfg.ascans_per_block

        pc.slots = cfg.process_slots

        # reasmpling
        pc.resampling_samples = resampling

        # spectral filter with dispersion correction
        window = np.hanning(pc.samples_per_ascan)
        phasor = dispersion_phasor(len(window), cfg.dispersion)
        pc.spectral_filter = window * phasor

        # DC subtraction per block
        pc.average_window = 2 * pc.ascans_per_block

        process = CUDAProcessor(get_logger('process', cfg.log_level))
        process.initialize(pc)
        self._process = process

        #
        # format planners
        #

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
        # galvo control
        #

        if cfg.doIO:
            # output
            ioc_out = DAQmxConfig()
            ioc_out.samples_per_block = ac.records_per_block
            ioc_out.samples_per_second = cfg.swept_source.triggers_per_second
            ioc_out.blocks_to_buffer = cfg.preload_count
            ioc_out.clock.source = "pfi12"
            ioc_out.name = 'output'

            stream = Block.StreamIndex.GalvoTarget
            ioc_out.channels.append(daqmx.AnalogVoltageOutput('Dev1/ao0', 15 / 10, stream, 0))
            ioc_out.channels.append(daqmx.AnalogVoltageOutput('Dev1/ao1', 15 / 10, stream, 1))

            io_out = DAQmxIO(get_logger(ioc_out.name, cfg.log_level))
            io_out.initialize(ioc_out)
            self._io_out = io_out


        if cfg.doStrobe:
            sc.name = 'strobe'
            sc.channels.append(daqmx.DigitalOutput('Dev1/port0', Block.StreamIndex.Strobes))
            strobe = DAQmxIO(get_logger(sc.name, cfg.log_level))
            strobe.initialize(sc)
            self._strobe = strobe


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
        ec.records_per_block = cfg.ascans_per_block
        ec.blocks_to_allocate = cfg.blocks_to_allocate
        ec.blocks_to_acquire = cfg.blocks_to_acquire
        print("blocks to acquire {0:d}".format(ec.blocks_to_acquire))


        engine = Engine(get_logger('engine', cfg.log_level))
        engine.initialize(ec)
        engine.prepare()
        self._engine = engine

