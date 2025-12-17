from dataclasses import dataclass, field
from vortex import Range
from vortex.scan import RasterScanConfig


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



@dataclass
class ScanParams():
    current_index: int = 0
    scans: dict[str, RasterScanParams|AimingScanParams|LineScanParams] =  field(default_factory=lambda: {})

#     def getRasterScanConfig(self):
#         cfg = RasterScanConfig()
#         if self.current_index == 0:
#             cfg.ascans_per_bscan = self.ascans_per_bscan
#             cfg.bscans_per_volume = self.bscans_per_volume
#             cfg.bidirectional_segments = self.bidirectional_segments
#             cfg.segment_extent = self.segment_extent
#             cfg.volume_extent = self.volume_extent
#         else:
#             cfg.angle = self.angle
#             cfg.ascans_per_bscan = self.ascans_per_bscan
#             cfg.bscans_per_volume = 1
#             cfg.bidirectional_segments = self.bidirectional_segments
#             cfg.segment_extent = self.segment_extent
#             cfg.volume_extent = Range(0, 0)
#         return cfg

# DEFAULT_SCAN_PARAMS = ScanParams(0, 500, 500, False, Range(-1, 1), Range(-1,1), 0)

