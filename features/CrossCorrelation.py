# load Modules
from PyQt5 import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
import numpy as np
import math
from scipy.signal import firwin, lfilter, lfilter_zi, hilbert, correlate

from util.functions import movingAverage
from features.Feature import Feature
from util.conf import cc_train_params, cc_amplitude_params

class CrossCorrelation(Feature):

    def __init__(self, data, name, input_data_name, parent=None, liveplot=None, step_mode = False):

        # Init Feature
        Feature.__init__(self, name, data, parent, liveplot)

        self.input_data_name = input_data_name
        self.step_mode = step_mode

        # data
        self.output = {'xrange':None, 'correlation':None, 'coefficient':None, 'delay':None, 'delay coefficient': None}

        self.showBtn = QtWidgets.QPushButton('Show Correlation Coefficients and Main Lags', self)
        self.showBtn.clicked.connect(self.showCoefficients)
        self.layout.addWidget(self.showBtn)
        self.dialog = QtWidgets.QDialog(self, flags = QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowCloseButtonHint)
        self.dialog.setWindowTitle(self.name + ' -- Correlation Coefficients and Main Lags')
        self.dialog_table_coefficients = QtWidgets.QTableWidget(self.dialog)
        self.dialog_table_delay = QtWidgets.QTableWidget(self.dialog)
        self.dialog_table_delay_coefficients = QtWidgets.QTableWidget(self.dialog)
        self.dialog_layout = QtWidgets.QGridLayout(self.dialog)
        self.dialog.setLayout(self.dialog_layout)
        self.dialog.layout().addWidget(QtWidgets.QLabel('Correlation Coefficients'))
        self.dialog.layout().addWidget(self.dialog_table_coefficients)
        self.dialog_mainlag_layout = QtWidgets.QLabel()
        self.dialog.layout().addWidget(self.dialog_mainlag_layout)
        self.dialog.layout().addWidget(self.dialog_table_delay)
        self.dialog_table_delay_coefficients_label = QtWidgets.QLabel('Correlation Coefficients at Main Lags')
        self.dialog.layout().addWidget(self.dialog_table_delay_coefficients_label)
        self.dialog.layout().addWidget(self.dialog_table_delay_coefficients)

    def showCoefficients(self):
        if self.output['coefficient'] is None or self.input[self.input_data_name] is None or self.output['delay'] is None or self.output['delay coefficient'] is None:
            return
        
        coeff = self.output['coefficient']
        delay = self.output['delay']
        delay_coefficient = self.output['delay coefficient']
        names = [data['name'] for data in self.input[self.input_data_name]]

        spike_cc = isinstance(self, SpikeCrossCorrelation)

        self.dialog_mainlag_layout.setText('Main Lags' if not spike_cc else 'Centers of Bins that contain Main Lags')

        if len(names) == 0 or len(coeff) == 0 or len(delay) == 0:
            return
            
        if spike_cc:
            self.dialog_table_delay_coefficients.hide()
            self.dialog_table_delay_coefficients_label.hide()
        else:
            self.dialog_table_delay_coefficients.show()
            self.dialog_table_delay_coefficients_label.show()

        self.dialog_table_coefficients.setRowCount(0)
        self.dialog_table_coefficients.setColumnCount(len(names)-1)
        self.dialog_table_delay.setRowCount(0)
        self.dialog_table_delay.setColumnCount(len(names)-1)
        if not spike_cc:
            self.dialog_table_delay_coefficients.setRowCount(0)
            self.dialog_table_delay_coefficients.setColumnCount(len(names)-1)

        n = len(names)

        for i in range(n-1):
            self.dialog_table_coefficients.horizontalHeader().setResizeMode(i, QtGui.QHeaderView.ResizeToContents)
            self.dialog_table_delay.horizontalHeader().setResizeMode(i, QtGui.QHeaderView.ResizeToContents)
            if not spike_cc:
                self.dialog_table_delay_coefficients.horizontalHeader().setResizeMode(i, QtGui.QHeaderView.ResizeToContents)

        self.dialog_table_coefficients.setHorizontalHeaderLabels(names[1:])
        self.dialog_table_delay.setHorizontalHeaderLabels(names[1:])
        if not spike_cc:
            self.dialog_table_delay_coefficients.setHorizontalHeaderLabels(names[1:])

        for i in range(n-1):
            self.dialog_table_coefficients.insertRow(i)
            self.dialog_table_delay.insertRow(i)
            self.dialog_table_coefficients.setVerticalHeaderItem(i, QtWidgets.QTableWidgetItem(names[i]))
            self.dialog_table_delay.setVerticalHeaderItem(i, QtWidgets.QTableWidgetItem(names[i]))
            if not spike_cc:
                self.dialog_table_delay_coefficients.insertRow(i)
                self.dialog_table_delay_coefficients.setVerticalHeaderItem(i, QtWidgets.QTableWidgetItem(names[i]))
            for j in range(i+1, n):
                c = coeff[i,j]
                d = delay[i,j]
                self.dialog_table_coefficients.setItem(i, j-1, QtWidgets.QTableWidgetItem('{0:.4f}'.format(round(c, 4))))
                self.dialog_table_delay.setItem(i, j-1, QtWidgets.QTableWidgetItem('{0:.4f}'.format(round(d, 4))))
                if not spike_cc:
                    d_c = delay_coefficient[i,j]
                    self.dialog_table_delay_coefficients.setItem(i, j-1, QtWidgets.QTableWidgetItem('{0:.4f}'.format(round(d_c, 4))))
        
        self.dialog.exec()

    def updateLivePlot(self):
        '''
        Plot All/Specific Correlograms
        '''
        cc = self.output['correlation']
        xrange_ = self.output['xrange']
        if cc is None or xrange_ is None:
            self.undisplayPlots()
            return
        # check if there is any deactivated spike detection where the plot may need to be reset
        if any(['train' in data.keys() and data['train'] is None for data in self.input[self.input_data_name]]):
            n = len(self.input[self.input_data_name])
            for i in range(n-1):
                data1 = self.input[self.input_data_name][i]
                invalid1 = 'train' in data1 and data1['train'] is None
                for j in range(i+1, n):
                    data2 = self.input[self.input_data_name][j]
                    invalid2 = 'train' in data2 and data2['train'] is None
                    if invalid1 or invalid2:
                        self.liveplot.setData('CC {} -- {}'.format(data1['name'], data2['name']), [], [])
        names = [data['name'] for data in self.input[self.input_data_name] if not 'train' in data.keys() or data['train'] is not None]
        n = len(names)
        for i in range(n-1):
            for j in range(i+1, n):
                if len(xrange_) != len(cc[i,j]) + self.step_mode:
                    x = []
                    y = []
                    print('something unexpected happened for the cross correlation between {} and {}'.format(names[i], names[j]))
                else:
                    x = xrange_
                    y = cc[i,j]
                self.liveplot.setData('CC {} -- {}'.format(names[i], names[j]), x, y)

    def clear(self):
        self.clearData()
        self.undisplayPlots()

    def undisplayPlots(self):
        Feature.undisplayPlots(self)
        if self.input[self.input_data_name] is not None:
            names = [data['name'] for data in self.input[self.input_data_name]]
            n = len(names)
            for i in range(n-1):
                for j in range(i+1, n):
                    self.liveplot.setData('CC {} -- {}'.format(names[i], names[j]), [], [])

    def adjustFrequencies(self, signals, freqs):
        """
        Input: a list of signals and their corresponding frequencies.
        Return: the signals adjusted in a way such that their frequencies are adapted to the lowest of all
        frequencies. Also, the lowest frequency.
        """
        min_freq = min(freqs)
        for signal_index, freq in zip(range(len(signals)), freqs):
            if freq != min_freq:
                signal_len = len(signals[signal_index])
                new_signal_len = math.ceil(signal_len * min_freq / freq)
                signals[signal_index] = np.interp(np.linspace(0, signal_len-1, num = new_signal_len), np.arange(signal_len), signals[signal_index])
        return signals, min_freq

    def sliceSignals(self, len1, len2, offset1, offset2):
        """
        Input: the length of two signals and their offsets. Both values shall be given in amount of frames.
        Return: the slices for the signals that determine the area where the signals are well-defined.
        Example:
        #           length          offset          well-defined    combined        slices
        signal1     10              1               1-10            3-10            2-9
        signal2     15              3               3-17            3-10            0-7
        """
        start = max(offset1, offset2)
        end = min(offset1 + len1, offset2 + len2)
        return slice(start-offset1, end-offset1), slice(start-offset2, end-offset2)

