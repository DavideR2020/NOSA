from PyQt5 import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
import numpy as np
from copy import deepcopy
from scipy.signal import savgol_filter
from scipy.optimize import curve_fit

from util.conf import sd_params, bd_params
from util.functions import movingAverage, func_exp
from features.Feature import Feature



# ================
# burst detection
# ================
class BurstDetection(Feature):

    def __init__(self, data, parent=None, liveplot=None):

        # Init Feature
        Feature.__init__(self, 'Burst Detection', data, parent, liveplot)

         # data
        self.input = {'y':None, 'object_source_frequency': None, 'object_noise_std': None}
        self.output = {'start':None, 'end':None, 'time':None, 'amplitude':None, 'duration':None, 'train':None, 'burst frequency':None, 'mean amplitude':None, 'mean duration':None, 'tPeak': None, 'aMax': None, 'τDecay': None, 'mean tPeak': None, 'mean aMax': None, 'mean τDecay': None}

        # dialog for averages
        self.showBtn = QtWidgets.QPushButton('Show quantities')
        self.showBtn.clicked.connect(self.showQuantities)
        self.layout.addWidget(self.showBtn)
        self.dialog = QtWidgets.QDialog(self, flags = QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowCloseButtonHint)
        self.dialog.setWindowTitle(self.name + ' -- Quantities')
        self.dialog_table = QtWidgets.QTableWidget(self.dialog)
        self.dialog_table.horizontalHeader().hide()
        self.dialog_table.verticalHeader().hide()
        self.dialog_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.dialog_table.setRowCount(6)
        self.dialog_table.setColumnCount(2)
        self.dialog_table.setItem(0, 0, QtWidgets.QTableWidgetItem('mean amplitude'))
        self.dialog_table.setItem(1, 0, QtWidgets.QTableWidgetItem('mean duration (s)'))
        self.dialog_table.setItem(2, 0, QtWidgets.QTableWidgetItem('burst frequency (#bursts / s)'))
        self.dialog_table.setItem(3, 0, QtWidgets.QTableWidgetItem('mean tPeak (s)'))
        self.dialog_table.setItem(4, 0, QtWidgets.QTableWidgetItem('mean aMax'))
        self.dialog_table.setItem(5, 0, QtWidgets.QTableWidgetItem('mean τDecay'))
        self.dialog_layout = QtWidgets.QGridLayout(self.dialog)
        self.dialog.setLayout(self.dialog_layout)
        self.dialog.layout().addWidget(self.dialog_table)

        ## METHODS ##
        self.addMethod('Threshold', bd_params, self.burstUpdate)

        self.initMethodUI()
        self.initParametersUI()

    def showQuantities(self):
        if (self.output['mean amplitude'] is None or self.output['mean duration'] is None or self.output['burst frequency'] is None or self.output['mean tPeak'] is None or self.output['mean aMax'] is None or self.output['mean τDecay'] is None or self.input['object_source_frequency'] is None):
            return
        
        self.dialog_table.setItem(0, 1, QtWidgets.QTableWidgetItem(str(round(self.output['mean amplitude'], 4))))
        self.dialog_table.setItem(1, 1, QtWidgets.QTableWidgetItem(str(round(self.output['mean duration'] / self.input['object_source_frequency'], 4))))
        self.dialog_table.setItem(2, 1, QtWidgets.QTableWidgetItem(str(round(self.output['burst frequency'], 4))))
        self.dialog_table.setItem(3, 1, QtWidgets.QTableWidgetItem(str(round(self.output['mean tPeak'] / self.input['object_source_frequency'], 4))))
        self.dialog_table.setItem(4, 1, QtWidgets.QTableWidgetItem(str(round(self.output['mean aMax'], 4))))
        self.dialog_table.setItem(5, 1, QtWidgets.QTableWidgetItem(str(round(self.output['mean τDecay'], 4))))

        self.dialog.exec()

