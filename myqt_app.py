import sys
import math
import random
import time
from pathlib import Path

import numpy as np
from qtpy.QtGui import QImage
from qtpy.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout
from qtpy.QtCore import QTimer, Qt
from qtpy.QtGui import QPen, QBrush, QColor
from QCustomPlot_PyQt5 import QCustomPlot, QCP, QCPAxisRect, QCPAxis, QCPAxisTickerLog, QCPColorMap, QCPColorMapData, QCPColorScale, QCPMarginGroup, QCPRange, QCPColorGradient, QCPGraph

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

def makeImageWidget():
    data = make_gradient_image(256, 256)
    return MyNumpyImageWidget(
        data=data,
        debug=False,
    )

def makeQCustomPlot():
    customPlot = QCustomPlot()

    # clear axes
    customPlot.plotLayout().clear() # clear everything in the plot layout (axes, color scales, etc.)

    # make axis rect for color map:
    axisRectCM = QCPAxisRect(customPlot)
    axisRectCM.setupFullAxesBox(True) # make left and bottom axes visible, but hide top and right axes
    customPlot.plotLayout().addElement(0, 0, axisRectCM)

    # axes for plot to the right of the color map:
    axisRectPlot = QCPAxisRect(customPlot)
    axisRectPlot.setupFullAxesBox(True) # make left and bottom axes visible, but
    axisRectPlot.axis(QCPAxis.atLeft).setScaleType(QCPAxis.stLogarithmic)
    logTicker = QCPAxisTickerLog()
    axisRectPlot.axis(QCPAxis.atLeft).setTicker(logTicker)
    axisRectPlot.axis(QCPAxis.atLeft).setNumberFormat("eb") # e = exponential, b = beautiful decimal powers
    axisRectPlot.axis(QCPAxis.atLeft).setNumberPrecision(0)  #
    axisRectPlot.axis(QCPAxis.atLeft).setRange(1e-2, 1e10)
    customPlot.plotLayout().addElement(0, 1, axisRectPlot)

    # axes for plot below the color map:
    axisRectPlot2 = QCPAxisRect(customPlot)
    axisRectPlot2.setupFullAxesBox(True) # make left and bottom axes visible, but
    customPlot.plotLayout().addElement(1, 0, axisRectPlot2)

    # axes for other plot below the color map:
    axisRectPlot3 = QCPAxisRect(customPlot)
    axisRectPlot3.setupFullAxesBox(True) # make left and bottom axes visible, but
    customPlot.plotLayout().addElement(1, 1, axisRectPlot3)

    # set up the QCPColorMap:
    colorMap = QCPColorMap(axisRectCM.axis(QCPAxis.atBottom), axisRectCM.axis(QCPAxis.atLeft))
    nx = 200
    ny = 200
    colorMap.data().setSize(nx, ny) # we want the color map to have nx * ny data points
    colorMap.data().setRange(QCPRange(-4, 4), QCPRange(-4, 4)) # and span the coordinate range -4..4 in both key (x) and value (y) dimensions
    # now we assign some data, by accessing the QCPColorMapData instance of the color map:
    for xIndex in range(nx):
        for yIndex in range(ny):
            x, y = colorMap.data().cellToCoord(xIndex, yIndex)
            r = 3*math.sqrt(x*x+y*y)+1e-2
            z = 2*x*(math.cos(r+2)/r-math.sin(r+2)/r) # the B field strength of dipole radiation (modulo physical constants)
            colorMap.data().setCell(xIndex, yIndex, z)
    
    # set the color gradient of the color map to one of the presets:
    colorMap.setGradient(QCPColorGradient(QCPColorGradient.GradientPreset.gpPolar))
    # we could have also created a QCPColorGradient instance and added own colors to
    # the gradient, see the documentation of QCPColorGradient for what's possible.
    
    # rescale the data dimension (color) such that all data points lie in the span visualized by the color gradient:
    colorMap.rescaleDataRange()    

    # Now add a graph to the right
    graph = customPlot.addGraph(axisRectPlot.axis(QCPAxis.atBottom), axisRectPlot.axis(QCPAxis.atLeft))
    graph.setPen(QPen(Qt.blue))
    graph.setBrush(QBrush(QColor(0, 0, 255, 20)))
    (x, y) = makeRandomLogPlotData(50, -2, 10)
    graph.setData(x, y)

    # graph below the color map:
    graph2 = customPlot.addGraph(axisRectPlot2.axis(QCPAxis.atBottom), axisRectPlot2.axis(QCPAxis.atLeft))
    graph2.setPen(QPen(Qt.red)) 
    graph2.setBrush(QBrush(QColor(255, 0, 0, 20)))
    (x, y) = makeRandomPlotData(50)
    graph2.setData(x, y)

    graph3 = customPlot.addGraph(axisRectPlot3.axis(QCPAxis.atBottom), axisRectPlot3.axis(QCPAxis.atLeft))
    graph3.setPen(QPen(Qt.green))
    graph3.setBrush(QBrush(QColor(0, 255, 0, 20)))
    (x, y) = makeRandomPlotData(50)
    graph3.setData(x, y)

    # rescale the key (x) and value (y) axes so the whole color map is visible:
    customPlot.rescaleAxes()
    return customPlot


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
    return (customPlot, graph0)

