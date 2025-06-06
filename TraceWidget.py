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
        super().__init__(fig)

    def paintEvent(self, e: QPaintEvent) -> None:
        if self._invalidated:
            self._invalidated = False
            if self._endpoint.tensor.shape:
                with self._endpoint.tensor as volume:
                    if isinstance(volume, cupy.ndarray):
                        with self._endpoint.stream:
                            ytmp = volume.mean(axis=1).get()
                        self._endpoint.stream.synchronize()
                    else:
                        ytmp = volume.mean(axis=1)
                ydata = ytmp.flatten()
                if self._line2d:
                    self._line2d.set_ydata(ydata)
                else:
                    xdata = list(range(1,len(ydata)+1))
                    line2ds = self._axes.plot(xdata, ydata)
                    self._line2d = line2ds[0]
                self.draw()
        super().paintEvent(e)

        # if self._debug:
        #     painter = QPainter(self)
        #     self._draw_stats(painter)


    def update_trace(self):
        self._invalidated = True
        self.update()

