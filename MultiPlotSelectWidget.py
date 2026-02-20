from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from qtpy.QtGui import QKeyEvent, QPaintEvent
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

import numpy as np
import cupy as cp
from typing import Iterable, List
from qtpy.QtGui import QPaintEvent
from typing import Tuple

# Inheriting from FigureCanvasQTAgg. 
# FigureCanvasQTAgg is a widget. Call update() to invalidate and trigger a paintEvent.

class MultiPlotSelectWidget(FigureCanvas):

    def __init__(self, parent=None, rows=4, cols=2, width=5, height=4, dpi=100, title=None):
        fig = Figure(figsize=(width, height), dpi=dpi)
        axs = fig.subplots(nrows=rows, ncols=cols*2)
        gs = axs[0, cols].get_gridspec()
        for i in range(rows):
             for j in range(cols, cols*2):
                  axs[i,j].remove()
        axbig = fig.add_subplot(gs[0:,cols:])
        axbig.annotate('Big Axes \nGridSpec[0:, {0:d}:]'.format(cols), (0.1, 0.5), xycoords='axes fraction', va='center')
        fig.tight_layout()
        super().__init__(fig)
        self.setParent(parent)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt5 Matplotlib 2D Image Example")

        # Create the Matplotlib canvas
        self.canvas = MultiPlotSelectWidget(self, width=5, height=4, dpi=100)

        # # Generate a sample 2D image (random data)
        # data = np.random.rand(100, 100)  # 100x100 array
        # self.plot_image(data)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

import sys
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

