from VtxBaseEngine import VtxBaseEngine
from vortex import Range, get_console_logger as get_logger
from vortex.marker import Flags
from vortex.engine import Engine, EngineConfig, Block, dispersion_phasor, StackDeviceTensorEndpointInt8
from vortex.acquire import AlazarConfig, AlazarAcquisition, alazar, FileAcquisitionConfig, FileAcquisition
from vortex.process import CUDAProcessor, CUDAProcessorConfig
from vortex.io import DAQmxIO, DAQmxConfig, daqmx
from VtxEngineParams import VtxEngineParams, AcquisitionType, FileSaveConfig
from vortex.scan import RasterScanConfig, RasterScan
from vortex.format import FormatPlanner, FormatPlannerConfig, StackFormatExecutorConfig, StackFormatExecutor, SimpleSlice
from vortex.storage import HDF5StackUInt16, HDF5StackInt8, HDF5StackConfig, HDF5StackHeader, SimpleStackUInt16, SimpleStackInt8, SimpleStackConfig, SimpleStackHeader
import numpy as np
from AcqParams import AcqParams, DEFAULT_ACQ_PARAMS

class VtxEngine(VtxBaseEngine):
    def __init__(self, cfg: VtxEngineParams, acq: AcqParams=DEFAULT_ACQ_PARAMS, scfg: RasterScanConfig=RasterScanConfig(), fcfg: FileSaveConfig=FileSaveConfig()):

        # base class 
        super().__init__(cfg)

        # Base class has stuff made, but no engine constructed:
        # self._acquire
        # self._octprocess  - CUDA based processing
        # self._nullprocess - no processing pass-through
        # self._io_out
        # self._strobe


        #
        # format planners - one each for spectra and ascans
        #

        fc = FormatPlannerConfig()
        fc.segments_per_volume = scfg.bscans_per_volume
        fc.records_per_segment = scfg.ascans_per_bscan
        fc.adapt_shape = False
        fc.mask = scfg.flags

        self._stack_format_spectra = FormatPlanner(get_logger('format-spectra', cfg.log_level))
        self._stack_format_spectra.initialize(fc)

        self._stack_format_ascans = FormatPlanner(get_logger('format-ascans', cfg.log_level))
        self._stack_format_ascans.initialize(fc)

        # format executor and endpoint for spectra
        sfec_spectra = StackFormatExecutorConfig()
        sfe_spectra  = StackFormatExecutor()
        sfe_spectra.initialize(sfec_spectra)
        ep = StackDeviceTensorEndpointInt8(sfe_spectra, (scfg.bscans_per_volume, scfg.ascans_per_bscan, samples_to_save), get_logger('stack', cfg.log_level))
        self._endpoint_spectra_list = [ep]

        # make another for saving spectra
        if fcfg.save_spectra:
            self._endpoint_spectra_list.append(self.getSpectraFileEndpoint(scfg))



        # format executor and endpoint for the ascans. Configured to retain half the spectrum.
        sfec_ascans = StackFormatExecutorConfig()
        sfec_ascans.sample_slice = SimpleSlice(self._octprocess.config.samples_per_ascan // 2)
        samples_to_save = sfec_ascans.sample_slice.count()
        sfe = StackFormatExecutor()
        sfe.initialize(sfec_ascans)
        self._endpoint_ascans = StackDeviceTensorEndpointInt8(sfe, (scfg.bscans_per_volume, scfg.ascans_per_bscan, samples_to_save), get_logger('stack', cfg.log_level))









        #
        # engine setup
        #

        ec = EngineConfig()
        ec.add_acquisition(self._acquire, [self._octprocess])
        ec.add_processor(self._octprocess, [self._stack_format_spectra, self._stack_format_ascans])
        ec.add_formatter(self._stack_format_ascans, [self._endpoint_ascans])

        # add galvo output
        ec.add_io(self._io_out, lead_samples=round(cfg.galvo_delay * self._io_out.config.samples_per_second))
        ec.galvo_output_channels = len(self._io_out.config.channels)
        print("there are {0:d} galvo channels".format(ec.galvo_output_channels))

        # strobe output
        ec.add_io(self._strobe)

        ec.preload_count = cfg.preload_count
        ec.records_per_block = acq.ascans_per_block
        ec.blocks_to_allocate = cfg.blocks_to_allocate
        ec.blocks_to_acquire = acq.blocks_to_acquire
        print("blocks to acquire {0:d}".format(ec.blocks_to_acquire))


        engine = Engine(get_logger('engine', cfg.log_level))
        engine.initialize(ec)
        engine.prepare()
        self._engine = engine

    def getSpectraFileStorageEndpoint(self, scfg: FileSaveConfig):
        if scfg.ext_spectra in ['matlab', 'hdf5']:
            fmt = HDF5StackHeader.MATLAB if scfg.ext_spectra == 'matlab' else HDF5StackHeader.Empty
            h5sc = HDF5StackConfig()
            h5sc.shape = (cfg.bscans_per_volume, cfg.ascans_per_bscan, self._acquire.config.samples_per_record, self._acquire.config.channels_per_sample)
            h5sc.header = fmt
            h5sc.path = f'{args.prefix}spectra{suffix}'

            storage = HDF5StackUInt16(gcl('hdf5-spectra', cfg.log_level))
            storage.open(h5sc)

            # TODO I have no idea what the difference between these is. The docs for volume_to_disk.py, where this code comes from, 
            # says that 'direct_mode'
            if args.direct_mode:
                spectra_endpoints.append(SpectraHDF5StackEndpoint(self._stack_spectra_storage, log=gcl('spectra', cfg.log_level)))
            else:
                spectra_endpoints.append(SpectraHDF5StackEndpoint(cfe_spectra, self._stack_spectra_storage, log=gcl('spectra', cfg.log_level)))


            if not args.no_save_ascans:
                # save ascan data
                h5sc = HDF5StackConfig()
                h5sc.shape = (cfg.bscans_per_volume, cfg.ascans_per_bscan, ascan_samples_to_save, 1)
                h5sc.header = fmt
                h5sc.path = f'{args.prefix}ascans{suffix}'

                self._stack_ascan_storage = HDF5StackInt8(gcl('hdf5-ascan', cfg.log_level))
                self._stack_ascan_storage.open(h5sc)
                ascan_endpoints.append(AscanHDF5StackEndpoint(cfe_ascans, self._stack_ascan_storage, log=gcl('hdf5-ascan', cfg.log_level)))

        else:

            if not args.no_save_spectra:
                # save spectra data
                npsc = SimpleStackConfig()
                npsc.shape = (cfg.bscans_per_volume, cfg.ascans_per_bscan, self._acquire.config.samples_per_record, self._acquire.config.channels_per_sample)
                npsc.header = SimpleStackHeader.NumPy
                npsc.path = f'{args.prefix}spectra.npy'

                self._stack_spectra_storage = SimpleStackUInt16(gcl('npy-spectra', cfg.log_level))
                self._stack_spectra_storage.open(npsc)

                if args.direct_mode:
                    spectra_endpoints.append(SpectraStackEndpoint(self._stack_spectra_storage, log=gcl('spectra', cfg.log_level)))
                else:
                    spectra_endpoints.append(SpectraStackEndpoint(cfe_spectra, self._stack_spectra_storage, log=gcl('spectra', cfg.log_level)))

            if not args.no_save_ascans:
                # save ascan data
                npsc = SimpleStackConfig()
                npsc.shape = (cfg.bscans_per_volume, cfg.ascans_per_bscan, ascan_samples_to_save, 1)
                npsc.header = SimpleStackHeader.NumPy
                npsc.path = f'{args.prefix}ascans.npy'

                self._stack_ascan_storage = SimpleStackInt8(gcl('npy-ascan', cfg.log_level))
                self._stack_ascan_storage.open(npsc)
                ascan_endpoints.append(AscanStackEndpoint(cfe_ascans, self._stack_ascan_storage, log=gcl('npy-ascan', cfg.log_level)))

