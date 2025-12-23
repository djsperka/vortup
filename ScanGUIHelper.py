from abc import ABC, abstractmethod
from typing import List, Any
from ScanConfigWidget import RasterScanConfigWidget, AimingScanConfigWidget, LineScanConfigWidget
from ScanParams import RasterScanParams, AimingScanParams, LineScanParams
from AcqParams import AcqParams
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from vortex_tools.ui.display import RasterEnFaceWidget, CrossSectionImageWidget
from TraceWidget import TraceWidget
import matplotlib as mpl

from vortex import Range
from vortex.scan import RasterScan, RasterScanConfig, RadialScan, RadialScanConfig
from vortex.engine import StackDeviceTensorEndpointInt8, SpectraStackHostTensorEndpointUInt16, SpectraStackEndpoint, NullEndpoint
from vortex.format import FormatPlanner, FormatPlannerConfig, StackFormatExecutorConfig, StackFormatExecutor, SimpleSlice
from vortex.storage import SimpleStackUInt16
from vortex.marker import Flags
from vortex import get_console_logger as get_logger
import logging

class ScanGUIHelper(ABC):
    def __init__(self, name, number, params, log_level=1):
        self.name = name
        self.number = number
        self.params = params
        self.log_level = log_level
        self._logger = logging.getLogger('GUIHeper({0:s})'.format(self.name))

    @property 
    def format_planner(self) -> FormatPlanner:
        '''
        Returns format planner for this scan
        
        :param self: Should be a FormatPlaner, which can be used in EngineConfig.add_processor. Subclasses should set value.

        '''
        return self._format_planner

    @property
    def endpoints(self) -> List[Any]:
        return [self._null_endpoint, self._storage_endpoint, self._spectra_endpoint, self.ascan_endpoint]

    @property
    def null_endpoint(self) -> NullEndpoint:
        return self._null_endpoint
    
    @property
    def storage_endpoint(self) -> NullEndpoint:
        return self._storage_endpoint
    
    @property
    def ascan_endpoint(self):
        return self._ascan_endpoint
    
    @property
    def spectra_endpoint(self):
        return self._spectra_endpoint


    @property
    def plot_widget(self):
        '''
        Widget displayed in the plotting widget - QStackedWidget. Subclasses should set this.
        
        :param self: Description
        '''
        return self._plot_widget

    @property
    def edit_widget(self):
        '''
        Widget displayed in the editing widget - QStackedWidget. Subclasses should set this.
        
        :param self: Description
        '''
        return self._edit_widget

    @abstractmethod
    def getScan(self):
        '''
        Returns a configured scan pattern, e.g. RasterScan
        
        :param self: Description
        '''

    @abstractmethod
    def getParams(self):
        """Return the parameters currently specified in the edit widget"""
        pass

    @abstractmethod
    def clear(self):
        """Clear plots and any internal data
        Returns:
            None: None
        """
        pass

class RasterScanGUIHelper(ScanGUIHelper):
    def __init__(self, name: str, number: int, params: RasterScanParams, acq:AcqParams, log_level: int):
        super().__init__(name, number, params, log_level)

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


