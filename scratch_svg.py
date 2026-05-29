import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
app = QApplication(sys.argv)
icon = QIcon("/usr/share/tiny-dfr/brightness_high.svg")
pixmap = icon.pixmap(64, 64)
print(f"Pixmap is null: {pixmap.isNull()}")
