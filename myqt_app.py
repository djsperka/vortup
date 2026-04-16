import sys
import math
import random
from pathlib import Path

import numpy as np
from qtpy.QtGui import QImage
from qtpy.QtWidgets import QApplication, QDialog, QVBoxLayout
from qtpy.QtCore import QTimer, Qt
from qtpy.QtGui import QPen, QBrush, QColor
from QCustomPlot_PyQt5 import QCustomPlot, QCP

from myqt import MyNumpyImageWidget

IMAGE_PATH = Path('/home/dan/work/oct/vortup/pattern.tiff')
customPlot = None
graph0 = None

def make_gradient_image(width: int, height: int) -> np.ndarray:
    x = np.linspace(0, 1, width)
    y = np.linspace(0, 1, height)
    xv, yv = np.meshgrid(x, y)
    return (xv + yv) / 2


def qimage_to_numpy(image: QImage) -> np.ndarray:
    image = image.convertToFormat(QImage.Format_RGB888)    
    width = image.width()
    height = image.height()

    ptr = image.bits()
    if hasattr(ptr, 'setsize'):
        ptr.setsize(image.byteCount())
        buffer = ptr
    else:
        buffer = ptr.asstring(image.byteCount())

    array = np.frombuffer(buffer, dtype=np.uint8)
    print(f'Loaded image before reshape: {array.shape} and dtype: {array.dtype}')

    array = array.reshape((height, width, 3))

    # Source - https://stackoverflow.com/a/42809034
    # Posted by J. Goedhart
    # Retrieved 2026-04-13, License - CC BY-SA 3.0

    img = 0.299*array[:,:,0]+0.587*array[:,:,1]+0.114*array[:,:,2]
    img = img.astype(np.uint8)
    (mx, mn) = (img.max(), img.min())
    print(f'Image max: {mx}, min: {mn}')


    return img


def makeRandomPlotData(num_points: int) -> (list, list):
    x = list(range(num_points))
    y = random.sample(range(1, 100), num_points)
    return (x, y)

def makePlotWidget():
    customPlot = QCustomPlot()
    graph0 = customPlot.addGraph()
    graph0.setPen(QPen(Qt.blue))
    graph0.setBrush(QBrush(QColor(0, 0, 255, 20)))

    (x, y) = makeRandomPlotData(50)

    graph0.setData(x, y)

    customPlot.rescaleAxes()
    customPlot.setInteraction(QCP.iRangeDrag)
    customPlot.setInteraction(QCP.iRangeZoom)
    customPlot.setInteraction(QCP.iSelectPlottables)
    return customPlot


def timeout():
    if graph0 is not None:
        (x, y) = makeRandomPlotData(50)
        graph0.setData(x, y)
        graph0.replot()

def main() -> int:
    app = QApplication(sys.argv)
    timer = QTimer()
    timer.timeout.connect(timeout)  # Connect to the timeout function
    timer.start(1000)  # Call timeout every 1000 ms (1 second)  

    data = make_gradient_image(256, 256)
    widget = MyNumpyImageWidget(
        data=data,
        debug=False,
    )
    widget.new_slice.connect(lambda y0, y1: print(f"Got slice signal {y0:f}-{y1:f}"))

    dialog = QDialog()
    dialog.setWindowTitle('MyNumpyImageWidget Viewer')
    layout = QVBoxLayout(dialog)
    layout.addWidget(widget)

    layout.addWidget(makePlotWidget())

    dialog.resize(900, 700)
    dialog.show()

    return app.exec_()


if __name__ == '__main__':
    raise SystemExit(main())