##########################################################################################

    def initParametersUI(self):
        bd = self.methods['Threshold']

        threshold_lambda = lambda _: self.setThresholdState()

        bd.initCheckbox('dynamic_threshold', updateFunc=threshold_lambda, label='dynamic threshold')
        bd.initCheckbox('relative_threshold', updateFunc=threshold_lambda, label='relative threshold')
        bd.initSlider('dynamic_smooth', slider_params=(3,600,10,1), updateFunc=self.update, label='smooth')
        bd.initSlider('absolute_amplitude', slider_params=(-500,500,1,0.01), updateFunc=self.update, label='minimal amplitude')
        bd.initRadioButtons('relative_amplitude_type', ['use std of noise', 'use std of data'], updateFunc=threshold_lambda)
        bd.initSlider('relative_amplitude', slider_params=(-50,50,1,0.1), updateFunc=self.update, label='relative amplitude (factor for std)')
        bd.initSlider('absolute_base', slider_params=(-100,100,1,0.01), updateFunc=self.update, label='minimal base')
        bd.initRadioButtons('relative_base', ['minimal base: median', 'minimal base: mean', 'minimal base: 0'], updateFunc=threshold_lambda)
        bd.initSlider('duration', slider_params=(10,400,1,1), updateFunc=self.update, label='minimal duration (ms)')
        bd.initComboBox('phase', ['depolarization', 'hyperpolarization'], updateFunc=self.phase_changed, label='Phase')

        self.setThresholdState(update = False)

        self.updateParametersUI()

    def phase_changed(self):
        bd = self.methods['Threshold']
        phase = bd.getParametersGUI('phase').layout().itemAt(1).widget().currentText()
        phase_before = bd.getParameters()['phase']
        # if different phase as before: multiply threshold parameters by -1
        if phase_before != phase:
            prevent_update_before = bd.prevent_update
            bd.prevent_update = True
            absolute_amplitude = bd.getParameters()['absolute_amplitude']
            bd.getParametersGUI('absolute_amplitude').setValue(-1 * absolute_amplitude)
            relative_amplitude = bd.getParameters()['relative_amplitude']
            bd.getParametersGUI('relative_amplitude').setValue(-1 * relative_amplitude)
            absolute_base = bd.getParameters()['absolute_base']
            bd.getParametersGUI('absolute_base').setValue(-1 * absolute_base)
            bd.prevent_update = prevent_update_before
        bd.setParameters({'phase': phase})
        self.update()

    def updateLivePlot(self):

        y = self.input['y']
        seconds_range = self.data.sources[self.data.source_selection].secondsRange()
        
        # threshold visualization
        self.liveplot.setData('minimal amplitude', seconds_range, self.th1)
        self.liveplot.setData('minimal base', seconds_range, self.th2)

        # plot input data
        self.liveplot.setData('y', seconds_range, y)
        
        # plot train
        if self.output['train'] is not None and len(self.output['train']) > 0:
            diff = max(y) - min(y)
            train_height = diff / 6
            self.liveplot.setData('train', seconds_range, train_height * self.output['train'])
        else:
            # can not call self.undisplayPlots because that would undisplay other data too, like y and thresholds
            # this is why we undisplay the train manually
            self.liveplot.setData('train', [], [])
            # and then Feature.undisplayPlots method which cares about the compare plots
            Feature.undisplayPlots(self)

        
        start = self.output['start']
        end = self.output['end']
        amplitude = self.output['amplitude']
        if start is not None and end is not None and amplitude is not None and len(start) == len(end) == len(amplitude):
            self.liveplot.setData('train start symbols', [seconds_range[t] for t in self.output['start']], amplitude)
            self.liveplot.setData('train end symbols', [seconds_range[t] for t in self.output['end']], amplitude)
        else:
            self.liveplot.setData('train start symbols', [], [])
            self.liveplot.setData('train end symbols', [], [])


    def clear(self):
        self.clearData()
        self.undisplayPlots()

    def undisplayPlots(self):
        Feature.undisplayPlots(self)
        self.liveplot.setData('minimal amplitude', [], [])
        self.liveplot.setData('minimal base', [], [])
        self.liveplot.setData('y', [], [])
        self.liveplot.setData('train', [], [])
        self.liveplot.setData('train start symbols', [], [])
        self.liveplot.setData('train end symbols', [], [])

