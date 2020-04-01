import unittest
import numpy as np
from PyQt5 import QtGui

from features.Smoothing import Smoothing
from tests.TestData import cell_mean, DataManager, source
from util.conf import sg_butterworth_params, sg_moving_average_params, sg_savitzky_golay_params

app = QtGui.QApplication([])

class SmoothingTest(unittest.TestCase):

    def setUp(self):
        self.smoothing = Smoothing(DataManager())
        self.smoothing.input['y'] = cell_mean
        self.smoothing.input['object_source_frequency'] = source.original_frequency

    def tearDown(self):
        self.smoothing.deleteLater()

    def update(self):
        self.smoothing.active = True
        self.smoothing.update(updateDependend = False, plot = False)

    def execute_test(self, method_name, method, params):
        self.smoothing.method_combo.setCurrentText(method_name)
        self.update()

        y1 = self.smoothing.output['y']
        noise_std1 = self.smoothing.output['noise_std']

        self.assertEqual(len(y1), len(cell_mean))

        out2 = method(**self.smoothing.input, **params)

        y2 = out2['y']
        noise_std2 = out2['noise_std']

        self.assertTrue(np.array_equal(y1, y2))
        self.assertTrue(np.array_equal(noise_std1, noise_std2))

    def test_butterworth(self):
        
        if source.original_frequency % 2 == 0:
            max_highcut = int(source.original_frequency / 2) - 1
        else:
            max_highcut = int(source.original_frequency / 2) # rounds down

        if sg_butterworth_params['highcut'] > max_highcut:
            sg_butterworth_params['highcut'] = max_highcut

        self.execute_test('Butterworth', self.smoothing.butter_lowpass_filter_wrapper, sg_butterworth_params)

    def test_movingaverage(self):
        self.execute_test('Moving Average', self.smoothing.movingAverageWrapper, sg_moving_average_params)

    def test_savitzkygolay(self):
        self.execute_test('Savitzky Golay', self.smoothing.updateSGData, sg_savitzky_golay_params)
