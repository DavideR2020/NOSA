import unittest
import numpy as np
from PyQt5 import QtGui

from features.EventShape import EventShape
from tests.TestData import processed, DataManager, Plot, source, burst_time, spike_time
from util.conf import es_params
from util.functions import movingAverage

app = QtGui.QApplication([])

class EventShapeTest(unittest.TestCase):

    def setUp(self):
        self.eventshape = EventShape(DataManager(), liveplot = Plot())
        self.eventshape.input['y'] = processed
        self.eventshape.input['object_source_frequency'] = source.original_frequency
        self.eventshape.input['burst_time'] = burst_time
        self.eventshape.input['spike_time'] = spike_time

    def tearDown(self):
        self.eventshape.deleteLater()

    def update(self):
        self.eventshape.active = True
        self.eventshape.update(updateDependend = False, plot = False)

    def execute_test(self, method_name, method, params):
        self.eventshape.method_combo.setCurrentText(method_name)
        self.update()

        shapes1 = self.eventshape.output['shapes']
        mean_shape1 = self.eventshape.output['mean shape']
        mean_shape_smoothed1 = self.eventshape.output['mean shape smoothed']

        # has the shape the correct length?
        left, right = params['interval']
        self.assertTrue(round((left + right) * source.original_frequency / 1000) == len(mean_shape1) == len(mean_shape_smoothed1))
        self.assertEqual(len(mean_shape1), len(mean_shape_smoothed1))

        # is mean set correct?
        self.assertTrue(np.array_equal(np.mean(shapes1, axis = 0), mean_shape1))

        # is smoothed set correct?
        self.assertTrue(np.array_equal(mean_shape_smoothed1, movingAverage(mean_shape1, window = es_params['smooth'])))

        out2 = method(**self.eventshape.input, **params)

        shapes2 = out2['shapes']
        mean_shape2 = out2['mean shape']
        mean_shape_smoothed2 = out2['mean shape smoothed']

        self.assertTrue(np.array_equal(shapes1, shapes2))
        self.assertTrue(np.array_equal(mean_shape1, mean_shape2))
        self.assertTrue(np.array_equal(mean_shape_smoothed1, mean_shape_smoothed2))

    def test_spike(self):
        self.execute_test('Spike Shape', self.eventshape.spikeShapeCalculation, es_params)

    def test_burst(self):
        self.execute_test('Burst Shape', self.eventshape.burstShapeCalculation, es_params)
