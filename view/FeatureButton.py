from PyQt5 import QtGui, QtWidgets, QtCore
import sys
import os

class FeatureButton(QtWidgets.QWidget):

    def __init__(self, title, parent=None):
        # button
        self.btn = QtWidgets.QPushButton(parent)
        try:
            base_path = sys._MEIPASS
        except:
            base_path = os.path.abspath('.')
        path = os.path.join(base_path, 'img/{}.png'.format(title))
        self.btn.setIcon(QtGui.QIcon(path))
        self.btn.setIconSize(QtCore.QSize(30,30))
        self.btn.setMaximumHeight(35)
        self.btn.setStyleSheet('text-align:left;')
        textLabel = QtGui.QLabel(title)
        textLabel.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        textLabel.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        textLabel.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.btn.setLayout(QtWidgets.QGridLayout())
        left, top, right, bottom = self.btn.layout().getContentsMargins()
        self.btn.layout().setContentsMargins(30 + 2 * left, top, right, bottom)
        self.btn.layout().addWidget(textLabel)
        # checkbox
        self.cb = QtWidgets.QCheckBox(parent)
        self.cb.setChecked(True)
        self.cb.setText('')
        self.cb.setMinimumSize(20, 20)
        self.cb.setMaximumSize(35, 35)
        # layout
        QtWidgets.QWidget.__init__(self, parent)
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().addWidget(self.cb)
        self.layout().addWidget(self.btn)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
