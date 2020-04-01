import unittest
import numpy as np
from PyQt5 import QtGui

from features.PowerSpectrum import PowerSpectrum
from tests.TestData import processed, DataManager, Plot, source
from util.conf import fs_fft_params

app = QtGui.QApplication([])

class PowerSpectrumTest(unittest.TestCase):

    def setUp(self):
        self.powerspectrum = PowerSpectrum(DataManager(), liveplot = Plot())
        self.powerspectrum.input['y'] = processed
        self.powerspectrum.input['object_source_frequency'] = source.original_frequency

    def tearDown(self):
        self.powerspectrum.deleteLater()

    def update(self):
        self.powerspectrum.active = True
        self.powerspectrum.update(updateDependend = False, plot = False)

    def test_powerspectrum(self):
        self.update()
        
        frequencies1 = self.powerspectrum.output['frequencies']
        psd1 = self.powerspectrum.output['psd']
        max_power1 = self.powerspectrum.output['max power']
        max_power_frequency1 = self.powerspectrum.output['max power frequency']

        self.assertEqual(len(frequencies1), len(psd1))

        # is the max power frequency a valid frequency?
        self.assertTrue(max_power_frequency1 in frequencies1)

        # is the max power a valid power value?
        self.assertTrue(max_power1 in psd1)

        # is the max power frequency set correct?
        self.assertEqual(psd1[np.where(frequencies1 == max_power_frequency1)], max(psd1))
        
        out2 = self.powerspectrum.updateFourier(**self.powerspectrum.input, **fs_fft_params)

        frequencies2 = out2['frequencies']
        psd2 = out2['psd']
        max_power2 = out2['max power']
        max_power_frequency2 = out2['max power frequency']

        self.assertTrue(np.array_equal(frequencies1, frequencies2))
        self.assertTrue(np.array_equal(psd1, psd2))
        self.assertEqual(max_power1, max_power2)
        self.assertEqual(max_power_frequency1, max_power_frequency2)
