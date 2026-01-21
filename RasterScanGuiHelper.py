from ScanGUIHelper import ScanGUIHelper
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
    def __init__(self, name: str, number: int, params: RasterScanParams, acq:AcqParams, settings: Dict[str, Any], log_level: int):
        super().__init__(name, number, params, settings, log_level)

        # Create engine parts for this scan
        fc = FormatPlannerConfig()
        fc.segments_per_volume = params.bscans_per_volume
        fc.records_per_segment = params.ascans_per_bscan
        fc.adapt_shape = False
        fc.mask = Flags(number)

        self._format_planner = FormatPlanner(get_logger('raster format', log_level))
        self._format_planner.initialize(fc)

        # For saving volumes, this NullEndpoint is used. The volume_callback for this 
        # endpoint will be called before that of the other endpoints. If needed, we open
        # the storage in the volume_callback for this endpoint when needed. The storage 
        # is closed in the volume_callback for the SpectraStackEndpoint, which does the 
        # saving/writing of volumes.
        self._null_endpoint = NullEndpoint(get_logger('Traffic cop', log_level))

        # For DISPLAYING ascans (oct-processed data), slice away half the data. 
        # This stack format executor isn't used with the other endpoints.
        sfec = StackFormatExecutorConfig()
        sfec.sample_slice = SimpleSlice(acq.samples_per_ascan // 2)
        samples_to_save = sfec.sample_slice.count()
        sfe = StackFormatExecutor()
        sfe.initialize(sfec)

        # endpoint for display of ascans
        vshape = (params.bscans_per_volume, params.ascans_per_bscan, samples_to_save)
        self._logger.info('Create StackDeviceTensorEndpointInt8 with shape {0:s}'.format(str(vshape)))
        self._ascan_endpoint = StackDeviceTensorEndpointInt8(sfe, vshape, get_logger('stack', log_level))


        sfec_spectra = StackFormatExecutorConfig()
        sfe_spectra  = StackFormatExecutor()
        sfe_spectra.initialize(sfec_spectra)
        shape_spectra = (params.bscans_per_volume, params.ascans_per_bscan, acq.samples_per_ascan)
        self._logger.info('Create SpectraStackHostTensorEndpointUInt16 with shape {0:s}'.format(str(shape_spectra)))
        self._spectra_endpoint = SpectraStackHostTensorEndpointUInt16(sfe_spectra, shape_spectra, get_logger('stack', log_level))

        # make an endpoint for saving spectra data
        shape = (params.bscans_per_volume, params.ascans_per_bscan, acq.samples_per_ascan, 1)
        self._spectra_storage = SimpleStackUInt16(get_logger('npy-spectra', log_level))
        sfec = StackFormatExecutorConfig()
        sfe = StackFormatExecutor()
        sfe.initialize(sfec)
        self._storage_endpoint = SpectraStackEndpoint(sfe, self._spectra_storage, log=get_logger('npy-spectra', log_level))

        self._edit_widget = RasterScanConfigWidget()
        self._edit_widget.setRasterScanParams(self.params)
        self._plot_widget = self.rasterPlotWidget()

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
        cfg.flags = Flags(self.number)
        scan = RasterScan()
        scan.initialize(cfg)
        return scan

    def rasterPlotWidget2(self):
        # importing the required libraries
        w = QLabel('Raster')
        w.setStyleSheet("background-color: yellow")
        return w


    def rasterPlotWidget(self) -> QWidget: 
        self._raster_widget = RasterEnFaceWidget(self.ascan_endpoint, cmap=mpl.colormaps['gray'])
        self._cross_widget = CrossSectionImageWidget(self.ascan_endpoint, cmap=mpl.colormaps['gray'])
        self._ascan_trace_widget = TraceWidget(self.ascan_endpoint, title="ascan")
        self._spectra_trace_widget = TraceWidget(self.spectra_endpoint, title="raw spectra")

        # apply settings
        if 'enface.range' in self.settings:
            self._raster_widget._range = self.settings['enface.range']

        if 'cross.range' in self.settings:
            self._cross_widget._range = self.settings['cross.range']

        if 'ascan.ylim' in self.settings:
            self._ascan_trace_widget.set_ylim(self.settings['ascan.ylim'])

        if 'spectra.ylim' in self.settings:
            self._spectra_trace_widget.set_ylim(self.settings['spectra.ylim'])

        
        # callbacks
        self.ascan_endpoint.aggregate_segment_callback = self.cb_ascan
        self.spectra_endpoint.aggregate_segment_callback = self.cb_spectra

        # 
        vbox = QVBoxLayout()
        hbox_upper = QHBoxLayout()
        hbox_upper.addWidget(self._raster_widget)
        hbox_upper.addWidget(self._cross_widget)
        hbox_lower = QHBoxLayout()
        hbox_lower.addWidget(self._spectra_trace_widget)
        hbox_lower.addWidget(self._ascan_trace_widget)
        vbox.addLayout(hbox_upper)
        vbox.addLayout(hbox_lower)
        w = QWidget()
        w.setLayout(vbox)
        return w

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