##########################################################################################

    def show(self):
        QtWidgets.QWidget.show(self)
        self.setThresholdState(update=False)

    def setThresholdState(self, update=True):
        bd = self.methods['Threshold']

        if bd.getParametersGUI('dynamic_threshold').isChecked():
            bd.setParameters({'dynamic_threshold':True})
            bd.getParametersGUI('dynamic_smooth').show()
        else:
            bd.setParameters({'dynamic_threshold':False})
            bd.getParametersGUI('dynamic_smooth').hide()

        if bd.getParametersGUI('relative_threshold').isChecked():
            bd.setParameters({'relative_threshold': True})
            bd.getParametersGUI('absolute_amplitude').hide()
            for btn in bd.getParametersGUI('relative_amplitude_type'):
                btn.show()
                if btn.isChecked():
                    bd.setParameters({'relative_amplitude_type': btn.text()})
            bd.getParametersGUI('relative_amplitude').show()
            bd.getParametersGUI('absolute_base').hide()
            for btn in bd.getParametersGUI('relative_base'):
                btn.show()
                if btn.isChecked():
                    bd.setParameters({'relative_base': btn.text()})
        else:
            bd.setParameters({'relative_threshold': False})
            bd.getParametersGUI('absolute_amplitude').show()
            for btn in bd.getParametersGUI('relative_amplitude_type'):
                btn.hide()
            bd.getParametersGUI('relative_amplitude').hide()
            bd.getParametersGUI('absolute_base').show()
            for btn in bd.getParametersGUI('relative_base'):
                btn.hide()

        self.layout.update()
        if update:
            self.update()

    def burstUpdate(self, y, object_source_frequency, object_noise_std, dynamic_threshold, relative_threshold, dynamic_smooth, absolute_amplitude, relative_amplitude_type, relative_amplitude, absolute_base, relative_base, duration, phase):

        x = np.arange(len(y))

        isDepolarization = phase == 'depolarization'

        # if there is no noise std, we calculate a default noise and its std
        if object_noise_std == 0:
            noise = y - savgol_filter(y, 5, 3)
            object_noise_std = np.std(noise)

        # thresholds
        if relative_threshold:
            amplitude = relative_amplitude * (object_noise_std if relative_amplitude_type == 'use std of noise' else np.std(y))
            if relative_base == 'minimal base: median':
                base = np.median(y)
            elif relative_base == 'minimal base: mean':
                base = np.mean(y)
            else:
                base = 0
        else:
            base = absolute_base
            amplitude = absolute_amplitude

        if dynamic_threshold:
            self.th1 = movingAverage(y, window=dynamic_smooth)+amplitude
            self.th2 = movingAverage(y, window=dynamic_smooth)+base
        else:
            self.th1 = np.full(len(y), amplitude, dtype=float)
            self.th2 = np.full(len(y), base, dtype=float)

        # change duration from ms to frames
        duration = object_source_frequency * duration / 1000.0 

        # get bursts (starts,ends) as frame index
        bursts = self.burstDetection(y, self.th1, self.th2, duration, isDepolarization)

        # get meta data
        if len(bursts[0]) is not 0:
            
            start = bursts[0]
            end = bursts[1]
            n = len(start)
            burstStart = np.array(x[start])
            burstEnd = np.array(x[end])
            peak = [s+(np.argmax(y[s:e]) if isDepolarization else np.argmin(y[s:e])) for s,e in np.nditer([start,end])]
            amplitude = y[peak]
            duration = burstEnd-burstStart
            tPeak = np.zeros(len(peak), dtype=np.int32)
            np.subtract(peak, start, out = tPeak)
            aMax = amplitude - self.th2[peak]
            tDecay = np.zeros_like(aMax)
            i = 0
            for decay_start,decay_end in np.nditer([peak, burstEnd]):
                decay_data = y[decay_start:decay_end]
                if len(decay_data) < 3:
                    tDecay[i] = np.nan
                else:
                    try:
                        x_data = np.linspace(0, (decay_end-decay_start)/object_source_frequency, decay_end-decay_start)
                        popt, _ = curve_fit(func_exp, xdata=x_data, ydata=decay_data, p0=[2.5, 15])
                        tDecay[i] = 1/popt[1]
                    except:
                        tDecay[i] = np.nan
                i += 1

            return {
                'start': burstStart,
                'end': burstEnd,
                'time': x[peak],
                'amplitude': amplitude,
                'duration': duration,
                'train': self.getBurstTrain(bursts, len(y)),
                'burst frequency': n*object_source_frequency/x[-1],
                'mean amplitude': amplitude.mean(),
                'mean duration': duration.mean(),
                'tPeak': tPeak,
                'aMax': aMax,
                'τDecay': tDecay,
                'mean tPeak': tPeak.mean(),
                'mean aMax': aMax.mean(),
                'mean τDecay': tDecay[~np.isnan(tDecay)].mean()
            }
        else:
            return {
                'start': np.array([]),
                'end': np.array([]),
                'time': np.array([]),
                'amplitude': np.array([]),
                'duration': np.array([]),
                'train': np.zeros(len(y)-1),
                'burst frequency': 0,
                'mean amplitude': np.nan,
                'mean duration': np.nan,
                'tPeak': np.array([]),
                'aMax': np.array([]),
                'τDecay': np.array([]),
                'mean tPeak': np.nan,
                'mean aMax': np.nan,
                'mean τDecay': np.nan
            }

