from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy
import cupy
from typing import Iterable, List
from qtpy.QtGui import QPaintEvent
from typing import Tuple

# Inheriting from FigureCanvasQTAgg. 
# FigureCanvasQTAgg is a widget. Call update() to invalidate and trigger a paintEvent.

class TraceWidget(FigureCanvas):

    def __init__(self, endpoint, parent=None, width=5, height=4, dpi=100, title=None):
        self._endpoint = endpoint
        fig = Figure(figsize=(width, height), dpi=dpi)
        self._axes = fig.add_subplot(111)
        self._axes.get_yaxis().set_visible(False)
        if title:
            self._axes.set_title(title)
        fig.tight_layout()
        self._line2d = None
        self._xdata = None
        self._ydata = None
        self._invalidated = False
        self._bidx = 0

        # call flush() to force a re-draw of the line (including re-doing range)
        self._is_flushed = False

        # Will check if tensor is a cupy or numpy array on first time 
        # accessing ydata. After that, assume the endpoint does not change.
        self._is_cuda_known = False
        self._is_cuda = False
        super().__init__(fig)

    def flush(self):
        if self._axes is not None:
            self._is_flushed = True
            self._axes.clear()
            self._line2d = None


    def get_xy_data(self) -> Tuple[bool, bool]:
        have_data = False
        must_plot = False
        if self._bidx >= 0:

            with self._endpoint.tensor as volume:

                if not self._is_cuda_known:
                    # Do this just one time - check data type
                    if isinstance(volume, cupy.ndarray):
                        self._is_cuda = True
                    else:
                        self._is_cuda = False
                    self._is_cuda_known = True

                if self._is_cuda:
                    with self._endpoint.stream:
                        self._ydata = volume[self._bidx].mean(axis=0).get()
                else:
                    self._ydata = volume[self._bidx].mean(axis=0)

            have_data = True

            # check for x data
            if self._xdata is None or len(self._ydata) != len(self._xdata):
                self._xdata = list(range(1,len(self._ydata)+1))
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
        
        if must_plot:
            line2ds = self._axes.plot(self._xdata, self._ydata)
            self._line2d = line2ds[0]
        else:
            self._line2d.set_ydata(self._ydata)
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