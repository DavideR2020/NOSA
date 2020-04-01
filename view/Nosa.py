from PyQt5 import QtGui, QtWidgets, QtCore
import pyqtgraph as pg

from model.DataManager import DataManager
from view.ImageView import ImageView
from view.SourceManager import SourceManager
from view.ObjectManager import ObjectManager
from view.PipelineManager import PipelineManager
from view.PlotManager import PlotManager
from features.CellSelection import CellSelection

class Nosa(QtGui.QWidget):

    def __init__(self, configurations, parent=None):

        QtGui.QWidget.__init__(self, parent)
        self.setWindowTitle("NOSA - Neuro-Optical Signal Analysis")

        self.conf = configurations
        self.infile = ''

        # layout
        self.layout = QtWidgets.QGridLayout(self)
        self.main_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)
        self.layout.addWidget(self.main_splitter, 0, 0)
        self.left_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical, self.main_splitter)

        # data manager
        self.data_manager = DataManager(self)

        # cell selection
        self.cell_selection = CellSelection(self.data_manager, parent=self.left_splitter)

        # source manager
        self.source_manager = SourceManager(self.data_manager, parent=self.left_splitter)
        
        # plot manager
        self.plot_manager = PlotManager(self.data_manager, cell_selection_imv = self.cell_selection.imv)

        # pipeline manager
        self.pipeline_manager = PipelineManager(self.data_manager, parent=self.main_splitter)
        
        # object_ manager
        self.object_manager = ObjectManager(self.data_manager, parent=self.left_splitter)

        self.left_splitter.addWidget(self.source_manager)
        self.left_splitter.addWidget(self.object_manager)
        self.left_splitter.addWidget(self.cell_selection)
        
        self.main_splitter.addWidget(self.left_splitter)
        self.main_splitter.addWidget(self.plot_manager)
        self.main_splitter.addWidget(self.pipeline_manager)
