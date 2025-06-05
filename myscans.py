from math import pi, cos, sin

import numpy as np
from matplotlib import pyplot as plt

from vortex import Range
from vortex.scan import RasterScan, RasterScanConfig
from vortex_tools.scan import plot_annotated_waveforms_space

fig, axs = plt.subplots(2, 2, sharex=True, sharey=True, constrained_layout=True, subplot_kw=dict(adjustable='box', aspect='equal'))
cfgs = []
names = []

cfg = RasterScanConfig()
cfg.segment_extent = Range.symmetric(1)
cfg.segments_per_volume = 10
cfg.samples_per_segment = 50
for limit in cfg.limits:
    limit.acceleration *= 5
cfg.loop = True

# change offset
names.append('Offset')
cfgs.append(cfg.copy())
cfgs[-1].offset = (1, 0)

# change extent
names.append('Extent')
cfgs.append(cfg.copy())
cfgs[-1].volume_extent = Range(2, -2)
cfgs[-1].segment_extent = Range(0, 1)

# change shape
names.append('Shape')
cfgs.append(cfg.copy())
cfgs[-1].segments_per_volume = 5

# change rotation
names.append('Angle')
cfgs.append(cfg.copy())
cfgs[-1].angle = pi / 6

for (name, cfg, ax) in zip(names, cfgs, axs.flat):
    scan = RasterScan()
    scan.initialize(cfg)
    plot_annotated_waveforms_space(scan.scan_buffer(), scan.scan_markers(), inactive_marker=None, scan_line='w-', axes=ax)
    ax.set_title(name)

    if not np.allclose(cfg.offset, (0, 0)):
        ax.plot([0, cfg.offset[0]], [0, cfg.offset[1]], 'ro-', zorder=20)
    if cfg.angle != 0:
        ax.plot([1, 0, cos(cfg.angle)], [0, 0, sin(cfg.angle)], 'ro-', zorder=20)
plt.show()