#--------------------------------------------------------#
#   Functional
#--------------------------------------------------------#

    def burstDetection(self, y, amplitude, base, duration, isDepolarization):
        """
        y: signal
        amplitude: upper threshold to decide whether there is a burst or not
        base: lower threshold to determine the start and end of the burst
        duration: amount of frames that a burst's length must be at minimum
        isDepolarization: defines if depolarization or hyperpolarization 
                should be detected

        returns tuple of arrays: start frames and end frames of the bursts

        definition of burst: one point must be at least the upper threshold (amplitude). 
        the start of the burst is the intersection of the signal (y) with the
        lower threshold (base) on the left of the point above the upper threshold.
        the end of the burst is the intersection of the signal (y) with the 
        lower threshold (base) on the right of the point above the upper threshold.
        the burst only counts if it is at least duration long.
        """
        bursts = ([],[])
        n = len(y)
        i = 1
        while (i < n-2):
            if (isDepolarization and y[i] > amplitude[i]) or (not isDepolarization and y[i] < amplitude[i]):
                start, end, error = self.burstBorderDetection(y, base, i, 0 if len(bursts[0]) == 0 else bursts[1][-1]+1, isDepolarization)
                if end-start > duration and not error:
                    bursts[0].append(start)
                    bursts[1].append(end)
                i = end + 2
            else:
                i += 1
        return bursts

    def burstBorderDetection(self, y, base, i, leftborder, isDepolarization):
        """
        y: signal
        base: lower threshold to determine start and end of burst
        i: frame of the point above the upper threshold
        leftborder: the most-left border the burst can start at
        isDepolarization: defines if depolarization or hyperpolarization 
                should be detected

        returns the intersections of the signal with the base on both sides
        of the point above the upper threshold, and an error-boolean. this 
        is True when start/end are not below the base, but we stopped because
        of the borders.
        """
        n = len(y) - 1
        start = i - 1
        while (start > leftborder and ((isDepolarization and y[start] >= base[start]) or (not isDepolarization and y[start] <= base[start]))):
            start -= 1
        end = i + 1
        while (end < n and ((isDepolarization and y[end] >= base[end]) or (not isDepolarization and y[end] <= base[end]))):
            end += 1
        error = (isDepolarization and (y[start] >= base[start] or y[end] >= base[end])) or (not isDepolarization and (y[start] <= base[start] or y[end] <= base[end]))
        return (start, end, error)

    def getBurstTrain(self, bursts, n):
        burst_train = np.zeros(n-1,dtype=float)
        s,e = bursts
        for i in range(len(s)):
            burst_train[s[i]:e[i]] = 1
        return burst_train


# ================
# spike detection
# ================

