from PyQt5 import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
import numpy as np
from scipy import signal

from util.conf import sg_savitzky_golay_params, sg_moving_average_params, sg_butterworth_params
from util.functions import movingAverage, butter_lowpass_filter
from features.Feature import Feature

class Smoothing(Feature):

    def __init__(self, data, parent=None, liveplot=None):

        # Init Feature
        Feature.__init__(self, 'Smoothing', data, parent, liveplot)

         # data
        self.input = {'y':None, 'object_source_frequency':None}
        self.output = {'y':None, 'noise_std': None}

        # methods
        # 1 Savitzky Golay
        self.addMethod('Savitzky Golay', sg_savitzky_golay_params, self.updateSGData)
        # 2 Moving Average
        self.addMethod('Moving Average', sg_moving_average_params, self.movingAverageWrapper)
        # 3 Butterworth
        self.addMethod('Butterworth', sg_butterworth_params, self.butter_lowpass_filter_wrapper)

        self.initMethodUI()
        self.initParametersUI()

    def initParametersUI(self):
        updateFunc = self.update
        #sg
        self.methods['Savitzky Golay'].initSlider('window', slider_params=(3,101,1,1), updateFunc=updateFunc)
        self.methods['Savitzky Golay'].initSlider('polyorder', slider_params=(2,6,1,1), updateFunc=updateFunc)
        #ma
        self.methods['Moving Average'].initSlider('window', slider_params=(3,101,1,1), updateFunc=updateFunc)
        #butter
        self.methods['Butterworth'].initSlider('highcut', slider_params=(1,125,1,1), updateFunc=updateFunc)
        self.setButterworthMaxHighcut()
        self.methods['Butterworth'].initSlider('order', slider_params=(2,6,1,1), updateFunc=updateFunc)
        # update GUI
        self.updateParametersUI()

    def inputConfiguration(self):
        if self.input['object_source_frequency'] is not None:
            self.setButterworthMaxHighcut()

    def setButterworthMaxHighcut(self):
        if self.input['object_source_frequency'] is None:
            return
        freq = self.input['object_source_frequency']
        if freq % 2 == 0:
            max_highcut = int(freq / 2) - 1
        else:
            max_highcut = int(freq / 2) # rounds down

        curr_highcut = self.methods['Butterworth'].getParameters()['highcut']
        if curr_highcut > max_highcut:
            self.methods['Butterworth'].getParametersGUI('highcut').setValue(max_highcut)
        
        self.methods['Butterworth'].getParametersGUI('highcut').setAbsolutes(1, max_highcut)
        self.methods['Butterworth'].getParametersGUI('highcut').setMaximum(max_highcut)
        

    def movingAverageWrapper(self, y, object_source_frequency, window=11):
        y_smoothed = movingAverage(y, window)
        noise = y - y_smoothed
        return {'y': y_smoothed, 'noise_std': np.std(noise)}

    def butter_lowpass_filter_wrapper(self, y, object_source_frequency, highcut, order):
        y_smoothed = butter_lowpass_filter(y, object_source_frequency, highcut, order)
        noise = y - y_smoothed
        return {'y': y_smoothed, 'noise_std': np.std(noise)}

    def updateSGData(self, y, object_source_frequency, polyorder, window):
        """Savitzky Golay Filtering"""

        if window%2 == 0:
            window+=1
        if window > polyorder:
            sg = signal.savgol_filter(y, window, polyorder)
        else:
            sg = y

        noise = y - sg

        return {'y': sg, 'noise_std': np.std(noise)}

    def updateLivePlot(self):
        pass