import unittest
import numpy as np
from PyQt5 import QtGui

from features.EventDetection import SpikeDetection
from tests.TestData import processed, DataManager, Plot, source, noise_std
from util.conf import sd_params

app = QtGui.QApplication([])

class SpikeDetectionTest(unittest.TestCase):

    def setUp(self):
        self.spike = SpikeDetection(DataManager(), liveplot = Plot())
        self.spike.input['y'] = processed
        self.spike.input['object_source_frequency'] = source.original_frequency
        self.spike.input['object_noise_std'] = noise_std

    def tearDown(self):
        self.spike.deleteLater()

    def update(self):
        self.spike.active = True
        self.spike.update(updateDependend = False, plot = False)

    def test(self):
        self.update()

        time1 = self.spike.output['time']
        amplitude1 = self.spike.output['amplitude']
        train1 = self.spike.output['train']
        mean_amplitude1 = self.spike.output['mean amplitude']

        self.assertEqual(len(train1), len(processed) - 1)
        self.assertEqual(len(time1), len(amplitude1))
        self.assertEqual(np.mean(amplitude1), mean_amplitude1)

        # is any burst outside the data?
        self.assertTrue(all([0 <= t <= len(processed) for t in time1]))

        # is the amplitude array correct?
        self.assertTrue(all([processed[t] == a for a,t in zip(amplitude1, time1)]))

        # is the train array set correct?
        self.assertTrue(all([train1[t] == 1 for t in time1]))
        self.assertTrue(all([train1[t] == 0 for t in range(len(train1)) if t not in time1]))

        # is any spike detected multiple times?
        self.assertEqual(len(time1), len(set(time1)))

        out2 = self.spike.spikeUpdate(**self.spike.input, **sd_params)

        time2 = out2['time']
        amplitude2 = out2['amplitude']
        train2 = out2['train']
        mean_amplitude2 = out2['mean amplitude']

        self.assertTrue(np.array_equal(time1, time2))
        self.assertTrue(np.array_equal(amplitude1, amplitude2))
        self.assertTrue(np.array_equal(train1, train2))
        self.assertEqual(mean_amplitude1, mean_amplitude2)