class SpikeDetection(Feature):

    def __init__(self, data, parent=None, liveplot=None):

        # Init Feature
        Feature.__init__(self, 'Spike Detection', data, parent, liveplot)

         # data
        self.input = {'y':None, 'object_source_frequency': None, 'object_noise_std': None}
        self.output = {'time':None, 'amplitude':None, 'train':None, 'spike frequency':None, 'mean amplitude':None, 'τDecay': None, 'mean τDecay': None}

        # dialog for averages
        self.showBtn = QtWidgets.QPushButton('Show quantities')
        self.showBtn.clicked.connect(self.showQuantities)
        self.layout.addWidget(self.showBtn)
        self.dialog = QtWidgets.QDialog(self, flags = QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowCloseButtonHint)
        self.dialog.setWindowTitle(self.name + ' -- Quantities')
        self.dialog_table = QtWidgets.QTableWidget(self.dialog)
        self.dialog_table.horizontalHeader().hide()
        self.dialog_table.verticalHeader().hide()
        self.dialog_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.dialog_table.setRowCount(3)
        self.dialog_table.setColumnCount(2)
        self.dialog_table.setItem(0, 0, QtWidgets.QTableWidgetItem('mean amplitude'))
        self.dialog_table.setItem(1, 0, QtWidgets.QTableWidgetItem('spike frequency (#spikes / s)'))
        self.dialog_table.setItem(2, 0, QtWidgets.QTableWidgetItem('mean τDecay'))
        self.dialog_layout = QtWidgets.QGridLayout(self.dialog)
        self.dialog.setLayout(self.dialog_layout)
        self.dialog.layout().addWidget(self.dialog_table)
        ## METHODS ##
        self.addMethod('Threshold', sd_params, self.spikeUpdate)

        self.initMethodUI()
        self.initParametersUI()

    def showQuantities(self):
        if self.output['mean amplitude'] is None or self.output['spike frequency'] is None or self.output['mean τDecay'] is None:
            return
        
        self.dialog_table.setItem(0, 1, QtWidgets.QTableWidgetItem(str(round(self.output['mean amplitude'], 4))))
        self.dialog_table.setItem(1, 1, QtWidgets.QTableWidgetItem(str(round(self.output['spike frequency'], 4))))
        self.dialog_table.setItem(2, 1, QtWidgets.QTableWidgetItem(str(round(self.output['mean τDecay'], 4))))

        self.dialog.exec()

##########################################################################################

    def initParametersUI(self):
        sd = self.methods['Threshold']

        threshold_lambda = lambda _: self.setThresholdState()

        sd.initCheckbox('dynamic_threshold', updateFunc=threshold_lambda, label='dynamic threshold')
        sd.initCheckbox('relative_threshold', updateFunc=threshold_lambda, label='relative threshold')
        sd.initSlider('dynamic_smooth', slider_params=(3,600,10,1), updateFunc=self.update, label='smooth')
        sd.initSlider('absolute_amplitude', slider_params=(0,500,1,0.01), updateFunc=self.update, label='minimal amplitude')
        sd.initRadioButtons('relative_amplitude_type', ['use std of noise', 'use std of data'], updateFunc=threshold_lambda)
        sd.initSlider('relative_amplitude', slider_params=(0,50,1,0.1), updateFunc=self.update, label='minimal amplitude (factor for std)')
        sd.initSlider('interval', slider_params=(0,400,1,1), updateFunc=self.update, label='minimal interval (ms)')

        self.setThresholdState(update = False)

        self.updateParametersUI()

    def updateLivePlot(self):
        y = self.input['y']
        seconds_range = self.data.sources[self.data.source_selection].secondsRange()
        
        # threshold visualization
        self.liveplot.setData('minimal amplitude', seconds_range, self.th)

        # plotting the signal
        self.liveplot.setData('y', seconds_range, y)

        # plotting the train
        if self.output['train'] is not None and len(self.output['train']) > 0:
            diff = max(y) - min(y)
            train_height = diff / 6
            self.liveplot.setData('train', seconds_range, train_height * self.output['train'])
        else:
            # can not call self.undisplayPlots because that would undisplay other data too, like y and thresholds
            # this is why we undisplay the train manually
            self.liveplot.setData('train', [], [])
            # and then Feature.undisplayPlots method which cares about the compare plots
            Feature.undisplayPlots(self)

        if self.output['time'] is not None and self.output['amplitude'] is not None:
            self.liveplot.setData('train symbols', [seconds_range[t] for t in self.output['time']], self.output['amplitude'])
        else:
            self.liveplot.setData('train symbols', [], [])

    def clear(self):
        self.clearData()
        self.undisplayPlots()

    def undisplayPlots(self):
        Feature.undisplayPlots(self)
        self.liveplot.setData('minimal amplitude', [], [])
        self.liveplot.setData('y', [], [])
        self.liveplot.setData('train', [], [])
        self.liveplot.setData('train symbols', [], [])


