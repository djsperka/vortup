import logging
import warnings
from collections.abc import Iterable, Sequence
from typing import Literal, Protocol

import cupy
import numpy
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from qtpy.QtCore import Qt
from qtpy.QtGui import QKeyEvent, QPaintEvent

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------------------------
# Trace sources: turn endpoint data into the line(s) a TraceWidget draws.
# ---------------------------------------------------------------------------------------------


class TraceSource(Protocol):
    """Computes the lines for a TraceWidget.

    Called on the GUI thread inside ``with endpoint.tensor as volume``. ``volume`` is a cupy array
    for device endpoints and a numpy array for host endpoints. Do any GPU work under
    ``with endpoint.stream:`` and return host (numpy) arrays, one per line, all the same length.

    - ``bidx``: first bscan index of the most recent segment callback.
    - ``new_bidxs``: every bscan index received since the last call (may contain repeats).
    """

    def __call__(self, endpoint, volume, bidx: int, new_bidxs: list[int]) -> list[numpy.ndarray]: ...


class AscanRangeTrace:
    """One line along depth, from a range of ascans of the current bscan.

    - ``mode="mean"``: the mean of those ascans.
    - ``mode="deviation"``: the middle ascan of the range minus the mean of the range.

    Then ``samples`` selects which samples to show, and the result is multiplied by ``factor``.
    """

    def __init__(
        self,
        mode: Literal["deviation", "mean"] = "deviation",
        ascans: slice = slice(100, 111),
        samples: slice = slice(None),
        factor: float = 1.0,
    ):
        if mode not in ("deviation", "mean"):
            raise ValueError(f"mode must be 'deviation' or 'mean', not {mode!r}")
        self.mode = mode
        self.ascans = ascans
        self.samples = samples
        self.factor = factor

    def __call__(self, endpoint, volume, bidx: int, new_bidxs: list[int]) -> list[numpy.ndarray]:
        # Ascan endpoints are device endpoints (cupy); spectra endpoints are host endpoints (numpy).
        # Bring the slice to the host if needed; everything after that is numpy.
        ztmp = volume[bidx, self.ascans, :]
        if isinstance(ztmp, cupy.ndarray):
            with endpoint.stream:
                ztmp = ztmp.get()
        zavg = ztmp.mean(axis=0)
        if self.mode == "deviation":
            trace = ztmp[len(ztmp) // 2] - zavg
        else:
            trace = zavg
        return [trace[self.samples] * self.factor]


class BidirectionalProfileTrace:
    """Two lines along the scan line, for tuning galvo delay on a bidirectional line scan.

    Each bscan is reduced to its max over depth (one value per ascan). The reduced bscans are
    kept for the whole volume, and the lines are the means of the even bscans and of the odd
    bscans, i.e. the two sweep directions. Every bscan index received is used, not only the latest.
    """

    def __init__(self):
        self._mip: numpy.ndarray | None = None  # bscans x ascans, NaN until a bscan arrives

    def __call__(self, endpoint, volume, bidx: int, new_bidxs: list[int]) -> list[numpy.ndarray]:
        if self._mip is None or self._mip.shape != tuple(volume.shape[:2]):
            self._mip = numpy.full(volume.shape[:2], numpy.nan)
        if new_bidxs:
            if isinstance(volume, cupy.ndarray):
                # reduce on the GPU, transfer only bscans x ascans
                with endpoint.stream:
                    self._mip[new_bidxs] = volume[new_bidxs].max(axis=2).get()
            else:
                self._mip[new_bidxs] = volume[new_bidxs].max(axis=2)
        with warnings.catch_warnings():
            # before any odd (or even) bscan has arrived its line is all NaN; that's expected
            warnings.simplefilter("ignore", RuntimeWarning)
            return [numpy.nanmean(self._mip[0::2], axis=0), numpy.nanmean(self._mip[1::2], axis=0)]


# ---------------------------------------------------------------------------------------------
# The widget
# ---------------------------------------------------------------------------------------------

# Inheriting from FigureCanvasQTAgg.
# FigureCanvasQTAgg is a widget. Call update() to invalidate and trigger a paintEvent.


class TraceWidget(FigureCanvas):
    """Line plot of one or more traces computed from an endpoint.

    What is plotted comes from ``trace``, a TraceSource (see ``AscanRangeTrace`` and
    ``BidirectionalProfileTrace``). If ``trace`` isn't given, an ``AscanRangeTrace`` is built from
    ``mode``, ``ascans``, ``samples`` and ``factor``.

    ``yscale`` chooses the starting y axis: ``"linear"`` is matplotlib's ``plot``, ``"log"`` is
    ``semilogy``. (``semilogy`` is ``plot`` after ``set_yscale("log")``, so the axes scale is set
    separately and the lines are always drawn with ``plot``.)

    ``color`` sets the colour of a single line; ``colors`` sets one per line. ``labels`` adds a
    legend. ``ylim`` sets the starting y limits.

    Works with device (cupy) and host (numpy) endpoints. Keys (click the plot first):

    - Y: fit the y limits to the data seen over one full volume.
    - L: toggle the y axis between linear and log. Each scale keeps its own limits.
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
        trace: TraceSource | None = None,
        colors: Sequence | None = None,
        labels: Sequence[str] | None = None,
        ylim: Sequence[float] | None = None,
    ):
        if yscale not in ("linear", "log"):
            raise ValueError(f"yscale must be 'linear' or 'log', not {yscale!r}")

        self._endpoint = endpoint
        self._trace = trace if trace is not None else AscanRangeTrace(mode, ascans, samples, factor)
        self._title = title
        self._yscale = yscale  # current scale; toggled with the L key
        self._initial_yscale = yscale  # constructor's scale; saved settings are for this one
        self._saved_ylim: dict[str, tuple[float, float]] = {}  # last limits used in each scale
        self._xlabel = xlabel
        self._ylabel = ylabel
        self._colors = list(colors) if colors is not None else [color]
        self._labels = list(labels) if labels is not None else None
        self._grid = grid

        fig = Figure(figsize=(width, height), dpi=dpi)
        self._axes = fig.add_subplot(111)
        self._setup_axes()
        if ylim is not None:
            self.set_ylim(ylim)
        fig.tight_layout()

        self._line2ds: list = []
        self._xdata = None
        self._ydata: list[numpy.ndarray] | None = None
        self._invalidated = False
        self._bidx = 0
        self._pending_bidxs: list[int] = []  # every bscan index since the last paint
        self._update_ylim_start_idx = -1
        self._update_ylim_last_idx = -1
        self._update_ylim_lap = False
        self._update_ylim = False
        self._update_ylim_ready = False
        self._ylim_temp = [999999, -999999]

        # call flush() to force a re-draw of the lines (including re-doing range)
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

    def _finite_ydata(self) -> numpy.ndarray:
        """All finite y values of all lines, as one flat array (empty if there are none)."""
        if not self._ydata:
            return numpy.empty(0)
        y = numpy.concatenate([numpy.asarray(d, dtype=float).ravel() for d in self._ydata])
        return y[numpy.isfinite(y)]

    def set_ylim(self, lim):
        if self._yscale == "log":
            # Round out to whole decades. Log axes can't show non-positive limits; ignore those.
            if lim[0] > 0 and lim[1] > 0:
                low_power = numpy.floor(numpy.log10(lim[0]))
                hi_power = numpy.ceil(numpy.log10(lim[1]))
                self._axes.set_ylim(10**low_power, 10**hi_power)
        else:
            self._axes.set_ylim(lim[0], lim[1])

    def get_ylim(self) -> tuple[float, float]:
        """Y limits for the constructor's scale (the one saved settings are applied to).

        If the plot is toggled to the other scale, returns the limits it last had in the
        constructor's scale, or the current limits if it was never drawn in that scale.
        """
        if self._yscale != self._initial_yscale and self._initial_yscale in self._saved_ylim:
            return self._saved_ylim[self._initial_yscale]
        return tuple(self._axes.get_ylim())

    def toggle_yscale(self) -> None:
        """Switch the y axis between linear and log, keeping each scale's limits."""
        self._saved_ylim[self._yscale] = tuple(self._axes.get_ylim())
        new_scale = "log" if self._yscale == "linear" else "linear"

        # Limits for the new scale: the ones it had last time, otherwise fit to the current data.
        # Log axes can't show non-positive values, so a log fit starts at the smallest positive value.
        lim = self._saved_ylim.get(new_scale)
        if lim is None:
            y = self._finite_ydata()
            if new_scale == "log":
                y = y[y > 0]
            if y.size > 0 and y.min() < y.max():
                lim = (float(y.min()), float(y.max()))

        if lim is None and new_scale == "log":
            # No data to fit yet: derive positive limits from the current linear ones. A log axis
            # must never be left with non-positive limits, or matplotlib fails when drawing ticks.
            lo, hi = self._axes.get_ylim()
            if hi <= 0:
                lim = (0.1, 1.0)
            else:
                lim = (lo if lo > 0 else hi / 1000, hi)

        self._yscale = new_scale
        if lim is None:
            # to linear with no data: the current (positive) log limits are valid as they are
            self._axes.set_yscale(new_scale)
        elif new_scale == "log":
            # set the positive limits while still linear, so the log axis never sees bad limits;
            # then set_ylim rounds them out to decades
            self._axes.set_ylim(lim[0], lim[1])
            self._axes.set_yscale(new_scale)
            self.set_ylim(lim)
        else:
            # switch first: lim may be negative, which a log axis would reject
            self._axes.set_yscale(new_scale)
            self.set_ylim(lim)

        # paintEvent only redraws when invalidated
        self._invalidated = True
        self.update()

    def flush(self):
        if self._axes is not None:
            self._is_flushed = True
            self._axes.clear()
            self._line2ds = []

    def get_xy_data(self) -> tuple[bool, bool]:
        have_data = False
        must_plot = False
        if self._bidx >= 0:
            # take the pending indices; update_trace (vortex thread) starts a new list
            new_bidxs, self._pending_bidxs = self._pending_bidxs, []
            with self._endpoint.tensor as volume:
                self._ydata = self._trace(self._endpoint, volume, self._bidx, new_bidxs)

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
                    y = self._finite_ydata()
                    if y.size > 0:
                        self._ylim_temp[0] = min(self._ylim_temp[0], float(y.min()))
                        self._ylim_temp[1] = max(self._ylim_temp[1], float(y.max()))
                    _logger.debug(
                        "ylim update first %d last %d, lim (%f,%f)",
                        self._update_ylim_start_idx,
                        self._update_ylim_last_idx,
                        self._ylim_temp[0],
                        self._ylim_temp[1],
                    )
            have_data = True

            # check for x data (all lines have the same length)
            n = len(self._ydata[0])
            if self._xdata is None or n != len(self._xdata):
                self._xdata = list(range(1, n + 1))
                must_plot = True

            # number of lines changed?
            if len(self._ydata) != len(self._line2ds):
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

        if must_plot or not self._line2ds:
            # first draw, or the axes were cleared by flush(): restore labels/scale/grid too
            for line in self._line2ds:
                line.remove()
            self._setup_axes()
            self._line2ds = []
            for i, y in enumerate(self._ydata):
                color = self._colors[i] if i < len(self._colors) else None
                label = self._labels[i] if self._labels and i < len(self._labels) else None
                self._line2ds.extend(self._axes.plot(self._xdata, y, color=color, label=label))
            if self._labels:
                self._axes.legend()
        else:
            for line, y in zip(self._line2ds, self._ydata, strict=True):
                line.set_ydata(y)

        if self._update_ylim_ready:
            self._update_ylim = False
            self._update_ylim_ready = False
            self._update_ylim_start_idx = -1
            self.set_ylim(self._ylim_temp)

        self._invalidated = False

        self.draw()
        super().paintEvent(e)

    def update_trace(self, bscan_idxs: Iterable[int] = []):
        # Record the indices, set _invalidated and call update(). The update() call moves the actual
        # update to the gui thread, not the daq thread.

        if len(bscan_idxs) > 0:
            self._bidx = bscan_idxs[0]
            self._pending_bidxs.extend(bscan_idxs)
            self._invalidated = True
            self.update()

    def clear(self):
        self._axes.clear()

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if e.key() == Qt.Key.Key_Y:
            if not self._update_ylim:
                self._update_ylim = True
        elif e.key() == Qt.Key.Key_L:
            self.toggle_yscale()
