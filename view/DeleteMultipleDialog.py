from PyQt5 import QtWidgets, QtCore, QtGui

class DeleteMultipleDialog(QtWidgets.QDialog):

    def __init__(self, parent, data_manager):

        QtWidgets.QDialog.__init__(self, parent, flags = QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowCloseButtonHint)

        self.data_manager = data_manager

        self.setWindowTitle('Delete multiple objects')
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(QtWidgets.QLabel('Please check everything you want to delete.'))
        self.checkboxes = []
        for object_ in self.data_manager.objects:
            checkbox = QtWidgets.QCheckBox(object_.name)
            checkbox.setChecked(False)
            layout.addWidget(checkbox)
            self.checkboxes.append(checkbox)
        control_widget = QtWidgets.QWidget()
        layout.addWidget(control_widget)
        control_layout = QtWidgets.QHBoxLayout()
        control_widget.setLayout(control_layout)
        delete_button = QtWidgets.QPushButton('Delete')
        cancel_button = QtWidgets.QPushButton('Cancel')
        delete_button.clicked.connect(self.delete)
        cancel_button.clicked.connect(self.cancel)
        control_layout.addWidget(delete_button)
        control_layout.addWidget(cancel_button)

        self.show()

    def cancel(self):
        self.reject()

    def delete(self):
        delete = [checkbox.isChecked() for checkbox in self.checkboxes]
        # if nothing was selected: dont do anything.
        if not any(delete):
            return
        # ask the user for confirmation
        string = 'Please confirm the deletion.'
        # check if a source would be deleted by this operation and if so, add another message
        for source in self.data_manager.sources:
            if 0 == len([idx for idx,object_ in enumerate(self.data_manager.objects) if not delete[idx] and object_.source is source]):
                string += ' The selection you took will result in the deletion of at least one source because the remaining Object(s) of that source will be removed.'
                break
        result = QtGui.QMessageBox.question(self, 'Confirm deletion', string, QtGui.QMessageBox.Ok, QtGui.QMessageBox.Cancel)
        if result == QtGui.QMessageBox.Ok:
            # hide the dialog
            self.accept()

            if not delete[self.data_manager.object_selection]:
                # if the selected object will not be deleted, we select it afterwards again.
                # the index will be the index from before - amount of deleted objects before that index
                selection_after = self.data_manager.object_selection
                selection_after -= sum(delete[:selection_after])
            else:
                # check if selected source will have any objects left
                objects_for_this_source_after_removal = [i for i, o in enumerate(self.data_manager.objects)
                    if o.source is self.data_manager.objects[self.data_manager.object_selection].source
                    and not delete[i]]
                if len(objects_for_this_source_after_removal) > 0:
                    # select the last added object of this source that will not be removed
                    selection_after = max(objects_for_this_source_after_removal)
                    selection_after -= sum(delete[:selection_after])
                else:
                    # select the last added object.
                    selection_after = -1
                # selected object will be removed: we need to check if we have to undisplay backgroundsubtraction and baseline
                background_subtraction = self.data_manager.getCurrentPipeline()._background_subtraction
                if background_subtraction.active:
                    background_subtraction.undisplayPlots()
                baseline = self.data_manager.getCurrentPipeline()._baseline
                if baseline.active:
                    baseline.undisplayPlots()

            last_deletion_index = max([i for i, d in enumerate(delete) if d])

            for index, delete_ in enumerate(delete):
                if delete_:
                    # remove object at index - amount of deleted objects before that index
                    self.data_manager.removeObject(remove_object_index = index - sum(delete[:index]),
                        refresh = index == last_deletion_index,
                        object_selection_after = selection_after,
                        prevent_feature_undisplay = True)