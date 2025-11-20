from VtxEngine import VtxEngine
from vortex import get_console_logger as get_logger
from vortex.engine import Engine, EngineConfig, StackDeviceTensorEndpointInt8, SpectraStackHostTensorEndpointUInt16, SpectraStackEndpoint, NullEndpoint
from vortex.format import FormatPlanner, FormatPlannerConfig, StackFormatExecutorConfig, StackFormatExecutor, SimpleSlice
from vortex.storage import SimpleStackUInt16
from ScanParams import ScanParams

class ScanManager():
    def __init__(self, scfg: ScanParams, log_level: int=1):
        self._savingVolumesNow = False
        self._savingVolumesStopNow = False
        self._savingVolumesThisMany = 0
        self._savingVolumesThisManySaved = 0
        self._savingVolumesRequested = False

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


        stack_format_ascans = FormatPlanner(get_logger('raster format', log_level))
        stack_format_ascans.initialize(fc)
        self._format_planner_ascans = stack_format_ascans

        stack_format_spectra = FormatPlanner(get_logger('raster format', log_level))
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
        self._null_endpoint = NullEndpoint(get_logger('Traffic cop', log_level))
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
        self._endpoint_ascan_display = StackDeviceTensorEndpointInt8(sfe, vshape, get_logger('stack', log_level))
        endpoints.append(self._endpoint_ascan_display)


        sfec_spectra = StackFormatExecutorConfig()
        sfe_spectra  = StackFormatExecutor()
        sfe_spectra.initialize(sfec_spectra)
        shape_spectra = (scfg.bscans_per_volume, scfg.ascans_per_bscan, acq.samples_per_ascan)
        self._logger.info('Create SpectraStackHostTensorEndpointUInt16 with shape {0:s}'.format(str(shape_spectra)))
        self._endpoint_spectra_display = SpectraStackHostTensorEndpointUInt16(sfe_spectra, shape_spectra, get_logger('stack', log_level))
        endpoints.append(self._endpoint_spectra_display)

        # make an endpoint for saving spectra data
        shape = (scfg.bscans_per_volume, scfg.ascans_per_bscan, acq.samples_per_ascan, 1)
        self._endpoint_spectra_storage, self._spectra_storage = self.getSpectraStorageEndpoint(shape)
        endpoints.append(self._endpoint_spectra_storage)

    def engineConfig(self, ec: EngineConfig):
        ec.add_acquisition(self._acquire, [self._octprocess])
        ec.add_processor(self._octprocess, [self._format_planner_ascans])
        ec.add_formatter(self._format_planner_ascans, endpoints)





    def volumeCallback(self, arg0, arg1, arg2):
        """volume callback that is (should be) called prior to other volume callbacks. 
        Because of that arrangement, this callback will open storage. Same storage is closed 
        in volumeCallback2

        Args:
            sample_idx (int): sample index
            scan_idx (int): scan index
            volume_idx (int): volume index
        """

        #self._logger.info("volumeCallback({0:d}, {1:d}, {2:d})".format(arg0, arg1, arg2))
        if self._savingVolumesRequested:
            (bOK, filename) = self.checkFileSaveStuff()
            if bOK:
                # Create SimpleStackConfig to config storage
                npsc = SimpleStackConfig()
                npsc.shape = (self._params.scn.bscans_per_volume, self._params.scn.ascans_per_bscan, self._params.acq.samples_per_ascan, 1)
                npsc.header = SimpleStackHeader.NumPy
                npsc.path = filename
                self._logger.info('Open storage.')
                self._vtxengine._spectra_storage.open(npsc)
                self._savingVolumesNow = True
                self._savingVolumesRequested = False
                #self._savingVolumesThisMany = SHOULD HAVE BEEN SET IN PB CALLBACK WHEN SAVING VOLUMES REQUESTED
                self._savingVolumesThisManySaved = 0
                self._octDialog.gbSaveVolumes.enableSaving(False, self._savingVolumesThisMany==0)
            else:
                self._logger.warning("Cannot open file {0:s} for saving.".format(filename))
                self._savingVolumesRequested = False

    def volumeCallback2(self, arg0, arg1, arg2):
        """This callback will close a file if opened.

        Args:
            arg0 (_type_): _description_
            arg1 (_type_): _description_
            arg2 (_type_): _description_
        """
        if self._savingVolumesNow:

            # this is called after the current volume has been written
            self._savingVolumesThisManySaved = self._savingVolumesThisManySaved + 1

            if self._savingVolumesStopNow or (self._savingVolumesThisMany > 0 and self._savingVolumesThisManySaved == self._savingVolumesThisMany):

                self._logger.info("Saved {0:d} volumes.".format(self._savingVolumesThisManySaved))
                # close file
                self._savingVolumesNow = False
                self._savingVolumesStopNow = False
                self._savingVolumesThisManySaved = 0
                self._savingVolumesThisMany = 0
                self._savingVolumesRequested = False
                self._vtxengine._spectra_storage.close()
                self._octDialog.gbSaveVolumes.enableSaving(True)
