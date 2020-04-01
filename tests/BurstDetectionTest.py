import unittest
import numpy as np
from PyQt5 import QtGui

from features.EventDetection import BurstDetection
from tests.TestData import processed, DataManager, Plot, source, noise_std
from util.conf import bd_params

app = QtGui.QApplication([])

class BurstDetectionTest(unittest.TestCase):

    def setUp(self):
        self.burst = BurstDetection(DataManager(), liveplot = Plot())
        self.burst.input['y'] = processed
        self.burst.input['object_source_frequency'] = source.original_frequency
        self.burst.input['object_noise_std'] = noise_std

    def tearDown(self):
        self.burst.deleteLater()

    def update(self):
        self.burst.active = True
        self.burst.update(updateDependend = False, plot = False)

    def test(self):
        self.update()
        
        start1 = self.burst.output['start']
        end1 = self.burst.output['end']
        time1 = self.burst.output['time']
        amplitude1 = self.burst.output['amplitude']
        duration1 = self.burst.output['duration']
        train1 = self.burst.output['train']
        mean_amplitude1 = self.burst.output['mean amplitude']
        mean_duration1 = self.burst.output['mean duration']

        self.assertEqual(len(train1), len(processed) - 1)
        self.assertTrue(len(time1) == len(amplitude1) == len(start1) == len(end1))
        np.testing.assert_equal(np.mean(amplitude1), mean_amplitude1)
        np.testing.assert_equal(np.mean(duration1), mean_duration1)

        # is any burst outside the data?
        self.assertTrue(all([s >= 0 for s in start1]))
        self.assertTrue(all([e <= len(processed) for e in end1]))
        
        # is the amplitude array set correct?
        self.assertTrue(all([processed[t] == a for a,t in zip(amplitude1, time1)]))

        # is start <= time <= end for every burst?
        self.assertTrue(all([s <= t <= e for s, t, e in zip(start1, time1, end1)]))

        # are any two bursts overlapping? (should never happen.)
        burst_indices = set()
        for s, e in zip(start1, end1):
            range_ = range(s, e)
            self.assertEqual(0, len([index for index in range_ if index in burst_indices]))
            burst_indices.update(range_)
        
        # is the train array set correct?
        self.assertTrue(all([train1[t] == 1 for t in burst_indices]))
        self.assertTrue(all([train1[t] == 0 for t in range(len(train1)) if t not in burst_indices]))

        out2 = self.burst.burstUpdate(**self.burst.input, **bd_params)

        start2 = out2['start']
        end2 = out2['end']
        time2 = out2['time']
        amplitude2 = out2['amplitude']
        duration2 = out2['duration']
        train2 = out2['train']
        mean_amplitude2 = out2['mean amplitude']
        mean_duration2 = out2['mean duration']

        self.assertTrue(np.array_equal(start1, start2))
        self.assertTrue(np.array_equal(end1, end2))
        self.assertTrue(np.array_equal(time1, time2))
        self.assertTrue(np.array_equal(amplitude1, amplitude2))
        self.assertTrue(np.array_equal(duration1, duration2))
        self.assertTrue(np.array_equal(train1, train2))
        np.testing.assert_equal(mean_amplitude1, mean_amplitude2)
        np.testing.assert_equal(mean_duration1, mean_duration2)