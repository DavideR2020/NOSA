from PyQt5 import QtWidgets, QtCore, QtGui

from view.Plot import Plot

class ActivateMultipleDialog(QtWidgets.QDialog):

    """
    Dialog that lets the user check for every object if the feature should be 
    activated or deactivated. 
    """
    
    def __init__(self, data_manager, index):
        """
        This creates and shows the modal dialog.
        """

        QtWidgets.QDialog.__init__(self, data_manager.pipeline_manager, flags = QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowCloseButtonHint)

        self.data_manager = data_manager
        self.index = index

        feature_name = self.data_manager.getCurrentPipeline().getPipeline()[index].name
        
        self.setWindowTitle('Activate / Deactivate {} for multiple objects'.format(feature_name))
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel('Please set the checkboxes however you want {} to be enabled or disabled.'.format(feature_name)))
        self.activate_multiple_checkboxes = []
        self.defaults = []
        pipeline = data_manager.getCurrentPipeline()
        bs_feature = pipeline.getPipeline()[self.index] is pipeline._background_subtraction
        for object_ in data_manager.objects:
            checkbox = QtWidgets.QCheckBox(object_.name)
            checkbox.setChecked(object_.pipeline.getPipeline()[self.index].active)
            self.defaults.append(object_.pipeline.getPipeline()[self.index].active)
            checkbox.setVisible(not bs_feature or object_.source.filetype == 'tif')
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

    def cancelClick(self):
        """ Hides the dialog. """
        self.hide()

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

            # get objects whose feature changed
            indices_that_changed = [i for i, (user_set_, default) in enumerate(zip(user_set, self.defaults)) if user_set_ != default]

            for index in indices_that_changed:
                # get the feature
                feature = self.data_manager.objects[index].pipeline.getPipeline()[self.index]

                # set the new active state
                feature.active = user_set[index]

                # clear the feature data if its deactivated
                if not user_set[index]:
                    feature.clearData()

                # update every objects pipeline. only calculate cc once (for the last object).
                self.data_manager.refreshPipeline(plot = True, object_index = index, start_with_feature = feature, ignore_cross_correlation = index != indices_that_changed[-1])

            # find out what plot to reset:
            # get current feature
            feature = self.data_manager.getCurrentPipeline().getPipeline()[self.index]
            # get its liveplot
            reset_plot = feature.liveplot
            # if its not a Plot but something different (None or something completely different, e.g. baseline has a tupel as liveplot):
            # we set it to -1. this way, resetComparePlots calls its functions with -1 and they instantly return without doing anything else
            if not isinstance(reset_plot, Plot):
                reset_plot = -1
            # reset that plot.
            self.data_manager.plot_manager.resetComparePlots(reset_plot)

            # if the selected object got changed, we need to refresh the pipelineview and resize the plots
            if self.data_manager.object_selection in indices_that_changed:
                self.data_manager.pipeline_manager.refreshView()
                if feature.active:
                    self.data_manager.plot_manager.refreshPlots(self.index)
                else:
                    self.data_manager.plot_manager.refreshPlots()
