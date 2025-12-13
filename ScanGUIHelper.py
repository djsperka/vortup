from abc import ABC, abstractmethod
from VtxEngine import VtxEngine
from ScanConfigWidget import RasterScanConfigWidget, AimingScanConfigWidget, LineScanConfigWidget
from ScanParams import RasterScanParams, AimingScanParams, LineScanParams
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout
from vortex_tools.ui.display import RasterEnFaceWidget, CrossSectionImageWidget
from TraceWidget import TraceWidget
import matplotlib as mpl

class ScanGUIHelper(ABC):
    def __init__(self, name, number, params, log_level=1):
        self.name = name
        self.number = number
        self.params = params
        self.log_level = log_level
        self.format_planner = None
        self.endpoints = []

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
    def getParams(self):
        """Return the parameters currently specified in the edit widget"""
        pass

    @abstractmethod
    def connectToEngine(self, engine: VtxEngine):
        """Connect any callbacks needed for plots. Do not worry about whatever was connected there before.

        Args:
            engine (VtxEngine): The engine to connect to. 

        Returns:
            _type_: None
        """
        pass

    @abstractmethod
    def clear(self):
        """Clear plots and any internal data
        Returns:
            None: None
        """
        pass


from vortex.engine import StackDeviceTensorEndpointInt8, SpectraStackHostTensorEndpointUInt16, NullEndpoint
from vortex.format import FormatPlanner, FormatPlannerConfig, StackFormatExecutorConfig, StackFormatExecutor, SimpleSlice
from vortex.storage import SimpleStackUInt16
from vortex.marker import Flags
from vortex import get_console_logger as get_logger


class RasterScanGUIHelper(ScanGUIHelper):
    def __init__(self, name, number, params, log_level):
        super().__init__(name, number, params, log_level)

        self._edit_widget = RasterScanConfigWidget()
        self._edit_widget.setRasterScanParams(self.params)
        self._plot_widget = self.rasterPlotWidget()
        (self.format, self.endpoints) = self.getEngineParts(params)

    def getEngineParts(self, params: RasterScanParams):
        fc = FormatPlannerConfig()
        fc.segments_per_volume = params.bscans_per_volume
        fc.records_per_segment = params.ascans_per_bscan
        fc.adapt_shape = False
        fc.mask = Flags(self.number);

        self.format_planner = FormatPlanner(get_logger('{0:s}-format', 1))
        self.format_planner.initialize(fc)

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





    def getParams(self):
        params = self._edit_widget.getRasterScanParams()
        return params

    def rasterPlotWidget(self) -> QWidget: 
        self._raster_widget = RasterEnFaceWidget(None, cmap=mpl.colormaps['gray'])
        self._cross_widget = CrossSectionImageWidget(None, cmap=mpl.colormaps['gray'])
        self._ascan_trace_widget = TraceWidget(None, title="ascan")
        self._spectra_trace_widget = TraceWidget(None, title="raw spectra")

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

    def connectToEngine(self, engine: VtxEngine):
        self._raster_widget.endpoint = engine._endpoint_ascan_display
        self._cross_widget.endpoint = engine._endpoint_ascan_display
        self._ascan_trace_widget.endpoint = engine._endpoint_ascan_display
        self._spectra_trace_widget.endpoint = engine._endpoint_spectra_display

        engine._endpoint_spectra_display.aggregate_segment_callback = self.cb_spectra
        engine._endpoint_ascan_display.aggregate_segment_callback = self.cb_ascan

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
    def __init__(self, name, number, params, log_level):
        super().__init__(name, number, params, log_level)

        self._edit_widget = AimingScanConfigWidget()
        self._edit_widget.setAimingScanParams(self.params)

        self._plot_widget = QWidget()

    def getParams(self):
        params = self._edit_widget.getAimingScanParams()
        return params

    def connectToEngine(self, engine: VtxEngine):
        print("AimingScanGUIHelper::connectToEngine")

    def clear(self):
        print("AimingScanGUIHelper::clear")

class LineScanGUIHelper(ScanGUIHelper):
    def __init__(self, name, number, params, log_level):
        super().__init__(name, number, params, log_level)

        self._edit_widget = LineScanConfigWidget()
        self._edit_widget.setLineScanParams(self.params)

        self._plot_widget = QWidget()

    def getParams(self):
        params = self._edit_widget.getAimingScanParams()
        return params

    def connectToEngine(self, engine: VtxEngine):
        print("LineScanGUIHelper::connectToEngine")

    def clear(self):
        print("LineScanGUIHelper::clear")


def scanGUIHelperFactory(name: str, number: int, params: RasterScanParams|AimingScanParams|LineScanParams, log_level: int = 1) -> ScanGUIHelper:
    if isinstance(params, RasterScanParams): 
        g=RasterScanGUIHelper(name, number, params, log_level)
    elif isinstance(params, AimingScanParams):
        g=AimingScanGUIHelper(name, number, params, log_level)
    elif isinstance(params, LineScanParams):
        g=LineScanGUIHelper(name, number, params, log_level)
    else:
        raise TypeError('Must pass one of these: RasterScanParams|AimingScanParams|LineScanParams')
    return g
