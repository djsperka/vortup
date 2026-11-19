import logging
from collections.abc import Iterable
from typing import Literal

import cupy
import numpy
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from qtpy.QtCore import Qt
from qtpy.QtGui import QKeyEvent, QPaintEvent

_logger = logging.getLogger(__name__)

# Inheriting from FigureCanvasQTAgg.
# FigureCanvasQTAgg is a widget. Call update() to invalidate and trigger a paintEvent.


class TraceWidget(FigureCanvas):
    """Line plot of one trace taken from the current bscan of an endpoint.

    The trace is computed from a range of ascans of the most recent bscan:

    - ``mode="mean"``: the mean of those ascans.
    - ``mode="deviation"``: the middle ascan of the range minus the mean of the range.

    Then ``samples`` selects which samples to show, and the result is multiplied by ``factor``.

    ``yscale`` chooses the y axis: ``"linear"`` is matplotlib's ``plot``, ``"log"`` is ``semilogy``.
    (``semilogy`` is ``plot`` after ``set_yscale("log")``, so the axes scale is set once and the
    line is always drawn with ``plot``.)

    Works with device (cupy) and host (numpy) endpoints. Press Y on the plot to fit the y limits to
    the data seen over one full volume.
    """

    def __init__(
        self,
        endpoint,
        parent=None,
        width=5,
        height=4,
        dpi=100,
        title: str | None = None,
        yscale: Literal["linear", "log"] = "linear",
        mode: Literal["deviation", "mean"] = "deviation",
        ascans: slice = slice(100, 111),
        samples: slice = slice(None),
        factor: float = 1.0,
        xlabel: str | None = None,
        ylabel: str | None = None,
        color=None,
        grid: bool = False,
    ):
        if yscale not in ("linear", "log"):
            raise ValueError(f"yscale must be 'linear' or 'log', not {yscale!r}")
        if mode not in ("deviation", "mean"):
            raise ValueError(f"mode must be 'deviation' or 'mean', not {mode!r}")

        self._endpoint = endpoint
        self._title = title
        self._yscale = yscale
        self._mode = mode
        self._ascans = ascans
        self._samples = samples
        self._factor = factor
        self._xlabel = xlabel
        self._ylabel = ylabel
        self._color = color
        self._grid = grid

        fig = Figure(figsize=(width, height), dpi=dpi)
        self._axes = fig.add_subplot(111)
        self._setup_axes()
        fig.tight_layout()

        self._line2d = None
        self._xdata = None
        self._ydata = None
        self._invalidated = False
        self._bidx = 0
        self._update_ylim_start_idx = -1
        self._update_ylim_last_idx = -1
        self._update_ylim_lap = False
        self._update_ylim = False
        self._update_ylim_ready = False
        self._ylim_temp = [999999, -999999]

        # call flush() to force a re-draw of the line (including re-doing range)
        self._is_flushed = False

        super().__init__(fig)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def _setup_axes(self) -> None:
        """Title, labels, y scale and grid. Called at creation and after the axes are cleared."""
        if self._title:
            self._axes.set_title(self._title)
        if self._xlabel:
            self._axes.set_xlabel(self._xlabel)
        if self._ylabel:
            self._axes.set_ylabel(self._ylabel)
        self._axes.set_yscale(self._yscale)
        if self._grid:
            self._axes.grid(True, which="both", color="0.5")

    def set_ylim(self, lim):
        if self._yscale == "log":
            # Round out to whole decades. Log axes can't show non-positive limits; ignore those.
            if lim[0] > 0 and lim[1] > 0:
                low_power = numpy.floor(numpy.log10(lim[0]))
                hi_power = numpy.ceil(numpy.log10(lim[1]))
                self._axes.set_ylim(10**low_power, 10**hi_power)
        else:
            self._axes.set_ylim(lim[0], lim[1])

    def flush(self):
        if self._axes is not None:
            self._is_flushed = True
            self._axes.clear()
            self._line2d = None

    def _compute_trace(self, volume) -> numpy.ndarray:
        # Ascan endpoints are device endpoints (cupy); spectra endpoints are host endpoints (numpy).
        # Bring the slice to the host if needed; everything after that is numpy.
        ztmp = volume[self._bidx, self._ascans, :]
        if isinstance(ztmp, cupy.ndarray):
            with self._endpoint.stream:
                ztmp = ztmp.get()
        zavg = ztmp.mean(axis=0)
        if self._mode == "deviation":
            # middle ascan of the range minus the mean of the range
            trace = ztmp[len(ztmp) // 2] - zavg
        else:
            trace = zavg
        return trace[self._samples] * self._factor

    def get_xy_data(self) -> tuple[bool, bool]:
        have_data = False
        must_plot = False
        if self._bidx >= 0:
            with self._endpoint.tensor as volume:
                self._ydata = self._compute_trace(volume)

                if self._update_ylim and not self._update_ylim_ready:
                    # This is true on the first time only.
                    # 'start_idx' is the bscan index right now. We will watch the indices,
                    # and look for when the _new_ incoming index is LESS THAN the last one --
                    # this is when the bscan finished a volume and started the next one.
                    # Once we see that, we wait until the index is GREATER THAN the first one --
                    # that means we've cycled through an entire volume.

                    if self._update_ylim_start_idx < 0:
                        self._update_ylim_start_idx = self._bidx
                        self._update_ylim_last_idx = self._bidx
                        self._update_ylim_lap = False
                        self._ylim_temp = [999999, -999999]

                    # check how far we've cycled for ylim. Important that on first time through,
                    # the last_idx is set to current _bidx
                    if not self._update_ylim_lap:
                        if self._bidx < self._update_ylim_last_idx:
                            self._update_ylim_lap = True
                    else:
                        if self._bidx > self._update_ylim_last_idx:
                            self._update_ylim_ready = True

                    self._update_ylim_last_idx = self._bidx
                    ylow = numpy.min(self._ydata)
                    yhi = numpy.max(self._ydata)
                    if ylow < self._ylim_temp[0]:
                        self._ylim_temp[0] = ylow
                    if yhi > self._ylim_temp[1]:
                        self._ylim_temp[1] = yhi
                    _logger.debug(
                        "ylim update first %d last %d, lim (%f,%f)",
                        self._update_ylim_start_idx,
                        self._update_ylim_last_idx,
                        self._ylim_temp[0],
                        self._ylim_temp[1],
                    )
            have_data = True

            # check for x data
            if self._xdata is None or len(self._ydata) != len(self._xdata):
                self._xdata = list(range(1, len(self._ydata) + 1))
                must_plot = True

            # flushed?
            if self._is_flushed:
                must_plot = True
                self._is_flushed = False

        return (have_data, must_plot)

    def paintEvent(self, e: QPaintEvent) -> None:
        if not self._invalidated:
            return

        (have_data, must_plot) = self.get_xy_data()
        if not have_data:
            return

        if must_plot or self._line2d is None:
            # first draw, or the axes were cleared by flush(): restore labels/scale/grid too
            self._setup_axes()
            line2ds = self._axes.plot(self._xdata, self._ydata, color=self._color)
            self._line2d = line2ds[0]
        else:
            self._line2d.set_ydata(self._ydata)

        if self._update_ylim_ready:
            self._update_ylim = False
            self._update_ylim_ready = False
            self._update_ylim_start_idx = -1
            self.set_ylim(self._ylim_temp)

        self._invalidated = False

        self.draw()
        super().paintEvent(e)

    def update_trace(self, bscan_idxs: Iterable[int] = []):
        # Set _invalidated to true and call update(). The update() call will move the actual update
        # to the gui thread, not the daq thread.

        if len(bscan_idxs) > 0:
            self._bidx = bscan_idxs[0]
            self._invalidated = True
            self.update()

    def clear(self):
        self._axes.clear()

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if e.key() == Qt.Key.Key_Y:
            if not self._update_ylim:
                self._update_ylim = True
