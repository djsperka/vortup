from vortex import Range, get_console_logger as get_logger
from vortex.engine import Block, dispersion_phasor
from vortex.acquire import AlazarConfig, AlazarAcquisition, alazar, FileAcquisitionConfig, FileAcquisition
from vortex.process import CUDAProcessor, CUDAProcessorConfig, NullProcessor, NullProcessorConfig
from vortex.io import DAQmxIO, DAQmxConfig, daqmx
from VtxEngineParams import VtxEngineParams, AcquisitionType
from AcqParams import AcqParams, DEFAULT_ACQ_PARAMS
import numpy as np
from typing import Tuple

class VtxBaseEngine():
    def __init__(self, cfg: VtxEngineParams, acq: AcqParams=DEFAULT_ACQ_PARAMS, dsp: Tuple[float, float]=(0,0)):

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

            # pull in acquisition params
            ac.records_per_block = acq.ascans_per_block
            ac.samples_per_record = acq.samples_per_ascan

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
            ac.records_per_block = acq.ascans_per_block
            ac.samples_per_record = acq.samples_per_ascan
            ac.loop = True # repeat the file indefinitely

            acquire = FileAcquisition(get_logger('acquire', cfg.log_level))
            acquire.initialize(ac)
            self._acquire = acquire

        #
        # OCT processing setup
        #

        pc = CUDAProcessorConfig()

        # match acquisition settings
        pc.samples_per_record = acq.samples_per_ascan
        pc.ascans_per_block = acq.ascans_per_block

        pc.slots = cfg.process_slots

        # reasmpling
        pc.resampling_samples = resampling

        # spectral filter with dispersion correction
        window = np.hanning(pc.samples_per_ascan)
        phasor = dispersion_phasor(len(window), dsp)
        pc.spectral_filter = window * phasor

        # DC subtraction per block
        pc.average_window = 2 * pc.ascans_per_block

        self._octprocess = CUDAProcessor(get_logger('process', cfg.log_level))
        self._octprocess.initialize(pc)

        #
        # galvo control
        #

        # output
        ioc_out = DAQmxConfig()
        ioc_out.samples_per_block = ac.records_per_block
        ioc_out.samples_per_second = cfg.swept_source.triggers_per_second
        ioc_out.blocks_to_buffer = cfg.preload_count
        ioc_out.clock.source = "pfi12"
        ioc_out.name = 'output'

        stream = Block.StreamIndex.GalvoTarget
        xAVO = daqmx.AnalogVoltageOutput('Dev1/ao0', cfg.galvo_x_units_per_volt, stream, 0)
        xAVO.limits = cfg.galvo_x_voltage_range
        ioc_out.channels.append(xAVO)
        yAVO = daqmx.AnalogVoltageOutput('Dev1/ao1', cfg.galvo_y_units_per_volt, stream, 1)
        yAVO.limits = cfg.galvo_y_voltage_range
        ioc_out.channels.append(yAVO)

        io_out = DAQmxIO(get_logger(ioc_out.name, cfg.log_level))
        io_out.initialize(ioc_out)
        self._io_out = io_out


        # examples show this being a copy of ioc_out. Make a new one instead.
        strobec = DAQmxConfig()
        strobec.samples_per_block = ac.records_per_block
        strobec.samples_per_second = cfg.swept_source.triggers_per_second
        strobec.blocks_to_buffer = cfg.preload_count
        strobec.clock.source = "pfi12"
        strobec.name = 'strobe'
        strobec.channels.append(daqmx.DigitalOutput('Dev1/port0', Block.StreamIndex.Strobes))
        strobe = DAQmxIO(get_logger(strobec.name, cfg.log_level))
        strobe.initialize(strobec)
        self._strobe = strobe
