import unittest
import numpy as np
from PyQt5 import QtGui

from features.Baseline import Baseline
from tests.TestData import cell_mean, source, DataManager, Plot
from util.conf import bl_asymmetric_ls_params, bl_top_hat_params, bl_moving_average_params, bl_polynomial_fitting_params

app = QtGui.QApplication([])

class BaselineTest(unittest.TestCase):

    def setUp(self):
        self.baseline = Baseline(DataManager(), liveplot = (None, Plot()))
        self.baseline.input['y'] = cell_mean
        self.baseline.input['object_source'] = source

    def tearDown(self):
        self.baseline.deleteLater()

    def update(self):
        self.baseline.active = True
        self.baseline.update(updateDependend = False, plot = False)

    def execute_test(self, method_name, method, params):
        self.baseline.method_combo.setCurrentText(method_name)
        self.update()

        baseline1 = self.baseline.output['baseline']
        y1 = self.baseline.output['y']

        self.assertTrue(len(baseline1) == len(cell_mean) == len(y1))

        out2 = method(**self.baseline.input, **params)

        baseline2 = out2['baseline']
        y2 = out2['y']

        self.assertTrue(np.array_equal(baseline1, baseline2))
        self.assertTrue(np.array_equal(y1, y2))

    def test_als(self):
        self.execute_test('Asymmetric Least Squares', self.baseline.alsWrapper, bl_asymmetric_ls_params)

    def test_tophat(self):
        self.execute_test('Top Hat', self.baseline.topHatWrapper, bl_top_hat_params)

    def test_movingaverage(self):
        self.execute_test('Moving Average', self.baseline.movingAverageWrapper, bl_moving_average_params)

    def test_polyfit(self):
        self.execute_test('Polynomial Fitting', self.baseline.polyFit, bl_polynomial_fitting_params)
