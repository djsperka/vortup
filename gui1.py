from PyQt5 import QtCore, QtGui, QtWidgets 
import sys 

# vortex imports
import numpy

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib import pyplot

from vortex import Range
from vortex.marker import Flags
from vortex.scan import RasterScan, RepeatedRasterScan, RadialScan, RepeatedRadialScan, FreeformScan, SequentialPattern, RasterScanConfig, RadialScanConfig

from vortex_tools.scan import plot_annotated_waveforms_time, plot_annotated_waveforms_space
#end vortex imports



class Ui_MainWindow(object): 

    def setupUi(self, MainWindow): 
        MainWindow.resize(506, 312) 
        self.centralwidget = QtWidgets.QWidget(MainWindow) 
        
        # adding pushbutton 
        self.pushButton = QtWidgets.QPushButton(self.centralwidget) 
        self.pushButton.setGeometry(QtCore.QRect(200, 150, 93, 28))
        self.pushButton.setText("Raster")
    
        # adding signal and slot 
        self.pushButton.clicked.connect(self.doRaster) 
    
        self.label = QtWidgets.QLabel(self.centralwidget) 
        self.label.setGeometry(QtCore.QRect(140, 90, 221, 20))     

        # keeping the text of label empty before button get clicked 
        self.label.setText("")     
        
        MainWindow.setCentralWidget(self.centralwidget) 

    def doRaster(self):
        standard(RasterScan(), 'Raster')

    def changelabeltext(self): 

        # changing the text of label after button get clicked 
        self.label.setText("You clicked PushButton")     

        # Hiding pushbutton from the main window 
        # after button get clicked. 
        self.pushButton.hide() 



# This is vortex from scan_explorer
def freeform():
    print("in freeform()")
    t = numpy.linspace(0, 1, 500)
    t2 = numpy.linspace(0, 5, 2500)
    waypoints = [
        numpy.column_stack((t+0.5, 0.3*t**2 + 0.5)),
        numpy.column_stack((0.01*numpy.cos(50*t), t/2)),
        numpy.column_stack((t/3+0.2, -t/2)),
        numpy.column_stack((0.1*numpy.sin(2*t2 + 0.2) - 0.5, 0.2*numpy.cos(3*t2) - 0.5))
    ]

    pattern = SequentialPattern().to_pattern(waypoints)

    scan = FreeformScan()
    cfg = scan.config
    cfg.pattern = pattern
    cfg.loop = True
    scan.initialize(cfg)

    show(scan, 'Freeform')

def standard(scan, name=None):
    name = name or type(scan)

    cfg = scan.config
    cfg.loop = True
    scan.initialize(cfg)

    show(scan, name)

def radial_nonnegative():
    scan = RadialScan()

    cfg = scan.config
    cfg.bscan_extent = Range(2, 5)
    cfg.volume_extent = Range(1, 2)
    cfg.loop = True
    scan.initialize(cfg)

    show(scan, 'Radial - Non-negative')

def raster_aim(name=None):
    raster = RasterScanConfig()
    raster.flags = Flags(0x1) # optional

    aiming = RadialScanConfig()
    aiming.set_aiming()
    aiming.offset = (5, 0)
    aiming.flags = Flags(0x2) # optional

    n = raster.segments_per_volume
    pattern = raster.to_segments()[:n//2] + aiming.to_segments() + raster.to_segments()[n//2:]

    scan = FreeformScan()
    cfg = scan.config
    cfg.pattern = pattern
    cfg.loop = True
    scan.initialize(cfg)

    show(scan, 'Raster + Aim')

def show(scan, name):
    print("in show()")
    cfg = scan.config

    fig, _ = plot_annotated_waveforms_time(cfg.sampling_interval, scan.scan_buffer(), scan.scan_markers())
    fig.suptitle(name)
    fig, _ = plot_annotated_waveforms_space(scan.scan_buffer(), scan.scan_markers())
    fig.suptitle(name)


if __name__ == "__main__": 
    app = QtWidgets.QApplication(sys.argv) 
    
    MainWindow = QtWidgets.QMainWindow() 
    ui = Ui_MainWindow() 
    ui.setupUi(MainWindow) 
    MainWindow.show() 

    sys.exit(app.exec_()) 
