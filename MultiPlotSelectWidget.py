from qtpy.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout
from image_display import ImageDisplay

import numpy as np
from dataclasses import dataclass

# Inheriting from FigureCanvasQTAgg. 
# FigureCanvasQTAgg is a widget. Call update() to invalidate and trigger a paintEvent.

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

#         for i in range(self._cols):
#             for j in range(self._rows):
#                 self._data[i][j] = None
#                 self._plots[i][j] = NumpyImageViewer()
#                 grid_layout.addWidget(self._plots[i][j], i, j)

        self._data = [[None for _ in range(self._columns)] for _ in range(self._rows)]
        self._l = [[0 for _ in range(self._columns)] for _ in range(self._rows)]
        for i in range(self._columns):
            for j in range(self._rows):
                self._l[j][i] = ImageDisplay()
                layout.addWidget(self._l[j][i], j, i)
        self._r = ImageDisplay()
        layout.addWidget(self._r, 0, self._columns, self._columns, self._rows)

        self.setLayout(layout)

    def add_data(self, ascan_data, spectra_data):
        # find first empty slot, save it there
        for i in range(self._columns):
            for j in range(self._rows):
                if self._data[j][i] is None:
                    self._data[j][i] = MPSWData(ascan_data, spectra_data)
                    print("Saved at ", i, j, np.shape(ascan_data))
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
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt5 Matplotlib 2D Image Example")

        self.plot = MPSW(self, rows=2, columns=2)

        self.setCentralWidget(self.plot)

import sys
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

