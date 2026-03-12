from vortex_tools.ui.display import BackendImageWidget
from qtpy.QtWidgets import QMainWindow, QApplication
from qtpy.QtGui import QCursor, QMouseEvent, QEnterEvent, QWheelEvent, QKeyEvent, QPainter, QTransform, QImage, QPixmap, QPaintEvent, QPen, QColor
from qtpy.QtCore import QEvent, Qt as qt, QPoint, QPointF
import sys
import skimage as ski
from typing import Iterable, List, Set, Optional
from math import floor, ceil


class TestPlotWidget(BackendImageWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._state = 0 # 0 unpressed, 1 pressed
        self._ty = -1

    def paintEvent(self, e: QPaintEvent) -> None:

        # background
        super().paintEvent(e)

        #draw line
        if self._state == 1 and self._ty > -1:
            painter = QPainter()
            painter.begin(self)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Exclusion)
            pen = QPen(QColor(255, 0, 0))
            painter.setPen(pen)
            print("paintEvent", self._ty)
            painter.drawLine(QPointF(0, self._ty), QPointF(self.width(), self._ty))
            painter.end()


        # # foreground
        # if self.pixmap:
        #     self._draw_image(painter)

        # if self._centerlines:
        #     self._draw_inverted_lines(painter, QPointF(self.width() / 2, self.height() / 2), Qt.PenStyle.DashLine)

        # if self._crosshairs and self.rect().contains(mouse) and self.pixmap:
        #     self._draw_inverted_lines(painter, QPointF(mouse))

        # self._draw_extra_lines(painter)

        # if self.pixmap and self._probe:
        #     self._draw_probe(painter, QPointF(mouse))

        # if self._debug or self._statistics:
        #     self._draw_stats(painter)

    



    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if self._state == 0:
            pass
        else:
            if e.type()==QEvent.Type.MouseButtonPress:
                print("QEvent.Type.MouseButtonPress")
            elif e.type()==QEvent.Type.MouseButtonRelease:
                print("QEvent.Type.MouseButtonRelease")
            elif e.type()==QEvent.Type.MouseButtonDblClick:
                print("QEvent.Type.MouseButtonDblClick")
            elif e.type()==QEvent.Type.MouseMove:
                window_mouse = self._map_window_to_data(e.localPos())
                #print("QEvent.Type.MouseMove local {0:f},{1:f} data {2:f},{3:f}".format(e.x(), e.y(), window_mouse[0], window_mouse[1]))
                self._ty = e.y()
                self.update()
            else:
                print("unknown event type")
        #super().mouseMoveEvent(e)
        e.accept()

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if self._state == 0:
            self._state = 1
            mouse = e.position()
            window_mouse = self._map_window_to_data(mouse)
            print("self size: {0:d}x{1:d} pos: {2:f}x{3:f} window: {4:f},{5:f}".format(self.width(), self.height(), mouse.x(), mouse.y(), window_mouse[0], window_mouse[1]))
            if e.buttons() & qt.MouseButton.LeftButton:
                print("mousePressEvent = left")
            if e.buttons() & qt.MouseButton.RightButton:
                print("mousePressEvent = right")
        elif self._state == 1:
            self._state = 0
        e.accept()

        #super().mousePressEvent(e)

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        if self._state == 1:
            self._state = 0
            # if e.buttons() & qt.MouseButton.LeftButton:
            #     print("mouseReleaseEvent = left")
            # elif e.buttons() & qt.MouseButton.RightButton:
            #     print("mouseReleaseEvent = right")
            # else:
            #     print("mouseReleaseEvent, unknown button")

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


if __name__ == "__main__":
    App = QApplication(sys.argv)
    window = Window()
    window.show()

    # get image
    image = ski.data.camera()
    window.plot.data = image

    sys.exit(App.exec())