##########################################################################################

    def show(self):
        QtWidgets.QWidget.show(self)
        self.setThresholdState(update=False)

    def setThresholdState(self, update=True):
        sd = self.methods['Threshold']
        if sd.getParametersGUI('dynamic_threshold').isChecked():
            sd.setParameters({'dynamic_threshold':True})
            sd.getParametersGUI('dynamic_smooth').show()
        else:
            sd.setParameters({'dynamic_threshold':False})
            sd.getParametersGUI('dynamic_smooth').hide()

        if sd.getParametersGUI('relative_threshold').isChecked():
            sd.setParameters({'relative_threshold': True})
            sd.getParametersGUI('absolute_amplitude').hide()
            for btn in sd.getParametersGUI('relative_amplitude_type'):
                btn.show()
                if btn.isChecked():
                    sd.setParameters({'relative_amplitude_type': btn.text()})
            sd.getParametersGUI('relative_amplitude').show()
        else:
            sd.setParameters({'relative_threshold': False})
            sd.getParametersGUI('absolute_amplitude').show()
            for btn in sd.getParametersGUI('relative_amplitude_type'):
                btn.hide()
            sd.getParametersGUI('relative_amplitude').hide()

        self.layout.update()
        if update:
            self.update()

    def spikeUpdate(self, y, object_source_frequency, object_noise_std, dynamic_threshold, relative_threshold, dynamic_smooth, absolute_amplitude, relative_amplitude_type, relative_amplitude, interval):
        
        x = np.arange(len(y))

        # if there is no noise std, we calculate a default noise and its std
        if object_noise_std == 0:
            noise = y - savgol_filter(y, 5, 3)
            object_noise_std = np.std(noise)

        if relative_threshold:
            amplitude = relative_amplitude * (object_noise_std if relative_amplitude_type == 'use std of noise' else np.std(y))
        else:
            amplitude = absolute_amplitude

        if dynamic_threshold:
            self.th = movingAverage(y, window=dynamic_smooth)+amplitude
        else:
            self.th = np.full(len(y), amplitude, dtype = float)

        # change interval from ms to frames
        interval = object_source_frequency * interval / 1000.0

        # get spike positions as frame numbers
        spikes = self.spikeDetection(y, self.th, interval)

        n = len(spikes)
        if n is not 0:
            time = x[spikes]
            amplitude = y[spikes]

            decay = np.zeros_like(amplitude)
            i = 0
            for decay_start in time:
                if interval < 3:
                    decay[i] = np.nan
                else:
                    decay_interval = round(interval/2)
                    decay_data = y[decay_start:decay_start+decay_interval]
                    try:
                        x_data = np.linspace(0, decay_interval/object_source_frequency, decay_interval)
                        popt, _ = curve_fit(func_exp, xdata=x_data, ydata=decay_data, p0=[2.5, 15])
                        decay[i] = 1/popt[1]
                    except:
                        decay[i] = np.nan
                i += 1

            return {
                'spike frequency': n*object_source_frequency/x[-1],
                'mean amplitude': np.mean(amplitude),
                'train': self.getSpikeTrain(spikes, len(y)),
                'time': time,
                'amplitude': amplitude,
                'τDecay': decay,
                'mean τDecay': decay[~np.isnan(decay)].mean()
            }
        else:
            return {
                'spike frequency': None,
                'mean amplitude': None,
                'train': None,
                'time': None,
                'amplitude': None,
                'τDecay': None,
                'mean τDecay': None
            }

#--------------------------------------------------------#
#   Functional
#--------------------------------------------------------#

    def spikeDetection(self, y, thresh, interval):
        """
        interval in frames
        """
        spikes = []
        i = 1
        n = len(y)
        while i < n-1:
            # if value is over the threshold and a local maximum
            if y[i]>thresh[i]:
                if (y[i] >= y[i-1] and y[i] >= y[i+1]):
                    spikes.append(i)
            i+=1
        j = 0
        while j < len(spikes)-1:
            if (spikes[j+1]-spikes[j]) < interval:
                if y[spikes[j]]>y[spikes[j+1]]:
                    del spikes[j+1]
                else:
                    del spikes[j]
            else:
                j+=1
        return spikes


    def getSpikeTrain(self, spikes, n):
        spike_train = np.zeros(n-1,dtype=float)
        for s in spikes:
            spike_train[s] = 1
        return spike_train
