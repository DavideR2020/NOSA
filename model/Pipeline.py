from dataclasses import dataclass
from copy import deepcopy
import numpy as np

from features.BackgroundSubtraction import BackgroundSubtraction
from features.Baseline import Baseline
from features.Smoothing import Smoothing
from features.AdjustFrequency import AdjustFrequency
from features.EventDetection import SpikeDetection, BurstDetection
from features.EventShape import EventShape
from features.PowerSpectrum import PowerSpectrum
from features.CrossCorrelation import SpikeCrossCorrelation, AmplitudeCrossCorrelation

@dataclass
class Pipeline():
    _background_subtraction: BackgroundSubtraction = None
    _baseline: Baseline = None
    _smoothing: Smoothing = None
    _adjust_frequency = None
    _spike_detection: SpikeDetection = None
    _burst_detection: BurstDetection = None
    _event_shape: EventShape = None
    _power_spectrum: PowerSpectrum = None
    _spike_cross_correlation: SpikeCrossCorrelation = None
    _amplitude_cross_correlation: AmplitudeCrossCorrelation = None

    def initPipeline(self, data_manager, source_is_tif, parent = None):
        self._background_subtraction = BackgroundSubtraction(data_manager, parent=parent, liveplot=data_manager.plot_manager.background_subtraction)
        baseline_liveplot = (data_manager.plot_manager.cell_selection.ui.roiPlot, data_manager.plot_manager.baseline)
        self._baseline = Baseline(data_manager, parent=parent, liveplot=baseline_liveplot)
        self._baseline.active = source_is_tif
        self._smoothing = Smoothing(data_manager, parent=parent, liveplot=data_manager.plot_manager.smoothing)
        self._adjust_frequency = AdjustFrequency(data_manager, parent=data_manager.source_manager.adjust_frequency_dialog.feature_view)
        self._spike_detection = SpikeDetection(data_manager, parent=parent, liveplot=data_manager.plot_manager.spike_detection)
        self._burst_detection = BurstDetection(data_manager, parent=parent, liveplot=data_manager.plot_manager.burst_detection)
        self._event_shape = EventShape(data_manager, parent=parent, liveplot=data_manager.plot_manager.event_shape)
        self._power_spectrum = PowerSpectrum(data_manager, parent=parent, liveplot=data_manager.plot_manager.frequency_spectrum)
        self._spike_cross_correlation = data_manager.pipeline_manager.spike_cross_correlation
        self._amplitude_cross_correlation = data_manager.pipeline_manager.amplitude_cross_correlation

    def getPipeline(self):
        return [
            self._background_subtraction,
            self._baseline,
            self._smoothing,
            self._spike_detection,
            self._burst_detection,
            self._event_shape,
            self._power_spectrum,
            self._spike_cross_correlation,
            self._amplitude_cross_correlation
        ]

    def getCalculatingPipeline(self):
        return [
            self._background_subtraction,
            self._baseline,
            self._adjust_frequency,
            self._smoothing,
            self._spike_detection,
            self._burst_detection,
            self._event_shape,
            self._power_spectrum,
            self._spike_cross_correlation,
            self._amplitude_cross_correlation
        ]

    def getActivePipeline(self):
        return [step for step in self.getPipeline() if step.active]

    def initMethodConfigurations(self, conf_pipeline, filetype):
        conf_p = conf_pipeline.getPipeline()
        for index,step in enumerate(self.getPipeline()):
            # set activated method
            step.disconnectMethodCombo()
            step.method_combo.setCurrentIndex(conf_p[index].method_combo.currentIndex())
            step.updateParametersUI()
            step.connectMethodCombo()
            # set parameters
            for key,method in step.methods.items():
                method.setParameters(deepcopy(conf_p[index].methods[key].parameters), prevent_update = True)
            # never activate BSR for non-tif-sources
            if isinstance(step, BackgroundSubtraction) and filetype != 'tif':
                step.active = False
            else:
                step.active = conf_p[index].active

    def getActiveStates(self):
        return [
            step.active for step in self.getPipeline()
        ]

    def getCalculatingActiveStates(self):
        return [
            step.active for step in self.getCalculatingPipeline()
        ]

    def getRawFeatures(self):
        return [
            self._background_subtraction
        ]

    def getProcessingFeatures(self):
        return [
            self._background_subtraction,
            self._baseline,
            self._adjust_frequency,
            self._smoothing
        ]