import matplotlib
matplotlib.use('Qt5Agg')
from PyQt5.QtGui import QPaintEvent

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy
import cupy

class TraceWidget(FigureCanvas):

    def __init__(self, endpoint, parent=None, width=5, height=4, dpi=100):
        self._endpoint = endpoint
        fig = Figure(figsize=(width, height), dpi=dpi)
        self._axes = fig.add_subplot(111)
        self._line2d = None
        self._xdata = None
        self._invalidated = False
        self._shape = None
        self._bidx = 0
        super().__init__(fig)

    def paintEvent(self, e: QPaintEvent) -> None:
        if self._invalidated:
            self._invalidated = False
            mustCallPlot = True
            if not self._shape:
                self._shape = self._endpoint.tensor.shape
            elif self._endpoint.tensor.shape:
                if self._shape == self._endpoint.tensor.shape:
                    mustCallPlot = False
                else:
                    self._shape = self._endpoint.tensor.shape

            # Now figure out how to deal with the volume we have. 
            # If volume as a single bscan, then average along axis=1, 
            # averaging all values at a single depth across the whole bscan.
            # When there are multiple bscans, use _bidx as the index 
            # of the bscan of interest. In that case, the slicing changes 
            # the axis along which we sum/mean/etc.

            if self._endpoint.tensor.shape:
                with self._endpoint.tensor as volume:
                    if self._endpoint.tensor.shape[0]==1:
                        if isinstance(volume, cupy.ndarray):
                            with self._endpoint.stream:
                                ytmp = volume.mean(axis=1).get()
                            self._endpoint.stream.synchronize()
                        else:
                            ytmp = volume.mean(axis=1)
                    else:
                        if self._bidx < 0 or self._bidx > self._endpoint.tensor.shape[1]:
                            self._bidx = 0
                        # work along axis 0 here because of slicing
                        if isinstance(volume, cupy.ndarray):
                            with self._endpoint.stream:
                                ytmp = volume[self._bidx,:,:].mean(axis=0).get()
                            self._endpoint.stream.synchronize()
                        else:
                            ytmp = volume[self._bidx,:,:].mean(axis=0)
                    ydata = ytmp.flatten()
                    if mustCallPlot:
                        if self._line2d:
                            self._axes.clear()
                            self._line2d = None
                        xdata = list(range(1,len(ydata)+1))
                        line2ds = self._axes.plot(xdata, ydata)
                        self._line2d = line2ds[0]
                    else:
                        self._line2d.set_ydata(ydata)
                    self.draw()
        super().paintEvent(e)

        # if self._debug:
        #     painter = QPainter(self)
        #     self._draw_stats(painter)


    def update_trace(self):
        # Set _invalidated to true and call update(). The update() call will move the actual update
        # to the gui thread, not the daq thread.
        self._invalidated = True
        self.update()

    def clear(self):
        self._axes.clear()