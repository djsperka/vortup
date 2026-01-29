from VtxBaseEngine import VtxBaseEngine
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
        acq = params.acq 
        scfg = params.scn

        # base class 
        super().__init__(params.vtx, params.acq)
        self._cfg = params.vtx
        self._logger = logging.getLogger(__name__)
        # Base class has stuff made, but no engine constructed:
        # self._acquire
        # self._octprocess  - CUDA based processing
        # self._io_out
        # self._strobe


        # Engine configuration
        ec = EngineConfig()
        ec.add_acquisition(self._acquire, [self._octprocess])

        # add galvo output
        if self._io_out is not None:
            ec.add_io(self._io_out, lead_samples=round(cfg.galvo_delay * cfg.ssrc_triggers_per_second))
            ec.galvo_output_channels = len(self._io_out.config.channels)

        # Add formatter and endpoints for each scan type in the parameters 
        # Also pick up any strobes that the scans might request
        # Pre-populate the strobes with a single universal VolumeStrobe
        # TODO make this part of config
        v=VolumeStrobe(0)   # default flags value is 0xfffffffffffff..., so this is active on all scans
        strobe_tuples = [("Dev1/port0/line7", VolumeStrobe(0))]
        for helper in helpers:
            ec.add_processor(self._octprocess, [helper.format_planner])
            ec.add_formatter(helper.format_planner, helper.endpoints)
            t = helper.getStrobe()
            if t is not None:
                t[1].line = len(strobe_tuples)
                self._logger.info("Scan {0:s} has strobe output on device {1:s}".format(helper.name, t[0]))
                strobe_tuples.append(t)


        # strobe
        if cfg.strobe_enabled:
            if len(strobe_tuples) > 0:
                strobec = DAQmxConfig()
                strobec.samples_per_block = acq.ascans_per_block
                strobec.samples_per_second = cfg.ssrc_triggers_per_second
                strobec.blocks_to_buffer = cfg.preload_count
                strobec.clock.source = cfg.strobe_clock_source
                strobec.name = 'strobe'
                for i,t in enumerate(strobe_tuples):
                    self._logger.info("Adding DigitalOutput channel for strobe on device {0:s}, line {1:d}, flags {2:x}".format(t[0], t[1].line, t[1].flags.value))
                    strobec.channels.append(daqmx.DigitalOutput(t[0], Block.StreamIndex.Strobes))
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
            ec.strobes = [t[1] for t in strobe_tuples]
            ec.add_io(self._strobe)




        ec.preload_count = cfg.preload_count
        ec.records_per_block = acq.ascans_per_block
        ec.blocks_to_allocate = cfg.blocks_to_allocate
        ec.blocks_to_acquire = acq.blocks_to_acquire

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
            
    def getSpectraStorageEndpoint(self, shape) -> Tuple[Any, Any]:

            storage = SimpleStackUInt16(get_logger('npy-spectra', self._cfg.log_level))

            # Executor config has only three properties:
            #
            # property erase_after_volume - not sure
            # property sample_slice  - Collect only a slice of samples from each ascan
            # property sample_transform - not sure
            # 
            # So basically, I'm not sure what the executor's role is here. 
            # But - when the Endpoint class is created, the executor is the first
            # arg to the constructor. 

            sfec = StackFormatExecutorConfig()
            sfe = StackFormatExecutor()
            sfe.initialize(sfec)
            endpoint_storage = SpectraStackEndpoint(sfe, storage, log=get_logger('npy-spectra', self._cfg.log_level))

            return endpoint_storage, storage