class SpikeCrossCorrelation(CrossCorrelation):

    def __init__(self, data, parent=None, liveplot=None):
        CrossCorrelation.__init__(self, data, 'Spike Cross Correlation', 'trains_data', parent, liveplot, step_mode = True)

        self.input = {'trains_data':None}

        self.addMethod('Spike Train', cc_train_params, self.trainCorrelation)
        
        self.initMethodUI()
        self.initParametersUI()

    def initParametersUI(self):
        self.methods['Spike Train'].initSlider('binfactor', slider_params=(1,50,1,1), updateFunc=self.update, label='binsize (factor)')
        self.methods['Spike Train'].initSlider('maxlag', slider_params=(10,500,100,0.01), updateFunc=self.update, label='max lag (s)')

        self.updateParametersUI()

    def trainCorrelation(self, trains_data, binfactor, maxlag):
        '''
        binfactor: factor that will be multiplied with 1/freq to give binsize
        '''

        trains = [data['train'] for data in trains_data if data['train'] is not None]
        freqs = [data['freq'] for data in trains_data if data['train'] is not None]
        offsets = [data['offset'] for data in trains_data if data['train'] is not None]

        n = len(trains)

        if n < 2:
            # TODO throw ui error: need multiple Objects with active eventdetection
            return {'xrange': None, 'correlation': None, 'coefficient': None, 'delay':None, 'delay coefficient': None}

        trains, freq = self.adjustFrequencies(trains, freqs)
        offsets = [round(offset * freq) for offset in offsets]

        lens = [len(train) for train in trains]

        # bins
        binsize = binfactor / freq
        number_of_bins = round(maxlag/binsize)
        #bins = np.arange(-number_of_bins-0.5, number_of_bins+0.5)*binsize
        bins = np.arange(-number_of_bins, number_of_bins + 1) * binsize
        
        cc = np.zeros((n,n), dtype=object)
        delay = np.zeros((n,n))
        coef = np.zeros((n,n))
        delay_coefficient = np.zeros((n,n))
        
        for i in range(n-1):
            for j in range(i+1, n):

                slice1, slice2 = self.sliceSignals(lens[i], lens[j], offsets[i], offsets[j])

                data1 = trains[i][slice1]
                data2 = trains[j][slice2]
                
                if len(data1) == 0 or len(data2) == 0:
                    cc[i,j] = []
                    delay[i,j] = np.nan
                    coef[i,j] = np.nan
                    delay_coefficient[i,j] = np.nan
                    continue

                #data1 -= np.mean(data1)
                #data2 -= np.mean(data2)

                norm_ones = np.ones(len(data1))
                norm = correlate(norm_ones, norm_ones, mode='same')
                scc = correlate(data1, data2, mode='same') / (np.std(data1) * np.std(data2) * norm)

                valid_values = len(scc)
                needed_values = 2 * number_of_bins
                if valid_values < needed_values * binfactor:
                    cc[i,j] = np.zeros(needed_values)
                    if valid_values % 2 == 0:
                        valid_left, valid_right = int(valid_values / 2), int(valid_values / 2)
                    else:
                        valid_left = int(valid_values / 2)
                        valid_right = valid_values - valid_left
                    padded_valid = np.pad(
                        scc,
                        [number_of_bins * binfactor - valid_left, number_of_bins * binfactor - valid_right],
                        mode = 'constant')
                    for k in range(needed_values):
                        from_ = k * binfactor
                        to_ = (k + 1) * binfactor
                        cc[i,j][k] = sum(padded_valid[from_ : to_])
                else:
                    mid = int(len(scc) / 2)
                    cc[i,j] = np.zeros(needed_values)
                    for k in range(needed_values):
                        from_ = mid + ((-number_of_bins + k) *binfactor)
                        to_ = mid + ((-number_of_bins + k + 1) * binfactor)
                        cc[i,j][k] = sum(scc[from_ : to_])

                argmax = np.argmax(np.abs(cc[i,j]))
                delay[i,j] = bins[argmax] + 0.5 * binsize
                coef[i,j] = np.corrcoef(data1, data2)[0,1]
                delay_coefficient[i,j] = np.nan


        return {'xrange': bins, 'correlation': cc, 'coefficient': coef, 'delay': delay, 'delay coefficient': delay_coefficient}

