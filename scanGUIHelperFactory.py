from typing import Any

from AimingScanGUIHelper import AimingScanGUIHelper
from GalvoTuningScanGUIHelper import GalvoTuningScanGUIHelper
from LineScanGUIHelper import LineScanGUIHelper
from RasterScanGuiHelper import RasterScanGUIHelper
from ScanGUIHelper import ScanGUIHelper
from ScanParams import AimingScanParams, GalvoTuningScanParams, LineScanParams, RasterScanParams


def scanGUIHelperFactory(
    name: str,
    number: int,
    params: RasterScanParams | AimingScanParams | LineScanParams | GalvoTuningScanParams,
    settings: dict[str, Any],
    octui,
) -> ScanGUIHelper:
    if isinstance(params, RasterScanParams):
        g = RasterScanGUIHelper(name, number, params, settings, octui)
    elif isinstance(params, AimingScanParams):
        g = AimingScanGUIHelper(name, number, params, settings, octui)
    elif isinstance(params, LineScanParams):
        g = LineScanGUIHelper(name, number, params, settings, octui)
    elif isinstance(params, GalvoTuningScanParams):
        g = GalvoTuningScanGUIHelper(name, number, params, settings, octui)
    else:
        raise TypeError(
            "Must pass one of these: RasterScanParams|AimingScanParams|LineScanParams|GalvoTuningScanGUIHelper"
        )
    return g
