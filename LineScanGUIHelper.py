from ScanGUIHelper import ScanGUIHelper
from typing import Any, Dict
from ScanConfigWidget import LineScanConfigWidget
from ScanParams import LineScanParams
from AcqParams import AcqParams
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout
from vortex_tools.ui.display import CrossSectionImageWidget
from TraceWidget import TraceWidget
from LineScanTraceWidget import LineScanTraceWidget
import matplotlib as mpl
from math import radians

from vortex import Range
from vortex.scan import RasterScan, RasterScanConfig, FreeformScan, FreeformScanConfig
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
    
        print("LineScanGUIHelper.init()")
        # Create engine parts for this scan
        fc = FormatPlannerConfig()
        fc.segments_per_volume = params.lines_per_volume
        fc.records_per_segment = params.ascans_per_bscan
        fc.adapt_shape = False
        fc.mask = Flags(number)

        self._format_planner = FormatPlanner(get_logger('line format', log_level))
        self._format_planner.initialize(fc)

        # For saving volumes, this NullEndpoint is used. The volume_callback for this 
        # endpoint will be called before that of the other endpoints. If needed, we open
        # the storage in the volume_callback for this endpoint when needed. The storage 
        # is closed in the volume_callback for the SpectraStackEndpoint, which does the 
        # saving/writing of volumes.
        self._null_endpoint = NullEndpoint(get_logger('Traffic cop(line)', log_level))

        # For DISPLAYING ascans (oct-processed data), slice away half the data. 
        # This stack format executor isn't used with the other endpoints.
        sfec = StackFormatExecutorConfig()
        sfec.sample_slice = SimpleSlice(acq.samples_per_ascan // 2)
        samples_to_save = sfec.sample_slice.count()
        sfe = StackFormatExecutor()
        sfe.initialize(sfec)

        # endpoint for display of ascans
        vshape = (params.lines_per_volume, params.ascans_per_bscan, samples_to_save)
        self._logger.info('Create StackDeviceTensorEndpointInt8 with shape {0:s}'.format(str(vshape)))
        self._ascan_endpoint = StackDeviceTensorEndpointInt8(sfe, vshape, get_logger('stack', log_level))

        sfec_spectra = StackFormatExecutorConfig()
        sfe_spectra  = StackFormatExecutor()
        sfe_spectra.initialize(sfec_spectra)
        shape_spectra = (params.lines_per_volume, params.ascans_per_bscan, acq.samples_per_ascan)
        self._logger.info('Create SpectraStackHostTensorEndpointUInt16 with shape {0:s}'.format(str(shape_spectra)))
        self._spectra_endpoint = SpectraStackHostTensorEndpointUInt16(sfe_spectra, shape_spectra, get_logger('stack', log_level))

        # make an endpoint for saving spectra data
        shape = (params.lines_per_volume, params.ascans_per_bscan, acq.samples_per_ascan, 1)
        self._spectra_storage = SimpleStackUInt16(get_logger('npy-spectra', log_level))
        sfec = StackFormatExecutorConfig()
        sfe = StackFormatExecutor()
        sfe.initialize(sfec)
        self._storage_endpoint = SpectraStackEndpoint(sfe, self._spectra_storage, log=get_logger('npy-spectra', log_level))

        self._edit_widget = LineScanConfigWidget()
        self._edit_widget.setLineScanParams(self.params)
        self._plot_widget = self.linePlotWidget()

    def linePlotWidget(self):
        # importing the required libraries
        # w = QLabel('Aiming')
        # w.setStyleSheet("background-color: lightgreen")

        self._cross_widget_1 = CrossSectionImageWidget(self.ascan_endpoint, cmap=mpl.colormaps['gray'], title="one way")
        self._cross_widget_2 = CrossSectionImageWidget(self.ascan_endpoint, cmap=mpl.colormaps['gray'], title="other way")
        # self._ascan_trace_widget = TraceWidget(self.ascan_endpoint, title="ascan")
        # self._spectra_trace_widget = TraceWidget(self.spectra_endpoint, title="raw spectra")
        self._linescan_trace_widget = LineScanTraceWidget(self._ascan_endpoint, title="Galvo tuning")

        # apply settings
        if 'cross1.range' in self.settings:
            self._cross_widget_1._range = self.settings['cross1.range']

        if 'cross2.range' in self.settings:
            self._cross_widget_2._range = self.settings['cross2.range']

        if 'linescan.ylim' in self.settings:
            self._linescan_trace_widget.set_ylim(self.settings['linescan.ylim'])

        # callbacks
        self.ascan_endpoint.aggregate_segment_callback = self.cb_ascan
        # self.spectra_endpoint.aggregate_segment_callback = self.cb_spectra
        # self.spectra_endpoint.volume_callback = self.cb_volume

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
            s = EventStrobe(0)
            s.flags = Flags(self.flags)
            return (self.params.strobe_output_device, s)
        else:
            return None