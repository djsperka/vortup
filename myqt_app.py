import sys
from pathlib import Path

import numpy as np
from qtpy.QtGui import QImage
from qtpy.QtWidgets import QApplication, QDialog, QVBoxLayout

from myqt import MyNumpyImageWidget

IMAGE_PATH = Path('/home/dan/work/oct/vortup/pattern.tiff')


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


def main() -> int:
    app = QApplication(sys.argv)

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
    dialog.resize(900, 700)
    dialog.show()

    return app.exec_()


if __name__ == '__main__':
    raise SystemExit(main())