def makeRandomLogPlotData(num_points: int, min_exp: float, max_exp: float) -> (list, list):
    x = list(range(num_points))
    y = [10**random.uniform(min_exp, max_exp) for _ in range(num_points)]
    return (x, y)

def makeLogPlotWidget():
    customPlot = QCustomPlot()
    customPlot.addGraph()
    pen = QPen()
    pen.setColor(QColor(255,170,100))
    pen.setWidth(2)
    pen.setStyle(Qt.DotLine)
    customPlot.graph(0).setPen(pen)
    customPlot.graph(0).setName("x")
    (x, y) = makeRandomLogPlotData(50, -2, 10)
    customPlot.graph(0).setData(x, y)
    customPlot.rescaleAxes()

    #customPlot.yAxis.grid.setSubGridVisible(True)
    #customPlot.xAxis.grid.setSubGridVisible(True)
    customPlot.yAxis.setScaleType(QCPAxis.stLogarithmic)
    customPlot.yAxis2.setScaleType(QCPAxis.stLogarithmic)
    logTicker = QCPAxisTickerLog()
    customPlot.yAxis.setTicker(logTicker)
    customPlot.yAxis2.setTicker(logTicker)
    customPlot.yAxis.setNumberFormat("eb") # e = exponential, b = beautiful decimal powers
    customPlot.yAxis.setNumberPrecision(0)  # makes sure "1*10^4" is displayed only as "10^4"
    #customPlot.xAxis.setRange(0, 19.9);
    customPlot.yAxis.setRange(1e-2, 1e10)
    # // make range draggable and zoomable:
    # customPlot->setInteractions(QCP::iRangeDrag | QCP::iRangeZoom);
    
    # // make top right axes clones of bottom left axes:
    # customPlot->axisRect()->setupFullAxesBox();
    # // connect signals so top and right axes move in sync with bottom and left axes:
    # connect(customPlot->xAxis, SIGNAL(rangeChanged(QCPRange)), customPlot->xAxis2, SLOT(setRange(QCPRange)));
    # connect(customPlot->yAxis, SIGNAL(rangeChanged(QCPRange)), customPlot->yAxis2, SLOT(setRange(QCPRange)));





    return (customPlot, customPlot.graph(0))



class MyDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('My Dialog')
        hlayout = QHBoxLayout()
        self.image_widget = makeImageWidget()
        # self.cm_image_widget = makeCMImageWidget()
        hlayout.addWidget(self.image_widget)
        # hlayout.addWidget(self.cm_image_widget)
        layout = QVBoxLayout()
        layout.addLayout(hlayout)
        (self.plot_widget, self.graph0) = makePlotWidget()
        layout.addWidget(self.plot_widget)
        (self.log_plot_widget, self.log_graph0) = makeLogPlotWidget()
        layout.addWidget(self.log_plot_widget)
        self.setLayout(layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.timeout)  # Connect to the timeout function
        self.timer.start(1000)  # Call timeout every 1000 ms (1 second)  

    def timeout(self):
        if self.plot_widget is not None:
            (x, y) = makeRandomPlotData(50)
            self.graph0.setData(x, y)
            self.plot_widget.replot()
        if self.log_plot_widget is not None:
            (x, y) = makeRandomLogPlotData(50, -2, 10)
            self.log_graph0.setData(x, y)
            self.log_plot_widget.replot()   


