from PyQt5 import QtWidgets, QtCore, QtGui

import time

class ExportDialog(QtWidgets.QDialog):

    """
    Dialog that lets the user select Objects and Features to export. Also,
    the user can set where to save the export and how to name it.
    """

    def __init__(self, parent, data_manager, already_used_dir = None):

        QtWidgets.QDialog.__init__(self, parent, flags = QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowCloseButtonHint)

        self.setWindowTitle('Export')
        self.setModal(True)

        # the object groupbox:
        # groupbox
        object_groupbox = QtWidgets.QGroupBox('Objects')
        object_groupbox.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        object_groupbox.customContextMenuRequested.connect(self.objectContextMenu)
        # groupbox > vboxlayout
        object_groupbox_layout = QtWidgets.QVBoxLayout()
        object_groupbox.setLayout(object_groupbox_layout)
        # groupbox > vboxlayout > scrollarea
        object_groupbox_scrollarea = QtWidgets.QScrollArea()
        object_groupbox_layout.addWidget(object_groupbox_scrollarea)
        # groupbox > vboxlayout > scrollarea > widget
        object_groupbox_scrollarea_widget = QtWidgets.QWidget()
        object_groupbox_scrollarea.setWidget(object_groupbox_scrollarea_widget)
        # groupbox > vboxlayout > scrollarea > widget > vboxlayout
        object_groupbox_scrollarea_widget_layout = QtWidgets.QVBoxLayout()
        object_groupbox_scrollarea_widget_layout.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        object_groupbox_scrollarea_widget.setLayout(object_groupbox_scrollarea_widget_layout)

        # filling the object groupbox
        # groupbox > vboxlayout > scrollarea > widget > vboxlayout > checkboxes
        self.object_checkboxes = []
        for object_ in data_manager.objects:
            checkbox = QtWidgets.QCheckBox(object_.name)
            checkbox.setChecked(True)
            checkbox.ensurePolished()
            object_groupbox_scrollarea_widget_layout.addWidget(checkbox)
            self.object_checkboxes.append(checkbox)

        checkbox_height = self.object_checkboxes[0].sizeHint().height()
        layout_spacing = object_groupbox_scrollarea_widget_layout.spacing()
        height = min(200, 2*layout_spacing + len(data_manager.objects)*(checkbox_height + 2*layout_spacing))
        object_groupbox_scrollarea_widget.setMinimumHeight(height)
        object_groupbox_scrollarea.setMinimumHeight(height)

        # the data groupbox
        data_groupbox = QtWidgets.QGroupBox('Data')
        data_groupbox.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        data_groupbox.customContextMenuRequested.connect(self.dataContextMenu)
        data_groupbox_layout = QtWidgets.QVBoxLayout()
        data_groupbox.setLayout(data_groupbox_layout)

        # filling the data groupbox
        self.data_cell_mean = QtWidgets.QCheckBox('raw data')
        self.data_cell_mean.setChecked(True)
        data_groupbox_layout.addWidget(self.data_cell_mean)
        self.data_processed = QtWidgets.QCheckBox('processed data')
        self.data_processed.setChecked(True)
        data_groupbox_layout.addWidget(self.data_processed)
        self.data_checkboxes = []
        for feature in data_manager.getCurrentPipeline().getCalculatingPipeline():
            checkbox = QtWidgets.QCheckBox(feature.name)
            checkbox.setChecked(True)
            data_groupbox_layout.addWidget(checkbox)
            self.data_checkboxes.append(checkbox)

        # the settings groupbox
        settings_groupbox = QtWidgets.QGroupBox('Settings')
        settings_groupbox_layout = QtWidgets.QVBoxLayout()
        settings_groupbox.setLayout(settings_groupbox_layout)

        # filling the settings groupbox
        self.settings_cc_only_inside_sources = QtWidgets.QCheckBox('CC only inside sources')
        self.settings_cc_only_inside_sources.setChecked(True)
        settings_groupbox_layout.addWidget(self.settings_cc_only_inside_sources)

        # the file groupbox
        file_groupbox = QtWidgets.QGroupBox('File')
        file_groupbox_layout = QtWidgets.QVBoxLayout()
        file_groupbox.setLayout(file_groupbox_layout)

        # filling the file groupbox
        if already_used_dir is None:
            self.file_info = QtCore.QFileInfo(self.getDefaultExportDialogSavefileName())
        else:
            self.file_info = QtCore.QFileInfo(already_used_dir, self.getDefaultExportDialogSavefileName())
        self.file_label = QtWidgets.QLabel(self.file_info.absoluteFilePath())
        file_groupbox_layout.addWidget(self.file_label)
        file_button = QtWidgets.QPushButton('Change File')
        file_button.clicked.connect(self.changeFile)
        file_groupbox_layout.addWidget(file_button)

        # the control groupbox
        control_groupbox = QtWidgets.QGroupBox()
        control_layout = QtWidgets.QHBoxLayout()
        control_groupbox.setLayout(control_layout)

        # filling the control groupbox
        export_button = QtWidgets.QPushButton('Export')
        export_button.clicked.connect(self.accept)
        control_layout.addWidget(export_button)
        cancel_button = QtWidgets.QPushButton('Cancel')
        cancel_button.clicked.connect(self.reject)
        control_layout.addWidget(cancel_button)

        # the dialog layout
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(object_groupbox)
        layout.addWidget(data_groupbox)
        layout.addWidget(settings_groupbox)
        layout.addWidget(file_groupbox)
        layout.addWidget(control_groupbox)

    def objectContextMenu(self):
        self.menu = QtGui.QMenu(self)

        selectAll = self.menu.addAction('Select All')
        selectAll.triggered.connect(lambda checked, select=True: self.objectSelectAll(select))

        deselectAll = self.menu.addAction('Deselect All')
        deselectAll.triggered.connect(lambda checked, select=False: self.objectSelectAll(select))

        self.menu.popup(QtGui.QCursor.pos())

    def objectSelectAll(self, select):
        for checkbox in self.object_checkboxes:
            checkbox.setChecked(select)

    def dataContextMenu(self):
        self.menu = QtGui.QMenu(self)

        selectAll = self.menu.addAction('Select All')
        selectAll.triggered.connect(lambda *args, select=True: self.dataSelectAll(select))

        deselectAll = self.menu.addAction('Deselect All')
        deselectAll.triggered.connect(lambda *args, select=False: self.dataSelectAll(select))

        self.menu.popup(QtGui.QCursor.pos())

    def dataSelectAll(self, select):
        for checkbox in [self.data_cell_mean, self.data_processed]:
            checkbox.setChecked(select)
        for checkbox in self.data_checkboxes:
            checkbox.setChecked(select)

    def changeFile(self):
        filename, ok = QtWidgets.QFileDialog.getSaveFileName(self, 'Export File', self.file_info.absoluteFilePath(), filter='(*.xlsx)')
        if ok and filename.endswith('.xlsx'):
            self.file_info = QtCore.QFileInfo(filename)
            self.file_label.setText(self.file_info.absoluteFilePath())
        
    def getDefaultExportDialogSavefileName(self):
        self.export_time = time.localtime()
        return time.strftime('%Y-%m-%d_%H-%M-%S_export.xlsx', self.export_time)

    def getSelectedData(self):
        objects = [cb.isChecked() for cb in self.object_checkboxes]
        data = [self.data_cell_mean.isChecked(), self.data_processed.isChecked()]
        for cb in self.data_checkboxes:
            data.append(cb.isChecked())
        return {
            'objects': objects,
            'data': data,
            'file_info': self.file_info,
            'export_time': self.export_time,
            'cc_only_inside_sources': self.settings_cc_only_inside_sources.isChecked()
        }
