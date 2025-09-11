from VtxBaseEngine import VtxBaseEngine
from vortex import get_console_logger as get_logger
from vortex.engine import Engine, EngineConfig, StackDeviceTensorEndpointInt8, SpectraStackHostTensorEndpointUInt16, SpectraStackEndpoint, NullEndpoint
from vortex.format import FormatPlanner, FormatPlannerConfig, StackFormatExecutorConfig, StackFormatExecutor, SimpleSlice
from vortex.storage import SimpleStackUInt16
import logging
from typing import Tuple, Any
from OCTUiParams import OCTUiParams

class VtxEngine(VtxBaseEngine):
    def __init__(self, params: OCTUiParams):

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


        #
        # format planners - one each for spectra and ascans. The config for each is identical.
        #
        # The format planner is actually inserted into the pipeline.
        # Its config specifies the size and shape of the volume. 
        # The bool values are initialized,  but the shape values
        # are NOT. Presumably, the job of the formatter is to assemble
        # collected data into data structures in the expected shape.
        # 
        # Also, the 2D shape is known here, but not the depth. 
        # We specify records/segment (ascans per bscan) and 
        # segments/volume (bscans per volume). We do NOT specify
        # anything like "samples per record" of "samples per ascan" here. 
        #
        # I'd speculate that this means that ascans, or records, are 
        # always passed as a unit from the acquisition module. They'd be 
        # collected that way, because each ascan is a sequence of K-clock 
        # triggers within a single sweep. 
        #
        # adapt_shape: bool  (False)
        # flip_reversed: bool (True)
        # mask: vortex.marker.Flags
        # records_per_segment: int - e.g. ascans_per_bscan
        # segments_per_volume: int - e.g. bscans_per_volume
        # shape: List[int[2]]
        # strip_inactive: bool (True)


        fc = FormatPlannerConfig()
        fc.segments_per_volume = scfg.bscans_per_volume
        fc.records_per_segment = scfg.ascans_per_bscan
        fc.adapt_shape = False
        #fc.mask = scfg.flags


        stack_format_ascans = FormatPlanner(get_logger('raster format', cfg.log_level))
        stack_format_ascans.initialize(fc)
        self._format_planner_ascans = stack_format_ascans

        stack_format_spectra = FormatPlanner(get_logger('raster format', cfg.log_level))
        stack_format_spectra.initialize(fc)
        self._format_planner_spectra = stack_format_spectra


        # As endpoints are created, stuff them into this list. 
        # They are added to the engine all at once.
        endpoints = []

        # For saving volumes, this NullEndpoint is used. The volume_callback for this 
        # endpoint will be called before that of the other endpoints. If needed, we open
        # the storage in the volume_callback for this endpoint when needed. The storage 
        # is closed in the volume_callback for the SpectraStackEndpoint, which does the 
        # saving/writing of volumes.
        self._null_endpoint = NullEndpoint(get_logger('Traffic cop', cfg.log_level))
        endpoints.append(self._null_endpoint)

        # For DISPLAYING ascans (oct-processed data), slice away half the data. 
        # This stack format executor isn't used with the other endpoints.
        sfec = StackFormatExecutorConfig()
        sfec.sample_slice = SimpleSlice(self._octprocess.config.samples_per_ascan // 2)
        samples_to_save = sfec.sample_slice.count()
        sfe = StackFormatExecutor()
        sfe.initialize(sfec)

        # endpoint for display of ascans
        vshape = (scfg.bscans_per_volume, scfg.ascans_per_bscan, samples_to_save)
        self._logger.info('Create StackDeviceTensorEndpointInt8 with shape {0:s}'.format(str(vshape)))
        self._endpoint_ascan_display = StackDeviceTensorEndpointInt8(sfe, vshape, get_logger('stack', cfg.log_level))
        endpoints.append(self._endpoint_ascan_display)


        sfec_spectra = StackFormatExecutorConfig()
        sfe_spectra  = StackFormatExecutor()
        sfe_spectra.initialize(sfec_spectra)
        shape_spectra = (scfg.bscans_per_volume, scfg.ascans_per_bscan, acq.samples_per_ascan)
        self._logger.info('Create SpectraStackHostTensorEndpointUInt16 with shape {0:s}'.format(str(shape_spectra)))
        self._endpoint_spectra_display = SpectraStackHostTensorEndpointUInt16(sfe_spectra, shape_spectra, get_logger('stack', cfg.log_level))
        endpoints.append(self._endpoint_spectra_display)

        # make an endpoint for saving spectra data
        shape = (scfg.bscans_per_volume, scfg.ascans_per_bscan, acq.samples_per_ascan, 1)
        self._endpoint_spectra_storage, self._spectra_storage = self.getSpectraStorageEndpoint(shape)
        endpoints.append(self._endpoint_spectra_storage)

        #
        # engine setup
        #

        ec = EngineConfig()
        ec.add_acquisition(self._acquire, [self._octprocess])
        ec.add_processor(self._octprocess, [self._format_planner_ascans])
        ec.add_formatter(self._format_planner_ascans, endpoints)

        # add galvo output
        ec.add_io(self._io_out, lead_samples=round(cfg.galvo_delay * self._io_out.config.samples_per_second))
        ec.galvo_output_channels = len(self._io_out.config.channels)

        # strobe output
        # default is [SampleStrobe(0, 2), SampleStrobe(1, 1000), SampleStrobe(2, 1000, Polarity.Low), SegmentStrobe(3), VolumeStrobe(4)]
        # ec.strobes = [VolumeStrobe(0)]
        # ec.strobes = [SegmentStrobe(0)]
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
            self._engine.stop()
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
