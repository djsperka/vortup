from vortex import get_console_logger as get_logger
from vortex.engine import Engine, Block, source, acquire_alazar_clock, find_rising_edges, compute_resampling, dispersion_phasor

from vortex.acquire import AlazarConfig, AlazarAcquisition, alazar
from vortex.process import CUDAProcessor, CUDAProcessorConfig
from vortex.io import DAQmxIO, DAQmxConfig, daqmx
from vortex.engine import source, Source, Engine
from VtxEngineParams import VtxEngineParams
from numpy import hanning

class VtxEngine(Engine):
    def __init__(self, cfg: VtxEngineParams):
        super().__init__(get_logger('engine', cfg.log_level))

        #
        # acquisition
        #

        # configure external clocking from an Alazar card
        # internal clock works for testing with 9350 (doesn't take 800*10**6)
        ac = AlazarConfig()

        if cfg.internal_clock:
            ac.clock = alazar.InternalClock(cfg.clock_samples_per_second)
        else:
            ac.clock = alazar.ExternalClock(level_ratio=cfg.external_clock_level_pct, coupling=alazar.Coupling.AC, edge=alazar.ClockEdge.Rising, dual=False)

        resampling = []
        board = alazar.Board(ac.device.system_index, ac.device.board_index)
        ac.samples_per_record = board.info.smallest_aligned_samples_per_record(cfg.swept_source.clock_rising_edges_per_trigger)

        # trigger with range - must be 5000 (2500 will err). TTL will work in config also. Discrepancy with docs
        ac.trigger = alazar.SingleExternalTrigger(range_millivolts=cfg.trigger_range_millivolts, level_ratio=cfg.trigger_level_fraction, delay_samples=0, slope=alazar.TriggerSlope.Negative)

        # only input channel A
        input = alazar.Input(alazar.Channel.A, cfg.input_channel_range_millivolts)
        ac.inputs.append(input)

        # pull in engine params
        ac.records_per_block = cfg.ascans_per_block
        ac.samples_per_record = cfg.samples_per_ascan

        acquire = AlazarAcquisition(get_logger('acquire', cfg.log_level))
        acquire.initialize(ac)
        self._acquire = acquire


        #
        # OCT processing setup
        #

        pc = CUDAProcessorConfig()

        # match acquisition settings
        pc.samples_per_record = cfg.samples_per_record
        pc.ascans_per_block = cfg.ascans_per_block

        pc.slots = cfg.process_slots

        # reasmpling
        pc.resampling_samples = resampling

        # spectral filter with dispersion correction
        window = hanning(pc.samples_per_ascan)
        phasor = dispersion_phasor(len(window), cfg.dispersion)
        pc.spectral_filter = window * phasor

        # DC subtraction per block
        pc.average_window = 2 * pc.ascans_per_block

        process = CUDAProcessor(get_logger('process', cfg.log_level))
        process.initialize(pc)
        self._process = process

        #
        # galvo control
        #

        if cfg.doIO:
            # output
            ioc_out = DAQmxConfig()
            ioc_out.samples_per_block = ac.records_per_block
            ioc_out.samples_per_second = cfg.swept_source.triggers_per_second
            ioc_out.blocks_to_buffer = cfg.preload_count
            
            # djs - use PFI12 instead of PFI0
            ioc_out.clock.source = "pfi12"

            sc = ioc_out.copy()

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


