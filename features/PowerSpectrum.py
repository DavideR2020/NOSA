from PyQt5 import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
import numpy as np
from copy import deepcopy

from util.conf import fs_fft_params
from util.functions import movingAverage
from features.Feature import Feature


class PowerSpectrum(Feature):

    def __init__(self, data, parent=None, liveplot=None):

        # Init Feature
        Feature.__init__(self, 'Power Spectrum', data, parent, liveplot)

        # data
        self.input = {'y':None, 'object_source_frequency':None}
        self.output = {'frequencies':None, 'psd':None, 'max power':None, 'max power frequency': None}

        # methods
        self.addMethod('Fast Fourier Transform', fs_fft_params, self.updateFourier)
        self.initMethodUI()
        self.initParametersUI()

    def initParametersUI(self):
        fft = self.methods['Fast Fourier Transform']
        fft.initSlider('smooth', slider_params=(3,30,10,1), updateFunc=self.update)
        fft.initSlider('threshold', slider_params=(0,100,1,0.01), updateFunc=self.update)
        fft.initButton('interval', self.setInterval)
        self.updateParametersUI()

    def setInterval(self):
        '''Set relevant area of Power Spectrum to show'''
        fft = self.methods['Fast Fourier Transform']
        a,b = fft.getParameters()['interval']
        mini,ok1 = QtWidgets.QInputDialog.getDouble(self,'Power Spectrum',"min", a)
        if ok1:
            maxi,ok2 = QtWidgets.QInputDialog.getDouble(self,'Power Spectrum',"max", b)
            if ok2:
                fft.setParameters({'interval':(mini,maxi)})
                self.update()

    def updateFourier(self, y, object_source_frequency, smooth, threshold, interval):
        y_detrended = y - np.mean(y)

        fft = np.fft.fft(y_detrended)
        fft = fft / len(fft)
        psd = np.abs(fft)**2
        freqs = np.fft.fftfreq(len(y_detrended), 1 / object_source_frequency)

        left_closest_index = np.argmin(np.abs(freqs - interval[0]))
        right_closest_index = np.argmin(np.abs(freqs - interval[1]))

        freqs = freqs[left_closest_index:right_closest_index+1]
        psd = psd[left_closest_index:right_closest_index+1]

        psd[psd < threshold] = 0
        psd = movingAverage(psd, window = smooth)
        
        if len(freqs) != len(psd):
            return {
                'frequencies': None,
                'psd': None,
                'max power': None,
                'max power frequency': None
            }
        peak = np.argmax(psd)
        peak_frequency = freqs[peak]
        peak = psd[peak]
        return {'frequencies':freqs, 'psd':psd, 'max power': peak, 'max power frequency': peak_frequency}

    def updateLivePlot(self):
        frequencies = self.output['frequencies']
        psd = self.output['psd']
        if frequencies is None or psd is None:
            self.undisplayPlots()
        else:
            self.liveplot.setData('PSD', frequencies, psd)

    def clear(self):
        self.clearData()
        self.undisplayPlots()

    def undisplayPlots(self):
        Feature.undisplayPlots(self)
        self.liveplot.setData('PSD', [], [])
