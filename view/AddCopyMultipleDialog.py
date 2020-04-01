from PyQt5 import QtWidgets, QtCore

class AddCopyMultipleDialog(QtWidgets.QDialog):
    """
    Dialog that lets the user choose from existing Objects. For every Object
    chosen, a new ROI shall be created.
    """

    def __init__(self, parent, existing_objects):

        QtWidgets.QDialog.__init__(self, parent, flags = QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowCloseButtonHint)

        self.setWindowTitle('Add copies')
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        label = QtWidgets.QLabel(
                'Please select Objects that the new ROIs will be copied from.\n\n'
                'Initially, the new ROIs will have the same position, active\n'
                'Features and Feature settings as the Objects you select here.\n'
                'If you select an Object that is not a ROI, different settings\n'
                'for the ROI position will be chosen.\n\n'
                'Please note that the new ROIs will belong to the currently\n'
                'selected Source, no matter what Objects you select to copy from.')
        layout.addWidget(label)

        # list of objects
        self.checkboxes = []
        for existing_object in existing_objects:
            checkbox = QtWidgets.QCheckBox(existing_object)
            checkbox.setChecked(False)
            layout.addWidget(checkbox)
            self.checkboxes.append(checkbox)

        # control buttons
        control_widget = QtWidgets.QWidget()
        control_layout = QtWidgets.QHBoxLayout()
        control_widget.setLayout(control_layout)
        layout.addWidget(control_widget)
        ok_button = QtWidgets.QPushButton('Ok')
        ok_button.clicked.connect(self.accept)
        control_layout.addWidget(ok_button)
        cancel_button = QtWidgets.QPushButton('Cancel')
        cancel_button.clicked.connect(self.reject)
        control_layout.addWidget(cancel_button)