class MyColorMap(QCPColorMap):
    def __init__(self, xAxis: QCPAxis, yAxis: QCPAxis):
        super().__init__(xAxis, yAxis)
        self.setGradient(QCPColorGradient(QCPColorGradient.GradientPreset.gpPolar))
        self.data().setSize(200, 200)
        self.data().setRange(QCPRange(-4, 4), QCPRange(-4, 4))
        for xIndex in range(200):
            for yIndex in range(200):
                x, y = self.data().cellToCoord(xIndex, yIndex)
                r = 3*math.sqrt(x*x+y*y)+1e-2
                z = 2*x*(math.cos(r+2)/r-math.sin(r+2)/r) # the B field strength of dipole radiation (modulo physical constants)
                self.data().setCell(xIndex, yIndex, z)
        self.rescaleDataRange()

    def updateRow(self, rowIndex: int, data: np.ndarray):
        for xIndex in range(200):
            self.data().setCell(xIndex, rowIndex, data[xIndex])

def makeQCustomPlot():
    customPlot = QCustomPlot()

    # clear axes
    customPlot.plotLayout().clear() # clear everything in the plot layout (axes, color scales, etc.)

    # make axis rect for color map:
    axisRectCM = QCPAxisRect(customPlot)
    axisRectCM.setupFullAxesBox(True) # make left and bottom axes visible, but hide top and right axes
    customPlot.plotLayout().addElement(0, 0, axisRectCM)

    # axes for plot to the right of the color map:
    axisRectPlot = QCPAxisRect(customPlot)
    axisRectPlot.setupFullAxesBox(True) # make left and bottom axes visible, but
    axisRectPlot.axis(QCPAxis.atLeft).setScaleType(QCPAxis.stLogarithmic)
    logTicker = QCPAxisTickerLog()
    axisRectPlot.axis(QCPAxis.atLeft).setTicker(logTicker)
    axisRectPlot.axis(QCPAxis.atLeft).setNumberFormat("eb") # e = exponential, b = beautiful decimal powers
    axisRectPlot.axis(QCPAxis.atLeft).setNumberPrecision(0)  #
    axisRectPlot.axis(QCPAxis.atLeft).setRange(1e-2, 1e10)
    customPlot.plotLayout().addElement(0, 1, axisRectPlot)

    # axes for plot below the color map:
    axisRectPlot2 = QCPAxisRect(customPlot)
    axisRectPlot2.setupFullAxesBox(True) # make left and bottom axes visible, but
    customPlot.plotLayout().addElement(1, 0, axisRectPlot2)

    # axes for other plot below the color map:
    axisRectPlot3 = QCPAxisRect(customPlot)
    axisRectPlot3.setupFullAxesBox(True) # make left and bottom axes visible, but
    customPlot.plotLayout().addElement(1, 1, axisRectPlot3)

    # set up the QCPColorMap:
    colorMap = MyColorMap(axisRectCM.axis(QCPAxis.atBottom), axisRectCM.axis(QCPAxis.atLeft))
    # nx = 200
    # ny = 200
    # colorMap.data().setSize(nx, ny) # we want the color map to have nx * ny data points
    # colorMap.data().setRange(QCPRange(-4, 4), QCPRange(-4, 4)) # and span the coordinate range -4..4 in both key (x) and value (y) dimensions
    # # now we assign some data, by accessing the QCPColorMapData instance of the color map:
    # for xIndex in range(nx):
    #     for yIndex in range(ny):
    #         x, y = colorMap.data().cellToCoord(xIndex, yIndex)
    #         r = 3*math.sqrt(x*x+y*y)+1e-2
    #         z = 2*x*(math.cos(r+2)/r-math.sin(r+2)/r) # the B field strength of dipole radiation (modulo physical constants)
    #         colorMap.data().setCell(xIndex, yIndex, z)
    
    # # set the color gradient of the color map to one of the presets:
    # colorMap.setGradient(QCPColorGradient(QCPColorGradient.GradientPreset.gpPolar))
    # we could have also created a QCPColorGradient instance and added own colors to
    # the gradient, see the documentation of QCPColorGradient for what's possible.
    
    # rescale the data dimension (color) such that all data points lie in the span visualized by the color gradient:
    #colorMap.rescaleDataRange()    

    # Now add a graph to the right
    graph = customPlot.addGraph(axisRectPlot.axis(QCPAxis.atBottom), axisRectPlot.axis(QCPAxis.atLeft))
    graph.setPen(QPen(Qt.blue))
    graph.setBrush(QBrush(QColor(0, 0, 255, 20)))
    (x, y) = makeRandomLogPlotData(50, -2, 10)
    graph.setData(x, y)

    # graph below the color map:
    graph2 = customPlot.addGraph(axisRectPlot2.axis(QCPAxis.atBottom), axisRectPlot2.axis(QCPAxis.atLeft))
    graph2.setPen(QPen(Qt.red)) 
    graph2.setBrush(QBrush(QColor(255, 0, 0, 20)))
    (x, y) = makeRandomPlotData(50)
    graph2.setData(x, y)

    graph3 = customPlot.addGraph(axisRectPlot3.axis(QCPAxis.atBottom), axisRectPlot3.axis(QCPAxis.atLeft))
    graph3.setPen(QPen(Qt.green))
    graph3.setBrush(QBrush(QColor(0, 255, 0, 20)))
    (x, y) = makeRandomPlotData(50)
    graph3.setData(x, y)

    # rescale the key (x) and value (y) axes so the whole color map is visible:
    customPlot.rescaleAxes()
    return customPlot, colorMap


