from PyQt5 import QtCore

class WorkerSignals(QtCore.QObject):
    max_progress = QtCore.pyqtSignal(int)
    progress = QtCore.pyqtSignal(int)
    finished = QtCore.pyqtSignal(dict)