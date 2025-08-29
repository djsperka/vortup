from PyQt5.QtWidgets import QApplication, QWidget, QFileDialog, QGroupBox
from PyQt5.QtCore import pyqtSignal
from Ui_SaveVolumeGroupBox import Ui_SaveVolumeGroupBox
from platformdirs import user_data_dir
from pathlib import Path
from datetime import datetime
import warnings

class SaveVolumeGroupBox(QGroupBox, Ui_SaveVolumeGroupBox):

    # signal emitted with dialog is closing
    saveContVolumes = pyqtSignal()
    saveNVolumes = pyqtSignal(int)

    def __init__(self, parent: QWidget=None, root_folder: str=None):
        """Instantiate class

        Args:
        """
        super().__init__(parent)
        self.setupUi(self)
        self.pbSelectFolder.clicked.connect(self.__getFolder)
        if root_folder is None:
            self.pathDataRoot = Path(user_data_dir())
        else:
            p = Path(root_folder)
            if not p.is_dir():
                warnings.warn("SaveVolumeGroupBox: given folder is not a folder: {0:s}".format(root_folder))
                self.pathDataRoot = Path(user_data_dir())
            else:
                self.pathDataRoot = p
        self.__updateLabels()
        self.pbSaveContinuous.clicked.connect(self.saveContVolumes)
        self.pbSaveFixedN.clicked.connect(self.__saveFixedN)

    def __saveFixedN(self):
        self.saveNVolumes.emit(self.sbN.value())


    # def getFileSaveConfig(self):
    #     cfg = FileSaveConfig(self._saveDataType)
    #     cfg.save = self._cb.isChecked()
    #     cfg.filename = self._filename
    #     cfg.extension = self._extension
    #     return cfg

    # def __enableDisable(self):
    #     if self._cb.isChecked():
    #         if self._filename:
    #             self._pb.setEnabled(True)
    #             self._label.setText(self._filename)
    #         else:
    #             self._cb.setChecked(False)
    #             self._label.setText("not saving data")
    #     else:
    #         self._pb.setEnabled(False)
    #         self._label.setText("not saving data")

    # def __cbToggled(self, bChecked):
    #     print("Checked: ", str(bChecked))
    #     if bChecked:
    #         # See if filename selected. If not, open dialog.
    #         if not self._filename:
    #             filename, extension = self.__getFileNameExt(self._filename)
    #             if filename:
    #                 self._filename = filename
    #                 self._extension = extension
    #     self.__enableDisable()

    def __getFolder(self, folder: str=''):
        selected_folder = QFileDialog.getExistingDirectory(self, "Select folder")
        print("Selected folder is {0:s}".format(selected_folder))
        if len(selected_folder)>0:
            self.pathDataRoot = Path(selected_folder)
        self.__updateLabels()

    def __updateLabels(self):
        self.labelFolder.setText(str(self.pathDataRoot))
        self.pathDataActual = self.pathDataRoot / datetime.today().strftime('%Y-%m-%d')
        self.labelStatus.setText("Data will be saved to folder {0:s}".format(str(self.pathDataActual)))

    def enableSaving(self, bEnable: bool=True):
        self.sbN.setEnabled(bEnable)
        self.pbSaveFixedN.setEnabled(bEnable)
        self.pbSaveContinuous.setEnabled(bEnable)

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = SaveVolumeGroupBox(None)
    w.show()
    app.exec()
    sys.exit()
