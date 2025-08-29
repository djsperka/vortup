from VtxBaseEngine import VtxBaseEngine
from vortex import Range, get_console_logger as get_logger
from vortex.marker import Flags
from vortex.engine import Engine, EngineConfig, Block, dispersion_phasor, StackDeviceTensorEndpointInt8, SpectraStackHostTensorEndpointUInt16, AscanStackEndpoint, SpectraStackEndpoint, VolumeStrobe, SegmentStrobe
from VtxEngineParams import VtxEngineParams, FileSaveConfig
from vortex.scan import RasterScanConfig
from vortex.format import FormatPlanner, FormatPlannerConfig, StackFormatExecutorConfig, StackFormatExecutor, SimpleSlice
from vortex.storage import HDF5StackUInt16, HDF5StackInt8, HDF5StackConfig, HDF5StackHeader, SimpleStackUInt16, SimpleStackInt8, SimpleStackConfig, SimpleStackHeader
import numpy as np
import logging
from typing import Tuple, Union, Any
#from AcqParams import AcqParams, DEFAULT_ACQ_PARAMS
from OCTUiParams import OCTUiParams

class VtxEngine(VtxBaseEngine):
    def __init__(self, params: OCTUiParams, fcfg_ascans: FileSaveConfig=FileSaveConfig('ascans'), fcfg_spectra: FileSaveConfig=FileSaveConfig('spectra')):

        cfg = params.vtx
        acq = params.acq 
        scfg = params.scn

        # base class 
        super().__init__(params.vtx, params.acq)
        self._cfg = params.vtx
        self._fcfg_ascans = fcfg_ascans
        self._fcfg_spectra = fcfg_spectra
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

        # For DISPLAYING ascans (oct-processed data), slice away half the data. 
        # This stack format executor isn't used with the other endpoints.
        sfec = StackFormatExecutorConfig()
        sfec.sample_slice = SimpleSlice(self._octprocess.config.samples_per_ascan // 2)
        samples_to_save = sfec.sample_slice.count()
        sfe = StackFormatExecutor()
        sfe.initialize(sfec)

        # endpoint for display
        vshape = (scfg.bscans_per_volume, scfg.ascans_per_bscan, samples_to_save)
        self._logger.info('Create StackDeviceTensorEndpointInt8 with shape {0:s}'.format(str(vshape)))
        self._endpoint_ascan_display = StackDeviceTensorEndpointInt8(sfe, vshape, get_logger('stack', cfg.log_level))
        endpoints.append(self._endpoint_ascan_display)

        if fcfg_ascans.save:
            # endpoint for saving ascan data
            # Will save ascans - a full volume at a time. Save all data acquired!
            # Shape of data SAVED will be different than the displayed data. Here we save all samples, not half of them.
            # The storage object 'SimpleStackInt8' doesn't save data until you call open().

            shape = (scfg.bscans_per_volume, scfg.ascans_per_bscan, samples_to_save, 1)
            self._endpoint_ascan_storage, self._ascan_storage = self.getStorageEndpoint(fcfg_ascans, shape)
            endpoints.append(self._endpoint_ascan_storage)


        sfec_spectra = StackFormatExecutorConfig()
        sfe_spectra  = StackFormatExecutor()
        sfe_spectra.initialize(sfec_spectra)
        shape_spectra = (scfg.bscans_per_volume, scfg.ascans_per_bscan, acq.samples_per_ascan)
        self._logger.info('Create SpectraStackHostTensorEndpointUInt16 with shape {0:s}'.format(str(shape_spectra)))
        self._endpoint_spectra_display = SpectraStackHostTensorEndpointUInt16(sfe_spectra, shape_spectra, get_logger('stack', cfg.log_level))
        endpoints.append(self._endpoint_spectra_display)
        if fcfg_spectra.save:

            # make an endpoint for saving spectra data
            shape = (scfg.bscans_per_volume, scfg.ascans_per_bscan, acq.samples_per_ascan, 1)
            self._endpoint_spectra_storage, self._spectra_storage = self.getStorageEndpoint(fcfg_spectra, shape)
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
        #self._logger.info("there are {0:d} galvo channels".format(ec.galvo_output_channels))

        # strobe output
        # default is [SampleStrobe(0, 2), SampleStrobe(1, 1000), SampleStrobe(2, 1000, Polarity.Low), SegmentStrobe(3), VolumeStrobe(4)]
        # ec.strobes = [VolumeStrobe(0)]
        # ec.strobes = [SegmentStrobe(0)]
        ec.add_io(self._strobe)

        ec.preload_count = cfg.preload_count
        ec.records_per_block = acq.ascans_per_block
        ec.blocks_to_allocate = cfg.blocks_to_allocate
        ec.blocks_to_acquire = acq.blocks_to_acquire
        #self._logger.info("blocks to acquire {0:d}".format(ec.blocks_to_acquire))


        engine = Engine(get_logger('engine', cfg.log_level))
        engine.initialize(ec)
        engine.prepare()
        self._engine = engine

    def stop(self):
        # only if we are running
        if self._engine and not self._engine.done:
            if self._fcfg_spectra.save:
                self._spectra_storage.close()
            if self._fcfg_ascans.save:
                self._ascan_storage.close()
            self._engine.stop()
        else:
            self._logger.warning('engine is not running')
            
    def getStorageEndpoint(self, fcfg: FileSaveConfig, shape) -> Tuple[Any, Any]:

        # The 'type' of the fcfg should be either 'spectra' or 'ascans'
        if fcfg.type=='spectra':

            if fcfg.extension == "npy":
                npsc = SimpleStackConfig()
                npsc.shape = shape
                npsc.header = SimpleStackHeader.NumPy
                npsc.path = fcfg.filename
                storage = SimpleStackUInt16(get_logger('npy-spectra', self._cfg.log_level))
                storage.open(npsc)

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

                def local_cb(sample_idx, scan_idx, volume_idx):
                    print("volume_callback ", volume_idx)
                    print("storage: ", endpoint_storage)
                    storage.close()
                endpoint_storage.volume_callback = local_cb
            else:
                self._logger.warning('extension {0:s} not supported yet sorry, use npy'.format(fcfg.extension))
                raise NotImplementedError('extension {0:s} not supported yet sorry, use npy'.format(fcfg.extension))

        elif fcfg.type=='ascans':
            if fcfg.extension == "npy":
                npsc = SimpleStackConfig()
                npsc.shape = shape
                npsc.header = SimpleStackHeader.NumPy
                npsc.path = fcfg.filename

                sfec = StackFormatExecutorConfig()
                sfe = StackFormatExecutor()
                sfe.initialize(sfec)
                storage = SimpleStackInt8(get_logger('npy-ascan', self._cfg.log_level))
                storage.open(npsc)
                endpoint_storage = AscanStackEndpoint(sfe, storage, log=get_logger('npy-ascan', self._cfg.log_level))

            else:
                self._logger.warning('extension {0:s} not supported yet sorry, use npy'.format(fcfg.extension))
                raise NotImplementedError('extension {0:s} not supported yet sorry, use npy'.format(fcfg.extension))

        else:
            raise ValueError('FileSaveConfig.type must be either ascans or spectra. ''{0:s}'' not supported.'.format(fcfg.type))


        return endpoint_storage, storage
