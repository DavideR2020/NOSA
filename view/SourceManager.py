from PyQt5 import QtGui, QtWidgets, QtCore

from view.MovementCorrectionDialog import MovementCorrectionDialog
from view.AdjustFrequencyDialog import AdjustFrequencyDialog
from model.ABFLoader import ABFLoader
from model.TIFLoader import TIFLoader

class SourceManager(QtGui.QWidget):

    def __init__(self, data_manager, parent=None):
        
        QtGui.QWidget.__init__(self, parent)

        self.setMinimumSize(350,100)

        self.data_manager = data_manager
        self.data_manager.source_manager = self

        # create the adjust frequency dialog
        self.adjust_frequency_dialog = AdjustFrequencyDialog(parent, data_manager)

        # table
        self.table 	= QtWidgets.QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['Filename','Frames','Frequency','Offset'])
        self.table.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)
        self.table.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setResizeMode(2, QtGui.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setResizeMode(3, QtGui.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setFixedHeight(QtGui.QFontMetrics(self.table.horizontalHeader().font()).height() + 10)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(20)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(lambda _: self.contextMenu())
        self.tableItemSelectionChangedConnect()

        # movement correction dialog
        self.movement_correction = MovementCorrectionDialog(self, self.data_manager)

        # table buttons
        self.add_btn = QtWidgets.QPushButton('Add', self)
        self.mc_btn = QtWidgets.QPushButton('Movement Correction', self)
        self.crop_btn = QtWidgets.QPushButton('Crop', self)
        self.offset_btn = QtWidgets.QPushButton('Offset', self)
        self.del_btn = QtWidgets.QPushButton('Delete', self)

        self.mc_btn.setEnabled(False)
        self.crop_btn.setEnabled(False)
        self.offset_btn.setEnabled(False)
        self.del_btn.setEnabled(False)

        self.add_btn.clicked.connect(self.add)
        self.mc_btn.clicked.connect(self.movementCorrection)
        self.crop_btn.clicked.connect(self.crop)
        self.offset_btn.clicked.connect(self.offset)
        self.del_btn.clicked.connect(self.delete)

        # layout
        self.layout = QtWidgets.QGridLayout()
        self.setLayout(self.layout)
        self.layout.setSpacing(0)
        self.layout.setMargin(0)
        self.layout.addWidget(self.table, 0, 0, 1, 5)
        self.layout.addWidget(self.add_btn, 1, 0)
        self.layout.addWidget(self.mc_btn, 1, 1)
        self.layout.addWidget(self.crop_btn, 1, 2)
        self.layout.addWidget(self.offset_btn, 1, 3)
        self.layout.addWidget(self.del_btn, 1, 4)

    def contextMenu(self):
        # do not show if there is no source available
        if len(self.data_manager.sources) == 0 or self.data_manager.source_selection is None:
            return
        self.menu = QtGui.QMenu(self)
        adjust_frequency = self.menu.addAction('adjust frequency')
        adjust_frequency.triggered.connect(lambda _: self.adjustFrequency())
        self.menu.popup(QtGui.QCursor.pos())

    def adjustFrequency(self):
        self.adjust_frequency_dialog.show()

    def add(self):
        """Opens a file dialog to let the user select a source file (.tif, .tiff, .abf) and loads this file."""
        fname,ok = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', directory='', filter='All (*.tiff *.tif *.abf);;TIFF (*.tiff *.tif);;ABF (*.abf)')
        if ok:
            if fname.endswith('abf'):
                _ = ABFLoader(self.data_manager, fname)
            else:
                _ = TIFLoader(self.data_manager, fname)

    def movementCorrection(self):
        self.movement_correction.show()

    def delete(self):
        ret = QtWidgets.QMessageBox.question(self, 'Confirm deletion', 'Please confirm deletion of the selected source. All Object\'s belonging to this source will be deleted too.', QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        if ret == QtWidgets.QMessageBox.Ok:
            self.data_manager.removeSource()

    def crop(self):
        """Opens a dialog to let the user select start and end frame of the source"""
        source = self.data_manager.sources[self.data_manager.source_selection]
        source_data_len = source.getMaxEndFrame()
        start_min = 0
        start_max = source_data_len-1
        startFrame,okStart = QtWidgets.QInputDialog.getInt(self,
            'Source Settings',
            'Start Frame (min: {}, max: {})'.format(start_min, start_max),
            value=source.start,
            min=start_min,
            max=start_max)
        if okStart:
            end_min = startFrame + 1
            end_max = source_data_len
            endFrame,okEnd = QtWidgets.QInputDialog.getInt(self,
                'Source Settings',
                'End Frame (min: {}, max: {})'.format(end_min, end_max),
                value=max(source.end, end_min),
                min=end_min,
                max=end_max)
            if okEnd:
                self.data_manager.setSourceAttributes(self.data_manager.source_selection, {'start': startFrame, 'end': endFrame})

    def offset(self):
        """Opens a dialog to let the user set the offset for the currently selected Source"""
        offset = self.data_manager.sources[self.data_manager.source_selection].offset
        new_offset, ok = QtWidgets.QInputDialog.getDouble(self,
            'Source Settings',
            'Offset (s)',
            value=offset,
            decimals=3)
        if ok:
            self.data_manager.setSourceAttributes(self.data_manager.source_selection, {'offset': new_offset})

    def refreshView(self):
        self.tableItemSelectionChangedDisconnect()
        selected = None
        if len(self.table.selectedIndexes()) > 0:
            selected = self.table.selectedIndexes()[0].row()

        self.table.setRowCount(0)
        for row in range(len(self.data_manager.sources)):
            source = self.data_manager.sources[row]
            self.table.insertRow(row)
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(source.name))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem('{}:{}'.format(source.start, source.end)))
            if source.adjust_frequency_active:
                freq_str = '{} (rec. {}) Hz'.format(source.getFrequency(), source.original_frequency)
            else:
                freq_str = '{} Hz'.format(source.original_frequency)
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(freq_str))
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem('{} s'.format(source.offset)))

        if selected is not None:
            self.table.selectRow(selected)
        self.tableItemSelectionChangedConnect()

        sources_available = len(self.data_manager.sources) > 0
        self.mc_btn.setEnabled(sources_available)
        self.crop_btn.setEnabled(sources_available)
        self.offset_btn.setEnabled(sources_available)
        self.del_btn.setEnabled(sources_available)

    def tableItemSelectionChangedDisconnect(self):
        self.table.itemSelectionChanged.disconnect()

    def tableItemSelectionChangedConnect(self):
        self.table.itemSelectionChanged.connect(self.itemSelectionChanged)

    def itemSelectionChanged(self):
        if len(self.table.selectedIndexes()) > 0:
            self.data_manager.selectSource(self.table.selectedIndexes()[0].row())
        else:
            # This should never happen.
            pass

