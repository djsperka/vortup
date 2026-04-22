import sys
import math
import random
from pathlib import Path

import numpy as np
from qtpy.QtGui import QImage
from qtpy.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout
from qtpy.QtCore import QTimer, Qt
from qtpy.QtGui import QPen, QBrush, QColor
from QCustomPlot_PyQt5 import QCustomPlot, QCP, QCPAxisRect, QCPAxisTickerLog, QCPColorMap, QCPColorScale, QCPMarginGroup, QCPRange, QCPColorGradient

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

def makeCMImageWidget():
    customPlot = QCustomPlot()

    # configure axis rect:
    customPlot.setInteractions(QCP.Interaction.iRangeDrag | QCP.Interaction.iRangeZoom) # this will also allow rescaling the color scale by dragging/zooming
    customPlot.axisRect().setupFullAxesBox(True)
    customPlot.xAxis.setLabel("x")
    customPlot.yAxis.setLabel("y")
        
    # set up the QCPColorMap:
    colorMap = QCPColorMap(customPlot.xAxis, customPlot.yAxis)
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
    
    # add a color scale:
    colorScale = QCPColorScale(customPlot)
    customPlot.plotLayout().addElement(0, 1, colorScale) # add it to the right of the main axis rect
    colorScale.setType(QCPAxis.AxisType.atRight) # scale shall be vertical bar with tick/axis labels right (actually atRight is already the default)
    colorMap.setColorScale(colorScale) # associate the color map with the color scale
    colorScale.axis().setLabel("Magnetic Field Strength")
    
    # set the color gradient of the color map to one of the presets:
    colorMap.setGradient(QCPColorGradient(QCPColorGradient.GradientPreset.gpPolar))
    # we could have also created a QCPColorGradient instance and added own colors to
    # the gradient, see the documentation of QCPColorGradient for what's possible.
    
    # rescale the data dimension (color) such that all data points lie in the span visualized by the color gradient:
    colorMap.rescaleDataRange()
    
    # make sure the axis rect and color scale synchronize their bottom and top margins (so they line up):
    marginGroup = QCPMarginGroup(customPlot)
    customPlot.axisRect().setMarginGroup(QCP.MarginSide.msBottom | QCP.MarginSide.msTop, marginGroup)
    colorScale.setMarginGroup(QCP.MarginSide.msBottom | QCP.MarginSide.msTop, marginGroup)
    
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

def makeQCustomPlot():
    customPlot = QCustomPlot()
    customPlot.plotLayout().clear()  # clear default axis rect so the layout is empty
    customPlot.setInteractions(QCP.Interaction.iRangeDrag | QCP.Interaction.iRangeZoom) # this will also allow rescaling the color scale by dragging/zooming
    # make axis rects and add them to the layout:

    axes = QCPAxisRect(customPlot)
    axes.setupFullAxesBox(True)
    axes.xAxis.setLabel("x")
    axes.yAxis.setLabel("y")
        
    # set up the QCPColorMap:
    colorMap = QCPColorMap(axes.xAxis, axes.yAxis)
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
    
    # add a color scale:
    colorScale = QCPColorScale(customPlot)
    customPlot.plotLayout().addElement(0, 1, colorScale) # add it to the right of the main axis rect
    colorScale.setType(QCPAxis.AxisType.atRight) # scale shall be vertical bar with tick/axis labels right (actually atRight is already the default)
    colorMap.setColorScale(colorScale) # associate the color map with the color scale
    colorScale.axis().setLabel("Magnetic Field Strength")
    
    # set the color gradient of the color map to one of the presets:
    colorMap.setGradient(QCPColorGradient(QCPColorGradient.GradientPreset.gpPolar))
    # we could have also created a QCPColorGradient instance and added own colors to
    # the gradient, see the documentation of QCPColorGradient for what's possible.
    
    # rescale the data dimension (color) such that all data points lie in the span visualized by the color gradient:
    colorMap.rescaleDataRange()
        
    # make sure the axis rect and color scale synchronize their bottom and top margins (so they line up):
    marginGroup = QCPMarginGroup(customPlot)
    customPlot.axisRect().setMarginGroup(QCP.MarginSide.msBottom | QCP.MarginSide.msTop, marginGroup)
    colorScale.setMarginGroup(QCP.MarginSide.msBottom | QCP.MarginSide.msTop, marginGroup)
    
    # rescale the key (x) and value (y) axes so the whole color map is visible:
    customPlot.rescaleAxes()





    return customPlot


class MyDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('My Dialog')
        hlayout = QHBoxLayout()
        self.image_widget = makeImageWidget()
        self.cm_image_widget = makeCMImageWidget()
        hlayout.addWidget(self.image_widget)
        hlayout.addWidget(self.cm_image_widget)
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



class MyDialog2(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('My Dialog')
        layout = QHBoxLayout()
        self.qcp = makeQCustomPlot()
        layout.addWidget(self.qcp)
        self.setLayout(layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.timeout)  # Connect to the timeout function
        self.timer.start(1000)  # Call timeout every 1000 ms (1 second)  

    def timeout(self):
        if self.qcp is not None:
            self.qcp.replot()




def main() -> int:
    app = QApplication(sys.argv)
    dialog = MyDialog2()
    dialog.setWindowTitle('MyNumpyImageWidget Viewer')

    dialog.resize(900, 700)
    dialog.show()

    return app.exec_()


if __name__ == '__main__':
    raise SystemExit(main())