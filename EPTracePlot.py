from plotpy.plot import BasePlot, BasePlotOptions

from guidata.configtools import get_icon
from guidata.qthelpers import qt_app_context, win32_fix_title_bar_background
from qtpy import QtWidgets as QW

from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QPaintEvent
from typing import Iterable


class EPTracePlot(BasePlot):

    __safe_update = Signal(bool, name='request_update')

    def __init__(self, *args, **kwargs):
        self._endpoint = kwargs.pop("endpoint", None)
        self._bidx = []
        self._invalidated = False
        super().__init__(*args, **kwargs)
        self.__safe_update.connect(self.update)
        self.update(safe=True)


    def update(self, safe=False) -> None:
        '''
        Call `update()` through the signal/slot mechanism by default.
        This simplifies calling update from background threads.
        '''
        if safe:
            super().update()
        else:
            self.__safe_update.emit(True)

    def update_trace(self, bscan_idxs: Iterable[int] = []):
        # Set _invalidated to true and call update(). The update() call will move the actual update
        # to the gui thread, not the daq thread.

        if len(bscan_idxs) > 0:
            self._bidx = bscan_idxs[0]
            self._invalidated = True
            self.update()

    def paintEvent(self, e: QPaintEvent) -> None:
        if not self._invalidated:
            return

        print("paintEvent")
        self._invalidated = False

        super().paintEvent(e)
