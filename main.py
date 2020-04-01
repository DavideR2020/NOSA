from PyQt5 import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
import qdarkstyle
import sys
# import needed for with pyinstaller exported neo to work
import numpy.lib.recfunctions

from view.Nosa import Nosa
from model.TIFLoader import TIFLoader

import unittest
from tests.BaselineTest import BaselineTest
from tests.SmoothingTest import SmoothingTest
from tests.SpikeDetectionTest import SpikeDetectionTest
from tests.BurstDetectionTest import BurstDetectionTest
from tests.EventShapeTest import EventShapeTest
from tests.PowerSpectrumTest import PowerSpectrumTest

if __name__ == '__main__':

    unittest.main(exit = False)

    app = QtGui.QApplication(['-platform', 'minimal'])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())


    conf = []
    nosa = Nosa(conf)
    nosa.show()

    app.exec_()

    QtCore.QThreadPool.globalInstance().waitForDone()
