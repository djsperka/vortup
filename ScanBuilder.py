from PyQt5.QtWidgets import QDialog, QApplication
from Ui_ScanBuilderDialog import Ui_ScanBuilderDialog
from vortex.scan import RasterScanConfig, RasterScan
from vortex import Range
from math import pi, cos, sin
import numpy as np
from matplotlib import pyplot as plt
from vortex_tools.scan import plot_annotated_waveforms_space, plot_annotated_waveforms_time



class ScanBuilder(QDialog, Ui_ScanBuilderDialog):
    """Wrapper class around designer-generated user interface. 
    
    The user interface file is created and updated using designer, which 
    is found somewhere in the qt5-tools package in your python installation
    (find site-packages inside your venv, as a starting point). The whole thing
    is done here (instead of inside the application file itself) to suppress a
    deprecation warning that comes up:

    sipPyTypeDict() is deprecated, the extension module should use sipPyTypeDictRef() instead

    I'm not sure what that means, but by moving the loading process (uic.loadUi) to a separate 
    file, it goes away. 

    Args:
        QDialog (_type_): Parent dialog that the UI is placed inside of
    """    
    
    def __init__(self):
        super().__init__() # Call the inherited class' __init__ method
        self.setupUi(self)  # Use Ui file geneated by pyuic5
        self.pbUpdate.clicked.connect(self.updateClicked)
        self.pbExit.clicked.connect(self.exitClicked)
        self.show()

    def updateClicked(self):
        print("Update clicked")
        self._cfg = self.getCfg()

        fig, axs = plt.subplots(1, 2, sharex=True, sharey=True, constrained_layout=True, subplot_kw=dict(adjustable='box', aspect='equal'))
        print("axs len ", len(axs))

        try:
            scan = RasterScan()
            scan.initialize(self._cfg)
            plot_annotated_waveforms_space(scan.scan_buffer(), scan.scan_markers(), inactive_marker=None, scan_line='w-', axes=axs[0])
            plot_annotated_waveforms_time(self._cfg.sampling_interval, scan.scan_buffer(), scan.scan_markers())
            plt.show()
        except RuntimeError as e:
            print("RuntimeError:")
            print(e)


    def exitClicked(self):
        self.accept()

    def getCfg(self):
        cfg = RasterScanConfig()
        imin = int(self.leLimitsBscanMin.text())
        imax = int(self.leLimitsBscanMax.text())
        cfg.segment_extent = Range(imin, imax)
        imin = int(self.leLimitsVolumeMin.text())
        imax = int(self.leLimitsVolumeMax.text())
        cfg.volume_extent = Range(imin, imax)
        cfg.segments_per_volume = 10
        cfg.samples_per_segment = 50
        for limit in cfg.limits:
            limit.acceleration *= 5
        cfg.loop = True
        return cfg




if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    dlg = ScanBuilder()
    dlg.show()
    sys.exit(app.exec_())
