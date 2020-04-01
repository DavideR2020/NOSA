from PyQt5 import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
import numpy as np
from util.conf import es_params

from util.functions import movingAverage
from features.Feature import Feature
import math

class EventShape(Feature):

    def __init__(self, data, parent=None, liveplot=None):

        # Init Feature
        Feature.__init__(self, 'Event Shape', data, parent, liveplot)

         # data
        self.input = {'y':None, 'burst_time':None, 'spike_time':None, 'object_source_frequency':None}
        self.output = {'shapes':None, 'mean shape':None, 'mean shape smoothed':None}

        ## METHODS ##

        # 1 Mean Amplitude
        self.addMethod('Spike Shape', es_params, self.spikeShapeCalculation)
        self.addMethod('Burst Shape', es_params, self.burstShapeCalculation)

        self.initMethodUI()
        self.initParametersUI()

    def initParametersUI(self):
        for method in self.methods.values():
            method.initSlider('smooth', slider_params=(3,100,10,1), updateFunc=self.update)
            method.initButton('interval', self.changeShapeSize)
            
        self.updateParametersUI()

    def inputConfiguration(self):
        left, right = self.getMethod().parameters['interval']
        # get intervalsize in frames
        intervalSize = math.floor((left + right - 1) * self.input['object_source_frequency'] / 1000.0)
        self.getMethod().getParametersGUI('smooth').setAbsolutes(3, intervalSize)
        self.getMethod().getParametersGUI('smooth').setMaximum(intervalSize)

    def changeShapeSize(self):
        freq = self.input['object_source_frequency']
        method = self.getMethod()
        left, right = method.parameters['interval']
        leftsize,ok1 = QtWidgets.QInputDialog.getInt(self,"Shape Interval","Left handside area of spike/burst peak that are supposed to be displayed (in ms)", left)
        if ok1:
            rightsize,ok2 = QtWidgets.QInputDialog.getInt(self,"Shape Interval","Right handside area of spike/burst peak that are supposed to be displayed (in ms)", right)
            if ok2:
                method.setParameters({'interval':(leftsize,rightsize)})
                # change values from milliseconds to frames for max smooth
                leftframes = round(leftsize * freq / 1000.0)
                rightframes = round(rightsize * freq / 1000.0)
                method.getParametersGUI('smooth').setMaximum(rightframes + leftframes - 1)
                self.update()

    def updateLivePlot(self):
        meanShape = self.output['mean shape']
        meanShapeSmoothed = self.output['mean shape smoothed']
        frequency = self.input['object_source_frequency']
        if meanShape is None or meanShapeSmoothed is None or frequency is None:
            self.undisplayPlots()
        else:
            amount = len(meanShape)
            left,right = self.getMethod().getParameters()['interval']
            seconds_range = np.linspace(-left / 1000.0, right / 1000.0, num=amount)
            self.liveplot.setData('shape', seconds_range, meanShape)
            self.liveplot.setData('smoothed shape', seconds_range, meanShapeSmoothed)

    def clear(self):
        self.clearData()
        self.undisplayPlots()

    def undisplayPlots(self):
        Feature.undisplayPlots(self)
        self.liveplot.setData('shape', [], [])
        self.liveplot.setData('smoothed shape', [], [])

    def burstShapeCalculation(self, y, burst_time, spike_time, object_source_frequency, smooth, interval):
        return self.eventShapeCalculation(y, burst_time, object_source_frequency, smooth, interval)

    def spikeShapeCalculation(self, y, burst_time, spike_time, object_source_frequency, smooth, interval):
        return self.eventShapeCalculation(y, spike_time, object_source_frequency, smooth, interval)

    def eventShapeCalculation(self, y, time, object_source_frequency, smooth, interval):
        '''Update Spike Shapes'''

        if time is None or isinstance(time, bool):
            return {
                'shapes': None,
                'mean shape': None,
                'mean shape smoothed': None
            }

        left,right = interval
        left = round(left * object_source_frequency / 1000.0)
        right = round(right * object_source_frequency / 1000.0)
        interval = left,right
        shapes = self.getShapes(y, time, interval, object_source_frequency)
        meanShape = self.getMeanShape(shapes)
        meanShapeSmoothed = movingAverage(meanShape, window=smooth)

        return {'shapes': shapes, 'mean shape': meanShape, 'mean shape smoothed': meanShapeSmoothed}

    # ---------------------------------------------------------
    #   Headless / Functional
    # ---------------------------------------------------------

    def getShapes(self, signal, peaks, interval, freq):
        '''
        Cut out spike/burst shapes from the signal
        signal (ndarray) : signal from where the spikes are subtracted
        peaks (ndarray) : time points of spike/burst peaks in seconds
        interval (tuple) : area before and after peak in seconds
        '''
        n = len(peaks)
        m = len(signal)
        #peaks = (peaks*freq).astype(int)    # from seconds to frames
        # start and end point
        backward, forward = interval
        shapes = []
        for peak in peaks:
            start = peak - backward
            end = peak + forward
            # if start is negative, repeat the first value of signal
            if start < 0:
                    diff_start = np.repeat(signal[0], abs(start))
                    shape = np.concatenate([diff_start, signal[:end]])
            # if end is bigger than signal length, repeat last value of signal
            elif end >= m:
                    diff_end = np.repeat(signal[m-1], (end-m))
                    shape = np.concatenate([signal[start:],diff_end])
            else:
                shape = signal[start:end]
            shapes.append(shape)
        return np.array(shapes)


    def getMeanShape(self, shapes):
        '''
        Calculate mean spike/burst shape
        shapes (ndarray) : spike/burst shapes
        '''
        return shapes.mean(axis=0)
