from vortex import Range, get_console_logger as get_logger
from vortex.engine import Block, dispersion_phasor
from vortex.acquire import AlazarConfig, AlazarAcquisition, alazar, FileAcquisitionConfig, FileAcquisition
from vortex.process import CUDAProcessor, CUDAProcessorConfig
from vortex.io import DAQmxIO, DAQmxConfig, daqmx
from VtxEngineParams import VtxEngineParams, AcquisitionType
from AcqParams import AcqParams, DEFAULT_ACQ_PARAMS
from DAQConst import getAlazarChannel
import numpy as np
from typing import Tuple
import logging

LOGGER = logging.getLogger(__name__)
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
            ac.samples_per_record = board.info.smallest_aligned_samples_per_record(cfg.ssrc_clock_rising_edges_per_trigger)

            # trigger with range - must be 5000 (2500 will err). TTL will work in config also. Discrepancy with docs
            ac.trigger = alazar.SingleExternalTrigger(range_millivolts=cfg.trigger_range_millivolts, level_ratio=cfg.trigger_level_fraction, delay_samples=acq.trigger_delay_samples, slope=alazar.TriggerSlope.Positive)

            # only input channel A
            LOGGER.info("Using input channel {0:s} for input \"{1:s}\"".format(str(getAlazarChannel(cfg.input_channel)), cfg.input_channel))
            input = alazar.Input(getAlazarChannel(cfg.input_channel), cfg.input_channel_range_millivolts)
            ac.inputs.append(input)

            # pull in acquisition params
            ac.records_per_block = acq.ascans_per_block
            ac.samples_per_record = acq.samples_per_ascan

            # AuxIO
            ac.options.append(alazar.AuxIOTriggerOut())

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

        self._octprocess_config = CUDAProcessorConfig()

        # match acquisition settings
        self._octprocess_config.samples_per_record = acq.samples_per_ascan
        self._octprocess_config.ascans_per_block = acq.ascans_per_block

        self._octprocess_config.slots = cfg.process_slots

        # reasmpling
        self._octprocess_config.resampling_samples = resampling

        # spectral filter with dispersion correction
        window = np.hanning(self._octprocess_config.samples_per_ascan)
        phasor = dispersion_phasor(len(window), dsp)
        self._octprocess_config.spectral_filter = window * phasor
        self._octprocess_config.spectral_filter = self.get_spectral_filter(dsp)

        # DC subtraction per block
        self._octprocess_config.average_window = 2 * self._octprocess_config.ascans_per_block

        self._octprocess = CUDAProcessor(get_logger('process', cfg.log_level))
        self._octprocess.initialize(self._octprocess_config)

        #
        # galvo control
        #
        # Control signals for the galvonometers are sent via the analog output of the IO card. 
        # We use DAQmxIO objects to control the NI card. This card must be configured with DI drivers, 
        # and should show up in your NI-MAX application under "Devices and Instruments". Make a note
        # of the name("Dev1" in our case).
        #

        if cfg.galvo_enabled:
            ioc_out = DAQmxConfig()
            ioc_out.samples_per_block = ac.records_per_block
            ioc_out.samples_per_second = cfg.ssrc_triggers_per_second
            ioc_out.blocks_to_buffer = cfg.preload_count
            ioc_out.clock.source = cfg.galvo_clock_source
            ioc_out.name = 'output'

            # channel 0, will be
            xAVO = daqmx.AnalogVoltageOutput(cfg.galvo_x_device_channel, cfg.galvo_x_units_per_volt, Block.StreamIndex.GalvoTarget, 0)
            xAVO.limits = cfg.galvo_x_voltage_range
            ioc_out.channels.append(xAVO)
            yAVO = daqmx.AnalogVoltageOutput(cfg.galvo_y_device_channel, cfg.galvo_y_units_per_volt, Block.StreamIndex.GalvoTarget, 1)
            yAVO.limits = cfg.galvo_y_voltage_range
            ioc_out.channels.append(yAVO)

            io_out = DAQmxIO(get_logger(ioc_out.name, cfg.log_level))
            io_out.initialize(ioc_out)
            self._io_out = io_out
        else:
            self._io_out = None

        # WIP: strobes added in VtxEngine. GUIHelpers might provide strobes.
        # # examples show this being a copy of ioc_out. Make a new one instead.

        # if cfg.strobe_enabled:
        #     strobec = DAQmxConfig()
        #     strobec.samples_per_block = ac.records_per_block
        #     strobec.samples_per_second = cfg.ssrc_triggers_per_second
        #     strobec.blocks_to_buffer = cfg.preload_count
        #     strobec.clock.source = cfg.strobe_clock_source
        #     strobec.name = 'strobe'
        #     strobec.channels.append(daqmx.DigitalOutput(cfg.strobe_device_channel, Block.StreamIndex.Strobes))
        #     strobe = DAQmxIO(get_logger(strobec.name, cfg.log_level))
        #     strobe.initialize(strobec)
        #     self._strobe = strobe
        # else:
        #     self._strobe = None

    def get_spectral_filter(self, dispersion: Tuple[float, float]) -> np.ndarray:
        window = np.hanning(self._octprocess_config.samples_per_ascan)
        phasor = dispersion_phasor(len(window), dispersion)
        filter = window * phasor
        return filter

    def update_dispersion(self, dispersion: Tuple[float, float]):
        self._octprocess_config.spectral_filter = self.get_spectral_filter(dispersion)
        self._octprocess.change(self._octprocess_config)
