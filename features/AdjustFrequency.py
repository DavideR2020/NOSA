import numpy as np
from scipy.interpolate import interp1d
from copy import deepcopy
from PyQt5 import QtWidgets, QtGui

from util.conf import af_params
from features.Feature import Feature

class AdjustFrequency(Feature):

    def __init__(self, data, parent=None, liveplot=None):
        
        Feature.__init__(self, 'Adjust Frequency', data, parent, liveplot, display_name_label=False)

        self.input = {'y': None, 'object_source_af_params': None}
        self.output = {'y': None}

        self.addMethod('Nearest Neighbour', af_params, self.nearestNeighbourWrapper)
        self.addMethod('Linear', af_params, self.linearWrapper)
        self.addMethod('Cubic', af_params, self.cubicWrapper)
        
        self.initMethodUI()
        self.initParametersUI()
        
        # disconnect the usual method because we dont want updates when the method is changed, only graphic updates.
        self.disconnectMethodCombo()
        self.method_combo.currentIndexChanged.connect(self.updateParametersUI)

    def inputConfiguration(self):
        af_params = self.input['object_source_af_params']
        if af_params is None:
            return
        # unpack the input
        original_freq, adjusted_freq, active, method = af_params
        # if we just deactivated self: cleardata
        if self.active and not active:
            self.clearData()
        # set active state
        self.active = active
        # set current method
        self.method_combo.setCurrentIndex(method)
        # set parameter
        self.getMethod().parameters['adjusted_frequency'] = adjusted_freq
        # refresh view
        self.setButtonLabel(self.getMethod())

    
    def initParametersUI(self):
        
        for method in self.methods.values():
            method.initButton('adjusted_frequency', self.adjustedFrequencyButton)
            self.setButtonLabel(method)

    def show(self):

        Feature.show(self)

        for method in self.methods.values():
            self.setButtonLabel(method)

        self.updateParametersUI()

    def setButtonLabel(self, method = None):

        if method is None or method not in self.methods.values():
            method = self.getMethod()

        adjusted_frequency = method.parameters['adjusted_frequency']
        method.getParametersGUI('adjusted_frequency').setText('Adjusted Frequency: {}'.format(adjusted_frequency))

    def adjustedFrequencyButton(self):
        af_params = self.input['object_source_af_params']
        if af_params is None:
            return

        default_frequency = af_params[0]

        old_frequency = self.getMethod().parameters['adjusted_frequency']
        
        new_frequency, ok = QtWidgets.QInputDialog.getDouble(
            self,
            'Adjust Frequency',
            (
                'Please set the frequency you want the processed data of this source to have (in Hz).\n\n'
                'Recording frequency is {} Hz.'
            ).format(default_frequency),
            value = old_frequency,
            decimals = 3,
            min = 0.001
        )
        if ok and old_frequency != new_frequency:
            self.getMethod().parameters['adjusted_frequency'] = new_frequency
            self.setButtonLabel()
    
    # call calculate and give the default frequency as parameter
    def nearestNeighbourWrapper(self, y, object_source_af_params, adjusted_frequency):
        return self.calculate(y, object_source_af_params[0], adjusted_frequency, 'nearest')

    def linearWrapper(self, y, object_source_af_params, adjusted_frequency):
        return self.calculate(y, object_source_af_params[0], adjusted_frequency, 'linear')

    def cubicWrapper(self, y, object_source_af_params, adjusted_frequency):
        return self.calculate(y, object_source_af_params[0], adjusted_frequency, 'cubic')

    def calculate(self, y, object_source_original_frequency, adjusted_frequency, method):
        old_x_len = len(y)
        interpolated = interp1d(range(old_x_len), y, kind = method)
        factor = adjusted_frequency / object_source_original_frequency
        new_x = np.linspace(0, old_x_len-1, num=round(factor * old_x_len), endpoint=True)
        return {'y': interpolated(new_x)}

    def updateLivePlot(self):
        pass