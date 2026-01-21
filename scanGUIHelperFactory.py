from ScanGUIHelper import ScanGUIHelper
from RasterScanGuiHelper import RasterScanGUIHelper
from LineScanGUIHelper import LineScanGUIHelper
from AimingScanGUIHelper import AimingScanGUIHelper
from typing import Any, Dict
from ScanParams import RasterScanParams, AimingScanParams, LineScanParams
from AcqParams import AcqParams
from vortex import get_console_logger as get_logger


def scanGUIHelperFactory(name: str, number: int, params: RasterScanParams|AimingScanParams|LineScanParams, acq: AcqParams, settings: Dict[str, Any], log_level: int = 1) -> ScanGUIHelper:
    if isinstance(params, RasterScanParams): 
        g=RasterScanGUIHelper(name, number, params, acq, settings, log_level)
    elif isinstance(params, AimingScanParams):
        g=AimingScanGUIHelper(name, number, params, acq, settings, log_level)
    elif isinstance(params, LineScanParams):
        g=LineScanGUIHelper(name, number, params, settings, log_level)
    else:
        raise TypeError('Must pass one of these: RasterScanParams|AimingScanParams|LineScanParams')
    return g
