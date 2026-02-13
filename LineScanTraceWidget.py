from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from qtpy.QtGui import QKeyEvent, QPaintEvent
from qtpy.QtCore import Qt

import numpy as np
import cupy as cp
from typing import Iterable, List
from qtpy.QtGui import QPaintEvent
from typing import Tuple

# Inheriting from FigureCanvasQTAgg. 
# FigureCanvasQTAgg is a widget. Call update() to invalidate and trigger a paintEvent.

class LineScanTraceWidget(FigureCanvas):

    def __init__(self, endpoint, parent=None, width=5, height=4, dpi=100, title=None, cuda=True):
        self._endpoint = endpoint
        self._cuda = cuda
        fig = Figure(figsize=(width, height), dpi=dpi)
        self._axes = fig.add_subplot(111)
        self._axes.set_ylim(0, 100)
        #self._axes.get_yaxis().set_visible(False)
        if title:
            self._axes.set_title(title)
        fig.tight_layout()
        self._line2d_a = None
        self._line2d_b = None
        self._ydata_a = None
        self._ydata_b = None
        self._color_a = (1,0,0)
        self._color_b = (0,0,1)
        self._update_ylim = False
        self._mip = None
        self._invalidated = False
        self._bscan_index_list = []     # when _invalidated is true, this is list of bscans to fetch
        self._not_ylim_yet = True
        super().__init__(fig)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def set_ylim(self, lim):
        self._axes.set_ylim(lim[0], lim[1])

    def flush(self):
        if self._axes is not None:
            self._is_flushed = True
            self._axes.clear()
            self._line2d = None


    def get_data(self) -> bool:
        retval = False
        if self._invalidated:
            # make a copy of list
            temp_list = self._bscan_index_list
            retval = True
            with self._endpoint.tensor as volume:
                if self._mip is None:
                    self._mip = np.full((volume.shape[0], volume.shape[1]), np.nan)
                if isinstance(volume, cp.ndarray):
                    self._mip[temp_list] = cp.max(volume[temp_list], axis=2).get()
                else:
                    self._mip[temp_list] = cp.max(volume[temp_list], axis=2)

                # compute averages
                self._ydata_a = np.nanmean(self._mip[::2], axis=0)
                self._ydata_b = np.nanmean(self._mip[1::2], axis=0)
        return retval
    
    def paintEvent(self, e: QPaintEvent) -> None:
        if not self._invalidated:
            return

        if self.get_data():

            if self._update_ylim:
                maxa = np.max(self._ydata_a)
                mina = np.min(self._ydata_a)
                self._axes.set_ylim(mina, maxa)
                self._update_ylim = False

            if self._line2d_a:
                self._line2d_a.set_ydata(self._ydata_a)
            else:
                l2ds = self._axes.plot(self._ydata_a, 'r')
                self._line2d_a = l2ds[0]
            if self._line2d_b:
                self._line2d_b.set_ydata(self._ydata_b)
            else:
                l2ds = self._axes.plot(self._ydata_b, 'b')
                self._line2d_b = l2ds[0]
        self._bscan_index_list.clear()
        self._invalidated = False

        self.draw()
        super().paintEvent(e)


    def update_trace(self, bscan_idxs: Iterable[int] = []):
        # Set _invalidated to true, save the bscan indices, and call update(). The update() call will move the actual update
        # to the gui thread, not the daq thread.

        if len(bscan_idxs) > 0:
            self._bscan_index_list = [*self._bscan_index_list, *bscan_idxs]
            self._invalidated = True
            self.update()

    def clear(self):
        self._axes.clear()

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if e.key() == Qt.Key.Key_Y:
            if not self._update_ylim:
                self._update_ylim = True

