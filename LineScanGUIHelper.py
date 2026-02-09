from ScanGUIHelper import ScanGUIHelper, ScanGUIHelperComponents
from typing import Any, Dict
from ScanConfigWidget import LineScanConfigWidget
from ScanParams import LineScanParams
from AcqParams import AcqParams
from OCTUiParams import OCTUiParams
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout
from vortex_tools.ui.display import CrossSectionImageWidget
from LineScanTraceWidget import LineScanTraceWidget
import matplotlib as mpl

from vortex import Range
from vortex.scan import RasterScanConfig, FreeformScan, FreeformScanConfig
from vortex.engine import StackDeviceTensorEndpointInt8, SpectraStackHostTensorEndpointUInt16, SpectraStackEndpoint, NullEndpoint, EventStrobe
from vortex.format import FormatPlanner, FormatPlannerConfig, StackFormatExecutorConfig, StackFormatExecutor, SimpleSlice
from vortex.storage import SimpleStackUInt16
from vortex.marker import Flags, Event
from vortex import get_console_logger as get_logger


class LineScanGUIHelper(ScanGUIHelper):
    '''
    GUIHelper for a line scan.
    '''
    def __init__(self, name: str, number: int, params: LineScanParams, acq:AcqParams, settings: Dict[str, Any], log_level: int):
        super().__init__(name, number, params, settings, log_level)

        self._edit_widget = LineScanConfigWidget()
        self._edit_widget.setLineScanParams(self.params)

        # These are saved here (they are also in _components, as part of the plot_widget)
        # for convenience
        self._cross_widget_1 = None
        self._cross_widget_2 = None
        self._linescan_trace_widget = None
        
        #self._plot_widget = self.linePlotWidget()

    def cb_ascan(self, v):
        # with self.spectra_endpoint.tensor as volume:
        #     print("{0:d}, ({1:d},{2:d},{3:d})".format(v[-1], volume.shape[0], volume.shape[1], volume.shape[2]))
        if v:
            if v[-1]%2:
                self._cross_widget_1.notify_segments(v)
            else:
                self._cross_widget_2.notify_segments(v)
        else:
            self._cross_widget_1.notify_segments(v)
            self._cross_widget_2.notify_segments(v)
        self._linescan_trace_widget.update_trace(v)

    # def cb_spectra(self, v):
    #         self._spectra_trace_widget.update_trace(v)

    def cb_volume(self, sample_idx, scan_idx, volume_idx):
        """volume callback that is (should be) called prior to other volume callbacks. 
        Because of that arrangement, this callback will open storage. Same storage is closed 
        in volumeCallback2

        Args:
            sample_idx (int): sample index
            scan_idx (int): scan index
            volume_idx (int): volume index
        """
        pass



    def getParams(self):
        params = self._edit_widget.getLineScanParams()
        return params

    def clear(self):
        print("LineScanGUIHelper::clear")

    def getSettings(self):
        settings = {}
        settings['cross1.range'] = self._cross_widget_1._range
        settings['cross2.range'] = self._cross_widget_2._range
        settings['linescan.ylim'] = list(self._linescan_trace_widget._axes.get_ylim())
        return settings
    
    def getScan(self):
        params = self.getParams()
        cfg = RasterScanConfig()
        cfg.bscans_per_volume = params.lines_per_volume
        cfg.ascans_per_bscan = params.ascans_per_bscan
        cfg.bscan_extent = params.line_extent
        cfg.volume_extent = Range(0, 0)
        cfg.bidirectional_segments = params.bidirectional_segments
        cfg.loop = True
        cfg.flags = Flags(self.flags)

        # now, for grins, let's get the segments for this scan
        segments = cfg.to_segments()

        # if strobe needed, put marker into correct segment
        if params.strobe_enabled:
            if params.strobe_bscan_index < 0 or params.strobe_bscan_index>(params.lines_per_volume-1):
                self._logger.warning("Cannot add strobe trigger at bscan index {0:d}: must be in less than lines per volume ({1:d})".format(params.strobe_bscan_index, params.lines_per_volume))
            else:
                e = Event()
                e.flags = Flags(self.flags)
                e.id = 1
                e.sample = 0
                segments[params.strobe_bscan_index].markers.append(e)

        # now make scan
        ffsc = FreeformScanConfig()
        ffsc.pattern = segments
        ffsc.loop = True

        scan = FreeformScan()
        scan.initialize(ffsc)
        # scan = RasterScan()
        # scan.initialize(cfg)
        return scan

    def getStrobe(self):
        if self.params.strobe_enabled:
            return EventStrobe(line=self.params.strobe_output_line, flags=Flags(self.flags))
        else:
            return None
        
    def createEngineComponents(self, octuiparams: OCTUiParams):
 
        fc = FormatPlannerConfig()
        fc.segments_per_volume = self.params.lines_per_volume
        fc.records_per_segment = self.params.ascans_per_bscan
        fc.adapt_shape = False
        fc.mask = Flags(self.flags)

        format_planner = FormatPlanner(get_logger('line format', self.log_level))
        format_planner.initialize(fc)

        # For saving volumes, this NullEndpoint is used. The volume_callback for this 
        # endpoint will be called before that of the other endpoints. If needed, we open
        # the storage in the volume_callback for this endpoint when needed. The storage 
        # is closed in the volume_callback for the SpectraStackEndpoint, which does the 
        # saving/writing of volumes.
        null_endpoint = NullEndpoint(get_logger('Traffic cop(line)', self.log_level))

        # For DISPLAYING ascans (oct-processed data), slice away half the data. 
        # This stack format executor isn't used with the other endpoints.
        sfec = StackFormatExecutorConfig()
        sfec.sample_slice = SimpleSlice(octuiparams.acq.samples_per_ascan // 2)
        samples_to_save = sfec.sample_slice.count()
        sfe = StackFormatExecutor()
        sfe.initialize(sfec)

        # endpoint for display of ascans
        vshape = (self.params.lines_per_volume, self.params.ascans_per_bscan, samples_to_save)
        self._logger.info('Create StackDeviceTensorEndpointInt8 with shape {0:s}'.format(str(vshape)))
        ascan_endpoint = StackDeviceTensorEndpointInt8(sfe, vshape, get_logger('stack', self.log_level))

        sfec_spectra = StackFormatExecutorConfig()
        sfe_spectra  = StackFormatExecutor()
        sfe_spectra.initialize(sfec_spectra)
        shape_spectra = (self.params.lines_per_volume, self.params.ascans_per_bscan, octuiparams.acq.samples_per_ascan)
        self._logger.info('Create SpectraStackHostTensorEndpointUInt16 with shape {0:s}'.format(str(shape_spectra)))
        spectra_endpoint = SpectraStackHostTensorEndpointUInt16(sfe_spectra, shape_spectra, get_logger('stack', self.log_level))

        # make an endpoint for saving spectra data
        shape = (self.params.lines_per_volume, self.params.ascans_per_bscan, octuiparams.acq.samples_per_ascan, 1)
        spectra_storage = SimpleStackUInt16(get_logger('npy-spectra', self.log_level))
        sfec = StackFormatExecutorConfig()
        sfe = StackFormatExecutor()
        sfe.initialize(sfec)
        storage_endpoint = SpectraStackEndpoint(sfe, spectra_storage, log=get_logger('npy-spectra', self.log_level))

        self._components = ScanGUIHelperComponents(format_planner=format_planner, null_endpoint=null_endpoint, storage_endpoint=storage_endpoint, spectra_endpoint=spectra_endpoint, storage=spectra_storage, ascan_endpoint=ascan_endpoint, plot_widget=self.getPlotWidget(ascan_endpoint))
    
    def getPlotWidget(self, ascan_endpoint) -> QWidget:
        self._cross_widget_1 = CrossSectionImageWidget(ascan_endpoint, cmap=mpl.colormaps['gray'], title="one way")
        self._cross_widget_2 = CrossSectionImageWidget(ascan_endpoint, cmap=mpl.colormaps['gray'], title="other way")
        self._linescan_trace_widget = LineScanTraceWidget(ascan_endpoint, title="Galvo tuning")

        # apply settings
        if 'cross1.range' in self.settings:
            self._cross_widget_1._range = self.settings['cross1.range']

        if 'cross2.range' in self.settings:
            self._cross_widget_2._range = self.settings['cross2.range']

        if 'linescan.ylim' in self.settings:
            self._linescan_trace_widget.set_ylim(self.settings['linescan.ylim'])

        # callbacks
        ascan_endpoint.aggregate_segment_callback = self.cb_ascan

        # 
        hbox = QHBoxLayout()
        vbox_left = QVBoxLayout()
        vbox_left.addWidget(self._cross_widget_1)
        vbox_left.addWidget(self._cross_widget_2)
        vbox_right = QVBoxLayout()
        vbox_right.addWidget(self._linescan_trace_widget)
        hbox.addLayout(vbox_left)
        hbox.addLayout(vbox_right)
        w = QWidget()
        w.setLayout(hbox)
        return w