class AmplitudeCrossCorrelation(CrossCorrelation):

    def __init__(self, data, parent, liveplot):
        CrossCorrelation.__init__(self, data, 'Amplitude Cross Correlation', 'amplitudes_data', parent, liveplot, step_mode = False)

        self.input = {'amplitudes_data':None}

        self.addMethod('Amplitude', cc_amplitude_params, self.amplitudeCorrelation)
        
        self.initMethodUI()
        self.initParametersUI()
    
    def show(self):
        Feature.show(self)
        self.bandpassStateChanged(update = False)
        self.instantaneousStateChanged(update = False)

    def initParametersUI(self):
        self.methods['Amplitude'].initSlider('maxlag', slider_params=(10,500,100,0.01), updateFunc=self.update, label='max lag (s)')
        self.methods['Amplitude'].initCheckbox('use_bandpass', updateFunc=lambda _:self.bandpassStateChanged(), label='Use bandpass filter')
        self.methods['Amplitude'].initSlider('order', slider_params=(3,10,1,1), updateFunc=self.update, label='bandpass order')
        self.methods['Amplitude'].initSlider('highpass_freq', slider_params=(1,124,1,1), updateFunc=self.update, label='highpass freq (Hz)')
        self.methods['Amplitude'].initSlider('lowpass_freq', slider_params=(1,124,1,1), updateFunc=self.update, label='lowpass freq (Hz)')
        self.methods['Amplitude'].initCheckbox('use_instantaneous', updateFunc=lambda _: self.instantaneousStateChanged(), label='Use instantaneous amplitude')

        self.bandpassStateChanged()
        self.instantaneousStateChanged()

        self.updateParametersUI()

    def bandpassStateChanged(self, update = True):
        acc = self.methods['Amplitude']
        # hide and show the checkbox to avoid a graphical bug that would otherwise sometimes happen
        acc.getParametersGUI('use_instantaneous').hide()
        acc.getParametersGUI('use_instantaneous').show()

        if acc.getParametersGUI('use_bandpass').isChecked():
            acc.setParameters({'use_bandpass': True})
            acc.getParametersGUI('order').show()
            acc.getParametersGUI('highpass_freq').show()
            acc.getParametersGUI('lowpass_freq').show()
        else:
            acc.setParameters({'use_bandpass': False})
            acc.getParametersGUI('order').hide()
            acc.getParametersGUI('highpass_freq').hide()
            acc.getParametersGUI('lowpass_freq').hide()
        self.layout.update()
        if update:
            self.update()

    def instantaneousStateChanged(self, update = True):
        acc = self.methods['Amplitude']
        acc.setParameters({'use_instantaneous': acc.getParametersGUI('use_instantaneous').isChecked()})
        if update:
            self.update()
        
    def instantaneous_amplitude(self, signal):
        hilbert_ = hilbert(signal)
        return np.abs(hilbert_)
    
    def bandpass(self, signal, order, freq, highpass_freq, lowpass_freq):
        filter_ = firwin(order, [highpass_freq, lowpass_freq], fs = freq, pass_zero = False)
        zi = lfilter_zi(filter_, 1.0)
        return lfilter(filter_, 1.0, signal, zi = zi * signal[0])[0]

    def amplitudeCorrelation(self, amplitudes_data, maxlag, use_bandpass, order, highpass_freq, lowpass_freq, use_instantaneous):
        """
        A Cross Correlation approach with options described in the following paper:

        Title:
            Cross-correlation of instantaneous amplitudes of field potential oscillations: a
            straightforward method to estimate the directionality and lag between brain areas
        Author:
            Avishek Adhikari, Torfi Sigurdsson, Mihir A. Topiwala, and Joshua A. Gordon
        Source:
            https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2924932/
        """

        n = len(amplitudes_data)
        
        if n < 2 or (use_bandpass and lowpass_freq <= highpass_freq):
            # TODO throw ui error: please select multiple trains...
            return {'xrange': None, 'correlation': None, 'coefficient': None, 'delay':None, 'delay coefficient': None}

        amps = [np.copy(data['processed']) for data in amplitudes_data]
        freqs = [data['freq'] for data in amplitudes_data]
        offsets = [data['offset'] for data in amplitudes_data]

        amps, freq = self.adjustFrequencies(amps, freqs)
        offsets = [round(offset * freq) for offset in offsets]
        
        if use_bandpass:
            if highpass_freq <= 0:
                highpass_freq = 1
            if lowpass_freq >= math.floor(freq/2):
                lowpass_freq = math.floor(freq/2) - 1
            if lowpass_freq <= highpass_freq or order >= round(freq) or order < 2:
                return {'xrange': None, 'correlation': None, 'coefficient': None, 'delay':None, 'delay coefficient': None}
        
        lens = [len(amp) for amp in amps]

        period_duration = 1.0 / freq
        number_of_xrange_values = round(maxlag / period_duration)
        xrange_ = np.arange(-number_of_xrange_values, number_of_xrange_values+1) * period_duration

        cc = np.zeros((n,n), dtype=object)
        delay = np.zeros((n,n))
        coef = np.zeros((n,n))
        delay_coefficient = np.zeros((n,n))

        for i in range(n-1):
            for j in range(i+1, n):

                slice1, slice2 = self.sliceSignals(lens[i], lens[j], offsets[i], offsets[j])

                data1 = amps[i][slice1]
                data2 = amps[j][slice2]

                if len(data1) == 0 or len(data2) == 0:
                    cc[i,j] = []
                    delay[i,j] = np.nan
                    coef[i,j] = np.nan
                    delay_coefficient[i,j] = np.nan
                    continue

                if use_bandpass:
                    data1 = self.bandpass(data1, order, freq, highpass_freq, lowpass_freq)
                    data2 = self.bandpass(data2, order, freq, highpass_freq, lowpass_freq)

                if use_instantaneous:
                    data1 = self.instantaneous_amplitude(data1)
                    data2 = self.instantaneous_amplitude(data2)

                data1 -= np.mean(data1)
                data2 -= np.mean(data2)

                norm_ones = np.ones(len(data1))
                norm = correlate(norm_ones, norm_ones, mode='same')
                acc = correlate(data1, data2, mode='same') / (np.std(data1) * np.std(data2) * norm)

                valid_values = len(acc)
                needed_values = 2 * number_of_xrange_values + 1
                if valid_values < needed_values:
                    cc[i,j] = np.zeros(needed_values)
                    if valid_values % 2 == 0:
                        valid_left, valid_right = int(valid_values / 2), int(valid_values / 2)
                    else:
                        valid_left = math.floor(valid_values / 2)
                        valid_right = valid_values - valid_left
                    cc[i,j][number_of_xrange_values - valid_left:number_of_xrange_values + valid_right] = acc
                else:
                    mid = int(len(acc) / 2)
                    cc[i,j] = acc[mid-number_of_xrange_values:mid+number_of_xrange_values+1]
                
                argmax = np.argmax(np.abs(cc[i,j]))
                delay[i,j] = xrange_[argmax]
                coef[i,j] = np.corrcoef(data1, data2)[0,1]
                offset_in_frames = argmax - number_of_xrange_values
                slice1, slice2 = self.sliceSignals(len(data1), len(data2), 0, offset_in_frames)
                data1 = data1[slice1]
                data2 = data2[slice2]
                delay_coefficient[i,j] = np.corrcoef(data1, data2)[0,1]

        return {'xrange':xrange_, 'correlation':cc, 'coefficient':coef, 'delay': delay, 'delay coefficient': delay_coefficient}
