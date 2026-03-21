from qtpy.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QLabel, QPushButton
from qtpy.QtCore import QTimer, Signal
from qtpy.QtGui import QPixmap, QImage
from image_display import ImageDisplay
from PIL import Image

import numpy as np
from dataclasses import dataclass




class MyImageWidget(QLabel):

    __clicked_signal = Signal(int, int, name='clicked')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScaledContents(True)
        self.setMinimumSize(256, 256)
        self._userdata = None

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

    def mouseReleaseEvent(self, ev):
        if self.userdata is None:
            d=(-1,-1)
        else:
            d=self.userdata
        self.__clicked_signal.emit(*d)


@dataclass
class MPSWData:
    ascan_data: None | np.ndarray = None
    spectra_data: None | np.ndarray = None


class MPSW(QWidget):

    def __init__(self, parent=None, columns=2, rows=2):
        super().__init__(parent)
        self._rows = rows
        self._columns = columns

        # we will make a QGridLayout 
        # Make it have rowsx(2*columns)
        # Left side rxc populate with image widgets
        # right side is a single widget
        layout = QGridLayout()


        # a word of warning: the widgets in QGridLayout are specified (0-based) ROW,COL

        self._data = [[None for _ in range(self._columns)] for _ in range(self._rows)]
        self._l = [[0 for _ in range(self._columns)] for _ in range(self._rows)]
        for i in range(self._columns):
            for j in range(self._rows):
                self._l[j][i] = MyImageWidget()
                self._l[j][i].userdata = (j,i)
                self._l[j][i].clicked.connect(self.image_clicked)
                layout.addWidget(self._l[j][i], j, i)
        self._r = MyImageWidget()
        layout.addWidget(self._r, 0, self._columns, self._columns, self._rows)

        self.setLayout(layout)

    def image_clicked(self, c, r):
        print("Image clicked c={:d} r={:d}".format(c, r))

    def add_data(self, ascan_data, spectra_data):
        # find first empty slot, save it there
        for i in range(self._columns):
            for j in range(self._rows):
                if self._data[j][i] is None:
                    self._data[j][i] = MPSWData(ascan_data, spectra_data)
                    self._l[j][i].set_image(ascan_data)
                    break
            else:
                # The else here is executed ONLY IF THERE WAS NO BREAK!
                # In other words, this is executed when the loop runs to completion.
                continue
            break



# class MPSW(QWidget):

#     def __init__(self, parent=None):
#         super().__init__(parent)

#         self._rows = 2
#         self._cols = 2
#         self._data = [[None for _ in range(self._cols)] for _ in range(self._rows)]
#         self._plots = [[None for _ in range(self._cols)] for _ in range(self._rows)]


#         grid_layout = QGridLayout()
#         for i in range(self._cols):
#             for j in range(self._rows):
#                 self._data[i][j] = None
#                 self._plots[i][j] = NumpyImageViewer()
#                 grid_layout.addWidget(self._plots[i][j], i, j)
#         self._bigplot = NumpyImageViewer()
#         hbox_layout = QHBoxLayout()
#         hbox_layout.addLayout(grid_layout)
#         hbox_layout.addWidget(self._bigplot)
#         self.setLayout(hbox_layout)

#     def add_data(self, ascan_data, spectra_data):
#         # find first empty slot, save it there
#         for i in range(self._cols):
#             for j in range(self._rows):
#                 if self._data[i][j] is None:

#                     self._data[i][j] = MPSWData(ascan_data, spectra_data)
#                     self._plots[i][j].data = self._data[i][j].ascan_data
#                     self._plots[i][j].invalidate()
#                     print("Saved at ", i, j, np.shape(ascan_data))
#                     break
#             else:
#                 # The else here is executed ONLY IF THERE WAS NO BREAK!
#                 # In other words, this is executed when the loop runs to completion.
#                 continue
#             break


# class MultiPlotSelectWidget(FigureCanvas):

#     def __init__(self, parent=None, rows=4, cols=2, width=5, height=4, dpi=100, title=None):
#         fig = Figure(figsize=(width, height), dpi=dpi)
#         axs = fig.subplots(nrows=rows, ncols=cols*2)
#         gs = axs[0, cols].get_gridspec()
#         for i in range(rows):
#              for j in range(cols, cols*2):
#                   axs[i,j].remove()
#         axbig = fig.add_subplot(gs[0:,cols:])
#         axbig.annotate('Big Axes \nGridSpec[0:, {0:d}:]'.format(cols), (0.1, 0.5), xycoords='axes fraction', va='center')
#         fig.tight_layout()
#         super().__init__(fig)
#         self.setParent(parent)




class MainWindow(QMainWindow):
    def __init__(self, list=[]):
        super().__init__()
        self._image_list = list
        self._image_index = 0
        self.setWindowTitle("PyQt5 Matplotlib 2D Image Example")
        self.plot = MPSW(self, rows=3, columns=3)
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

