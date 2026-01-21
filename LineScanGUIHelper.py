from ScanGUIHelper import ScanGUIHelper
from typing import Any, Dict
from ScanConfigWidget import LineScanConfigWidget
from ScanParams import LineScanParams
from AcqParams import AcqParams
from PyQt5.QtWidgets import QLabel
from vortex_tools.ui.display import RasterEnFaceWidget, CrossSectionImageWidget
from TraceWidget import TraceWidget
import matplotlib as mpl
from math import radians

from vortex import Range
from vortex.scan import RasterScan, RasterScanConfig
from vortex.engine import StackDeviceTensorEndpointInt8, SpectraStackHostTensorEndpointUInt16, SpectraStackEndpoint, NullEndpoint
from vortex.format import FormatPlanner, FormatPlannerConfig, StackFormatExecutorConfig, StackFormatExecutor, SimpleSlice
from vortex.storage import SimpleStackUInt16
from vortex.marker import Flags
from vortex import get_console_logger as get_logger

class LineScanGUIHelper(ScanGUIHelper):
    def __init__(self, name: str, number: int, params: LineScanParams, acq:AcqParams, settings: Dict[str, Any], log_level: int):
        super().__init__(name, number, params, settings, log_level)

        self._edit_widget = LineScanConfigWidget()
        self._edit_widget.setLineScanParams(self.params)
        self._plot_widget = self.linePlotWidget()

    def linePlotWidget(self):
        # importing the required libraries
        w = QLabel('Line')
        w.setStyleSheet("background-color: lightblue")
        return w

    def getParams(self):
        params = self._edit_widget.getLineScanParams()
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

    def getSettings(self):
        return {}

