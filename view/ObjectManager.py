from PyQt5 import QtGui, QtWidgets, QtCore
import time
import numpy as np

from util import colors
from view.ExportDialog import ExportDialog
from model.export import export
from view.AddCopyMultipleDialog import AddCopyMultipleDialog
from view.DeleteMultipleDialog import DeleteMultipleDialog

class ObjectManager(QtGui.QWidget):

    def __init__(self, data_manager, parent=None):
        
        QtGui.QWidget.__init__(self, parent)
        
        self.setMinimumSize(350,150)

        self.data_manager = data_manager
        self.data_manager.object_manager = self

        # table
        self.table 	= QtWidgets.QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['','Name', 'Source', 'Invert'])
        self.table.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setResizeMode(2, QtGui.QHeaderView.Stretch)
        self.table.horizontalHeader().setResizeMode(3, QtGui.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setFixedHeight(QtGui.QFontMetrics(self.table.horizontalHeader().font()).height() + 10)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(20)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.setShowGrid(False)
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.contextMenu)
        self.table.itemSelectionChanged.connect(self.itemSelectionChanged)
        self.table.setStyleSheet('QCheckBox{background-color:rgba(1,1,1,0);}')
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.activated.connect(self.cellActivated)

        self.invert_checkboxes = []

        # table buttons
        self.add_btn = QtWidgets.QPushButton('Add', self)
        self.add_masked_btn = QtWidgets.QPushButton('Add copies')
        self.name_btn = QtWidgets.QPushButton('Name', self)
        self.delete_btn = QtWidgets.QPushButton('Delete', self)
        self.export_btn = QtWidgets.QPushButton('Export', self)

        self.add_btn.setEnabled(False)
        self.add_masked_btn.setEnabled(False)
        self.name_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.export_btn.setEnabled(False)

        self.add_btn.clicked.connect(self.add)
        self.add_masked_btn.clicked.connect(self.addMasked)
        self.name_btn.clicked.connect(self.name)
        self.delete_btn.clicked.connect(self.delete)
        self.export_btn.clicked.connect(self.exportDialogShow)

        # layout
        self.layout = QtWidgets.QGridLayout()
        self.setLayout(self.layout)
        self.layout.setSpacing(0)
        self.layout.setMargin(0)
        self.layout.addWidget(self.table, 0, 0, 1, 5)
        self.layout.addWidget(self.add_btn, 1, 0, 1, 1)
        self.layout.addWidget(self.add_masked_btn, 1, 1, 1, 1)
        self.layout.addWidget(self.name_btn, 1, 2, 1, 1)
        self.layout.addWidget(self.delete_btn, 1, 3, 1, 1)
        self.layout.addWidget(self.export_btn, 1, 4, 1, 1)

        self.already_used_dir = None

    def exportDialogShow(self):
        dialog = ExportDialog(self, self.data_manager, self.already_used_dir)
        result = dialog.exec()
        self.already_used_dir = dialog.file_info.absoluteDir()
        if result == QtWidgets.QDialog.Accepted:
            export(self.data_manager, **dialog.getSelectedData())

    def cellActivated(self, *args):
        self.name()

    def tableItemSelectionChangedConnect(self):
        self.table.itemSelectionChanged.connect(self.itemSelectionChanged)
    
    def tableItemSelectionChangedDisconnect(self):
        self.table.itemSelectionChanged.disconnect()

    def addMasked(self):
        objects = [object_.name for object_ in self.data_manager.objects]
        dialog = AddCopyMultipleDialog(self, objects)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            for index, checkbox in enumerate(dialog.checkboxes):
                if checkbox.isChecked():
                    self.data_manager.addObject(mask_object_index = index)

    def add(self):
        self.data_manager.addObject()

    def refreshTableStyleSheet(self):
        selected_indexes = self.table.selectedIndexes()
        if len(selected_indexes) < 1 or selected_indexes[0].row() >= len(self.data_manager.objects):
            return
        colorTable = colors.getColorTable(len(self.data_manager.objects))
        color = colorTable[self.table.selectedIndexes()[0].row()]
        self.table.setStyleSheet('QTableWidget::item:selected{{ background-color: rgba({},{},{}) }}\
            QCheckBox{{ background-color:rgba(1,1,1,0); }}'.format(color[0], color[1], color[2]))

    def itemSelectionChanged(self):
        if len(self.table.selectedIndexes()) > 0:
            self.data_manager.selectObject(self.table.selectedIndexes()[0].row())
        else:
            # This should never happen.
            print('Object Manager, itemSelectionChanged. No selection!')
            pass
        
    def contextMenu(self):
        # dont show any option if there is at most 1 object
        if len(self.data_manager.objects) < 2:
            return
        
        self.menu = QtGui.QMenu(self)
        
        invert_all = self.menu.addAction('invert all')
        invert_all.triggered.connect(lambda *args: self.invertAll(True))

        deinvert_all = self.menu.addAction('remove invert all')
        deinvert_all.triggered.connect(lambda *args: self.invertAll(False))
        
        deleteMultiple = self.menu.addAction('delete multiple')
        deleteMultiple.triggered.connect(self.deleteMultiple)

        self.menu.popup(QtGui.QCursor.pos())
        
    def deleteMultiple(self, _):
        _ = DeleteMultipleDialog(self, self.data_manager)

    def name(self):
        name = self.data_manager.objects[self.data_manager.object_selection].name
        new_name, ok = QtWidgets.QInputDialog.getText(self,
            'Rename',
            'Set a new name',
            text = name)
        if ok:
            self.data_manager.setObjectAttributes(self.data_manager.object_selection, {'name': new_name})

    def delete(self):
        last_object_for_current_source = 1 == len([o for o in self.data_manager.objects if o.source is self.data_manager.sources[self.data_manager.source_selection]])
        msg = 'Please confirm deletion of the selected Object.'
        if last_object_for_current_source:
            msg += ' The selected Object is the only Object belonging to its source. Deleting the Object will delete the source too.'
        ret = QtWidgets.QMessageBox.question(self, 'Confirm deletion', msg, QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        if ret == QtWidgets.QMessageBox.Ok:
            self.data_manager.removeObject()

    def invert(self, state, row):
        self.data_manager.setObjectAttributes(row, {'invert': state == QtCore.Qt.Checked}, prevent_object_manager_refresh = True, prevent_roiview_refresh = True)

    def invertAll(self, invert):
        for invert_checkbox in self.invert_checkboxes:
            invert_checkbox.setChecked(invert)

    def activeChanged(self, state, row):
        self.data_manager.setObjectAttributes(row, {'active': state == QtCore.Qt.Checked}, prevent_object_manager_refresh = True)

    def refreshView(self):
        # disconnect signals because this would trigger
        try:
            self.tableItemSelectionChangedDisconnect()
        except TypeError:
            pass

        selected = None
        if len(self.table.selectedIndexes()) > 0:
            selected = self.table.selectedIndexes()[0].row()

        colorTable = colors.getColorTable(len(self.data_manager.objects))
        
        self.invert_checkboxes = []
        self.table.setRowCount(0)
        for row, object_ in enumerate(self.data_manager.objects):
            self.table.insertRow(row)
            active = QtWidgets.QCheckBox()
            active.setChecked(object_.active)
            active.stateChanged.connect(lambda state, row = row: self.activeChanged(state, row))
            self.table.setCellWidget(row, 0, active)
            name = QtWidgets.QTableWidgetItem(object_.name)
            color = colorTable[row]
            name.setBackground(QtGui.QBrush(QtGui.QColor(color[0], color[1], color[2], alpha = 255)))
            self.table.setItem(row, 1, name)
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(object_.source.name))
            invert = QtWidgets.QCheckBox()
            invert.setChecked(object_.invert)
            invert.stateChanged.connect(lambda state, row = row: self.invert(state, row))
            self.invert_checkboxes.append(invert)
            self.table.setCellWidget(row, 3, invert)
        if selected is not None:
            self.table.selectRow(selected)
            self.refreshTableStyleSheet()

        # reconnect signals
        self.tableItemSelectionChangedConnect()

        objects_available = len(self.data_manager.objects) > 0
        self.name_btn.setEnabled(objects_available)
        self.delete_btn.setEnabled(objects_available)
        self.export_btn.setEnabled(objects_available)
        self.add_btn.setEnabled(len(self.data_manager.sources) > 0)
        self.add_masked_btn.setEnabled(objects_available)