def makeCMData(width:int , height: int, noise_level: float) -> QCPColorMapData:
    data = QCPColorMapData(width, height, QCPRange(-4, 4), QCPRange(-4, 4))
    for xIndex in range(width):
        for yIndex in range(height):
            x, y = data.cellToCoord(xIndex, yIndex)
            r = 3*math.sqrt(x*x+y*y)+1e-2
            z = 2*x*(math.cos(r+2)/r-math.sin(r+2)/r) # the B field strength of dipole radiation (modulo physical constants)
            z += noise_level * (random.random() - 0.5) * 2 # add some random noise
            data.setCell(xIndex, yIndex, z)
    return data 



class MyDialog2(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('My Dialog')
        layout = QHBoxLayout()
        self.qcp, self.colorMap = makeQCustomPlot()
        layout.addWidget(self.qcp)
        self.setLayout(layout)
        self.nextRow = 0

    def start(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.timeout)  # Connect to the timeout function
        self.timer.start(1000)  # Call timeout every 1000 ms (1 second)  

    def timeout(self):
        if self.qcp is not None:
            start = time.time()
            data = makeCMData(500, 500, noise_level=0.5)
            self.colorMap.setData(data, True) # set the whole data at once, with copy (True)
            self.colorMap.rescaleDataRange() # rescale the color range to fit the new data
            # data = (np.random.rand(200) - 0.5) * 4

            # self.colorMap.updateRow(self.nextRow, data)
            # self.nextRow = (self.nextRow + 1) % 200

            self.qcp.replot()
            end = time.time()
            print(f'Updated color map and replotted in {end - start:.3f} seconds')




def main() -> int:
    app = QApplication(sys.argv)
    # dialog = MyDialog2()
    # dialog.colorMap.setData(makeCMData(500, 500, noise_level=0), True)
    # dialog.qcp.rescaleAxes()
    # dialog.qcp.replot()
    dialog = MyDialog()
    dialog.setWindowTitle('MyNumpyImageWidget Viewer')

    dialog.resize(900, 700)
    dialog.show()
    # dialog.start() # start the timer to update the color map data

    return app.exec_()


if __name__ == '__main__':
    raise SystemExit(main())