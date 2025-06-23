import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QFileDialog, QMessageBox
from Ui_CbFileSaveWidget import Ui_CbFileSaveWidget
from VtxEngineParams import FileSaveConfig

class CbFileSaveWidget(QWidget, Ui_CbFileSaveWidget):
    def __init__(self, parent: QWidget=None, filename: str='', datatype: str = 'data'):
        super().__init__(parent)
        self.setupUi(self)
        self._filename = filename
        self._extension = ''
        self._labelDataType = datatype

        # text
        self._cb.setText("Save {0:s} data".format(self._labelDataType))

        # callbacks
        self._cb.toggled.connect(self.__cbToggled)
        self._pb.clicked.connect(self.__selectFileClicked)

        # enable/disable
        self.__enableDisable()

    def getFileSaveConfig(self):
        cfg = FileSaveConfig()
        cfg.save = self._cb.isChecked()
        cfg.filename = self._filename
        cfg.extension = self._extension
        return cfg

    def __enableDisable(self):
        if self._cb.isChecked():
            if self._filename:
                self._pb.setEnabled(True)
                self._label.setText(self._filename)
            else:
                self._cb.setChecked(False)
                self._label.setText("not saving data")
        else:
            self._pb.setEnabled(False)
            self._label.setText("not saving data")

    def __cbToggled(self, bChecked):
        print("Checked: ", str(bChecked))
        if bChecked:
            # See if filename selected. If not, open dialog.
            if not self._filename:
                filename, extension = self.__getFileNameExt(self._filename)
                if filename:
                    self._filename = filename
                    self._extension = extension
        self.__enableDisable()

    def __getFileNameExt(self, filename: str='') -> FileSaveConfig:
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog

        selectedFileName = ''
        selectedFileExtension = ''
        bTryAgain = True
        while bTryAgain:
            fileName, _ = QFileDialog.getSaveFileName(self,"Select filename for {0:s}".format(self._labelDataType),filename,"MATLAB (*.mat);;HD5 (*.h5);;Numpy (*.npy)", options=options)
            if fileName:
                d = os.path.dirname(fileName)
                b = os.path.basename(fileName)
                n,ext = os.path.splitext(b)
                if ext:
                    match ext.lower():
                        case '.mat':
                            selectedFileExtension = 'mat'
                            bTryAgain = False
                        case '.h5':
                            selectedFileExtension = 'h5'
                            bTryAgain = False
                        case '.npy':
                            selectedFileExtension = 'npy'
                            bTryAgain = False
                else:
                    bTryAgain = True
            else:
                bTryAgain = False
            if bTryAgain:
               QMessageBox.information(self, "Oops", "Cannot determine file type. Please choose a file with extension \".mat\", \".h5\", or \".npy\".")
            else:
                selectedFileName = fileName
        return selectedFileName, selectedFileExtension


    def __selectFileClicked(self):
        filename, extension = self.__getFileNameExt(self._filename)
        if filename:
            self._filename = filename
            self._extension = extension
        self.__enableDisable()

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = CbFileSaveWidget()
    ui = Ui_CbFileSaveWidget()
    w.show()
    app.exec()
    print("w._filename {0:s}\nw._extension {1:s}".format(w._filename, w._extension))
    sys.exit()
