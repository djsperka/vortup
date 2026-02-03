from ScanGUIHelper import ScanGUIHelper, ScanGUIHelperComponents
from typing import Any, Dict
from ScanConfigWidget import RasterScanConfigWidget
from ScanParams import RasterScanParams
from AcqParams import AcqParams
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from vortex_tools.ui.display import RasterEnFaceWidget, CrossSectionImageWidget
from TraceWidget import TraceWidget
import matplotlib as mpl
from math import radians

from vortex.scan import RasterScan, RasterScanConfig
from vortex.engine import StackDeviceTensorEndpointInt8, SpectraStackHostTensorEndpointUInt16, SpectraStackEndpoint, NullEndpoint
from vortex.format import FormatPlanner, FormatPlannerConfig, StackFormatExecutorConfig, StackFormatExecutor, SimpleSlice
from vortex.storage import SimpleStackUInt16
from vortex.marker import Flags
from vortex import get_console_logger as get_logger


class RasterScanGUIHelper(ScanGUIHelper):
    def __init__(self, name: str, flags: int, params: RasterScanParams, acq:AcqParams, settings: Dict[str, Any], log_level: int):
        super().__init__(name, flags, params, settings, log_level)

        self._edit_widget = RasterScanConfigWidget()
        self._edit_widget.setRasterScanParams(self.params)
        #self._plot_widget = self.rasterPlotWidget()

    def getSettings(self):
        settings = {}
        settings['enface.range'] = self._raster_widget._range
        settings['cross.range'] = self._cross_widget._range
        settings['ascan.ylim'] = list(self._ascan_trace_widget._axes.get_ylim())
        settings['spectra.ylim'] = list(self._spectra_trace_widget._axes.get_ylim())
        return settings

    def getParams(self):
        params = self._edit_widget.getRasterScanParams()
        return params

    def getScan(self):

        params = self.getParams()
        cfg = RasterScanConfig()
        cfg.ascans_per_bscan = params.ascans_per_bscan
        cfg.bscans_per_volume = params.bscans_per_volume
        cfg.bidirectional_segments = params.bidirectional_segments
        cfg.segment_extent = params.segment_extent
        cfg.volume_extent = params.volume_extent
        cfg.angle = radians(params.angle)
        cfg.flags = Flags(self.flags)
        scan = RasterScan()
        scan.initialize(cfg)
        return scan


    def clear(self):
        self._cross_widget.notify_segments([0])
        self._raster_widget.notify_segments([0])
        self._ascan_trace_widget.flush()
        self._spectra_trace_widget.flush()

    def cb_ascan(self, v):
        self._cross_widget.notify_segments(v)
        self._raster_widget.notify_segments(v)
        self._ascan_trace_widget.update_trace(v)

    def cb_spectra(self, v):
            self._spectra_trace_widget.update_trace(v)

    def cb_volume(self, sample_idx, scan_idx, volume_idx):
        """volume callback that is (should be) called prior to other volume callbacks. 
        Because of that arrangement, this callback will open storage. Same storage is closed 
        in volumeCallback2

        Args:
            sample_idx (int): sample index
            scan_idx (int): scan index
            volume_idx (int): volume index
        """
        #print("raster cb_volume({0:d},{1:d},{2:d})".format(sample_idx, scan_idx, volume_idx))
        pass

    def getStrobe(self):
        return super().getStrobe()
    
    def getEngineComponents(self, octuiparams):
        # Create engine parts for this scan
        fc = FormatPlannerConfig()
        fc.segments_per_volume = self.params.bscans_per_volume
        fc.records_per_segment = self.params.ascans_per_bscan
        fc.adapt_shape = False
        fc.mask = Flags(self.flags)

        format_planner = FormatPlanner(get_logger('raster format', self.log_level))
        format_planner.initialize(fc)

        # For saving volumes, this NullEndpoint is used. The volume_callback for this 
        # endpoint will be called before that of the other endpoints. If needed, we open
        # the storage in the volume_callback for this endpoint when needed. The storage 
        # is closed in the volume_callback for the SpectraStackEndpoint, which does the 
        # saving/writing of volumes.
        null_endpoint = NullEndpoint(get_logger('Traffic cop', self.log_level))

        # For DISPLAYING ascans (oct-processed data), slice away half the data. 
        # This stack format executor isn't used with the other endpoints.
        sfec = StackFormatExecutorConfig()
        sfec.sample_slice = SimpleSlice(octuiparams.acq.samples_per_ascan // 2)
        samples_to_save = sfec.sample_slice.count()
        sfe = StackFormatExecutor()
        sfe.initialize(sfec)

        # endpoint for display of ascans
        vshape = (self.params.bscans_per_volume, self.params.ascans_per_bscan, samples_to_save)
        self._logger.info('Create StackDeviceTensorEndpointInt8 with shape {0:s}'.format(str(vshape)))
        ascan_endpoint = StackDeviceTensorEndpointInt8(sfe, vshape, get_logger('stack', self.log_level))


        sfec_spectra = StackFormatExecutorConfig()
        sfe_spectra  = StackFormatExecutor()
        sfe_spectra.initialize(sfec_spectra)
        shape_spectra = (self.params.bscans_per_volume, self.params.ascans_per_bscan, octuiparams.acq.samples_per_ascan)
        self._logger.info('Create SpectraStackHostTensorEndpointUInt16 with shape {0:s}'.format(str(shape_spectra)))
        spectra_endpoint = SpectraStackHostTensorEndpointUInt16(sfe_spectra, shape_spectra, get_logger('stack', self.log_level))

        # make an endpoint for saving spectra data
        shape = (self.params.bscans_per_volume, self.params.ascans_per_bscan, octuiparams.acq.samples_per_ascan, 1)
        spectra_storage = SimpleStackUInt16(get_logger('npy-spectra', self.log_level))
        sfec = StackFormatExecutorConfig()
        sfe = StackFormatExecutor()
        sfe.initialize(sfec)
        storage_endpoint = SpectraStackEndpoint(sfe, spectra_storage, log=get_logger('npy-spectra', self.log_level))


        return ScanGUIHelperComponents(format_planner=format_planner, null_endpoint=null_endpoint, storage_endpoint=storage_endpoint, spectra_endpoint=spectra_endpoint, ascan_endpoint=ascan_endpoint)


    def getPlotWidget(self, components: ScanGUIHelperComponents) -> QWidget:
        raster_widget = RasterEnFaceWidget(components.ascan_endpoint, cmap=mpl.colormaps['gray'])
        cross_widget = CrossSectionImageWidget(components.ascan_endpoint, cmap=mpl.colormaps['gray'])
        ascan_trace_widget = TraceWidget(components.ascan_endpoint, title="ascan")
        spectra_trace_widget = TraceWidget(components.spectra_endpoint, title="raw spectra")

        # apply settings
        if 'enface.range' in self.settings:
            raster_widget._range = self.settings['enface.range']

        if 'cross.range' in self.settings:
            cross_widget._range = self.settings['cross.range']

        if 'ascan.ylim' in self.settings:
            ascan_trace_widget.set_ylim(self.settings['ascan.ylim'])

        if 'spectra.ylim' in self.settings:
            spectra_trace_widget.set_ylim(self.settings['spectra.ylim'])

        
        # callbacks
        components.ascan_endpoint.aggregate_segment_callback = self.cb_ascan
        components.spectra_endpoint.aggregate_segment_callback = self.cb_spectra
        components.spectra_endpoint.volume_callback = self.cb_volume

        # 
        vbox = QVBoxLayout()
        hbox_upper = QHBoxLayout()
        hbox_upper.addWidget(raster_widget)
        hbox_upper.addWidget(cross_widget)
        hbox_lower = QHBoxLayout()
        hbox_lower.addWidget(spectra_trace_widget)
        hbox_lower.addWidget(ascan_trace_widget)
        vbox.addLayout(hbox_upper)
        vbox.addLayout(hbox_lower)
        w = QWidget()
        w.setLayout(vbox)
        return w

