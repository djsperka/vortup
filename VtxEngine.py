from VtxBaseEngine import VtxBaseEngine
from VtxEngineParams import AcquisitionType
from vortex import get_console_logger as get_logger
from vortex.engine import Engine, EngineConfig, SpectraStackEndpoint, VolumeStrobe, Block, EventStrobe
from vortex.io import DAQmxIO, DAQmxConfig, daqmx
from vortex.format import StackFormatExecutorConfig, StackFormatExecutor
from vortex.storage import SimpleStackUInt16
import logging
from typing import Tuple, Any, List
from OCTUiParams import OCTUiParams
from ScanGUIHelper import ScanGUIHelper

class VtxEngine(VtxBaseEngine):
    def __init__(self, params: OCTUiParams, helpers: List[ScanGUIHelper]):

        cfg = params.vtx

        # base class 
        super().__init__(params.vtx)
        self._logger = logging.getLogger(__name__)
        # Base class has stuff made, but no engine constructed:
        # self._acquire
        # self._octprocess  - CUDA based processing
        # self._io_out


        # Engine configuration
        ec = EngineConfig()
        ec.add_acquisition(self._acquire, [self._processor])

        # add galvo output
        if self._io_out is not None:
            ec.add_io(self._io_out, lead_samples=round(cfg.galvo_delay * cfg.ssrc_triggers_per_second))
            ec.galvo_output_channels = len(self._io_out.config.channels)

        # Add formatter and endpoints for each scan type in the parameters 
        # Also pick up any strobes that the scans might request
        # Pre-populate the strobes with a single universal VolumeStrobe
        # TODO make this part of config
        strobes = [VolumeStrobe(7)]
        for helper in helpers:
            helper.createEngineComponents(params, self._processor.config.samples_per_record)
            ec.add_processor(self._processor, [helper.components.format_planner])
            ec.add_formatter(helper.components.format_planner, helper.components.endpoints)
            s = helper.getStrobe()
            if s is not None:
                self._logger.info("Scan {0:s} has strobe output on device line {1:d} with flags {2:x}".format(helper.name, s.line, s.flags.value))
                strobes.append(s)


        # strobe
        if cfg.strobe_enabled and cfg.acquisition_type == AcquisitionType.ALAZAR_ACQUISITION:
            if len(strobes) > 0:
                strobec = DAQmxConfig()
                strobec.samples_per_block = cfg.ascans_per_block
                strobec.samples_per_second = cfg.ssrc_triggers_per_second
                strobec.blocks_to_buffer = cfg.preload_count
                strobec.clock.source = cfg.strobe_clock_source
                strobec.name = 'strobe'
                self._logger.info("Adding DigitalOutput channel for strobes on device {0:s}".format(cfg.strobe_device_channel))
                strobec.channels.append(daqmx.DigitalOutput(cfg.strobe_device_channel, Block.StreamIndex.Strobes))
                strobe = DAQmxIO(get_logger(strobec.name, cfg.log_level))
                strobe.initialize(strobec)
                self._strobe = strobe
            else:
                self._logger.warning('Strobe is enabled, but no strobe outputs are configured.')
                self._strobe = None
        else:
            self._strobe = None


        # # strobe output
        # # default is [SampleStrobe(0, 2), SampleStrobe(1, 1000), SampleStrobe(2, 1000, Polarity.Low), SegmentStrobe(3), VolumeStrobe(4)]
        # es = EventStrobe(0)
        # ec.strobes = [es]

        # ec.strobes = [SegmentStrobe(0)]
        if self._strobe is not None:
            for s in strobes:
                self._logger.info("Strobe type {0:s}, line {1:d}, flags {2:x}".format(type(s).__name__, s.line, s.flags.value))
            ec.strobes = strobes
            ec.add_io(self._strobe)


        ec.preload_count = cfg.preload_count
        ec.records_per_block = cfg.ascans_per_block
        ec.blocks_to_allocate = cfg.blocks_to_allocate
        ec.blocks_to_acquire = cfg.blocks_to_acquire

        engine = Engine(get_logger('engine', cfg.log_level))
        engine.initialize(ec)
        engine.prepare()
        self._engine = engine

    def stop(self):
        # only if we are running
        if self._engine and not self._engine.done:
            self._logger.info('stop...')
            self._engine.stop()
            self._logger.info('wait...')
            self._engine.wait()
            self._logger.info('stopped.')
        else:
            self._logger.warning('engine is not running')
            