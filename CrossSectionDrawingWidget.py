from vortex_tools.ui.display import CrossSectionImageWidget
from qtpy.QtWidgets import QMainWindow, QApplication
from qtpy.QtGui import QCursor, QMouseEvent, QEnterEvent, QKeyEvent, QPainter, QTransform, QPaintEvent, QPen, QColor
from qtpy.QtCore import QEvent, Qt as qt, QPoint, QPointF, Signal
import sys
import skimage as ski
from typing import Iterable, List, Set, Optional
from math import floor


from enum import Enum

class PlotCmdStates(Enum):
    NOTHING = 1
    PLACING_FIRST_SLICE = 2
    PLACING_SECOND_SLICE = 3


class CrossSectionDrawingWidget(CrossSectionImageWidget):

    __new_slice_signal = Signal(float, float, name='new_slice')


    def __init__(self, *args, **kwargs):

        # clobber args 
        kwargs['probe'] = True
        kwargs['crosshairs'] = False
        kwargs['centerlines'] = False
        kwargs['statistics'] = False

        # now init superclass
        super().__init__(*args, **kwargs)

        self._cmdstate = PlotCmdStates.NOTHING
        self._slice_y = []
        self._has_slice = False
        self._maybe_slice_first_y = 0
        self._placing_slice_color = QColor(255, 0, 0)
        self._placed_slice_color = QColor(0, 255, 0)

        print("responsive? {0:s}", self._mouse_responsive)
        self.setMouseTracking(True)
        self.update(safe=True)
        print("responsive? {0:s}", self._mouse_responsive)


    def keyPressEvent(self, e: QKeyEvent) -> None:
        needsUpdate = False
        if e.key() == qt.Key.Key_S:
            if self._cmdstate == PlotCmdStates.NOTHING:
                self._cmdstate = PlotCmdStates.PLACING_FIRST_SLICE
                print("keyPress - cmd started")
            bUpdate = True

        if needsUpdate: self.update(True)

    def paintEvent(self, e: QPaintEvent) -> None:

        mouse: QPoint = QPoint(self.mapFromGlobal(QCursor.pos()))

        # draw image
        super().paintEvent(e)

        painter = QPainter()
        painter.begin(self)

        # slice lines? 
        if self._has_slice:
            # draw existing slice
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.setPen(QPen(self._placed_slice_color))
            painter.drawLine(QPointF(0, self._slice_y[0]), QPointF(self.width(), self._slice_y[0]))
            painter.drawLine(QPointF(0, self._slice_y[1]), QPointF(self.width(), self._slice_y[1]))

        if self._cmdstate == PlotCmdStates.PLACING_FIRST_SLICE:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.setPen(QPen(self._placing_slice_color))
            painter.drawLine(QPointF(0, mouse.y()), QPointF(self.width(), mouse.y()))
        elif self._cmdstate == PlotCmdStates.PLACING_SECOND_SLICE:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.setPen(QPen(self._placing_slice_color))
            painter.drawLine(QPointF(0, mouse.y()), QPointF(self.width(), mouse.y()))
            painter.drawLine(QPointF(0, self._maybe_slice_first_y), QPointF(self.width(), self._maybe_slice_first_y))

        painter.end()


    def enterEvent(self, e: QEnterEvent) -> None:
        if self._cmdstate is not PlotCmdStates.NOTHING:
            self.update(safe=True)

        super().enterEvent(e)

    def leaveEvent(self, e: QEvent) -> None:
        if self._cmdstate is not PlotCmdStates.NOTHING:
            self.update(safe=True)

        super().leaveEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        self.update(safe=True)
        # if self._state == 0:
        #     pass
        # else:
        #     if e.type()==QEvent.Type.MouseButtonPress:
        #         print("QEvent.Type.MouseButtonPress")
        #     elif e.type()==QEvent.Type.MouseButtonRelease:
        #         print("QEvent.Type.MouseButtonRelease")
        #     elif e.type()==QEvent.Type.MouseButtonDblClick:
        #         print("QEvent.Type.MouseButtonDblClick")
        #     elif e.type()==QEvent.Type.MouseMove:
        #         window_mouse = self._map_window_to_data(e.localPos())
        #         #print("QEvent.Type.MouseMove local {0:f},{1:f} data {2:f},{3:f}".format(e.x(), e.y(), window_mouse[0], window_mouse[1]))
        #         self._ty = e.y()
        #         self.update()
        #     else:
        #         print("unknown event type")
        # #super().mouseMoveEvent(e)
        e.accept()

    def mousePressEvent(self, e: QMouseEvent) -> None:
        # right button is reset/quit command
        if e.buttons() & qt.MouseButton.RightButton:
            print("mousePressEvent = right button")
            self._cmdstate = PlotCmdStates.NOTHING
        elif e.buttons() & qt.MouseButton.LeftButton:
            if self._cmdstate == PlotCmdStates.PLACING_FIRST_SLICE:
                print("mousePressEvent = placing first slice")
                self._cmdstate = PlotCmdStates.PLACING_SECOND_SLICE
                self._maybe_slice_first_y = e.position().y()
            elif self._cmdstate == PlotCmdStates.PLACING_SECOND_SLICE:
                # second point placed. Command done. Make sure min&max are right
                self._slice_y = [min(self._maybe_slice_first_y, e.position().y()), max(self._maybe_slice_first_y, e.position().y())]
                print("mousePressEvent = placing second slice at {0:f}-{1:f}".format(self._slice_y[0], self._slice_y[1]))
                (row0, _) = self._map_window_to_data(QPointF(0, self._slice_y[0]))
                (row1, _) = self._map_window_to_data(QPointF(0, self._slice_y[1]))
                self._has_slice = True
                self._cmdstate = PlotCmdStates.NOTHING
                self.__new_slice_signal.emit(row0, row1)
        e.accept()

        #super().mousePressEvent(e)

    # def mouseReleaseEvent(self, e: QMouseEvent) -> None:
    #     if self._state == 1:
    #         self._state = 0
    #         # if e.buttons() & qt.MouseButton.LeftButton:
    #         #     print("mouseReleaseEvent = left")
    #         # elif e.buttons() & qt.MouseButton.RightButton:
    #         #     print("mouseReleaseEvent = right")
    #         # else:
    #         #     print("mouseReleaseEvent, unknown button")

    def _make_draw_transform(self, shape: Optional[Iterable[int]]=None) -> QTransform:
        if shape is None:
            shape = self.data.shape
        (image_height, image_width) = shape

        xform = QTransform()

        # start by translating half the width/height of widget
        xform.translate(self.width() / 2, self.height() / 2)

        # scale
        s = min([self.width()/image_width, self.height()/image_height])
        #xform.scale(self.width()/image_width, self.height()/image_height)
        xform.scale(s,s)
        return xform
    #     # return composed with user transform
    #     return xform * self._transform

    def _make_window_transform(self) -> QTransform:
        xform = self._make_draw_transform()
        xform.translate(-self.data.shape[1] / 2, -self.data.shape[0] / 2)
        xform = xform.inverted()[0]
        return xform

    def _map_window_to_data(self, window_point: QPointF) -> QPointF:
        image_point = self._make_window_transform().map(window_point)
        row = int(floor(image_point.y()))
        col = int(floor(image_point.x()))
        return (row, col)



class Window(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("QMainWindow Example")
        self.resize(800, 600)
   
        # Create a central widget
        self.plot = TestPlotWidget(self)
        self.setCentralWidget(self.plot)

        self.plot.new_slice.connect(self.slice)

    def slice(self, y0, y1):
        print("Got slice signal {0:f}-{1:f}".format(y0, y1))

if __name__ == "__main__":
    App = QApplication(sys.argv)
    window = Window()
    window.show()

    # get image
    image = ski.data.camera()
    window.plot.data = image

    sys.exit(App.exec())

