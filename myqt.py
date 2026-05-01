from typing import List, Tuple, Iterable, Optional, Callable
from enum import Enum, IntFlag
from math import floor, ceil
from pathlib import Path
from warnings import warn

import numpy as np

from qtpy.QtWidgets import QWidget, QFileDialog
from qtpy.QtGui import QCursor, QMouseEvent, QEnterEvent, QWheelEvent, QKeyEvent, QPainter, QTransform, QImage, QPixmap, QPaintEvent, QPen, QColor
from qtpy.QtCore import Qt, QEvent, QPoint, QPointF, QRectF, Signal

from vortex_tools.ui.backend.base import BaseImageWidget

__all__ = ['MyNumpyImageWidget']


class PlotCmdStates(Enum):
    NOTHING = 1
    PLACING_FIRST_SLICE = 2
    PLACING_SECOND_SLICE = 3
    DOING_TEST = 4




class MyNumpyImageWidget(BaseImageWidget, QWidget):
    class Scaling(Enum):
        Absolute = 0
        Relative = 1
        Percentile = 2

    class Sizing(Enum):
        Fixed = 0
        Fit = 1
        Stretch = 2

    class Flip(IntFlag):
        Horizontal = 2**0
        Vertical = 2**1

    __safe_update = Signal(bool, name='request_update')
    __new_slice_signal = Signal(float, float, name='new_slice')

    def __init__(self, *args, **kwargs):
        '''
        Efficiently display a Numpy array as a color-mapped image.

        Set the displayed array using the `data` property.
        The array may be edited in-place.
        Call `invalidate()` to request regeneration of the display image when editing the array in place.

        transform `QTransform`: `None`
            Transformation to apply to the displayed image.
            The origin is the center of the display.
            This transformation is applied after the image has been initially scaled.
        scaling `Scaling`: `Relative`
            Interpretation of range.
            `Absolute` indicates fixed values.
            `Relative` indicates values relative to the range of the input data as a ratio in [0, 1].
            `Percentile` indicates percentiles of the input data as a ratio in [0, 1].
        sizing `Iterable[Sizing]`: [`Fit`, `Fit`]
            Control sizing of image within widget in the horizontal and vertical directions, respectively.
            `Fixed` does not scale with the display.
            `Stretch` fills the direction with the image.
            `Fit` uses the largest length of that dimension while respecting the other settings.
        pan `Tuple[float, float]`: `(0, 0)`
            Offset in pixels of the image center from the center of the widget.
        angle `float`: `0`
            Angle in degrees of rotation about the image center.
        zoom `float`: `1`
            Scale factor of the image.
        flip `Flip`: 0
            Flags to control horizontal or vertical flipping of the image.
        cursor_width_hint `int`: `16`
            The assumed size of the cursor in pixels if it cannot be obtained programmatically.
        angle_key_step `float`: `30`
            Degrees to rotate per key press.
        angle_mouse_step `float`: `0.2`
            Degrees per pixel of mouse movement.
        zoom_key_step `float`: `0.1`
            Relative zoom factor per key press.
        zoom_mouse_step `float`: `0.001`
            Relative zoom factor per wheel step.
        range_step `int`: `1`
            Value to adjust range bounds per key press.
        '''

        self._transform = kwargs.pop('transform', None)
        if not self._transform:
            self._transform = QTransform()

        self._range_mode: MyNumpyImageWidget.Scaling = kwargs.pop('scaling', MyNumpyImageWidget.Scaling.Absolute)
        self._size_mode: Iterable[MyNumpyImageWidget.Sizing] = kwargs.pop('sizing', [MyNumpyImageWidget.Sizing.Fit, MyNumpyImageWidget.Sizing.Fit])

        self._statistics: bool = kwargs.pop('statistics', False)

        self._pan: Tuple[float, float] = kwargs.pop('pan', (0, 0))
        self._angle: float = kwargs.pop('angle', 0)
        self._zoom: float = kwargs.pop('zoom', 1)
        self._flip: int = kwargs.pop('flip', 0)

        self._cursor_width_hint: int = kwargs.pop('cursor_width_hint', 16)

        self._enable_keyboard: bool = kwargs.pop('enable_keyboard', True)

        self._angle_key_step: float = kwargs.pop('angle_key_step', 30)
        self._angle_mouse_step: float = kwargs.pop('angle_mouse_step', 0.2)
        self._zoom_key_step: float = kwargs.pop('zoom_key_step', 0.1)
        self._zoom_mouse_step: float = kwargs.pop('zoom_mouse_step', 0.001)

        self._range_step: int = kwargs.pop('range_step', 1)

        self._vmin = 0
        self._vmax = 0

        self.__pixmap: Optional[QPixmap] = None
        self.__pixmap_draw_rect: Optional[QRectF] = None

        super().__init__(*args, **kwargs)

        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        self.__safe_update.connect(self.update)
        self.update(safe=True)

        self._mouse_down_position: Optional[QPoint]=None
        self._mouse_down_pan: Optional[Tuple[float, float]]=None
        self._mouse_down_angle: Optional[float]=None

        self._cmdstate = PlotCmdStates.NOTHING
        self._slice_y = []
        self._has_slice = False
        self._maybe_slice_first_y = 0
        self._placing_slice_color = QColor(255, 0, 0)
        self._placed_slice_color = QColor(0, 255, 0)

        self.setMouseTracking(True)
        # self.update(safe=True)


    def paintEvent(self, e: QPaintEvent) -> None:

        mouse: QPoint = QPoint(self.mapFromGlobal(QCursor.pos()))

        painter = QPainter(self)

        # background
        super().paintEvent(e)

        # foreground
        if self.pixmap:
            self._draw_image(painter)

        self._draw_extra_lines(painter)

        if self._debug or self._statistics:
            self._draw_stats(painter)

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

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if self._enable_keyboard:
            shift = (e.modifiers() & Qt.KeyboardModifier.ShiftModifier) == Qt.KeyboardModifier.ShiftModifier
            sign = 1 if not shift else -1

            # display transform
            if e.key() == Qt.Key.Key_R:
                self._angle += sign * self._angle_key_step
                self.invalidate()
            elif e.key() == Qt.Key.Key_F:
                self._flip += sign
                self.invalidate()
            elif e.key() == Qt.Key.Key_Z:
                if shift:
                    factor = 1 - self._zoom_key_step
                else:
                    factor = 1 + self._zoom_key_step
                self._zoom *= factor
                self._pan = [self._pan[0] * factor, self._pan[1] * factor]
                self.invalidate()

            # display range
            elif e.key() == Qt.Key.Key_BracketLeft:
                self._range[0] -= self._range_step
                self.invalidate()
            elif e.key() == Qt.Key.Key_Minus:
                self._range[0] += self._range_step
                self.invalidate()
            elif e.key() == Qt.Key.Key_BracketRight:
                self._range[1] -= self._range_step
                self.invalidate()
            elif e.key() == Qt.Key.Key_Equal:
                self._range[1] += self._range_step
                self.invalidate()

            # export image
            elif e.key() == Qt.Key.Key_E:
                if self.pixmap:
                    (path, _) = QFileDialog.getSaveFileName(self, f'Export {self.windowTitle()}...', Path().as_posix(), "Images (*.png *.jpg *.gif *.bmp *.tiff *.webp)")
                    if path:
                        self.pixmap.save(path, quality=100)

            # display reset
            elif e.key() == Qt.Key.Key_Home:
                self._angle = 0
                self._flip = 0
                self._zoom = 1
                self._pan = [0, 0]
                self._cmdstate = PlotCmdStates.NOTHING
                self._has_slice = False

                self.invalidate()

            elif e.key() == Qt.Key.Key_S:
                if self._cmdstate == PlotCmdStates.NOTHING:
                    self._cmdstate = PlotCmdStates.PLACING_FIRST_SLICE
                    print("keyPress - cmd started")
            
            elif e.key() == Qt.Key.Key_T:
                if self._cmdstate == PlotCmdStates.NOTHING:
                    self._cmdstate = PlotCmdStates.DOING_TEST
                    print("keyPress - doing test")

            e.accept()

        super().keyPressEvent(e)
        self.update(safe=True)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        # right button is reset/quit command
        if e.buttons() & Qt.MouseButton.RightButton:
            print("mousePressEvent = right button")
            self._cmdstate = PlotCmdStates.NOTHING
        elif e.buttons() & Qt.MouseButton.LeftButton:
            if self._cmdstate == PlotCmdStates.PLACING_FIRST_SLICE:
                print("mousePressEvent = placing first slice")
                self._cmdstate = PlotCmdStates.PLACING_SECOND_SLICE
                self._maybe_slice_first_y = e.position().y()
            elif self._cmdstate == PlotCmdStates.PLACING_SECOND_SLICE:
                # second point placed. Command done. Make sure min&max are right
                self._slice_y = [min(self._maybe_slice_first_y, e.position().y()), max(self._maybe_slice_first_y, e.position().y())]
                print("mousePressEvent = placing second slice at {0:f}-{1:f}".format(self._slice_y[0], self._slice_y[1]))
                self._has_slice = True
                self._cmdstate = PlotCmdStates.NOTHING

                testx = 439
                (y0, x0) = self._map_window_to_data(QPointF(testx, self._slice_y[0]))
                (y1, x1) = self._map_window_to_data(QPointF(testx, self._slice_y[1]))
                self.__new_slice_signal.emit(y0, y1)

                print("mapped xy {0:f},{1:f} to data coordinates {2:f},{3:f}".format(testx, self._slice_y[0], x0, y0))
                print("mapped xy {0:f},{1:f} to data coordinates {2:f},{3:f}".format(testx, self._slice_y[1], x1, y1))

                xform = self._make_draw_transform()
                p = xform.map(QPointF(testx, self._slice_y[0]))
                print("widget size is {0:d}x{1:d}".format(self.width(), self.height()))
                print("mapping point {0:f},{1:f} to {2:f},{3:f}".format(testx, self._slice_y[0], p.x(), p.y()))

            elif self._cmdstate == PlotCmdStates.NOTHING:
                # If we already have a slice, check if we're clicking near it to move it
                if self._has_slice and abs(e.position().y() - self._slice_y[0]) < 10:
                    print("mousePressEvent = starting slice move")
                    self._editslice_initial_position = self._slice_y[0]
                    self._editslice_index = 0
            elif self._cmdstate == PlotCmdStates.DOING_TEST:
                print("mousePressEvent = doing test, printing data coords")
                (y, x) = self._map_window_to_data(e.position())
                print("mapped xy {0:f},{1:f} to data coordinates {2:f},{3:f}".format(e.position().x(), e.position().y(), x, y))

                (yw, xw) = self._map_data_to_window(QPointF(x, y))
                print("mapping data coords {0:f},{1:f} back to window coords {2:f},{3:f}".format(x, y, xw, yw))

        e.accept()





    # def mouseReleaseEvent(self, e: QMouseEvent) -> None:
    #     self._mouse_down_position = None
    #     self._mouse_down_pan = None
    #     self._mouse_down_angle = None

    #     e.accept()

    #     super().mouseReleaseEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if self._mouse_down_position:
            delta = e.position() - self._mouse_down_position

            if self._mouse_down_pan is not None:
                self._pan = [self._mouse_down_pan[0] + delta.x(), self._mouse_down_pan[1] + delta.y()]
                self.invalidate()
            if self._mouse_down_angle is not None:
                self._angle = self._mouse_down_angle + delta.y() * self._angle_mouse_step
                self.invalidate()

            e.accept()

        super().mouseMoveEvent(e)
        self.update(safe=True)

    def wheelEvent(self, e: QWheelEvent) -> None:
        delta = e.angleDelta().y()

        if delta >= 0:
            factor = (1 + self._zoom_mouse_step)**delta
        else:
            factor = (1 - self._zoom_mouse_step)**-delta
        self._zoom *= factor
        self._pan = [self._pan[0] * factor, self._pan[1] * factor]
        self.invalidate()

        e.accept()

        super().wheelEvent(e)
        self.update(safe=True)

    def invalidate(self) -> None:
        '''
        Clear the cached image.
        This is required for changes to the underlying data buffer to display.
        '''
        self.__pixmap = None
        self.__pixmap_draw_rect = None

    def update(self, safe=False) -> None:
        '''
        Call `update()` through the signal/slot mechanism by default.
        This simplifies calling update from background threads.
        '''
        if safe:
            #self.setMouseTracking(self._mouse_responsive)

            super().update()
        else:
            self.__safe_update.emit(True)

    @property
    def pixmap(self) -> QPixmap:
        '''QPixmap representation of drawn image'''
        if self.__pixmap is None:
            self._make_and_cache_image()

        # get from cache
        return self.__pixmap

    def _draw_image(self, painter: QPainter) -> None:
        painter.save()
        painter.setTransform(self._make_draw_transform())
        try:
            painter.drawPixmap(self.__pixmap_draw_rect, self.pixmap, QRectF(self.pixmap.rect()))
        except TypeError:
            warn(f'unable to draw pixmap due to strange TypeError')
        painter.restore()

    def _draw_inverted_lines(self, painter: QPainter, point: QPointF, style: Optional[Qt.PenStyle]=None) -> None:
        painter.save()
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Exclusion)
        pen = QPen(QColor(255, 255, 255))
        if style is not None:
            pen.setStyle(style)
        painter.setPen(pen)
        painter.drawLine(QPointF(0, point.y()), QPointF(self.width(), point.y()))
        painter.drawLine(QPointF(point.x(), 0), QPointF(point.x(), self.height()))
        painter.restore()

    def _draw_extra_lines(self, painter: QPainter) -> None:
        pass

    def _make_and_cache_image(self) -> None:
        if self.data is None:
            return

        shape = self.data.shape
        xform = self._make_draw_transform(shape)
        img_rect = QRectF(-shape[1] / 2, -shape[0] / 2, shape[1], shape[0])
        wnd_rect = xform.mapRect(img_rect)

        # clip to displayed region
        tl = wnd_rect.topLeft()
        br = wnd_rect.bottomRight()

        tl.setX(np.clip(tl.x(), 0, self.width()))
        tl.setY(np.clip(tl.y(), 0, self.height()))
        br.setX(np.clip(br.x(), 0, self.width()))
        br.setY(np.clip(br.y(), 0, self.height()))

        win_roi_rect = QRectF(tl, br)

        img_roi_rect = xform.inverted()[0].mapRect(win_roi_rect)
        img_roi_rect.translate(shape[1] / 2.0, shape[0] / 2.0)

        start = np.asanyarray([
            np.clip(floor(img_roi_rect.topLeft().y()), 0, shape[0]),
            np.clip(floor(img_roi_rect.topLeft().x()), 0, shape[1])
        ])
        end = np.asanyarray([
            np.clip(ceil(img_roi_rect.bottomRight().y()), 0, shape[0]),
            np.clip(ceil(img_roi_rect.bottomRight().x()), 0, shape[1])
        ])

        # check if nothing to draw
        if (end - start).min() <= 0 or win_roi_rect.width() <= 0 or win_roi_rect.width() <= 0:
            return

        # extract region of interest
        step = (end - start + 1) // np.asanyarray([ win_roi_rect.height(), win_roi_rect.width() ]).round().astype(int)
        step = np.where(step < 1, 1, step)
        data = self.data[start[0]:end[0]:step[0], start[1]:end[1]:step[1], ...]

        # determine scale bounds on full data
        if self._range_mode == MyNumpyImageWidget.Scaling.Absolute:
            (self._vmin, self._vmax) = self._range
        elif self._range_mode == MyNumpyImageWidget.Scaling.Relative:
            self._vmin = self.data.min()
            self._vmax = self.data.max()
        elif self._range_mode == MyNumpyImageWidget.Scaling.Percentile:
            (self._vmin, self._vmax) = np.percentile(self.data, self._range)
        else:
            raise ValueError(f'unknown data range mode: {self._range_mode}')

        # apply scale and colormap
        data = (data.astype(np.float32) - self._vmin) / (self._vmax - self._vmin)
        data = self._colormap(data, bytes=True)

        # determine image format
        data = np.squeeze(data)
        if data.ndim in [1, 2]:
            color = False
            alpha = False
        elif data.ndim == 3:
            color = data.shape[2] >= 3
            alpha = data.shape[2] in [2, 4]
        else:
            raise ValueError(f'invalid image dimensions: {data.ndim}')

        # match Qt optimized image format
        data = np.atleast_3d(data)
        if color:
            if alpha:
                # native format already
                pass
            else:
                data = np.concatenate((data, np.full(data.shape[:2], 255)))
        else:
            if alpha:
                data = np.take(data, [0, 0, 0, 1], axis=2)
            else:
                data = np.concatenate((data, data, data, np.full(data.shape[:2], 255)[..., None]))

        # convert to QImage
        # data = cbook._unmultiplied_rgba8888_to_premultiplied_argb32(memoryview(data))
        # self.__pixmap = QPixmap.fromImage(QImage(data, data.shape[1], data.shape[0], QImage.Format_ARGB32_Premultiplied))
        self.__pixmap = QPixmap.fromImage(QImage(data, data.shape[1], data.shape[0], QImage.Format_RGBA8888))
        self.__pixmap_draw_rect = QRectF(QPointF(start[1], start[0]), QPointF(end[1], end[0])).translated(-shape[1] / 2, -shape[0] / 2)


    def _get_drawn_image_dimensions(self, shape: Optional[Iterable[int]]=None) -> Tuple[float, float]:
        """Determine the size of the image that will be drawn, given current widget 
        size (self.width(), self.height()), sizing mode (self._size_mode), and image aspect ratio (self._aspect).
        If shape passed is None, then the current data shape is used.

        Args:
            shape (Optional[Iterable[int]], optional): _ription_. Defaults to None.

        Raises:
            ValueError: _description_
            ValueError: _description_

        Returns:
            Tuple[float, float]: (width, height) dimensions of the image that will be drawn in the widget, in pixels.
        """

        if shape is None:
            shape = self.data.shape
        (image_height, image_width) = shape

        (xs, ys) = self._size_mode

        if xs == MyNumpyImageWidget.Sizing.Fixed:
            width = image_width
        elif xs == MyNumpyImageWidget.Sizing.Stretch:
            width = self.width()
        elif xs == MyNumpyImageWidget.Sizing.Fit:
            width = None
        else:
            raise ValueError(f'unknown size mode: {xs}')

        if ys == MyNumpyImageWidget.Sizing.Fixed:
            height = image_height
        elif ys == MyNumpyImageWidget.Sizing.Stretch:
            height = self.height()
        elif ys == MyNumpyImageWidget.Sizing.Fit:
            height = None
        else:
            raise ValueError(f'unknown size mode: {ys}')

        if height and width:
            pass
        elif height:
            width = self._aspect * height
        elif width:
            height = width / self._aspect
        else:
            # fit image into widget
            s = min([self.width() / (image_height * self._aspect), self.height() / image_height])
            height = s * image_height
            width = self._aspect * height

        return (width, height)

    def _make_draw_transform(self, shape: Optional[Iterable[int]]=None) -> QTransform:
        if shape is None:
            shape = self.data.shape
        (image_height, image_width) = shape

        xform = QTransform()

        def _sign(bit):
            return -1 if (self._flip & bit) else 1

        # start by drawing a 1x1 image in the widget center
        xform.translate(self.width() / 2 + self._pan[0], self.height() / 2 + self._pan[1])
        xform.rotate(self._angle)
        xform.scale(
            self._zoom * _sign(MyNumpyImageWidget.Flip.Horizontal) / image_width,
            self._zoom * _sign(MyNumpyImageWidget.Flip.Vertical) / image_height
        )

        (width, height) = self._get_drawn_image_dimensions(shape)

        #print(f'make_draw_transform: image size {image_width}x{image_height} -> draw size {width}x{height}')
        # scale up to actual display size
        xform.scale(width, height)

        # return composed with user transform
        return xform * self._transform

    def _make_additional_stats(self) -> List[str]:
        lines = []
        if self.__pixmap is None:
            lines += ['Image: None']
        else:
            lines += [f'Image: {self.__pixmap.height()} x {self.__pixmap.width()}']
        lines += ['']
        lines += [f'Range: {self._vmin} - {self._vmax}']
        lines += [f'Pan: ({self._pan[0]}, {self._pan[1]})']
        lines += [f'Angle: {self._angle}']
        lines += [f'Flip: {self._flip % 4}']
        lines += [f'Zoom: {self._zoom:.2g}']
        return lines

    def _make_window_transform(self) -> QTransform:
        xform = self._make_draw_transform()
        xform.translate(-self.data.shape[1] / 2, -self.data.shape[0] / 2)
        xform = xform.inverted()[0]
        return xform

    def _map_window_to_data(self, window_point: QPointF) -> QPointF:
        """Given a point in window coordinates, returns same point in data coordinates. 

        Args:
            window_point (QPointF): Data point in window coordinates, where (0, 0) is the top-left of the widget and (width, height) is the bottom-right.

        Returns:
            QPointF: Data point in data coordinates.
        """
        image_point = self._make_window_transform().map(window_point)
        row = int(floor(image_point.y()))
        col = int(floor(image_point.x()))
        return (row, col)
    
    def _map_data_to_window(self, data_point: QPointF) -> Tuple[float, float]:
        """Given a point in data coordinates, return the point in current window (widget, really) coords

        Args:
            data_point (QPointF): Point in data coordinates

        Returns:
            QPointF: Point in widget coords
        """


        # translate to data center before rotation and scaling, so that those operations are about the image center.
        shape = self.data.shape
        tr1 = QTransform()
        tr1.translate(-shape[1] / 2, -shape[0] / 2)
        print("tr1 {0:f}, {1:f}".format(tr1.dx(), tr1.dy()))

        # Rotation and scale
        (drawn_width, drawn_height) = self._get_drawn_image_dimensions(shape)
        tr2 = QTransform()  
        tr2.rotate(self._angle)
        tr2.scale(
            self._zoom * (-1 if (self._flip & MyNumpyImageWidget.Flip.Horizontal) else 1) * drawn_width / shape[1],
            self._zoom * (-1 if (self._flip & MyNumpyImageWidget.Flip.Vertical) else 1) * drawn_height / shape[0]
        )
        print("tr2 m11 {0:f}, m22 {1:f}".format(tr2.m11(), tr2.m22()))

        # and translate to widget center
        tr3 = QTransform()
        tr3.translate(self.width() / 2 + self._pan[0], self.height() / 2 + self._pan[1])
        print("tr3 {0:f}, {1:f}".format(tr3.dx(), tr3.dy()))


        ptr1 = tr1.map(data_point)
        ptr2 = tr2.map(ptr1)
        ptr3 = tr3.map(ptr2)
        print("ptr1 {0:f}, {1:f}".format(ptr1.x(), ptr1.y()))
        print("ptr2 {0:f}, {1:f}".format(ptr2.x(), ptr2.y()))
        print("ptr3 {0:f}, {1:f}".format(ptr3.x(), ptr3.y()))

        # Now build full transform.
        xf = tr1 * tr2 * tr3    
        window_point = xf.map(data_point)
        return (window_point.y(), window_point.x())


    @property
    def flip(self) -> Flip:
        return self._flip
    @flip.setter
    def flip(self, value: Flip):
        self._flip = value
        self.update()

    @property
    def angle(self) -> float:
        return self._angle
    @angle.setter
    def angle(self, value: float):
        self._angle = value
        self.update()
