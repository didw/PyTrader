import sys
from PyQt5.QtCore import Qt, QTimer, QTime
from PyQt5 import uic
import Kiwoom

class PyMon:
    def __init__(self):
        self.kiwoom = Kiwoom.Kiwoom()
        self.kiwoom.CommConnect()

    def run(self):
        print("run")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    pymon = PyMon()
    pymon.run()
