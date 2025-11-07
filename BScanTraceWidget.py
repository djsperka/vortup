import matplotlib
matplotlib.use('Qt5Agg')
from PyQt5.QtGui import QPaintEvent

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import numpy
import cupy
from typing import Iterable, List

# Inheriting from FigureCanvasQTAgg. 
# FigureCanvasQTAgg is a widget. Call update() to invalidate and trigger a paintEvent.

class BScanTraceWidget(FigureCanvasQTAgg):

    def __init__(self, endpoint, parent=None, width=5, height=4, dpi=100, title=None):
        self._endpoint = endpoint
        fig = Figure(figsize=(width, height), dpi=dpi)
        self._axes = fig.add_subplot(111)
        if title:
            self._axes.set_title(title)
        self._line2d = None
        self._xdata = None
        self._ydata = None
        self._invalidated = False
        self._shape = None
        self._bidx = 0
        super().__init__(fig)

    def paintEvent(self, e: QPaintEvent) -> None:
        if not self._invalidated:
            return
        
        with self._endpoint.tensor as volume:
            if isinstance(volume, cupy.ndarray):
                # asynchronous on GPU
                with self._endpoint.stream:
                    self._ydata = volume[self._bidx].mean(axis=0).get()
            else:
                self._ydata = volume[self._bidx].mean(axis=0)

        if self._xdata is None:
            self._xdata = list(range(1,len(self._ydata)+1))

        self._invalidated = False
        if self._line2d is None:
            line2ds = self._axes.plot(self._xdata, self._ydata)
            self._line2d = line2ds[0]
        else:
            self._line2d.set_ydata(self._ydata)
        # self._axes.relim()
        # self._axes.autoscale_view()
        self.draw()
        super().paintEvent(e)


    def update_trace(self, bscan_idxs: Iterable[int]):
        # Set _invalidated to true and call update(). The update() call will move the actual update
        # to the gui thread, not the daq thread.

        self._bidx = bscan_idxs[0]
        self._invalidated = True
        self.update()

    def clear(self):
        self._axes.clear()