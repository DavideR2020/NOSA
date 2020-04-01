from PyQt5 import QtWidgets, QtCore, QtGui
from copy import deepcopy

class SetMultipleDialog(QtWidgets.QDialog):

    """
    Dialog that lets the user check for every object if the feature settings
    of the currently selected object should be copied.
    """

    def __init__(self, data_manager, index):
        """
        This creates and shows the modal dialog.
        """

        QtWidgets.QDialog.__init__(self, data_manager.pipeline_manager, flags = QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowCloseButtonHint)

        self.data_manager = data_manager
        self.index = index

        feature_name = self.data_manager.getCurrentPipeline().getPipeline()[index].name
        
        self.setWindowTitle('Copy {} Settings for multiple objects'.format(feature_name))
        self.setModal(True)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel(
            'Please set the checkboxes if you want the\n'
            '{} settings\n'
            'of the currently selected object to be copied to that object.\n\n'
            'Please note that only the selected method and chosen parameters\n'
            'will be copied, not the active state.'
            .format(feature_name)))
        self.activate_multiple_checkboxes = []
        self.defaults = []
        pipeline = self.data_manager.getCurrentPipeline()
        bs_feature = pipeline.getPipeline()[self.index] is pipeline._background_subtraction
        for object_ in data_manager.objects:
            checkbox = QtWidgets.QCheckBox(object_.name)
            checkbox.setChecked(False)
            self.defaults.append(False)
            checkbox.setVisible(not bs_feature or object_.source.filetype == 'tif')
            # checkbox for the currently selected object_ shall not be visible
            if data_manager.objects[data_manager.object_selection] is object_:
                checkbox.setVisible(False)
            layout.addWidget(checkbox)
            self.activate_multiple_checkboxes.append(checkbox)
        control_widget = QtWidgets.QWidget()
        layout.addWidget(control_widget)
        control_layout = QtWidgets.QHBoxLayout()
        control_widget.setLayout(control_layout)
        confirm_button = QtWidgets.QPushButton('Confirm')
        cancel_button = QtWidgets.QPushButton('Cancel')
        confirm_button.clicked.connect(lambda _: self.confirmClick())
        cancel_button.clicked.connect(lambda _: self.cancelClick())
        control_layout.addWidget(confirm_button)
        control_layout.addWidget(cancel_button)

        self.show()

    def confirmClick(self):
        """
        If the user did not change anything, shows an information QMessageBox that informs about it.

        If the user did change something, makes these changes and hides the dialog.
        """
        user_set = []
        for cb in self.activate_multiple_checkboxes:
            user_set.append(cb.isChecked())
        # return if nothing changed.
        if user_set == self.defaults:
            QtGui.QMessageBox.information(self, 'Nothing changed', 'The settings did not change.')
            return
        # get confirmation from user to change stuff
        result = QtGui.QMessageBox.question(self, 'Confirm settings', 'Please confirm the new settings.', QtGui.QMessageBox.Ok, QtGui.QMessageBox.Cancel)
        if result == QtGui.QMessageBox.Ok:
            # hide dialog
            self.hide()

            # get the affected objects
            affected_object_indices = [i for i, (user_set_, default) in enumerate(zip(user_set, self.defaults)) if user_set_ != default]

            # get the feature to copy from
            copy_from = self.data_manager.getCurrentPipeline().getPipeline()[self.index]

            for index in affected_object_indices:

                # get the feature to copy to
                copy_to = self.data_manager.objects[index].pipeline.getPipeline()[self.index]

                # set selected method without emitting the signal to update. 
                copy_to.disconnectMethodCombo()
                copy_to.method_combo.setCurrentIndex(copy_from.method_combo.currentIndex())
                copy_to.connectMethodCombo()
                # because we disconnected the signal, we need to update the parametersui manually
                copy_to.updateParametersUI()
                # because we called updateparametersui, backgroundsubtraction will show its rois. this is not wanted
                # for objects other than the selected.
                if copy_from is self.data_manager.getCurrentPipeline()._background_subtraction:
                    copy_to.undisplayPlots()

                # set parameters with preventing an update.
                for key, method in copy_to.methods.items():
                    method.setParameters(deepcopy(copy_from.methods[key].parameters), prevent_update = True)

                # update the pipeline. only do CC once (for last affected active object)
                self.data_manager.refreshPipeline(plot = True, object_index = index, start_with_feature = copy_to, ignore_cross_correlation = index != affected_object_indices[-1])

    def cancelClick(self):
        """ Hides the dialog. """
        self.hide()