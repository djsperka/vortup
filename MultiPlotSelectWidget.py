from qtpy.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QLabel
from qtpy.QtCore import QTimer, Signal
from qtpy.QtGui import QPixmap, QImage, QPen, QColor, QPainter
from image_display import ImageDisplay
from PIL import Image

import numpy as np
from dataclasses import dataclass




class MyImageWidget(QLabel):

    __clicked_signal = Signal(int, int, name='clicked')
 #  __selected_color = QColor(102, 255, 51)
    __selected_color = QColor(51, 204, 255)
    __selected_width = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScaledContents(True)
        self.setMinimumSize(256, 256)
        self._userdata = None
        self._selected = False

    @property
    def userdata(self):
        return self._userdata
    
    @userdata.setter
    def userdata(self, value):
        self._userdata = value

    def set_image(self, data: np.ndarray):
        #        qrgb_dict = {'r': lambda x: QtGui.qRgb(x, 0, 0),
        #              'g': lambda x: QtGui.qRgb(0, x, 0),
        #              'b': lambda x: QtGui.qRgb(0, 0, x)}
        # colortable = [qrgb_dict[color](i) for i in range(256)]
        s=data.shape
        img = QImage(data, s[1], s[0], s[1], QImage.Format_Indexed8)
        qpix = QPixmap(QImage(img))
        self.setPixmap(qpix)

    def mousePressEvent(self, ev):
        d = self.userdata
        self.__clicked_signal.emit(*d)

    def mouseDoubleClickEvent(self, ev):
        d = self.userdata
        print("double click at {:d},{:d}".format(*d))

    def paintEvent(self, ev):

        super().paintEvent(ev)

        painter = QPainter()
        painter.begin(self)
        if self._selected:
            # draw box at edge
            self._drawOutlineBox(painter)
        painter.end()


    def _drawOutlineBox(self, painter: QPainter):
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        pen = QPen(self.__selected_color)
        pen.setWidth(self.__selected_width)
        painter.setPen(pen)
        painter.drawRect(0, 0, self.width(), self.height())





@dataclass
class MPSWData:
    ascan_data: None | np.ndarray = None
    spectra_data: None | np.ndarray = None


class MPSW(QWidget):

    def __init__(self, parent=None, columns=2, rows=2):
        super().__init__(parent)
        self._rows = rows
        self._columns = columns

        layout = QGridLayout()

        # a word of warning: the widgets in QGridLayout are specified (0-based) ROW,COL
        self._data = [[None for _ in range(self._columns)] for _ in range(self._rows)]
        self._widgets = [[0 for _ in range(self._columns)] for _ in range(self._rows)]
        self._count = -1     # this will keep track of the next position to be replaced
        for i in range(self._columns):
            for j in range(self._rows):
                self._widgets[j][i] = MyImageWidget()
                self._widgets[j][i].userdata = (j,i)
                self._widgets[j][i].clicked.connect(self.image_clicked)
                layout.addWidget(self._widgets[j][i], j, i)

        self.setLayout(layout)

    def _update_selected(self, r, c):
        for i in range(self._columns):
            for j in range(self._rows):
                if self._widgets[j][i]._selected:
                    self._widgets[j][i]._selected = False
                    self._widgets[j][i].update()
        self._widgets[r][c]._selected = True
        self._widgets[r][c].update()

    def image_clicked(self, r, c):
        self._update_selected(r, c)
        print("Image clicked r={:d} c={:d}, width={:d} height={:d}".format(r, c, self._widgets[r][c].width(), self._widgets[c][r].height()))

    def _ind2sub(self, ind):
        i = ind % (self._rows * self._columns)
        r = i // self._columns
        c = i % self._columns
        return (r, c)

    def _next_position(self):
        while True:
            self._count+=1
            (r,c) = self._ind2sub(self._count)
            if self._data[r][c] is None or not self._widgets[r][c]._selected:
                return (r,c)

    def add_data(self, ascan_data, spectra_data):
        (r, c) = self._next_position()
        self._data[r][c] = MPSWData(ascan_data, spectra_data)
        self._widgets[r][c].set_image(ascan_data)
        # find first empty slot, save it there
        # for i in range(self._columns):
        #     for j in range(self._rows):
        #         if self._data[j][i] is None:
        #             self._data[j][i] = MPSWData(ascan_data, spectra_data)
        #             self._widgets[j][i].set_image(ascan_data)
        #             break
        #     else:
        #         # The else here is executed ONLY IF THERE WAS NO BREAK!
        #         # In other words, this is executed when the loop runs to completion.
        #         continue
        #     break



class MainWindow(QMainWindow):
    def __init__(self, list=[]):
        super().__init__()
        self._image_list = list
        self._image_index = 0
        self.setWindowTitle("PyQt5 Matplotlib 2D Image Example")
        self.plot = MPSW(self, rows=3, columns=5)
        self.setCentralWidget(self.plot)
        self.timer = QTimer()
        self.timer.timeout.connect(self.timeout)
        self.timer.start(1000)  # might not actually start until event loop starts

    def timeout(self):
        if len(self._image_list) > 0:
            image = Image.open(self._image_list[self._image_index])
            # convert image to numpy array
            data = np.asarray(image)
            self.plot.add_data(data, data.shape)    # the data.shape is dummy - should be spectra_data that might be saved
            self._image_index+=1
            if self._image_index >= len(self._image_list):
                self._image_index = 0
        else:
            print('no images')



import sys
if __name__ == "__main__":

    # load image filenames
    with open('images.txt', 'r') as f:
        image_list = [line.rstrip() for line in f]

    app = QApplication(sys.argv)
    window = MainWindow(image_list)
    window.show()
    sys.exit(app.exec())