class AimingScanGUIHelper(ScanGUIHelper):
    '''
    GUIHelper for an aiming scan. The config for an aiming scan 
    '''
    def __init__(self, name, number, params, acq, log_level):
        super().__init__(name, number, params, log_level)

        # Create engine parts for this scan
        fc = FormatPlannerConfig()
        fc.segments_per_volume = params.bscans_per_volume  # TODO
        fc.records_per_segment = params.ascans_per_bscan
        fc.adapt_shape = False
        fc.mask = Flags(number)

        self._format_planner = FormatPlanner(get_logger('aiming format', log_level))
        self._format_planner.initialize(fc)

        # For saving volumes, this NullEndpoint is used. The volume_callback for this 
        # endpoint will be called before that of the other endpoints. If needed, we open
        # the storage in the volume_callback for this endpoint when needed. The storage 
        # is closed in the volume_callback for the SpectraStackEndpoint, which does the 
        # saving/writing of volumes.
        self._null_endpoint = NullEndpoint(get_logger('Traffic cop(aiming)', log_level))

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

        self._edit_widget = AimingScanConfigWidget()
        self._edit_widget.setAimingScanParams(self.params)
        self._plot_widget = self.aimingPlotWidget()

    def aimingPlotWidget(self):
        # importing the required libraries
        # w = QLabel('Aiming')
        # w.setStyleSheet("background-color: lightgreen")

        self._cross_widget_1 = CrossSectionImageWidget(self.ascan_endpoint, cmap=mpl.colormaps['gray'], title="horiz")
        self._cross_widget_2 = CrossSectionImageWidget(self.ascan_endpoint, cmap=mpl.colormaps['gray'], title="vert")
        self._ascan_trace_widget = TraceWidget(self.ascan_endpoint, title="ascan")
        self._spectra_trace_widget = TraceWidget(self.spectra_endpoint, title="raw spectra")

        # callbacks
        self.ascan_endpoint.aggregate_segment_callback = self.cb_ascan
        self.spectra_endpoint.aggregate_segment_callback = self.cb_spectra

        # 
        vbox = QVBoxLayout()
        hbox_upper = QHBoxLayout()
        hbox_upper.addWidget(self._cross_widget_1)
        hbox_upper.addWidget(self._cross_widget_2)
        hbox_lower = QHBoxLayout()
        hbox_lower.addWidget(self._spectra_trace_widget)
        hbox_lower.addWidget(self._ascan_trace_widget)
        vbox.addLayout(hbox_upper)
        vbox.addLayout(hbox_lower)
        w = QWidget()
        w.setLayout(vbox)
        return w

    def cb_ascan(self, v):
        if v:
            if v[-1]%2:
                self._cross_widget_1.notify_segments(v)
            else:
                self._cross_widget_2.notify_segments(v)
        else:
            self._cross_widget_1.notify_segments(v)
            self._cross_widget_2.notify_segments(v)
        self._ascan_trace_widget.update_trace(v)

    def cb_spectra(self, v):
            self._spectra_trace_widget.update_trace(v)

    def getParams(self):
        params = self._edit_widget.getAimingScanParams()
        return params

    def clear(self):
        print("AimingScanGUIHelper::clear")

    def getScan(self):
        params = self.getParams()
        cfg = RadialScanConfig()
        cfg.ascans_per_bscan = params.ascans_per_bscan
        cfg.bscans_per_volume = params.bscans_per_volume
        cfg.bidirectional_segments = params.bidirectional_segments
        cfg.segment_extent = params.aim_extent
        cfg.volume_extent = params.aim_extent
        cfg.flags = Flags(self.number)
        cfg.set_aiming()
        scan = RadialScan()
        scan.initialize(cfg)
        return scan


class LineScanGUIHelper(ScanGUIHelper):
    def __init__(self, name, number, params, log_level):
        super().__init__(name, number, params, log_level)

        self._edit_widget = LineScanConfigWidget()
        self._edit_widget.setLineScanParams(self.params)
        self._plot_widget = self.linePlotWidget()

    def linePlotWidget(self):
        # importing the required libraries
        w = QLabel('Line')
        w.setStyleSheet("background-color: lightblue")
        return w

    def getParams(self):
        params = self._edit_widget.getAimingScanParams()
        return params

    def clear(self):
        print("LineScanGUIHelper::clear")

    def getScan(self):
        params = self.getParams()
        cfg = RasterScanConfig()
        cfg.ascans_per_bscan = params.ascans_per_bscan
        cfg.bscans_per_volume = params.lines_per_volume
        cfg.bidirectional_segments = params.bidirectional_segments
        cfg.segment_extent = params.line_extent
        cfg.volume_extent = Range(0,0)
        cfg.flags = Flags(self.number)
        scan = RasterScan()
        scan.initialize(cfg)
        return scan

def scanGUIHelperFactory(name: str, number: int, params: RasterScanParams|AimingScanParams|LineScanParams, acq: AcqParams, log_level: int = 1) -> ScanGUIHelper:
    if isinstance(params, RasterScanParams): 
        g=RasterScanGUIHelper(name, number, params, acq, log_level)
    elif isinstance(params, AimingScanParams):
        g=AimingScanGUIHelper(name, number, params, acq, log_level)
    elif isinstance(params, LineScanParams):
        g=LineScanGUIHelper(name, number, params, log_level)
    else:
        raise TypeError('Must pass one of these: RasterScanParams|AimingScanParams|LineScanParams')
    return g
