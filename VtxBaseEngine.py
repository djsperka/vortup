from vortex import Range, get_console_logger as get_logger
from vortex.engine import Block, dispersion_phasor
from vortex.acquire import AlazarConfig, AlazarAcquisition, alazar, FileAcquisitionConfig, FileAcquisition
from vortex.process import CUDAProcessor, CUDAProcessorConfig, NullProcessor, NullProcessorConfig, CPUProcessor, CPUProcessorConfig
from vortex.io import DAQmxIO, DAQmxConfig, daqmx
from VtxEngineParams import VtxEngineParams, AcquisitionType
from DAQConst import getAlazarChannel
import numpy as np
from typing import Tuple
import logging

LOGGER = logging.getLogger(__name__)
class VtxBaseEngine():
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
                LOGGER.warning("alazar internal clock not tested in this program!")
                ac.clock = alazar.InternalClock(cfg.clock_samples_per_second)


                # (clock_samples_per_second, clock) = acquire_alazar_clock(cfg.swept_source, ac, cfg.clock_channel, get_logger('acquire', cfg.log_level))
                # cfg.swept_source.clock_edges_seconds = find_rising_edges(clock, clock_samples_per_second, len(cfg.swept_source.clock_edges_seconds))
                # resampling = compute_resampling(cfg.swept_source, ac.samples_per_second, cfg.samples_per_ascan)

                # # acquire enough samples to obtain the required ones
                # ac.samples_per_record = board.info.smallest_aligned_samples_per_record(resampling.max())

            else:
                ac.clock = alazar.ExternalClock(level_ratio=cfg.external_clock_level_pct, coupling=alazar.Coupling.AC, edge=alazar.ClockEdge.Rising, dual=False)

            board = alazar.Board(ac.device.system_index, ac.device.board_index)
            ac.samples_per_record = board.info.smallest_aligned_samples_per_record(cfg.ssrc_clock_rising_edges_per_trigger)
            ac.records_per_block = cfg.ascans_per_block

            # trigger with range - must be 5000 (2500 will err). TTL will work in config also. Discrepancy with docs
            ac.trigger = alazar.SingleExternalTrigger(range_millivolts=cfg.trigger_range_millivolts, level_ratio=cfg.trigger_level_fraction, delay_samples=cfg.trigger_delay_samples, slope=alazar.TriggerSlope.Positive)

            # only input channel A
            LOGGER.info("Using input channel {0:s} for input \"{1:s}\"".format(str(getAlazarChannel(cfg.input_channel)), cfg.input_channel))
            input = alazar.Input(getAlazarChannel(cfg.input_channel), cfg.input_channel_range_millivolts)
            ac.inputs.append(input)

            # # pull in acquisition params
            # ac.records_per_block = acq.ascans_per_block
            # ac.samples_per_record = acq.samples_per_ascan

            # AuxIO
            ac.options.append(alazar.AuxIOTriggerOut())

            acquire = AlazarAcquisition(get_logger('acquire', cfg.log_level))
            acquire.initialize(ac)
            self._acquire = acquire


            # Now set up CUDA processing
            self._processor_config = CUDAProcessorConfig()

            # match acquisition settings. The value for sample_per_record should be the recomputed value
            # from above. This value is taken from the VtxEngineParams, but is rounded down to the closest
            # multiple allowed by the alazar card.
            self._processor_config.samples_per_record = ac.samples_per_record
            self._processor_config.ascans_per_block = cfg.ascans_per_block
            self._processor_config.slots = cfg.process_slots

            # reasmpling
            self._processor_config.resampling_samples = resampling

            # spectral filter with dispersion correction
            self._processor_config.spectral_filter = self.get_spectral_filter(cfg.dispersion, ac.samples_per_record)

            # DC subtraction per block
            self._processor_config.average_window = 2 * self._processor_config.ascans_per_block

            self._processor = CUDAProcessor(get_logger('process', cfg.log_level))
            self._processor.initialize(self._processor_config)

        elif cfg.acquisition_type == AcquisitionType.FILE_ACQUISITION:

            # create a temporary file with a pure sinusoid for tutorial purposes only
            #spectrum = 2**15 + 2**14 * np.sin(2*np.pi * (cfg.samples_per_ascan / 4) * np.linspace(0, 1, cfg.samples_per_ascan))
            #spectrum = 2**15 + 2**14 * np.sin(2*np.pi * (8) * np.linspace(0, 1, cfg.samples_per_ascan))
            #spectrum = 2**14 + 2**13 * 0.5*(np.sin(2*np.pi * (8) * np.linspace(0, 1, cfg.samples_per_ascan)) + np.sin(2*np.pi * (3) * np.linspace(0, 1, cfg.samples_per_ascan)))
            rng = np.random.default_rng()
            spectrum = rng.integers(0, 2**14, cfg.samples_per_ascan)
            spectra = np.repeat(spectrum[None, ...], cfg.ascans_per_block, axis=0)

            import os
            from tempfile import mkstemp
            (fd, test_file_path) = mkstemp()
            # NOTE: the Python bindings are restricted to the uint16 data type
            open(test_file_path, 'wb').write(spectra.astype(np.uint16).tobytes())
            os.close(fd)
            print(test_file_path)


            # produce blocks ready from a file
            ac = FileAcquisitionConfig()
            ac.path = test_file_path
            ac.samples_per_record = cfg.samples_per_ascan
            ac.records_per_block = cfg.ascans_per_block
            ac.loop = True # repeat the file indefinitely

            acquire = FileAcquisition(get_logger('acquire', cfg.log_level))
            acquire.initialize(ac)
            self._acquire = acquire

            # configure no processing. 
            # pc = NullProcessorConfig()
            # pc.samples_per_record = ac.samples_per_record   #has to be same as that in AcquisitionConfig
            # pc.ascans_per_block = cfg.ascans_per_block

            # self._octprocess = NullProcessor()
            # self._octprocess.initialize(pc)

            # Now set up CPU processing
            self._processor_config = CPUProcessorConfig()

            # match acquisition settings. The value for sample_per_record should be the recomputed value
            # from above. This value is taken from the VtxEngineParams, but is rounded down to the closest
            # multiple allowed by the alazar card.
            self._processor_config.samples_per_record = ac.samples_per_record
            self._processor_config.ascans_per_block = cfg.ascans_per_block
            self._processor_config.slots = cfg.process_slots

            # reasmpling
            self._processor_config.resampling_samples = resampling

            # spectral filter with dispersion correction
            self._processor_config.spectral_filter = self.get_spectral_filter(cfg.dispersion, ac.samples_per_record)

            # DC subtraction per block
            self._processor_config.average_window = 2 * self._processor_config.ascans_per_block

            self._processor = CPUProcessor(get_logger('process', cfg.log_level))
            self._processor.initialize(self._processor_config)




        # Save the number of samples per record that we settled on. 
        self._samples_per_record = self._processor.config.samples_per_record

        #
        # galvo control
        #
        # Control signals for the galvonometers are sent via the analog output of the IO card. 
        # We use DAQmxIO objects to control the NI card. This card must be configured with DI drivers, 
        # and should show up in your NI-MAX application under "Devices and Instruments". Make a note
        # of the name("Dev1" in our case).
        #
        # No galvo for FileAcquisition!

        if cfg.galvo_enabled and cfg.acquisition_type == AcquisitionType.ALAZAR_ACQUISITION:
            ioc_out = DAQmxConfig()
            ioc_out.samples_per_block = cfg.ascans_per_block
            ioc_out.samples_per_second = cfg.ssrc_triggers_per_second
            ioc_out.blocks_to_buffer = cfg.preload_count
            ioc_out.clock.source = cfg.galvo_clock_source
            ioc_out.name = 'output'

            # channel 0, will be
            LOGGER.info("Galvo slow axis output on \"{0:s}\", {1:f} units/volt".format(cfg.galvo_x_device_channel, cfg.galvo_x_units_per_volt))
            xAVO = daqmx.AnalogVoltageOutput(cfg.galvo_x_device_channel, cfg.galvo_x_units_per_volt, Block.StreamIndex.GalvoTarget, 0)
            xAVO.limits = cfg.galvo_x_voltage_range
            ioc_out.channels.append(xAVO)
            LOGGER.info("Galvo fast axis output on \"{0:s}\", {1:f} units/volt".format(cfg.galvo_y_device_channel, cfg.galvo_y_units_per_volt))
            yAVO = daqmx.AnalogVoltageOutput(cfg.galvo_y_device_channel, cfg.galvo_y_units_per_volt, Block.StreamIndex.GalvoTarget, 1)
            yAVO.limits = cfg.galvo_y_voltage_range
            ioc_out.channels.append(yAVO)

            io_out = DAQmxIO(get_logger(ioc_out.name, cfg.log_level))
            io_out.initialize(ioc_out)
            self._io_out = io_out
        else:
            self._io_out = None


    def get_spectral_filter(self, dispersion: Tuple[float, float], samples_per_record: int) -> np.ndarray:
        window = np.hanning(samples_per_record)
        phasor = dispersion_phasor(len(window), list(dispersion))
        filter = window * phasor
        return filter

    def update_dispersion(self, dispersion: Tuple[float, float]):
        self._processor_config.spectral_filter = self.get_spectral_filter(dispersion, self._samples_per_record)
        self._processor.change(self._processor_config)
