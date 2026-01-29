from dataclasses import dataclass, field
from vortex import Range

@dataclass
class RasterScanParams():
    ascans_per_bscan: int = 500
    bscans_per_volume: int = 500
    bidirectional_segments: bool = False
    segment_extent: Range = field(default_factory=lambda: Range(-1,1))
    volume_extent: Range = field(default_factory=lambda: Range(-1,1))
    angle: float = 0.0

@dataclass
class AimingScanParams():
    ascans_per_bscan: int = 500
    bscans_per_volume: int = 50
    bidirectional_segments: bool = False
    aim_extent: Range = field(default_factory=lambda: Range(-1,1))
    angle: float = 0.0

@dataclass
class LineScanParams():
    ascans_per_bscan: int = 500
    bidirectional_segments: bool = False
    line_extent: Range = field(default_factory=lambda: Range(-1,1))
    lines_per_volume: int = 10
    angle: float = 0.0
    strobe_enabled: bool = False
    strobe_output_line: int = 0
    strobe_bscan_index: int = 0

@dataclass
class GalvoTuningScanParams():
    ascans_per_bscan: int = 500
    tuning_extent: Range = field(default_factory=lambda: Range(-1,1))
    lines_per_volume: int = 10

@dataclass
class ScanParams():
    current_index: int = 0
    scans: dict[str, RasterScanParams|AimingScanParams|LineScanParams|GalvoTuningScanParams] =  field(default_factory=lambda: {})

