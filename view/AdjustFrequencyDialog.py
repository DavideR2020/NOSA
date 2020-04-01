from PyQt5 import QtWidgets, QtCore
from scipy.interpolate import interp1d
from copy import deepcopy

class AdjustFrequencyDialog(QtWidgets.QDialog):

    """
    Dialog that lets the user activate or deactivate the AdjustFrequency feature for the currently selected source.

    A Checkbox represents the active state. 

    A StackedWidget displays the feature.
    """

    def __init__(self, parent, data_manager):

        QtWidgets.QDialog.__init__(self, parent, flags = QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowCloseButtonHint)

        self.data_manager = data_manager
        self.initial_active_state = None
        self.initial_parameters = None
        self.initial_method = None

        self.setWindowTitle('Adjust frequency')
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.active_checkbox = QtWidgets.QCheckBox('active')
        layout.addWidget(self.active_checkbox)

        self.feature_view = QtWidgets.QStackedWidget()
        layout.addWidget(self.feature_view)

        button_widget = QtWidgets.QWidget()
        layout.addWidget(button_widget)
        button_layout = QtWidgets.QHBoxLayout()
        button_widget.setLayout(button_layout)
        confirm_button = QtWidgets.QPushButton('Confirm')
        confirm_button.clicked.connect(self.confirm)
        button_layout.addWidget(confirm_button)
        cancel_button = QtWidgets.QPushButton('Cancel')
        cancel_button.clicked.connect(self.cancel)
        button_layout.addWidget(cancel_button)
    
    def connectActiveStateCheckbox(self):
        self.active_checkbox.stateChanged.connect(self.activeStateChanged)

    def disconnectActiveStateCheckbox(self):
        try:
            self.active_checkbox.stateChanged.disconnect()
        except:
            pass

    def activeStateChanged(self, state):
        active = state == QtCore.Qt.Checked
        self.af.active = active
        self.synchronizeActiveStateWithView()

    def synchronizeActiveStateWithView(self):
        if self.af.active:
            self.feature_view.setCurrentWidget(self.af)
            self.af.show()
        else:
            self.af.hide()
            self.af.clearData()
            self.feature_view.setCurrentIndex(-1)

    def confirm(self):
        self.accept()

        self.af.hide()

        # deactivate if adjusted freq is the same as original freq
        if self.af.getMethod().parameters['adjusted_frequency'] == self.af.input['object_source_af_params'][0]:
            # check if we have to cleardata and deactivate
            if self.af.active:
                self.af.clearData()
                self.af.active = False

        # no need to update when it was not active and is not active now
        was_inactive_and_is_inactive = (not self.af.active and not self.initial_active_state)
        if was_inactive_and_is_inactive:
            return

        # no need to update when everything is the same
        both_active = self.af.active and self.initial_active_state
        same_method = self.af.method_combo.currentText() == self.initial_method
        same_parameters = self.af.getMethod().parameters == self.initial_parameters[self.af.method_combo.currentText()]
        if both_active and same_method and same_parameters:
            return

        # refresh sourcemanager view
        self.data_manager.source_manager.refreshView()
        
        # set source attributes such that every pipeline affected is udpated
        self.data_manager.setSourceAttributes(attributes = {
            'adjusted_frequency': self.af.getMethod().parameters['adjusted_frequency'],
            'adjust_frequency_active': self.af.active,
            'adjust_frequency_method': self.af.method_combo.currentIndex()
        })

    def cancel(self):

        # correctly reset all parameters
        for name, parameters in self.initial_parameters.items():
            self.af.methods[name].parameters = parameters
        self.af.method_combo.setCurrentText(self.initial_method)
        self.af.active = self.initial_active_state
        self.af.hide()
        
        self.reject()

    def show(self):

        QtWidgets.QDialog.show(self)

        if self.data_manager.source_selection is None:
            self.done(QtWidgets.QDialog.Rejected)
            return

        self.af = self.data_manager.objects[self.data_manager.object_selection].pipeline._adjust_frequency
        self.af.inputConfiguration()
      
        self.disconnectActiveStateCheckbox()
        self.active_checkbox.setChecked(self.af.active)
        self.synchronizeActiveStateWithView()
        self.connectActiveStateCheckbox()
        
        self.initial_active_state = self.af.active
        self.initial_parameters = {name: deepcopy(method.parameters) for name, method in self.af.methods.items()}
        self.initial_method = self.af.method_combo.currentText()