from PyQt5 import QtGui, QtWidgets, QtCore
from copy import copy

from model.Pipeline import Pipeline

from view.FeatureButton import FeatureButton
from view.ActivateMultipleDialog import ActivateMultipleDialog
from view.SetMultipleDialog import SetMultipleDialog

from features.BackgroundSubtraction import BackgroundSubtraction
from features.MergedTif import MergedTif
from features.CrossCorrelation import SpikeCrossCorrelation, AmplitudeCrossCorrelation
from features.Baseline import Baseline

class PipelineManager(QtGui.QWidget):

    def __init__(self, data_manager, parent=None):
        
        QtGui.QWidget.__init__(self, parent)
        
        self.setMinimumSize(300,700)

        self.parent = parent

        self.data_manager = data_manager
        self.data_manager.pipeline_manager = self

        """
        we need to remember the feature that is shown, s.t. we can hide it when a object_ change has been done
        and the shown feature is not part of the current pipeline. 
        """
        self.current_feature_shown = None

        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)
        
        self.feature_view = QtWidgets.QStackedWidget(self)
        self.feature_view.setMinimumSize(290, 400)

        self.spike_cross_correlation = SpikeCrossCorrelation(data_manager, parent=self.feature_view, liveplot=data_manager.plot_manager.spike_cross_correlation)
        self.amplitude_cross_correlation = AmplitudeCrossCorrelation(data_manager, parent=self.feature_view, liveplot=data_manager.plot_manager.amplitude_cross_correlation)

        self.pipeline_steps = []
        self.default_pipeline = Pipeline()
        self.default_pipeline.initPipeline(self.data_manager, source_is_tif = False, parent = self.feature_view)
        for index,step in enumerate(self.default_pipeline.getPipeline()):
            button = FeatureButton(step.name, self)
            self.layout.addWidget(button)
            self.pipeline_steps.append(button)
            # context menu for checkbox
            button.cb.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            button.cb.customContextMenuRequested.connect(lambda _, idx=index: self.checkboxContextMenu(idx))
            button.btn.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            button.btn.customContextMenuRequested.connect(lambda _, idx=index: self.buttonContextMenu(idx))
        self._connectCheckboxes()
        self.refreshPipelineView()

        self.layout.addWidget(self.feature_view)

    def checkboxContextMenu(self, index):
        # if amount of objects is 0 or 1: return
        if len(self.data_manager.objects) <= 1:
            return
        # if feature is backgroundsubtraction and the amount of objects that are optical data is 0 or 1: return
        amount_optical_data = len([object_ for object_ in self.data_manager.objects if object_.source.filetype == 'tif'])
        pipeline = self.data_manager.getCurrentPipeline()
        is_bs = pipeline.getPipeline()[index] is pipeline._background_subtraction
        if amount_optical_data <= 1 and is_bs:
            return
        # if feature is cc: return
        is_acc = pipeline.getPipeline()[index] is pipeline._amplitude_cross_correlation
        is_scc = pipeline.getPipeline()[index] is pipeline._spike_cross_correlation
        if is_acc or is_scc:
            return
        # otherwise: show option to display dialog
        self.menu = QtGui.QMenu(self)
        activate_multiple = self.menu.addAction('activate / deactivate for multiple objects')
        activate_multiple.triggered.connect(lambda _, idx=index: self.activateMultipleDialog(index))
        self.menu.popup(QtGui.QCursor.pos())

    def buttonContextMenu(self, index):
        # if amount of objects is 0 or 1: return
        if len(self.data_manager.objects) <= 1:
            return
        # if feature is backgroundsubtraction further checks
        pipeline = self.data_manager.getCurrentPipeline()
        is_bs = pipeline.getPipeline()[index] is pipeline._background_subtraction
        if is_bs:
            # if selected object is not optical: return
            if self.data_manager.objects[self.data_manager.object_selection].source.filetype != 'tif':
                return
            # if amount of optical objects is 0 or 1: return
            amount_optical_data = len([object_ for object_ in self.data_manager.objects if object_.source.filetype == 'tif'])
            if amount_optical_data <= 1:
                return
        # if feature is cc: return
        is_acc = pipeline.getPipeline()[index] is pipeline._amplitude_cross_correlation
        is_scc = pipeline.getPipeline()[index] is pipeline._spike_cross_correlation
        if is_acc or is_scc:
            return
        # otherwise: show option to display dialog
        self.menu = QtGui.QMenu(self)
        copy_settings = self.menu.addAction('copy settings to multiple objects')
        copy_settings.triggered.connect(lambda _, idx=index: self.setMultipleDialog(index))
        self.menu.popup(QtGui.QCursor.pos())

    def setMultipleDialog(self, index):
        _ = SetMultipleDialog(self.data_manager, index)

    def activateMultipleDialog(self, index):
        _ = ActivateMultipleDialog(self.data_manager, index)

    def _disconnectCheckboxes(self):
        """
        Disconnects all Checkbox stateChanged signals.
        """
        for button in self.pipeline_steps:
            button.cb.stateChanged.disconnect()

    def _connectCheckboxes(self):
        """
        Connects all Checkbox stateChanged signals.
        """
        for index,button in enumerate(self.pipeline_steps):
            button.cb.stateChanged.connect(lambda state, idx=index: self.activeFeatureChanged(idx, state))

    def featureClick(self, index):
        pipeline = self.data_manager.getCurrentPipeline().getPipeline()
        if pipeline[index].active:
            self.showFeature(index)
        else:
            self.pipeline_steps[index].cb.setChecked(True)

    def showFeature(self, index):
        """
        Shows the feature at index. If another feature is shown before, it gets hidden. To show no feature, use showNoFeature().
        """
        if self.current_feature_shown is not None:
            self.current_feature_shown.hide()
            self.current_feature_shown = None
        if index != -1:
            pipeline = self.data_manager.getCurrentPipeline().getPipeline()
            pipeline[index].show()
            self.current_feature_shown = pipeline[index]
            self.feature_view.setCurrentWidget(pipeline[index])
        else:
            self.feature_view.setCurrentIndex(-1)

    def showNoFeature(self):
        """
        Hides all features. 
        """
        self.showFeature(-1)

    def activeFeatureChanged(self, index, state):
        """
        Called when a Checkbox stateChanged signal is emitted. 

        Shows the feature if the state is Checked now. Hides all otherwise.
        
        Sets the feature active or not active, according to the state. Refreshes the current Pipeline.
        """
        pipeline = self.data_manager.getCurrentPipeline().getPipeline()
        feature = pipeline[index]
        if state == QtCore.Qt.Checked:
            feature.active = True
            feature.activateFunc()
            self.showFeature(index)
            self.data_manager.plot_manager.refreshPlots(index)
        else:
            feature.setActive(False)
            self.showNoFeature()
            self.data_manager.plot_manager.refreshPlots()
        # changes checkable states of other features
        if isinstance(feature, MergedTif):
            self.refreshPipelineView()
        self.data_manager.refreshPipeline(start_with_feature = feature)

    def refreshPipelineView(self):
        """
        Sets all the Checkboxes and Buttons according to the current Pipeline, without emitting stateChanged signals.
        """
        self._disconnectCheckboxes()
        pipeline = self.data_manager.getCurrentPipeline()
        default_pipeline = pipeline is self.default_pipeline
        pipeline = pipeline.getPipeline()
        non_tif_source = (self.data_manager.source_selection is not None
            and self.data_manager.sources[self.data_manager.source_selection].filetype != 'tif')
        merged_tif_active = (self.data_manager.source_selection is not None
            and pipeline[1].active)
        for index,step in enumerate(pipeline):
            # never activate BSR and MergedTif for non-tif-sources
            # never activate any features for default pipeline
            # if MergedTif is active other features are not activated
            if default_pipeline or ((isinstance(pipeline[index], BackgroundSubtraction)  or
                                     (isinstance(pipeline[index], MergedTif)))  and non_tif_source):
                self.pipeline_steps[index].cb.setCheckable(False)
            elif merged_tif_active and not isinstance(pipeline[index], MergedTif):
                self.pipeline_steps[index].cb.setCheckable(False)
            else:
                self.pipeline_steps[index].cb.setCheckable(True)
            self.pipeline_steps[index].cb.setChecked(step.active)
            # always disconnect, s.t. we dont get multiple calls from one signal
            try: self.pipeline_steps[index].btn.clicked.disconnect()
            except TypeError: pass
            self.pipeline_steps[index].btn.clicked.connect(lambda checked, idx=index: self.featureClick(idx))
        self._connectCheckboxes()

    def refreshView(self):
        """
        calls refreshPipelineView(). if there is a feature that is being shown and 
        the same kind of feature in the current pipeline is active, we show the feature
        from the current pipeline. Otherwise, we show no feature.
        """
        self.refreshPipelineView()
        still_show_feature = False
        if self.current_feature_shown is not None:
            for index, step in enumerate(self.data_manager.getCurrentPipeline().getPipeline()):
                if type(step) == type(self.current_feature_shown) and step.active:
                    self.showFeature(index)
                    still_show_feature = True
                    break
        if not still_show_feature:
            self.showNoFeature()